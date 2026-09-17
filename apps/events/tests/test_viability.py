import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.credentials.models import CredentialType, LicenseRecord, SignedAgreement
from apps.events.models import (
    Event,
    Location,
    OperatingPeriod,
    Position,
    ResponsibleAdult,
    SignUp,
)
from apps.events.services.slots import generate_slots
from apps.events.services.viability import checkin_window_open, evaluate, would_break
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def club_config():
    ClubSetting.objects.create(
        key="license_ladder", value=["Novice", "Technician", "General", "Advanced", "Extra"]
    )
    ClubSetting.objects.create(
        key="slot_roles",
        value=[
            {"key": "operator", "on_air": True},
            {"key": "mentor", "on_air": True},
            {"key": "observer", "on_air": False},
        ],
    )
    ClubSetting.objects.create(
        key="viability_rule_default",
        value={
            "require_all_of": [
                {"credential": "amateur_license", "min_class_from_event": True},
                {"credential": "station_access"},
                {"credential": "it_access"},
            ]
        },
    )
    for key in ("station_access", "it_access"):
        CredentialType.objects.create(key=key, label=key, established_by="agreement")
    CredentialType.objects.create(
        key="amateur_license", label="lic", established_by="fcc_uls", graded=True
    )


def person(name, cls=None, station=False, it=False, minor=False):
    u = User.objects.create_user(
        f"{name}@example.org",
        "x",
        first_name=name,
        last_name="T",
        groups=["member"],
        under_18=minor,
        callsign=f"N0{name[:2].upper()}" if cls else "",
    )
    far = timezone.now().date() + dt.timedelta(days=400)
    if cls:
        LicenseRecord.objects.create(
            user=u, callsign=u.callsign, operator_class=cls, status="active", expiry_date=far
        )
    for flag, key in ((station, "station_access"), (it, "it_access")):
        if flag:
            SignedAgreement.objects.create(
                user=u,
                credential=CredentialType.objects.get(key=key),
                signer_name=name,
                state="approved",
                expires_on=far,
            )
    return u


def slot_for(min_class="General"):
    ev = Event.objects.create(title="T", state="published", min_license_class=min_class)
    start = timezone.now() + dt.timedelta(days=3)
    OperatingPeriod.objects.create(event=ev, start=start, end=start + dt.timedelta(hours=2))
    loc = Location.objects.create(event=ev, name="Station")
    pos = Position.objects.create(location=loc, name="Run")
    return generate_slots(ev, [pos], minutes=60)[0]


def test_empty():
    assert evaluate(slot_for()).status == "empty"


def test_one_person_holding_everything_is_at_risk_not_viable_alone():
    s = slot_for()
    SignUp.objects.create(slot=s, user=person("ann", "Extra", True, True), role="operator")
    st = evaluate(s)
    assert st.status == "at_risk"  # viable, but depends on one person
    assert st.control_operator.first_name == "ann"


def test_two_people_split_credentials_is_viable():
    s = slot_for()
    SignUp.objects.create(
        slot=s, user=person("lic", "General"), role="operator"
    )  # licensed, no access
    SignUp.objects.create(
        slot=s, user=person("key", None, True, True), role="mentor"
    )  # unlicensed faculty with access
    st = evaluate(s)
    assert st.status in ("viable", "at_risk")
    assert st.control_operator.first_name == "lic"  # FR-63


def test_technician_below_preferred_is_viable_with_a_warning():
    # FR-61 as amended 2026-09-15: any class makes the slot viable; below the event's preferred
    # class is a warning. One person holding everything is still "at risk".
    s = slot_for("General")
    SignUp.objects.create(slot=s, user=person("tec", "Technician", True, True), role="operator")
    st = evaluate(s)
    assert st.status == "at_risk" and st.below_preferred == "Technician"
    assert not any("General or higher" in r for r in st.reasons)  # no longer a missing credential


def test_observer_does_not_count_for_operating_slot():
    s = slot_for()
    SignUp.objects.create(slot=s, user=person("obs", "Extra", True, True), role="observer")
    assert evaluate(s).status == "not_viable"


def test_minor_needs_responsible_adult():
    s = slot_for()
    SignUp.objects.create(slot=s, user=person("adult", "Extra", True, True), role="operator")
    kid = SignUp.objects.create(slot=s, user=person("kid", None, minor=True), role="observer")
    assert evaluate(s).status == "not_viable"
    ResponsibleAdult.objects.create(signup=kid, name="A Parent", phone="555")
    assert evaluate(s).status in ("viable", "at_risk")


def test_would_break_warns_before_cancel():
    s = slot_for()
    only = SignUp.objects.create(slot=s, user=person("solo", "Extra", True, True), role="operator")
    broken = would_break(s, only)
    assert broken is not None and broken.status == "empty"


def test_checkin_window():
    s = slot_for()
    ClubSetting.objects.create(key="defaults.checkin_opens_minutes_before", value=30)
    assert checkin_window_open(s, s.start - dt.timedelta(minutes=29))
    assert not checkin_window_open(s, s.start - dt.timedelta(minutes=31))
    assert checkin_window_open(s, s.end)
