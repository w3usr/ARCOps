"""What SK found on a phone on 2026-10-22, before the beta: buttons that wrap without a gap,
a bullet beside each message, the roster key run together on one line, and the join pages laid
out unlike sign-in. Measured in a real browser in each engine, because each is a layout question.
"""

from datetime import timedelta

from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file

PHONE = {"width": 390, "height": 844}

# Every button-like control in the page content, with its box and its parent.
BUTTONS = """() => [...document.querySelectorAll('main a.button, main button')]
  .filter(b => b.offsetParent !== null)
  .map(b => { const r = b.getBoundingClientRect();
              return {parent: b.parentElement, top: r.top, bottom: r.bottom, text: b.textContent.trim()}; })"""

TOUCHING = (
    BUTTONS
    + """.reduce((bad, b, i, all) => {
    for (const a of all.slice(0, i)) {
      if (a.parent === b.parent && b.top > a.top + 1 && b.top - a.bottom < 4)
        bad.push(`${a.text} / ${b.text}: ${Math.round(b.top - a.bottom)}px`);
    }
    return bad; }, [])"""
)


def test_wrapped_buttons_keep_a_gap_between_lines(live_server, engine):
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport=PHONE)
        sign_in(page, live_server.url, ACCOUNTS["advisor"])
        found = {}
        for path in ("/members/", "/members/roster/"):
            page.goto(live_server.url + path)
            found[path] = page.evaluate(TOUCHING)
        browser.close()
    assert found == {"/members/": [], "/members/roster/": []}, found


def test_messages_carry_no_bullet(live_server, engine):
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport=PHONE)
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/me/messages/")
        marker = page.evaluate(
            "() => getComputedStyle(document.querySelector('.msglist > li')).listStyleType"
        )
        browser.close()
    assert marker == "none"


def test_the_roster_key_is_labelled_and_one_entry_a_line_on_a_phone(live_server, engine):
    from apps.events.models import Event

    event = Event.objects.filter(state=Event.State.PUBLISHED).order_by("pk").first()
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport=PHONE)
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/events/{event.pk}/")
        label = page.locator(".legend .legend-label").inner_text().strip()
        tops = page.evaluate(
            "() => [...document.querySelectorAll('.legend li')].map(li => li.getBoundingClientRect().top)"
        )
        browser.close()
    assert label == "Key", "the key says what it is, for everyone (#132's finding)"
    assert len(tops) >= 4 and len(set(round(t) for t in tops)) == len(tops), (
        "each entry on its own line"
    )


def test_the_join_pages_are_laid_out_like_sign_in(live_server, engine):
    from django.utils import timezone

    from apps.accounts import entry
    from apps.accounts.models import User
    from apps.accounts.services import create_invitation

    officer = User.objects.by_address(ACCOUNTS["officer"]).get()
    inv = create_invitation(officer, "beta.tester@example.org", "student")
    link = entry.create_link(
        officer, label="BETA", kind="class", expires_at=timezone.now() + timedelta(days=30)
    )
    pages = {"invitation": f"/me/invite/{inv.token}/", "entry link": f"/join/{link.token}/form/"}
    placed = {}
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        for width in (1280, 390):
            page = browser.new_page(viewport={"width": width, "height": 900})
            for name, path in pages.items():
                page.goto(live_server.url + path)
                placed[(name, width)] = page.locator(".auth-card form").count() == 1
            page.close()
        browser.close()
    assert all(placed.values()), placed
