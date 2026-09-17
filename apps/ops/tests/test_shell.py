"""The application shell and the sign-in page (design run of 2026-09-13)."""

import re

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import User
from apps.ops import config
from apps.ops.models import ClubSetting

pytestmark = pytest.mark.django_db


def _set(key, value):
    ClubSetting.objects.update_or_create(key=key, defaults={"value": value})


def test_sign_in_page_is_the_split_layout_without_signup_or_contact_noise(client: Client):
    body = client.get("/accounts/login/").content.decode()
    assert 'class="auth"' in body and "auth-hero" in body
    assert "invitation from a club officer" not in body
    assert "Times are shown" not in body
    assert "mailto:" not in body  # the footer names the club and links its page, nothing else
    assert "Forgot your username or password?" in body
    # No inline executable script: the CSP allows own-origin files only.
    assert not [
        t
        for t in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", body)
        if 'type="application/json"' not in t
    ]


def test_footer_links_the_club_page_and_credits_the_product(client: Client):
    _set("club.public_page", "https://example.edu/radio")
    _set("club.callsign", "N0CLB")
    _set("club.name", "Example Radio Club")
    body = client.get("/accounts/login/").content.decode()
    assert '<a href="https://example.edu/radio">N0CLB Example Radio Club</a>' in body
    assert "Powered by" in body


def test_signed_in_pages_get_the_sidebar_with_the_current_page_marked():
    u = User.objects.create_user("m@example.org", "pw-Testing-123", first_name="Mo", last_name="M")
    u.groups.set(Group.objects.filter(name="member"))
    u.save()
    c = Client()
    c.force_login(u)
    body = c.get("/events/").content.decode()
    assert 'id="sidenav"' in body
    assert re.search(r'href="/events/"\s+aria-current="page"', body)
    assert ">Invite<" not in body  # officers only


def test_accent_comes_from_club_config_when_it_carries_white_text(client: Client):
    _set("branding.accent", "#401068")
    assert "--brand: #401068" in client.get("/accounts/login/").content.decode()


def test_accent_that_fails_aa_contrast_falls_back_to_the_default():
    _set("branding.accent", "#ffff00")
    assert config.accent_color() == config.DEFAULT_ACCENT
    _set("branding.accent", "not-a-color")
    assert config.accent_color() == config.DEFAULT_ACCENT
    _set("branding.accent", "#401068")
    assert config.accent_color() == "#401068"
    assert config.contrast_with_white("#401068") > 4.5
