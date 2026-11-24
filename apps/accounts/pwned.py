"""A password that has appeared in a known data breach is refused (TR-15; REQUIREMENTS §2.6).

Have I Been Pwned's range API: only the first five characters of the password's SHA-1 leave the
server, and the answer is every breached hash starting with them, padded with decoys (count 0) so
the reply's size gives nothing away either. If the service cannot be reached the password is
accepted and the miss logged: a member is never kept from setting a password by a third party.
"""

import hashlib
import logging
import urllib.request

from django.core.exceptions import ValidationError

log = logging.getLogger(__name__)
RANGE_API = "https://api.pwnedpasswords.com/range/"


class PwnedPasswordValidator:
    def validate(self, password, user=None):
        digest = hashlib.sha1(password.encode()).hexdigest().upper()  # noqa: S324 - the API's scheme
        req = urllib.request.Request(  # noqa: S310 - fixed https host
            RANGE_API + digest[:5], headers={"Add-Padding": "true", "User-Agent": "ARCOps"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                body = resp.read().decode()
        except (OSError, ValueError) as exc:  # URLError, timeouts, a bad reply
            log.warning("breached-password check skipped: %s", exc)
            return
        for line in body.splitlines():
            suffix, _, count = line.strip().partition(":")
            if suffix == digest[5:] and count.strip() not in ("", "0"):
                raise ValidationError(
                    "This password has appeared in a data breach on another site, so it is among "
                    "the first an attacker tries. Choose a different one.",
                    code="password_pwned",
                )

    def get_help_text(self):
        return "Not one that has appeared in a known data breach."
