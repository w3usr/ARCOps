"""Phase 6: the settings page (FR-89), the privacy notice (FR-101), the seeded outline (FR-77)."""

import re

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.ops.config import DEFAULT_ACCENT, set_setting, setting
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
    # One bad field saves nothing and comes back with everything that was typed, beside the
    # reason. It used to save the good fields, drop the typed ones, and redirect to a fresh page.
    r = c.post(
        "/ops/settings/",
        {
            "defaults.slot_length_minutes": "90",
            "club.short_name": "Test Club",
            "slot_roles": "not json",
        },
    )
    assert r.status_code == 200
    body = r.content.decode()
    assert "Nothing was saved" in body and "not valid JSON" in body
    assert "not json" in body and "Test Club" in body  # what was typed is still on the page
    assert setting("defaults.slot_length_minutes") == 60
    assert not ClubSetting.objects.filter(key="club.short_name").exists()

    r = c.post(
        "/ops/settings/",
        {
            "defaults.slot_length_minutes": "90",
            "club.short_name": "Test Club",
            "slot_roles": '["operator"]',
        },
    )
    assert r.status_code == 302
    assert setting("defaults.slot_length_minutes") == 90
    assert ClubSetting.objects.get(key="club.short_name").value == "Test Club"
    assert AuditLog.objects.filter(action="setting.changed").count() >= 2
    c2, _ = _as("officer")
    assert c2.get("/ops/settings/").status_code == 404


def test_a_refused_time_zone_is_not_called_the_saved_value():
    """A typed zone that is refused was also described as "the saved value", though nothing was
    saved (T43 step 1, 2026-10-21)."""
    c, _ = _as("sysadmin")
    body = c.post("/ops/settings/", {"club.timezone": "Mars/Olympus_Mons"}).content.decode()
    assert "Nothing was saved" in body and "is not a known time zone" in body
    assert "The saved value" not in body
    assert setting("club.timezone") != "Mars/Olympus_Mons"


def test_saving_one_setting_leaves_the_imported_notice_and_unset_accent_alone():
    """The form posts back every field as the page shows it. An imported notice as
    the editor returns it (cleaned, trimmed) and an unset accent as the color input shows it
    are not changes, so one changed value is one setting changed."""
    from apps.ops.templatetags.richtext import sanitise

    notice = '<h1>Privacy notice</h1>\n<p>Write to <a href="mailto:club@example.org">us</a>.</p>\n'
    ClubSetting.objects.create(key="privacy_notice_html", value=notice)  # as club_import stores it
    ClubSetting.objects.create(key="branding.accent", value=None)
    c, _ = _as("sysadmin")
    page = c.get("/ops/settings/").content.decode()
    shown = re.search(r'name="branding\.accent" type="color" value="([^"]*)"', page)[1]
    assert shown == DEFAULT_ACCENT  # was #000000, which a save then stored
    r = c.post(
        "/ops/settings/",
        {
            "club.short_name": "Test Club",
            "branding.accent": shown,  # a color input always posts the color it shows
            "privacy_notice_html": sanitise(notice).strip(),  # what the editor sends back
        },
        follow=True,
    )
    assert "1 setting changed." in r.content.decode()
    assert ClubSetting.objects.get(key="privacy_notice_html").source == "import"
    assert setting("branding.accent") is None


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


def test_accent_uses_the_color_picker_and_images_upload(settings, tmp_path):
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


def test_the_shipped_privacy_notice_says_where_the_data_is_held(settings):
    """FR-101 and T44: what is collected, who sees it, where it is held, how to close an account.
    The example ARCOps ships had no "where" (T44 step 1, generic club, 2026-10-21)."""
    from apps.ops.config import load_yaml

    settings.CLUB_OVERLAY_DIR = None  # the shipped defaults, not an installation's overlay
    notice = load_yaml(settings.CLUB_DEFAULTS_DIR)["privacy_notice_html"]
    heads = [h for h in ("Who sees what", "Where it is", "Closing your account") if h in notice]
    assert heads == ["Who sees what", "Where it is", "Closing your account"]
    assert "replaces this" in notice, "worded as a placeholder a club replaces, not a claim"
