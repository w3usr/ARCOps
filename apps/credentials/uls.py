"""
The FCC ULS import (FR-14, TR-13): the weekly complete Amateur file and the daily transaction
files, streamed from the FCC's public server into a local table, one row per callsign.

Files: `l_amat.zip` (complete, produced Sundays, about 200 MB) and `l_am_<day>.zip` (that day's
transactions, small). Each zip holds pipe-delimited `HD.dat` (header: callsign, status, grant and
expiry dates), `AM.dat` (amateur: operator class), and `EN.dat` (entity: licensee name, FRN), all
keyed by the unique system identifier. A callsign can appear on several records (its history and
renewals), so the run stages every record and then keeps, per callsign, the active one, else the
most recently granted.

Memory: the archive goes to disk in chunks and each member is read line by line; staging is a
database table written in batches, so the working set is one batch, whatever the file size.
"""

from __future__ import annotations

import datetime as dt
import logging
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.ops.branding import PRODUCT_NAME, PRODUCT_URL

from .models import LicenseRecord, UlsLicense, UlsStaging

log = logging.getLogger(__name__)

BASE = "https://data.fcc.gov/download/pub/uls"
WEEKLY_URL = f"{BASE}/complete/l_amat.zip"
DAILY_URL = f"{BASE}/daily/l_am_{{day}}.zip"  # day: sun mon tue wed thu fri sat
BATCH = 5000

STATUS = {
    "A": "active",
    "E": "expired",
    "C": "cancelled",
    "T": "cancelled",
    "X": "cancelled",
    "P": "cancelled",
    "L": "pending",
}
CLASS = {
    "A": "Advanced",
    "E": "Extra",
    "G": "General",
    "N": "Novice",
    "P": "Technician",
    "T": "Technician",
}


def _date(text: str) -> dt.date | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        m, d, y = (int(x) for x in text.split("/"))
        return dt.date(y, m, d)
    except (ValueError, TypeError):
        return None


def download(url: str, dest: Path) -> Path:
    """Stream the archive to disk in chunks; never hold it in memory."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not url.startswith("https://data.fcc.gov/"):
        raise ValueError(f"refusing to fetch {url!r}: only the FCC's server is expected here")
    # The FCC's front end answers 403 to a GET without an Accept header and an explicit
    # Accept-Encoding (urllib sends neither by default); observed 2026-09-15.
    req = urllib.request.Request(  # noqa: S310
        url,
        headers={
            "User-Agent": f"{PRODUCT_NAME} uls:sync (+{PRODUCT_URL})",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as fh:  # noqa: S310
        shutil.copyfileobj(resp, fh, length=1 << 20)
    return dest


def _lines(zf: zipfile.ZipFile, name: str):
    """Yield the fields of each record of one member, streamed. Records are pipe-delimited and
    occasionally continue across a newline (a name with an embedded newline); a line that does
    not start with the record type is glued to the previous one."""
    member = next((n for n in zf.namelist() if n.upper() == name.upper()), None)
    if member is None:
        return
    rtype = name.split(".")[0].upper()
    buf = None
    with zf.open(member) as fh:
        for raw in fh:
            line = raw.decode("latin-1").rstrip("\r\n")
            if line.startswith(rtype + "|"):
                if buf is not None:
                    yield buf.split("|")
                buf = line
            elif buf is not None:
                buf += " " + line
        if buf is not None:
            yield buf.split("|")


def _flush_create(rows: list[UlsStaging]) -> None:
    if rows:
        UlsStaging.objects.bulk_create(rows, ignore_conflicts=True)
        rows.clear()


def _flush_update(rows: list[UlsStaging], fields: list[str]) -> None:
    if rows:
        UlsStaging.objects.bulk_update(rows, fields)
        rows.clear()


def stage(zip_path: Path) -> dict:
    """Load one archive into UlsStaging (emptied first). Returns counts."""
    UlsStaging.objects.all().delete()
    counts = {"hd": 0, "am": 0, "en": 0}
    with zipfile.ZipFile(zip_path) as zf:
        rows: list[UlsStaging] = []
        for f in _lines(zf, "HD.dat"):
            if len(f) < 9 or not f[4].strip():
                continue
            rows.append(
                UlsStaging(
                    usi=f[1].strip()[:12],
                    callsign=f[4].strip().upper()[:12],
                    status_code=f[5].strip()[:2],
                    grant_date=_date(f[7]),
                    expiry_date=_date(f[8]),
                )
            )
            counts["hd"] += 1
            if len(rows) >= BATCH:
                _flush_create(rows)
        _flush_create(rows)

        pending: list[UlsStaging] = []
        for f in _lines(zf, "AM.dat"):
            if len(f) < 6:
                continue
            pending.append(UlsStaging(usi=f[1].strip()[:12], class_code=f[5].strip()[:2]))
            counts["am"] += 1
            if len(pending) >= BATCH:
                _flush_update(pending, ["class_code"])
        _flush_update(pending, ["class_code"])

        for f in _lines(zf, "EN.dat"):
            if len(f) < 11 or f[5].strip() != "L":  # the licensee entity only
                continue
            pending.append(
                UlsStaging(
                    usi=f[1].strip()[:12],
                    entity_name=f[7].strip()[:160],
                    first_name=f[8].strip()[:80],
                    last_name=f[10].strip()[:80],
                    frn=(f[22].strip()[:20] if len(f) > 22 else ""),
                )
            )
            counts["en"] += 1
            if len(pending) >= BATCH:
                _flush_update(pending, ["entity_name", "first_name", "last_name", "frn"])
        _flush_update(pending, ["entity_name", "first_name", "last_name", "frn"])
    return counts


def _winner_rows():
    """One staging row per callsign: the active record, else the latest grant. Done in SQL so
    the Python side never holds the table."""
    table = UlsStaging._meta.db_table  # a model's table name, never user input
    sql = """
        SELECT s.usi FROM STAGING s
        WHERE s.usi = (
            SELECT s2.usi FROM STAGING s2 WHERE s2.callsign = s.callsign
            ORDER BY CASE WHEN s2.status_code = 'A' THEN 0 ELSE 1 END, s2.grant_date DESC, s2.usi DESC
            LIMIT 1
        )
    """.replace("STAGING", table)
    with connection.cursor() as cur:
        cur.execute(sql)
        while True:
            chunk = cur.fetchmany(BATCH)
            if not chunk:
                break
            yield [r[0] for r in chunk]


def apply_staging(now=None) -> dict:
    """Write the winners into UlsLicense. Returns counts and the callsigns touched."""
    now = now or timezone.now()
    written = 0
    touched: set[str] = set()
    for usis in _winner_rows():
        rows = UlsStaging.objects.filter(usi__in=usis)
        objs = []
        for s in rows:
            name = s.entity_name or " ".join(p for p in (s.first_name, s.last_name) if p)
            objs.append(
                UlsLicense(
                    callsign=s.callsign,
                    licensee_name=name[:160],
                    first_name=s.first_name,
                    last_name=s.last_name,
                    operator_class=CLASS.get(s.class_code, ""),
                    status=STATUS.get(s.status_code, s.status_code.lower() or "unknown"),
                    grant_date=s.grant_date,
                    expiry_date=s.expiry_date,
                    frn=s.frn,
                    updated=now,
                )
            )
            touched.add(s.callsign)
        with transaction.atomic():
            UlsLicense.objects.bulk_create(
                objs,
                update_conflicts=True,
                update_fields=[
                    "licensee_name",
                    "first_name",
                    "last_name",
                    "operator_class",
                    "status",
                    "grant_date",
                    "expiry_date",
                    "frn",
                    "updated",
                ],
                unique_fields=["callsign"],
            )
        written += len(objs)
    UlsStaging.objects.all().delete()
    return {"written": written, "touched": touched}


def refresh_members(callsigns: set[str] | None = None) -> int:
    """Refresh every member's LicenseRecord from the table (all, or only the callsigns touched)."""
    from .services import refresh_license_from_local_table

    qs = LicenseRecord.objects.select_related("user")
    if callsigns is not None:
        qs = qs.filter(callsign__in=callsigns)
    n = 0
    for lic in qs:
        refresh_license_from_local_table(lic.user)
        n += 1
    return n


def run(now=None, *, full: bool | None = None, file: str | None = None) -> dict:
    """The job body. `full` forces the weekly file; None chooses: full when the table is empty or
    the day after the FCC's Sunday build, daily otherwise. `file` imports a local archive instead
    of downloading (tests, rehearsals)."""
    now = now or timezone.now()
    workdir = Path(getattr(settings, "VAR_DIR", tempfile.gettempdir())) / "uls"
    if file:
        path, kind = Path(file), "file"
    else:
        if full is None:
            full = not UlsLicense.objects.exists() or now.weekday() == 0  # Monday: Sunday's file
        if full:
            path, kind = download(WEEKLY_URL, workdir / "l_amat.zip"), "weekly"
        else:
            day = (now - dt.timedelta(days=1)).strftime("%a").lower()
            path, kind = (
                download(DAILY_URL.format(day=day), workdir / f"l_am_{day}.zip"),
                f"daily:{day}",
            )
    counts = stage(path)
    applied = apply_staging(now)
    refreshed = refresh_members(None if kind == "weekly" else applied["touched"])
    if not file:
        try:
            path.unlink()
        except OSError:
            pass
    return {
        "source": kind,
        **counts,
        "written": applied["written"],
        "members_refreshed": refreshed,
        "table": UlsLicense.objects.count(),
    }
