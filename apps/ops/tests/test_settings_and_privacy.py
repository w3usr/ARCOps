"""Phase 6: the settings page (FR-89), the privacy notice (FR-101), the seeded outline (FR-77)."""

import pytest
from django.test import Client

from apps.accounts.models import AccessLevel, User
from apps.ops.config import set_setting, setting
from apps.ops.models import AuditLog, ClubSetting

pytestmark = pytest.mark.django_db


def _as(level):
    u = User.objects.create_user(
        f"{level}@example.org", "pw-Testing-123", access_level=level, first_name="A", last_name="B"
    )
    c = Client()
    c.force_login(u)
    return c, u


def test_settings_page_edits_are_stored_and_audited():
    c, u = _as(AccessLevel.SYSADMIN)
    set_setting(None, "defaults.slot_length_minutes", 60)
    r = c.get("/ops/settings/")
    assert r.status_code == 200 and b"defaults.slot_length_minutes" in r.content
    r = c.post(
        "/ops/settings/",
        {
            "defaults.slot_length_minutes": "90",
            "club.short_name": "Test Club",
            "slot_roles": "not json",
        },
    )
    assert r.status_code == 302
    assert setting("defaults.slot_length_minutes") == 90
    assert ClubSetting.objects.get(key="club.short_name").value == "Test Club"
    assert not ClubSetting.objects.filter(key="slot_roles").exists()
    assert AuditLog.objects.filter(action="setting.changed").count() >= 2
    c2, _ = _as(AccessLevel.OFFICER)
    assert c2.get("/ops/settings/").status_code == 404


def test_privacy_notice_is_public_and_linked():
    set_setting(
        None,
        "privacy_notice_html",
        "<h1>Privacy notice</h1><p>Kept for two years.</p><script>x()</script>",
    )
    r = Client().get("/privacy/")
    assert (
        r.status_code == 200 and b"Kept for two years" in r.content and b"<script>" not in r.content
    )
    c, _ = _as(AccessLevel.MEMBER)
    assert b'href="/privacy/"' in c.get("/").content


def test_new_event_form_starts_with_kbyg_outline():
    c, _ = _as(AccessLevel.OFFICER)
    r = c.get("/events/new/")
    assert r.status_code == 200
    assert b"Where and when" in r.content and b"Who to contact" in r.content
    assert b"tinymce.min.js" in r.content
