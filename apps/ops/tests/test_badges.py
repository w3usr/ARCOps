"""Badges (#226): every tone's word reads at 4.5:1 on its fill, light and dark, measured from the
colors app.css draws; and the state-to-tone map gives a class for each state it names."""

import re
from pathlib import Path

from apps.events.models import Event
from apps.ops.config import contrast, mix_oklab
from apps.ops.templatetags.badges import TONES, tone

CSS = (Path(__file__).resolve().parents[3] / "static" / "css" / "app.css").read_text()
LIGHT, DARK = CSS.split("@media (prefers-color-scheme: dark)", 1)


def _value(block: str, name: str) -> str:
    """A token's color in a theme: the dark block's own value, else the light one, with any
    var() in it resolved in the theme, as the browser does."""
    found = re.search(rf"{name}: ([^;]+);", block) or re.search(rf"{name}: ([^;]+);", LIGHT)
    raw = found[1].strip()
    if raw.startswith("color-mix"):  # the club's color mixed, as config.py measures it
        share, other = re.search(r"var\(--brand\) (\d+)%, (#[0-9a-f]{6})", raw).groups()
        return mix_oklab(re.search(r"--brand: (#[0-9a-f]{6})", LIGHT)[1], other, int(share) / 100)
    if raw.startswith("var("):
        return _value(block, raw[4:-1])
    return raw


def test_every_tone_reads_on_its_fill_in_both_themes():
    pairs = {
        "neutral": ("--muted", "--tag-neutral"),
        "ok": ("--ok", "--tag-ok"),
        "warn": ("--warn", "--tag-warn"),
        "bad": ("--bad", "--tag-bad"),
        "info": ("--accent-soft-fg", "--tag-info"),
    }
    low = {
        (scheme, name): round(contrast(_value(block, fg), _value(block, bg)), 2)
        for scheme, block in (("light", LIGHT), ("dark", DARK))
        for name, (fg, bg) in pairs.items()
    }
    assert all(r >= 4.5 for r in low.values()), low


def test_each_event_state_has_a_tone_and_unknown_ones_are_neutral():
    assert set(TONES["event"]) == set(Event.State.values)
    assert tone(Event.State.PUBLISHED, "event") == "ok" and tone("cancelled", "event") == "bad"
    assert tone("anything", "event") == "" and tone("draft", "nobody") == ""
