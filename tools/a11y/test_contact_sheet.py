"""A picture of every page, so the interface can be reviewed by eye in one pass.

The axe sweep beside this file says whether a page is usable. It cannot say whether a page
reads well, and that is what the 2026-09-17 interface review was about. This writes one
screenshot per page per width into a gitignored directory and an index.html that lays them out
side by side.

It is skipped unless asked for, because it is slow and produces nothing the build needs:

    pytest tools/a11y/test_contact_sheet.py -o addopts="" --contact-sheet
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_axe import ACCOUNTS, DESKTOP, PHONE, pages_for, sign_in

pytestmark = pytest.mark.django_db(transaction=True)

OUT = Path(__file__).resolve().parents[2] / "var" / "contact-sheet"


def _name(role: str, url: str, width: int) -> str:
    slug = url.strip("/").replace("/", "-") or "home"
    return f"{role}--{slug}--{width}.png"


@pytest.mark.contact_sheet
def test_write_a_contact_sheet(live_server, request):
    if not request.config.getoption("--contact-sheet", default=False):
        pytest.skip("run with --contact-sheet")
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    shots: list[tuple[str, str, str, str]] = []  # role, url, desktop file, phone file
    # Every query runs before Playwright starts: inside its greenlet loop Django refuses a
    # synchronous query.
    by_role = {
        role: (
            ["/accounts/login/", "/privacy/", "/accounts/password/reset/"]
            if email is None
            else pages_for(role)
        )
        for role, email in ACCOUNTS.items()
    }

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for role, email in ACCOUNTS.items():
            urls = by_role[role]
            taken: dict[str, dict[int, str]] = {}
            for viewport in (DESKTOP, PHONE):
                ctx = browser.new_context(viewport=viewport)
                page = ctx.new_page()
                if email:
                    sign_in(page, live_server.url, email, raise_level=role == "sysadmin")
                for url in urls:
                    page.goto(f"{live_server.url}{url}")
                    page.wait_for_load_state("networkidle")
                    name = _name(role, url, viewport["width"])
                    page.screenshot(path=str(OUT / name), full_page=True)
                    taken.setdefault(url, {})[viewport["width"]] = name
                ctx.close()
            for url, by_width in taken.items():
                shots.append((role, url, by_width.get(1280, ""), by_width.get(390, "")))
        browser.close()

    (OUT / "index.html").write_text(_index(shots), encoding="utf-8")
    print(f"\ncontact sheet: {OUT / 'index.html'} ({len(shots)} pages)")
    assert shots


def _index(shots) -> str:
    rows = []
    for role, url, desktop, phone in shots:
        rows.append(
            f"<section><h2>{role} · <code>{url}</code></h2>"
            f'<div class="pair"><figure><figcaption>1280px</figcaption>'
            f'<img src="{desktop}" alt="{url} at 1280px" loading="lazy"></figure>'
            f'<figure><figcaption>390px</figcaption>'
            f'<img src="{phone}" alt="{url} at 390px" loading="lazy"></figure></div></section>'
        )
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Contact sheet</title><style>"
        "body{font:16px/1.5 system-ui;margin:2rem;max-width:80rem}"
        "section{margin:2rem 0;border-top:1px solid #ccc;padding-top:1rem}"
        ".pair{display:flex;gap:1rem;align-items:flex-start}"
        "figure{margin:0;flex:1}figure:last-child{flex:0 0 390px}"
        "img{width:100%;border:1px solid #ccc}"
        "figcaption{font-size:.85rem;color:#555}"
        "</style></head><body><h1>Every page, at both widths</h1>"
        + "".join(rows)
        + "</body></html>"
    )
