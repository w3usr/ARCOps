"""What every form here shares."""


class NoColon:
    """The house style puts no colon after a label."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
