"""FR-4: the application opens with the callsign, and the name comes from the FCC record.

The join form and the invitation form share this. With JavaScript, typing a callsign asks the
server for the name block (`_names.html`), which shows the FCC's record and a "This is me" box in
place of the name fields; without it, the same block is drawn on submit. A callsign that is not
in the FCC's data yet, or no callsign at all ("I do not have a callsign"), keeps the name fields,
and a name typed beside a callsign takes the older path: the account is made with it and a
differing FCC name is asked about afterwards (FR-16).
"""

from __future__ import annotations

from functools import cached_property

from django import forms
from django.shortcuts import render

NAMES = ("first_name", "middle_name", "last_name")
TRUE = ("on", "true", "1", True)


class CallsignFirst:
    """Mixed into a form that has `callsign` and the three name fields; `lookup_url` is where
    the callsign field asks for the name block."""

    NAMES = NAMES
    # The words, addressed to whoever fills the form in; a guardian's form says "they".
    no_callsign_label = "I do not have a callsign"
    is_me_label = "This is me"
    is_me_error = "Tick this if the FCC's record is yours; if it is not, check the callsign."
    record_help = (
        "Your name comes from this record. Not you? Check the callsign. To be known by another "
        "name in the club, fill in Preferred name."
    )

    def __init__(self, *args, lookup_url: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name"):
            self.fields[name].required = False  # the FCC's record may supply them; see clean()
        self.fields["no_callsign"] = forms.BooleanField(
            required=False, label=self.no_callsign_label
        )
        self.fields["is_me"] = forms.BooleanField(required=False, label=self.is_me_label)
        # The callsign, and the choice not to have one, come before the names they decide.
        order = [f for f in self.fields if f not in ("callsign", "no_callsign", "is_me")]
        at = order.index("first_name")
        order[at:at] = ["callsign", "no_callsign"]
        self.order_fields(order)
        if lookup_url:
            ask = {
                "hx-get": lookup_url,
                "hx-target": "#names",
                "hx-include": "#names, [name=callsign], [name=no_callsign]",
            }
            self.fields["callsign"].widget.attrs.update(
                ask | {"hx-trigger": "input changed delay:500ms, change"}
            )
            self.fields["no_callsign"].widget.attrs.update(ask | {"hx-trigger": "change"})
        self.fields["is_me"].widget.attrs["required"] = True  # drawn only beside a record

    def _raw(self, key):
        src = self.data if self.is_bound else self.initial
        return src.get(key)

    @cached_property
    def looked_up(self) -> tuple[str, object]:
        """(the callsign as typed, its FCC row or None); ("", None) with no callsign."""
        from apps.credentials.models import UlsLicense

        if self._raw("no_callsign") in TRUE:
            return "", None
        call = (self._raw("callsign") or "").upper().strip()
        row = UlsLicense.objects.filter(callsign=call).first() if call else None
        return call, row

    @property
    def names_typed(self) -> bool:
        return any((self._raw(n) or "").strip() for n in ("first_name", "last_name"))

    @property
    def fcc_record(self):
        """The FCC's record, shaped as the License card reads one, when it is to stand in for
        the name fields: a row was found and no name was typed."""
        from apps.credentials.models import LicenseRecord

        call, row = self.looked_up
        if row is None or self.names_typed:
            return None
        return LicenseRecord(
            callsign=call,
            licensee_name=row.licensee_name,
            operator_class=row.operator_class,
            licensee_type=row.applicant_type,
            status=row.status or "active",
            expiry_date=row.expiry_date,
        )

    @property
    def missing_callsign(self) -> str:
        """A callsign typed that the FCC's data does not hold yet."""
        call, row = self.looked_up
        return call if call and row is None else ""

    def clean(self):
        data = super().clean()
        if data.get("no_callsign"):
            data["callsign"] = ""
        if self.fcc_record is not None:
            if not data.get("is_me"):
                self.add_error("is_me", self.is_me_error)
            return data  # the name is the FCC's, applied with the callsign (FR-4)
        for name in ("first_name", "last_name"):
            if not data.get(name) and name not in self.errors:
                self.add_error(name, forms.Field.default_error_messages["required"])
        return data


def names_block(request, form) -> object:
    """The name block alone, for the callsign field's request."""
    return render(request, "accounts/_names.html", {"form": form})
