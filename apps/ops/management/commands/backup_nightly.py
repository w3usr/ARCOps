"""backup:nightly (TR-22): a consistent copy of the database and the media directory (the signed
agreements), tarred and encrypted with `age` to BACKUP_AGE_RECIPIENT, written to BACKUP_DIR as
`YYYYMMDD_HHMMUT_<BACKUP_NAME>.tar.age` (a gzipped tar) with a `sha256sum`-format sidecar. Nothing unencrypted
is written beside it: the tar streams straight into `age`. Both files appear under their final
names only when complete, so a pull never takes half an archive. Archives older than
BACKUP_KEEP_DAYS go; a machine elsewhere pulls them and keeps the long history."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tarfile
import tempfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection

from apps.ops.jobs import ScheduledCommand


class Command(ScheduledCommand):
    help = "Write tonight's encrypted backup and drop those past the retention (TR-22)."
    job_name = "backup:nightly"

    def run_job(self, now, **options):
        recipient = settings.BACKUP_AGE_RECIPIENT
        if not recipient:
            raise CommandError("BACKUP_AGE_RECIPIENT is not set, so no backup was written")
        out = Path(settings.BACKUP_DIR)
        suffix = f"_{settings.BACKUP_NAME}.tar.age"
        name = now.strftime("%Y%m%d_%H%MUT") + suffix
        part = out / f".{name}.part"  # not *.age: the puller neither checks nor keeps it as one
        try:
            with tempfile.TemporaryDirectory() as tmp:
                db = Path(tmp) / "ops.sqlite3"
                with connection.cursor() as c:  # one consistent copy, safe against a live server
                    c.execute("VACUUM INTO %s", [str(db)])
                with part.open("wb") as fh:
                    # No shell; the recipient is from the root-owned env file; `age` from PATH.
                    age = subprocess.Popen(  # noqa: S603
                        ["age", "--encrypt", "-r", recipient],  # noqa: S607
                        stdin=subprocess.PIPE,
                        stdout=fh,
                    )
                    with tarfile.open(fileobj=age.stdin, mode="w|gz") as tar:
                        tar.add(db, arcname="ops.sqlite3")
                        if Path(settings.MEDIA_ROOT).is_dir():
                            tar.add(settings.MEDIA_ROOT, arcname="media")
                    age.stdin.close()
                    if age.wait():
                        raise CommandError(f"age exited {age.returncode}")
            os.chmod(part, 0o640)  # the pull user reads it through the directory's group
            with part.open("rb") as fh:
                digest = hashlib.file_digest(fh, "sha256").hexdigest()
            os.replace(part, out / name)
        finally:
            part.unlink(missing_ok=True)
        sums = out / f".{name}.sha256.part"
        sums.write_text(f"{digest}  {name}\n")
        os.chmod(sums, 0o640)
        os.replace(sums, out / f"{name}.sha256")

        cutoff = (now - timedelta(days=settings.BACKUP_KEEP_DAYS)).strftime("%Y%m%d")
        removed = 0
        for f in out.iterdir():
            if (f.name.endswith(suffix) or f.name.endswith(suffix + ".sha256")) and f.name[
                :8
            ] < cutoff:
                f.unlink()
                removed += 1
        return {"file": name, "bytes": (out / name).stat().st_size, "removed": removed}
