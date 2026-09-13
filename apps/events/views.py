"""Event list, roster, sign-up, cancel, role change, check-in, my schedule."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ops.audit import record
from apps.ops.config import setting

from .models import Event, RoleCapacity, SignUp, Slot
from .services.eligibility import can_sign_up
from .services.slots import health
from .services.viability import checkin_window_open, evaluate, would_break


def _visible(user, event: Event) -> bool:
    return event.visible_to_members or user.can_captain(event)


@login_required
def event_list(request):
    now = timezone.now()
    events = Event.objects.prefetch_related("periods")
    if not request.user.is_officer:
        events = events.filter(state__in=["published", "locked", "completed"]) | events.filter(
            captaincies__user=request.user
        )
    upcoming, past = [], []
    for e in events.distinct():
        (upcoming if (e.ends_at() or now) >= now else past).append(e)
    upcoming.sort(key=lambda e: e.starts_at() or now)
    return render(request, "events/list.html", {"upcoming": upcoming, "past": past[:20]})


@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not _visible(request.user, event):
        raise Http404
    is_captain = request.user.can_captain(event)
    slots = (
        Slot.objects.filter(position__location__event=event, cancelled=False)
        .select_related("position", "position__location", "control_operator")
        .prefetch_related(
            "signups__user", "signups__user__license", "signups__responsible_adults", "capacities"
        )
        .order_by("start", "position__location__order", "position__order")
    )
    my_slot_ids = set(
        SignUp.objects.filter(user=request.user, slot__in=slots).values_list("slot_id", flat=True)
    )
    rows = []
    for s in slots:
        st = evaluate(s)
        caps = {c.role: c.capacity for c in s.capacities.all()}
        taken = {}
        for su in s.signups.all():
            taken[su.role] = taken.get(su.role, 0) + 1
        open_roles = [r for r, c in caps.items() if taken.get(r, 0) < c]
        rows.append(
            {
                "slot": s,
                "status": st,
                "signups": list(s.signups.all()),
                "open_roles": open_roles,
                "mine": s.pk in my_slot_ids,
            }
        )
    return render(
        request,
        "events/detail.html",
        {
            "event": event,
            "rows": rows,
            "health": health(event),
            "is_captain": is_captain,
            "roles": setting("slot_roles", []),
        },
    )


@login_required
@require_POST
def sign_up(request, slot_id):
    slot = get_object_or_404(Slot, pk=slot_id, cancelled=False, closed=False)
    event = slot.event
    if not _visible(request.user, event) or event.state != Event.State.PUBLISHED:
        raise Http404
    role = request.POST.get("role", "")
    cap = RoleCapacity.objects.filter(slot=slot, role=role).first()
    if not cap:
        messages.error(request, "That role is not open in this slot.")
        return redirect("event_detail", pk=event.pk)
    if slot.signups.filter(role=role).count() >= cap.capacity:
        messages.error(request, "That role is full.")
        return redirect("event_detail", pk=event.pk)
    allowed, reason = can_sign_up(request.user, slot, role)
    if not allowed:
        messages.error(request, f"You cannot take that role: {reason}.")
        return redirect("event_detail", pk=event.pk)
    su, created = SignUp.objects.get_or_create(
        slot=slot,
        user=request.user,
        defaults={"role": role, "note": request.POST.get("note", "")[:500]},
    )
    if not created:
        messages.info(request, "You already hold this slot.")
    else:
        record(request.user, "signup.created", su, after={"role": role})
        messages.success(request, f"Signed up as {role} for {slot.start:%a %d %b %H:%M}Z.")
    return redirect("event_detail", pk=event.pk)


@login_required
@require_POST
def cancel_signup(request, signup_id):
    su = get_object_or_404(SignUp, pk=signup_id)
    slot = su.slot
    if su.user != request.user and not request.user.can_captain(slot.event):
        raise Http404
    if request.POST.get("confirmed") != "yes":
        broken = would_break(slot, su)
        if broken:
            messages.warning(
                request,
                f"If you cancel, this slot becomes {broken.label.lower()}: {'; '.join(broken.reasons)}. Cancel anyway?",
            )
            return render(request, "events/confirm_cancel.html", {"signup": su, "broken": broken})
    record(request.user, "signup.cancelled", su, before={"role": su.role, "user": su.user_id})
    su.delete()
    messages.success(request, "Sign-up cancelled.")
    return redirect("event_detail", pk=slot.event.pk)


@login_required
@require_POST
def check_in(request, signup_id):
    su = get_object_or_404(SignUp, pk=signup_id)
    now = timezone.now()
    if su.user != request.user and not request.user.can_captain(su.slot.event):
        raise Http404
    if not checkin_window_open(su.slot, now):
        messages.error(request, "Check-in opens 30 minutes before the slot.")
        return redirect("my_schedule")
    su.checked_in_at = now
    su.checked_in_by = request.user
    su.save(update_fields=["checked_in_at", "checked_in_by"])
    record(request.user, "signup.checked_in", su)
    messages.success(request, "Checked in. Have a good shift.")
    return redirect("my_schedule")


@login_required
def my_schedule(request):
    now = timezone.now()
    signups = (
        SignUp.objects.filter(user=request.user, slot__cancelled=False)
        .select_related(
            "slot", "slot__position", "slot__position__location", "slot__position__location__event"
        )
        .order_by("slot__start")
    )
    upcoming = [s for s in signups if s.slot.end >= now]
    return render(
        request,
        "events/my_schedule.html",
        {
            "upcoming": upcoming,
            "now": now,
            "ready": [
                s for s in upcoming if checkin_window_open(s.slot, now) and not s.checked_in_at
            ],
        },
    )


@login_required
@require_POST
def confirm_signup(request, signup_id):
    su = get_object_or_404(SignUp, pk=signup_id, user=request.user)
    su.confirmed_at = timezone.now()
    su.save(update_fields=["confirmed_at"])
    messages.success(request, "Confirmed. Thank you.")
    return redirect("my_schedule")


@login_required
@require_POST
def publish(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not request.user.can_captain(event):
        raise Http404
    if event.state == Event.State.DRAFT:
        event.state = Event.State.PUBLISHED
        event.published_at = timezone.now()
        event.published_by = request.user
        event.save()
        record(request.user, "event.published", event)
        messages.success(request, "Published. Members can see it now.")
    elif (
        event.state == Event.State.PUBLISHED
        and not SignUp.objects.filter(slot__position__location__event=event).exists()
    ):
        event.state = Event.State.DRAFT
        event.save(update_fields=["state"])
        record(request.user, "event.unpublished", event)
        messages.info(request, "Back to draft.")
    else:
        messages.error(
            request, "A published event with sign-ups can only be cancelled, not unpublished."
        )
    return redirect("event_detail", pk=pk)


def roster_counts(event):  # used by templates via view context if needed
    return (
        SignUp.objects.filter(slot__position__location__event=event)
        .values("role")
        .annotate(n=Count("id"))
    )
