"""Signing out leaves no offline copy of the member's own pages (FR-96, §5.7).

My schedule and My messages are kept for reading offline. On a shared machine, the station's
computer, the next person must not find them there after the member signs out, online or off.
"""

import time

import pytest
from playwright.sync_api import Error, TimeoutError, sync_playwright
from test_axe import ACCOUNTS, sign_in

PAGES = ("/events/mine/", "/me/messages/")
CACHED = "async p => { for (const k of await caches.keys()) if (await (await caches.open(k)).match(p, {ignoreSearch: true})) return true; return false; }"


def _cached(page, want: bool, seconds: float = 10) -> list[bool]:
    """Whether each page is in the cache, waiting up to `seconds` for it to be `want` for both.
    The service worker writes and deletes after the page has loaded."""
    end = time.monotonic() + seconds
    while True:
        got = [page.evaluate(CACHED, path) for path in PAGES]
        if got == [want, want] or time.monotonic() > end:
            return got
        page.wait_for_timeout(100)


def test_signing_out_clears_the_offline_pages(live_server, engine):
    base = live_server.url
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        sign_in(page, base, ACCOUNTS["member"])
        page.goto(f"{base}/")
        try:
            page.wait_for_function(
                "() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)",
                timeout=10_000,
            )
        except TimeoutError:
            browser.close()
            if engine == "firefox":  # seen on CI: the page never comes under the worker there
                pytest.skip("Playwright's Firefox runs no service worker for this page")
            raise
        for path in PAGES:
            page.goto(f"{base}{path}")
        kept = _cached(page, True)

        page.get_by_role("button", name="Sign out").click()
        page.wait_for_url("**/accounts/login/**")
        left = _cached(page, False)
        ctx.set_offline(True)
        shown = []
        for path in PAGES:
            try:
                page.goto(f"{base}{path}")
                shown.append(page.content())
            except Error:
                shown.append("")
        browser.close()

    assert kept == [True, True], "signed in, both pages are kept for offline reading"
    assert left == [False, False], "signing out removes both"
    assert not any("N0CAN" in body for body in shown), "signed out and offline, neither is shown"
