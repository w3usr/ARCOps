"""The preferred class (FR-61), role defaults (FR-122), lettered names (FR-67), hours (FR-124)."""

import datetime as dt

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccessLevel, EntryLink, User
from apps.events.models import SignUp
from apps.events.services.eligibility import can_sign_up
from apps.events.services.hours import course_report
from apps.events.services.roster import build
from apps.events.services.viability import evaluate
from apps.events.tests.test_viability import (  # noqa: F401 - fixture and helpers
    club_config,
    person,
    slot_for,
)
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


def test_a_technician_makes_a_general_event_viable_with_a_warning():
    s = slot_for("General")
    SignUp.objects.create(slot=s, user=person("tech", "Technician"), role="mentor")
    SignUp.objects.create(slot=s, user=person("acc", None, station=True, it=True), role="operator")
    st = evaluate(s)
    assert st.status in ("viable", "at_risk") and st.below_preferred == "Technician"
    data = build(s.event, person("viewer"), "utc")
    cell = data["days"][0].rows[0].cells[0]
    assert (
        cell.shown.word == "Covered"
        and "below preferred class (Technician)" in cell.shown.detail
        and cell.shown.tone == "warn"
    )
    # a General present: no warning
    SignUp.objects.create(slot=s, user=person("gen", "General"), role="operator")
    assert evaluate(s).below_preferred is None


def test_mentor_needs_a_license_operator_does_not():
    ClubSetting.objects.filter(key="slot_roles").update(
        value=[
            {"key": "operator", "on_air": True},
            {"key": "mentor", "on_air": True, "requires_license": True},
            {"key": "observer", "on_air": False},
        ]
    )
    s = slot_for("General")
    nobody = person("nobody")
    ok, reason = can_sign_up(nobody, s, "mentor")
    assert not ok and "license" in reason
    assert can_sign_up(nobody, s, "operator") == (True, "")
    assert can_sign_up(person("tech", "Technician"), s, "mentor") == (
        True,
        "",
    )  # any class; the event's class only warns


def test_names_carry_the_license_letter():
    e = person("ann", "Extra")
    assert e.short_name_lettered == "ann N0AN (E)" and e.full_name_lettered == "ann T N0AN (E)"
    n = person("nolic")
    assert n.short_name_lettered == "nolic T. (U)"
    assert (
        person("gen", "General").license_letter == "G"
        and person("tech", "Technician").license_letter == "T"
    )


def test_hours_credit_check_in_unless_no_show_and_export_csv():
    off = User.objects.create_user(
        "off@example.org", "x", access_level=AccessLevel.OFFICER, first_name="Ann", last_name="O"
    )
    link = EntryLink.objects.create(
        label="PHYS 101",
        kind="class",
        required_domain="example.org",
        expires_at=timezone.now() + dt.timedelta(days=9),
        created_by=off,
    )
    stu = person("stu")
    stu.joined_via = link
    stu.save()
    s = slot_for()
    su = SignUp.objects.create(slot=s, user=stu, role="operator")
    assert course_report("PHYS 101")["totals"][0][1] == 0.0
    su.checked_in_at = timezone.now()
    su.save()
    assert course_report("PHYS 101")["totals"][0][1] == 1.0
    c = Client()
    c.force_login(off)
    c.post(f"/events/signup/{su.pk}/no-show/")
    su.refresh_from_db()
    assert su.no_show and course_report("PHYS 101")["totals"][0][1] == 0.0
    c.post(f"/events/signup/{su.pk}/no-show/")
    body = c.get("/members/hours/?course=PHYS%20101").content.decode()
    assert "stu" in body and "1" in body
    csv_body = c.get("/members/hours/?course=PHYS%20101&format=csv").content.decode()
    assert "Credited hours" in csv_body and "TOTAL" in csv_body
    assert Client().get("/members/hours/").status_code == 302  # login required
