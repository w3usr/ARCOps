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
            "club.phone_region",
            "club.station_location_name",
        ],
    ),
    (
        "Mail",
        ["club.sending_address", "club.sending_display_name", "defaults.email_delivery"],
    ),
    (
        "How the club runs",
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
        "How long things are kept",
        [
            "defaults.retention_responsible_adult_days",
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
            "branding.maskable_icon",
            "branding.qsl_card",
            "branding.accent",
        ],
    ),
    (
        "The club's own lists",
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
# What each setting is called on the page, and one line saying what it does. The page used
# to show the dotted key and nothing else, which told the reader nothing.
SETTING_WORDS: dict[str, tuple[str, str]] = {
    "club.name": (
        "The club's name",
        "In full, as it should appear on a page and in mail.",
    ),
    "club.short_name": (
        "Short name",
        "What fits in the corner of a page and at the front of a subject line.",
    ),
    "club.callsign": (
        "Club callsign",
        "The club station's own call.",
    ),
    "club.university": (
        "University or institution",
        "Leave empty for a club that belongs to no institution.",
    ),
    "club.department": (
        "Department",
        "The department the club sits under, if any.",
    ),
    "club.public_page": (
        "Public web page",
        "Where the footer's club name links to.",
    ),
    "club.contact_email": (
        "General contact address",
        "Published as the way to reach the club, and used as the reply address when nothing better fits.",
    ),
    "club.phone_region": (
        "Where phone numbers are",
        "How a number typed without a country code is read and written back: US turns "
        "9735551234 into (973) 555-1234. A number from elsewhere keeps its own country's shape.",
    ),
    "club.timezone": (
        "The club's time zone",
        "Events are shown in this zone unless an event names another.",
    ),
    "club.station_location_name": (
        "What the station is called",
        'The name members would use for it: "Club station", "The shack".',
    ),
    "club.sending_address": (
        "Mail comes from",
        "Every message the application sends carries this address.",
    ),
    "club.sending_display_name": (
        "Shown as the sender",
        "The name beside that address in somebody's inbox.",
    ),
    "defaults.email_delivery": (
        "Send mail",
        '"on" once your mail path works. With it off, messages are written to the outbox and nothing leaves the server.',
    ),
    "defaults.slot_length_minutes": (
        "Slot length",
        "How long one slot lasts when a grid is generated. Minutes.",
    ),
    "defaults.cancellation_cutoff_hours": (
        "Late cancellation starts at",
        "A cancellation inside this many hours of the slot is flagged to the captains as late.",
    ),
    "defaults.reminder_hours_before": (
        "Reminder sent",
        "How many hours before a slot its reminder goes out.",
    ),
    "defaults.at_risk_horizon_hours": (
        "Watch slots this far ahead",
        "How many hours ahead the nightly check looks for slots that are short of people.",
    ),
    "defaults.checkin_opens_minutes_before": (
        "Check-in opens",
        "How many minutes before the slot a captain can check people in.",
    ),
    "defaults.late_arrival_notice_minutes": (
        "Late arrival noticed after",
        "How many minutes past the start before somebody not checked in counts as late.",
    ),
    "defaults.invitation_expiry_days": (
        "An invitation lasts",
        "Days before an unanswered invitation stops working.",
    ),
    "defaults.temporary_password_expiry_hours": (
        "A temporary password lasts",
        "Hours before an issued one-time password stops working.",
    ),
    "defaults.agreement_expiry_notice_days": (
        "Warn about an expiring agreement",
        "How many days before it expires the holder and the advisor are told.",
    ),
    "defaults.entry_link_verification_days": (
        "Confirm an address within",
        "Days an account that arrived through an entry link has to confirm its address. An officer can waive it.",
    ),
    "defaults.waitlist_offer_hours": (
        "A waitlist offer lasts",
        "Hours somebody has to take a place offered to them before it passes on.",
    ),
    "defaults.health_overview_weeks": (
        "Upcoming health looks ahead",
        "Weeks of events on the at-a-glance page.",
    ),
    "defaults.retention_responsible_adult_days": (
        "Keep responsible adults for",
        "Days after the event before the adults named for a minor's slot are removed.",
    ),
    "defaults.retention_message_days": (
        "Keep message text for",
        "Days before a message's text is removed. That it was sent, and to how many, is kept.",
    ),
    "defaults.retention_invitation_days": (
        "Keep unanswered invitations for",
        "Days after it expires before an invitation nobody completed is removed.",
    ),
    "branding.logo": (
        "Logo",
        "Shown in the menu and on the sign-in page.",
    ),
    "branding.logo_monochrome": (
        "Logo, one color",
        "For places that cannot carry the full logo.",
    ),
    "branding.favicon": (
        "Browser tab icon",
        "The small square a browser shows on the tab.",
    ),
    "branding.apple_touch_icon": (
        "Home screen icon",
        "Used when somebody adds the site to an iPhone or iPad home screen.",
    ),
    "branding.maskable_icon": (
        "Installed app icon",
        "Used when somebody installs the site as an app on a phone. The phone crops it to its own shape, so the mark belongs in the middle eight tenths and the rest of the square is filled.",
    ),
    "branding.qsl_card": (
        "QSL card",
        "The club's card, if you want it on the site.",
    ),
    "branding.accent": (
        "The club's color",
        "Footer, sign-in panel, buttons, and links. It must carry white text at readable contrast, or the application's own color is used instead.",
    ),
    "member_categories": (
        "Member categories",
        "The kinds of member the club has. Each needs a key and a label.",
    ),
    "club_positions": (
        "Club positions",
        "Officer posts and other roles, for the directory. Each needs a key and a label.",
    ),
    "license_ladder": (
        "License classes",
        "The ladder from lowest to highest, used when an event prefers a class.",
    ),
    "slot_roles": (
        "Slot roles",
        "What somebody can be signed up as. on_air marks a role that counts as operating.",
    ),
    "trusted_email_domains": (
        "Trusted address domains",
        "An account arriving through a class link at one of these domains is admitted at once. Empty means class links cannot be made.",
    ),
    "non_operating_slot_kinds": (
        "Other kinds of slot",
        "Setup, breakdown, and anything else that is not operating time.",
    ),
    "credential_types": (
        "Credentials",
        "What a member can hold: station access, computer access, and any others.",
    ),
    "viability_rule_default.require_all_of": (
        "What a slot needs to run",
        "The credentials somebody in the slot must hold before it counts as covered.",
    ),
}


RICH = ["privacy_notice_html"]
# Field kinds beyond text, number, and JSON. A time zone is always a drop-down (NAF,
# 2026-09-16, after a typo in the free-text field); a color gets the color picker; an image
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


def _check_image(upload) -> str:
    """The file extension for an acceptable upload; a ValueError carries why one is refused."""
    ext = IMAGE_TYPES.get(upload.content_type)
    if ext is None:
        raise ValueError("PNG, JPEG, SVG, WebP, or ICO only.")
    if upload.size > IMAGE_MAX_BYTES:
        raise ValueError("2 MB at most.")
    return ext


def _store_image(key: str, upload) -> str:
    """Save an uploaded branding image as MEDIA_ROOT/branding/<name>.<ext> and return the
    setting value; a ValueError carries the reason a file is refused."""
    ext = _check_image(upload)
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
    if not request.user.may("edit_club_settings"):
        raise Http404
    current = _current()
    errors: dict[str, str] = {}
    typed: dict[str, str] = {}
    if request.method == "POST":
        # Two passes. The first only reads and checks, so a single bad value no longer saves
        # half the form, throws away everything typed, and redirects to a blank page. Nothing
        # is written unless every field is good.
        pending: dict[str, object] = {}
        images: dict[str, object] = {}
        for group, keys in GROUPS:
            for key in keys:
                kind = KIND_OF.get(key)
                if kind == "image":
                    upload = request.FILES.get(key)
                    if request.POST.get(f"{key}__clear") == "on":
                        if current.get(key):
                            images[key] = None
                    elif upload:
                        try:
                            _check_image(upload)
                            images[key] = upload
                        except ValueError as exc:
                            errors[key] = str(exc)
                    continue
                if key not in request.POST:
                    continue
                raw = request.POST.get(key, "")
                typed[key] = raw
                old = current.get(key)
                if kind == "tz":
                    if raw not in zone_names():
                        errors[key] = f"{raw!r} is not a known time zone."
                        continue
                    new = raw
                elif kind == "color":
                    new = raw.strip().lower()
                    if not re.fullmatch(r"#[0-9a-f]{6}", new):
                        errors[key] = "A color like #401068 is needed."
                        continue
                elif group == "The club's own lists":
                    try:
                        new = json.loads(raw) if raw.strip() else []
                    except ValueError as exc:
                        errors[key] = f"This is not valid JSON: {exc}."
                        continue
                elif isinstance(old, bool):
                    new = raw.lower() in ("on", "true", "yes", "1")
                elif isinstance(old, int) and not isinstance(old, bool):
                    try:
                        new = int(raw)
                    except ValueError:
                        errors[key] = "A whole number is needed."
                        continue
                else:
                    new = raw.strip() or None
                if new != old:
                    pending[key] = new
        for key in RICH:
            if key in request.POST:
                new = sanitise(request.POST.get(key, ""))
                typed[key] = new
                if new != (current.get(key) or ""):
                    pending[key] = new
        if errors:
            what = "One field" if len(errors) == 1 else f"{len(errors)} fields"
            messages.error(
                request,
                f"Nothing was saved. {what} below need correcting; what you typed is still here.",
            )
        else:
            for key, value in images.items():
                pending[key] = None if value is None else _store_image(key, value)
            for key, value in pending.items():
                set_setting(request.user, key, value)
            n = len(pending)
            messages.success(
                request, f"{n} setting{'' if n == 1 else 's'} changed." if n else "Nothing changed."
            )
            return redirect("settings_page")
    groups = []
    for label, keys in GROUPS:
        rows = []
        for key in keys:
            v = current.get(key)
            kind = KIND_OF.get(key) or (
                "json"
                if label == "The club's own lists"
                else "int"
                if isinstance(v, int) and not isinstance(v, bool)
                else "text"
            )
            shown = json.dumps(v, indent=1) if kind == "json" else ("" if v is None else str(v))
            rows.append(
                {
                    "key": key,
                    "label": SETTING_WORDS.get(key, (key, ""))[0],
                    "help": SETTING_WORDS.get(key, (key, ""))[1],
                    "value": typed.get(key, shown),
                    "error": errors.get(key),
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
            "privacy_html": typed.get("privacy_notice_html")
            or current.get("privacy_notice_html")
            or "",
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
