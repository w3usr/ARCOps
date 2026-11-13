"""Breadcrumb links are not underlined until pointed at or focused (D5, #265): the event page's
"Events" crumb sat underlined right above tabs that carry none. Measured in a browser, because
only a browser computes the style a rule finally gives."""

from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

from apps.events.models import Event


def test_a_crumb_is_underlined_only_under_the_pointer(live_server, engine):
    event = Event.objects.exclude(state="draft").first()  # before Playwright's event loop starts
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/events/{event.pk}/")
        crumb = page.locator(".crumbs a").first
        line = "el => getComputedStyle(el).textDecorationLine"
        at_rest = crumb.evaluate(line)
        crumb.hover()
        hovered = crumb.evaluate(line)
        browser.close()

    assert at_rest == "none"
    assert hovered == "underline"
