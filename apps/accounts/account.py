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
from apps.ops.config import institution_email_domain, setting

from .models import AccessLevel, User

# What the member keeps for themselves, and what only a sysadmin sets. `club_position` is the
# one field an officer sets on another member's account.
OWN_FIELDS = (
    "preferred_name",
    "callsign",
    "institution_email",
    "institution_email_delivery",
    "personal_email",
    "personal_email_delivery",
    "cell_phone",
)
STUDENT_FIELDS = ("student_level", "graduation_semester", "graduation_year")
NAME_FIELDS = ("first_name", "middle_name", "last_name")
POSITION_FIELDS = ("club_position",)
PRIVILEGE_FIELDS = ("email", "category", "access_level", "under_18", "legal_hold")

LABELS = {
    "email": "Sign-in email",
    "personal_email": "Personal email",
    "cell_phone": "Mobile number",
    "student_level": "Student level",
    "graduation_semester": "Graduation semester",
    "graduation_year": "Graduation year",
    "under_18": "Under 18",
    "legal_hold": "Legal hold: the retention job leaves this account's records alone",
    "institution_email_delivery": "Send club email here",
    "personal_email_delivery": "Send club email here",
}


def editable_fields(actor: User, subject: User) -> list[str]:
    """Which fields this person may change on that account.

    The member's own details are theirs; an officer sets a club position and nothing else; a
    sysadmin sets everything, on any account including their own. A name that comes from the FCC
    record is nobody's to type (it is refreshed by the licence sync), and the student fields
    belong to the Student category.
    """
    is_self = actor.pk == subject.pk
    fields: list[str] = []
    if is_self or actor.is_sysadmin:
        fields += list(OWN_FIELDS)
        if not subject.name_from_uls:
            fields += list(NAME_FIELDS)
        if subject.category == "student" or actor.is_sysadmin:
            fields += list(STUDENT_FIELDS)
    if actor.is_officer and not is_self:
        fields += list(POSITION_FIELDS)
    if actor.is_sysadmin:
        fields += [f for f in POSITION_FIELDS if f not in fields]
        fields += list(PRIVILEGE_FIELDS)
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
        if "club_position" in self.fields:
            positions = setting("club_positions", []) or []
            self.fields["club_position"] = forms.ChoiceField(
                choices=[("", "None")] + [(p["key"], p["label"]) for p in positions],
                required=False,
                label="Club position",
            )
        if "access_level" in self.fields:
            self.fields["access_level"] = forms.ChoiceField(
                choices=AccessLevel.choices, label="Access level"
            )
        if "email" in self.fields:
            self.fields["email"].required = False
        if "institution_email" in self.fields:
            domain = institution_email_domain()
            self.fields["institution_email"].label = (
                f"{domain} email" if domain else "Institution email"
            )
        for name, label in LABELS.items():
            if name in self.fields and name != "institution_email":
                self.fields[name].label = label

    ADDRESS_PAIRS = (
        ("institution_email", "institution_email_delivery"),
        ("personal_email", "personal_email_delivery"),
    )

    @property
    def address_fields(self) -> list[str]:
        """The addresses and their delivery switches, which the page groups together."""
        names = ["email"] + [n for pair in self.ADDRESS_PAIRS for n in pair]
        return [n for n in names if n in self.fields]

    @property
    def email_field(self):
        return self["email"] if "email" in self.fields else None

    @property
    def address_pairs(self) -> list[dict]:
        out = []
        for address, switch in self.ADDRESS_PAIRS:
            if address in self.fields:
                out.append(
                    {
                        "address": self[address],
                        "switch": self[switch] if switch in self.fields else None,
                    }
                )
        return out

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

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:  # a form posted without the field keeps the sign-in address as it is
            return self.instance.email
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already signs in with that address.")
        return email


def save_account(form: AccountForm, actor: User, base_url: str = "") -> dict:
    """The one save path. A callsign always goes through the lookup and the name check, whoever
    typed it; addresses that changed lose or gain their standing; the change is audited once.

    Returns what the page needs to say: the callsign result, if any, and the addresses a
    confirmation link went to.
    """
    from . import addresses
    from .services import apply_callsign

    subject = form.instance
    before = {f: getattr(User.objects.get(pk=subject.pk), f) for f in form.changed_data}
    old_callsign = User.objects.get(pk=subject.pk).callsign
    user = form.save(commit=False)
    new_callsign = (user.callsign or "").upper().strip()
    user.callsign = old_callsign  # apply_callsign owns the change
    user.save()

    callsign_result = None
    if "callsign" in form.changed_data and new_callsign != old_callsign:
        callsign_result = apply_callsign(user, new_callsign, previous=old_callsign)

    sent = []
    if {"email", "institution_email", "personal_email"} & set(form.changed_data):
        sent = addresses.sync(user, actor, base_url)

    if form.changed_data:
        record(
            actor,
            "member.edited",
            user,
            before=before,
            after={f: getattr(user, f) for f in form.changed_data},
        )
    return {"callsign": callsign_result, "addresses_sent": sent}
