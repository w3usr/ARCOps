"""
An email backend that honours the club's "email delivery" switch (FR-105).

Everything the application composes goes through the outbox, which already checks the switch.
This backend is the belt to that brace: anything else that tries to send mail (a framework's
password-reset message, say) is swallowed and logged while delivery is off, so no request can
fail because the mail path is not there yet.
"""

import logging

from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

from apps.ops.config import setting

log = logging.getLogger(__name__)


class GatedSMTPBackend(SMTPBackend):
    def send_messages(self, email_messages):
        if str(setting("defaults.email_delivery", "off")).lower() != "on":
            for m in email_messages:
                log.info("email delivery off; not sent: %r to %s", m.subject, m.to)
            return 0
        return super().send_messages(email_messages)
