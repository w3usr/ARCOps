"""
Composing and (when allowed) delivering messages.

Every message goes through `compose`, which records it in the outbox first (FR-82); `deliver`
sends it only if email delivery is on (FR-105) and the member's preference allows the category
(FR-71). Nothing else in the application sends mail directly. `render_message` turns a template
key and a context into a subject and body (FR-78); `send` does both in one call.
"""

from __future__ import annotations

import html2text
from django.conf import settings as dj
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template
from django.utils import timezone

from apps.ops.config import setting

from .categories import CONTROLLED
from .defaults import DEFAULTS_BY_KEY
from .models import MessageTemplate, Outbox


def recipient_addresses(user) -> list[str]:
    """Where a message to this person goes: every address of theirs that takes club mail, and
    for a member under 18 their guardians' as well, always (FR-70). A minor with no address of
    their own is reached entirely through the guardians, which is why they need none."""
    from apps.accounts.addresses import for_delivery

    addrs: list[str] = []
    if user.under_18:
        for g in user.guardianships.filter(active=True).select_related("guardian"):
            addrs += recipient_addresses(g.guardian)
    addrs += for_delivery(user)
    return sorted({a.lower() for a in addrs if a})


def email_wanted(user, category: str) -> bool:
    """FR-71: mandatory categories always; controlled ones unless the member switched them off.
    Absence of a preference row means on."""
    if user is None or category not in CONTROLLED:
        return True
    pref = user.notification_preferences.filter(category=category).first()
    return True if pref is None else bool(pref.email)


def _plain_text(body_html: str) -> str:
    """The text alternative. Wrapping is off because html2text's default breaks a long URL
    across lines, which leaves the text-only reader with a link they cannot follow."""
    converter = html2text.HTML2Text()
    converter.body_width = 0
    return converter.handle(body_html)


def compose(
    user,
    category: str,
    subject: str,
    body_html: str,
    deliver_now: bool = True,
    to: list[str] | None = None,
) -> Outbox:
    """Record a message for `user` (or for bare addresses `to` when there is no account yet,
    as with an invitation) and deliver it if allowed."""
    if to is None:
        to = recipient_addresses(user) if user else []
    msg = Outbox.objects.create(
        user=user,
        to_addresses=to,
        category=category,
        subject=subject[:200],
        body_html=body_html,
        body_text=_plain_text(body_html),
    )
    if deliver_now:
        deliver(msg)
    return msg


def email_enabled() -> bool:
    return str(setting("defaults.email_delivery", "off")).lower() == "on"


def deliver(msg: Outbox) -> Outbox:
    _push(msg)
    if not email_wanted(msg.user, msg.category):
        msg.state = Outbox.State.SKIPPED
        msg.save(update_fields=["state"])
        return msg
    if not email_enabled():
        msg.state = Outbox.State.NOT_SENT
        msg.save(update_fields=["state"])
        return msg
    from_addr = f"{setting('club.sending_display_name', 'Club Operations')} <{setting('club.sending_address', 'ops@example.org')}>"
    reply_to = msg.reply_to or (
        [setting("club.contact_email", "")] if setting("club.contact_email", "") else None
    )
    try:
        email = EmailMultiAlternatives(
            msg.subject, msg.body_text, from_addr, msg.to_addresses, reply_to=reply_to
        )
        from .layout import wrap

        email.attach_alternative(wrap(msg.body_html), "text/html")
        if msg.category == "announcement" and msg.user is not None:
            # FR-81: list mail carries a working unsubscribe, by link and by one-click POST
            from django.urls import reverse

            from .announce import unsubscribe_token

            one_click = f"{getattr(dj, 'SITE_URL', '')}{reverse('unsubscribe', args=[unsubscribe_token(msg.user)])}"
            club = setting("club.contact_email", "")
            email.extra_headers["List-Unsubscribe"] = f"<{one_click}>" + (
                f", <mailto:{club}?subject=unsubscribe>" if club else ""
            )
            email.extra_headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        email.send()
        msg.state, msg.sent_at = Outbox.State.SENT, timezone.now()
    except Exception as exc:  # noqa: BLE001
        msg.state, msg.error = Outbox.State.FAILED, str(exc)[:500]
    msg.save(update_fields=["state", "sent_at", "error"])
    return msg


def _push(msg: Outbox) -> None:
    """FR-112: the browser copy, best effort, subject and link only."""
    from .push import push_wanted, send_push

    if msg.user is None or not push_wanted(msg.user, msg.category):
        return
    try:
        send_push(msg.user, msg.subject, f"{getattr(dj, 'SITE_URL', '')}/me/messages/")
    except Exception as exc:  # noqa: BLE001 - never blocks the email or the copy
        import logging

        logging.getLogger(__name__).warning("push skipped: %s", exc)


# ------------------------------------------------------------------ templates (FR-78) ---


def base_context() -> dict:
    return {
        "club": {
            "name": setting("club.name", "the club"),
            "short_name": setting("club.short_name", "the club"),
            "contact_email": setting("club.contact_email", ""),
        },
        "site_url": getattr(dj, "SITE_URL", ""),
    }


def get_template(key: str) -> MessageTemplate:
    """The row if it exists, else an unsaved instance carrying the shipped default."""
    row = MessageTemplate.objects.filter(key=key).first()
    if row:
        return row
    default = DEFAULTS_BY_KEY.get(key)
    if default is None:
        raise KeyError(f"no message template {key!r}")
    return MessageTemplate(**default)


def render_message(key: str, context: dict | None = None) -> tuple[str, str]:
    """(subject, body_html) for a template key. Bodies are sanitised on save; the render here
    trusts them, so the output is safe to mark as HTML."""
    tpl = get_template(key)
    ctx = Context({**base_context(), **(context or {})}, autoescape=True)
    subject = Template(tpl.subject).render(ctx).strip().replace("\n", " ")
    body = Template(tpl.body_html).render(ctx)
    return subject, body


def send(key: str, user, category: str, context: dict | None = None, to=None) -> Outbox:
    """Render `key` for `user` and compose it in `category`. `user` is in the context as
    `user`; pass other names in `context`."""
    ctx = {"user": user, **(context or {})}
    subject, body = render_message(key, ctx)
    return compose(user, category, subject, body, to=to)


def seed_templates(reset: bool = False) -> tuple[int, int, int]:
    """Create missing rows from the defaults; refresh unedited ones; keep edited ones unless
    reset. Returns (created, updated, kept)."""
    created = updated = kept = 0
    for d in DEFAULTS_BY_KEY.values():
        row, was_created = MessageTemplate.objects.get_or_create(
            key=d["key"],
            defaults={
                "subject": d["subject"],
                "body_html": d["body_html"],
                "variables": d["variables"],
            },
        )
        if was_created:
            created += 1
            continue
        if row.edited and not reset:
            if row.variables != d["variables"]:
                row.variables = d["variables"]
                row.save(update_fields=["variables"])
            kept += 1
            continue
        changed = (row.subject, row.body_html, row.variables, row.edited) != (
            d["subject"],
            d["body_html"],
            d["variables"],
            False,
        )
        if changed:
            row.subject, row.body_html, row.variables, row.edited = (
                d["subject"],
                d["body_html"],
                d["variables"],
                False,
            )
            row.save()
            updated += 1
    return created, updated, kept
