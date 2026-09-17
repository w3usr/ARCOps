"""Capabilities and the groups that hold them.

The advisor's issue 87, 2026-09-17: "We need a 'Faculty Advisor' access level. This is above
'Club Officer' but below 'Sysadmin'. Faculty Advisors should have the ability to approve access
agreements. Club officers should not." Then, the same day: "have access be item-by-item, and
then define configurable access groups... Systemic is superuser." So there is no ladder: a group
is a set of capabilities, the club decides what is in it, and a sysadmin holds every one.
"""

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")


def _user(email, groups=(), **kw):
    kw.setdefault("first_name", email.split("@")[0].title())
    kw.setdefault("last_name", "Tester")
    kw.setdefault("category", "faculty")
    return User.objects.create_user(email, "pw-Testing-123", groups=list(groups), **kw)


def test_a_group_is_a_set_of_capabilities_and_nothing_else():
    from apps.ops.capabilities import CODENAMES
    from apps.ops.groups import capabilities_of

    advisor = Group.objects.get(name="advisor")
    held = {code for code, _ in capabilities_of(advisor)}
    assert "approve_agreements" in held and "view_archive" in held
    assert "edit_club_settings" not in held  # the club's configuration is not theirs
    assert held <= set(CODENAMES)


def test_an_advisor_holds_everything_an_officer_holds():
    from apps.ops.groups import capabilities_of

    officer = {code for code, _ in capabilities_of(Group.objects.get(name="officer"))}
    advisor = {code for code, _ in capabilities_of(Group.objects.get(name="advisor"))}
    assert officer < advisor


def test_a_sysadmin_holds_every_capability_by_being_a_superuser():
    from apps.ops.capabilities import CODENAMES

    sysadmin = _user("sys@example.org", is_superuser=True)
    assert all(sysadmin.may(code) for code in CODENAMES)
    assert sysadmin.has_access and not sysadmin.groups.exists()


def test_a_club_position_carries_no_capability():
    officer = _user("off@example.org", ["officer"], club_position="faculty_advisor")
    assert officer.may("manage_events") and not officer.may("approve_agreements")


def test_only_an_advisor_or_above_approves_an_access_agreement():
    """The capability used to hang on the club position, so an elected officer in a marked
    position could approve. It is a capability of its own now, held by the advisor group."""
    from apps.credentials.services import approvers
    from apps.credentials.views import _is_approver

    sysadmin = _user("sys@example.org", is_superuser=True)
    advisor = _user("adv@example.org", ["advisor"])
    officer = _user("off@example.org", ["officer"], club_position="faculty_advisor")
    member = _user("mem@example.org", ["member"])

    assert _is_approver(sysadmin) and _is_approver(advisor)
    assert not _is_approver(officer) and not _is_approver(member)
    assert {u.pk for u in approvers()} == {sysadmin.pk, advisor.pk}

    # and the approvals page follows the same rule
    for user, expected in ((advisor, 200), (officer, 404), (member, 404)):
        c = Client()
        c.force_login(user)
        assert c.get("/credentials/approvals/").status_code == expected, user.email


def test_the_advisor_contact_line_on_a_reminder_follows_the_capability():
    """A slot reminder carries "who to call": the captains and whoever answers for access to the
    station, which is a capability rather than a position or a rank."""
    from apps.events.services.notify import advisors

    advisor = _user("adv@example.org", ["advisor"])
    _user("pres@example.org", ["officer"], club_position="president")
    _user("mem@example.org", ["member"], club_position="faculty_advisor")
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
