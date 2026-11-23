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

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.accounts.pick import find_redirect, matches
from apps.credentials.models import CredentialType
from apps.credentials.services import ladder
from apps.ops import when
from apps.ops.audit import record
from apps.ops.config import setting
from apps.ops.templatetags.labels import role_label

from .models import EligibilityRule, Event, RoleCapacity, SignUp, Slot, Waitlist
from .services import reshape, waitlist
from .services.adults import name_guardians_on_slot
from .services.eligibility import can_sign_up
from .services.notify import assigned_by_captain
from .services.roster import cell_for
from .services.viability import checkin_window_open, may_control
from .views_rules import captained_event, event_rule, shown


def _visible(user, event: Event) -> bool:
    return event.visible_to_members or user.can_captain(event)


def back_to_slot(request, pk, slot_id):
    """The slot again, with Manage this slot still open when the action came from inside it (its
    forms post manage=1; private tracker 280)."""
    url = reverse("slot_detail", args=[pk, slot_id])
    return redirect(f"{url}?manage=1" if request.POST.get("manage") else url)


def roster_or_slot(request, slot: Slot):
    """Where an action on a slot lands: the roster, or from the roster's dialog (an htmx request)
    the slot again, so the dialog shows what changed and the roster stays where it was (#139)."""
    if request.headers.get("HX-Request"):
        return back_to_slot(request, slot.event.pk, slot.pk)
    return redirect("event_detail", pk=slot.event.pk)


@login_required
def slot_detail(request, pk, slot_id):
    event = get_object_or_404(Event, pk=pk)
    if not _visible(request.user, event):
        raise Http404
    slot = get_object_or_404(Slot, pk=slot_id, position__location__event=event, cancelled=False)
    cell, data = cell_for(slot, request.user)
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
    my_wait = Waitlist.objects.filter(
        slot=slot, user=request.user, state__in=["pending", "offered"]
    ).first()
    slot_rules = list(EligibilityRule.objects.filter(slot=slot)) if is_captain else []
    # The override starts from the rule the event applies to each role, the club's where the
    # event has none (#277): each role's choice carries it, and the first is drawn filled in.
    override = []
    if is_captain:
        for r in data["roles"]:
            rule = shown(event_rule(event, r["key"]))
            override.append(
                {"key": r["key"], "label": r["label"], "rule": rule, "json": json.dumps(rule)}
            )
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
        "override": override,
        "override_credentials": list(
            CredentialType.objects.exclude(key="amateur_license").order_by("label")
        )
        if is_captain
        else [],
        # re-time, split, merge (FR-46, #156): why not, or what follows on to merge with
        "frozen": reshape.frozen(slot) if is_captain else "",
        "next_slot": next_slot(slot) if is_captain else None,
        "slot_minutes": int((slot.end - slot.start).total_seconds() // 60),
        "slot_middle": slot.start + (slot.end - slot.start) / 2,
        "waiting_count": slot.waitlist.filter(state__in=["pending", "offered"]).count()
        if is_captain
        else 0,
        "categories": setting("member_categories", []) or [],
        "ladder": ladder(),
        "capacities": caps,
        "on_air": [s for s in cell.signups],
        **(_assign_pick(request, slot, data["roles"]) if is_captain else {}),
        "partial": bool(request.headers.get("HX-Request")),
        "manage_open": request.GET.get("manage") == "1",
        "roster": data,  # for the roster cell sent back with the dialog
        "day": data["day"],
    }
    template = "events/_slot_body.html" if ctx["partial"] else "events/slot.html"
    response = render(request, template, ctx)
    patch_vary_headers(response, ["HX-Request"])  # one URL, two answers: never cache one for both
    return response


def _assign_pick(request, slot, roles):
    """Sign someone up: the role first, then whoever matches what was typed and may take that
    role here, leaving out the people already in the slot (private tracker 281; SK, 2026-11-16)."""
    keys = [r["key"] for r in roles]
    role = request.GET.get("role") if request.GET.get("role") in keys else (keys[0] if keys else "")
    q = request.GET.get("q", "").strip()
    found, more = matches(
        User.objects.with_access().exclude(signups__slot=slot),
        q,
        keep=lambda m: can_sign_up(m, slot, role, by_captain=True)[0],
    )
    return {
        "assign_role": role,
        "assign_q": q,
        "assign_found": found,
        "assign_more": more,
        "assign_id": f"assign-{slot.pk}",
        "assign_include": f"#assign-role-{slot.pk}",
    }


def _captain_slot(request, pk, slot_id):
    event = captained_event(request, pk)
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
    refused = seats_refused(slot, seats)
    if refused:
        messages.error(request, refused[0].upper() + refused[1:] + ".")
        return back_to_slot(request, pk, slot_id)
    set_seats(request.user, slot, seats)
    messages.success(request, "Seats updated.")
    return back_to_slot(request, pk, slot_id)


def seats_refused(slot, seats: dict[str, int]) -> str:
    """Why these seats cannot be set, or "". Fewer seats than people already in the role is
    refused: they would be left holding seats that no longer exist (SK, 2026-10-16)."""
    for key, n in seats.items():
        held = slot.signups.filter(role=key).count()
        if n < held:
            return (
                f"{held} {'person holds' if held == 1 else 'people hold'} {role_label(key)} here; "
                f"remove them first, or keep at least {held} seat{'s' if held != 1 else ''}"
            )
    return ""


def set_seats(user, slot, seats: dict[str, int]) -> None:
    """FR-49: the slot's seats per role, for the roles in `seats`; a seat added is a place
    opened, offered to the waitlist (FR-57, #253). Shared by Save seats and Change seats (282)."""
    for key, n in seats.items():
        if n:
            RoleCapacity.objects.update_or_create(slot=slot, role=key, defaults={"capacity": n})
        else:
            RoleCapacity.objects.filter(slot=slot, role=key).delete()
    for key, n in seats.items():
        if n:  # after the save: a change undone must not have offered anyone a place
            transaction.on_commit(lambda key=key: waitlist.on_place_opened(slot, key))
    record(user, "slot.capacities", slot, after=seats)


@login_required
@require_POST
def slot_control_operator(request, pk, slot_id):
    """FR-63: the captain names the control operator from the people in the slot."""
    event, slot = _captain_slot(request, pk, slot_id)
    uid = request.POST.get("user") or None
    su = slot.signups.select_related("user").filter(user_id=uid).first() if uid else None
    if uid and su is None:
        messages.error(request, "The control operator must be signed up for the slot.")
        return back_to_slot(request, pk, slot_id)
    if su and not may_control(slot, su):  # an unlicensed member cannot be one (SK, 2026-10-15)
        messages.error(
            request,
            "The control operator must hold a valid amateur license and be signed up in an "
            "on-air role.",
        )
        return back_to_slot(request, pk, slot_id)
    slot.control_operator_id = uid
    slot.save(update_fields=["control_operator"])
    record(request.user, "slot.control_operator", slot, after={"user": uid})
    messages.success(
        request, "Control operator set." if uid else "Control operator left to the default rule."
    )
    return back_to_slot(request, pk, slot_id)


@login_required
@require_POST
def slot_assign(request, pk, slot_id):
    """A captain signs a member up on their behalf; the eligibility rules still apply."""
    event, slot = _captain_slot(request, pk, slot_id)
    if event.state not in (Event.State.PUBLISHED, Event.State.LOCKED):  # SK, 2026-10-16
        messages.error(request, "Captains sign people up once the event is published.")
        return back_to_slot(request, pk, slot_id)
    if request.POST.get("find"):  # with script off: list who matches (private tracker 281)
        return find_redirect(request, reverse("slot_detail", args=[pk, slot_id]), "role", "manage")
    if not request.POST.get("user"):
        messages.error(request, "Type part of a name or callsign, then choose who.")
        return back_to_slot(request, pk, slot_id)
    member = get_object_or_404(User, pk=request.POST.get("user"))
    role = request.POST.get("role", "")
    cap = RoleCapacity.objects.filter(slot=slot, role=role).first()
    if not cap or slot.signups.filter(role=role).count() >= cap.capacity:
        messages.error(request, "No seat open in that role.")
        return back_to_slot(request, pk, slot_id)
    ok, reason = can_sign_up(member, slot, role, by_captain=True)
    if not ok:
        messages.error(request, f"{member.short_name} cannot take that role: {reason}.")
        return back_to_slot(request, pk, slot_id)
    su, created = SignUp.objects.get_or_create(
        slot=slot, user=member, defaults={"role": role, "note": ""}
    )
    if created:
        record(request.user, "signup.assigned", su, after={"role": role, "user": member.pk})
        name_guardians_on_slot(request.user, su)  # A40
        if member != request.user:
            assigned_by_captain(request.user, su)  # FR-58
        messages.success(request, f"{member.short_name} signed up as {role_label(role)}.")
    else:
        messages.info(request, f"{member.short_name} already holds this slot.")
    return back_to_slot(request, pk, slot_id)


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
                refused.append(f"{when.local(s.start)}: closed")
                continue
            if not waitlist.seats_open(s, role):
                refused.append(f"{when.local(s.start)}: no {role_label(role)} seat open")
                continue
            if s.signups.filter(user=request.user).exists():
                refused.append(f"{when.local(s.start)}: you already hold it")
                continue
            ok, reason = can_sign_up(request.user, s, role)
            if not ok:
                refused.append(f"{when.local(s.start)}: {reason}")
                continue
            su = SignUp.objects.create(slot=s, user=request.user, role=role, note=note)
            record(request.user, "signup.created", su, after={"role": role, "bulk": True})
            name_guardians_on_slot(request.user, su)  # A40
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
    if action == "seats":
        return _bulk_seats(request, event, slots)
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


SEAT_OPS = [("keep", "Leave as is"), ("set", "Set to"), ("add", "Add"), ("remove", "Remove")]


def _bulk_seats(request, event, slots):
    """Change seats on the ticked slots (private tracker 282; NAF, 2026-11-12; SK, 2026-11-16:
    set, add or remove N per role). Three passes over one page: choose, review what it will do
    and what it refuses, then apply. A slot that would leave people holding seats that no longer
    exist is refused on its own, as Save seats refuses it; every other slot is changed."""
    roles = setting("slot_roles", []) or []
    chosen = {}
    for r in roles:
        op = request.POST.get(f"op_{r['key']}", "keep")
        try:
            n = max(0, min(20, int(request.POST.get(f"n_{r['key']}") or 0)))
        except ValueError:
            n = 0
        if op in ("set", "add", "remove"):
            chosen[r["key"]] = (op, n)
    plan, refused = [], []
    for s in slots:
        now = {c.role: c.capacity for c in s.capacities.all()}
        seats = {}
        for key, (op, n) in chosen.items():
            cur = now.get(key, 0)
            new = {"set": n, "add": cur + n, "remove": cur - n}[op]
            seats[key] = max(0, min(20, new))
        seats = {k: v for k, v in seats.items() if v != now.get(k, 0)}
        why = seats_refused(s, seats)
        if why:
            refused.append(f"{when.local(s.start)}, {s.position.name}: {why}")
        elif seats:
            plan.append((s, seats))
    step = request.POST.get("step", "")
    if step == "apply" and chosen:
        with transaction.atomic():  # every slot or none: a retry after a failure must not add twice
            for s, seats in plan:
                set_seats(request.user, s, seats)
        n = len(plan)
        messages.success(request, f"Seats changed on {n} slot{'s' if n != 1 else ''}.")
        for r in refused:
            messages.warning(request, "Not changed. " + r)
        return redirect("event_detail", pk=event.pk)
    return render(
        request,
        "events/confirm_bulk_seats.html",
        {
            "event": event,
            "slots": slots,
            "roles": [
                {
                    **r,
                    "op": chosen.get(r["key"], ("keep", 0))[0],
                    "n": chosen.get(r["key"], ("", ""))[1],
                }
                for r in roles
            ],
            "ops": SEAT_OPS,
            "review": step == "review" and bool(chosen),
            "plan": plan,
            "refused": refused,
        },
    )


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


def _typed_utc(text, data, event):
    """A time box's text as (a UTC time or None, why not): ISO 8601 with the browser's offset, or
    without the page's script the viewer's wall clock (A38; when.parse_box). `why` is said only
    for a time the clocks skip or repeat; anything else unreadable is None."""
    from apps.ops.when import Unreadable, parse_box

    try:
        return parse_box(text), ""
    except Unreadable as exc:
        return None, str(exc) if "clocks" in str(exc) else ""


def next_slot(slot: Slot):
    """The live slot of the same position and kind that follows straight on: what merges."""
    return Slot.objects.filter(
        position=slot.position, kind=slot.kind, cancelled=False, start=slot.end
    ).first()


@login_required
@require_POST
def slot_retime(request, pk, slot_id):
    event, slot = _captain_slot(request, pk, slot_id)
    start, unreadable = _typed_utc(request.POST.get("start", ""), request.POST, event)
    minutes = request.POST.get("minutes", "")
    why = reshape.frozen(slot) or unreadable
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
        request, f"Slot moved to {when.local_span(slot.start, slot.end, year=True)}.{people}"
    )
    return roster_or_slot(request, slot)


@login_required
@require_POST
def slot_split(request, pk, slot_id):
    event, slot = _captain_slot(request, pk, slot_id)
    at, unreadable = _typed_utc(request.POST.get("at", ""), request.POST, event)
    why = reshape.frozen(slot) or unreadable
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
    messages.success(request, f"Slot split at {when.local(at, year=True)}.{people}")
    return roster_or_slot(request, slot)


@login_required
@require_POST
def slot_merge(request, pk, slot_id):
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
        f"Merged: the slot now runs {when.local_span(slot.start, slot.end, year=True)}.{people}",
    )
    return roster_or_slot(request, slot)
