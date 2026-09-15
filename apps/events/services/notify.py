"""
Notices about slots and events (FR-56, FR-58, FR-72, FR-73, FR-74, FR-91, FR-110, FR-113).

Everything here composes through apps.comms.services.send, so each notice renders from a
sysadmin-editable template, lands in the recipient's outbox, and honours their preferences.
The two periodic entry points, send_reminders and send_warnings, are what the timers call.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings as dj
from django.core import signing
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccessLevel, User
from apps.comms.services import send
from apps.ops.audit import record
from apps.ops.config import setting

from ..models import Event, SignUp, Slot, SlotWarning
from .roster import UTC, display_zone, zone_label
from .viability import evaluate

CONFIRM_SALT = "signup-confirm"


# ------------------------------------------------------------------------- people ---


def captains_of(event: Event) -> list[User]:
    return [c.user for c in event.captaincies.select_related("user")]


def advisors() -> list[User]:
    """Members in an approver position (§2.3): the faculty advisors, at W3USR."""
    keys = {p["key"] for p in (setting("club_positions", []) or []) if p.get("approver")}
    if not keys:
        return []
    return list(
        User.objects.filter(club_position__in=keys, is_active=True).exclude(
            access_level=AccessLevel.NONE
        )
    )


def officers() -> list[User]:
    return list(
        User.objects.filter(
            access_level__in=[AccessLevel.OFFICER, AccessLevel.SYSADMIN], is_active=True
        )
    )


def contact_line(u: User) -> str:
    bits = [u.full_name + (f" {u.callsign}" if u.callsign else "")]
    if u.email:
        bits.append(u.email)
    if u.cell_phone:
        bits.append(u.cell_phone)
    return ", ".join(bits)


# -------------------------------------------------------------------------- times ---


def when_text(slot: Slot, zone=None) -> str:
    z = zone or display_zone(slot.event)
    s, e = slot.start.astimezone(z), slot.end.astimezone(z)
    return f"{s:%a %-d %b %H:%M}–{e:%H:%M} {zone_label(slot.start, z)}"


def site() -> str:
    return getattr(dj, "SITE_URL", "") or ""


def slot_link(slot: Slot) -> str:
    return site() + reverse("slot_detail", args=[slot.event.pk, slot.pk])


# ---------------------------------------------------------------- confirm tokens ---


def confirm_token(su: SignUp) -> str:
    return signing.dumps({"s": su.pk, "u": su.user_id}, salt=CONFIRM_SALT)


def signup_from_token(token: str) -> SignUp | None:
    """The sign-up a token names, if the token is genuine, unexpired (the slot has not ended),
    and the sign-up still exists (FR-100)."""
    try:
        data = signing.loads(token, salt=CONFIRM_SALT, max_age=timedelta(days=60))
    except signing.BadSignature:
        return None
    su = (
        SignUp.objects.filter(pk=data.get("s"), user_id=data.get("u"))
        .select_related("slot")
        .first()
    )
    if su is None or su.slot.end < timezone.now():
        return None
    return su


# ------------------------------------------------------------------- reminders ---


def reminder_hours(event: Event) -> int:
    return int(event.reminder_hours_before or setting("defaults.reminder_hours_before", 24))


def send_reminders(now: datetime | None = None) -> dict:
    """FR-72: once per sign-up, when the slot is within the event's reminder window."""
    now = now or timezone.now()
    horizon = now + timedelta(hours=72)
    due = (
        SignUp.objects.filter(
            reminder_sent_at__isnull=True,
            slot__cancelled=False,
            slot__start__gt=now,
            slot__start__lte=horizon,
            slot__position__location__event__state__in=[Event.State.PUBLISHED, Event.State.LOCKED],
        )
        .select_related("slot__position__location__event", "user")
        .order_by("slot__start")
    )
    sent = 0
    for su in due:
        slot = su.slot
        event = slot.event
        if slot.start - now > timedelta(hours=reminder_hours(event)):
            continue
        send_one_reminder(su, now)
        sent += 1
    return {"sent": sent}


def send_one_reminder(su: SignUp, now: datetime | None = None) -> None:
    now = now or timezone.now()
    slot, event, user = su.slot, su.slot.event, su.user
    signups = list(slot.signups.select_related("user").exclude(pk=su.pk))
    status = evaluate(slot)
    co = status.control_operator
    caps = captains_of(event)
    kbyg = (slot.position.location.kbyg_html or "") + (event.kbyg_html or "")
    local = display_zone(event)
    ctx = {
        "event": event,
        "role": su.role,
        "when_lead": when_text(slot, local),
        "when_local": when_text(slot, local),
        "when_utc": when_text(slot, UTC),
        "location": slot.position.location.name,
        "position": slot.position.name,
        "control_operator": co.short_name if co else "",
        "others": ", ".join(s.user.short_name_lettered for s in signups),
        "confirm_link": site() + reverse("confirm_by_token", args=[confirm_token(su)]),
        "cannot_link": site() + reverse("cannot_by_token", args=[confirm_token(su)]),
        "kbyg": kbyg,
        "captains": [contact_line(c) for c in caps],
        "advisors": [contact_line(a) for a in advisors() if a not in caps],
    }
    send("reminder", user, "reminder", ctx)
    su.reminder_sent_at = now
    su.save(update_fields=["reminder_sent_at"])


# -------------------------------------------------------------------- warnings ---


def _state_key(status, unconfirmed: bool) -> str:
    return f"{status.status}|{','.join(sorted(status.missing))}|{'unconf' if unconfirmed else ''}"


def send_warnings(now: datetime | None = None) -> dict:
    """FR-73: for each future slot inside the horizon that cannot run, depends on one person, or
    has an unconfirmed sign-up within 24 hours, warn the people in it and the captains, at most
    once per state per 12 hours. Notes added inside 48 hours ride along to the captains
    (FR-110). Then FR-113's no-show notices."""
    now = now or timezone.now()
    horizon = timedelta(hours=int(setting("defaults.at_risk_horizon_hours", 72)))
    slots = (
        Slot.objects.filter(
            cancelled=False,
            start__gt=now,
            start__lte=now + horizon,
            position__location__event__state__in=[Event.State.PUBLISHED, Event.State.LOCKED],
        )
        .select_related("position__location__event")
        .prefetch_related("signups__user", "signups__user__license", "signups__responsible_adults")
    )
    per_captain: dict[int, list[dict]] = {}
    captains_cache: dict[int, list[User]] = {}
    warned = 0
    for slot in slots:
        signups = list(slot.signups.all())
        if not signups:
            continue
        status = evaluate(slot, signups)
        unconfirmed = slot.start - now <= timedelta(hours=24) and any(
            not s.confirmed_at and not s.checked_in_at for s in signups
        )
        if status.status not in ("not_viable", "at_risk") and not unconfirmed:
            continue
        key = _state_key(status, unconfirmed)
        recent = SlotWarning.objects.filter(
            slot=slot, state_key=key, sent_at__gte=now - timedelta(hours=12)
        ).exists()
        if recent:
            continue
        reasons = list(status.reasons)
        if unconfirmed:
            names = ", ".join(
                s.user.short_name for s in signups if not s.confirmed_at and not s.checked_in_at
            )
            reasons.append(f"unconfirmed: {names}")
        event = slot.event
        when = when_text(slot)
        link = slot_link(slot)
        label = status.label if status.status in ("not_viable", "at_risk") else "Unconfirmed"
        for s in signups:
            if status.status in ("not_viable", "at_risk"):
                send(
                    "warning.person",
                    s.user,
                    "warning",
                    {
                        "event": event,
                        "when": when,
                        "position": slot.position.name,
                        "status": label,
                        "reasons": "; ".join(reasons),
                        "link": link,
                    },
                )
        notes = "; ".join(
            f"{s.user.short_name}: {s.note}"
            for s in signups
            if s.note and s.created >= now - timedelta(hours=48)
        )
        row = {
            "event": event.title,
            "when": when,
            "position": slot.position.name,
            "status": label,
            "reasons": "; ".join(reasons),
            "notes": notes,
            "link": link,
        }
        caps = captains_cache.setdefault(event.pk, captains_of(event) or officers())
        for c in caps:
            per_captain.setdefault(c.pk, []).append(row)
        SlotWarning.objects.create(slot=slot, state_key=key, sent_at=now)
        warned += 1
    users = {u.pk: u for caps in captains_cache.values() for u in caps}
    for pk, rows in per_captain.items():
        send(
            "warning.captains",
            users[pk],
            "warning",
            {"count": len(rows), "horizon": int(horizon.total_seconds() // 3600), "slots": rows},
        )
    no_shows = notify_no_shows(now)
    return {"slots_warned": warned, "captains_told": len(per_captain), "no_show_notices": no_shows}


def notify_no_shows(now: datetime | None = None) -> int:
    """FR-113: N minutes into a slot, one notice to the captains naming confirmed people who have
    not checked in."""
    now = now or timezone.now()
    minutes = int(setting("defaults.late_arrival_notice_minutes", 15))
    due = SignUp.objects.filter(
        confirmed_at__isnull=False,
        checked_in_at__isnull=True,
        no_show_notified_at__isnull=True,
        slot__cancelled=False,
        slot__start__lte=now - timedelta(minutes=minutes),
        slot__end__gt=now,
    ).select_related("slot__position__location__event", "user")
    by_slot: dict[int, list[SignUp]] = {}
    for su in due:
        by_slot.setdefault(su.slot_id, []).append(su)
    sent = 0
    for signups in by_slot.values():
        slot = signups[0].slot
        event = slot.event
        names = ", ".join(s.user.short_name for s in signups)
        for c in captains_of(event) or officers():
            send(
                "captain.no_show",
                c,
                "warning",
                {
                    "names": names,
                    "event": event,
                    "minutes": minutes,
                    "when": when_text(slot),
                    "position": slot.position.name,
                    "link": slot_link(slot),
                },
            )
        SignUp.objects.filter(pk__in=[s.pk for s in signups]).update(no_show_notified_at=now)
        sent += 1
    return sent


# ---------------------------------------------------------- cancellations, moves ---


def member_cancelled(actor: User, su: SignUp, broken=None) -> None:
    """FR-56: the member cancels; the captains always hear, flagged late inside the cutoff."""
    slot, event = su.slot, su.slot.event
    cutoff = int(setting("defaults.cancellation_cutoff_hours", 24))
    late = slot.start - timezone.now() <= timedelta(hours=cutoff)
    for c in captains_of(event) or officers():
        send(
            "captain.member_cancelled",
            c,
            "cancellation",
            {
                "person": su.user.short_name_lettered,
                "role": su.role,
                "event": event,
                "when": when_text(slot),
                "position": slot.position.name,
                "late": late,
                "cutoff": cutoff,
                "broken": broken.label.lower() if broken else "",
                "link": slot_link(slot),
            },
        )


def removed_by_captain(actor: User, su: SignUp, reason: str = "") -> None:
    """FR-58, FR-74: someone else removed the sign-up; the member is told."""
    slot, event = su.slot, su.slot.event
    send(
        "signup.removed",
        su.user,
        "moved",
        {
            "actor": actor.full_name,
            "event": event,
            "when": when_text(slot),
            "position": slot.position.name,
            "role": su.role,
            "reason": reason,
            "link": site() + reverse("event_detail", args=[event.pk]),
        },
    )


def assigned_by_captain(actor: User, su: SignUp) -> None:
    """FR-58: a captain signed the member up."""
    slot, event = su.slot, su.slot.event
    send(
        "signup.assigned",
        su.user,
        "moved",
        {
            "actor": actor.full_name,
            "event": event,
            "when": when_text(slot),
            "position": slot.position.name,
            "role": su.role,
            "link": slot_link(slot),
        },
    )


def cancel_slot_with_people(actor: User, slot: Slot, reason: str = "") -> int:
    """FR-52, FR-74: cancel a slot that has sign-ups; every person is told, with the reason."""
    signups = list(slot.signups.select_related("user"))
    event = slot.event
    when = when_text(slot)
    for su in signups:
        send(
            "slot.cancelled",
            su.user,
            "cancellation",
            {
                "actor": actor.full_name,
                "event": event,
                "when": when,
                "position": slot.position.name,
                "reason": reason,
                "link": site() + reverse("event_detail", args=[event.pk]),
            },
        )
        record(
            actor,
            "signup.cancelled",
            su,
            before={"role": su.role, "user": su.user_id, "by": "slot cancelled"},
        )
    slot.signups.all().delete()
    slot.cancelled = True
    slot.save(update_fields=["cancelled"])
    record(actor, "slot.cancelled", slot, after={"reason": reason, "people": len(signups)})
    return len(signups)


def event_cancelled(actor: User, event: Event, reason: str = "") -> int:
    """FR-44, FR-74: everyone signed up for a future slot is told once."""
    now = timezone.now()
    signups = SignUp.objects.filter(
        slot__position__location__event=event, slot__end__gte=now, slot__cancelled=False
    ).select_related("user")
    by_user: dict[int, list[SignUp]] = {}
    for su in signups:
        by_user.setdefault(su.user_id, []).append(su)
    for sus in by_user.values():
        send(
            "event.cancelled",
            sus[0].user,
            "cancellation",
            {"actor": actor.full_name, "event": event, "reason": reason, "count": len(sus)},
        )
    return len(by_user)


def access_removed(actor: User, user: User) -> int:
    """FR-91: the person's future sign-ups go, and each event's captains are told."""
    now = timezone.now()
    signups = list(
        SignUp.objects.filter(user=user, slot__end__gte=now, slot__cancelled=False).select_related(
            "slot__position__location__event"
        )
    )
    by_event: dict[int, list[SignUp]] = {}
    for su in signups:
        by_event.setdefault(su.slot.event.pk, []).append(su)
    for sus in by_event.values():
        event = sus[0].slot.event
        for c in captains_of(event) or officers():
            if c.pk == user.pk:
                continue
            send(
                "captain.access_removed",
                c,
                "moved",
                {
                    "person": user.full_name,
                    "actor": actor.full_name if actor else "the system",
                    "count": len(sus),
                    "event": event,
                    "slots": "; ".join(when_text(s.slot) for s in sus),
                    "link": site() + reverse("event_detail", args=[event.pk]),
                },
            )
        for su in sus:
            record(
                actor,
                "signup.cancelled",
                su,
                before={"role": su.role, "user": su.user_id, "by": "access removed"},
            )
    SignUp.objects.filter(pk__in=[s.pk for s in signups]).delete()
    return len(signups)


# ---------------------------------------------------------------------- digest ---


def send_digest(now: datetime | None = None) -> dict:
    """FR-79: upcoming events, slots still needing people, and the member's own commitments."""
    now = now or timezone.now()
    until = now + timedelta(days=14)
    events = [
        e
        for e in Event.objects.filter(
            state__in=[Event.State.PUBLISHED, Event.State.LOCKED]
        ).prefetch_related("periods")
        if e.starts_at() and e.starts_at() <= until and (e.ends_at() or now) >= now
    ]
    rows = []
    total_open = 0
    for e in events:
        slots = Slot.objects.filter(
            position__location__event=e, cancelled=False, closed=False, start__gte=now
        ).prefetch_related("signups__user", "signups__user__license", "signups__responsible_adults")
        open_n = needs_n = 0
        for s in slots:
            st = evaluate(s, list(s.signups.all()))
            if st.status == "empty":
                open_n += 1
            elif st.status in ("not_viable", "at_risk"):
                needs_n += 1
        total_open += open_n
        start, end = e.starts_at(), e.ends_at()
        z = display_zone(e)
        rows.append(
            {
                "title": e.title,
                "when": f"{start.astimezone(z):%a %-d %b %H:%M} to {end.astimezone(z):%a %-d %b %H:%M} {zone_label(start, z)}",
                "open": open_n,
                "needs": needs_n,
                "link": site() + reverse("event_detail", args=[e.pk]),
            }
        )
    members = User.objects.filter(
        is_active=True,
        access_level__in=[AccessLevel.MEMBER, AccessLevel.OFFICER, AccessLevel.SYSADMIN],
    )
    sent = 0
    for u in members:
        mine = [
            f"{s.slot.event.title}, {when_text(s.slot)}, {s.slot.position.name} as {s.role}"
            for s in SignUp.objects.filter(user=u, slot__start__gte=now, slot__cancelled=False)
            .select_related("slot__position__location__event")
            .order_by("slot__start")[:20]
        ]
        send("digest.weekly", u, "digest", {"events": rows, "open_slots": total_open, "mine": mine})
        sent += 1
    return {"members": sent, "events": len(rows)}
