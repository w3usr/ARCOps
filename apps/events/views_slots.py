"""
One slot at a time, and many at once.

The slot page (`/events/<pk>/slot/<id>/`) is the full record of a slot and every action on it;
the roster opens the same content in a dialog (`?partial=1`) when JavaScript is present. Bulk
actions come from the roster's checkboxes: a member signs up for several slots in one role with
one note and gets a per-slot answer; a captain closes, reopens, or cancels several at once.
Nothing here deletes: a slot with history is cancelled, never removed (FR-102).
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import AccessLevel, User
from apps.ops.audit import record
from apps.ops.config import setting

from .models import Event, RoleCapacity, SignUp, Slot
from .services.eligibility import can_sign_up
from .services.roster import cell_for
from .services.viability import checkin_window_open


def _lead(request) -> str:
    return request.session.get("roster_tz", "local")


def _visible(user, event: Event) -> bool:
    return event.visible_to_members or user.can_captain(event)


@login_required
def roster_tz(request, pk):
    """Swap which zone leads on the roster; remembered for the session."""
    choice = request.GET.get("tz", "local")
    request.session["roster_tz"] = "utc" if choice == "utc" else "local"
    return redirect("event_detail", pk=pk)


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
        "waiting_count": slot.waitlist.filter(state__in=["pending", "offered"]).count()
        if is_captain
        else 0,
        "categories": setting("member_categories", []) or [],
        "ladder": __import__("apps.credentials.services", fromlist=["ladder"]).ladder(),
        "capacities": {c.role: c.capacity for c in slot.capacities.all()},
        "on_air": [s for s in cell.signups],
        "members": User.objects.exclude(access_level=AccessLevel.NONE).order_by(
            "last_name", "first_name"
        )
        if is_captain
        else [],
        "partial": request.GET.get("partial") == "1",
    }
    template = "events/_slot_body.html" if ctx["partial"] else "events/slot.html"
    return render(request, template, ctx)


def _captain_slot(request, pk, slot_id):
    event = get_object_or_404(Event, pk=pk)
    if not request.user.can_captain(event):
        raise Http404
    return event, get_object_or_404(Slot, pk=slot_id, position__location__event=event)


@login_required
@require_POST
def slot_capacities(request, pk, slot_id):
    """FR-49: seats per role in this slot."""
    event, slot = _captain_slot(request, pk, slot_id)
    for r in setting("slot_roles", []) or []:
        key = r["key"]
        try:
            n = max(0, min(20, int(request.POST.get(f"cap_{key}", "0") or 0)))
        except ValueError:
            continue
        if n:
            RoleCapacity.objects.update_or_create(slot=slot, role=key, defaults={"capacity": n})
        else:
            RoleCapacity.objects.filter(slot=slot, role=key).delete()
    record(request.user, "slot.capacities", slot)
    messages.success(request, "Seats updated.")
    return redirect("slot_detail", pk=pk, slot_id=slot_id)


@login_required
@require_POST
def slot_control_operator(request, pk, slot_id):
    """FR-63: the captain names the control operator from the people in the slot."""
    event, slot = _captain_slot(request, pk, slot_id)
    uid = request.POST.get("user") or None
    if uid and not slot.signups.filter(user_id=uid).exists():
        messages.error(request, "The control operator must be signed up for the slot.")
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
    member = get_object_or_404(User, pk=request.POST.get("user"))
    role = request.POST.get("role", "")
    cap = RoleCapacity.objects.filter(slot=slot, role=role).first()
    if not cap or slot.signups.filter(role=role).count() >= cap.capacity:
        messages.error(request, "No seat open in that role.")
        return redirect("slot_detail", pk=pk, slot_id=slot_id)
    ok, reason = can_sign_up(member, slot, role)
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
        messages.success(request, f"{member.short_name} signed up as {role}.")
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
            messages.error(request, "Sign-ups open when the event is published.")
            return redirect("event_detail", pk=pk)
        done, refused = [], []
        for s in slots:
            if s.closed:
                refused.append(f"{s.start:%a %H:%M}Z: closed")
                continue
            cap = RoleCapacity.objects.filter(slot=s, role=role).first()
            if not cap or s.signups.filter(role=role).count() >= cap.capacity:
                refused.append(f"{s.start:%a %H:%M}Z: no {role} seat open")
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
                request, f"Signed up as {role} for {len(done)} slot{'s' if len(done) != 1 else ''}."
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
        n = Slot.objects.filter(pk__in=[s.pk for s in free]).update(cancelled=True)
        record(request.user, "slots.cancel", event, after={"count": n})
        messages.success(request, f"{n} slot{'s' if n != 1 else ''} cancelled.")
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
