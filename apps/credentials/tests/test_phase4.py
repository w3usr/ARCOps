"""Phase 4: shared password page and rotation (FR-32, FR-34, FR-90), agreement expiry notices and
summaries (FR-28), revocation (FR-29), re-sign policy on a new version (FR-30), the signed PDF
(FR-23), access rosters (FR-31, FR-84), participation (FR-86), and the member roster (FR-87)."""

import datetime as dt

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.comms.models import Outbox
from apps.credentials.models import AgreementTemplate, CredentialType, SignedAgreement
from apps.credentials.services import agreement_expiry_run, approve
from apps.ops.models import AuditLog, ClubSetting

pytestmark = pytest.mark.django_db


def _user(email, level="member", position="", **kw):
    u = User.objects.create_user(email, "pw-Testing-123", **kw)
    if level == "sysadmin":  # a sysadmin is a superuser, not a member of a group
        u.is_superuser = True
    else:
        u.groups.set(Group.objects.filter(name=level))
    u.club_position = position
    u.category = kw.get("category", "student")
    u.save()
    return u


def _setup():
    ClubSetting.objects.update_or_create(
        key="club_positions",
        defaults={"value": [{"key": "advisor", "label": "Advisor"}]},
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


def _confirmed(client, password="pw-Testing-123"):
    """Go through Confirm Access, as a person does: the page that shows the shared password
    asks for it every time, and is satisfied by a password or a passkey (§2.6)."""
    client.post("/accounts/reauthenticate/", {"password": password})
    return client


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
    adv = _user("adv@example.org", "advisor", "advisor", first_name="Ad", last_name="Visor")
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
    if mem.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    body = c.get("/credentials/agreements/").content.decode()
    assert (
        "you signed version 1; version 2 is current and must be re-signed by" in body
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
    adv = _user("adv@example.org", "advisor", "advisor", first_name="Ad", last_name="Visor")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member", callsign="N0MEM")
    today = timezone.now().date()
    a = _approved(mem, t_st, today + dt.timedelta(days=20))
    _approved(mem, t_it, today + dt.timedelta(days=200))
    c = Client()
    c.force_login(adv)
    if adv.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    body = c.get("/credentials/access-rosters/").content.decode()
    # First, Last and Callsign are columns of their own now (issue #92, 2026-09-20).
    assert body.count(">Member</a>") == 2 and body.count(">N0MEM<") == 2
    assert "Revoke" in body
    # The credential opens what they signed, for somebody who may read it.
    assert f"/credentials/agreements/{a.pk}/pdf/" in body

    body = c.get("/credentials/access-rosters/?expiring=30").content.decode()
    assert body.count(">N0MEM<") == 1, "the expiry bucket narrows it"

    # Contact details are on the roster, and the Status panel opens on Active (issue #92).
    body = c.get("/credentials/access-rosters/").content.decode()
    assert "Institution email" in body and "Personal email" in body and "Phone" in body
    assert "Days</a>" not in body, "the Days column is gone"
    assert "mem@example.org" in body
    lapsed = _approved(mem, t_st, today - dt.timedelta(days=5))
    lapsed.state = "expired"
    lapsed.save(update_fields=["state"])
    body = c.get("/credentials/access-rosters/").content.decode()
    assert "Expired" not in body.split("<tbody>")[1], "Active only, until asked otherwise"
    body = c.get("/credentials/access-rosters/?status=expired").content.decode()
    assert "Expired" in body.split("<tbody>")[1]
    body = c.get("/credentials/access-rosters/?status=active&status=expired").content.decode()
    assert "Expired" in body and body.count(">N0MEM<") == 3
    body = c.get("/credentials/access-rosters/?credential=it_access").content.decode()
    assert body.count(">N0MEM<") == 1 and "Computer access" in body
    body = c.get("/credentials/access-rosters/?q=N0MEM").content.decode()
    assert body.count(">N0MEM<") == 2
    body = c.get("/credentials/access-rosters/?q=nobody-by-that-name").content.decode()
    assert ">N0MEM<" not in body and "Show everyone who holds access" in body

    # Every column sorts, and the link back carries the narrowing with it.
    body = c.get("/credentials/access-rosters/?credential=it_access&sort=callsign").content.decode()
    assert "credential=it_access" in body and "sort=first" in body
    first = c.get("/credentials/access-rosters/?sort=expires&dir=asc").content.decode()
    last = c.get("/credentials/access-rosters/?sort=expires&dir=desc").content.decode()
    assert first != last, "reversing a column reverses the page"

    csv_body = c.get("/credentials/access-rosters/?format=csv").content.decode()
    assert (
        "Station access" in csv_body
        and "Computer access" in csv_body
        and AuditLog.objects.filter(action="report.access_rosters_exported").exists()
    )
    # The download is what is on the screen: it follows the filters (issue #92).
    narrowed = c.get(
        "/credentials/access-rosters/?credential=it_access&format=csv"
    ).content.decode()
    assert "Computer access" in narrowed and "Station access" not in narrowed
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
    if mem.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    assert c.get("/credentials/access-rosters/").status_code == 404


def test_signed_pdf_is_rendered_stored_and_downloadable_by_signer_and_approver(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    st, it, t_st, t_it = _setup()
    adv = _user("adv@example.org", "advisor", "advisor", first_name="Ad", last_name="Visor")
    mem = _user("mem@example.org", first_name="Mo", last_name="Member")
    other = _user("o@example.org", first_name="Ot", last_name="Her")
    c = Client()
    c.force_login(mem)
    if mem.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
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
    if adv.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    assert c.get(f"/credentials/agreements/{a.pk}/pdf/").status_code == 200
    c.force_login(other)
    if other.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    assert c.get(f"/credentials/agreements/{a.pk}/pdf/").status_code == 404
    body = Client()
    body.force_login(mem)
    if mem.is_superuser:
        session = body.session  # acting at the raised level
        session["acting_view"] = "sysadmin"
        session.save()
    assert "Open what you signed" in body.get("/credentials/agreements/").content.decode()


def test_password_manage_rotates_and_notifies_current_holders_and_lists_former_viewers(settings):
    from cryptography.fernet import Fernet

    settings.FIELD_ENCRYPTION_KEY = Fernet.generate_key().decode()
    st, it, t_st, t_it = _setup()
    sysadmin = _user("s@example.org", "sysadmin", first_name="Sys", last_name="Admin")
    holder = _user("h@example.org", first_name="Ho", last_name="Lder")
    former = _user("f@example.org", first_name="For", last_name="Mer")
    today = timezone.now().date()
    _approved(holder, t_it, today + dt.timedelta(days=200))
    AuditLog.objects.create(actor=former, actor_label=str(former), action="shared_secret.viewed")
    c = Client()
    c.force_login(holder)
    if holder.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    assert c.get("/credentials/computer-password/manage/").status_code == 404
    c.force_login(sysadmin)
    if sysadmin.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
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
    if holder.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    # Confirm Access guards it, and the proof is spent on one view of it.
    assert c.get("/credentials/computer-password/")["Location"].startswith(
        "/accounts/reauthenticate/"
    )
    r = _confirmed(c).get("/credentials/computer-password/")
    assert b"c0rrect-horse" in r.content
    assert c.get("/credentials/computer-password/")["Location"].startswith(
        "/accounts/reauthenticate/"
    ), "a reload asks again"


def test_member_roster_filters_graduated_and_audits_contact_export():
    _setup()
    off = _user("off@example.org", "officer", first_name="An", last_name="Officer")
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
    if off.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
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
    if cur.is_superuser:
        session = c.session  # a sysadmin signs in acting lower
        session["acting_view"] = "sysadmin"
        session.save()
    assert c.get("/members/roster/").status_code == 404


def test_the_advisor_reaches_the_computer_password_from_the_sidebar(settings):
    """FR-32: the page that sets the station password had no way in but a typed address.

    > There needs to be a UI entry point for the faculty advisor and above to rotate this.
    > — NAF, 2026-09-20

    The advisor answers to the University for station access, so the password is theirs, and
    Advisor tools is where it belongs: an officer holds neither the link nor the page.
    """
    from cryptography.fernet import Fernet

    settings.FIELD_ENCRYPTION_KEY = Fernet.generate_key().decode()
    call_command("club_import")
    advisor = _user("adv@example.org", "advisor", category="faculty")
    officer = _user("off2@example.org", "officer")

    c = Client()
    c.force_login(advisor)
    home = c.get("/").content.decode()
    # "Set the computer password" is the advisor's entry; a member's own entry, for reading it,
    # says "Computer password" and is a different page (2026-09-20).
    assert "Set the computer password" in home
    assert "/credentials/computer-password/manage/" in home
    assert c.get("/credentials/computer-password/manage/").status_code == 200

    c.force_login(officer)
    home = c.get("/").content.decode()
    assert "Set the computer password" not in home
    assert "/credentials/computer-password/manage/" not in home
    assert c.get("/credentials/computer-password/manage/").status_code == 404


def test_the_approvals_page_carries_the_pdf_the_badge_and_a_way_back_from_a_decline():
    """Four things the advisor asked for on 2026-09-20, walking the page with one signature on it.

    > Can the Approvals navigation item also get a badge indicating the number of things that
    > need approval? … I want the Approve and Decline buttons on the same line. There should
    > also be a link to download the signed PDF. … we need some way to approve after an
    > accidental decline.
    """
    call_command("club_import")
    st, it, t_st, t_it = _setup()
    advisor = _user("adv3@example.org", "advisor", category="faculty")
    member = _user("mem3@example.org")
    signed = SignedAgreement.objects.create(
        user=member,
        template=t_st,
        credential=st,
        signer_name="Mem Ber",
        state=SignedAgreement.State.SIGNED,
    )

    c = Client()
    c.force_login(advisor)
    page = c.get("/credentials/approvals/").content.decode()
    assert f"/credentials/agreements/{signed.pk}/pdf/" in page  # what they signed, to read
    assert "decide-row" in page  # Approve and Decline on one row
    assert "1 waiting for approval" in page  # the sidebar badge, on every page

    # An accidental decline is not the member's to undo by signing again.
    c.post(
        f"/credentials/approvals/{signed.pk}/decide/",
        {"decision": "decline", "reason": "wrong button"},
    )
    signed.refresh_from_db()
    assert signed.state == SignedAgreement.State.DECLINED
    page = c.get("/credentials/approvals/").content.decode()
    assert "Approve after all" in page and "wrong button" in page
    assert "1 waiting for approval" not in page  # the badge counts what is waiting, not this

    # A reversal says why: without a reason it is refused and nothing changes.
    c.post(f"/credentials/approvals/{signed.pk}/decide/", {"decision": "approve"})
    signed.refresh_from_db()
    assert signed.state == SignedAgreement.State.DECLINED
    c.post(
        f"/credentials/approvals/{signed.pk}/decide/",
        {"decision": "approve", "reversal_reason": "mis-click; the signature was in order"},
    )
    signed.refresh_from_db()
    assert signed.state == SignedAgreement.State.APPROVED
    assert signed.decision_reason == ""  # the reason it was declined for no longer describes it
    assert signed.expires_on and signed.approver == advisor

    # Declining something already declined says so rather than recording it twice.
    other = SignedAgreement.objects.create(
        user=member,
        template=t_it,
        credential=it,
        signer_name="Mem Ber",
        state=SignedAgreement.State.DECLINED,
    )
    c.post(f"/credentials/approvals/{other.pk}/decide/", {"decision": "decline", "reason": "no"})
    other.refresh_from_db()
    assert other.state == SignedAgreement.State.DECLINED and other.decision_reason == ""


def test_the_badge_and_the_declined_list_are_only_for_somebody_who_may_approve():
    call_command("club_import")
    st, _it, t_st, _t_it = _setup()
    officer = _user("off3@example.org", "officer")
    member = _user("mem4@example.org")
    SignedAgreement.objects.create(
        user=member,
        template=t_st,
        credential=st,
        signer_name="Mem Ber",
        state=SignedAgreement.State.SIGNED,
    )
    c = Client()
    c.force_login(officer)
    home = c.get("/").content.decode()
    assert "waiting for approval" not in home
    assert c.get("/credentials/approvals/").status_code == 404


def test_a_member_who_holds_computer_access_is_shown_the_way_to_the_password(settings):
    """FR-33: the page had no entry of its own and was reached from the rotation notice alone.

    > what is the UI route for a person who has been granted access to view the station password
    > for viewing the station password? I want that to be straightforward and simple.
    > — NAF, 2026-09-20
    """
    from cryptography.fernet import Fernet

    settings.FIELD_ENCRYPTION_KEY = Fernet.generate_key().decode()
    call_command("club_import")
    st, it, _t_st, t_it = _setup()
    holder = _user("holder@example.org")
    plain = _user("plain@example.org")
    _approved(holder, t_it, timezone.now().date() + dt.timedelta(days=200))

    c = Client()
    c.force_login(holder)
    home = c.get("/").content.decode()
    assert "/credentials/computer-password/" in home and "Computer password" in home
    # and again where the credential was granted
    agreements = c.get("/credentials/agreements/").content.decode()
    assert "See the computer password" in agreements
    assert c.get("/credentials/computer-password/")["Location"].startswith(
        "/accounts/reauthenticate/"
    )

    # Somebody without the credential is offered neither, and the page still refuses them.
    c.force_login(plain)
    home = c.get("/").content.decode()
    assert "/credentials/computer-password/" not in home
    assert "See the computer password" not in c.get("/credentials/agreements/").content.decode()
    assert c.get("/credentials/computer-password/").status_code == 403


def test_the_decision_log_keeps_every_act_and_sorts_narrows_and_exports():
    """FR-25: what has been decided, on the page of the person who decides it.

    > I think we need a searchable, filterable, sortable log on this page of what approval
    > actions have been taken. — NAF, 2026-09-20

    The agreement row carries only the latest decision, so the pair that matters most — a
    decline and the approval that corrected it — would otherwise read as one approval.
    """
    from apps.credentials.models import CredentialDecision
    from apps.credentials.services import agreement_expiry_run, revoke

    call_command("club_import")
    st, it, t_st, t_it = _setup()
    advisor = _user("adv4@example.org", "advisor", category="faculty")
    member = _user("mem5@example.org", first_name="Dee", last_name="Cided", callsign="N0DEC")
    signed = SignedAgreement.objects.create(
        user=member, template=t_st, credential=st, signer_name="Dee Cided"
    )
    c = Client()
    c.force_login(advisor)

    # The queue is a list rather than a card each, and declining opens its reason in place.
    waiting = c.get("/credentials/approvals/").content.decode()
    assert "Decline and tell them" in waiting and "Approve" in waiting
    assert f"/credentials/agreements/{signed.pk}/pdf/" in waiting, "read what they signed"

    c.post(f"/credentials/approvals/{signed.pk}/decide/", {"decision": "decline", "reason": "typo"})
    c.post(
        f"/credentials/approvals/{signed.pk}/decide/",
        {"decision": "approve", "reversal_reason": "mis-click"},
    )
    actions = list(CredentialDecision.objects.order_by("pk").values_list("action", flat=True))
    assert actions == ["declined", "approved_after_decline"], "both, in the order they happened"

    body = c.get("/credentials/approvals/").content.decode()
    assert "Decisions taken" in body
    assert "Approved after a decline" in body and "Declined" in body and "typo" in body
    # The stored key never reaches the reader; only the words do (TR-44). It is allowed in a
    # filter checkbox's value, which is a form value rather than something anybody reads.
    body_rows = body.split("<tbody>")[-1].split("</tbody>")[0]
    assert "approved_after_decline" not in body_rows

    # Revoking and expiring are decisions too, and each is named rather than counted.
    revoke(advisor, signed, "left the club")
    other = _approved(member, t_it, timezone.now().date() - dt.timedelta(days=1))
    agreement_expiry_run()
    assert CredentialDecision.objects.filter(action="revoked").count() == 1
    assert CredentialDecision.objects.filter(action="expired", agreement=other).count() == 1

    # Narrowing, sorting and the download, on the shared helpers.
    body = c.get("/credentials/approvals/?action=revoked").content.decode()
    log = body.split("Decisions taken")[1]
    assert "left the club" in log and "typo" not in log
    assert "Show them all" not in log

    body = c.get("/credentials/approvals/?q=N0DEC").content.decode()
    assert "N0DEC" in body.split("Decisions taken")[1]
    body = c.get("/credentials/approvals/?q=nobody").content.decode()
    assert "Show them all" in body.split("Decisions taken")[1]

    body = c.get("/credentials/approvals/?action=revoked&sort=member").content.decode()
    assert "action=revoked" in body, "a heading keeps the narrowing"

    csv_body = c.get(
        "/credentials/approvals/?format=csv&report=decisions&action=revoked"
    ).content.decode()
    assert "left the club" in csv_body and "typo" not in csv_body
    assert AuditLog.objects.filter(action="report.decisions_exported").exists()


def test_the_decision_log_is_only_for_somebody_who_may_approve():
    call_command("club_import")
    _setup()
    officer = _user("off4@example.org", "officer")
    c = Client()
    c.force_login(officer)
    assert c.get("/credentials/approvals/").status_code == 404
    assert c.get("/credentials/approvals/?format=csv&report=decisions").status_code == 404


def test_station_and_computer_access_need_an_institution_address_from_anyone():
    """FR-27, widened 2026-09-20.

    The advisor, 2026-09-20, having approved station access for somebody with no institution
    address and finding that he could: require one first, for the computer agreement as well,
    so everybody granted real access is at least in the institution's own directory.

    It was asked of a community member's station access alone, so a student or a faculty member
    holding only a personal address was approved without one, and so was anybody at all for
    computer access.
    """
    from apps.accounts import addresses
    from apps.ops.models import ClubSetting

    call_command("club_import")
    ClubSetting.objects.update_or_create(
        key="trusted_email_domains", defaults={"value": ["example.edu"]}
    )
    st, it, t_st, t_it = _setup()
    advisor = _user("adv5@example.org", "advisor", category="faculty")
    c = Client()
    c.force_login(advisor)

    # One member per credential: granting one puts an institution address on the account, and
    # the second credential then has no reason to ask again, which is the point of asking.
    for n, template in enumerate((t_st, t_it)):
        # A student, not a community member, and holding only a personal address.
        member = _user(f"nobadge{n}@example.org", first_name="No", last_name=f"Badge{n}")
        addresses.add(member, f"nobadge{n}@example.org", kind="personal", confirmed=True)
        signed = SignedAgreement.objects.create(
            user=member, template=template, credential=template.credential, signer_name="No Badge"
        )
        body = c.get("/credentials/approvals/").content.decode()
        assert "Institution email" in body, template.credential.key

        r = c.post(f"/credentials/approvals/{signed.pk}/decide/", {"decision": "approve"})
        signed.refresh_from_db()
        assert signed.state == SignedAgreement.State.SIGNED, "refused without one"
        assert "institution email address" in c.get(r["Location"]).content.decode()

        # A personal address is not one, however it is typed in.
        c.post(
            f"/credentials/approvals/{signed.pk}/decide/",
            {"decision": "approve", "institution_email": f"no.badge{n}@gmail.com"},
        )
        signed.refresh_from_db()
        assert signed.state == SignedAgreement.State.SIGNED, "and not any address will do"

        # The institution's own domain grants it, and is put on the account.
        c.post(
            f"/credentials/approvals/{signed.pk}/decide/",
            {"decision": "approve", "institution_email": f"no.badge{n}@example.edu"},
        )
        signed.refresh_from_db()
        assert signed.state == SignedAgreement.State.APPROVED
