"""Manage's small forms open in a dialog (#168, SK 2026-11-02): each a page of its own, which htmx
fetches into the dialog; a refusal comes back there with what was typed, a save sends the page
behind to its step (#172). The event's details are read on Details and edited on a page."""

import re

import pytest

from apps.accounts.models import User
from apps.events.models import Event, OperatingPeriod, Slot

from .test_manage import _as, _build

pytestmark = pytest.mark.django_db

HX = {"HTTP_HX_REQUEST": "true"}


def _forms(ev, loc_pk):
    base = f"/events/{ev.pk}"
    run, mult = ev.locations.get().positions.order_by("order")
    return {
        "periods/add": ("periods", "Add an operating period"),
        f"periods/{ev.periods.get().pk}/edit": ("periods", "Edit the operating period"),
        "locations/add": ("locations", "Add a location"),
        f"locations/{loc_pk}/positions/add": ("locations", "Add a position at Club station"),
        f"positions/{run.pk}/edit": ("locations", "Rename Run"),
        f"positions/{mult.pk}/edit": ("locations", "Rename Mult"),
        "captains/add": ("publish", "Appoint a captain"),
        "slots/generate": ("slots", "Generate slots"),
        "slots/add": ("slots", "Add a slot"),
        "openings/add": ("rules", "Add an opening"),
    }, base


def test_each_form_is_a_page_and_a_dialog(officer):
    c = _as(officer)
    ev = _build(c)
    forms, base = _forms(ev, ev.locations.get().pk)
    for path, (tab, heading) in forms.items():
        url = f"{base}/{path}/"
        page = c.get(url).content.decode()
        assert f'<h1 id="dialog-title">{heading}</h1>' in page and 'class="crumbs"' in page, url
        assert f'<form method="post" action="{url}" class="stack">' in page, (
            url
        )  # no htmx on the page
        assert f'href="{base}/manage/{tab}/">Manage</a>' in page, url
        part = c.get(url, **HX)
        body = part.content.decode()
        assert "<html" not in body and 'class="crumbs"' not in body, url
        assert f'hx-post="{url}"' in body and "data-close" in body, url
        assert "HX-Request" in part["Vary"]


def test_each_step_opens_its_forms_from_buttons_in_one_dialog(officer):
    c = _as(officer)
    ev = _build(c)
    forms, base = _forms(ev, ev.locations.get().pk)
    seen = set()
    for tab in ("periods", "locations", "slots", "rules", "publish"):
        body = c.get(f"{base}/manage/{tab}/").content.decode()
        assert body.count('<dialog id="manage-dialog"') == 1
        for href, target in re.findall(
            r'<a class="button secondary(?: small)?" href="([^"]+)" hx-get="\1" hx-target="([^"]+)" data-dialog>',
            body,
        ):
            assert target == "#manage-dialog-body"
            seen.add(href.removeprefix(base + "/").rstrip("/"))
    assert seen == set(forms)
    assert (
        "<form"
        not in c.get(f"{base}/manage/periods/")
        .content.decode()
        .split('aria-labelledby="per"', 1)[1]
        .split("</ul>", 1)[1]
        .split("</section>", 1)[0]
    )


def test_a_save_from_the_dialog_sends_the_page_to_its_step(officer):
    c = _as(officer)
    ev = _build(c)
    url = f"/events/{ev.pk}/periods/add/"
    data = {"start": "2026-07-01T18:00", "end": "2026-07-01T20:00"}
    r = c.post(url, data, **HX)
    assert r.status_code == 200 and r["HX-Redirect"] == f"/events/{ev.pk}/manage/periods/"
    assert ev.periods.count() == 2
    r = c.post(url, {"start": "2026-07-02T18:00", "end": "2026-07-02T20:00"})
    assert r.status_code == 302 and r["Location"] == f"/events/{ev.pk}/manage/periods/"


def test_a_refusal_comes_back_in_the_dialog_with_what_was_typed(officer):
    c = _as(officer)
    ev = _build(c)
    r = c.post(
        f"/events/{ev.pk}/periods/add/",
        {"start": "2026-07-01T18:00", "end": "2026-07-01T17:00"},
        **HX,
    )
    body = r.content.decode()
    assert r.status_code == 200 and "HX-Redirect" not in r and "<html" not in body
    assert (
        '<span class="lvl">Problem:</span>' in body and "The end must come after the start." in body
    )
    assert 'value="2026-07-01T18:00"' in body and ev.periods.count() == 1
    r = c.post(f"/events/{ev.pk}/slots/add/", {"start": "2026-06-27T20:30", "minutes": "60"}, **HX)
    assert "No slot was added; correct the fields marked below." in r.content.decode()


def test_the_details_are_read_on_setup_and_edited_on_their_page(officer):
    c = _as(officer)
    ev = _build(c)
    setup = c.get(f"/events/{ev.pk}/manage/details/").content.decode()
    det = setup.split('<h2 id="det">Details</h2>', 1)[1].split("</section>", 1)[0]
    assert "<dt>Title</dt><dd>Field Day</dd>" in det and "<form" not in det
    assert re.search(rf'href="/events/{ev.pk}/details/">(<svg.*?</svg>)?Edit details</a>', det)
    page = c.get(f"/events/{ev.pk}/details/").content.decode()
    assert '<h1 id="dialog-title">Edit details</h1>' in page and "tinymce" in page
    form = {"title": "Field Day 2026", "type": "contest", "reminder_hours_before": "24"}
    r = c.post(f"/events/{ev.pk}/details/", form)
    ev.refresh_from_db()
    assert r["Location"] == f"/events/{ev.pk}/manage/details/" and ev.title == "Field Day 2026"
    r = c.post(f"/events/{ev.pk}/details/", form | {"title": ""})
    assert r.status_code == 200 and "Problem:" in r.content.decode()


def test_a_location_and_a_position_are_edited_after_they_are_added(officer):
    """FR-51: a typo in a location's name or address, or a position's name, is put right on
    Locations, not in the admin (SK, 2026-11-11). Each change is in the audit log."""
    from apps.ops.models import AuditLog

    c = _as(officer)
    ev = _build(c)
    loc = ev.locations.get()
    run = loc.positions.get(name="Run")
    slots = run.slots.count()
    page = c.get(f"/events/{ev.pk}/locations/{loc.pk}/edit/").content.decode()
    assert 'value="Club station"' in page and 'name="position"' not in page
    r = c.post(
        f"/events/{ev.pk}/locations/{loc.pk}/edit/",
        {"name": "Field site ", "address": "Pavilion 2"},
        **HX,
    )
    assert r["HX-Redirect"] == f"/events/{ev.pk}/manage/locations/"
    loc.refresh_from_db()
    assert (loc.name, loc.address, loc.is_club_station) == ("Field site", "Pavilion 2", False)
    r = c.post(f"/events/{ev.pk}/positions/{run.pk}/edit/", {"name": ""})
    assert r.status_code == 200 and "Problem:" in r.content.decode()
    r = c.post(f"/events/{ev.pk}/positions/{run.pk}/edit/", {"name": "Run 2"})
    assert r["Location"] == f"/events/{ev.pk}/manage/locations/"
    run.refresh_from_db()
    assert run.name == "Run 2" and run.slots.count() == slots  # its slots stay with it
    rows = AuditLog.objects.filter(action="event.edited", subject_id=str(ev.pk))
    assert rows.filter(before__location="Club station", after__location="Field site").exists()
    assert rows.filter(before__position="Run", after__position="Run 2").exists()
    other = Event.objects.create(title="Other")  # never another event's location
    assert c.get(f"/events/{other.pk}/locations/{loc.pk}/edit/").status_code == 404


def test_the_generator_says_what_it_will_make_before_making_it(officer):
    c = _as(officer)
    ev = _build(c)
    Slot.objects.filter(position__location__event=ev).delete()
    page = c.get(f"/events/{ev.pk}/slots/generate/").content.decode()
    line = page.split('id="gen-preview"', 1)[1].split("</div>", 1)[0]
    assert (
        "<strong>52 slots</strong> <span>26 per position × 2 positions, including a setup and "
        "a breakdown slot each.</span>" in line
    )
    assert f'hx-post="/events/{ev.pk}/slots/preview/"' in page
    r = c.post(
        f"/events/{ev.pk}/slots/preview/",
        {
            "minutes": "120",
            "setup_slots": "0",
            "breakdown_slots": "0",
            "cap_operator": "1",
            "cap_mentor": "0",
        },
        **HX,
    )
    assert r.content.decode().strip() == (
        "<strong>24 slots</strong> <span>12 per position × 2 positions.</span>"
    )
    assert not Slot.objects.filter(position__location__event=ev).exists()


def test_replacing_from_the_dialog_asks_there_and_never_loses_the_grid_to_bad_hours(officer):
    c = _as(officer)
    ev = _build(c)
    before = Slot.objects.filter(position__location__event=ev).count()
    form = {
        "minutes": "60",
        "setup_slots": "0",
        "breakdown_slots": "0",
        "cap_operator": "1",
        "cap_mentor": "0",
        "mode": "replace",
    }
    r = c.post(f"/events/{ev.pk}/slots/generate/", form, **HX)
    body = r.content.decode()
    assert "<html" not in body and '<h1 id="dialog-title">Replace the whole grid?</h1>' in body
    assert (
        'hx-post="/events/' in body
        and "Keep the grid" in body.split("Replace the grid</button>")[0]
    )
    # Hours outside every period are refused where they are chosen, the on-air hours (#247),
    # so the generator cannot be asked for them; nothing is deleted before the confirmation.
    assert Slot.objects.filter(position__location__event=ev).count() == before
    r = c.post(f"/events/{ev.pk}/slots/generate/", form | {"confirmed": "yes"}, **HX)
    assert r["HX-Redirect"] == f"/events/{ev.pk}/"


def test_a_member_captain_cannot_open_the_captain_form(officer):
    c = _as(officer)
    ev = _build(c)
    mem = User.objects.create_user(
        "m@example.org", "pw-Testing-123", groups=["member"], first_name="M", last_name="M"
    )
    c.post(f"/events/{ev.pk}/captains/add/", {"user": mem.pk})
    assert _as(mem).get(f"/events/{ev.pk}/captains/add/").status_code == 404
    assert (
        "Appoint captain" not in _as(mem).get(f"/events/{ev.pk}/manage/publish/").content.decode()
    )
    assert (
        Event.objects.filter(pk=ev.pk).exists()
        and OperatingPeriod.objects.filter(event=ev).exists()
    )


def test_the_generator_groups_its_fields_and_sizes_its_numbers(officer):
    """NN/g and GOV.UK, 2026-11-03 (SK): related fields grouped under a legend, one under another;
    whole numbers in small boxes with the numeric keypad and no spinner; the hours optional."""
    from apps.events.models import SignUp

    c = _as(officer)
    ev = _build(c)
    page = c.get(f"/events/{ev.pk}/slots/generate/").content.decode()
    legends = re.findall(r'<fieldset class="group"><legend>([^<]+)</legend>', page)
    assert legends == ["Slots", "Setup and breakdown", "Seats in each slot"]
    seats = page.split("<legend>Seats in each slot</legend>", 1)[1].split("</fieldset>", 1)[0]
    assert re.findall(r"<label[^>]*>([^<]+)</label>", seats) == ["Operator", "Mentor"]
    assert 'type="number"' not in page and page.count('inputmode="numeric"') == 7
    assert "Hours to operate each day" not in page  # a range a day in the on-air hours (#248)
    assert "Setup slots before" in page  # nobody has signed up: Regenerate slots may use it
    s = Slot.objects.filter(position__location__event=ev, kind="operating").first()
    SignUp.objects.create(slot=s, user=officer, role="operator")
    page = c.get(f"/events/{ev.pk}/slots/generate/").content.decode()
    assert "Setup slots before" not in page and "Breakdown slots after" not in page
    assert page.count('inputmode="numeric"') == 3
    r = c.post(  # the line, from the same fields: no setup or breakdown to send
        f"/events/{ev.pk}/slots/preview/",
        {"minutes": "60", "cap_operator": "1", "cap_mentor": "0"},
        HTTP_HX_REQUEST="true",
    )
    assert (
        r.content.decode()
        == "<strong>Every hour already has a slot; nothing would be added.</strong>"
    )


def test_a_slot_by_hand_groups_its_seats(officer):
    c = _as(officer)
    ev = _build(c)
    page = c.get(f"/events/{ev.pk}/slots/add/").content.decode()
    seats = page.split("<legend>Seats in this slot</legend>", 1)[1].split("</fieldset>", 1)[0]
    assert re.findall(r"<label[^>]*>([^<]+)</label>", seats) == ["Operator", "Mentor"]
    assert 'type="number"' not in page
