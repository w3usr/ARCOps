"""What every form here shares."""


class NoColon:
    """The house style puts no colon after a label."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


def utc_field(label: str, required: bool = True, help_text: str | None = None):
    """A UTC date and time typed as 2026-11-21 21:00 (#274; apps/ops/when.py), in a plain text
    box the browser does not reformat by its locale."""
    from django import forms

    from . import when

    class Field(forms.CharField):
        def to_python(self, value):
            try:
                return when.parse_utc(value)
            except when.Unreadable as exc:
                raise forms.ValidationError(str(exc)) from None

        def prepare_value(self, value):
            return when.typed(value) if hasattr(value, "astimezone") else value

    return Field(
        label=label,
        required=required,
        help_text=when.HELP if help_text is None else help_text,
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false", "size": 16}),
    )
