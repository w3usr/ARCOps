"""Phase 6: the settings page (FR-89), the privacy notice (FR-101), the seeded outline (FR-77)."""

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.ops.config import set_setting, setting
from apps.ops.models import AuditLog, ClubSetting

pytestmark = pytest.mark.django_db


def _as(level):
    u = User.objects.create_user(
        f"{level}@example.org",
        "pw-Testing-123",
        groups=[] if level == "sysadmin" else [level],
        is_superuser=level == "sysadmin",
        first_name="A",
        last_name="B",
    )
    c = Client()
    c.force_login(u)
    if u.is_superuser:
        session = c.session  # a sysadmin signs in acting lower; this is the raised view
        session["acting_view"] = "sysadmin"
        session.save()
    return c, u


def test_settings_page_edits_are_stored_and_audited():
    c, u = _as("sysadmin")
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
    c2, _ = _as("officer")
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
    c, _ = _as("member")
    assert b'href="/privacy/"' in c.get("/").content


def test_new_event_form_starts_with_kbyg_outline():
    c, _ = _as("officer")
    r = c.get("/events/new/")
    assert r.status_code == 200
    assert b"Where and when" in r.content and b"Who to contact" in r.content
    assert b"tinymce.min.js" in r.content


def test_time_zone_is_a_drop_down_and_bad_values_are_refused():
    c, _ = _as("sysadmin")
    set_setting(None, "club.timezone", "America/New_York")
    r = c.get("/ops/settings/")
    body = r.content.decode()
    assert (
        '<select id="s-1-8" name="club.timezone">' in body
        and 'value="America/New_York" selected' in body
    )
    c.post("/ops/settings/", {"club.timezone": "America/New_YorDk"})
    assert setting("club.timezone") == "America/New_York"
    c.post("/ops/settings/", {"club.timezone": "America/Chicago"})
    assert setting("club.timezone") == "America/Chicago"


def test_accent_uses_the_colour_picker_and_images_upload(settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    c, _ = _as("sysadmin")
    body = c.get("/ops/settings/").content.decode()
    assert (
        'name="branding.accent" type="color"' in body and 'name="branding.logo" type="file"' in body
    )
    c.post("/ops/settings/", {"branding.accent": "purple"})
    assert setting("branding.accent") != "purple"
    c.post("/ops/settings/", {"branding.accent": "#401068"})
    assert setting("branding.accent") == "#401068"
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    r = c.post(
        "/ops/settings/",
        {"branding.logo": SimpleUploadedFile("anything.png", png, content_type="image/png")},
    )
    assert r.status_code == 302 and setting("branding.logo") == "media/branding/logo.png"
    assert (tmp_path / "branding" / "logo.png").read_bytes() == png
    r = c.get("/branding/logo.png")
    assert (
        r.status_code == 200
        and r["Content-Type"] == "image/png"
        and "max-age" in r["Cache-Control"]
    )
    assert c.get("/branding/../settings.py").status_code == 404
    page = c.get("/").content.decode()
    assert "/branding/logo.png?v=" in page  # the shell shows the uploaded logo
    r = c.post(
        "/ops/settings/",
        {"branding.logo": SimpleUploadedFile("x.txt", b"hi", content_type="text/plain")},
    )
    assert setting("branding.logo") == "media/branding/logo.png"  # refused, unchanged
    c.post("/ops/settings/", {"branding.logo__clear": "on"})
    assert setting("branding.logo") is None


def test_event_form_offers_the_display_zone_as_a_drop_down():
    c, _ = _as("officer")
    body = c.get("/events/new/").content.decode()
    assert '<select name="display_timezone"' in body and 'value="America/New_York"' in body
