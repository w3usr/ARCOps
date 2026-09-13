"""
Composing and (when allowed) delivering messages. Every message goes through `compose`, which
records it in the outbox first (FR-82); `deliver` sends it only if email delivery is on
(FR-105). Nothing else in the application sends mail directly.
"""

from __future__ import annotations

import html2text
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.ops.config import setting

from .models import Outbox


def recipient_addresses(user) -> list[str]:
    """FR-70: the member's chosen addresses; a minor's guardians always."""
    addrs = []
    if user.under_18:
        for g in user.guardianships.filter(active=True).select_related("guardian"):
            addrs += recipient_addresses(g.guardian)
        if user.email:
            addrs.append(user.email)
        return sorted(set(addrs))
    addrs.append(user.email)
    if user.email_preference == "both":
        for a in (user.institution_email, user.personal_email):
            if a and a.lower() != user.email.lower():
                addrs.append(a)
    return sorted(set(a for a in addrs if a))


def compose(user, category: str, subject: str, body_html: str, deliver_now: bool = True) -> Outbox:
    msg = Outbox.objects.create(
        user=user,
        to_addresses=recipient_addresses(user) if user else [],
        category=category,
        subject=subject,
        body_html=body_html,
        body_text=html2text.html2text(body_html),
    )
    if deliver_now:
        deliver(msg)
    return msg


def email_enabled() -> bool:
    return str(setting("defaults.email_delivery", "off")).lower() == "on"


def deliver(msg: Outbox) -> Outbox:
    if not email_enabled():
        msg.state = Outbox.State.NOT_SENT
        msg.save(update_fields=["state"])
        return msg
    from_addr = f"{setting('club.sending_display_name', 'Club Operations')} <{setting('club.sending_address', 'ops@example.org')}>"
    reply_to = [setting("club.contact_email", "")] if setting("club.contact_email", "") else None
    try:
        email = EmailMultiAlternatives(
            msg.subject, msg.body_text, from_addr, msg.to_addresses, reply_to=reply_to
        )
        email.attach_alternative(msg.body_html, "text/html")
        if msg.category == "announcement":
            email.extra_headers["List-Unsubscribe"] = (
                f"<mailto:{setting('club.contact_email', '')}?subject=unsubscribe>"
            )
        email.send()
        msg.state, msg.sent_at = Outbox.State.SENT, timezone.now()
    except Exception as exc:  # noqa: BLE001
        msg.state, msg.error = Outbox.State.FAILED, str(exc)[:500]
    msg.save(update_fields=["state", "sent_at", "error"])
    return msg
