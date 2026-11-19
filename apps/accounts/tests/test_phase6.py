"""Phase 6: view-as (FR-94), closure (FR-11), deletion (FR-118), retention (TR-28)."""

import datetime as dt
from unittest import mock

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Invitation, User
from apps.accounts.services import DeletionRefused, delete_account
from apps.comms.models import Outbox
from apps.credentials.models import AgreementTemplate, CredentialType, SignedAgreement
from apps.events.models import Captaincy, Event, Location, Position, SignUp
from apps.events.services.slots import generate_slots
from apps.ops.models import AuditLog
from apps.ops.retention import apply

pytestmark = pytest.mark.django_db


def _user(email, level="member", **kw):
    kw.setdefault("first_name", email.split("@")[0].title())
    kw.setdefault("last_name", "Tester")
    return User.objects.create_user(
        email,
        "pw-Testing-123",
        groups=[] if level == "sysadmin" else [level],
        is_superuser=level == "sysadmin",
        **kw,
    )


def _as(user, view="sysadmin"):
    c = Client()
    c.force_login(user)
    if user.is_superuser:
        session = c.session  # the level a sysadmin's session acts at
        session["acting_view"] = view
        session.save()
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
    ev.start, ev.end = start, start + dt.timedelta(hours=1)
    ev.save(update_fields=["start", "end"])
    pos = Position.objects.create(
        location=Location.objects.create(event=ev, name="Station"), name="Run"
    )
    Captaincy.objects.create(event=ev, user=captain)
    return generate_slots(ev, [pos], minutes=60)[0]


def test_sysadmin_views_as_member_read_only_and_audited():
    s = _user("sys@example.org", "sysadmin")
    m = _user("mem@example.org")
    c = _as(s)
    assert c.post(f"/members/{m.pk}/view-as/").status_code == 302
    r = c.get("/")
    assert r.status_code == 200
    assert r.context["user"] == m and r.context["impersonator"] == s
    assert b"Viewing as" in r.content
    # every state change is refused while viewing
    assert c.post("/me/edit/", {"first_name": "X"}).status_code == 403
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


def test_viewing_as_a_member_reads_none_of_their_messages():
    """T43, 2026-10-21: opening Messages while viewing as a member marked theirs read, though
    the banner says nothing can be changed. Only the member's own visit does."""
    s = _user("sys@example.org", "sysadmin")
    m = _user("mem@example.org")
    msg = Outbox.objects.create(user=m, category="account", subject="Hello", body_html="<p>hi</p>")
    c = _as(s)
    c.post(f"/members/{m.pk}/view-as/")
    assert c.get("/me/messages/").status_code == 200
    assert Outbox.objects.get(pk=msg.pk).read_at is None
    _as(m).get("/me/messages/")
    assert Outbox.objects.get(pk=msg.pk).read_at is not None


def test_view_as_refused_for_sysadmins_and_for_members():
    s = _user("sys@example.org", "sysadmin")
    s2 = _user("sys2@example.org", "sysadmin")
    m = _user("mem@example.org")
    c = _as(s)
    c.post(f"/members/{s2.pk}/view-as/")
    assert c.get("/").context["user"] == s
    assert _as(m).post(f"/members/{s.pk}/view-as/").status_code == 404


def test_member_closes_own_account():
    _user("sys@example.org", "sysadmin")
    m = _user("mem@example.org")
    c = _as(m)
    assert c.post("/me/close/", {}).status_code == 302  # no confirmation: nothing happens
    m.refresh_from_db()
    assert m.in_group("member")
    c.post("/me/close/", {"confirm": "yes"})
    m.refresh_from_db()
    assert not m.has_access and m.closure_requested_at is not None
    assert Outbox.objects.filter(subject__contains="asked to close their account").count() == 1
    r = c.get("/")
    assert r.status_code == 302 and "/login" in r["Location"] or r.status_code == 200


def test_delete_account_anonymises_withdraws_and_keeps_shape():
    s = _user("sys@example.org", "sysadmin")
    cap = _user("cap@example.org", "officer")
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
    r = c.get(f"/members/{m.pk}/edit/")
    assert b"Delete this account" in r.content
    r = c.post(
        f"/members/{m.pk}/edit/",
        {"action": "delete", "confirm": "yes", "reason": "asked in writing"},
    )
    assert r.status_code == 302
    m.refresh_from_db()
    assert (
        m.deleted_at is not None
        and m.full_name == "Deleted member"
        and m.callsign == ""
        and m.cell_phone == ""
    )
    assert not m.is_active and not m.has_access
    assert SignUp.objects.filter(slot=future, user=m).count() == 0  # future withdrawn
    assert SignUp.objects.filter(slot=past, user=m).count() == 1  # past kept for counts
    assert SignedAgreement.objects.filter(user=m).count() == 1  # kept for retention
    assert Outbox.objects.filter(user=cap).exists()  # captain told
    row = AuditLog.objects.get(action="account.deleted")
    assert row.after["reason"] == "asked in writing"
    # The deletion's record counts what went rather than copying it (SK, 2026-11-19, private
    # tracker 329): no name, callsign or address in it.
    assert row.before == {"addresses": 1, "callsign": True}
    # the addresses go, and with them the sign-in library's copies: a deleted account answers to
    # no address, and nothing had to be invented to stand in for one
    from allauth.account.models import EmailAddress

    assert not m.addresses.exists() and not EmailAddress.objects.filter(user=m).exists()


def test_deletion_blanks_responsible_adult_rows_drops_authenticators_and_counts_true():
    """FR-118, private tracker 329: a responsible-adult row naming the deleted member keeps its
    place but not their details; their authenticators go; the confirmation's count of future
    sign-ups leaves out one kept for attendance, as the withdrawal does."""
    from allauth.mfa.models import Authenticator

    from apps.accounts.services import deletion_effects
    from apps.events.models import ResponsibleAdult

    s = _user("sys@example.org", "sysadmin")
    cap = _user("cap@example.org", "officer")
    m = _user("mem@example.org", cell_phone="555")
    minor = _user("minor@example.org")
    later, running = _slot(cap, days=5), _slot(cap, days=0)
    SignUp.objects.create(slot=later, user=m, role="operator")
    SignUp.objects.create(slot=running, user=m, role="operator", checked_in_at=timezone.now())
    ra = ResponsibleAdult.objects.create(
        signup=SignUp.objects.create(slot=later, user=minor, role="operator"),
        name=m.full_name,
        email="mem@example.org",
        phone="555",
        member=m,
    )
    Authenticator.objects.create(user=m, type=Authenticator.Type.TOTP, data={"secret": "x"})

    promised = deletion_effects(m)["future_signups"]
    done = delete_account(s, m, "asked in writing")
    assert promised == done["withdrawn"] == 1  # the checked-in one stays, and was never promised
    ra.refresh_from_db()
    assert (ra.name, ra.email, ra.phone, ra.member) == ("Deleted member", "", "", None)
    assert not Authenticator.objects.filter(user=m).exists()


def test_deletion_blanks_mail_to_them_invitations_and_notes_but_not_mail_to_others():
    """SK, 2026-11-19, private tracker 329 (A39): mail to them keeps its date, kind and subject
    but not where it went or what it said; mail about them to someone else stays; invitations to
    their address keep who invited and when; their notes on sign-ups that stay are cleared."""
    s = _user("sys@example.org", "sysadmin")
    cap = _user("cap@example.org", "officer")
    m = _user("mem@example.org")
    past = _slot(cap, days=-5)
    kept = SignUp.objects.create(slot=past, user=m, role="operator", note="Mem, AB1CDE, room 12")
    to_them = Outbox.objects.create(
        user=m,
        to_addresses=["mem@example.org"],
        category="account",
        subject="Welcome",
        body_html="<p>Hello Mem</p>",
        body_text="Hello Mem",
    )
    to_cap = Outbox.objects.create(
        user=cap,
        to_addresses=["cap@example.org"],
        category="moved",
        subject="Mem canceled",
        body_html="<p>Mem canceled</p>",
    )
    inv = Invitation.objects.create(
        email="MEM@example.org",
        category="student",
        issued_by=s,
        accepted_by=m,
        expires_at=timezone.now() + dt.timedelta(days=7),
    )

    delete_account(s, m, "asked in writing")
    to_them.refresh_from_db()
    to_cap.refresh_from_db()
    inv.refresh_from_db()
    kept.refresh_from_db()
    assert (to_them.to_addresses, to_them.body_html, to_them.body_text) == ([], "", "")
    assert to_them.subject == "Welcome" and to_them.category == "account"
    assert to_cap.body_html == "<p>Mem canceled</p>"  # the captain's mail is the captain's
    assert inv.email == "" and inv.issued_by == s
    assert (kept.note, kept.note_at) == ("", None)


def test_deletion_guards():
    s = _user("sys@example.org", "sysadmin")
    with pytest.raises(DeletionRefused):
        delete_account(s, s, "oops")  # last sysadmin


def test_retention_keeps_member_records_and_agreements_and_sweeps_only_the_rest():
    """The advisor, 2026-09-17: "I don't really like the automatic deletion. Instead, can we have
    a method to archive members?" So a former member's profile and their signed agreements are
    kept; what still ages out is what is not a member's record."""
    now = timezone.now()
    old = _user("old@example.org", "none", cell_phone="555")
    # written 800 days ago: the log refuses an UPDATE (TR-21), so the clock is moved instead
    with mock.patch("django.utils.timezone.now", return_value=now - dt.timedelta(days=800)):
        AuditLog.objects.create(
            action="access.changed", subject_type="User", subject_id=str(old.pk)
        )
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
