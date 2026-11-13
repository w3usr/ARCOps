"""A field that has a default shows it filled in, never "blank means the default" (#272, #277;
NAF, 2026-11-12). Untouched, the event follows the club's default: nothing is stored, and a later
change to the club setting reaches it (SK, 2026-11-12: "Follow"). A "Club default" tag stands
beside a field while it holds the club's value. Written before the code."""

import pytest

from apps.credentials.models import CredentialType
from apps.events.models import EligibilityRule
from apps.events.services.eligibility import can_sign_up
from apps.events.views_manage import GenerateForm
from apps.ops.models import ClubSetting

from .test_manage import _as
from .test_manage_gaps import _future, _live
from .test_phase2 import _user

pytestmark = pytest.mark.django_db


def _club(key, value):
    ClubSetting.objects.update_or_create(key=key, defaults={"value": value})


def _mentor_needs_a_license():
    """A club whose Mentor needs a valid license of any class (FR-122)."""
    _club(
        "slot_roles",
        [
            {"key": "operator", "label": "Operator", "on_air": True},
            {"key": "mentor", "label": "Mentor", "on_air": True, "requires_license": True},
        ],
    )


def _input_value(page, name):
    tag = page.split(f'name="{name}"', 1)[1].split(">", 1)[0]
    return tag.split('value="', 1)[1].split('"', 1)[0] if 'value="' in tag else ""


# ------------------------------------------------------------------- #272: the reminder ---


def test_the_reminder_box_shows_the_clubs_default_and_untouched_follows_it(officer):
    _club("defaults.reminder_hours_before", 36)
    c = _as(officer)
    page = c.get("/events/new/").content.decode()
    assert _input_value(page, "reminder_hours_before") == "36"
    assert "Club default" in page and "Blank uses" not in page
    ev = _future(c)  # created with the box as it was shown
    ev.refresh_from_db()
    assert ev.reminder_hours_before is None  # follows the club
    details = {"title": ev.title, "type": "contest", "reminder_hours_before": "36"}
    c.post(f"/events/{ev.pk}/details/", details)
    ev.refresh_from_db()
    assert ev.reminder_hours_before is None
    c.post(f"/events/{ev.pk}/details/", details | {"reminder_hours_before": "12"})
    ev.refresh_from_db()
    assert ev.reminder_hours_before == 12
    page = c.get(f"/events/{ev.pk}/details/").content.decode()
    assert _input_value(page, "reminder_hours_before") == "12"


# ----------------------------------------------------- #277 case 2: setup and breakdown ---


def test_setup_and_breakdown_lengths_show_the_slot_length_and_follow_it():
    _club("defaults.slot_length_minutes", 45)
    form = GenerateForm(roles=[{"key": "operator", "label": "Operator"}])
    for name in ("setup_minutes", "breakdown_minutes"):
        assert form.fields[name].initial == 45
        assert form.fields[name].widget.attrs.get("data-follows") == "minutes"
        assert "Left blank" not in (form.fields[name].help_text or "")
    data = {"minutes": "90", "setup_slots": "1", "breakdown_slots": "1", "cap_operator": "1"}
    # untouched (still the 45 shown) while the slot became 90: follows the slot
    f = GenerateForm(
        data | {"setup_minutes": "45", "breakdown_minutes": "45"},
        roles=[{"key": "operator", "label": "Operator"}],
    )
    assert f.is_valid(), f.errors
    assert f.cleaned_data["setup_minutes"] in (None, 90) and f.cleaned_data[
        "breakdown_minutes"
    ] in (None, 90)
    # edited to 45 on purpose (the script marks it): kept
    f = GenerateForm(
        data | {"setup_minutes": "45", "setup_minutes_edited": "1", "breakdown_minutes": "30"},
        roles=[{"key": "operator", "label": "Operator"}],
    )
    assert f.is_valid(), f.errors
    assert f.cleaned_data["setup_minutes"] == 45 and f.cleaned_data["breakdown_minutes"] == 30


# ------------------------------------------------------- #277 case 3: who may sign up ---


def test_the_sign_up_rules_show_the_rule_actually_applied(officer):
    _mentor_needs_a_license()
    c = _as(officer)
    ev = _future(c)
    page = c.get(f"/events/{ev.pk}/manage/rules/").content.decode()
    assert "Nothing set means" not in page
    mentor = page.split('name="class_mentor"', 1)[1].split("</select>", 1)[0]
    assert 'value="any" selected' in mentor  # the club's: a valid license of any class
    operator = page.split('name="class_operator"', 1)[1].split("</select>", 1)[0]
    assert 'value="" selected' in operator or "selected" not in operator
    assert "Club default" in page
    # saved as shown: nothing stored, the club's rule still applies
    shown = {
        "class_mentor": "any",
        "class_operator": "",
        "minors_mentor": "on",
        "minors_operator": "on",
    }
    c.post(f"/events/{ev.pk}/eligibility/", shown)
    assert not EligibilityRule.objects.filter(event=ev).exists()


def test_a_mentor_set_to_need_nothing_is_stored_and_applied(officer):
    _mentor_needs_a_license()
    c = _as(officer)
    ev = _future(c)
    c.post(
        f"/events/{ev.pk}/eligibility/",
        {"class_mentor": "", "minors_mentor": "on", "minors_operator": "on"},
    )
    rule = EligibilityRule.objects.get(event=ev, role="mentor")
    assert rule.required_credentials == [] and rule.min_license_class == ""
    slot = _live(ev).first()
    ok, _ = can_sign_up(_user("nolicense@example.org"), slot, "mentor")
    assert ok


def test_any_class_with_a_category_keeps_the_license(officer):
    _mentor_needs_a_license()
    CredentialType.objects.get_or_create(
        key="amateur_license", defaults={"label": "Amateur license"}
    )
    c = _as(officer)
    ev = _future(c)
    c.post(
        f"/events/{ev.pk}/eligibility/",
        {
            "class_mentor": "any",
            "cat_mentor": "student",
            "minors_mentor": "on",
            "minors_operator": "on",
        },
    )
    rule = EligibilityRule.objects.get(event=ev, role="mentor")
    assert "amateur_license" in rule.required_credentials and rule.categories == ["student"]
    ok, why = can_sign_up(_user("stu@example.org"), _live(ev).first(), "mentor")
    assert not ok and "license" in why


# ---------------------------------------------------- #277 case 4: a location's own rule ---


def test_a_locations_needs_start_from_the_clubs_rule_and_untouched_follow_it(officer):
    for key, label in (
        ("amateur_license", "Amateur license"),
        ("station_access", "Station access"),
        ("it_access", "Computer access"),
        ("site_lead", "Site lead"),
    ):
        CredentialType.objects.get_or_create(key=key, defaults={"label": label})
    c = _as(officer)
    ev = _future(c)
    loc = ev.locations.get()
    url = f"/events/{ev.pk}/locations/{loc.pk}/edit/"
    page = c.get(url).content.decode()
    assert 'name="own_rule"' not in page and "the club's rule applies" not in page
    for key in ("amateur_license", "station_access", "it_access"):
        box = page.split(f'value="{key}"', 1)[1].split(">", 1)[0]
        assert "checked" in box, key
    assert "checked" not in page.split('value="site_lead"', 1)[1].split(">", 1)[0]
    form = {"name": "Shack", "address": "", "directions_html": "", "kbyg_html": ""}
    c.post(url, form | {"needs": ["amateur_license", "station_access", "it_access"]})
    loc.refresh_from_db()
    assert loc.viability_rule is None  # as shown: the club's rule, followed
    c.post(url, form | {"needs": ["site_lead"]})
    loc.refresh_from_db()
    assert loc.viability_rule == {"require_all_of": [{"credential": "site_lead"}]}


# ------------------------------------------------- #277 case 5: a slot's own override ---


def test_a_slots_override_starts_from_the_events_rule(officer):
    c = _as(officer)
    ev = _future(c)
    slot = _live(ev).first()
    page = c.get(f"/events/{ev.pk}/slot/{slot.pk}/").content.decode()
    form = page.split("Who may sign up for this slot", 1)[1].split("</details>", 1)[0]
    assert 'value="any"' in form  # the override can say "any class"
    assert "data-rule=" in form  # each role carries the rule it starts from


# ------------------------------------------------------------------- the sweep ---


def test_no_help_text_says_blank_means_the_default():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    for path in [*root.glob("apps/**/*.py"), *root.glob("templates/**/*.html")]:
        if "tests" in path.parts or "migrations" in path.parts:
            continue
        text = path.read_text()
        for phrase in ("Left blank", "Blank uses", "Nothing set means"):
            assert phrase not in text, f"{path}: {phrase}"
