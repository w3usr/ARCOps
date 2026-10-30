"""
Reading club configuration (TR-32, TR-40, TR-41).

Two layers: the files (an overlay directory if configured, else the shipped defaults in
config/) and the database (ClubSetting rows, which `club_import` seeds from the files and
sysadmins edit afterwards). Code asks `setting("club.name")` and never cares which.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings as dj

log = logging.getLogger(__name__)


def config_dir() -> Path:
    """The directory whose club.yaml applies: the overlay if set, else the defaults."""
    if dj.CLUB_OVERLAY_DIR and (dj.CLUB_OVERLAY_DIR / "club.yaml").exists():
        return dj.CLUB_OVERLAY_DIR
    return dj.CLUB_DEFAULTS_DIR


def _read(directory: Path) -> dict[str, Any] | None:
    for name in ("club.yaml", "club.example.yaml"):
        path = directory / name
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
    return None


def _under(defaults: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """The overlay's answers, with the shipped ones filling the gaps.

    Dictionaries are merged key by key; a list or a value the overlay states is taken whole,
    because a club that lists its own categories, groups or agreements means *those* and not
    those plus ours.
    """
    merged = dict(defaults)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _under(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_yaml(directory: Path | None = None) -> dict[str, Any]:
    """The club's configuration: an overlay laid over the shipped defaults (TR-41).

    It is an overlay rather than a replacement, so a setting added to the application reaches an
    installation that has its own club.yaml. Without this, `security.two_factor_required_groups`
    was invisible on the club's own server on the day it was added (2026-09-20).
    """
    directory = directory or config_dir()
    overlay = _read(directory)
    if overlay is None:
        raise FileNotFoundError(f"no club.yaml or club.example.yaml in {directory}")
    defaults = _read(dj.CLUB_DEFAULTS_DIR) if directory != dj.CLUB_DEFAULTS_DIR else None
    return _under(defaults, overlay) if defaults else overlay


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """{"club": {"name": x}} -> {"club.name": x}. Lists stay whole under their key."""
    out: dict[str, Any] = {}
    for key, value in data.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, dotted + "."))
        else:
            out[dotted] = value
    return out


def normalise_static_path(value: str | None) -> str | None:
    """Branding paths in club.yaml are written relative to the config directory
    ("static/club/logo.png" in an overlay, "assets/club-logo.svg" in the defaults); the
    application serves both under the static prefix "club/"."""
    if not value:
        return None
    if value.startswith("static/"):
        return value[len("static/") :]
    if value.startswith("assets/"):
        return "club/" + value[len("assets/") :]
    return value


def setting(key: str, default: Any = None) -> Any:
    """A configuration value from the database, falling back to the files, then `default`."""
    from .models import ClubSetting

    try:
        return ClubSetting.objects.get(key=key).value
    except ClubSetting.DoesNotExist:
        pass
    except Exception:  # noqa: BLE001 - before migrations, during checks
        return default
    try:
        return flatten(load_yaml()).get(key, default)
    except FileNotFoundError:
        return default


def set_setting(actor, key: str, value: Any):
    """Change one value from the interface, audited (FR-89, FR-105). The row is marked as an
    interface edit so `club_import` keeps it unless run with --reset."""
    from .audit import record
    from .models import ClubSetting

    row, _ = ClubSetting.objects.get_or_create(key=key)
    before = row.value
    row.value, row.source = value, "interface"
    row.save(update_fields=["value", "source", "updated"])
    record(actor, "setting.changed", row, before={"value": before}, after={"value": value})
    return row


DEFAULT_ACCENT = "#1f3a5f"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _relative_luminance(hex_color: str) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_with_white(hex_color: str) -> float:
    """WCAG contrast ratio of white text on the color."""
    return 1.05 / (_relative_luminance(hex_color) + 0.05)


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two colors, whichever is lighter."""
    hi, lo = sorted((_relative_luminance(a), _relative_luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _to_oklab(hex_color: str) -> tuple[float, float, float]:
    def linear(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(int(hex_color[i : i + 2], 16)) for i in (1, 3, 5))
    l_, m, s = (
        (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3),
        (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3),
        (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3),
    )
    return (
        0.2104542553 * l_ + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l_ - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l_ + 0.7827717662 * m - 0.8086757660 * s,
    )


def _from_oklab(L: float, a: float, b: float) -> str:  # noqa: N803 (L is OKLab's name)
    l_, m, s = (
        (L + 0.3963377774 * a + 0.2158037573 * b) ** 3,
        (L - 0.1055613458 * a - 0.0638541728 * b) ** 3,
        (L - 0.0894841775 * a - 1.2914855480 * b) ** 3,
    )
    rgb = (
        4.0767416621 * l_ - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l_ + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l_ - 0.7034186147 * m + 1.7076147010 * s,
    )

    def encode(c: float) -> int:
        c = min(1.0, max(0.0, c))  # ponytail: clipped, where a browser maps into the gamut
        return round(255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055))

    return "#" + "".join(f"{encode(c):02x}" for c in rgb)


def mix_oklab(color: str, other: str, share: float) -> str:
    """CSS `color-mix(in oklab, color share, other)`, so the server can measure what app.css draws."""
    one, two = _to_oklab(color), _to_oklab(other)
    return _from_oklab(*(share * x + (1 - share) * y for x, y in zip(one, two, strict=True)))


# The roles app.css mixes from the club's color (docs/INTERFACE.md, "Color"): (share of the
# club's color, what it is mixed with). Keep in step with app.css's :root; test_shell checks.
ROLE_MIXES = {
    "--accent-soft": (0.09, "#ffffff"),
    "dark --accent": (0.42, "#ffffff"),
    "dark --accent-soft": (0.45, "#111418"),
}
DARK_BG, DARK_ON_ACCENT = "#111418", "#0c1220"


def role_contrasts(brand: str) -> dict[str, float]:
    """Every text-on-color pair the club's color makes, light and dark, as WCAG ratios."""
    soft, accent, dark_soft = (
        mix_oklab(brand, other, share) for share, other in ROLE_MIXES.values()
    )
    return {
        "white on the club color": contrast("#ffffff", brand),
        "the club color on its container": contrast(brand, soft),
        "dark mode's accent on the page": contrast(accent, DARK_BG),
        "text on dark mode's accent": contrast(DARK_ON_ACCENT, accent),
        "dark mode's accent on its container": contrast(accent, dark_soft),
    }


def accent_color() -> str:
    """The club's accent (branding.accent) if it is a six-digit hex color and every pair it
    makes reads at AA (4.5:1, FR-116): white on it (buttons, the sign-in panel), it as text
    on white and on its own tint (links, the active menu entry), and the colors dark mode mixes
    from it (#143). Otherwise the application's default."""
    value = setting("branding.accent")
    if not value or not _HEX.match(str(value)):
        return DEFAULT_ACCENT
    value = str(value).lower()
    low = {pair: round(ratio, 2) for pair, ratio in role_contrasts(value).items() if ratio < 4.5}
    if low:
        log.warning("branding.accent %s fails AA contrast (%s); using the default", value, low)
        return DEFAULT_ACCENT
    return value


BRANDING_IMAGES = (
    "logo",
    "logo_monochrome",
    "favicon",
    "apple_touch_icon",
    "maskable_icon",
    "qsl_card",
)


def branding_url(value: str | None) -> str | None:
    """A branding setting is either a path in the club's static overlay (served hashed through
    the static storage) or, when uploaded from Settings, a file under MEDIA_ROOT/branding/
    served by `ops.views.branding_file`. Either way the templates get a URL."""
    if not value:
        return None
    if value.startswith("media/branding/"):
        from django.urls import reverse

        name = value[len("media/branding/") :]
        path = dj.MEDIA_ROOT / "branding" / name
        stamp = int(path.stat().st_mtime) if path.exists() else 0
        return reverse("branding_file", args=[name]) + f"?v={stamp}"
    from django.templatetags.static import static

    try:
        return static(normalise_static_path(value))
    except ValueError:  # not in the collected manifest: a wrong path in the configuration
        return None


def branding() -> dict[str, str | None]:
    out = {key: branding_url(setting(f"branding.{key}")) for key in BRANDING_IMAGES}
    out["accent"] = accent_color()
    return out


def institution_domains() -> list[str]:
    """The domains that count as the institution's own: the one source for an address's kind,
    the agreement rule, and the field's label (T22, 2026-10-21, found them reading different
    settings). The trusted domains first; older configurations carried it on a member category."""
    domains = [
        str(d).strip().lower().lstrip("@") for d in (setting("trusted_email_domains", []) or [])
    ]
    if any(domains):
        return [d for d in domains if d]
    for c in setting("member_categories", []) or []:
        if isinstance(c, dict) and c.get("email_domain"):
            return [str(c["email_domain"]).strip().lower().lstrip("@")]
    return []


def institution_email_domain() -> str:
    """The institution's domain as the address field names it: the first of
    `institution_domains`, so the label and the rule never disagree."""
    domains = institution_domains()
    return domains[0] if domains else ""
