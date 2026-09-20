"""
One account form, for the member editing their own details and for an officer or sysadmin
editing someone else's.

There was a form for each page, and they drifted: the same field carried two labels, a callsign
typed on one page went through the FCC lookup and the name check while a callsign typed on the
other did not, and a member could not edit their own name although the requirements say they
may. The fields a person may change are one table here, read from the requirements' editability
rules, and both pages save through one path.
"""

from __future__ import annotations

from django import forms

from apps.ops.audit import record
from apps.ops.config import setting

from .models import User

# What the member keeps for themselves, and what only a sysadmin sets. `club_positions` is the
# one field an officer sets on another member's account.
OWN_FIELDS = ("preferred_name", "callsign", "cell_phone")
STUDENT_FIELDS = ("student_level", "graduation_semester", "graduation_year")
NAME_FIELDS = ("first_name", "middle_name", "last_name")
POSITION_FIELDS = ("club_positions",)
# Under 18 is not among them: it is set on the invitation (§2.4) and cleared by the conversion
# at 18 (FR-109), which is a one-way door.
#
# > once an account has been converted to adult, it cannot go back to Under 18. Removing this
# > will avoid us having to debug a workflow to convert an account backwards. — NAF, 2026-09-20
PRIVILEGE_FIELDS = ("category", "legal_hold")
GROUP_FIELDS = ("groups", "is_superuser")  # what the account may do

LABELS = {
    "cell_phone": "Mobile number",
    "student_level": "Student level",
    "graduation_semester": "Graduation semester",
    "graduation_year": "Graduation year",
    "under_18": "Under 18",
    "legal_hold": "Retain this account indefinitely",
}


def editable_fields(actor: User, subject: User) -> list[str]:
    """Which fields this person may change on that account.

    The member's own details are theirs; an officer sets a club position and nothing else; a
    sysadmin sets everything, on any account including their own. A name that comes from the FCC
    record is nobody's to type (it is refreshed by the license sync), and the student fields
    belong to the Student category.
    """
    is_self = actor.pk == subject.pk
    fields: list[str] = []
    if is_self or actor.may("edit_member_privileges"):
        fields += list(OWN_FIELDS)
        if not subject.name_from_uls:
            fields += list(NAME_FIELDS)
        if subject.category == "student" or actor.may("edit_member_privileges"):
            fields += list(STUDENT_FIELDS)
    # Including on your own account: the advisor is both the faculty advisor and the club's
    # license trustee, and recording offices is the job this capability names (2026-09-20).
    if actor.may("set_club_position"):
        fields += list(POSITION_FIELDS)
    if actor.may("edit_member_privileges"):
        fields += [f for f in POSITION_FIELDS if f not in fields]
        fields += list(PRIVILEGE_FIELDS)
    # Who may be appointed to what (§2.3): a group is yours to grant when everything it grants
    # is something you already hold, and only an account below you is yours to change.
    from apps.ops.groups import may_set_access

    # Only while there is access to change. Once an account is closed or suspended the way back
    # is the control that says so, which records who let them in (FR-91):
    #
    # > Once the account is closed, the Access menu should disappear or be disabled. It should
    # > only be granted again through "Let them back in as a member". — NAF, 2026-09-20
    if may_set_access(actor, subject) and subject.pk and subject.has_access:
        fields.append("groups")
    if actor.is_superuser and getattr(actor, "acting_capabilities", None) is None:
        fields.append("is_superuser")  # a sysadmin is made by a sysadmin, at the top level
    # the model's own order, so the page reads the same however the lists are built
    order = [f.name for f in User._meta.get_fields() if hasattr(f, "name")]
    return sorted(set(fields), key=lambda f: order.index(f) if f in order else 99)


class AccountForm(forms.ModelForm):
    """The one form both pages use. `actor` is who is typing, the instance is whose account it
    is; the fields follow from the two."""

    class Meta:
        model = User
        fields = [
            *NAME_FIELDS,
            *OWN_FIELDS,
            *STUDENT_FIELDS,
            *POSITION_FIELDS,
            *PRIVILEGE_FIELDS,
            *GROUP_FIELDS,
        ]

    def __init__(self, *args, actor: User, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        allowed = set(editable_fields(actor, self.instance))
        for name in list(self.fields):
            if name not in allowed:
                self.fields.pop(name)
        self.actor = actor

        if "category" in self.fields:
            cats = setting("member_categories", []) or []
            self.fields["category"] = forms.ChoiceField(
                choices=[(c["key"], c["label"]) for c in cats], required=False, label="Category"
            )
        if "club_positions" in self.fields:
            # Any number of them, and each one held by any number of people: one member is both
            # the faculty advisor and the license trustee, and a board has several members (the
            # advisor, 2026-09-20). Ticked boxes rather than a list to pick from, so holding two
            # takes one gesture each.
            positions = setting("club_positions", []) or []
            self.fields["club_positions"] = forms.MultipleChoiceField(
                choices=[(p["key"], p["label"]) for p in positions],
                required=False,
                label="Club positions",
                widget=forms.CheckboxSelectMultiple,
                help_text="Every office this member holds. None is the ordinary case.",
            )
        if "groups" in self.fields:
            from django.contrib.auth.models import Group

            from apps.ops.groups import assignable_groups, label_of

            # One level at a time, chosen from a list (the advisor, 2026-09-19: "Access should be
            # a drop-down. You should only be able to pick one."), and only the groups this
            # person may grant are in it, whatever the page was made to submit.
            allowed = assignable_groups(actor, self.instance)
            # **No access is not one of the answers.** Taking access away is closing or
            # suspending the account, and both of those carry a reason and a name (FR-91):
            #
            # > I think there should not be a No Access option through the Access menu. That
            # > should be set through Close Account or Suspend Account, both of which require
            # > explanations. — NAF, 2026-09-20, extending to everyone what an officer already
            # > met on 2026-09-19
            #
            # The field is only here while the account has access at all (editable_fields), so
            # it always holds one of the levels and never an empty answer.
            self.fields["groups"] = forms.ModelChoiceField(
                queryset=Group.objects.filter(pk__in=[g.pk for g in allowed]).order_by("name"),
                required=True,
                empty_label=None,
                label="Permission level",
                help_text="What this account may do. To take access away, close or suspend the "
                "account: both of those record a reason.",
            )
            configured = setting("access_groups", []) or []
            self.fields["groups"].label_from_instance = lambda g: label_of(g, configured)
            self.initial["groups"] = self.instance.groups.first() if self.instance.pk else None

        if "is_superuser" in self.fields:
            self.fields["is_superuser"] = forms.BooleanField(
                required=False,
                label="Sysadmin",
                help_text=(
                    "Every capability there is, including the club's configuration, the groups "
                    "themselves, and the Django admin. A sysadmin needs no group."
                ),
            )
        for name, label in LABELS.items():
            if name in self.fields:
                self.fields[name].label = label
        # One line under the switch, rather than an explanation crammed into its label.
        if "legal_hold" in self.fields:
            self.fields["legal_hold"].help_text = (
                "Exempt from the club's retention policy, for an account under a legal or "
                "institutional hold."
            )

    def clean_groups(self):
        """The field holds one group; the relation behind it holds a list."""
        group = self.cleaned_data.get("groups")
        return [group] if group else []

    @property
    def student_fields(self) -> list[str]:
        """The page hides these while the category is anything but Student."""
        return [f for f in STUDENT_FIELDS if f in self.fields]

    def clean(self):
        data = super().clean()
        # The student fields belong to the Student category. The page hides them as the category
        # changes; this makes it true on the server, whichever page posted.
        category = data.get("category", self.instance.category)
        if category != "student":
            for name in self.student_fields:
                data[name] = None if name == "graduation_year" else ""
        return data


def save_account(form: AccountForm, actor: User, base_url: str = "") -> dict:
    """The one save path. A callsign always goes through the lookup and the name check, whoever
    typed it, and the change is audited once. Addresses are rows with their own controls, so
    nothing here touches them.

    Returns what the page needs to say: the callsign result, if any.
    """
    from .services import apply_callsign

    subject = form.instance
    before = {f: _auditable(User.objects.get(pk=subject.pk), f) for f in form.changed_data}
    old_callsign = User.objects.get(pk=subject.pk).callsign
    user = form.save(commit=False)
    new_callsign = (user.callsign or "").upper().strip()
    user.callsign = old_callsign  # apply_callsign owns the change
    user.save()
    if "groups" in form.fields:
        form.save_m2m()  # the access groups, which the form holds as a many-to-many

    callsign_result = None
    if "callsign" in form.changed_data and new_callsign != old_callsign:
        callsign_result = apply_callsign(user, new_callsign, previous=old_callsign)

    if form.changed_data:
        record(
            actor,
            "member.edited",
            user,
            before=before,
            after={f: _auditable(user, f) for f in form.changed_data},
        )
    return {"callsign": callsign_result}


def _auditable(user: User, field: str):
    """A field's value in a form the audit log can hold. The access groups are a relation, so
    they are recorded as the names that mean something to a reader."""
    value = getattr(user, field)
    if field == "groups":
        return sorted(g.name for g in value.all())
    return value


def _groups_line(subject: User) -> str:
    """The account's access, in words: the groups it is in, or what having none means."""
    from apps.ops.groups import label_of

    if subject.is_superuser:
        return "Sysadmin (every capability)"
    configured = setting("access_groups", []) or []
    names = [label_of(g, configured) for g in subject.groups.all().order_by("name")]
    return ", ".join(names) or "No access"


def _position_line(subject: User) -> str:
    """The offices the member holds, in the club's own words and the club's own order, one per
    line as the addresses above them are (the advisor, 2026-09-20)."""
    held = set(subject.club_positions or [])
    labels = [p["label"] for p in (setting("club_positions", []) or []) if p.get("key") in held]
    return "\n".join(labels)


def _label(setting_key: str, key: str) -> str:
    """The configured label for a category or position, rather than its key."""
    for row in setting(setting_key, []) or []:
        if row.get("key") == key:
            return row.get("label", key)
    return key or ""


# Beyond the fields: what else a person can do on somebody's account page. A reader who holds
# none of these and no editable field sees the profile and no way to change it.
MANAGING_CAPABILITIES = (
    "manage_member_addresses",
    "override_license",
    "assign_groups",
    "archive_members",
    "delete_accounts",
    "issue_temporary_password",
    "impersonate_members",
    "convert_minor_accounts",
    "edit_member_privileges",
)


def may_manage(actor: User, subject: User) -> bool:
    """Whether this person has anything to change on that account.

    What decides whether the profile page offers `Edit profile` (NAF, 2026-09-19: "If they have
    the permission to edit a profile... there should be a button").
    """
    if bool(editable_fields(actor, subject)):
        return True
    return any(actor.may(c) for c in MANAGING_CAPABILITIES)


def profile_rows(subject: User, skip: tuple[str, ...] = ()) -> list[dict]:
    """Every account field as a line of text, whoever is reading.

    A profile page shows the account without a form in front of it (NAF, 2026-09-19: a name in
    the directory opens "a read-only view of their profile page"), and editing is a page of its
    own. Each row carries the field it came from, so `readonly_rows` can take the same list and
    drop what the reader is about to be given an input for.

    The name is three rows, because it is three fields: the advisor asked on 2026-09-19 for
    "the stored user first, middle, and last names printed read-only in the details box", where
    a callsign makes them the FCC's and nobody's to type (FR-8).
    """
    from apps.ops.templatetags.labels import phone

    rows: list[dict] = []

    def add(field: str, label: str, value) -> None:
        if field not in skip and value:
            rows.append({"field": field, "label": label, "value": value})

    add("first_name", "First name", subject.first_name)
    add("middle_name", "Middle name", subject.middle_name)
    add("last_name", "Last name", subject.last_name)
    add("preferred_name", "Preferred name", subject.preferred_name)
    add("callsign", "Callsign", subject.callsign)
    add("category", "Category", _label("member_categories", subject.category))
    add("club_positions", "Club positions", _position_line(subject))
    add("groups", "Permission level", _groups_line(subject))
    add("cell_phone", "Mobile number", phone(subject.cell_phone))
    if subject.under_18:
        add("under_18", "Under 18", "yes, a guardian acts for them")
    if subject.category == "student":
        add("student_level", "Student level", subject.get_student_level_display())
        graduation = " ".join(
            str(p)
            for p in (subject.get_graduation_semester_display(), subject.graduation_year)
            if p
        )
        add("graduation_year", "Graduation", graduation)
    joined = subject.date_joined.strftime("%d %b %Y") if subject.date_joined else ""
    if subject.joined_via_id and subject.joined_via:
        joined += f" via {subject.joined_via.label}"
    add("date_joined", "Joined", joined)
    return rows


def readonly_rows(actor: User, subject: User, skip: tuple[str, ...] = ()) -> list[dict]:
    """The account fields this person may not change.

    `skip` drops a field the page shows elsewhere, such as the name in a page heading.

    A page shows each field once: an input where they may change it, a line of text where they
    may not. The two come from the same table, so nothing is shown twice and nothing is missed.
    """
    allowed = set(editable_fields(actor, subject))
    return [r for r in profile_rows(subject, skip=skip) if r["field"] not in allowed]
