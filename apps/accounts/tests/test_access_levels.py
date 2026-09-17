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


def test_the_advisor_contact_line_on_a_reminder_follows_the_access_level():
    """A slot reminder carries "who to call": the captains and the faculty advisors. It read the
    club position until the position stopped saying anything about what a person may do."""
    from apps.events.services.notify import advisors

    advisor = _user("adv@example.org", AccessLevel.ADVISOR)
    _user("pres@example.org", AccessLevel.OFFICER, club_position="president")
    _user("mem@example.org", AccessLevel.MEMBER, club_position="faculty_advisor")
    assert [u.pk for u in advisors()] == [advisor.pk]


def test_nothing_grants_a_capability_from_a_club_position():
    """The advisor, 2026-09-17: "It seems like we are moving to a model where access is governed
    by access level, rather than position." A position is a label now. Showing one is fine; this
    reads the tree to catch a rule branching on one, which is how the old approver flag worked.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[3]
    # a query selecting people by position; a permission test on the viewer's own position; or
    # anything reading an `approver` key back out of the configured positions
    smells = re.compile(
        r"club_position__in|if [^\n]*\b(?:request\.)?user\.club_position|get\(.approver.\)"
    )
    offenders = []
    for path in sorted(root.glob("apps/**/*.py")) + sorted(root.glob("templates/**/*.html")):
        if "migrations" in path.parts or "tests" in path.parts:
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if smells.search(line):
                offenders.append(f"{path.relative_to(root)}:{number}")
    assert not offenders, "a capability still derives from the club position: " + ", ".join(
        offenders
    )
