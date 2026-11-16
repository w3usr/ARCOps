"""What every form here shares."""


class NoColon:
    """The house style puts no colon after a label."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


def utc_field(label: str, required: bool = True, help_text: str = ""):
    """A UTC date and time in the browser's own date and time box (A35; apps/ops/when.py)."""
    from django import forms

    from . import when

    class Field(forms.CharField):
        takes_utc = True
        zone = None  # set by clock(): the box was filled in the event's own clock, not UTC

        def to_python(self, value):
            try:
                t = when.parse_utc(value)
            except when.Unreadable as exc:
                raise forms.ValidationError(str(exc)) from None
            return t.replace(tzinfo=self.zone).astimezone(when.UTC) if t and self.zone else t

        def prepare_value(self, value):
            return when.typed(value) if hasattr(value, "astimezone") else value

    return Field(
        label=label,
        required=required,
        help_text=help_text,
        widget=forms.TextInput(attrs={"type": "datetime-local", "autocomplete": "off"}),
    )


def clock(form, data, zone):
    """UTC or the event's own clock (A35): the switch app.js adds posts `clock`, and each UTC box
    carries the zone it converts to. Without JavaScript there is no switch, and boxes are UTC."""
    local = (data or {}).get("clock") == "local"
    for field in form.fields.values():
        if getattr(field, "takes_utc", False):
            field.zone = zone if local else None
            field.widget.attrs["data-zone"] = getattr(zone, "key", "UTC")
            if local:
                field.widget.attrs["data-clock"] = "local"
    return form
