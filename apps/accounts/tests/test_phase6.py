"""Phase 6: view-as (FR-94), closure (FR-11), deletion (FR-118), retention (TR-28)."""

import datetime as dt

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccessLevel, Invitation, User
from apps.accounts.services import DeletionRefused, delete_account
from apps.comms.models import Outbox
from apps.credentials.models import AgreementTemplate, CredentialType, SignedAgreement
from apps.events.models import Captaincy, Event, Location, OperatingPeriod, Position, SignUp
from apps.events.services.slots import generate_slots
from apps.ops.models import AuditLog
from apps.ops.retention import apply

pytestmark = pytest.mark.django_db


def _user(email, level=AccessLevel.MEMBER, **kw):
    kw.setdefault("first_name", email.split("@")[0].title())
    kw.setdefault("last_name", "Tester")
    return User.objects.create_user(email, "pw-Testing-123", access_level=level, **kw)


def _as(user):
    c = Client()
    c.force_login(user)
    return c


def _template():
    ct = CredentialType.objects.create(key="access", label="Access")
    return AgreementTemplate.objects.create(
        key="k",
        credential=ct,
        title="T",
        version=1,
        content_hash="x",
        html="<p>t</p>",
        effective_date=timezone.localdate(),
    )


def _slot(captain, days=5):
    ev = Event.objects.create(title="Test Contest", state="published")
    start = timezone.now() + dt.timedelta(days=days)
    OperatingPeriod.objects.create(event=ev, start=start, end=start + dt.timedelta(hours=1))
    pos = Position.objects.create(
        location=Location.objects.create(event=ev, name="Station"), name="Run"
    )
    Captaincy.objects.create(event=ev, user=captain)
    return generate_slots(ev, [pos], minutes=60)[0]


def test_sysadmin_views_as_member_read_only_and_audited():
    s = _user("sys@example.org", AccessLevel.SYSADMIN)
    m = _user("mem@example.org")
    c = _as(s)
    assert c.post(f"/members/{m.pk}/view-as/").status_code == 302
    r = c.get("/")
    assert r.status_code == 200
    assert r.context["user"] == m and r.context["impersonator"] == s
    assert b"Viewing as" in r.content
    # every state change is refused while viewing
    assert c.post("/me/", {"first_name": "X"}).status_code == 403
    assert m.refresh_from_db() is None and m.first_name == "Mem"
    r = c.post("/me/view-as/stop/")
    assert r.status_code == 302
    assert c.get("/").context["user"] == s
    actions = list(
        AuditLog.objects.filter(action__startswith="impersonation")
        .order_by("at", "pk")
        .values_list("action", flat=True)
    )
    assert actions == ["impersonation.started", "impersonation.stopped"]


def test_view_as_refused_for_sysadmins_and_for_members():
    s = _user("sys@example.org", AccessLevel.SYSADMIN)
    s2 = _user("sys2@example.org", AccessLevel.SYSADMIN)
    m = _user("mem@example.org")
    c = _as(s)
    c.post(f"/members/{s2.pk}/view-as/")
    assert c.get("/").context["user"] == s
    assert _as(m).post(f"/members/{s.pk}/view-as/").status_code == 404


def test_member_closes_own_account():
    _user("sys@example.org", AccessLevel.SYSADMIN)
    m = _user("mem@example.org")
    c = _as(m)
    assert c.post("/me/close/", {}).status_code == 302  # no confirmation: nothing happens
    m.refresh_from_db()
    assert m.access_level == AccessLevel.MEMBER
    c.post("/me/close/", {"confirm": "yes"})
    m.refresh_from_db()
    assert m.access_level == AccessLevel.NONE and m.closure_requested_at is not None
    assert Outbox.objects.filter(subject__contains="asked to close their account").count() == 1
    r = c.get("/")
    assert r.status_code == 302 and "/login" in r["Location"] or r.status_code == 200


def test_delete_account_anonymises_withdraws_and_keeps_shape():
    s = _user("sys@example.org", AccessLevel.SYSADMIN)
    cap = _user("cap@example.org", AccessLevel.OFFICER)
    m = _user("mem@example.org", callsign="AB1CDE", cell_phone="555")
    future = _slot(cap, days=5)
    past = _slot(cap, days=-5)
    SignUp.objects.create(slot=future, user=m, role="operator")
    SignUp.objects.create(slot=past, user=m, role="operator")
    tpl = _template()
    SignedAgreement.objects.create(
        user=m,
        template=tpl,
        credential=tpl.credential,
        signer_name="Mem Tester",
        expires_on=timezone.localdate() + dt.timedelta(days=100),
    )
    c = _as(s)
    r = c.get(f"/members/{m.pk}/")
    assert b"Delete this account" in r.content
    r = c.post(
        f"/members/{m.pk}/", {"action": "delete", "confirm": "yes", "reason": "asked in writing"}
    )
    assert r.status_code == 302
    m.refresh_from_db()
    assert (
        m.deleted_at is not None
        and m.full_name == "Deleted member"
        and m.callsign == ""
        and m.cell_phone == ""
    )
    assert not m.is_active and m.access_level == AccessLevel.NONE
    assert SignUp.objects.filter(slot=future, user=m).count() == 0  # future withdrawn
    assert SignUp.objects.filter(slot=past, user=m).count() == 1  # past kept for counts
    assert SignedAgreement.objects.filter(user=m).count() == 1  # kept for retention
    assert Outbox.objects.filter(user=cap).exists()  # captain told
    row = AuditLog.objects.get(action="account.deleted")
    assert row.before["callsign"] == "AB1CDE" and row.after["reason"] == "asked in writing"
    # the addresses go, and with them the sign-in library's copies: a deleted account answers to
    # no address, and nothing had to be invented to stand in for one
    from allauth.account.models import EmailAddress

    assert row.before["addresses"] == ["mem@example.org"]
    assert not m.addresses.exists() and not EmailAddress.objects.filter(user=m).exists()


def test_deletion_guards():
    s = _user("sys@example.org", AccessLevel.SYSADMIN)
    with pytest.raises(DeletionRefused):
        delete_account(s, s, "oops")  # last sysadmin


def test_retention_keeps_member_records_and_agreements_and_sweeps_only_the_rest():
    """The advisor, 2026-09-17: "I don't really like the automatic deletion. Instead, can we have
    a method to archive members?" So a former member's profile and their signed agreements are
    kept; what still ages out is what is not a member's record."""
    now = timezone.now()
    old = _user("old@example.org", AccessLevel.NONE, cell_phone="555")
    AuditLog.objects.create(
        action="access_level.changed", subject_type="User", subject_id=str(old.pk)
    )
    AuditLog.objects.filter(action="access_level.changed").update(at=now - dt.timedelta(days=800))
    Invitation.objects.create(
        email="x@example.org", category="student", expires_at=now - dt.timedelta(days=100)
    )
    tpl = _template()
    SignedAgreement.objects.create(
        user=old,
        template=tpl,
        credential=tpl.credential,
        signer_name="Old",
        expires_on=timezone.localdate() - dt.timedelta(days=4 * 365),
    )
    counts = apply(now)
    old.refresh_from_db()

    # kept, however long ago the account lost access
    assert old.cell_phone == "555" and old.addresses.exists()
    assert SignedAgreement.objects.filter(user=old).count() == 1
    assert "profiles_contact_removed" not in counts and "agreements_purged" not in counts

    # still swept: nothing here is a member's own record
    assert counts["invitations_deleted"] == 1
    assert AuditLog.objects.filter(action="retention.applied").exists()
