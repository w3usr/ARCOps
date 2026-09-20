"""The interface faults that lose somebody's work or act without asking.

The advisor read the live site on 2026-09-17 and found the interface showing the shape of the
code rather than speaking to the person. A review of every template turned up a dozen faults
that were not cosmetic at all; these are the tests for them.
"""

from datetime import UTC, datetime, timedelta

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.comms.models import Announcement
from apps.credentials.models import AgreementTemplate, CredentialType, SignedAgreement
from apps.events.models import (
    Event,
    Location,
    OperatingPeriod,
    Position,
    RoleCapacity,
    SignUp,
    Slot,
)
from apps.events.services.slots import generate_slots

pytestmark = pytest.mark.django_db
PASSWORD = "pw-Testing-123"


def _as(user, view="sysadmin"):
    c = Client()
    c.force_login(user)
    if user.is_superuser:
        session = c.session
        session["acting_view"] = view
        session.save()
    return c


@pytest.fixture
def event():
    off = User.objects.create_user(
        "off@example.org", PASSWORD, groups=["officer"], first_name="Ann", last_name="Officer"
    )
    ev = Event.objects.create(title="RTTY", state=Event.State.PUBLISHED, created_by=off)
    start = datetime(2026, 9, 26, 0, 0, tzinfo=UTC)
    OperatingPeriod.objects.create(event=ev, start=start, end=start + timedelta(hours=3))
    loc = Location.objects.create(event=ev, name="Club station")
    pos = Position.objects.create(location=loc, name="Run", order=1)
    for s in generate_slots(ev, [pos], minutes=60):
        RoleCapacity.objects.create(slot=s, role="operator", capacity=2)
    return {"officer": off, "event": ev, "position": pos}


def test_recount_keeps_the_announcement_the_officer_has_written(event):
    """Recount was a GET, and the GET branch rebuilt the form without the body, so pressing it
    threw away everything written so far."""
    c = _as(event["officer"])
    r = c.post(
        f"/events/{event['event'].pk}/announce/",
        {"action": "recount", "subject": "Bring a coat", "body_html": "<p>It is cold.</p>"},
    )
    assert r.status_code == 200
    body = r.content.decode()
    assert "It is cold." in body and "Bring a coat" in body
    assert not Announcement.objects.exists()  # recounting sends nothing


def test_a_captain_removing_somebody_says_why_and_asks_first(event):
    """The remove control posted confirmed=yes with no reason, so the member was told they had
    been removed and told nothing about why."""
    ev = event["event"]
    slot = Slot.objects.filter(position=event["position"]).first()
    mem = User.objects.create_user(
        "mem@example.org", PASSWORD, groups=["member"], first_name="Mo", last_name="Member"
    )
    su = SignUp.objects.create(slot=slot, user=mem, role="operator")

    c = _as(event["officer"])
    body = c.get(f"/events/{ev.pk}/slot/{slot.pk}/").content.decode()
    assert (
        f"/events/signup/{su.pk}/remove/" in body
    )  # the control goes to the confirmation, not the act

    r = c.get(f"/events/signup/{su.pk}/remove/")
    assert r.status_code == 200
    page = r.content.decode()
    assert "Mo Member" in page and "required" in page
    assert SignUp.objects.filter(pk=su.pk).exists()  # nothing has happened yet

    c.post(f"/events/signup/{su.pk}/cancel/", {"confirmed": "yes", "reason": "Station closed"})
    assert not SignUp.objects.filter(pk=su.pk).exists()


def test_a_member_may_not_reach_the_removal_page_for_somebody_else(event):
    slot = Slot.objects.filter(position=event["position"]).first()
    a = User.objects.create_user(
        "a@example.org", PASSWORD, groups=["member"], first_name="A", last_name="One"
    )
    b = User.objects.create_user(
        "b@example.org", PASSWORD, groups=["member"], first_name="B", last_name="Two"
    )
    su = SignUp.objects.create(slot=slot, user=a, role="operator")
    assert _as(b).get(f"/events/signup/{su.pk}/remove/").status_code == 404


def test_regenerating_the_grid_asks_before_it_deletes_it(event):
    ev = event["event"]
    c = _as(event["officer"])
    before = Slot.objects.filter(position__location__event=ev).count()
    assert before

    r = c.post(
        f"/events/{ev.pk}/slots/generate/",
        {
            "minutes": "30",
            "setup_slots": "1",
            "breakdown_slots": "1",
            "cap_operator": "1",
            "cap_mentor": "0",
            "cap_observer": "0",
        },
    )
    assert r.status_code == 200 and b"Replace the whole grid" in r.content
    assert Slot.objects.filter(position__location__event=ev).count() == before

    c.post(
        f"/events/{ev.pk}/slots/generate/",
        {
            "minutes": "30",
            "setup_slots": "1",
            "breakdown_slots": "1",
            "cap_operator": "1",
            "cap_mentor": "0",
            "cap_observer": "0",
            "confirmed": "yes",
        },
    )
    assert Slot.objects.filter(position__location__event=ev).count() != before


def test_a_bad_generate_form_comes_back_with_what_was_typed(event):
    ev = event["event"]
    r = _as(event["officer"]).post(
        f"/events/{ev.pk}/slots/generate/",
        {
            "minutes": "0",
            "setup_slots": "1",
            "breakdown_slots": "1",
            "cap_operator": "1",
            "cap_mentor": "0",
            "cap_observer": "0",
        },
    )
    assert r.status_code == 200
    assert b"Nothing was generated" in r.content


def test_approving_and_declining_an_agreement_are_separate_forms():
    """Both buttons in one form meant Enter in the reason field fired the first one, which
    approved the agreement and granted station access."""
    advisor = User.objects.create_user(
        "adv@example.org", PASSWORD, groups=["advisor"], first_name="Ad", last_name="Visor"
    )
    mem = User.objects.create_user(
        "mem@example.org", PASSWORD, groups=["member"], first_name="Mo", last_name="Member"
    )
    ct = CredentialType.objects.create(
        key="station_access", label="Station", established_by="agreement"
    )
    t = AgreementTemplate.objects.create(
        key="sa",
        credential=ct,
        title="Station Agreement",
        audience=["student"],
        version=1,
        content_hash="h",
        html="<p>x</p>",
        effective_date="2026-01-01",
        is_current=True,
    )
    SignedAgreement.objects.create(
        user=mem, template=t, credential=ct, signer_name="Mo Member", content_hash="h"
    )

    body = _as(advisor).get("/credentials/approvals/").content.decode()
    # The reason field and the Approve button are no longer in the same form.
    before_reason = body.split('name="reason"')[0]
    assert before_reason.count("</form>") >= 1, "Approve must close before the reason field opens"


def test_the_page_says_nobody_yet_where_it_counts_empty_slots(event):
    """The column was headed "Open", which means "seats free" on the event page and counted
    slots with nobody on them here."""
    body = _as(event["officer"]).get("/events/health/").content.decode()
    assert "Nobody yet" in body


def test_a_flash_message_can_be_reached_and_carries_its_level_as_a_word(event):
    c = _as(event["officer"])
    r = c.post(f"/events/{event['event'].pk}/bulk/", {"action": "close", "slots": []}, follow=True)
    body = r.content.decode()
    assert 'id="messages"' in body and 'tabindex="-1"' in body
    assert '<span class="lvl">' in body


def test_no_page_carries_an_inline_event_handler(event):
    """The CSP allows scripts from this origin and nothing inline, so an onchange attribute is
    dead code that silently does the wrong thing."""
    ev = event["event"]
    slot = Slot.objects.filter(position=event["position"]).first()
    sysadmin = User.objects.create_user(
        "sys@example.org", PASSWORD, first_name="Sys", last_name="Admin", is_superuser=True
    )
    c = _as(sysadmin)
    for url in (
        "/",
        f"/events/{ev.pk}/",
        f"/events/{ev.pk}/slot/{slot.pk}/",
        f"/events/{ev.pk}/manage/",
        "/ops/settings/",
        f"/members/{sysadmin.pk}/",  # your own profile, which /me/ forwards to
    ):
        r = c.get(url)
        assert r.status_code == 200, f"{url} gave {r.status_code}"
        body = r.content.decode()
        for attr in ("onchange=", "onclick=", "onsubmit=", "onload="):
            assert attr not in body, f"{attr} on {url}"


@pytest.mark.django_db
def test_a_refused_page_is_the_clubs_own_page_and_says_what_to_do():
    """NAF, 2026-09-19, after dropping a level on a sysadmin page: "I don't want a Not Found."

    The application answers 404 where a session may not open a page, so that a page nobody may
    see and a page you may not see look alike from outside (§2.1). That is worth keeping; the
    bare server page it used to render is not.
    """
    from django.core.management import call_command

    call_command("club_import")
    sysadmin = User.objects.create_user(
        "sys@example.org", "pw-Testing-123", first_name="Sy", last_name="Sadmin"
    )
    sysadmin.is_superuser = True
    sysadmin.save(update_fields=["is_superuser"])
    c = Client()
    c.force_login(
        sysadmin
    )  # signed in at the club's everyday level, so /ops/settings/ is not theirs
    r = c.get("/ops/settings/")
    assert r.status_code == 404
    body = r.content.decode()
    assert "Page not found" in body and "Go to Home" in body
    assert "Change your level" in body and "Faculty advisor" in body
    assert "<html" in body and "sidenav" in body, "the club's own page, not the server's"


@pytest.mark.django_db
def test_the_footer_credits_the_authoring_club_with_a_link():
    """The advisor, 2026-09-19: the authoring club's name in the credit line should link to its
    own page.

    It is the software's attribution, so it points at the club that wrote it wherever the
    software runs, rather than at the club running this copy.
    """
    from django.core.management import call_command
    from django.test import Client

    from apps.ops.branding import PRODUCT_AUTHOR, PRODUCT_AUTHOR_URL

    call_command("club_import")
    body = Client().get("/accounts/login/").content.decode()
    assert f'free software from <a href="{PRODUCT_AUTHOR_URL}">{PRODUCT_AUTHOR}</a>' in body
