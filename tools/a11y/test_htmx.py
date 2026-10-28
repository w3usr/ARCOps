"""htmx runs with the settings in the base template's meta tag (technical addendum A7).

Each of them keeps something out: eval, which the security policy would refuse anyway; scripts
in a swapped response; a <style> htmx would otherwise inject; requests to other sites; and copies
of whole pages, member names and rosters among them, in localStorage.
"""

from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

CONFIG = """() => ({
    allowEval: htmx.config.allowEval,
    allowScriptTags: htmx.config.allowScriptTags,
    includeIndicatorStyles: htmx.config.includeIndicatorStyles,
    historyCacheSize: htmx.config.historyCacheSize,
    selfRequestsOnly: htmx.config.selfRequestsOnly,
    injectedStyle: [...document.querySelectorAll('style')].some(s => s.textContent.includes('htmx-indicator')),
})"""


def test_htmx_runs_with_the_configured_settings(live_server, engine):
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page()
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/events/")
        found = page.evaluate(CONFIG)
        browser.close()

    assert found == {
        "allowEval": False,
        "allowScriptTags": False,
        "includeIndicatorStyles": False,
        "historyCacheSize": 0,
        "selfRequestsOnly": True,
        "injectedStyle": False,
    }
