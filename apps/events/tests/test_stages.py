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


def test_a_new_event_is_the_details_step_and_goes_on_to_periods(officer):
    """#173: no first period on the create form; creating lands on Operating periods."""
    c = _as(officer)
    body = c.get("/events/new/").content.decode()
    bar = _bar(body)
    assert "href=" not in bar  # nothing to open before the event exists
    assert '<span class="cell" aria-current="step">' in bar and bar.count("After Details") == 4
    assert "Create draft and continue" in body and "Starts (UTC)" not in body
    r = c.post("/events/new/", {"title": "Net night", "type": "net"}, follow=True)
    ev = Event.objects.get(title="Net night")
    assert r.redirect_chain[-1][0] == f"/events/{ev.pk}/manage/periods/"
    assert "Draft created." in r.content.decode() and not ev.periods.exists()


def test_duplicating_lands_on_operating_periods(officer):
    c = _as(officer)
    ev = _build(c)
    r = c.post(f"/events/{ev.pk}/duplicate/")
    copy = Event.objects.exclude(pk=ev.pk).get()
    assert r["Location"] == f"/events/{copy.pk}/manage/periods/"


def test_know_before_you_go_is_its_own_step(officer):
    """#174: the outline from the start, saved sanitized, outline only until a section is written;
    not on Details, and not for a display-only event."""
    c = _as(officer)
    ev = _build(c)
    url = f"/events/{ev.pk}/manage/kbyg/"
    body = c.get(url).content.decode()
    assert "Where and when" in body and "tinymce" in body
    assert "Know before you go</a>: outline only" in _bar(body)
    assert (
        "Know before you go"
        not in c.get(f"/events/{ev.pk}/manage/details/")
        .content.decode()
        .split('<h2 id="det">', 1)[1]
        .split("</section>", 1)[0]
    )
    html = "<h2>Where and when</h2><p>Room 101<script>alert(1)</script></p>"
    r = c.post(url, {"kbyg_html": html})
    assert r.status_code == 302 and r["Location"] == url
    ev.refresh_from_db()
    assert "Room 101" in ev.kbyg_html and "<script" not in ev.kbyg_html
    assert "Know before you go</a>: written" in _bar(c.get(url).content.decode())
    Event.objects.filter(pk=ev.pk).update(display_only=True)
    assert "/manage/kbyg/" not in _bar(c.get(f"/events/{ev.pk}/manage/details/").content.decode())


def test_a_drafts_publish_step_checks_every_step_first(officer):
    """#175: a row per step, each linking to its step; a required step not done says so, and
    publishing stays allowed. Once published, no check."""
    c = _as(officer)
    ev = _build(c)
    url = f"/events/{ev.pk}/manage/publish/"
    body = c.get(url).content.decode()
    dl = body.split('<dl class="dl summary">', 1)[1].split("</dl>", 1)[0]
    names = re.findall(r"<dt>([^<]+)</dt>", dl)
    assert names == [
        "Details",
        "Operating periods",
        "Locations",
        "Slots",
        "Sign-up rules",
        "Contest details",
        "Know before you go",
        "Captains",
    ]
    links = re.findall(r'href="/events/\d+/manage/([a-z]+)/(?:#cap)?">Change', dl)
    assert links == [
        "details",
        "periods",
        "locations",
        "slots",
        "rules",
        "contest",
        "kbyg",
        "publish",
    ]
    assert "Field Day, Contest" in dl and "1 period, " in dl and "Club station: Run, Mult" in dl
    assert "Not done yet" not in dl
    Slot.objects.filter(position__location__event=ev).delete()
    dl = c.get(url).content.decode().split('<dl class="dl summary">', 1)[1]
    assert '<dt>Slots</dt><dd class="missing"><span>Not done yet</span>' in dl
    page = c.get(url).content.decode()  # A17 (SK, 2026-11-10): a line in place of Publish
    assert (
        "Not ready to publish: Slots is not done yet." in page and ">Publish</button>" not in page
    )
    Event.objects.filter(pk=ev.pk).update(state=Event.State.PUBLISHED)
    assert 'class="dl summary"' not in c.get(url).content.decode()


def test_a_steps_own_forms_save_in_place(officer):
    """#177: the listed forms carry the in-place attributes; an htmx save is a redirect htmx
    follows to the step (not an HX-Redirect), and the step's messages come inside the swap."""
    c = _as(officer)
    ev = _build(c)
    base = f"/events/{ev.pk}"
    marked = {
        "periods": 1,  # Remove on the period
        "locations": 2,  # Remove on each position
        "slots": 2,  # Add range (#247, ranges only since #248), Save limits
        "rules": 1,  # Save who may sign up (no opening yet)
        "contest": 1,
        "publish": 0,  # a draft: Publish is a page change; Remove on a lone captain is not offered
    }
    for step, n in marked.items():
        body = c.get(f"{base}/manage/{step}/").content.decode()
        assert body.count("data-in-place") == n, step
    r = c.post(
        f"{base}/limits/", {"max_hours_per_day": "6", "day_basis": "utc"}, HTTP_HX_REQUEST="true"
    )
    assert (
        r.status_code == 302 and r["Location"] == f"{base}/manage/slots/" and "HX-Redirect" not in r
    )
    body = c.get(r["Location"]).content.decode()
    stage = body.split('id="stage-body">', 1)[1]
    assert 'id="messages"' in stage and 'id="stages"' in body
    Event.objects.filter(pk=ev.pk).update(state=Event.State.PUBLISHED)
    assert (
        c.get(f"{base}/manage/publish/").content.decode().count("data-in-place") == 1
    )  # Lock, Complete
