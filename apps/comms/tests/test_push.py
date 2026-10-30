"""Browser notifications (FR-112): subscription endpoints, delivery hook, dropped devices."""

import json
from unittest import mock

import pytest
from django.contrib.auth.models import Group
from django.test import Client, override_settings

from apps.accounts.models import NotificationPreference, PushSubscription, User
from apps.comms.services import compose

pytestmark = pytest.mark.django_db

SUB = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "P", "auth": "A"}}


def _user(email="m@example.org"):
    u = User.objects.create_user(email, "pw-Testing-123", first_name="Mo", last_name="M")
    u.groups.set(Group.objects.filter(name="member"))
    u.save()
    return u


def test_subscribe_revoke_and_toggle():
    u = _user()
    c = Client()
    c.force_login(u)
    r = c.post("/me/push/subscribe/", data=json.dumps(SUB), content_type="application/json")
    assert r.status_code == 200 and r.json()["created"]
    r = c.post("/me/push/subscribe/", data=json.dumps(SUB), content_type="application/json")
    assert r.json()["created"] is False and PushSubscription.objects.count() == 1
    assert (
        c.post("/me/push/subscribe/", data="nope", content_type="application/json").status_code
        == 400
    )
    with override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv"):
        body = c.get(
            "/me/edit/", follow=True
        ).content.decode()  # the switches live on the edit page
        assert "Browser notifications" in body and "revoke" in body and 'data-vapid="pub"' in body
        assert "Browser notifications are on" in c.get("/me/", follow=True).content.decode()
    c.post("/me/push/toggle/", {})
    u.refresh_from_db()
    assert u.push_enabled is False
    sub = PushSubscription.objects.get()
    c.post(f"/me/push/{sub.pk}/revoke/")
    assert PushSubscription.objects.count() == 0


def test_delivery_pushes_subject_and_link_only_and_drops_gone_devices():
    u = _user()
    PushSubscription.objects.create(user=u, endpoint="https://push.example/1", p256dh="P", auth="A")
    PushSubscription.objects.create(user=u, endpoint="https://push.example/2", p256dh="P", auth="A")
    from pywebpush import WebPushException

    gone = WebPushException("gone", response=mock.Mock(status_code=410))
    with override_settings(
        VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv", SITE_URL="https://ops.example"
    ):
        with mock.patch("pywebpush.webpush", side_effect=[None, gone]) as wp:
            compose(u, "warning", "Slot at risk", "<p>secret body</p>")
    assert wp.call_count == 2
    payload = json.loads(wp.call_args_list[0].kwargs["data"])
    assert payload["title"].endswith("Slot at risk") and "secret" not in json.dumps(payload)
    assert payload["url"] == "https://ops.example/me/messages/"
    assert PushSubscription.objects.count() == 1  # the 410 device is gone


def test_push_respects_the_member_switch_and_per_category_preference():
    u = _user()
    PushSubscription.objects.create(user=u, endpoint="https://push.example/1", p256dh="P", auth="A")
    NotificationPreference.objects.create(user=u, category="reminder", email=True, push=False)
    with override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv"):
        with mock.patch("pywebpush.webpush") as wp:
            compose(u, "reminder", "Reminder", "<p>x</p>")
            assert wp.call_count == 0
            compose(u, "cancellation", "Cancelled", "<p>x</p>")  # mandatory: pushed
            assert wp.call_count == 1
            u.push_enabled = False
            u.save()
            compose(u, "cancellation", "Cancelled", "<p>x</p>")
            assert wp.call_count == 1
    with mock.patch("pywebpush.webpush") as wp:  # no keys configured: nothing happens
        compose(u, "cancellation", "Cancelled", "<p>x</p>")
        assert wp.call_count == 0


def test_push_title_names_the_club_so_two_installations_are_distinguishable():
    from apps.ops.models import ClubSetting

    ClubSetting.objects.update_or_create(key="club.short_name", defaults={"value": "Test ARC"})
    u = _user()
    PushSubscription.objects.create(user=u, endpoint="https://push.example/1", p256dh="P", auth="A")
    with override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv"):
        with mock.patch("pywebpush.webpush") as wp:
            compose(u, "cancellation", "Slot canceled", "<p>x</p>")
    payload = json.loads(wp.call_args.kwargs["data"])
    assert payload["title"] == "Test ARC: Slot canceled"
    assert "/static//" not in payload["icon"]  # branding() already gives a URL


UA = {
    "Chrome on macOS": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Safari on macOS": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Firefox on macOS": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Edge on Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Opera on Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 OPR/114.0.0.0",
    "Chrome on Android": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
    "Samsung Internet on Android": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/26.0 Chrome/122.0.0.0 Mobile Safari/537.36",
    "Safari on iOS": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Chrome on iOS": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/130.0.6723.90 Mobile/15E148 Safari/604.1",
    "Firefox on Linux": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Chrome on ChromeOS": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
}


def test_a_device_is_listed_by_browser_and_system():
    """T34: each device "by browser and date". The user agent cut to 60 characters stopped
    before the browser's name on a Mac, so every device read the same (T34 step 1, 2026-10-20)."""
    for want, ua in UA.items():
        assert PushSubscription(user_agent=ua).device_label == want, ua
    assert PushSubscription(user_agent="").device_label == "a browser"
    assert PushSubscription(user_agent="curl/8.0").device_label == "a browser"

    u = _user()
    PushSubscription.objects.create(
        user=u,
        endpoint="https://push.example/9",
        p256dh="P",
        auth="A",
        user_agent=UA["Chrome on macOS"],
    )
    c = Client()
    c.force_login(u)
    with override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv"):
        body = c.get("/me/edit/", follow=True).content.decode()
    assert "Chrome on macOS, since" in body and "Mozilla/5.0" not in body
