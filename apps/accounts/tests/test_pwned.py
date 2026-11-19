"""TR-15, REQUIREMENTS §2.6 (private tracker 292): a breached password is refused; the network is
faked, so no test ever calls Have I Been Pwned."""

import hashlib
import io
import urllib.error

import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.accounts import pwned

PASSWORD = "correct-horse-battery-staple"
DIGEST = hashlib.sha1(PASSWORD.encode()).hexdigest().upper()


@pytest.fixture
def reply(monkeypatch):
    """Answer the range API with `lines`, or raise `error`; record what was asked."""
    asked = []

    def answer(lines=(), error=None):
        def urlopen(req, timeout):
            asked.append(req)
            if error:
                raise error
            return io.BytesIO("\r\n".join(lines).encode())

        monkeypatch.setattr(pwned.urllib.request, "urlopen", urlopen)
        return asked

    return answer


def test_a_breached_password_is_refused_and_only_five_characters_leave(reply):
    asked = reply(["0000000000000000000000000000000000A:0", f"{DIGEST[5:]}:3861493"])
    with pytest.raises(ValidationError) as err:
        pwned.PwnedPasswordValidator().validate(PASSWORD)
    assert err.value.code == "password_pwned"
    assert asked[0].full_url == pwned.RANGE_API + DIGEST[:5]
    assert asked[0].get_header("Add-padding") == "true"


def test_a_padding_decoy_or_an_absent_hash_is_accepted(reply):
    reply([f"{DIGEST[5:]}:0", "0000000000000000000000000000000000A:12"])
    pwned.PwnedPasswordValidator().validate(PASSWORD)
    reply(["0000000000000000000000000000000000A:12"])
    pwned.PwnedPasswordValidator().validate(PASSWORD)


def test_an_unreachable_service_lets_the_password_through_and_says_so(reply, caplog):
    reply(error=urllib.error.URLError("no route"))
    pwned.PwnedPasswordValidator().validate(PASSWORD)
    assert "breached-password check skipped" in caplog.text


def test_it_runs_with_the_real_validators(reply):
    from config.settings import base

    assert "apps.accounts.pwned.PwnedPasswordValidator" in [
        v["NAME"] for v in base.AUTH_PASSWORD_VALIDATORS
    ]
    reply([f"{DIGEST[5:]}:7"])
    with override_settings(AUTH_PASSWORD_VALIDATORS=base.AUTH_PASSWORD_VALIDATORS):
        with pytest.raises(ValidationError) as err:
            validate_password(PASSWORD)
    assert "data breach" in " ".join(err.value.messages)
