"""A card's first and last lines sit at its padding, with no margin added above or below.

Found on the contact sheet (2026-10-23): on your profile the Email card had visibly more space
under its last line than the License card. Measured in a real browser, because the space is a
margin and the markup does not show it. The space under a card's last line can come from one
level down, a table or paragraph whose margin collapses through its parent (#148); the space
above its first line, from a form's hidden field standing before the heading (#149).
"""

import pytest
from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

# The space above the highest and under the lowest thing drawn in each card, less its padding:
# its text and controls, the leaves, so a list item's own padding counts as space too. Text is
# measured itself, since a paragraph's last line can run on past its last link. What is inside a
# closed <details> is not drawn, apart from its summary.
EXTRA = """() => [...document.querySelectorAll('.card')].filter(c => c.offsetParent).map(c => {
    const cs = getComputedStyle(c), box = c.getBoundingClientRect();
    let top = box.bottom, bottom = box.top;
    const reach = r => { if (r.height) { top = Math.min(top, r.top); bottom = Math.max(bottom, r.bottom); } };
    for (const el of c.querySelectorAll('*')) {
        const closed = el.parentElement.closest('details:not([open])');
        if (closed && closed !== c && !el.closest('summary')) continue;
        if (!el.children.length || el.matches('select, button, summary')) { reach(el.getBoundingClientRect()); continue; }
        for (const n of el.childNodes) {
            if (n.nodeType !== Node.TEXT_NODE || !n.textContent.trim()) continue;
            const text = document.createRange();
            text.selectNodeContents(n);
            reach(text.getBoundingClientRect());
        }
    }
    const above = top - box.top - parseFloat(cs.borderTopWidth) - parseFloat(cs.paddingTop);
    const under = box.bottom - parseFloat(cs.borderBottomWidth) - bottom - parseFloat(cs.paddingBottom);
    return {card: (c.querySelector('h2, h3') || c).textContent.trim().slice(0, 40),
            above: Math.round(above), under: Math.round(under)};
})"""

# The pages where a card ended or began with a margin, by the account that reaches them.
PAGES = {
    "member": ["/me/", "/me/edit/", "/me/messages/"],
    "advisor": ["/credentials/approvals/"],
    "sysadmin": [
        "/ops/status/",
        "/ops/templates/invitation/",
        "/credentials/computer-password/manage/",
    ],
}


@pytest.mark.parametrize("role", list(PAGES))
def test_a_card_begins_and_ends_with_its_padding(live_server, engine, role):
    uneven = []
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS[role], raise_level=role == "sysadmin")
        for url in PAGES[role]:
            page.goto(f"{live_server.url}{url}")  # /me/ forwards to the member's own page
            cards = page.evaluate(EXTRA)
            assert cards, f"{url} has cards"
            # An inline leaf (a <strong> in a line) sits a few pixels inside its line's height;
            # a margin or a list item's padding is 12 px or more.
            uneven += [(url, c) for c in cards if c["above"] > 4 or c["under"] > 4]
        browser.close()

    assert not uneven, f"space above the first line or under the last beyond the padding: {uneven}"
