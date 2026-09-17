"""
Announcements (FR-75, FR-106, FR-69, FR-81).

A captain announces to an event's participants (filtered by day, role, slot status, confirmation
state, or member category); an officer or sysadmin also announces to every member. The sender
sees the resolved count before sending. Every announcement is recorded with its audience
definition and resolved recipients, and each recipient's copy carries Reply-To (sender, the
event's captains, the club address), an unsubscribe link in the body, and the List-Unsubscribe
headers. "Copy for my own mail client" records the announcement as sent outside the system.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings as dj
from django.core import signing
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AccessLevel, User, levels_at_least
from apps.events.models import Event, SignUp
from apps.events.services.roster import display_zone
from apps.events.services.viability import evaluate
from apps.ops.audit import record
from apps.ops.config import setting

from .models import Announcement
from .services import compose

UNSUB_SALT = "announcement-unsubscribe"
STATUS_FILTERS = {"open": "empty", "needs": "not_viable", "thin": "at_risk", "covered": "viable"}


def _site() -> str:
    return getattr(dj, "SITE_URL", "") or ""


def unsubscribe_token(user) -> str:
    return signing.dumps({"u": user.pk}, salt=UNSUB_SALT)


def user_from_unsubscribe_token(token: str):
    try:
        data = signing.loads(token, salt=UNSUB_SALT, max_age=timedelta(days=365))
    except signing.BadSignature:
        return None
    return User.objects.filter(pk=data.get("u"), is_active=True).first()


def resolve_audience(event: Event | None, filters: dict) -> list[User]:
    """The people an announcement reaches, given the filters. With an event: those signed up
    for a future slot, narrowed by day (YYYY-MM-DD in the event's zone), role, slot status,
    confirmation state, and category. Without: every active member, narrowed by category."""
    cats = [c for c in filters.get("categories", []) if c]
    if event is None:
        qs = User.objects.filter(
            is_active=True,
            access_level__in=levels_at_least(AccessLevel.MEMBER),
        )
        if cats:
            qs = qs.filter(category__in=cats)
        return list(qs.order_by("last_name", "first_name"))
    now = timezone.now()
    signups = (
        SignUp.objects.filter(
            slot__position__location__event=event, slot__cancelled=False, slot__end__gte=now
        )
        .select_related("user", "slot", "slot__position")
        .prefetch_related(
            "slot__signups__user",
            "slot__signups__user__license",
            "slot__signups__responsible_adults",
        )
    )
    zone = display_zone(event)
    day, role, status, confirm = (
        filters.get("day", ""),
        filters.get("role", ""),
        filters.get("status", ""),
        filters.get("confirmation", ""),
    )
    status_cache: dict[int, str] = {}
    chosen: dict[int, User] = {}
    for su in signups:
        if day and su.slot.start.astimezone(zone).strftime("%Y-%m-%d") != day:
            continue
        if role and su.role != role:
            continue
        if cats and su.user.category not in cats:
            continue
        if confirm == "unconfirmed" and (su.confirmed_at or su.checked_in_at):
            continue
        if confirm == "confirmed" and not (su.confirmed_at or su.checked_in_at):
            continue
        if status:
            if su.slot_id not in status_cache:
                status_cache[su.slot_id] = evaluate(su.slot, list(su.slot.signups.all())).status
            if status_cache[su.slot_id] != STATUS_FILTERS.get(status, status):
                continue
        chosen[su.user_id] = su.user
    return sorted(chosen.values(), key=lambda u: (u.last_name, u.first_name))


def reply_to_for(sender: User, event: Event | None) -> list[str]:
    """FR-69: the sender, the event's captains, and the club address."""
    addrs = [sender.email]
    if event is not None:
        addrs += [c.user.email for c in event.captaincies.select_related("user") if c.user.email]
    club = setting("club.contact_email", "")
    if club:
        addrs.append(club)
    seen, out = set(), []
    for a in addrs:
        if a and a.lower() not in seen:
            seen.add(a.lower())
            out.append(a)
    return out


def send_announcement(
    sender: User,
    event: Event | None,
    filters: dict,
    subject: str,
    body_html: str,
    *,
    outside: bool = False,
) -> Announcement:
    recipients = resolve_audience(event, filters)
    ann = Announcement.objects.create(
        sender=sender,
        event=event,
        audience=filters,
        recipients=[[u.pk, u.short_name] for u in recipients],
        recipient_count=len(recipients),
        subject=subject[:200],
        body_html=body_html,
        sent_outside=outside,
    )
    record(
        sender,
        "announcement.sent" if not outside else "announcement.recorded_outside",
        ann,
        after={
            "event": event.pk if event else None,
            "recipients": len(recipients),
            "filters": filters,
        },
    )
    if outside:
        return ann
    reply_to = reply_to_for(sender, event)
    for u in recipients:
        link = _site() + reverse("unsubscribe", args=[unsubscribe_token(u)])
        footer = (
            f'<p class="muted"><small>Sent by {sender.full_name} to {"the people signed up for " + event.title if event else "every member"}. '
            f'To stop receiving announcements by email, <a href="{link}">unsubscribe</a>; notices about your own slots and account are unaffected.</small></p>'
        )
        msg = compose(u, "announcement", subject, body_html + footer, deliver_now=False)
        msg.reply_to = reply_to
        msg.announcement = ann
        msg.save(update_fields=["reply_to", "announcement"])
        from .services import deliver

        deliver(msg)
    return ann


def outside_copy(sender: User, event: Event | None, filters: dict) -> tuple[list[str], list[User]]:
    """FR-106: the comma-separated address list for the sender's own BCC field."""
    users = resolve_audience(event, filters)
    from .services import recipient_addresses

    addrs: list[str] = []
    for u in users:
        for a in recipient_addresses(u):
            if a not in addrs:
                addrs.append(a)
    return addrs, users


def set_announcement_email(user, on: bool) -> None:
    from apps.accounts.models import NotificationPreference

    NotificationPreference.objects.update_or_create(
        user=user, category="announcement", defaults={"email": on}
    )
    record(user, "preference.announcement_email", user, after={"email": on})
