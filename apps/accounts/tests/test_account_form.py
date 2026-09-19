"""One account form, two pages, and the permission table it derives its fields from.

The advisor, 2026-09-17: "there should be a single user entry UI, just with different levels of
permission. Right now there are clearly two different ones." These cases pin the table so the
two pages cannot drift apart again.
"""

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.account import AccountForm, editable_fields
from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def _user(email, level="member", **kw):
    kw.setdefault("first_name", email.split("@")[0].title())
    kw.setdefault("last_name", "Tester")
    u = User.objects.create_user(email, "pw-Testing-123", **kw)
    if level == "sysadmin":  # a sysadmin is a superuser, not a member of a group
        u.is_superuser = True
    else:
        u.groups.set(Group.objects.filter(name=level))
    u.save()
    return u


def test_a_member_edits_their_own_details_and_no_privilege_field():
    m = _user("mem@example.org")
    fields = editable_fields(m, m)
    for allowed in ("preferred_name", "callsign", "cell_phone", "first_name"):
        assert allowed in fields, allowed
    for refused in ("category", "groups", "club_position", "under_18", "legal_hold", "email"):
        assert refused not in fields, refused


def test_a_member_with_a_name_from_the_fcc_does_not_type_their_name():
    m = _user("mem@example.org")
    m.name_from_uls = True
    m.save()
    fields = editable_fields(m, m)
    assert "first_name" not in fields and "preferred_name" in fields


def test_an_officer_says_who_is_a_member_and_nothing_else():
    """An officer holds the bounded form of "decide which groups an account is in" (§2.3, the
    advisor's rule of 2026-09-19). Who holds which office is the advisor's to record, from the
    same day: "Only Faculty Advisors and above should be able to set club position."
    """
    off, m = _user("off@example.org", "officer"), _user("mem@example.org")
    assert editable_fields(off, m) == ["groups"]
    other = _user("off2@example.org", "officer")
    assert editable_fields(off, other) == [], "a peer is not theirs to change at all"
    advisor = _user("adv@example.org", "advisor")
    assert editable_fields(advisor, m) == ["club_position", "groups"]


def test_a_sysadmin_sets_everything_on_any_account_including_their_own():
    sys_user, m = _user("sys@example.org", "sysadmin"), _user("mem@example.org")
    for subject in (m, sys_user):
        fields = editable_fields(sys_user, subject)
        for allowed in (
            "first_name",
            "preferred_name",
            "callsign",
            "cell_phone",
            "category",
            "club_position",
            "groups",
            "under_18",
            "legal_hold",
            "student_level",
        ):
            assert allowed in fields, f"{allowed} for {subject.email}"


def test_both_pages_render_the_same_fields_for_the_same_person():
    """The member's own page and a sysadmin's view of them differ by permission, not by page."""
    sys_user = _user("sys@example.org", "sysadmin")
    own = set(AccountForm(instance=sys_user, actor=sys_user).fields)
    from_member_page = set(AccountForm(instance=sys_user, actor=sys_user).fields)
    assert own == from_member_page

    m = _user("mem@example.org")
    c = Client()
    c.force_login(m)
    if m.is_superuser:
        session = c.session  # acting at the raised level
        session["acting_view"] = "sysadmin"
        session.save()
    profile = c.get("/me/edit/", follow=True).content.decode()
    c2 = Client()
    c2.force_login(sys_user)
    if sys_user.is_superuser:
        session = c2.session  # acting at the raised level
        session["acting_view"] = "sysadmin"
        session.save()
    member_page = c2.get(f"/members/{m.pk}/edit/").content.decode()
    # the member's own fields appear on their page; the privilege fields only on the officer's
    assert 'name="preferred_name"' in profile and 'name="category"' not in profile
    assert 'name="preferred_name"' in member_page and 'name="category"' in member_page
    # and the same field carries the same label on both
    assert "Mobile number" in profile and "Mobile number" in member_page


def test_a_callsign_typed_on_the_member_page_goes_through_the_fcc_lookup():
    """It used to be uppercased and stored, skipping the lookup, the license record, and the
    name check that the profile did (found 2026-09-17)."""
    from apps.credentials.models import LicenseRecord, UlsLicense

    sys_user, m = _user("sys@example.org", "sysadmin"), _user("mem@example.org")
    UlsLicense.objects.create(
        callsign="N0PAGE",
        first_name="Mem",
        last_name="Tester",
        operator_class="General",
        status="active",
    )
    c = Client()
    c.force_login(sys_user)
    if sys_user.is_superuser:
        session = c.session  # acting at the raised level
        session["acting_view"] = "sysadmin"
        session.save()
    r = c.post(
        f"/members/{m.pk}/edit/",
        {
            "action": "save",
            "first_name": "Mem",
            "last_name": "Tester",
            "category": "",
            "groups": [Group.objects.get(name="member").pk],
            "email": m.email,
            "callsign": "n0page",
        },
    )
    assert r.status_code == 302
    m.refresh_from_db()
    assert m.callsign == "N0PAGE"
    lic = LicenseRecord.objects.get(user=m)
    assert lic.operator_class == "General" and lic.source == "fcc_uls_local"

    # changing it again keeps the old one in the history, as the profile always did
    c.post(
        f"/members/{m.pk}/edit/",
        {
            "action": "save",
            "first_name": "Mem",
            "last_name": "Tester",
            "category": "",
            "groups": [Group.objects.get(name="member").pk],
            "email": m.email,
            "callsign": "N0NEW",
        },
    )
    assert m.callsign_history.filter(callsign="N0PAGE").exists()


def test_a_field_is_shown_once_as_an_input_or_as_text_but_never_both():
    """The advisor, 2026-09-17: "I don't like the UI where the information is duplicated with a
    read-only view and an edit view." The read-only rows are the complement of the form."""
    from apps.accounts.account import editable_fields, readonly_rows

    sys_user = _user("sys@example.org", "sysadmin")
    off = _user("off@example.org", "officer")
    m = _user("mem@example.org", category="student", cell_phone="555-0100")

    for actor in (m, off, sys_user):
        editable = set(editable_fields(actor, m))
        shown = {r["label"] for r in readonly_rows(actor, m)}
        # nothing a person may type is also printed at them as settled text
        if "cell_phone" in editable:
            assert "Mobile number" not in shown
        if "category" in editable:
            assert "Category" not in shown
        if "first_name" in editable:
            assert "First name" not in shown
        if "groups" in editable:
            assert "Access" not in shown

    # a sysadmin edits every field there is; what is left as text is what nobody types
    assert [r["field"] for r in readonly_rows(sys_user, m)] == ["date_joined"]
    # an officer edits the club position and who is a member, so the rest is text
    labels = {r["label"] for r in readonly_rows(off, m)}
    assert {"First name", "Last name", "Category", "Mobile number"} <= labels
    assert "Access" not in labels, "which they may set, so it is a field rather than a line"


def test_no_template_comment_reaches_the_page():
    """Django's {# #} is one line only; a multi-line one renders as text, which it did."""
    sys_user = _user("sys@example.org", "sysadmin")
    c = Client()
    c.force_login(sys_user)
    if sys_user.is_superuser:
        session = c.session  # acting at the raised level
        session["acting_view"] = "sysadmin"
        session.save()
    for url in ("/me/", "/me/edit/", f"/members/{sys_user.pk}/edit/"):
        body = c.get(url).content.decode()
        assert "{#" not in body and "editable_fields" not in body, url
