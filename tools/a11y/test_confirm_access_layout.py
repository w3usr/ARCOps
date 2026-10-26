"""Confirm Access is laid out like the sign-in page: Confirm, and the passkey under it.

Found running T51 step 3 (2026-10-21): with a passkey on the account, Use a passkey sat on
Confirm's row, to its right, where the sign-in page stacks its passkey button full width under
Sign in. Measured in a real browser, because the library's forms are `display: contents` and
the markup alone cannot say where the buttons land.
"""

from playwright.sync_api import sync_playwright
from test_axe import ACCOUNTS, sign_in  # the sweep lives beside this file


def test_the_passkey_sits_under_confirm_at_its_width(live_server, engine, monkeypatch):
    from allauth.mfa.models import Authenticator
    from allauth.mfa.webauthn.internal import auth as webauthn_auth

    from apps.accounts.models import User

    # The page asks the library for a challenge; a browser test has no authenticator to answer.
    monkeypatch.setattr(webauthn_auth, "begin_authentication", lambda user: {"challenge": "x"})
    user = User.objects.get(emailaddress__email=ACCOUNTS["member"])
    Authenticator.objects.create(
        user=user, type=Authenticator.Type.WEBAUTHN, data={"name": "Key", "credential": {}}
    )
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in(page, live_server.url, ACCOUNTS["member"])
        page.goto(f"{live_server.url}/accounts/reauthenticate/")
        confirm, passkey = (
            page.locator(f"main button:has-text('{label}')").bounding_box()
            for label in ("Confirm", "Use a passkey")
        )
        field = page.locator("main input[name=password]").bounding_box()
        browser.close()

    assert round(confirm["x"]) == round(passkey["x"]), "they start at the same edge"
    assert round(confirm["width"]) == round(passkey["width"]), "and are as wide as each other"
    assert passkey["y"] >= confirm["y"] + confirm["height"], "the passkey is under Confirm"
    assert round(confirm["width"]) == round(field["width"]), "as wide as the password above"
