"""Manage as steps under one progress bar (#172, SK 2026-11-03): Details, Operating periods,
Locations, Slots and Publish, then the optional Sign-up rules and Contest details, each a page of
its own drawn by the server, so a step can be linked to and works without JavaScript."""

import re

import pytest

from apps.events.models import Event, Slot

from .test_manage import _as, _build

pytestmark = pytest.mark.django_db

STEPS = ["details", "periods", "locations", "slots", "publish"]
HOLDS = {  # each step's sections, by the heading ids the page has always had
    "details": ["det"],
    "periods": ["per"],
    "locations": ["loc"],
    "slots": ["gen", "lim"],
    "publish": ["pub", "cap", "more", "dz"],  # a draft; published, Status and Announce for Publish
    "rules": ["who", "opn"],
    "contest": ["con"],
}


def _ids(body):
    return set(re.findall(r'<h[23] id="([a-z-]+)"', body))


def _bar(body):
    return body.split('<nav class="stages"', 1)[1].split("</nav>", 1)[0]


def test_each_step_is_a_page_holding_its_own_sections(officer):
    c = _as(officer)
    ev = _build(c)
    every = {i for ids in HOLDS.values() for i in ids} | {"st", "ann"}
    for step in HOLDS:
        r = c.get(f"/events/{ev.pk}/manage/{step}/")
        body = r.content.decode()
        assert r.status_code == 200, step
        assert _ids(body) & every == set(HOLDS[step]), step
        bar = _bar(body)
        ol = bar.split("<ol>", 1)[1].split("</ol>", 1)[0]
        assert re.findall(r'href="/events/\d+/manage/([a-z]+)/"', ol) == STEPS
        assert bar.count('aria-current="step"') == 1
        assert f'href="/events/{ev.pk}/manage/{step}/" aria-current="step"' in bar
    assert c.get(f"/events/{ev.pk}/manage/nonsense/").status_code == 404


def test_a_published_event_has_status_and_announce_on_publish(officer):
    c = _as(officer)
    ev = _build(c)
    Event.objects.filter(pk=ev.pk).update(state=Event.State.PUBLISHED)
    body = c.get(f"/events/{ev.pk}/manage/publish/").content.decode()
    assert {"st", "ann", "cap", "more", "dz"} <= _ids(body) and "pub" not in _ids(body)
    assert '<span class="st">Published</span>' in _bar(body)


def test_manage_opens_on_the_first_step_not_done_or_publish(officer):
    c = _as(officer)
    ev = _build(c)  # periods, positions and slots: the next step is to publish
    land = lambda: c.get(f"/events/{ev.pk}/manage/")["Location"]  # noqa: E731
    assert land() == f"/events/{ev.pk}/manage/publish/"
    Slot.objects.filter(position__location__event=ev).delete()
    assert land() == f"/events/{ev.pk}/manage/slots/"
    ev.locations.all().delete()
    assert land() == f"/events/{ev.pk}/manage/locations/"
    ev.periods.all().delete()
    assert land() == f"/events/{ev.pk}/manage/periods/"


def test_the_old_tabs_redirect_to_their_steps(officer):
    c = _as(officer)
    ev = _build(c)
    for old, new in (("setup", "details"), ("status", "publish")):
        r = c.get(f"/events/{ev.pk}/manage/{old}/")
        assert r.status_code == 301 and r["Location"] == f"/events/{ev.pk}/manage/{new}/"


def test_slots_is_not_a_link_until_there_is_a_period_and_a_position(officer):
    c = _as(officer)
    ev = _build(c)
    ev.locations.all().delete()
    body = c.get(f"/events/{ev.pk}/manage/locations/").content.decode()
    assert "/manage/slots/" not in _bar(body)
    assert '<span class="st">After Locations</span>' in _bar(body)
    assert '<span class="st">Next</span>' in _bar(body)  # Locations itself
    assert "Continue to" not in body
    assert c.get(f"/events/{ev.pk}/manage/slots/").status_code == 404


def test_the_foot_walks_the_numbered_steps(officer):
    c = _as(officer)
    ev = _build(c)
    body = c.get(f"/events/{ev.pk}/manage/locations/").content.decode()
    foot = body.split('class="stage-foot"', 1)[1].split("</p>", 1)[0]
    assert "Back to Operating periods" in foot and "Continue to Slots" in foot
    body = c.get(f"/events/{ev.pk}/manage/details/").content.decode()
    assert "Back to" not in body and "Continue to Operating periods" in body


def test_a_display_only_event_has_three_steps(officer):
    c = _as(officer)
    ev = _build(c)
    Event.objects.filter(pk=ev.pk).update(display_only=True, type="net")
    bar = _bar(c.get(f"/events/{ev.pk}/manage/details/").content.decode())
    assert re.findall(r'href="/events/\d+/manage/([a-z]+)/"', bar) == [
        "details",
        "periods",
        "publish",
    ]


def test_contest_details_only_for_a_contest_or_one_that_has_them(officer):
    c = _as(officer)
    ev = _build(c)  # a contest
    assert "/manage/contest/" in _bar(c.get(f"/events/{ev.pk}/manage/details/").content.decode())
    Event.objects.filter(pk=ev.pk).update(type="training")
    assert "/manage/contest/" not in _bar(
        c.get(f"/events/{ev.pk}/manage/details/").content.decode()
    )
    Event.objects.filter(pk=ev.pk).update(calendar_ref=12)
    assert "/manage/contest/" in _bar(c.get(f"/events/{ev.pk}/manage/details/").content.decode())


def test_a_save_returns_to_its_step(officer):
    c = _as(officer)
    ev = _build(c)
    base = f"/events/{ev.pk}"
    saves = {
        "periods": (
            f"{base}/periods/add/",
            {"start": "2026-07-01T18:00", "end": "2026-07-01T20:00"},
        ),
        "slots": (f"{base}/limits/", {"max_hours_per_day": "6", "day_basis": "utc"}),
        "rules": (f"{base}/eligibility/", {}),
        "contest": (f"{base}/contest/", {"calendar_ref": "12"}),
        "publish": (f"{base}/publish/", {"from": "manage"}),
    }
    for step, (url, data) in saves.items():
        r = c.post(url, data)
        assert r.status_code == 302 and r["Location"] == f"{base}/manage/{step}/", (step, url)
    r = c.post(f"{base}/state/", {"what": "lock"})
    assert r["Location"] == f"{base}/manage/publish/"
    # From the event page's banner, Publish still goes back to the event.
    Event.objects.filter(pk=ev.pk).update(state=Event.State.DRAFT)
    assert c.post(f"{base}/publish/")["Location"] == f"{base}/"
