"""Event list, roster, sign-up, cancel, role change, check-in, my schedule."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ops import when
from apps.ops.audit import record
from apps.ops.templatetags.labels import role_label

from . import contest_fields
from .models import Event, RoleCapacity, SignUp, Slot
from .services.adults import name_guardians_on_slot, release_guardian
from .services.eligibility import can_sign_up
from .services.notify import drop_empty_sections
from .services.roster import build as build_roster
from .services.slots import health
from .services.viability import checkin_ready, checkin_window_open, would_break
from .views_manage import publish_blocker
from .views_rules import captained_event
from .views_slots import _visible, roster_or_slot


@login_required
def event_list(request):
    now = timezone.now()
    events = Event.objects.all()
    if not request.user.may("manage_events"):
        events = events.filter(state__in=["published", "locked", "completed"]) | events.filter(
            captaincies__user=request.user
        )
    upcoming, past, regular = [], [], []
    for e in events.distinct():
        if e.display_only:
            regular.append(e)  # FR-45: on the calendar, no roster
        else:
            # FR-44: completed by a captain or once its last slot ended, whichever came first;
            # either way it is over, though its dates may run on (2026-11-10).
            over = e.state == Event.State.COMPLETED or (e.end or now) < now
            (past if over else upcoming).append(e)
    upcoming.sort(key=lambda e: e.start or now)
    # Each row's date tile, in the viewer's zone (A38), and a captain's coverage counts.
    from .services.roster import coverage

    for e in upcoming + past:
        e.tile = e.start
    # Coverage is worked out slot by slot, so only for an event members sign up to: never for a
    # draft or a canceled one, which an officer may have hundreds of (dev, 2026-11-09).
    for e in upcoming:
        e.captain = request.user.can_captain(e)
        live = e.state in (Event.State.PUBLISHED, Event.State.LOCKED)
        e.cov = coverage(e, now) if e.captain and live else None
    return render(
        request,
        "events/list.html",
        {"upcoming": upcoming, "past": past[:20], "regular": regular},
    )


def _address(user, location, is_captain) -> str:
    """The address the event page shows for its one location. A private residence's goes only
    to people signed up there and to its captains and the officers (FR-51, section 4.2)."""
    if not location or not location.address:
        return ""
    if location.is_private_residence and not is_captain:
        if not SignUp.objects.filter(slot__position__location=location, user=user).exists():
            return ""
    return location.address


def _places(user, event, is_captain) -> list[dict]:
    """Getting there: each location that has directions or its own know-before-you-go text
    (FR-51), with its address. A private residence's go only where its address goes."""
    mine = set(
        SignUp.objects.filter(slot__position__location__event=event, user=user).values_list(
            "slot__position__location_id", flat=True
        )
    )
    out = []
    for loc in event.locations.all():
        directions = drop_empty_sections(loc.directions_html)
        notes = drop_empty_sections(loc.kbyg_html)
        if not (directions or notes):
            continue
        if loc.is_private_residence and not is_captain and loc.pk not in mine:
            continue
        out.append(
            {"name": loc.name, "address": loc.address, "directions": directions, "notes": notes}
        )
    return out


@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not _visible(request.user, event):
        raise Http404
    roster = build_roster(
        event,
        request.user,
        filter=request.GET.get("filter", ""),
        open_fold=request.GET.get("open", ""),  # a folded run, opened without JavaScript
    )
    return render(
        request,
        "events/detail.html",
        {
            "event": event,
            "roster": roster,
            "health": health(event) if roster["is_captain"] else None,
            "is_captain": roster["is_captain"],
            "address": _address(request.user, roster["single_location"], roster["is_captain"]),
            "places": _places(request.user, event, roster["is_captain"]),
            # the Draft banner's Publish waits for the required steps too
            "missing": publish_blocker(event)
            if roster["is_captain"] and event.state == Event.State.DRAFT
            else "",
            "roles": roster["roles"],
            # The outline an untouched event starts with is headings only; the reminder drops the
            # empty ones, and the page drops the same ones.
            "kbyg": drop_empty_sections(event.kbyg_html),
            "contest": contest_fields.present(event.contest_fields or {}),
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
        return roster_or_slot(request, slot)
    if slot.signups.filter(role=role).count() >= cap.capacity:
        messages.error(request, "That role is full. You can join the waitlist from the slot.")
        return redirect("slot_detail", pk=event.pk, slot_id=slot.pk)
    allowed, reason = can_sign_up(request.user, slot, role)
    if not allowed:
        messages.error(request, f"You cannot take that role: {reason}.")
        return roster_or_slot(request, slot)
    su, created = SignUp.objects.get_or_create(
        slot=slot,
        user=request.user,
        defaults={"role": role, "note": request.POST.get("note", "")[:500]},
    )
    if not created:
        messages.info(request, "You already hold this slot.")
    else:
        record(request.user, "signup.created", su, after={"role": role})
        name_guardians_on_slot(request.user, su)
        messages.success(
            request, f"Signed up as {role_label(role)} for {when.local(slot.start, year=True)}."
        )
        if request.user.under_18:  # FR-64: the guardian names who accompanies the minor
            messages.info(
                request,
                f"Now name the responsible adult who will accompany {request.user.display_first}.",
            )
            return redirect("signup_adults", signup_id=su.pk)
    return roster_or_slot(request, slot)


@login_required
def confirm_remove_signup(request, signup_id):
    """A captain taking somebody else out of a slot (FR-58).

    The remove control used to post straight through with confirmed=yes and no reason, so the
    club member got a removal notice with an empty reason and the captain never saw what it did
    to the slot. This page says both things before anything happens.
    """
    su = get_object_or_404(SignUp, pk=signup_id)
    if not request.user.can_captain(su.slot.event):
        raise Http404
    if su.kept:  # attendance, an ended slot or an event that is over stays in the record
        messages.error(request, su.kept)
        return redirect("slot_detail", pk=su.slot.event.pk, slot_id=su.slot.pk)
    return render(
        request,
        "events/confirm_remove.html",
        {"signup": su, "broken": would_break(su.slot, su), "event": su.slot.event},
    )


@login_required
@require_POST
def cancel_signup(request, signup_id):
    su = get_object_or_404(SignUp, pk=signup_id)
    slot = su.slot
    if su.user != request.user and not request.user.can_captain(slot.event):
        raise Http404
    if su.kept:  # for a captain as well: attendance cannot be undone
        messages.error(request, su.kept)
        return redirect("event_detail", pk=slot.event.pk)
    if slot.event.state == Event.State.LOCKED and not request.user.can_captain(slot.event):
        messages.error(request, "The roster is locked; ask a captain to change your sign-up.")
        return redirect("event_detail", pk=slot.event.pk)  # FR-44
    if request.POST.get("confirmed") != "yes":
        broken = would_break(slot, su)
        if broken:  # the page says what breaks; a flash repeating it put two warnings on one fact
            return render(request, "events/confirm_cancel.html", {"signup": su, "broken": broken})
    from .services import notify

    reason = request.POST.get("reason", "").strip()[:300]
    if su.user != request.user and not reason:  # FR-58; the form's `required` is not enough
        messages.error(request, "A removal needs a reason; the member is told it.")
        return redirect("confirm_remove_signup", signup_id=su.pk)
    broken = would_break(slot, su)
    record(request.user, "signup.cancelled", su, before={"role": su.role, "user": su.user_id})
    if su.user == request.user:
        notify.member_cancelled(request.user, su, broken)  # FR-56: the captains always hear
    else:
        notify.removed_by_captain(request.user, su, reason)  # FR-58
    role = su.role
    release_guardian(request.user, su)
    su.delete()
    from .services import waitlist

    waitlist.on_place_opened(slot, role)  # FR-57
    messages.success(request, "Sign-up canceled.")
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

    su = signup_from_token(token, "cannot")
    if su is None:
        return render(request, "events/token_invalid.html", status=410)
    if request.method == "GET" and request.GET.get("kept"):
        # Keep it: say so here, signed out as well as in; My schedule would ask for a sign-in.
        # Nothing is recorded, and keeping a slot is not confirming attendance.
        return render(request, "events/token_confirmed.html", {"signup": su, "kept": True})
    if su.kept:  # an event completed early still sends links for slots ahead
        return render(request, "events/token_kept.html", {"why": su.kept}, status=409)
    event = su.slot.event
    if event.state == Event.State.LOCKED:  # FR-44, as the signed-in cancel
        captains = ", ".join(c.user.short_name for c in event.captaincies.select_related("user"))
        why = "The roster is locked, so a late change goes through a captain" + (
            f": {captains}." if captains else "."
        )
        return render(request, "events/token_kept.html", {"why": why}, status=409)
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
        release_guardian(su.user, su)
        su.delete()
        from .services import waitlist

        waitlist.on_place_opened(slot, role)
        return render(request, "events/token_cancelled.html", {"event_pk": event_pk})
    return render(request, "events/token_cannot.html", {"signup": su, "broken": broken})


@login_required
@require_POST
def check_in(request, signup_id):
    """FR-113: check the member in for this slot and the rest of its run (SignUp.checkin_run,
    A42). Only this slot's window applies; a minor's adult is named as present."""
    su = get_object_or_404(SignUp, pk=signup_id)
    now = timezone.now()
    if su.user != request.user and not request.user.can_captain(su.slot.event):
        raise Http404
    # A captain checking people in goes back to the slot for the next one.
    back = (
        redirect("my_schedule")
        if su.user == request.user
        else redirect("slot_detail", pk=su.slot.event.pk, slot_id=su.slot.pk)
    )
    if not checkin_window_open(su.slot, now):
        messages.error(request, "Check-in opens 30 minutes before the slot.")
        return back
    run = su.checkin_run()
    present, left = [], None
    if (
        su.user.under_18
    ):  # FR-113: a guardian or a captain checks a minor in, naming the adult present
        adults = list(su.responsible_adults.all())
        chosen = request.POST.getlist("adult") or ([str(adults[0].pk)] if len(adults) == 1 else [])
        here = [a for a in adults if str(a.pk) in chosen]
        if not here:
            messages.error(
                request,
                f"Say which responsible adult is with {su.user.display_first} before checking them in.",
            )
            return redirect("slot_detail", pk=su.slot.event.pk, slot_id=su.slot.pk)

        def who(a):
            return ("member", a.member_id) if a.member_id else ("name", a.name.strip().casefold())

        keys = {who(a) for a in here}
        # A later slot counts only where one of those adults is designated (FR-64); the run
        # stops at the first that has none, and that slot is checked in on its own.
        for i, s in enumerate(run):
            there = [a for a in s.responsible_adults.all() if who(a) in keys] if i else here
            if not there:
                run, left = run[:i], s
                break
            present += there
        for a in present:
            a.present_at = now
            a.save(update_fields=["present_at"])
    by = getattr(request.user, "acting_guardian", None) or request.user
    for s in run:
        if s is su or not s.checked_in_at:  # a later slot already checked in keeps its time
            s.checked_in_at, s.checked_in_by = now, by
            s.save(update_fields=["checked_in_at", "checked_in_by"])
    after = {}
    if present:
        after["present"] = sorted({a.name for a in present})
    if len(run) > 1:
        after["run"] = [s.pk for s in run]
    record(request.user, "signup.checked_in", su, after=after or None)
    done = (
        f"Checked in for {len(run)} slots, {when.clock_span(su.slot.start, run[-1].slot.end)}."
        if len(run) > 1
        else "Checked in."
    )
    if left:
        done += (
            f" The slot from {when.clock_span(left.slot.start, left.slot.end)} has none of those "
            "adults named, so check in for it on its own."
        )
    messages.success(
        request,
        f"{done} Have a good shift."
        if su.user == request.user
        else f"{done} {su.user.display_first} is here.",
    )
    return back


@login_required
def my_schedule(request):
    now = timezone.now()
    signups = (
        SignUp.objects.filter(user=request.user, slot__cancelled=False)
        .exclude(slot__position__location__event__state=Event.State.CANCELLED)
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
            "ready": checkin_ready(upcoming, now),
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
    event = captained_event(request, pk)
    blocked = publish_blocker(event) if event.state == Event.State.DRAFT else ""
    if blocked:  # the button is greyed too; this is for a form posted from an older page
        messages.error(request, f"Not published: {blocked}")
    elif event.state == Event.State.DRAFT:
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
            request, "A published event with sign-ups can only be canceled, not unpublished."
        )
    # The Publish step of Manage posts here too, and goes back to it.
    if request.POST.get("from") == "manage":
        return redirect("event_step", pk=pk, step="publish")
    return redirect("event_detail", pk=pk)
