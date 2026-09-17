"""The access ladder, and what the faculty advisor level holds.

The advisor, 2026-09-17 (issue 87): "We need a 'Faculty Advisor' access level. This is above
'Club Officer' but below 'Sysadmin'. Faculty Advisors should have the ability to approve access
agreements. Club officers should not."
"""

import pytest
from django.test import Client

from apps.accounts.models import AccessLevel, User, levels_at_least

pytestmark = pytest.mark.django_db


def _user(email, level, **kw):
    kw.setdefault("first_name", email.split("@")[0].title())
    kw.setdefault("last_name", "Tester")
    kw.setdefault("category", "faculty")
    return User.objects.create_user(email, "pw-Testing-123", access_level=level, **kw)


def test_the_ladder_runs_from_no_access_to_sysadmin():
    assert levels_at_least(AccessLevel.ADVISOR) == [AccessLevel.ADVISOR, AccessLevel.SYSADMIN]
    assert AccessLevel.OFFICER not in levels_at_least(AccessLevel.ADVISOR)
    assert set(levels_at_least(AccessLevel.NONE)) == set(AccessLevel.values)


def test_an_advisor_holds_everything_an_officer_holds():
    advisor = _user("adv@example.org", AccessLevel.ADVISOR)
    assert advisor.is_officer and advisor.is_member and advisor.is_advisor
    assert not advisor.is_sysadmin  # and nothing that is a sysadmin's
    assert not advisor.at_least(AccessLevel.SYSADMIN)


def test_an_officer_is_not_an_advisor_whatever_their_club_position():
    officer = _user("off@example.org", AccessLevel.OFFICER, club_position="faculty_advisor")
    assert officer.is_officer and not officer.is_advisor


def test_only_an_advisor_or_above_approves_an_access_agreement():
    """The capability used to hang on the club position, so an elected officer in a marked
    position could approve. It follows the access level now."""
    from apps.credentials.services import approvers
    from apps.credentials.views import _is_approver

    sysadmin = _user("sys@example.org", AccessLevel.SYSADMIN)
    advisor = _user("adv@example.org", AccessLevel.ADVISOR)
    officer = _user("off@example.org", AccessLevel.OFFICER, club_position="faculty_advisor")
    member = _user("mem@example.org", AccessLevel.MEMBER)

    assert _is_approver(sysadmin) and _is_approver(advisor)
    assert not _is_approver(officer) and not _is_approver(member)
    assert {u.pk for u in approvers()} == {sysadmin.pk, advisor.pk}

    # and the approvals page follows the same rule
    for user, expected in ((advisor, 200), (officer, 404), (member, 404)):
        c = Client()
        c.force_login(user)
        assert c.get("/credentials/approvals/").status_code == expected, user.email
