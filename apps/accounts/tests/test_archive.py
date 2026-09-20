"""The archive of former members (FR-125).

The advisor, 2026-09-17: "I don't really like the automatic deletion. Instead, can we have a
method to archive members? Only faculty advisors and above can view the archive."

Two things changed on 2026-09-19. An account is closed or suspended **before** it is archived,
so that every account somebody could still use stays on the members list; and the archive is a
filter on that list rather than a page of its own, with the status it went in with kept intact,
so taking a record out of the archive and letting the person back in are two acts.
"""

import pytest
from django.test import Client

from apps.accounts.models import Guardianship, User
from apps.accounts.services import ArchiveRefused, archive_member, restore_member
from apps.ops.models import AuditLog

pytestmark = pytest.mark.django_db
PASSWORD = "pw-Testing-123"


def _user(email, level="member", **kw):
    kw.setdefault("first_name", email.split("@")[0].title())
    kw.setdefault("last_name", "Tester")
    kw.setdefault("category", "student")
    return User.objects.create_user(
        email,
        PASSWORD,
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


def _closed(member):
    """The state an account is in before it can be archived: the member asked to leave."""
    from apps.accounts.services import request_closure

    request_closure(member)
    member.refresh_from_db()
    return member


def test_archiving_an_open_account_closes_it_in_the_same_act():
    """An archived account is never one somebody can still use.

    The advisor, 2026-09-19: "Faculty Advisors and above should be able to Close and archive
    accounts without suspending." A departure is not a decision about somebody's conduct, so
    filing a graduating member takes one action and no suspension.
    """
    advisor = _user("adv@example.org", "advisor")
    member = _user("mem@example.org")
    r = _as(advisor).post(
        f"/members/{member.pk}/edit/", {"action": "archive", "reason": "graduated"}, follow=True
    )
    assert r.status_code == 200
    member.refresh_from_db()
    assert member.is_archived and member.status == "closed" and not member.has_access
    assert member.closed_by == advisor and member.suspended_at is None


def test_an_advisor_closes_an_account_without_suspending_it():
    advisor = _user("adv@example.org", "advisor")
    member = _user("mem@example.org")
    _as(advisor).post(
        f"/members/{member.pk}/edit/", {"action": "shut", "reason": "graduated"}, follow=True
    )
    member.refresh_from_db()
    assert member.status == "closed" and not member.is_archived
    body = _as(advisor).get(f"/members/{member.pk}/").content.decode()
    assert "Closed by" in body and "Suspended" not in body

    # an officer has no such button, and a forged post does nothing
    officer = _user("off@example.org", "officer")
    other = _user("two@example.org")
    assert 'value="shut"' not in _as(officer).get(f"/members/{other.pk}/edit/").content.decode()
    _as(officer).post(f"/members/{other.pk}/edit/", {"action": "shut"})
    other.refresh_from_db()
    assert other.has_access


def test_archiving_keeps_everything_and_ends_access():
    advisor = _user("adv@example.org", "advisor")
    member = _closed(_user("mem@example.org", callsign="N0ARC", cell_phone="555-0100"))
    c = _as(advisor)
    r = c.post(
        f"/members/{member.pk}/edit/", {"action": "archive", "reason": "graduated"}, follow=True
    )
    assert r.status_code == 200 and b"is in the archive" in r.content

    member.refresh_from_db()
    assert member.is_archived and member.archived_reason == "graduated"
    assert not member.has_access  # and so sign-in is refused
    assert not Client().login(email="mem@example.org", password=PASSWORD)
    # nothing of theirs was deleted
    assert member.callsign == "N0ARC" and member.cell_phone == "555-0100"
    assert member.addresses.filter(address="mem@example.org").exists()
    assert AuditLog.objects.filter(action="member.archived").exists()


def test_a_former_member_leaves_the_list_until_it_is_asked_for_them():
    advisor = _user("adv@example.org", "advisor")
    member = _closed(_user("mem@example.org", callsign="N0ARC"))
    archive_member(advisor, member, "moved away")

    c = _as(advisor)
    assert b"N0ARC" not in c.get("/members/").content
    body = c.get("/members/?archived=yes").content
    assert b"N0ARC" in body and b"Archived" in body
    assert b"N0ARC" in c.get("/members/archive/", follow=True).content, "the old URL still works"
    # and an ordinary member's list never held them either
    other = _user("other@example.org")
    assert b"N0ARC" not in _as(other).get("/members/?archived=yes").content


def test_only_a_faculty_advisor_or_above_reads_the_archive():
    sysadmin = _user("sys@example.org", "sysadmin")
    advisor = _user("adv@example.org", "advisor")
    officer = _user("off@example.org", "officer")
    member = _user("mem@example.org")
    for user, expected in ((sysadmin, 302), (advisor, 302), (officer, 404), (member, 404)):
        assert _as(user).get("/members/archive/").status_code == expected, user.email
    # and an officer asking for the archived rows by hand gets the ordinary list instead
    archived = _closed(_user("gone@example.org", callsign="N0GON"))
    archive_member(advisor, archived, "graduated")
    assert b"N0GON" not in _as(officer).get("/members/?archived=yes").content
    # one roster, so no second menu entry: the archived rows are a filter and a column on the
    # members list, and only a reader who may see one gets either (NAF, 2026-09-19)
    assert b"Archived members" not in _as(advisor).get("/").content
    body = _as(advisor).get("/members/").content.decode()
    assert "sort=archived" in body and 'name="archived"' in body, "the column and the filter"
    officer_body = _as(officer).get("/members/").content.decode()
    assert "sort=archived" not in officer_body and 'name="archived"' not in officer_body


def test_an_officer_cannot_reach_a_former_member_by_url():
    """The archive would leak through the member page otherwise, since an officer can open any
    member by number."""
    advisor = _user("adv@example.org", "advisor")
    officer = _user("off@example.org", "officer")
    member = _closed(_user("mem@example.org"))
    archive_member(advisor, member, "graduated")
    assert _as(officer).get(f"/members/{member.pk}/").status_code == 404
    assert _as(advisor).get(f"/members/{member.pk}/").status_code == 200


def test_opening_the_archive_is_recorded():
    """It holds contact details for people who are no longer around to ask, so who reads it is
    part of the record."""
    advisor = _user("adv@example.org", "advisor")
    _as(advisor).get("/members/?archived=yes&q=smith")
    row = AuditLog.objects.get(action="archive.viewed")
    assert row.actor == advisor and row.after == {"search": "smith"}


def test_taking_a_record_out_of_the_archive_leaves_its_status_alone():
    """Two dimensions, two acts (the advisor, 2026-09-19): the record comes back Closed, and
    somebody lets the person in afterwards."""
    advisor = _user("adv@example.org", "advisor")
    member = _closed(_user("mem@example.org"))
    archive_member(advisor, member, "graduated")
    r = _as(advisor).post(f"/members/{member.pk}/edit/", {"action": "restore"}, follow=True)
    assert r.status_code == 200
    member.refresh_from_db()
    assert not member.is_archived and member.status == "closed" and not member.has_access
    back = Client()
    back.force_login(member)
    assert back.get("/").status_code == 302, "no access is still no access"
    assert AuditLog.objects.filter(action="member.restored").exists()

    _as(advisor).post(f"/members/{member.pk}/edit/", {"action": "reopen"})
    member.refresh_from_db()
    assert member.status == "active" and member.in_group("member")
    assert Client().login(email="mem@example.org", password=PASSWORD)


def test_an_officer_cannot_archive_anyone():
    officer = _user("off@example.org", "officer")
    member = _closed(_user("mem@example.org"))
    _as(officer).post(f"/members/{member.pk}/edit/", {"action": "archive"})
    member.refresh_from_db()
    assert not member.is_archived


def test_a_guardian_with_a_minor_and_the_last_sysadmin_are_refused():
    advisor = _user("adv@example.org", "advisor")
    guardian = _closed(_user("guard@example.org"))
    minor = _user("kid@example.org", under_18=True)
    Guardianship.objects.create(minor=minor, guardian=guardian)
    with pytest.raises(ArchiveRefused):
        archive_member(advisor, guardian)

    sysadmin = _user("sys@example.org", "sysadmin")
    with pytest.raises(ArchiveRefused):
        archive_member(advisor, sysadmin)


def test_archiving_your_own_account_is_refused():
    advisor = _user("adv@example.org", "advisor")
    r = _as(advisor).post(f"/members/{advisor.pk}/edit/", {"action": "archive"}, follow=True)
    assert b"cannot archive your own account" in r.content
    advisor.refresh_from_db()
    assert not advisor.is_archived


def test_restoring_returns_the_record_untouched():
    """Nothing ages out while someone is in the archive, so there is nothing to restore but the
    access itself."""
    advisor = _user("adv@example.org", "advisor")
    member = _closed(_user("mem@example.org", callsign="N0ARC", cell_phone="555-0100"))
    archive_member(advisor, member, "graduated")
    restore_member(advisor, member)
    member.refresh_from_db()
    assert member.callsign == "N0ARC" and member.cell_phone == "555-0100"
    assert member.archived_reason == "" and member.archived_at is None


def test_taking_an_account_out_of_service_is_all_in_one_place():
    """NAF, 2026-09-20: "Account closing should also be under the Danger Zone" and "The option to
    Archive should only appear for accounts that are already Closed or Suspended."

    So the Danger zone holds closing, suspension, archiving and deletion, and archiving is the
    second step: an active account offers no way to skip straight to it.
    """
    from django.core.management import call_command

    call_command("club_import")
    sysadmin = _user("sys@example.org", "sysadmin")
    member = _user("mem@example.org")
    page = _as(sysadmin).get(f"/members/{member.pk}/edit/").content.decode()
    zone = page[page.index("Danger zone") :]
    assert "Close this account" in zone, "closing is a danger-zone control now"
    assert "Leaving the club" not in page, "and has no card of its own"
    assert "Archive this member" not in page, "not while the account is active"

    from apps.accounts.services import close_account

    close_account(sysadmin, member, "graduated")
    page = _as(sysadmin).get(f"/members/{member.pk}/edit/").content.decode()
    zone = page[page.index("Danger zone") :]
    assert "Archive this member" in zone, "offered once the account is closed"
    assert "Close this account" not in zone, "and closing is done"
