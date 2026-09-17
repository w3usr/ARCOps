"""
What a person may do, one item at a time.

The advisor, 2026-09-17: *"I am thinking the correct way to do this is actually have access be
item-by-item, and then define configurable access groups (member, officer, faculty advisor,
etc). Systemic is superuser."*

So this module holds the list of capabilities, and nothing else decides who has one. A group is
a named set of them, seeded from the club's configuration and editable afterwards, which is what
lets a club invent a role this application has never heard of. A sysadmin is a Django superuser
and holds every capability by definition.

Two kinds of rule are deliberately **not** here:

* **Whether the account may be used at all.** Signing in, the verification deadline, a minor's
  read-only session, and the archive are states of an account, not things it may do. An account
  in no group can hold no capability, which is what "no access" means now.
* **Rules about a particular record.** Captain of *this* event, guardian of *this* minor, the
  owner of *this* sign-up. Those depend on the row in front of you, and they stay in the code
  that knows about the row.

Adding a capability: put it in `CAPABILITIES`, add it to the groups that should hold it in
`config/club.example.yaml`, and use it. `manage.py sync_permissions` writes any new one into the
database, and the deploy runs it.
"""

from __future__ import annotations

# Each entry is (codename, what it lets someone do, in the words the settings page shows).
CAPABILITIES: list[tuple[str, str]] = [
    # the club's people
    ("view_directory", "See the member directory"),
    ("view_member_records", "Open a member's page, with their contact details and standing"),
    ("invite_members", "Send invitations and manage entry links"),
    ("set_club_position", "Set another member's club position"),
    ("edit_member_privileges", "Edit another member's category, name, and student details"),
    ("assign_groups", "Decide which groups an account is in"),
    ("manage_groups", "Create and change the groups themselves"),
    ("manage_member_addresses", "Add, confirm, or remove the addresses on another account"),
    ("issue_temporary_password", "Issue a one-time password for someone who cannot get in"),
    ("archive_members", "Archive a member who has left, and bring one back"),
    ("view_archive", "Read the archive of former members"),
    ("delete_accounts", "Delete an account outright"),
    ("impersonate_members", "View the site as another member, read-only"),
    # licenses and access to the station
    ("override_license", "Override a license class, status, or expiry"),
    ("approve_agreements", "Approve a signed access agreement, and revoke an approval"),
    ("convert_minor_accounts", "Convert a member's account to an adult's at 18"),
    ("rotate_shared_secret", "Set or rotate the computer password"),
    # events
    ("create_events", "Create an event and import from the calendar"),
    ("manage_events", "Edit any event, its slots, and its captains"),
    ("manage_signups", "Move, remove, or check in another person's sign-up"),
    ("view_participant_contacts", "See the phone and email of people on a roster"),
    # messages
    ("send_announcements", "Send an announcement to members"),
    ("view_outbox", "Read the outbox of everything the site has sent"),
    # the club's records
    ("view_reports", "View and export participation, hours, and credential reports"),
    ("view_audit_log", "Read the audit log"),
    ("edit_club_settings", "Edit the club's configuration and message templates"),
    ("view_job_status", "See the scheduled jobs and their last runs"),
]

CODENAMES = [code for code, _ in CAPABILITIES]
LABELS = dict(CAPABILITIES)

# The permissions hang on this app, so a codename is written "ops.approve_agreements".
APP_LABEL = "ops"


def full(codename: str) -> str:
    return f"{APP_LABEL}.{codename}"


def ensure_permissions(permission_model=None, content_type_model=None) -> int:
    """Write any capability that has no permission row yet, and correct the labels.

    Django creates permissions from a model's frozen Meta, so a capability added after a
    migration was written would never appear. This reads the list above instead, which is the
    one place capabilities are declared. `club_import` calls it, and so does the deploy.
    """
    from django.contrib.auth.models import Permission as LivePermission
    from django.contrib.contenttypes.models import ContentType as LiveContentType

    Permission = permission_model or LivePermission
    ContentType = content_type_model or LiveContentType

    content_type, _ = ContentType.objects.get_or_create(app_label=APP_LABEL, model="capability")
    written = 0
    for codename, label in CAPABILITIES:
        row, created = Permission.objects.get_or_create(
            content_type=content_type, codename=codename, defaults={"name": label}
        )
        if created:
            written += 1
        elif row.name != label:
            row.name = label
            row.save(update_fields=["name"])
    return written


def holds(user, codename: str) -> bool:
    """Whether this person holds a capability. A superuser holds every one; an account that
    cannot be used holds none, which Django's own backend already enforces."""
    return bool(getattr(user, "is_authenticated", False)) and user.has_perm(full(codename))
