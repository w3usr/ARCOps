"""
club_import: load a configuration directory (config/ or an overlay) into the database.

    manage.py club_import                  the overlay if configured, else config/
    manage.py club_import /path/to/dir     an explicit directory
    manage.py club_import --reset          overwrite values a sysadmin changed in the interface

Idempotent. Settings are written by dotted key (TR-32). Agreement templates are versioned by
content hash (FR-21, FR-30): an unchanged file is a no-op, a changed file becomes a new
current version, and signed records keep pointing at the version they signed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import nh3
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.credentials.models import AgreementTemplate, CredentialType
from apps.ops.config import config_dir, flatten, load_yaml
from apps.ops.models import ClubSetting

ALLOWED_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "p",
    "ol",
    "ul",
    "li",
    "strong",
    "em",
    "a",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "br",
    "blockquote",
}


def sanitise(html: str) -> str:
    return nh3.clean(
        html, tags=ALLOWED_TAGS, attributes={"a": {"href"}, "th": {"scope"}}, link_rel="noopener"
    )


class Command(BaseCommand):
    help = "Load club.yaml and agreement templates from a configuration directory."

    def add_arguments(self, parser):
        parser.add_argument("directory", nargs="?", help="configuration directory")
        parser.add_argument("--reset", action="store_true", help="overwrite interface edits")
        parser.add_argument(
            "--resign-by",
            help="FR-30: signers of the earlier version of any agreement republished in this run must re-sign by this date (YYYY-MM-DD); default: existing approvals stand until their own expiry",
        )

    def handle(self, *args, **opts):
        directory = Path(opts["directory"]) if opts["directory"] else config_dir()
        try:
            data = load_yaml(directory)
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        created = updated = kept = 0
        for key, value in flatten({k: v for k, v in data.items() if k != "agreements"}).items():
            obj, was_created = ClubSetting.objects.get_or_create(key=key, defaults={"value": value})
            if was_created:
                created += 1
            elif obj.source == "interface" and not opts["reset"]:
                kept += 1
            elif obj.value != value:
                obj.value, obj.source = value, "import"
                obj.save(update_fields=["value", "source", "updated"])
                updated += 1
        self.stdout.write(
            f"settings: {created} created, {updated} updated, {kept} kept (interface edits)"
        )

        for ct in data.get("credential_types", []):
            CredentialType.objects.update_or_create(
                key=ct["key"],
                defaults={
                    "label": ct.get("label", ct["key"]),
                    "established_by": ct.get("established_by", "agreement"),
                    "graded": bool(ct.get("graded", False)),
                    "default_expiry": ct.get("default_expiry", "one_year"),
                },
            )

        new_versions = 0
        for ag in data.get("agreements", []):
            path = directory / ag["file"]
            if not path.exists():
                self.stderr.write(f"agreement file missing, skipped: {path}")
                continue
            html = sanitise(path.read_text(encoding="utf-8"))
            digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
            try:
                credential = CredentialType.objects.get(key=ag["credential"])
            except CredentialType.DoesNotExist as exc:
                raise CommandError(
                    f"agreement {ag['key']} names unknown credential {ag['credential']}"
                ) from exc
            current = AgreementTemplate.objects.filter(key=ag["key"], is_current=True).first()
            if current and current.content_hash == digest:
                current.title, current.audience = (
                    ag.get("title", current.title),
                    ag.get("audience", []),
                )
                current.save(update_fields=["title", "audience"])
                continue
            version = (current.version + 1) if current else 1
            if current:
                current.is_current = False
                current.save(update_fields=["is_current"])
            from django.utils.dateparse import parse_date

            AgreementTemplate.objects.create(
                key=ag["key"],
                credential=credential,
                title=ag.get("title", ag["key"]),
                audience=ag.get("audience", []),
                version=version,
                content_hash=digest,
                html=html,
                effective_date=timezone.now().date(),
                is_current=True,
                resign_by=parse_date(opts["resign_by"])
                if (current and opts.get("resign_by"))
                else None,
            )
            new_versions += 1
        self.stdout.write(f"agreements: {new_versions} new version(s) from {directory}")

        from apps.comms.services import seed_templates

        c, u, k = seed_templates(reset=opts["reset"])
        self.stdout.write(
            f"message templates: {c} created, {u} updated, {k} kept (interface edits)"
        )
