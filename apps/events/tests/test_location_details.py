"""A location's own directions, know-before-you-go text and viability rule (FR-51, #249), and
setup and breakdown slots of their own length (FR-47, #250). SK, 2026-11-11."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.comms.models import Outbox
from apps.credentials.models import CredentialType
from apps.events.models import SignUp, Slot
from apps.events.services import notify
from apps.events.services.viability import rule_for

from .test_manage import _as
from .test_manage_gaps import GEN, _future, _live

pytestmark = pytest.mark.django_db


def test_a_location_is_edited_on_a_page_with_its_directions_notes_and_rule(officer):
    for key, label in (("station_access", "Station access"), ("site_lead", "Site lead")):
        CredentialType.objects.get_or_create(key=key, defaults={"label": label})
    c = _as(officer)
    ev = _future(c)
    loc = ev.locations.get()
    url = f"/events/{ev.pk}/locations/{loc.pk}/edit/"
    page = c.get(url).content.decode()
    assert '<h1 id="dialog-title">Edit Shack</h1>' in page and "tinymce" in page
    for name in ("directions_html", "kbyg_html", "own_rule", "needs"):
        assert f'name="{name}"' in page, name
    assert "Site lead" in page
    # the step links to the page; it is not one of the dialog's forms
    step = c.get(f"/events/{ev.pk}/manage/locations/").content.decode()
    assert f'<a class="button secondary small" href="{url}">' in step
    slot = _live(ev).first()
    default = rule_for(slot)
    form = {
        "name": "Shack",
        "address": "",
        "directions_html": "<p>Third floor, <script>x</script>past the lab.</p>",
        "kbyg_html": "<p>Bring boots.</p>",
    }
    r = c.post(url, form)
    assert r["Location"] == f"/events/{ev.pk}/manage/locations/"
    loc.refresh_from_db()
    assert "past the lab" in loc.directions_html and "<script>" not in loc.directions_html
    assert loc.kbyg_html == "<p>Bring boots.</p>" and loc.viability_rule is None
    assert rule_for(slot) == default  # no rule of its own: the club's
    c.post(url, form | {"own_rule": "on", "needs": ["site_lead"]})
    slot.refresh_from_db()
    assert rule_for(slot) == [{"credential": "site_lead"}]
    c.post(url, form | {"own_rule": "on"})  # its own rule, and it needs nothing
    slot = Slot.objects.get(pk=slot.pk)
    assert rule_for(slot) == []
    page = c.get(url).content.decode()
    assert 'name="own_rule"' in page and "checked" in page.split('name="own_rule"', 1)[1][:80]
    c.post(url, form)
    assert rule_for(Slot.objects.get(pk=slot.pk)) == default


def test_directions_reach_the_event_page_and_the_reminder(officer, member):
    c = _as(officer)
    ev = _future(c)
    loc = ev.locations.get()
    loc.address, loc.directions_html = "12 Elm Street", "<p>Blue door at the back.</p>"
    loc.kbyg_html = "<p>Mind the dog.</p>"
    loc.save()
    c.post(f"/events/{ev.pk}/publish/", {})
    m = _as(member)
    page = m.get(f"/events/{ev.pk}/").content.decode()
    place = page.split('<h2 id="where">Getting there</h2>', 1)[1].split("</section>", 1)[0]
    assert "Blue door at the back." in place and "Mind the dog." in place
    # a private residence's directions go where its address goes
    loc.is_private_residence = True
    loc.save()
    page = m.get(f"/events/{ev.pk}/").content.decode()
    assert "Blue door" not in page and "Getting there" not in page
    su = SignUp.objects.create(slot=_live(ev).first(), user=member, role="operator")
    assert "Blue door" in m.get(f"/events/{ev.pk}/").content.decode()
    notify.send_one_reminder(su, timezone.now())
    body = Outbox.objects.filter(user=member, category="reminder").get().body_html
    assert "Shack, 12 Elm Street" in body
    assert "<h2>Getting to Shack</h2><p>Blue door at the back.</p>" in body
    assert "Mind the dog." in body


def test_setup_and_breakdown_slots_have_their_own_length(officer):
    c = _as(officer)
    ev = _future(c)
    Slot.objects.filter(position__location__event=ev).delete()
    page = c.get(f"/events/{ev.pk}/slots/generate/").content.decode()
    assert 'name="setup_minutes"' in page and 'name="breakdown_minutes"' in page
    c.post(
        f"/events/{ev.pk}/slots/generate/",
        GEN
        | {
            "setup_slots": "1",
            "setup_minutes": "120",
            "breakdown_slots": "2",
            "breakdown_minutes": "30",
        },
    )
    start, end = ev.starts_at(), ev.ends_at()
    setup = Slot.objects.get(kind="setup")
    assert (setup.start, setup.end) == (start - timedelta(hours=2), start)
    down = list(Slot.objects.filter(kind="breakdown").order_by("start"))
    assert [(s.start, s.end) for s in down] == [
        (end, end + timedelta(minutes=30)),
        (end + timedelta(minutes=30), end + timedelta(hours=1)),
    ]
    assert _live(ev).filter(kind="operating").count() == 4
    # left out, each is as long as an operating slot, as before
    Slot.objects.filter(position__location__event=ev).delete()
    c.post(f"/events/{ev.pk}/slots/generate/", GEN | {"setup_slots": "1"})
    setup = Slot.objects.get(kind="setup")
    assert setup.end - setup.start == timedelta(hours=1)
