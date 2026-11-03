"""Manage in tabs (#167, SK 2026-11-02): Setup, Slots, Sign-up rules, Contest, Status, each a page
of its own drawn by the server, so a tab can be linked to and works without JavaScript."""

import re

import pytest

from apps.events.models import Event, Slot

from .test_manage import _as, _build

pytestmark = pytest.mark.django_db

TABS = ["setup", "slots", "rules", "contest", "status"]
HOLDS = {  # each tab's sections, by the heading ids the page has always had
    "setup": ["det", "per", "loc", "cap"],
    "slots": ["gen", "add-slot", "lim"],
    "rules": ["who", "opn"],
    "contest": ["con"],
    "status": ["st", "ann", "more", "dz"],
}


def _ids(body):
    return set(re.findall(r'<h[23] id="([a-z-]+)"', body))


def test_each_tab_is_a_page_holding_its_own_sections(officer):
    c = _as(officer)
    ev = _build(c)
    every = {i for ids in HOLDS.values() for i in ids}
    for tab in TABS:
        r = c.get(f"/events/{ev.pk}/manage/{tab}/")
        body = r.content.decode()
        assert r.status_code == 200, tab
        assert _ids(body) & every == set(HOLDS[tab]), tab
        nav = body.split('<nav class="tabs"', 1)[1].split("</nav>", 1)[0]
        links = re.findall(r'<a href="/events/\d+/manage/([a-z]+)/"', nav)
        assert links == TABS
        assert nav.count('aria-current="page"') == 1
        assert f'href="/events/{ev.pk}/manage/{tab}/" aria-current="page"' in nav
    assert c.get(f"/events/{ev.pk}/manage/nonsense/").status_code == 404


def test_manage_opens_on_the_step_to_do_next_or_setup(officer):
    c = _as(officer)
    ev = _build(c)  # periods, positions and slots: the next step is to publish
    assert c.get(f"/events/{ev.pk}/manage/")["Location"] == f"/events/{ev.pk}/manage/status/"
    Slot.objects.filter(position__location__event=ev).delete()
    assert c.get(f"/events/{ev.pk}/manage/")["Location"] == f"/events/{ev.pk}/manage/slots/"
    ev.locations.all().delete()
    assert c.get(f"/events/{ev.pk}/manage/")["Location"] == f"/events/{ev.pk}/manage/setup/"
    Event.objects.filter(pk=ev.pk).update(state=Event.State.PUBLISHED)
    assert c.get(f"/events/{ev.pk}/manage/")["Location"] == f"/events/{ev.pk}/manage/setup/"


def test_the_steps_link_to_their_tabs(officer):
    c = _as(officer)
    ev = _build(c)
    body = c.get(f"/events/{ev.pk}/manage/setup/").content.decode()
    steps = body.split('<ol class="steps">', 1)[1].split("</ol>", 1)[0]
    assert re.findall(r'href="/events/\d+/manage/([a-z]+)/#([a-z-]+)"', steps) == [
        ("setup", "per"),
        ("setup", "loc"),
        ("slots", "gen"),
        ("status", "st"),
    ]


def test_a_save_returns_to_its_tab(officer):
    c = _as(officer)
    ev = _build(c)
    base = f"/events/{ev.pk}"
    saves = {
        "setup": (f"{base}/periods/add/", {"start": "2026-07-01T18:00", "end": "2026-07-01T20:00"}),
        "slots": (f"{base}/limits/", {"max_hours_per_day": "6", "day_basis": "utc"}),
        "rules": (f"{base}/eligibility/", {}),
        "contest": (f"{base}/contest/", {"calendar_ref": "12"}),
        "status": (f"{base}/state/", {"what": "lock"}),
    }
    for tab, (url, data) in saves.items():
        r = c.post(url, data)
        assert r.status_code == 302 and r["Location"] == f"{base}/manage/{tab}/", (tab, url)


def test_a_refused_form_comes_back_on_its_own_tab(officer):
    c = _as(officer)
    ev = _build(c)
    r = c.post(f"/events/{ev.pk}/slots/generate/", {"minutes": "0", "mode": "fill"})
    body = r.content.decode()
    assert r.status_code == 200 and "Nothing was generated" in body
    assert f'href="/events/{ev.pk}/manage/slots/" aria-current="page"' in body
    r = c.post(f"/events/{ev.pk}/manage/setup/", {"title": ""})
    body = r.content.decode()
    assert (
        r.status_code == 200 and f'href="/events/{ev.pk}/manage/setup/" aria-current="page"' in body
    )
