"""Gaps in managing an event, found by reading the flow and closed at SK's word, 2026-11-11:
a private residence's address (FR-51), editing a period, overlapping periods, a slot with no
seat, completing by one click, removing a position, and deleting a draft never published."""

import pytest

from apps.accounts.models import User
from apps.events.models import Event, RoleCapacity, SignUp, Slot
from apps.ops.models import AuditLog

from .test_manage import _as

pytestmark = pytest.mark.django_db

SEATS = {"cap_operator": "2", "cap_mentor": "1", "cap_observer": "0"}
GEN = {"minutes": "60", "setup_slots": "0", "breakdown_slots": "0", **SEATS}


def _future(c, title="Sweepstakes"):
    """A draft a year ahead: one four-hour period, one location, one position, four slots."""
    c.post("/events/new/", {"title": title, "type": "contest"})
    ev = Event.objects.get(title=title)
    c.post(
        f"/events/{ev.pk}/periods/add/", {"start": "2027-06-26T18:00", "end": "2027-06-26T22:00"}
    )
    c.post(f"/events/{ev.pk}/locations/add/", {"name": "Shack", "position": "Run"})
    c.post(f"/events/{ev.pk}/slots/generate/", GEN)
    return ev


def _live(ev):
    return Slot.objects.filter(position__location__event=ev, cancelled=False)


def test_a_private_residence_shows_its_address_only_to_those_signed_up_there(officer, member):
    """FR-51: "A location that is a private residence shows its address only to people signed up
    there and to captains, officers, and sysadmins"."""
    c = _as(officer)
    ev = _future(c)
    loc = ev.locations.get()
    page = c.get(f"/events/{ev.pk}/locations/{loc.pk}/edit/").content.decode()
    assert 'name="is_private_residence"' in page
    c.post(
        f"/events/{ev.pk}/locations/{loc.pk}/edit/",
        {"name": "Shack", "address": "12 Elm Street", "is_private_residence": "on"},
    )
    loc.refresh_from_db()
    assert loc.is_private_residence and loc.address == "12 Elm Street"
    c.post(f"/events/{ev.pk}/publish/", {})
    assert "12 Elm Street" in c.get(f"/events/{ev.pk}/").content.decode()  # a captain
    m = _as(member)
    assert "12 Elm Street" not in m.get(f"/events/{ev.pk}/").content.decode()
    SignUp.objects.create(slot=_live(ev).first(), user=member, role="operator")
    assert "12 Elm Street" in m.get(f"/events/{ev.pk}/").content.decode()
    c.post(  # not private: everybody who sees the event sees where it is
        f"/events/{ev.pk}/locations/{loc.pk}/edit/", {"name": "Shack", "address": "12 Elm Street"}
    )
    SignUp.objects.all().delete()
    assert "12 Elm Street" in m.get(f"/events/{ev.pk}/").content.decode()


def test_a_period_is_edited_and_keeps_or_cancels_its_slots(officer, member):
    c = _as(officer)
    ev = _future(c)
    p = ev.periods.get()
    url = f"/events/{ev.pk}/periods/{p.pk}/edit/"
    page = c.get(url).content.decode()
    assert 'value="2027-06-26T18:00"' in page and 'value="2027-06-26T22:00"' in page
    assert f'href="{url}"' in c.get(f"/events/{ev.pk}/manage/periods/").content.decode()
    # longer: every slot stays, and the new hour is empty until it is filled
    c.post(url, {"start": "2027-06-26T18:00", "end": "2027-06-26T23:00"})
    p.refresh_from_db()
    assert p.end.hour == 23 and _live(ev).count() == 4
    c.post(f"/events/{ev.pk}/slots/generate/", GEN | {"mode": "fill"})
    assert _live(ev).count() == 5
    # shorter, with someone in the hour that would go: refused, nothing changes
    last = _live(ev).order_by("start").last()
    su = SignUp.objects.create(slot=last, user=member, role="operator")
    r = c.post(url, {"start": "2027-06-26T18:00", "end": "2027-06-26T22:00"})
    p.refresh_from_db()
    assert r.status_code == 200 and "1 person is signed up" in r.content.decode()
    assert p.end.hour == 23 and _live(ev).count() == 5
    # shorter, nobody there: the slots left outside are canceled, and it is in the audit log
    su.delete()
    r = c.post(url, {"start": "2027-06-26T19:00", "end": "2027-06-26T22:00"}, follow=True)
    assert _live(ev).count() == 3
    assert "2 slots left outside it were canceled" in r.content.decode()
    row = (
        AuditLog.objects.filter(action="event.edited", subject_id=str(ev.pk)).order_by("pk").last()
    )
    assert row.after["slots canceled"] == 2 and "18:00" in row.before["period"]


def test_a_period_that_overlaps_another_is_refused(officer):
    c = _as(officer)
    ev = _future(c)
    r = c.post(
        f"/events/{ev.pk}/periods/add/", {"start": "2027-06-26T21:00", "end": "2027-06-27T02:00"}
    )
    assert r.status_code == 200 and ev.periods.count() == 1
    assert "overlaps the period Sat 26 Jun 18:00 to Sat 26 Jun 22:00 UTC" in r.content.decode()
    # one that starts as the other ends is a second period, as a split contest has
    c.post(
        f"/events/{ev.pk}/periods/add/", {"start": "2027-06-26T22:00", "end": "2027-06-27T02:00"}
    )
    assert ev.periods.count() == 2
    second = ev.periods.order_by("start").last()
    r = c.post(  # editing one into the other is refused the same way
        f"/events/{ev.pk}/periods/{second.pk}/edit/",
        {"start": "2027-06-26T21:00", "end": "2027-06-27T02:00"},
    )
    assert r.status_code == 200 and "overlaps the period" in r.content.decode()


def test_slots_are_not_made_with_no_seat_at_all(officer):
    c = _as(officer)
    ev = _future(c)
    Slot.objects.filter(position__location__event=ev).delete()
    none = {"cap_operator": "0", "cap_mentor": "0", "cap_observer": "0"}
    r = c.post(f"/events/{ev.pk}/slots/generate/", GEN | none)
    assert r.status_code == 200 and not Slot.objects.filter(position__location__event=ev).exists()
    assert "Give at least one seat" in r.content.decode()
    pos = ev.locations.get().positions.get()
    by_hand = {
        "position": pos.pk,
        "start": "2027-06-26T18:00",
        "minutes": "60",
        "kind": "operating",
    }
    r = c.post(f"/events/{ev.pk}/slots/add/", by_hand | none)
    assert "Give at least one seat" in r.content.decode() and not Slot.objects.exists()
    c.post(f"/events/{ev.pk}/slots/add/", by_hand | SEATS)
    assert RoleCapacity.objects.filter(slot__position=pos).count() == 2


def test_mark_completed_asks_first(officer):
    c = _as(officer)
    ev = _future(c)
    c.post(f"/events/{ev.pk}/publish/", {})
    page = c.get(f"/events/{ev.pk}/manage/publish/").content.decode()
    dialog = page.split('<dialog id="complete-dlg"', 1)[1].split("</dialog>", 1)[0]
    assert "It cannot be undone" in dialog and 'name="what" value="complete"' in dialog
    assert 'name="what" value="complete"' not in page.replace(dialog, "")  # only inside it
    assert 'commandfor="complete-dlg" command="show-modal"' in page


def test_removing_a_position_asks_first_and_is_refused_with_people_in_it(officer, member):
    c = _as(officer)
    ev = _future(c)
    loc = ev.locations.get()
    c.post(f"/events/{ev.pk}/locations/{loc.pk}/positions/add/", {"name": "Mult"})
    c.post(f"/events/{ev.pk}/slots/generate/", GEN | {"mode": "fill"})
    run, mult = loc.positions.order_by("order")
    su = SignUp.objects.create(slot=mult.slots.first(), user=member, role="operator")
    page = c.get(f"/events/{ev.pk}/manage/locations/").content.decode()
    asks = page.split(f'<dialog id="pos-rm-{run.pk}"', 1)[1].split("</dialog>", 1)[0]
    assert "Its 4 slots go with it" in asks and "Remove the position" in asks
    refuses = page.split(f'<dialog id="pos-rm-{mult.pk}"', 1)[1].split("</dialog>", 1)[0]
    assert "1 person is signed up" in refuses and "<form" not in refuses
    c.post(f"/events/{ev.pk}/positions/{mult.pk}/delete/")
    assert loc.positions.count() == 2  # the server refuses the same
    su.delete()
    c.post(f"/events/{ev.pk}/positions/{mult.pk}/delete/")
    assert list(loc.positions.all()) == [run]
    row = (
        AuditLog.objects.filter(action="event.edited", subject_id=str(ev.pk)).order_by("pk").last()
    )
    assert row.before == {"position": "Mult", "location": "Shack", "slots": 4}
    # the last position of a location takes the location with it, and the dialog says so
    page = c.get(f"/events/{ev.pk}/manage/locations/").content.decode()
    assert "the location goes with it" in page.split(f'<dialog id="pos-rm-{run.pk}"', 1)[1]
    c.post(f"/events/{ev.pk}/publish/", {})
    r = c.post(f"/events/{ev.pk}/positions/{run.pk}/delete/", follow=True)
    assert "A published event keeps at least one position" in r.content.decode()
    c.post(f"/events/{ev.pk}/publish/", {})  # back to draft
    c.post(f"/events/{ev.pk}/positions/{run.pk}/delete/")
    assert not ev.locations.exists()


def test_a_draft_never_published_is_deleted_and_any_other_event_is_not(officer, member):
    c = _as(officer)
    ev = _future(c)
    page = c.get(f"/events/{ev.pk}/manage/publish/").content.decode()
    assert "Delete this draft" in page
    appointed = User.objects.get(pk=member.pk)
    ev.captaincies.create(user=appointed)  # a member made captain runs it, and does not delete it
    assert _as(appointed).post(f"/events/{ev.pk}/delete/", {"confirm": "yes"}).status_code == 404
    c.post(f"/events/{ev.pk}/delete/", {})  # the confirmation's tick box is the server's too
    assert Event.objects.filter(pk=ev.pk).exists()
    r = c.post(f"/events/{ev.pk}/delete/", {"confirm": "yes"}, follow=True)
    assert not Event.objects.filter(pk=ev.pk).exists() and not Slot.objects.exists()
    assert "Draft “Sweepstakes” deleted." in r.content.decode()
    assert AuditLog.objects.filter(action="event.deleted", before__title="Sweepstakes").exists()
    # once it has been published, even if taken back to draft, it is canceled, never deleted
    ev = _future(c, "Field Day")
    c.post(f"/events/{ev.pk}/publish/", {})
    c.post(f"/events/{ev.pk}/publish/", {})
    ev.refresh_from_db()
    assert ev.state == "draft"
    assert "Delete this draft" not in c.get(f"/events/{ev.pk}/manage/publish/").content.decode()
    c.post(f"/events/{ev.pk}/delete/", {"confirm": "yes"})
    assert Event.objects.filter(pk=ev.pk).exists()
