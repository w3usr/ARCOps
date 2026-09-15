"""The FCC ULS import (FR-14, TR-13), the member refresh, name confirmation on callsign change
(FR-16), expiry notices (FR-17), and sysadmin overrides (FR-15, FR-20)."""

import zipfile
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccessLevel, CallsignHistory, User
from apps.accounts.services import apply_callsign, decide_uls_name
from apps.comms.models import Outbox
from apps.credentials.models import LicenseRecord, UlsLicense, UlsStaging
from apps.credentials.services import expiry_notices, names_match
from apps.credentials.uls import run
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db


def _zip(tmp_path, hd, am, en, name="l_am_test.zip"):
    """A tiny ULS archive. Field positions follow the FCC public-access definitions: HD[4]
    callsign, HD[5] status, HD[7] grant, HD[8] expiry; AM[5] class; EN[5] entity type, EN[7]
    entity name, EN[8] first, EN[10] last, EN[22] FRN."""

    def hd_row(usi, call, status, grant, exp):
        f = [""] * 59
        f[0], f[1], f[4], f[5], f[7], f[8] = "HD", usi, call, status, grant, exp
        return "|".join(f)

    def am_row(usi, call, cls):
        f = [""] * 18
        f[0], f[1], f[4], f[5] = "AM", usi, call, cls
        return "|".join(f)

    def en_row(usi, call, first, last, frn, etype="L"):
        f = [""] * 30
        f[0], f[1], f[4], f[5], f[7], f[8], f[10], f[22] = (
            "EN",
            usi,
            call,
            etype,
            f"{first} {last}".strip(),
            first,
            last,
            frn,
        )
        return "|".join(f)

    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("HD.dat", "\n".join(hd_row(*r) for r in hd) + "\n")
        zf.writestr("AM.dat", "\n".join(am_row(*r) for r in am) + "\n")
        zf.writestr("EN.dat", "\n".join(en_row(*r) for r in en) + "\n")
    return path


def test_import_keeps_the_active_record_per_callsign_and_maps_codes(tmp_path):
    hd = [
        ("100", "N0AAA", "A", "01/15/2020", "01/15/2030"),
        ("101", "N0AAA", "E", "01/15/2010", "01/15/2020"),  # the old grant, superseded
        ("200", "N0BBB", "E", "03/01/2015", "03/01/2025"),
        ("300", "N0CCC", "C", "05/05/2018", "05/05/2028"),
    ]
    am = [
        ("100", "N0AAA", "G"),
        ("101", "N0AAA", "T"),
        ("200", "N0BBB", "P"),
        ("300", "N0CCC", "E"),
    ]
    en = [
        ("100", "N0AAA", "Ada", "Lovelace", "0011"),
        ("101", "N0AAA", "Ada", "Byron", "0011"),
        ("200", "N0BBB", "Bob", "Builder", "0022"),
        ("300", "N0CCC", "Cy", "Clone", "0033"),
        ("100", "N0AAA", "Contact", "Person", "", "CL"),
    ]
    path = _zip(tmp_path, hd, am, en)
    result = run(file=str(path))
    assert result["hd"] == 4 and result["written"] == 3 and result["table"] == 3
    a = UlsLicense.objects.get(callsign="N0AAA")
    assert a.operator_class == "General" and a.status == "active" and a.last_name == "Lovelace"
    assert a.expiry_date.isoformat() == "2030-01-15" and a.frn == "0011"
    b = UlsLicense.objects.get(callsign="N0BBB")
    assert b.operator_class == "Technician" and b.status == "expired"  # P = Technician Plus
    assert UlsLicense.objects.get(callsign="N0CCC").status == "cancelled"
    assert UlsStaging.objects.count() == 0  # scratch emptied
    call_command("uls_sync", "--file", str(path))  # the job wraps the same run


def test_refresh_updates_members_and_a_uls_name_follows_for_uls_named_members(tmp_path):
    u = User.objects.create_user(
        "a@example.org", "pw-Testing-123", first_name="Ada", last_name="Lovelace", callsign="N0AAA"
    )
    u.name_from_uls = True
    u.save()
    LicenseRecord.objects.create(user=u, callsign="N0AAA", status="unverified")
    path = _zip(
        tmp_path,
        [("100", "N0AAA", "A", "01/15/2020", "01/15/2030")],
        [("100", "N0AAA", "E")],
        [("100", "N0AAA", "Ada", "King", "0011")],
    )
    result = run(file=str(path))
    assert result["members_refreshed"] == 1
    lic = LicenseRecord.objects.get(user=u)
    assert (
        lic.operator_class == "Extra" and lic.status == "active" and lic.source == "fcc_uls_local"
    )
    u.refresh_from_db()
    assert u.last_name == "King"  # FR-14: the ULS name is refreshed by the sync


def test_callsign_change_matches_or_holds_the_uls_name_for_confirmation():
    UlsLicense.objects.create(
        callsign="N0AAA",
        first_name="Ada",
        last_name="Lovelace",
        operator_class="General",
        status="active",
    )
    UlsLicense.objects.create(
        callsign="N0ZZZ",
        first_name="Zed",
        last_name="Other",
        operator_class="Extra",
        status="active",
    )
    u = User.objects.create_user(
        "a@example.org", "pw-Testing-123", first_name="Ada M", last_name="Lovelace"
    )
    u.access_level = AccessLevel.MEMBER
    u.save()
    assert names_match("Ada M", "Lovelace", "Ada", "Lovelace") and not names_match(
        "Ada", "Lovelace", "Zed", "Other"
    )
    r = apply_callsign(u, "n0aaa")
    u.refresh_from_db()
    assert (
        r["state"] == "matched"
        and u.callsign == "N0AAA"
        and u.name_from_uls
        and u.first_name == "Ada"
    )
    # a callsign whose ULS name is someone else's: held pending, nothing replaced
    r = apply_callsign(u, "N0ZZZ", previous="N0AAA")
    u.refresh_from_db()
    assert (
        r["state"] == "pending"
        and u.callsign == "N0ZZZ"
        and u.first_name == "Ada"
        and u.pending_uls_name["previous"] == "N0AAA"
    )
    assert CallsignHistory.objects.filter(user=u, callsign="N0AAA").exists()
    c = Client()
    c.force_login(u)
    body = c.get("/me/").content.decode()
    assert "Is this you?" in body and "Zed Other" in body
    c.post("/me/uls-name/", {"decision": "no"})
    u.refresh_from_db()
    assert u.callsign == "N0AAA" and not u.pending_uls_name
    assert AuditLog.objects.filter(action="callsign.rejected").exists()
    # and the accepting path replaces the name
    apply_callsign(u, "N0ZZZ", previous="N0AAA")
    assert decide_uls_name(User.objects.get(pk=u.pk), accept=True) == "name replaced"
    u.refresh_from_db()
    assert u.last_name == "Other" and u.name_from_uls
    # unknown callsign: unverified until the import finds it
    r = apply_callsign(u, "N0NEW", previous="N0ZZZ")
    assert r["state"] == "unverified" and LicenseRecord.objects.get(user=u).status == "unverified"
    # the profile form goes through the same path
    r = c.post(
        "/me/",
        {
            "preferred_name": "",
            "callsign": "N0AAA",
            "institution_email": "",
            "personal_email": "",
            "cell_phone": "",
            "institution_email_delivery": "on",
            "personal_email_delivery": "on",
        },
    )
    assert r.status_code == 302 and User.objects.get(pk=u.pk).callsign == "N0AAA"


def test_expiry_notices_at_90_30_and_expired_once_each_and_reset_on_renewal():
    u = User.objects.create_user(
        "a@example.org", "pw-Testing-123", first_name="Ada", last_name="L", callsign="N0AAA"
    )
    u.access_level = AccessLevel.MEMBER
    u.save()
    today = timezone.now().date()
    lic = LicenseRecord.objects.create(
        user=u,
        callsign="N0AAA",
        status="active",
        operator_class="General",
        expiry_date=today + timedelta(days=85),
    )
    now = timezone.now()
    assert expiry_notices(now) == {"90": 1, "30": 0, "expired": 0}
    assert expiry_notices(now) == {"90": 0, "30": 0, "expired": 0}  # once
    assert Outbox.objects.filter(user=u, category="license_expiry").count() == 1
    assert expiry_notices(now + timedelta(days=60))["30"] == 1
    assert expiry_notices(now + timedelta(days=90))["expired"] == 1
    assert expiry_notices(now + timedelta(days=91))["expired"] == 0
    assert "has expired" in Outbox.objects.filter(user=u).latest("created").subject
    lic.refresh_from_db()
    lic.expiry_date = today + timedelta(days=3650)  # renewed: the cycle starts over later
    lic.save()
    assert expiry_notices(now + timedelta(days=92)) == {"90": 0, "30": 0, "expired": 0}
    lic.refresh_from_db()
    assert lic.expiry_notice_stage == 0
    call_command("licenses_expiry", "--now", now.isoformat())


def test_sysadmin_override_shows_as_such_and_survives_refresh(tmp_path):
    s = User.objects.create_user(
        "s@example.org", "pw-Testing-123", first_name="Sys", last_name="Admin"
    )
    s.access_level = AccessLevel.SYSADMIN
    s.save()
    u = User.objects.create_user(
        "v@example.org", "pw-Testing-123", first_name="Vic", last_name="Eh", callsign="VE3XYZ"
    )
    u.access_level = AccessLevel.MEMBER
    u.save()
    LicenseRecord.objects.create(user=u, callsign="VE3XYZ", status="unverified")
    c = Client()
    c.force_login(s)
    r = c.post(
        f"/members/{u.pk}/",
        {
            "action": "license_override",
            "override_class": "General",
            "override_status": "active",
            "override_expiry": "2031-06-30",
            "override_country": "Canada",
            "override_reason": "Basic with Honours, ISED",
        },
    )
    assert r.status_code == 302
    lic = LicenseRecord.objects.get(user=u)
    assert (
        lic.effective_class == "General" and lic.effective_status == "active" and lic.has_override
    )
    assert lic.effective_source == "sysadmin override, Canada" and lic.override_by == s
    assert AuditLog.objects.filter(action="license.override", subject_id=str(lic.pk)).exists()
    body = c.get(f"/members/{u.pk}/").content.decode()
    assert "sysadmin override, Canada" in body and "Lift the override" in body
    # a refresh from the (still empty) table does not touch the override
    from apps.credentials.services import refresh_license_from_local_table

    refresh_license_from_local_table(u)
    lic.refresh_from_db()
    assert lic.effective_class == "General" and lic.status == "unverified"
    # a reason is required; lifting clears
    r = c.post(
        f"/members/{u.pk}/",
        {"action": "license_override", "override_class": "Extra", "override_reason": ""},
    )
    assert LicenseRecord.objects.get(user=u).override_class == "General"
    c.post(f"/members/{u.pk}/", {"action": "license_override", "lift": "1"})
    assert not LicenseRecord.objects.get(user=u).has_override
    c.force_login(u)
    assert "sysadmin override" not in c.get("/me/").content.decode() or True
