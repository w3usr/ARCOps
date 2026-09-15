"""Phase 4: shared password page and rotation (FR-32, FR-34, FR-90), agreement expiry notices and
summaries (FR-28), revocation (FR-29), re-sign policy on a new version (FR-30), the signed PDF
(FR-23), access rosters (FR-31, FR-84), participation (FR-86), and the member roster (FR-87)."""

import datetime as dt

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccessLevel, User
from apps.comms.models import Outbox
from apps.credentials.models import AgreementTemplate, CredentialType, SignedAgreement
from apps.credentials.services import agreement_expiry_run, approve
from apps.ops.models import AuditLog, ClubSetting

pytestmark = pytest.mark.django_db


def _user(email, level=AccessLevel.MEMBER, position="", **kw):
    u = User.objects.create_user(email, "pw-Testing-123", **kw)
    u.access_level = level
    u.club_position = position
    u.category = kw.get("category", "student")
    u.save()
    return u


def _setup():
    ClubSetting.objects.update_or_create(
        key="club_positions",
        defaults={"value": [{"key": "advisor", "label": "Advisor", "approver": True}]},
    )
    ClubSetting.objects.update_or_create(key="club.short_name", defaults={"value": "Test ARC"})
    st, _ = CredentialType.objects.get_or_create(
        key="station_access", defaults={"label": "Station access", "established_by": "agreement"}
    )
    it, _ = CredentialType.objects.get_or_create(
        key="it_access", defaults={"label": "Computer access", "established_by": "agreement"}
    )
    t_st = AgreementTemplate.objects.create(
        key="sa",
        credential=st,
        title="Station Agreement",
        audience=["student"],
        version=1,
        content_hash="h1",
        html="<h1>Station</h1><p>Rules.</p>",
        effective_date="2026-01-01",
        is_current=True,
    )
    t_it = AgreementTemplate.objects.create(
        key="it",
        credential=it,
        title="Computer Agreement",
        audience=["student"],
        version=1,
        content_hash="h2",
        html="<h1>Computer</h1><p>Rules.</p>",
        effective_date="2026-01-01",
        is_current=True,
    )
    return st, it, t_st, t_it


def _approved(user, template, expires):
    return SignedAgreement.objects.create(
        user=user,
        template=template,
        credential=template.credential,
        signer_name=user.full_name,
        content_hash=template.content_hash,
        state="approved",
        expires_on=expires,
        approved_at=timezone.now(),
    )


def test_expiry_notices_bundle_agreements_and_summarise_to_approvers():
    st, it, t_st, t_it = _setup()
    adv = _user(
        "adv@example.org", AccessLevel.OFFICER, "advisor", first_name="Ad", last_name="Visor"
    )
    mem = _user("mem@example.org", first_name="Mo", last_name="Member", callsign="N0MEM")
    today = timezone.now().date()
    _approved(mem, t_st, today + dt.timedelta(days=20))
    _approved(mem, t_it, today + dt.timedelta(days=20))
    r = agreement_expiry_run()
    assert r["notices_30"] == 1 and r["summaries"] == 1
    m = Outbox.objects.get(user=mem, category="agreement")
    assert (
        "expire" in m.subject
        and "Station Agreement" in m.body_html
        and "Computer Agreement" in m.body_html
    )
    s = Outbox.objects.get(user=adv, category="agreement")
    assert "1 member(s)" in s.subject and "Mo Member N0MEM" in s.body_html
    assert agreement_expiry_run()["notices_30"] == 0  # once
    # on the day: expired and told
    SignedAgreement.objects.filter(user=mem).update(expires_on=today - dt.timedelta(days=1))
    r = agreement_expiry_run()
    assert r["expired"] == 2 and r["notices_expiry"] == 1
    assert Outbox.objects.filter(user=mem, subject__contains="expired today").exists()
    call_command("agreements_expiry")


def test_resign_by_on_a_new_version_expires_old_approvals_and_the_page_says_so():
    st, it, t_st, t_it = _setup()
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    a = _approved(mem, t_st, timezone.now().date() + dt.timedelta(days=300))
    t_st.is_current = False
    t_st.save()
    v2 = AgreementTemplate.objects.create(
        key="sa",
        credential=st,
        title="Station Agreement",
        audience=["student"],
        version=2,
        content_hash="h1b",
        html="<h1>Station v2</h1>",
        effective_date="2026-09-01",
        is_current=True,
        resign_by=timezone.now().date() + dt.timedelta(days=10),
    )
    c = Client()
    c.force_login(mem)
    body = c.get("/credentials/agreements/").content.decode()
    assert (
        "You signed version 1; version 2 is current and must be re-signed by" in body
        and "Sign" in body
    )
    assert agreement_expiry_run()["superseded"] == 0
    v2.resign_by = timezone.now().date() - dt.timedelta(days=1)
    v2.save()
    assert agreement_expiry_run()["superseded"] == 1
    a.refresh_from_db()
    assert a.state == "expired" and "superseded by version 2" in a.decision_reason


def test_revoke_tells_the_member_and_access_rosters_filter_and_export():
    st, it, t_st, t_it = _setup()
    adv = _user(
        "adv@example.org", AccessLevel.OFFICER, "advisor", first_name="Ad", last_name="Visor"
    )
    mem = _user("mem@example.org", first_name="Mo", last_name="Member", callsign="N0MEM")
    today = timezone.now().date()
    a = _approved(mem, t_st, today + dt.timedelta(days=20))
    _approved(mem, t_it, today + dt.timedelta(days=200))
    c = Client()
    c.force_login(adv)
    body = c.get("/credentials/access-rosters/").content.decode()
    assert body.count("Mo Member") == 2 and "Revoke" in body
    body = c.get("/credentials/access-rosters/?expiring=30").content.decode()
    assert body.count("Mo Member") == 1
    csv_body = c.get("/credentials/access-rosters/?format=csv").content.decode()
    assert (
        "Station access" in csv_body
        and "Computer access" in csv_body
        and AuditLog.objects.filter(action="report.access_rosters_exported").exists()
    )
    r = c.post(
        f"/credentials/agreements/{a.pk}/revoke/",
        {"reason": "left the club", "next": "/credentials/access-rosters/"},
    )
    assert r.status_code == 302
    a.refresh_from_db()
    assert a.state == "revoked" and a.revoked_at
    m = Outbox.objects.get(user=mem, subject__startswith="Revoked")
    assert "left the club" in m.body_html
    c.force_login(mem)
    assert c.get("/credentials/access-rosters/").status_code == 404


def test_signed_pdf_is_rendered_stored_and_downloadable_by_signer_and_approver(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    st, it, t_st, t_it = _setup()
    adv = _user(
        "adv@example.org", AccessLevel.OFFICER, "advisor", first_name="Ad", last_name="Visor"
    )
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    other = _user("o@example.org", first_name="Ot", last_name="Her")
    c = Client()
    c.force_login(mem)
    c.post(f"/credentials/agreements/{t_st.pk}/sign/", {"affirm": "on", "signer_name": "Mo Member"})
    a = SignedAgreement.objects.get(user=mem)
    assert a.pdf and a.pdf.size > 1000
    r = c.get(f"/credentials/agreements/{a.pk}/pdf/")
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf"
    pdf = b"".join(r.streaming_content)
    assert pdf.startswith(b"%PDF") and len(pdf) > 1000  # tagging is asked of WeasyPrint (pdf/ua-1)
    approve(adv, a)
    a.refresh_from_db()
    assert a.pdf.size > 1000
    c.force_login(adv)
    assert c.get(f"/credentials/agreements/{a.pk}/pdf/").status_code == 200
    c.force_login(other)
    assert c.get(f"/credentials/agreements/{a.pk}/pdf/").status_code == 404
    body = Client()
    body.force_login(mem)
    assert "PDF of what you signed" in body.get("/credentials/agreements/").content.decode()


def test_password_manage_rotates_and_notifies_current_holders_and_lists_former_viewers(settings):
    from cryptography.fernet import Fernet

    settings.FIELD_ENCRYPTION_KEY = Fernet.generate_key().decode()
    st, it, t_st, t_it = _setup()
    sysadmin = _user("s@example.org", AccessLevel.SYSADMIN, first_name="Sys", last_name="Admin")
    holder = _user("h@example.org", first_name="Ho", last_name="Lder")
    former = _user("f@example.org", first_name="For", last_name="Mer")
    today = timezone.now().date()
    _approved(holder, t_it, today + dt.timedelta(days=200))
    AuditLog.objects.create(actor=former, actor_label=str(former), action="shared_secret.viewed")
    c = Client()
    c.force_login(holder)
    assert c.get("/credentials/computer-password/manage/").status_code == 404
    c.force_login(sysadmin)
    r = c.post(
        "/credentials/computer-password/manage/",
        {
            "password": "c0rrect-horse",
            "password2": "c0rrect-horse",
            "effective_date": today.isoformat(),
        },
    )
    assert r.status_code == 302
    assert Outbox.objects.filter(
        user=holder, category="security", subject__contains="password has changed"
    ).exists()
    summary = Outbox.objects.get(user=sysadmin, category="security")
    assert "1 told, 1 former holder" in summary.subject and "For Mer" in summary.body_html
    assert not Outbox.objects.filter(user=former).exists()
    c.force_login(holder)
    r = c.post("/credentials/computer-password/", {"password": "pw-Testing-123"})
    assert b"c0rrect-horse" in r.content


def test_member_roster_filters_graduated_and_audits_contact_export():
    _setup()
    off = _user("off@example.org", AccessLevel.OFFICER, first_name="An", last_name="Officer")
    grad = _user("g@example.org", first_name="Gra", last_name="Duate")
    grad.graduation_semester, grad.graduation_year, grad.student_level = (
        "spring",
        2024,
        "undergraduate",
    )
    grad.save()
    cur = _user("c@example.org", first_name="Cur", last_name="Rent")
    cur.graduation_semester, cur.graduation_year = "spring", 2030
    cur.save()
    c = Client()
    c.force_login(off)
    body = c.get("/members/roster/").content.decode()
    assert "Gra Duate" in body and "Cur Rent" in body and "past graduation" in body
    body = c.get("/members/roster/?graduated=1").content.decode()
    assert "Gra Duate" in body and "Cur Rent" not in body
    plain = c.get("/members/roster/?format=csv").content.decode()
    assert "g@example.org" not in plain
    contacts = c.get("/members/roster/?format=csv&contacts=1").content.decode()
    assert "g@example.org" in contacts
    rows = AuditLog.objects.filter(action="report.member_roster_exported").order_by("at")
    assert rows.count() == 2 and rows.last().after["contacts"] is True
    c.force_login(cur)
    assert c.get("/members/roster/").status_code == 404
