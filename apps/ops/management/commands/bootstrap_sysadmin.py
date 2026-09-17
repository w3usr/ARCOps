"""
bootstrap_sysadmin: create (or promote) the first sysadmin with a one-time temporary password.

    manage.py bootstrap_sysadmin --email who@example.org --first Ada --last Lovelace [--callsign N0CALL]

The temporary password is printed once (FR-7); it must be changed at first sign-in. Nothing
is emailed. Re-running for an existing address promotes the account and issues a new
temporary password.
"""

import secrets

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.ops.audit import record


class Command(BaseCommand):
    help = "Create or promote a sysadmin and print a one-time temporary password."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--first", required=True)
        parser.add_argument("--last", required=True)
        parser.add_argument("--callsign", default="")
        parser.add_argument("--category", default="faculty")

    def handle(self, *args, **opts):
        password = secrets.token_urlsafe(12)
        address = opts["email"].lower().strip()
        user = User.objects.by_address(address).first()
        created = user is None
        if created:
            # The address is confirmed because whoever runs this command at the server console
            # is vouching for it, and the account must be able to sign in with it at once.
            user = User.objects.create_user(
                address,
                None,
                first_name=opts["first"],
                last_name=opts["last"],
                callsign=opts["callsign"].upper(),
                category=opts["category"],
                is_superuser=True,
            )
        user.is_superuser = True  # the Django admin, and every capability
        user.is_active = True
        user.password_is_temporary = True
        user.set_password(password)
        user.save()
        record(None, "sysadmin.bootstrap", user, after={"created": created})
        self.stdout.write(f"{'created' if created else 'promoted'} sysadmin {user.email}")
        self.stdout.write(
            f"one-time temporary password (shown once, change at first sign-in): {password}"
        )
