"""Skip to content moves focus into the page, not only the scroll position (WCAG 2.4.1).

Found by SK on 2026-10-22 with VoiceOver in Firefox: after Skip to content, VoiceOver read the
sidebar again. `<main>` could not take focus, so following the link scrolled the page and left
focus, which VoiceOver follows, where it was. Measured in a real browser, because only a browser
decides where focus goes.
"""

from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file


def test_skip_to_content_puts_focus_on_the_page_content(live_server, engine):
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/events/")
        # Safari's Tab skips links unless "Press Tab to highlight each item" is on; Option-Tab
        # reaches them, which is what a keyboard user there presses.
        tab = "Alt+Tab" if engine == "webkit" else "Tab"
        page.keyboard.press(tab)
        first = page.evaluate("() => document.activeElement.textContent.trim()")
        page.keyboard.press("Enter")
        landed = page.evaluate("() => document.activeElement.id")
        page.keyboard.press(tab)
        inside = page.evaluate("() => !!document.activeElement.closest('main')")
        browser.close()

    assert first == "Skip to content", "the skip link is the first thing Tab reaches"
    assert landed == "main", "following it puts focus on the page content"
    assert inside, "and the next Tab stays in the content, not back in the sidebar"
