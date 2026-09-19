"""
FR-117, TR-36: axe-core over every page of the seeded demo, as each kind of account, at desktop
and phone width. A violation at the serious or critical level fails; so does a page that scrolls
sideways at phone width (FR-95). The pages come from the demo data, so a new page is covered by
adding it to PAGES below (or to seed_demo when it needs a record to exist).

Run: `playwright install chromium` once, then `pytest tools/a11y -o addopts=""`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.django_db(transaction=True)

AXE = (Path(__file__).parent / "axe.min.js").read_text(encoding="utf-8")
PASSWORD = "demo-password-please-change"  # noqa: S105  (the public demo password of seed_demo)
PHONE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 900}
FAIL_ON = {"serious", "critical"}
# Rules that do not apply to a server-rendered page checked in a headless browser, or that axe
# reports for third-party widgets outside our control. Keep this list short and explained.
DISABLED_RULES = {
    "region": "the skip link and banners sit outside a landmark by design",
}


def pages_for(role: str) -> list[str]:
    """Every distinct page a person of this role can reach, from the demo data."""
    from apps.accounts.models import User
    from apps.comms.models import MessageTemplate
    from apps.events.models import Event, SignUp, Slot

    ev = Event.objects.order_by("pk").first()
    slot = (
        Slot.objects.filter(position__location__event=ev, kind="operating")
        .order_by("start")
        .first()
    )
    member = User.objects.by_address("cy@example.org").get()
    minor_su = SignUp.objects.filter(user__under_18=True).first()
    common = [
        "/",
        "/me/",  # forwards to your own member page, which is the profile
        "/me/edit/",
        "/events/mine/",
        "/me/messages/",
        "/events/",
        f"/events/{ev.pk}/",
        f"/events/{ev.pk}/slot/{slot.pk}/",
        "/credentials/agreements/",
        "/credentials/computer-password/",
        "/me/level/",
        "/privacy/",
    ]
    if role == "minor":
        # A member under 18 reads their profile; the guardian edits it while acting (§2.4).
        return [u for u in common if u != "/me/edit/"]
    if role == "member":
        return common
    if role == "guardian":
        return common + ([f"/events/signup/{minor_su.pk}/adults/"] if minor_su else [])
    officer = [
        f"/events/{ev.pk}/manage/",
        f"/events/{ev.pk}/announce/",
        "/events/new/",
        "/events/health/",
        f"/events/{ev.pk}/participation/",
        "/announce/",
        "/announcements/",
        "/me/invitations/",
        "/me/entry-links/",
        "/members/",
        f"/members/{member.pk}/",
        f"/members/{member.pk}/edit/",
        "/members/roster/",
        "/members/hours/",
        "/credentials/access-rosters/",
        "/ops/outbox/",
    ]
    if role == "officer":
        return common + officer
    tpl = MessageTemplate.objects.order_by("pk").first()
    advisor = ["/credentials/approvals/", "/members/archive/"]
    if role == "advisor":
        return common + officer + advisor
    sysadmin = [
        "/ops/status/",
        "/ops/settings/",
        "/ops/groups/",
        "/ops/templates/",
        f"/ops/templates/{tpl.key}/" if tpl else "/ops/templates/",
        "/credentials/computer-password/manage/",
    ]
    return common + officer + advisor + sysadmin


ACCOUNTS = {
    "signed-out": None,
    "member": "cy@example.org",
    "officer": "ben@example.org",
    "advisor": "dee@example.org",
    "sysadmin": "ada@example.org",
    "guardian": "pat@example.org",
    "minor": "kim@example.org",
}


def sign_in(page, base, email, raise_level: bool = False):
    page.goto(f"{base}/accounts/login/")
    page.fill("input[name=login]", email)
    page.fill("input[name=password]", PASSWORD)
    page.click("form button[type=submit], form input[type=submit]")
    page.wait_for_load_state("networkidle")
    assert "/accounts/login" not in page.url, f"sign-in failed for {email}"
    if raise_level:
        # A sysadmin signs in acting at the club's everyday level, so the sysadmin pages are not
        # theirs until they step up (apps/accounts/acting.py). Stepping up is itself a page worth
        # checking, and doing it here is the only way the pages behind it can be.
        page.goto(f"{base}/me/level/")
        page.check("#v-sysadmin")
        page.fill("#pw", PASSWORD)
        # By name, because "form button[type=submit]" also matches Sign out in the sidebar, and
        # the first match at phone width is off screen inside the collapsed menu.
        page.get_by_role("button", name="Act at this level").click()
        page.wait_for_load_state("networkidle")
        assert "/accounts/login" not in page.url, "the step-up signed us out"


def audit(page) -> list[dict]:
    page.add_script_tag(content=AXE)
    result = page.evaluate(
        """async (disabled) => await axe.run(document, {
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] },
            rules: Object.fromEntries(disabled.map((r) => [r, { enabled: false }])),
        })""",
        list(DISABLED_RULES),
    )
    return [v for v in result["violations"] if v["impact"] in FAIL_ON]


def describe(url: str, width: int, violations: list[dict]) -> str:
    lines = [f"{url} at {width}px:"]
    for v in violations:
        targets = "; ".join(",".join(n["target"]) for n in v["nodes"][:3])
        lines.append(
            f"  [{v['impact']}] {v['id']}: {v['help']} ({len(v['nodes'])} node(s): {targets})"
        )
    return "\n".join(lines)


@pytest.mark.parametrize("role", list(ACCOUNTS))
def test_every_page_passes_axe_and_fits_a_phone(live_server, role):
    from playwright.sync_api import sync_playwright

    base = live_server.url
    email = ACCOUNTS[role]
    urls = (
        ["/accounts/login/", "/privacy/", "/accounts/password/reset/"]
        if email is None
        else pages_for(role)
    )
    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for viewport in (DESKTOP, PHONE):
            ctx = browser.new_context(viewport=viewport)
            page = ctx.new_page()
            if email:
                sign_in(page, base, email, raise_level=role == "sysadmin")
            for url in urls:
                r = page.goto(f"{base}{url}")
                # A refusal page is still a page someone reads (the computer password for a
                # member without IT access, for instance); a missing page is a broken list.
                assert r is not None and r.status in (200, 403), (
                    f"{url} answered {r.status if r else 'nothing'} for {role}"
                )
                page.wait_for_load_state("networkidle")
                if viewport is PHONE:
                    wide = page.evaluate(
                        "document.documentElement.scrollWidth > window.innerWidth + 1"
                    )
                    if wide:
                        failures.append(f"{url} at {viewport['width']}px scrolls sideways (FR-95)")
                bad = audit(page)
                if bad:
                    failures.append(describe(url, viewport["width"], bad))
            ctx.close()
        browser.close()
    assert not failures, "\n\n".join(failures)


def test_a_deliberate_violation_is_caught(live_server):
    """The check must be able to fail: an unlabelled input on a synthetic page is reported."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"{live_server.url}/privacy/")
        page.evaluate(
            "document.querySelector('main').insertAdjacentHTML('beforeend', '<form><input type=text name=x></form>')"
        )
        bad = audit(page)
        browser.close()
    assert any(v["id"] == "label" for v in bad), json.dumps([v["id"] for v in bad])
