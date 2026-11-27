"""FR-4: the application opens with the callsign; the FCC's record supplies the name, read-only,
and the applicant says it is them. "I do not have a callsign" keeps the name fields."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts import entry
from apps.accounts.models import User
from apps.accounts.services import create_invitation
from apps.credentials.models import UlsLicense

pytestmark = pytest.mark.django_db
PASSWORDS = {
    "password1": "a-long-password-123",
    "password2": "a-long-password-123",
    "consent": "on",
}


@pytest.fixture(autouse=True)
def club():
    call_command("club_import")
    UlsLicense.objects.create(
        callsign="K1ABC",
        operator_class="General",
        status="active",
        licensee_name="Sample, Pat Q",
        first_name="Pat",
        middle_initial="Q",
        last_name="Sample",
        expiry_date=timezone.now().date() + timedelta(days=900),
    )


@pytest.fixture
def off():
    return User.objects.create_user(
        "off@example.org", "x", first_name="Off", last_name="Icer", groups=["officer"]
    )


def test_the_callsign_brings_the_fcc_record_in_place_of_the_name_fields(off):
    inv = create_invitation(off, "new@example.org", "student")
    page = Client().get(f"/me/invite/{inv.token}/").content.decode()
    assert f'hx-get="/me/invite/{inv.token}/names/"' in page  # the callsign field asks
    assert 'name="first_name"' in page and "I do not have a callsign" in page
    block = Client().get(f"/me/invite/{inv.token}/names/", {"callsign": "k1abc"}).content.decode()
    assert (
        "The FCC's record for <strong>K1ABC</strong>: <strong>Sample, Pat Q</strong>, General, active"
        in block
    )
    assert 'name="is_me"' in block and 'name="first_name"' not in block
    block = Client().get(f"/me/invite/{inv.token}/names/", {"callsign": "K9NEW"}).content.decode()
    assert "no record for <strong>K9NEW</strong> yet" in block and 'name="first_name"' in block
    block = (
        Client()
        .get(f"/me/invite/{inv.token}/names/", {"callsign": "K1ABC", "no_callsign": "on"})
        .content.decode()
    )
    assert "FCC's record" not in block and 'name="first_name"' in block


def test_this_is_me_takes_the_fcc_name_and_nothing_is_asked_afterwards(off):
    inv = create_invitation(off, "new@example.org", "student")
    c = Client()
    r = c.post(f"/me/invite/{inv.token}/", {"callsign": "K1ABC", **PASSWORDS})
    assert (
        r.status_code == 200 and "Tick this if the FCC&#x27;s record is yours" in r.content.decode()
    )
    assert (
        "The FCC's record for <strong>K1ABC</strong>" in r.content.decode()
    )  # without JavaScript too
    r = c.post(f"/me/invite/{inv.token}/", {"callsign": "K1ABC", "is_me": "on", **PASSWORDS})
    assert r.status_code == 302
    u = User.objects.by_address("new@example.org").get()
    assert (u.first_name, u.middle_name, u.last_name) == ("Pat", "Q", "Sample")
    assert u.name_from_uls and not u.pending_uls_name and u.license.operator_class == "General"


def test_no_callsign_needs_a_name_and_drops_a_callsign_typed_anyway(off):
    inv = create_invitation(off, "new@example.org", "student")
    c = Client()
    r = c.post(f"/me/invite/{inv.token}/", {"callsign": "K1ABC", "no_callsign": "on", **PASSWORDS})
    assert r.status_code == 200 and not User.objects.by_address("new@example.org").exists()
    r = c.post(
        f"/me/invite/{inv.token}/",
        {
            "callsign": "K1ABC",
            "no_callsign": "on",
            "first_name": "Ann",
            "last_name": "Other",
            **PASSWORDS,
        },
    )
    assert r.status_code == 302
    u = User.objects.by_address("new@example.org").get()
    assert u.callsign == "" and u.first_name == "Ann"


def test_the_join_link_asks_the_same_way_and_only_while_it_is_open(off):
    link = entry.create_link(
        off,
        label="TEST 101",
        kind="class",
        required_domain="uni.example",
        expires_at=timezone.now() + timedelta(days=30),
    )
    page = Client().get(f"/join/{link.token}/form/").content.decode()
    assert f'hx-get="/join/{link.token}/names/"' in page
    block = Client().get(f"/join/{link.token}/names/", {"callsign": "K1ABC"}).content.decode()
    assert "Sample, Pat Q" in block
    assert Client().get("/join/no-such-link/names/", {"callsign": "K1ABC"}).status_code == 404
    assert Client().get("/me/invite/no-such/names/", {"callsign": "K1ABC"}).status_code == 404


def test_the_guardian_looks_the_members_callsign_up_the_same_way(off):
    """FR-4 on the guardian's form (§2.4): the callsign first, the FCC's record for it, and
    "This is them", in words addressed to the guardian."""
    inv = create_invitation(
        off, "kid@example.org", "student", is_minor=True, guardian_email="parent@example.org"
    )
    c = Client()
    page = c.get(f"/me/invite/{inv.token}/").content.decode()
    assert page.index('name="callsign"') < page.index('name="first_name"')  # callsign first
    assert "They do not have a callsign" in page
    block = c.get(f"/me/invite/{inv.token}/names/", {"callsign": "K1ABC"}).content.decode()
    assert "Sample, Pat Q" in block and "This is them" in block and "Not them?" in block
    form = {
        "guardian_first_name": "Lee",
        "guardian_last_name": "Parent",
        "guardian_phone": "555-0100",
        "relationship": "parent",
        "guardian_password1": "pw-Testing-123!",
        "guardian_password2": "pw-Testing-123!",
        "callsign": "K1ABC",
        "minor_email": "kid@example.org",
        "password1": "pw-Kid-Testing-123!",
        "password2": "pw-Kid-Testing-123!",
        "consent": "on",
    }
    r = c.post(f"/me/invite/{inv.token}/", form)
    assert r.status_code == 200 and "the FCC&#x27;s record is theirs" in r.content.decode()
    assert c.post(f"/me/invite/{inv.token}/", {**form, "is_me": "on"}).status_code == 302
    kid = User.objects.by_address("kid@example.org").get()
    assert (kid.first_name, kid.last_name, kid.callsign) == ("Pat", "Sample", "K1ABC")
    assert kid.name_from_uls and not kid.pending_uls_name
