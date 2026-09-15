"""Event list, roster, sign-up, cancel, role change, check-in, my schedule."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ops.audit import record

from .models import Event, RoleCapacity, SignUp, Slot
from .services.eligibility import can_sign_up
from .services.roster import build as build_roster
from .services.slots import health
from .services.viability import checkin_window_open, would_break


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
    upcoming, past, regular = [], [], []
    for e in events.distinct():
        if e.display_only:
            regular.append(e)  # FR-45: on the calendar, no roster
        else:
            (upcoming if (e.ends_at() or now) >= now else past).append(e)
    upcoming.sort(key=lambda e: e.starts_at() or now)
    return render(
        request,
        "events/list.html",
        {"upcoming": upcoming, "past": past[:20], "regular": regular},
    )


@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not _visible(request.user, event):
        raise Http404
    lead = request.session.get("roster_tz", "local")
    roster = build_roster(event, request.user, lead, filter=request.GET.get("filter", ""))
    return render(
        request,
        "events/detail.html",
        {
            "event": event,
            "roster": roster,
            "health": health(event) if roster["is_captain"] else None,
            "is_captain": roster["is_captain"],
            "roles": roster["roles"],
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
        messages.error(request, "That role is full. You can join the waitlist from the slot.")
        return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)
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
    if slot.event.state == Event.State.LOCKED and not request.user.can_captain(slot.event):
        messages.error(request, "The roster is locked; ask a captain to change your sign-up.")
        return redirect("event_detail", pk=slot.event.pk)  # FR-44
    if request.POST.get("confirmed") != "yes":
        broken = would_break(slot, su)
        if broken:
            messages.warning(
                request,
                f"If you cancel, this slot becomes {broken.label.lower()}: {'; '.join(broken.reasons)}. Cancel anyway?",
            )
            return render(request, "events/confirm_cancel.html", {"signup": su, "broken": broken})
    from .services import notify

    broken = would_break(slot, su)
    record(request.user, "signup.cancelled", su, before={"role": su.role, "user": su.user_id})
    if su.user == request.user:
        notify.member_cancelled(request.user, su, broken)  # FR-56: the captains always hear
    else:
        notify.removed_by_captain(request.user, su, request.POST.get("reason", "")[:300])  # FR-58
    role = su.role
    su.delete()
    from .services import waitlist

    waitlist.on_place_opened(slot, role)  # FR-57
    messages.success(request, "Sign-up cancelled.")
    return redirect("event_detail", pk=slot.event.pk)


def confirm_by_token(request, token):
    """FR-72, FR-100: the one-click confirm link in a reminder works without signing in. A used
    or expired token shows a clear message and a route to sign in."""
    from .services.notify import signup_from_token

    su = signup_from_token(token)
    if su is None:
        return render(request, "events/token_invalid.html", status=410)
    already = su.confirmed_at is not None
    if not already:
        su.confirmed_at = timezone.now()
        su.save(update_fields=["confirmed_at"])
        record(su.user, "signup.confirmed", su, after={"via": "token"})
    return render(request, "events/token_confirmed.html", {"signup": su, "already": already})


def cannot_by_token(request, token):
    """FR-72: the cannot-make-it link opens the cancellation flow, signed in or not, with the
    same warning a signed-in cancel gives (FR-56)."""
    from .services import notify
    from .services.notify import signup_from_token

    su = signup_from_token(token)
    if su is None:
        return render(request, "events/token_invalid.html", status=410)
    broken = would_break(su.slot, su)
    if request.method == "POST":
        record(
            su.user,
            "signup.cancelled",
            su,
            before={"role": su.role, "user": su.user_id, "via": "token"},
        )
        notify.member_cancelled(su.user, su, broken)
        event_pk, slot, role = su.slot.event.pk, su.slot, su.role
        su.delete()
        from .services import waitlist

        waitlist.on_place_opened(slot, role)
        return render(request, "events/token_cancelled.html", {"event_pk": event_pk})
    return render(request, "events/token_cannot.html", {"signup": su, "broken": broken})


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
    from .views_member import feed_token

    return render(
        request,
        "events/my_schedule.html",
        {
            "upcoming": upcoming,
            "now": now,
            "feed_url": request.build_absolute_uri(
                reverse("ical_feed", args=[feed_token(request.user)])
            ),
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
        if request.POST.get("announce") == "yes":
            from .services.lifecycle import announce_published

            n = announce_published(request.user, event)
            messages.success(request, f"Published and announced to {n} member(s).")
        else:
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
