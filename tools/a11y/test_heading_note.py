"""The rich-text editor says so when a heading level is skipped (FR-115).

Found by the acceptance walk of T45 on 2026-10-19: the note never appeared on any page. The
editors are started by django-tinymce's script, which runs before static/js/richtext-check.js,
so the check's listener for newly added editors heard none of them. Measured in a real browser,
because only the order the scripts run in shows the fault.
"""

from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

READY = "() => !!window.tinymce && tinymce.get('id_description_html') && tinymce.get('id_description_html').initialized"


def test_a_skipped_heading_level_is_noted_beneath_the_editor(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["officer"])
        page.goto(f"{live_server.url}/events/new/")
        page.wait_for_function(READY)
        set_content = "html => tinymce.get('id_description_html').setContent(html)"
        page.evaluate(set_content, "<h1>One</h1><h3>Three</h3>")
        skipped = page.locator(".heading-note").first.inner_text()
        page.evaluate(set_content, "<h1>One</h1><h2>Two</h2>")
        in_order = page.locator(".heading-note").first.inner_text()
        browser.close()

    assert skipped.startswith("A heading level is skipped"), (
        "Heading 1 straight to Heading 3 is noted"
    )
    assert in_order == "", "and the note clears once the levels are in order"
