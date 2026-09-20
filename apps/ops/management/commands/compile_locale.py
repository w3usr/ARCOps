"""Compile the club's message catalogue, without needing gettext on the machine.

`manage.py compilemessages` shells out to GNU gettext's `msgfmt`, which is not installed here or
on the server and is one more thing to provision for a file of a dozen strings. polib does the
same job in Python, so `tools/check.sh` and the deploy both run this and every machine gets the
same result (TR-45).
"""

from __future__ import annotations

from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compile every locale/**/*.po to the .mo Django reads."

    def handle(self, *args, **options) -> None:
        written = 0
        for directory in [Path(p) for p in settings.LOCALE_PATHS]:
            for po_path in sorted(directory.glob("*/LC_MESSAGES/*.po")):
                mo_path = po_path.with_suffix(".mo")
                polib.pofile(str(po_path)).save_as_mofile(str(mo_path))
                written += 1
                self.stdout.write(f"{po_path.relative_to(directory.parent)} -> {mo_path.name}")
        self.stdout.write(f"catalogues compiled: {written}")
