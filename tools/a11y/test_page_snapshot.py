"""What every page draws, as data, so a change meant to alter no page can be shown to alter none.

For each role and each page it reaches, at 390 and 1280 px, it records the page's visible text
and, for every element in the body, a hash of its computed style and its box. Take one before a
change and one after, then compare:

    pytest tools/a11y/test_page_snapshot.py -o addopts="" -n auto --page-snapshot=var/snap-before
    pytest tools/a11y/test_page_snapshot.py -o addopts="" -n auto --page-snapshot=var/snap-after
    python tools/a11y/compare_snapshots.py var/snap-before var/snap-after

It renders only what a page shows on arrival: a dialog opened by script, a confirmation page,
an error state, mail and the agreement's PDF are outside it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_axe import ACCOUNTS, DESKTOP, PHONE, pages_for, sign_in

pytestmark = pytest.mark.django_db(transaction=True)

SIGNED_OUT = ["/accounts/login/", "/privacy/", "/accounts/password/reset/"]

# Each element: a path that names it, a hash of every computed property, and its rounded box.
WALK = """() => {
  const hash = s => { let h = 5381; for (let i = 0; i < s.length; i++) h = (h * 33 ^ s.charCodeAt(i)) >>> 0; return h; };
  const path = el => { const p = []; for (; el && el !== document.body; el = el.parentElement) {
    p.unshift(el.tagName.toLowerCase() + ':' + Array.prototype.indexOf.call(el.parentElement.children, el)); }
    return p.join('>'); };
  const els = [...document.body.querySelectorAll('*')].map(el => {
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    // Sorted: Chromium lists custom properties in a different order from run to run. And url(...)
    // values are absolute, with the test server's port in them.
    const s = [...cs].map(k => k + ':' + cs.getPropertyValue(k)).sort().join(';');
    return [path(el), hash(s.split(location.origin).join('')), [r.x, r.y, r.width, r.height].map(Math.round)];
  });
  return {text: document.body.innerText, els};
}"""


@pytest.mark.contact_sheet
@pytest.mark.parametrize("role", list(ACCOUNTS))
def test_write_a_page_snapshot(live_server, request, role):
    out = request.config.getoption("--page-snapshot", default=None)
    if not out:
        pytest.skip("run with --page-snapshot=DIR")
    from playwright.sync_api import sync_playwright

    email = ACCOUNTS[role]
    urls = SIGNED_OUT if email is None else pages_for(role)  # before Playwright: see the sheet
    taken: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for viewport in (DESKTOP, PHONE):
            ctx = browser.new_context(viewport=viewport)
            page = ctx.new_page()
            if email:
                sign_in(page, live_server.url, email, raise_level=role == "sysadmin")
            for url in urls:
                page.goto(f"{live_server.url}{url}")
                page.wait_for_load_state("networkidle")
                taken[f"{url}@{viewport['width']}"] = page.evaluate(WALK)
            ctx.close()
        browser.close()
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / f"{role}.json").write_text(json.dumps(taken), encoding="utf-8")
    assert taken
