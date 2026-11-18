"""What every form here shares."""


class NoColon:
    """The house style puts no colon after a label."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


def utc_field(label: str, required: bool = True, help_text: str = ""):
    """A date and time in the browser's own box, on the viewer's clock, stored as UTC (A35, A38;
    apps/ops/when.py parse_box). `data-instant` has the page's script send it with its offset."""
    from django import forms

    from . import when

    class Field(forms.CharField):
        def to_python(self, value):
            try:
                return when.parse_box(value)
            except when.Unreadable as exc:
                raise forms.ValidationError(str(exc)) from None

        def prepare_value(self, value):
            if isinstance(value, str) and when.has_offset(value):
                try:  # sent back after an error: the box takes a wall clock, not an offset
                    value = when.parse_box(value)
                except when.Unreadable:
                    return value
            return when.typed(value) if hasattr(value, "astimezone") else value

    return Field(
        label=label,
        required=required,
        help_text=help_text,
        widget=forms.TextInput(
            attrs={"type": "datetime-local", "autocomplete": "off", "data-instant": ""}
        ),
    )
