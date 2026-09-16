"""FR-89: club configuration edited in the interface (one plain form over the settings rows,
grouped, audited); FR-101: the privacy notice page."""

from __future__ import annotations

import json
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .config import BRANDING_IMAGES, branding_url, flatten, load_yaml, set_setting, setting
from .models import ClubSetting
from .templatetags.richtext import sanitise

GROUPS = [
    (
        "Club identity",
        [
            "club.name",
            "club.short_name",
            "club.callsign",
            "club.university",
            "club.department",
            "club.public_page",
            "club.contact_email",
            "club.timezone",
            "club.station_location_name",
        ],
    ),
    (
        "Sending mail",
        ["club.sending_address", "club.sending_display_name", "defaults.email_delivery"],
    ),
    (
        "Defaults",
        [
            "defaults.slot_length_minutes",
            "defaults.cancellation_cutoff_hours",
            "defaults.reminder_hours_before",
            "defaults.at_risk_horizon_hours",
            "defaults.checkin_opens_minutes_before",
            "defaults.late_arrival_notice_minutes",
            "defaults.invitation_expiry_days",
            "defaults.temporary_password_expiry_hours",
            "defaults.agreement_expiry_notice_days",
            "defaults.entry_link_verification_days",
            "defaults.waitlist_offer_hours",
            "defaults.health_overview_weeks",
        ],
    ),
    (
        "Retention (days)",
        [
            "defaults.retention_no_access_days",
            "defaults.retention_responsible_adult_days",
            "defaults.retention_agreement_days",
            "defaults.retention_message_days",
            "defaults.retention_invitation_days",
        ],
    ),
    (
        "Branding",
        [
            "branding.logo",
            "branding.logo_monochrome",
            "branding.favicon",
            "branding.apple_touch_icon",
            "branding.qsl_card",
            "branding.accent",
        ],
    ),
    (
        "Lists (JSON)",
        [
            "member_categories",
            "club_positions",
            "license_ladder",
            "slot_roles",
            "trusted_email_domains",
            "non_operating_slot_kinds",
            "credential_types",
            "viability_rule_default.require_all_of",
        ],
    ),
]
RICH = ["privacy_notice_html"]
# Field kinds beyond text, number, and JSON. A time zone is always a drop-down (NAF,
# 2026-09-16, after a typo in the free-text field); a colour gets the colour picker; an image
# gets an uploader with a preview, stored under MEDIA_ROOT/branding/ (FR-89).
KIND_OF = {
    "club.timezone": "tz",
    "branding.accent": "color",
    **{f"branding.{k}": "image" for k in BRANDING_IMAGES},
}
IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
}
IMAGE_MAX_BYTES = 2 * 1024 * 1024


def zone_names() -> list[str]:
    import zoneinfo

    return sorted(zoneinfo.available_timezones())


def _store_image(key: str, upload) -> str:
    """Save an uploaded branding image as MEDIA_ROOT/branding/<name>.<ext> and return the
    setting value; a ValueError carries the reason a file is refused."""
    ext = IMAGE_TYPES.get(upload.content_type)
    if ext is None:
        raise ValueError("PNG, JPEG, SVG, WebP, or ICO only")
    if upload.size > IMAGE_MAX_BYTES:
        raise ValueError("2 MB at most")
    stem = key.split(".", 1)[1]
    folder = settings.MEDIA_ROOT / "branding"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(stem + ".*"):  # one file per key
        old.unlink()
    with (folder / (stem + ext)).open("wb") as fh:
        for chunk in upload.chunks():
            fh.write(chunk)
    return f"media/branding/{stem}{ext}"


def _current() -> dict:
    """Every known key with its current value: the database row if any, else the file."""
    try:
        base = flatten({k: v for k, v in load_yaml().items() if k != "agreements"})
    except FileNotFoundError:
        base = {}
    for row in ClubSetting.objects.all():
        base[row.key] = row.value
    return base


@login_required
@require_http_methods(["GET", "POST"])
def settings_page(request):
    if not request.user.is_sysadmin:
        raise Http404
    current = _current()
    if request.method == "POST":
        changed = 0
        for group, keys in GROUPS:
            for key in keys:
                kind = KIND_OF.get(key)
                if kind == "image":
                    upload = request.FILES.get(key)
                    if request.POST.get(f"{key}__clear") == "on":
                        if current.get(key):
                            set_setting(request.user, key, None)
                            changed += 1
                    elif upload:
                        try:
                            set_setting(request.user, key, _store_image(key, upload))
                            changed += 1
                        except ValueError as exc:
                            messages.error(request, f"{key}: {exc}; left unchanged.")
                    continue
                if key not in request.POST:
                    continue
                raw = request.POST.get(key, "")
                old = current.get(key)
                if kind == "tz":
                    if raw not in zone_names():
                        messages.error(
                            request, f"{key}: {raw!r} is not a known time zone; left unchanged."
                        )
                        continue
                    new = raw
                elif kind == "color":
                    new = raw.strip().lower()
                    if not re.fullmatch(r"#[0-9a-f]{6}", new):
                        messages.error(
                            request, f"{key}: a colour like #401068 is needed; left unchanged."
                        )
                        continue
                elif group == "Lists (JSON)":
                    try:
                        new = json.loads(raw) if raw.strip() else []
                    except ValueError:
                        messages.error(request, f"{key}: not valid JSON; left unchanged.")
                        continue
                elif isinstance(old, bool):
                    new = raw.lower() in ("on", "true", "yes", "1")
                elif isinstance(old, int) and not isinstance(old, bool):
                    try:
                        new = int(raw)
                    except ValueError:
                        messages.error(request, f"{key}: a whole number is needed; left unchanged.")
                        continue
                else:
                    new = raw.strip() or None
                if new != old:
                    set_setting(request.user, key, new)
                    changed += 1
        for key in RICH:
            if key in request.POST:
                new = sanitise(request.POST.get(key, ""))
                if new != (current.get(key) or ""):
                    set_setting(request.user, key, new)
                    changed += 1
        messages.success(
            request, f"{changed} setting(s) changed." if changed else "Nothing changed."
        )
        return redirect("settings_page")
    groups = []
    for label, keys in GROUPS:
        rows = []
        for key in keys:
            v = current.get(key)
            kind = KIND_OF.get(key) or (
                "json"
                if label == "Lists (JSON)"
                else "int"
                if isinstance(v, int) and not isinstance(v, bool)
                else "text"
            )
            shown = json.dumps(v, indent=1) if kind == "json" else ("" if v is None else str(v))
            rows.append(
                {
                    "key": key,
                    "value": shown,
                    "kind": kind,
                    "url": branding_url(v) if kind == "image" else None,
                    "interface": ClubSetting.objects.filter(key=key, source="interface").exists(),
                }
            )
        groups.append((label, rows))
    mce_conf = json.dumps({**settings.TINYMCE_DEFAULT_CONFIG, "selector": "#privacy_notice_html"})
    return render(
        request,
        "ops/settings.html",
        {
            "groups": groups,
            "privacy_html": current.get("privacy_notice_html") or "",
            "mce_conf": mce_conf,
            "zones": zone_names(),
        },
    )


def privacy(request):
    """FR-101: reachable from every page, signed in or not."""
    html = (
        setting("privacy_notice_html", "")
        or "<h1>Privacy notice</h1><p>The club has not yet published its notice.</p>"
    )
    return render(request, "ops/privacy.html", {"notice": html})
