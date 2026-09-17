"""The archive of former members (FR-125).

The advisor, 2026-09-17: "I don't really like the automatic deletion. Instead, can we have a
method to archive members? Only faculty advisors and above can view the archive."
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
        email, PASSWORD, groups=[level], is_superuser=level == "sysadmin", **kw
    )


def _as(user):
    c = Client()
    c.force_login(user)
    return c


def test_archiving_keeps_everything_and_ends_access():
    advisor = _user("adv@example.org", "advisor")
    member = _user("mem@example.org", callsign="N0ARC", cell_phone="555-0100")
    c = _as(advisor)
    r = c.post(f"/members/{member.pk}/", {"action": "archive", "reason": "graduated"}, follow=True)
    assert r.status_code == 200 and b"is in the archive" in r.content

    member.refresh_from_db()
    assert member.is_archived and member.archived_reason == "graduated"
    assert not member.has_access  # and so sign-in is refused
    assert not Client().login(email="mem@example.org", password=PASSWORD)
    # nothing of theirs was deleted
    assert member.callsign == "N0ARC" and member.cell_phone == "555-0100"
    assert member.addresses.filter(address="mem@example.org").exists()
    assert AuditLog.objects.filter(action="member.archived").exists()


def test_a_former_member_leaves_the_directory_and_appears_in_the_archive():
    advisor = _user("adv@example.org", "advisor")
    member = _user("mem@example.org", callsign="N0ARC")
    archive_member(advisor, member, "moved away")

    c = _as(advisor)
    assert b"N0ARC" not in c.get("/members/").content
    body = c.get("/members/archive/").content
    assert b"N0ARC" in body and b"moved away" in body
    # and an ordinary member's directory never held them either
    other = _user("other@example.org")
    assert b"N0ARC" not in _as(other).get("/members/").content


def test_only_a_faculty_advisor_or_above_reads_the_archive():
    sysadmin = _user("sys@example.org", "sysadmin")
    advisor = _user("adv@example.org", "advisor")
    officer = _user("off@example.org", "officer")
    member = _user("mem@example.org")
    for user, expected in ((sysadmin, 200), (advisor, 200), (officer, 404), (member, 404)):
        assert _as(user).get("/members/archive/").status_code == expected, user.email
    # the sidebar offers it to exactly those people
    assert b"Archive" in _as(advisor).get("/").content
    assert b"Archive" not in _as(officer).get("/").content


def test_an_officer_cannot_reach_a_former_member_by_url():
    """The archive would leak through the member page otherwise, since an officer can open any
    member by number."""
    advisor = _user("adv@example.org", "advisor")
    officer = _user("off@example.org", "officer")
    member = _user("mem@example.org")
    archive_member(advisor, member, "graduated")
    assert _as(officer).get(f"/members/{member.pk}/").status_code == 404
    assert _as(advisor).get(f"/members/{member.pk}/").status_code == 200


def test_opening_the_archive_is_recorded():
    """It holds contact details for people who are no longer around to ask, so who reads it is
    part of the record."""
    advisor = _user("adv@example.org", "advisor")
    _as(advisor).get("/members/archive/?q=smith")
    row = AuditLog.objects.get(action="archive.viewed")
    assert row.actor == advisor and row.after == {"search": "smith"}


def test_an_advisor_brings_a_former_member_back():
    advisor = _user("adv@example.org", "advisor")
    member = _user("mem@example.org")
    archive_member(advisor, member, "graduated")
    r = _as(advisor).post(f"/members/{member.pk}/", {"action": "restore"}, follow=True)
    assert r.status_code == 200
    member.refresh_from_db()
    assert not member.is_archived and member.in_group("member")
    assert Client().login(email="mem@example.org", password=PASSWORD)
    assert AuditLog.objects.filter(action="member.restored").exists()


def test_an_officer_cannot_archive_anyone():
    officer = _user("off@example.org", "officer")
    member = _user("mem@example.org")
    _as(officer).post(f"/members/{member.pk}/", {"action": "archive"})
    member.refresh_from_db()
    assert not member.is_archived


def test_a_guardian_with_a_minor_and_the_last_sysadmin_are_refused():
    advisor = _user("adv@example.org", "advisor")
    guardian = _user("guard@example.org")
    minor = _user("kid@example.org", under_18=True)
    Guardianship.objects.create(minor=minor, guardian=guardian)
    with pytest.raises(ArchiveRefused):
        archive_member(advisor, guardian)

    sysadmin = _user("sys@example.org", "sysadmin")
    with pytest.raises(ArchiveRefused):
        archive_member(advisor, sysadmin)


def test_archiving_your_own_account_is_refused():
    advisor = _user("adv@example.org", "advisor")
    r = _as(advisor).post(f"/members/{advisor.pk}/", {"action": "archive"}, follow=True)
    assert b"cannot archive your own account" in r.content
    advisor.refresh_from_db()
    assert not advisor.is_archived


def test_restoring_returns_the_record_untouched():
    """Nothing ages out while someone is in the archive, so there is nothing to restore but the
    access itself."""
    advisor = _user("adv@example.org", "advisor")
    member = _user("mem@example.org", callsign="N0ARC", cell_phone="555-0100")
    archive_member(advisor, member, "graduated")
    restore_member(advisor, member)
    member.refresh_from_db()
    assert member.callsign == "N0ARC" and member.cell_phone == "555-0100"
    assert member.archived_reason == "" and member.archived_at is None
