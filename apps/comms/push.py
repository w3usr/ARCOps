"""
Browser notifications (FR-112, TR-7): web push with VAPID keys held in the server env file.

Every message that would reach a member by email under their preferences is also pushed to each
of their subscribed devices, mandatory categories included. The payload carries the subject and
a link only, never the body: a notification is not the place for a password or a phone number.
Delivery is best effort: a failed push is logged, counted on the subscription, never retried,
and never blocks the email or the in-application copy. A 404 or 410 from the push service
means the browser dropped the subscription, so the row is deleted.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings

log = logging.getLogger(__name__)


def configured() -> bool:
    return bool(
        getattr(settings, "VAPID_PUBLIC_KEY", "") and getattr(settings, "VAPID_PRIVATE_KEY", "")
    )


def push_wanted(user, category: str) -> bool:
    from .categories import CONTROLLED

    if user is None or not getattr(user, "push_enabled", True):
        return False
    if category not in CONTROLLED:
        return True
    pref = user.notification_preferences.filter(category=category).first()
    return True if pref is None else bool(pref.push)


def send_push(user, title: str, url: str = "/") -> int:
    """Push `title` to each of the user's devices. Returns the number delivered."""
    if not configured() or user is None:
        return 0
    from django.utils import timezone

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:  # pragma: no cover - dependency pinned
        log.warning("pywebpush not installed; push skipped")
        return 0
    payload = json.dumps({"title": title[:120], "body": "", "url": url})
    claims = {"sub": f"mailto:{getattr(settings, 'VAPID_CLAIMS_EMAIL', '') or 'ops@example.org'}"}
    delivered = 0
    for sub in list(user.push_subscriptions.all()):
        info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
        try:
            webpush(
                subscription_info=info,
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=dict(claims),
                ttl=6 * 3600,
                timeout=10,
            )
            sub.last_success = timezone.now()
            sub.save(update_fields=["last_success"])
            delivered += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                sub.delete()  # the browser unsubscribed
                continue
            sub.failures += 1
            sub.save(update_fields=["failures"])
            log.warning("push failed (%s) for %s: %s", status, sub.endpoint[:60], exc)
        except Exception as exc:  # noqa: BLE001
            sub.failures += 1
            sub.save(update_fields=["failures"])
            log.warning("push error for %s: %s", sub.endpoint[:60], exc)
    return delivered
