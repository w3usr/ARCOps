"""
One slot at a time, and many at once.

The slot page (`/events/<pk>/slot/<id>/`) is the full record of a slot and every action on it;
the roster opens the same content in a dialog through htmx (`HX-Request`), and each action in the
dialog comes back to it there, with the slot's roster cell for the page behind (#139). Bulk
actions come from the roster's checkboxes: a member signs up for several slots in one role with
one note and gets a per-slot answer; a captain closes, reopens, or cancels several at once.
Nothing here deletes: a slot with history is canceled, never removed (FR-102).
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.ops.audit import record
from apps.ops.config import setting
from apps.ops.templatetags.labels import role_label

from .models import Event, RoleCapacity, SignUp, Slot
from .services.eligibility import can_sign_up
from .services.roster import cell_for
from .services.viability import checkin_window_open, may_control


def _lead(request) -> str:
    return "utc"  # UTC is the roster's axis (functional addendum A12)


def _visible(user, event: Event) -> bool:
    return event.visible_to_members or user.can_captain(event)


def roster_or_slot(request, slot: Slot):
    """Where an action on a slot lands: the roster, or from the roster's dialog (an htmx request)
    the slot again, so the dialog shows what changed and the roster stays where it was (#139)."""
    if request.headers.get("HX-Request"):
        return redirect("slot_detail", pk=slot.event.pk, slot_id=slot.pk)
    return redirect("event_detail", pk=slot.event.pk)


@login_required
@login_required
def slot_detail(request, pk, slot_id):
    event = get_object_or_404(Event, pk=pk)
    if not _visible(request.user, event):
        raise Http404
    slot = get_object_or_404(Slot, pk=slot_id, position__location__event=event, cancelled=False)
    cell, data = cell_for(slot, request.user, _lead(request))
    is_captain = data["is_captain"]
    eligible_roles = []
    if data["published"] and not slot.closed and not cell.mine:
        for role in cell.open_roles:
            ok, _ = can_sign_up(request.user, slot, role)
            if ok:
                eligible_roles.append(role)
    # FR-111: roles the holder could switch to (open seat, eligible); FR-57: full roles they
    # are eligible for, to wait on.
    switch_roles, waitable = [], []
    caps = {c.role: c.capacity for c in slot.capacities.all()}
    if data["published"] and not slot.closed:
        for role in caps:
            ok, _ = can_sign_up(request.user, slot, role)
            if not ok:
                continue
            if cell.mine and role != cell.mine.role and role in cell.open_roles:
                switch_roles.append(role)
            if not cell.mine and role not in cell.open_roles:
                waitable.append(role)
    from .models import EligibilityRule, Waitlist

    my_wait = Waitlist.objects.filter(
        slot=slot, user=request.user, state__in=["pending", "offered"]
    ).first()
    slot_rules = list(EligibilityRule.objects.filter(slot=slot)) if is_captain else []
    ctx = {
        "event": event,
        "slot": slot,
        "cell": cell,
        "row": data["row"],
        "roles": data["roles"],
        "is_captain": is_captain,
        "checkin_open": checkin_window_open(slot, timezone.now()),
        "published": data["published"],
        "locked": event.state == Event.State.LOCKED,
        "eligible_roles": eligible_roles,
        "switch_roles": switch_roles,
        "waitable": waitable,
        "my_wait": my_wait,
        "slot_rules": slot_rules,
        # re-time, split, merge (FR-46, #156): why not, or what follows on to merge with
        "frozen": __import__("apps.events.services.reshape", fromlist=["frozen"]).frozen(slot)
        if is_captain
        else "",
        "next_slot": next_slot(slot) if is_captain else None,
        "slot_minutes": int((slot.end - slot.start).total_seconds() // 60),
        "slot_middle": slot.start + (slot.end - slot.start) / 2,
        "waiting_count": slot.waitlist.filter(state__in=["pending", "offered"]).count()
        if is_captain
        else 0,
        "categories": setting("member_categories", []) or [],
        "ladder": __import__("apps.credentials.services", fromlist=["ladder"]).ladder(),
        "capacities": {c.role: c.capacity for c in slot.capacities.all()},
        "on_air": [s for s in cell.signups],
        "members": User.objects.with_access().order_by("last_name", "first_name")
        if is_captain
        else [],
        "partial": bool(request.headers.get("HX-Request")),
        "roster": data,  # for the roster cell sent back with the dialog
        "day": data["day"],
    }
    template = "events/_slot_body.html" if ctx["partial"] else "events/slot.html"
    response = render(request, template, ctx)
    patch_vary_headers(response, ["HX-Request"])  # one URL, two answers: never cache one for both
    return response


def _captain_slot(request, pk, slot_id):
    event = get_object_or_404(Event, pk=pk)
    if not request.user.can_captain(event):
        raise Http404
    return event, get_object_or_404(
        Slot, pk=slot_id, position__location__event=event, cancelled=False
    )


@login_required
@require_POST
def slot_capacities(request, pk, slot_id):
    """FR-49: seats per role in this slot."""
    event, slot = _captain_slot(request, pk, slot_id)
    seats = {}
    for r in setting("slot_roles", []) or []:
        try:
            seats[r["key"]] = max(0, min(20, int(request.POST.get(f"cap_{r['key']}", "0") or 0)))
        except ValueError:
            continue
    # Fewer seats than people already in the role is refused, and nothing is saved: the people
    # would be left holding seats that no longer exist (SK, 2026-10-16).
    for key, n in seats.items():
        held = slot.signups.filter(role=key).count()
        if n < held:
            messages.error(
                request,
                f"{held} {'person holds' if held == 1 else 'people hold'} {role_label(key)} here; "
                f"remove them first, or keep at least {held} seat{'s' if held != 1 else ''}.",
            )
            return redirect("slot_detail", pk=pk, slot_id=slot_id)
    for key, n in seats.items():
        if n:
            RoleCapacity.objects.update_or_create(slot=slot, role=key, defaults={"capacity": n})
        else:
            RoleCapacity.objects.filter(slot=slot, role=key).delete()
    from .services import waitlist

    for key, n in seats.items():  # a seat added is a place opened (FR-57, #253)
        if n:
            waitlist.on_place_opened(slot, key)
    record(request.user, "slot.capacities", slot)
    messages.success(request, "Seats updated.")
    return redirect("slot_detail", pk=pk, slot_id=slot_id)


@login_required
@require_POST
def slot_control_operator(request, pk, slot_id):
    """FR-63: the captain names the control operator from the people in the slot."""
    event, slot = _captain_slot(request, pk, slot_id)
    uid = request.POST.get("user") or None
    su = slot.signups.select_related("user").filter(user_id=uid).first() if uid else None
    if uid and su is None:
        messages.error(request, "The control operator must be signed up for the slot.")
        return redirect("slot_detail", pk=pk, slot_id=slot_id)
    if su and not may_control(slot, su):  # an unlicensed member cannot be one (SK, 2026-10-15)
        messages.error(
            request,
            "The control operator must hold a valid amateur license and be signed up in an "
            "on-air role.",
        )
        return redirect("slot_detail", pk=pk, slot_id=slot_id)
    slot.control_operator_id = uid
    slot.save(update_fields=["control_operator"])
    record(request.user, "slot.control_operator", slot, after={"user": uid})
    messages.success(
        request, "Control operator set." if uid else "Control operator left to the default rule."
    )
    return redirect("slot_detail", pk=pk, slot_id=slot_id)


@login_required
@require_POST
def slot_assign(request, pk, slot_id):
    """A captain signs a member up on their behalf; the eligibility rules still apply."""
    event, slot = _captain_slot(request, pk, slot_id)
    if event.state not in (Event.State.PUBLISHED, Event.State.LOCKED):  # SK, 2026-10-16
        messages.error(request, "Captains sign people up once the event is published.")
        return redirect("slot_detail", pk=pk, slot_id=slot_id)
    member = get_object_or_404(User, pk=request.POST.get("user"))
    role = request.POST.get("role", "")
    cap = RoleCapacity.objects.filter(slot=slot, role=role).first()
    if not cap or slot.signups.filter(role=role).count() >= cap.capacity:
        messages.error(request, "No seat open in that role.")
        return redirect("slot_detail", pk=pk, slot_id=slot_id)
    ok, reason = can_sign_up(member, slot, role, by_captain=True)
    if not ok:
        messages.error(request, f"{member.short_name} cannot take that role: {reason}.")
        return redirect("slot_detail", pk=pk, slot_id=slot_id)
    su, created = SignUp.objects.get_or_create(
        slot=slot, user=member, defaults={"role": role, "note": ""}
    )
    if created:
        record(request.user, "signup.assigned", su, after={"role": role, "user": member.pk})
        if member != request.user:
            from .services.notify import assigned_by_captain

            assigned_by_captain(request.user, su)  # FR-58
        messages.success(request, f"{member.short_name} signed up as {role_label(role)}.")
    else:
        messages.info(request, f"{member.short_name} already holds this slot.")
    return redirect("slot_detail", pk=pk, slot_id=slot_id)


@login_required
@require_POST
def event_bulk(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not _visible(request.user, event):
        raise Http404
    ids = request.POST.getlist("slots")
    slots = list(
        Slot.objects.filter(pk__in=ids, position__location__event=event, cancelled=False).order_by(
            "start"
        )
    )
    action = request.POST.get("action")
    if not slots:
        messages.error(request, "Tick at least one slot first.")
        return redirect("event_detail", pk=pk)

    if action == "signup":
        role = request.POST.get("role", "")
        note = request.POST.get("note", "")[:500]
        if event.state != Event.State.PUBLISHED:
            refusal = {
                Event.State.DRAFT: "Sign-ups open when the event is published.",
                Event.State.LOCKED: "The roster is locked. To change a sign-up, contact a captain.",
                Event.State.COMPLETED: "This event has finished.",
                Event.State.CANCELLED: "This event was canceled.",
            }[event.state]
            messages.error(request, refusal)
            return redirect("event_detail", pk=pk)
        done, refused = [], []
        for s in slots:
            if s.closed:
                refused.append(f"{s.start:%a %H:%M}Z: closed")
                continue
            cap = RoleCapacity.objects.filter(slot=s, role=role).first()
            if not cap or s.signups.filter(role=role).count() >= cap.capacity:
                refused.append(f"{s.start:%a %H:%M}Z: no {role_label(role)} seat open")
                continue
            if s.signups.filter(user=request.user).exists():
                refused.append(f"{s.start:%a %H:%M}Z: you already hold it")
                continue
            ok, reason = can_sign_up(request.user, s, role)
            if not ok:
                refused.append(f"{s.start:%a %H:%M}Z: {reason}")
                continue
            su = SignUp.objects.create(slot=s, user=request.user, role=role, note=note)
            record(request.user, "signup.created", su, after={"role": role, "bulk": True})
            done.append(s)
        if done:
            messages.success(
                request,
                f"Signed up as {role_label(role)} for {len(done)} slot{'s' if len(done) != 1 else ''}.",
            )
        for r in refused:
            messages.warning(request, "Not taken. " + r)
        return redirect("event_detail", pk=pk)

    if not request.user.can_captain(event):
        raise Http404
    if action in ("close", "reopen"):
        n = Slot.objects.filter(pk__in=[s.pk for s in slots]).update(closed=(action == "close"))
        record(request.user, f"slots.{action}", event, after={"count": n})
        messages.success(
            request,
            f"{n} slot{'s' if n != 1 else ''} {'closed' if action == 'close' else 'reopened'}.",
        )
    elif action == "cancel":
        with_people = [s for s in slots if s.signups.exists()]
        free = [s for s in slots if not s.signups.exists()]
        if request.POST.get("confirmed") != "yes":
            # Canceling cannot be undone, and the control sat between Close and Reopen, which
            # both can. Say what is about to go before anything goes.
            return render(
                request,
                "events/confirm_bulk_cancel.html",
                {"event": event, "free": free, "with_people": with_people},
            )
        n = Slot.objects.filter(pk__in=[s.pk for s in free]).update(cancelled=True)
        record(request.user, "slots.cancel", event, after={"count": n})
        messages.success(request, f"{n} slot{'s' if n != 1 else ''} canceled.")
        if with_people:
            messages.warning(
                request,
                f"{len(with_people)} left alone because people are signed up; remove them first.",
            )
    else:
        raise Http404
    return redirect("event_detail", pk=pk)


@login_required
@require_POST
def signup_no_show(request, signup_id):
    """FR-124: a captain removes (or restores) the credit for a checked-in slot."""
    su = get_object_or_404(SignUp, pk=signup_id)
    event = su.slot.event
    if not request.user.can_captain(event):
        raise Http404
    su.no_show = not su.no_show
    su.save(update_fields=["no_show"])
    record(request.user, "signup.no_show" if su.no_show else "signup.no_show_undone", su)
    messages.success(
        request,
        "Marked as a no-show; no hours credited."
        if su.no_show
        else "No-show undone; hours credited again.",
    )
    return redirect("slot_detail", pk=event.pk, slot_id=su.slot_id)


# ------------------------------------------------ re-time, split, merge (FR-46, #156) ---


def _typed_utc(text):
    """A datetime-local box's text as a UTC time, or None: the forms say UTC."""
    from datetime import UTC

    from django import forms

    try:
        t = forms.DateTimeField().clean(text)
    except forms.ValidationError:
        return None
    return t.replace(tzinfo=UTC) if timezone.is_naive(t) else t


def next_slot(slot: Slot):
    """The live slot of the same position and kind that follows straight on: what merges."""
    return Slot.objects.filter(
        position=slot.position, kind=slot.kind, cancelled=False, start=slot.end
    ).first()


@login_required
@require_POST
def slot_retime(request, pk, slot_id):
    from datetime import timedelta

    from .services import reshape

    event, slot = _captain_slot(request, pk, slot_id)
    start = _typed_utc(request.POST.get("start", ""))
    minutes = request.POST.get("minutes", "")
    why = reshape.frozen(slot)
    if not why and not (start and minutes.isdigit() and int(minutes) <= 720):
        why = "Give a start and a length in minutes."
    if not why:
        end = start + timedelta(minutes=int(minutes))
        why = reshape.misfit(slot, start, end)
    if why:
        messages.error(request, f"The slot was not moved. {why}")
        return roster_or_slot(request, slot)
    told = reshape.retime(request.user, slot, start, end)
    people = (
        f" {told} {'person was' if told == 1 else 'people were'} told and asked to confirm again."
        if told
        else ""
    )
    messages.success(
        request, f"Slot moved to {slot.start:%a %d %b %H:%M}–{slot.end:%H:%M} UTC.{people}"
    )
    return roster_or_slot(request, slot)


@login_required
@require_POST
def slot_split(request, pk, slot_id):
    from .services import reshape

    event, slot = _captain_slot(request, pk, slot_id)
    at = _typed_utc(request.POST.get("at", ""))
    why = reshape.frozen(slot)
    if not why and not at:
        why = "Give the time to split it at."
    if not why and not (slot.start + reshape.SHORTEST <= at <= slot.end - reshape.SHORTEST):
        why = "Each part has to be at least 15 minutes long, inside the slot."
    if why:
        messages.error(request, f"The slot was not split. {why}")
        return roster_or_slot(request, slot)
    reshape.split(request.user, slot, at)
    n = slot.signups.count()
    people = (
        f" The {n} {'person' if n == 1 else 'people'} in it {'is' if n == 1 else 'are'} in both parts."
        if n
        else ""
    )
    messages.success(request, f"Slot split at {at:%H:%M} UTC.{people}")
    return roster_or_slot(request, slot)


@login_required
@require_POST
def slot_merge(request, pk, slot_id):
    from .services import reshape

    event, slot = _captain_slot(request, pk, slot_id)
    other = next_slot(slot)
    why = reshape.frozen(slot)
    if not why and (other is None or str(other.pk) != request.POST.get("with", "")):
        why = "Only the slot that follows straight on, in the same position, can be merged."
    if not why:
        why = reshape.frozen(other)
    if why:
        messages.error(request, f"The slots were not merged. {why}")
        return roster_or_slot(request, slot)
    told = reshape.merge(request.user, slot, other)
    people = (
        f" {told} {'person was' if told == 1 else 'people were'} told and asked to confirm again."
        if told
        else ""
    )
    messages.success(
        request,
        f"Merged: the slot now runs {slot.start:%a %d %b %H:%M}–{slot.end:%H:%M} UTC.{people}",
    )
    return roster_or_slot(request, slot)
