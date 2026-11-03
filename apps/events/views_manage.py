"""
Creating and running an event without the Django admin (§2.2, FR-42, FR-44, FR-46 to FR-52).

Officers create events. An event's captains (every officer is one by definition; a member
becomes one by appointment) edit it from a single manage page: the details, the operating
periods, the locations and positions, the captains, and the slot grid, which is generated from
the periods and can be regenerated freely until someone has signed up.
"""

from __future__ import annotations

import re
from datetime import UTC, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views.decorators.http import require_http_methods, require_POST
from tinymce.widgets import TinyMCE

from apps.accounts.models import User
from apps.credentials.services import ladder
from apps.ops.audit import record
from apps.ops.config import setting
from apps.ops.templatetags.richtext import sanitise

from .form_pages import done, form_page, tab_url
from .models import (
    Captaincy,
    Event,
    Location,
    OperatingPeriod,
    Position,
    RoleCapacity,
    SignUp,
    Slot,
)
from .services.manage import duplicate_event, generate_with_capacities, has_signups
from .services.slots import limit_report
from .views_rules import rules_context
from .views_slots import roster_or_slot

DEFAULT_EVENT_TYPES = [
    ("contest", "Contest"),
    ("activation", "Special-event or activation"),
    ("net", "Net"),
    ("training", "Training or workshop"),
    ("meeting", "Meeting"),
    ("other", "Other"),
]


def _types():
    cfg = setting("event_types", None)
    if cfg:
        return [(t["key"], t["label"]) for t in cfg]
    return DEFAULT_EVENT_TYPES


def _captain_or_404(user, event):
    if not user.can_captain(event):
        raise Http404


class EventForm(forms.ModelForm):
    def clean_description_html(self):
        return sanitise(self.cleaned_data.get("description_html") or "")

    def clean_kbyg_html(self):
        return sanitise(self.cleaned_data.get("kbyg_html") or "")

    class Meta:
        model = Event
        fields = [
            "title",
            "type",
            "description_html",
            "rules_url",
            "min_license_class",
            "kbyg_html",
            "display_timezone",
            "reminder_hours_before",
            "display_only",
            "recurrence_text",
        ]
        labels = {
            "description_html": "Description",
            "rules_url": "Rules link",
            "min_license_class": "Preferred license class",
            "reminder_hours_before": "Reminder, hours before each slot",
            "display_only": "Display only: on the calendar, no roster (a net, a meeting)",
            "recurrence_text": "When it recurs, in words",
            "kbyg_html": "Know before you go",
        }
        widgets = {
            "description_html": TinyMCE(attrs={"rows": 8}),  # FR-115
            "kbyg_html": TinyMCE(attrs={"rows": 12}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        self.fields["type"] = forms.ChoiceField(choices=_types())
        self.fields["min_license_class"] = forms.ChoiceField(  # replaced, so Meta.labels is lost
            label="Preferred license class",
            choices=[("", "Any")] + [(c, c) for c in ladder()],
            required=False,
        )
        import zoneinfo

        self.fields["display_timezone"] = forms.ChoiceField(  # a drop-down, never free text
            label="Local time zone for the roster",
            choices=[("", f"The club's ({setting('club.timezone', 'UTC')})")]
            + [(z, z) for z in sorted(zoneinfo.available_timezones())],
            required=False,
            help_text="For an event operated from somewhere else; the roster shows it beside UTC.",
        )
        self.fields[
            "description_html"
        ].help_text = "Plain text or simple HTML; shown at the top of the event."
        self.fields[
            "kbyg_html"
        ].help_text = "Shown under the roster: where to go, what to bring, who to call."


class PeriodForm(forms.Form):
    start = forms.DateTimeField(
        label="Starts (UTC)", widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    end = forms.DateTimeField(
        label="Ends (UTC)", widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)

    def clean(self):
        d = super().clean()
        s, e = d.get("start"), d.get("end")
        if s and e:
            # datetime-local carries no zone; the form says UTC, so that is what it is.
            d["start"] = s.replace(tzinfo=UTC) if timezone.is_naive(s) else s
            d["end"] = e.replace(tzinfo=UTC) if timezone.is_naive(e) else e
            if d["end"] <= d["start"]:
                self.add_error("end", "The end must come after the start.")
        return d


def _num(size):
    """A whole number, sized to what it holds and without a spinner: a text box with the numeric
    keypad (GOV.UK Design System, Text input: not type=number). The form still checks it."""
    return forms.TextInput(
        attrs={"inputmode": "numeric", "pattern": "[0-9]*", "class": "num", "size": size}
    )


class FieldGroups:
    """Fields drawn in groups, each a fieldset with a legend, or loose where the legend is empty
    (forms/_fields.html; NN/g: visually group related labels and fields). `GROUPS` names them."""

    GROUPS: list[tuple[str, list[str]]] = []

    @property
    def field_groups(self):
        seats = [n for n in self.fields if n.startswith("cap_")]
        out = []
        for legend, names in self.GROUPS:
            names = seats if names == ["cap_*"] else [n for n in names if n in self.fields]
            if names:
                out.append((legend, [self[n] for n in names]))
        return out


class SeatFields:
    """Seats per role (FR-49), starting from each role's configured default. In a group whose
    legend says what they are, each is named by its role alone (#168)."""

    def add_seat_fields(self, roles, label="{}"):
        for r in roles:
            self.fields[f"cap_{r['key']}"] = forms.IntegerField(
                label=label.format(r["label"]),
                min_value=0,
                max_value=20,
                initial=int(r.get("default_capacity", 1)),
                widget=_num(2),
            )

    def capacities(self) -> dict[str, int]:
        return {k[4:]: v for k, v in self.cleaned_data.items() if k.startswith("cap_")}


class GenerateForm(FieldGroups, SeatFields, forms.Form):
    GROUPS = [
        ("Slots", ["minutes", "setup_slots", "breakdown_slots"]),
        ("", ["windows"]),
        ("Seats in each slot", ["cap_*"]),
    ]
    minutes = forms.IntegerField(
        label="Slot length (minutes)", min_value=15, max_value=720, initial=60, widget=_num(3)
    )
    setup_slots = forms.IntegerField(
        label="Setup slots before", min_value=0, max_value=6, initial=1, widget=_num(1)
    )
    breakdown_slots = forms.IntegerField(
        label="Breakdown slots after", min_value=0, max_value=6, initial=1, widget=_num(1)
    )

    windows = forms.CharField(
        label="Hours to operate each day (optional)",
        help_text="Leave empty to fill the whole of each period, or give one range a line, "
        "such as 15:00-21:00",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean_windows(self):
        out = []
        for line in (self.cleaned_data.get("windows") or "").splitlines():
            line = line.strip().replace(" ", "")
            if not line:
                continue
            try:
                a, b = line.split("-")
                for t in (a, b):
                    h, m = t.split(":")
                    assert 0 <= int(h) < 24 and 0 <= int(m) < 60
            except (ValueError, AssertionError) as exc:
                raise forms.ValidationError(f"{line!r} is not HH:MM-HH:MM") from exc
            out.append((a, b))
        return out

    def __init__(self, *args, roles, fill_only=False, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        self.fields["minutes"].initial = int(setting("defaults.slot_length_minutes", 60))  # FR-89
        self.add_seat_fields(roles)
        if fill_only:  # filling makes operating slots only (#153), so these would do nothing
            del self.fields["setup_slots"], self.fields["breakdown_slots"]


class LocationForm(forms.Form):
    name = forms.CharField(label="Name", max_length=120)
    address = forms.CharField(label="Address (optional)", max_length=200, required=False)
    position = forms.CharField(
        label="First position", max_length=60, required=False, help_text="Run, Mult, VHF…"
    )
    is_club_station = forms.BooleanField(
        label="This is the club station", required=False, initial=True
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class PositionForm(forms.Form):
    name = forms.CharField(
        label="Position name", max_length=60, required=False, help_text="Run, Mult, VHF…"
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class CaptainForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.none(), label="Member", empty_label=None)

    def __init__(self, *args, event, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = (
            User.objects.with_access()
            .exclude(captaincies__event=event)
            .order_by("last_name", "first_name")
        )
        self.fields["user"].label_from_instance = lambda u: " ".join(
            x for x in (u.full_name, u.callsign) if x
        )


class AddSlotForm(FieldGroups, SeatFields, forms.Form):
    """One slot by hand, beside a grid that may already have people in it (FR-46, FR-47)."""

    GROUPS = [("", ["position", "start", "minutes", "kind"]), ("Seats in this slot", ["cap_*"])]

    position = forms.ModelChoiceField(queryset=Position.objects.none(), empty_label=None)
    start = forms.DateTimeField(
        label="Starts (UTC)", widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    minutes = forms.IntegerField(
        label="Length (minutes)", min_value=15, max_value=720, widget=_num(3)
    )
    kind = forms.ChoiceField(label="Kind")

    def __init__(self, *args, event, roles, **kwargs):
        kwargs.setdefault("label_suffix", "")
        # Its own ids: the period and generator forms on the same page have a start, a length and
        # seats too, and a label must not point at another form's field.
        kwargs.setdefault("auto_id", "slot-%s")
        super().__init__(*args, **kwargs)
        self.event = event
        self.fields["position"].queryset = (
            Position.objects.filter(location__event=event)
            .select_related("location")
            .order_by("location__order", "order")
        )
        self.fields["minutes"].initial = int(setting("defaults.slot_length_minutes", 60))
        self.fields["kind"].choices = [("operating", "Operating")] + [
            (k["key"], k["label"]) for k in setting("non_operating_slot_kinds", []) or []
        ]
        self.add_seat_fields(roles)

    def clean(self):
        d = super().clean()
        start, minutes, position = d.get("start"), d.get("minutes"), d.get("position")
        if not (start and minutes and position):
            return d
        # datetime-local carries no zone; the form says UTC, so that is what it is.
        start = start.replace(tzinfo=UTC) if timezone.is_naive(start) else start
        end = start + timedelta(minutes=minutes)
        d["start"], d["end"] = start, end
        # An operating slot sits inside an operating period (FR-38); setup, training and the
        # rest may sit before, after or between them (FR-47).
        if (
            d.get("kind") == "operating"
            and not self.event.periods.filter(start__lte=start, end__gte=end).exists()
        ):
            self.add_error("start", "An operating slot has to fit inside an operating period.")
        # A canceled slot is off the roster, so its time is free again: canceling a mistake and
        # adding it afresh is how a slot is re-timed.
        clash = Slot.objects.filter(
            position=position, cancelled=False, start__lt=end, end__gt=start
        ).first()
        if clash:
            self.add_error(
                "start",
                f"{position} already has a slot from {clash.start:%a %d %b %H:%M} to "
                f"{clash.end:%H:%M} UTC.",
            )
        return d


KBYG_OUTLINE = (
    "<h2>Where and when</h2><p></p>"
    "<h2>Getting into the station</h2><p></p>"
    "<h2>What to bring</h2><p></p>"
    "<h2>Operating and logging</h2><p></p>"
    "<h2>If something goes wrong</h2><p></p>"
    "<h2>Who to contact</h2><p></p>"
)


def kbyg_outline() -> str:
    """FR-77: the headings a new event's Know-before-you-go starts with. The club can replace
    the outline in its configuration (`defaults.kbyg_outline_html`)."""
    return setting("defaults.kbyg_outline_html", None) or KBYG_OUTLINE


@login_required
@require_http_methods(["GET", "POST"])
def event_create(request):
    if not request.user.may("manage_events"):
        raise Http404
    form = EventForm(request.POST or None, initial={"kbyg_html": kbyg_outline()})
    period = PeriodForm(request.POST or None)
    if (
        request.method == "POST"
        and form.is_valid()
        and (form.cleaned_data.get("display_only") or period.is_valid())
    ):
        event = form.save(commit=False)
        event.created_by = request.user
        event.save()
        if period.is_valid():
            OperatingPeriod.objects.create(
                event=event, start=period.cleaned_data["start"], end=period.cleaned_data["end"]
            )
        Captaincy.objects.get_or_create(event=event, user=request.user)
        record(request.user, "event.created", event, after={"title": event.title})
        messages.success(
            request, "Event created as a draft. Add its location and generate the slots."
        )
        return to_tab(event.pk, "setup")
    return render(request, "events/form.html", {"form": form, "period": period})


@login_required
def event_manage(request, pk, tab=None):
    """Manage, one tab at a time (#167). `/manage/` opens on the tab of the step to do next, or
    Setup. Its forms are pages of their own, opened in a dialog (#168)."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    if tab is None:
        return to_tab(pk, _first_tab(event))
    if tab not in dict(TABS):
        raise Http404
    return _manage_page(request, event, tab)


@login_required
@require_http_methods(["GET", "POST"])
def event_edit(request, pk):
    """The event's details (#168): read on Setup, edited here. A page, not a dialog: the rich
    text editor puts its menus on the page body, where a modal dialog would hide them."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    form = EventForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        before = {f: form.initial.get(f) for f in form.changed_data}
        form.save()
        record(
            request.user,
            "event.edited",
            event,
            before=before,
            after={f: getattr(event, f) for f in form.changed_data},
        )
        messages.success(request, "Saved.")
        return to_tab(pk, "setup")
    return form_page(
        request,
        event,
        form,
        heading="Edit details",
        submit="Save details",
        tab="setup",
        editor=True,
    )


def _details(event) -> list[tuple[str, str]]:
    """Setup's read of the event's details, label and value, in the form's order (#168)."""
    from apps.ops.templatetags.richtext import richtext

    from .services.notify import drop_empty_sections

    kbyg = re.findall(r"<h[1-6][^>]*>(.*?)</h[1-6]>", drop_empty_sections(event.kbyg_html))
    rows = [
        ("Title", event.title),
        ("Type", dict(_types()).get(event.type, event.type)),
        (
            "Description",
            richtext(event.description_html) if event.description_html else "None yet",
        ),
        ("Rules link", event.rules_url or "None"),
        ("Preferred license class", event.min_license_class or "Any"),
        (
            "Local time zone for the roster",
            event.display_timezone or f"The club's ({setting('club.timezone', 'UTC')})",
        ),
        (
            "Reminder, hours before each slot",
            event.reminder_hours_before
            or f"The club's default ({setting('defaults.reminder_hours_before', 24)})",
        ),
        ("Know before you go", ", ".join(kbyg) if kbyg else "Nothing filled in yet"),
    ]
    if event.display_only:
        rows.append(
            ("Display only", f"Yes: on the calendar, no roster. {event.recurrence_text}".strip())
        )
    return rows


# Manage in tabs (#167, SK 2026-11-02): each a page of its own, drawn by the server, so it works
# with JavaScript off and a tab can be linked to. docs/INTERFACE.md, "A page that edits more than
# a few things".
TABS = [
    ("setup", "Setup"),
    ("slots", "Slots"),
    ("rules", "Sign-up rules"),
    ("contest", "Contest"),
    ("status", "Status"),
]


def to_tab(pk, tab):
    """Back to the tab a form was on."""
    return redirect("event_manage_tab", pk=pk, tab=tab)


def _first_tab(event) -> str:
    positions = Position.objects.filter(location__event=event).exists()
    slots = Slot.objects.filter(position__location__event=event, cancelled=False).count()
    nxt = next((s for s in setup_steps(event, positions, slots) if s["next"]), None)
    return nxt["tab"] if nxt else "setup"


def setup_steps(event, positions, slot_count) -> list[dict]:
    """Setting an event up is four things in order, and the page is a dozen cards. Without this
    a captain has to know which card to open first, and there is nothing on the page that says.

    Each step says whether it is done, which one to do next, and where on the page it lives.
    """
    periods = event.periods.exists()
    steps = [
        {
            "title": "Say when the club will be on the air",
            "done": periods,
            "anchor": "per",
            "tab": "setup",
            "detail": "One operating period, or several. The slots are generated inside them.",
        },
        {
            "title": "Say where, and how many seats",
            "done": bool(positions),
            "anchor": "loc",
            "tab": "setup",
            "detail": "A location, and a position for each operating seat at it.",
        },
        {
            "title": "Generate the slots",
            "done": bool(slot_count),
            "anchor": "gen",
            "tab": "slots",
            "detail": "One slot per position per interval, across every period.",
        },
        {
            "title": "Publish it",
            "done": event.state
            in (Event.State.PUBLISHED, Event.State.LOCKED, Event.State.COMPLETED),
            "anchor": "st",
            "tab": "status",
            "detail": "Members see it and can sign up.",
        },
    ]
    for step in steps:  # the first one not done is the one to do
        step["next"] = False
    nxt = next((step for step in steps if not step["done"]), None)
    if nxt is not None:
        nxt["next"] = True
    return steps


def _manage_page(request, event, tab):
    """One tab of Manage. Its forms are pages of their own (#168), so it binds none."""
    positions = (
        Position.objects.filter(location__event=event)
        .select_related("location")
        .order_by("location__order", "order")
    )
    slot_count = Slot.objects.filter(position__location__event=event, cancelled=False).count()
    return render(
        request,
        "events/manage.html",
        {
            "event": event,
            "tab": tab,
            "tabs": TABS,
            "tab_label": dict(TABS)[tab],
            "details": _details(event),
            "periods": event.periods.order_by("start"),
            "locations": event.locations.prefetch_related("positions").order_by("order"),
            "positions": positions,
            "captains": event.captaincies.select_related("user").order_by("user__last_name"),
            # Appointing captains (§2.2) and cancelling the event (SK, 2026-10-15) are officers'.
            "may_manage_events": request.user.may("manage_events"),
            "slot_count": slot_count,
            "setup_steps": setup_steps(event, positions, slot_count),
            "signups_exist": has_signups(event),
            "limits": limit_report(event),
            "contest_fields": __import__(
                "apps.events.contest_fields", fromlist=["CONTEST_FIELDS"]
            ).CONTEST_FIELDS,
            **rules_context(event),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def period_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    form = PeriodForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        OperatingPeriod.objects.create(
            event=event, start=form.cleaned_data["start"], end=form.cleaned_data["end"]
        )
        messages.success(request, "Operating period added.")
        return done(request, tab_url(pk, "setup"))
    return form_page(
        request, event, form, heading="Add an operating period", submit="Add period", tab="setup"
    )


@login_required
@require_POST
def period_delete(request, pk, period_id):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    OperatingPeriod.objects.filter(pk=period_id, event=event).delete()
    messages.success(
        request, "Operating period removed. Regenerate the slots if they were built from it."
    )
    return to_tab(pk, "setup")


@login_required
@require_http_methods(["GET", "POST"])
def location_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    form = LocationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        loc = Location.objects.create(
            event=event,
            name=d["name"].strip(),
            is_club_station=d["is_club_station"],
            address=d["address"].strip(),
            order=event.locations.count() + 1,
        )
        Position.objects.create(location=loc, name=d["position"].strip() or "Station", order=1)
        messages.success(request, f"Location “{loc.name}” added with its first position.")
        return done(request, tab_url(pk, "setup"))
    return form_page(
        request, event, form, heading="Add a location", submit="Add location", tab="setup"
    )


@login_required
@require_http_methods(["GET", "POST"])
def position_add(request, pk, location_id):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    loc = get_object_or_404(Location, pk=location_id, event=event)
    form = PositionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        name = form.cleaned_data["name"].strip() or f"Position {loc.positions.count() + 1}"
        Position.objects.create(location=loc, name=name, order=loc.positions.count() + 1)
        messages.success(request, f"Position “{name}” added.")
        return done(request, tab_url(pk, "setup"))
    return form_page(
        request,
        event,
        form,
        heading=f"Add a position at {loc.name}",
        submit="Add position",
        tab="setup",
    )


@login_required
@require_POST
def position_delete(request, pk, position_id):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    pos = get_object_or_404(Position, pk=position_id, location__event=event)
    if SignUp.objects.filter(slot__position=pos).exists():
        messages.error(request, "That position has sign-ups; cancel them first.")
    else:
        pos.delete()
        messages.success(request, "Position removed with its slots.")
    return to_tab(pk, "setup")


@login_required
@require_http_methods(["GET", "POST"])
def captain_add(request, pk):
    # §2.2: captains are appointed by an officer or sysadmin, so a member who is captain of
    # this event runs it but does not choose who else does.
    if not request.user.may("manage_events"):
        raise Http404
    event = get_object_or_404(Event, pk=pk)
    form = CaptainForm(request.POST or None, event=event)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        Captaincy.objects.get_or_create(event=event, user=user)
        record(request.user, "captain.added", event, after={"user": user.pk})
        messages.success(request, f"{user.short_name} is now a captain of this event.")
        return done(request, tab_url(pk, "setup"))
    return form_page(
        request,
        event,
        form,
        heading="Appoint a captain",
        submit="Appoint captain",
        tab="setup",
        intro="Every officer already has a captain's powers on every event; appoint here to "
        "give them to a member for this event only.",
    )


@login_required
@require_POST
def captain_remove(request, pk, user_id):
    if not request.user.may("manage_events"):  # §2.2, as in captain_add
        raise Http404
    event = get_object_or_404(Event, pk=pk)
    captaincy = get_object_or_404(Captaincy, event=event, user_id=user_id)
    # The captains are who the event's notices go to (notify.captains_of); an event left with
    # none would go quiet without anyone being told.
    if event.captaincies.count() == 1:
        messages.error(request, "An event keeps at least one captain; appoint another first.")
        return to_tab(pk, "setup")
    captaincy.delete()
    record(request.user, "captain.removed", event, before={"user": user_id})
    messages.success(request, "Captain removed.")
    return to_tab(pk, "setup")


def _windows(event, form):
    """The daily hours as instants, None for the whole periods, or [] when they miss every period."""
    if not form.cleaned_data.get("windows"):
        return None
    from .services.slots import windows_from_daily

    return windows_from_daily(event, form.cleaned_data["windows"])


def _preview(event, positions, form, fill) -> str:
    """The generator's line before anything is made (#168), for the fields as they stand."""
    from .services.slots import describe

    if form.is_bound and not form.is_valid():
        return ""
    if form.is_bound:
        d, windows = form.cleaned_data, _windows(event, form)
        if windows == []:
            return "Those hours fall outside every operating period."
    else:
        d, windows = {name: f.initial for name, f in form.fields.items()}, None
    return describe(
        event,
        positions,
        minutes=int(d.get("minutes") or 60),
        setup_slots=int(d.get("setup_slots") or 0),
        breakdown_slots=int(d.get("breakdown_slots") or 0),
        windows=windows,
        fill=fill,
    )


def _preview_parts(text: str) -> dict:
    """The line as a headline and the rest: "51 slots" over "51 per position × 1 position…"."""
    head, sep, rest = text.partition(": ")
    return {"preview_head": head, "preview_rest": rest} if sep else {"preview_head": text}


@login_required
@require_http_methods(["GET", "POST"])
def slots_generate(request, pk):
    """The generator (FR-46 to FR-48): a page of its own, opened in Manage's dialog (#168). On an
    empty roster it builds the grid; once slots exist it adds to the empty hours (#153), and,
    while nobody has signed up, can replace the grid behind its confirmation."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    roles = setting("slot_roles", []) or []
    positions = list(Position.objects.filter(location__event=event))
    if not event.periods.exists() or not positions:
        messages.error(request, "Add an operating period and a location first.")
        return done(request, tab_url(pk, "slots"))
    existing = Slot.objects.filter(position__location__event=event)
    slot_count = existing.filter(cancelled=False).count()
    signups = has_signups(event)
    form = GenerateForm(request.POST or None, roles=roles, fill_only=bool(slot_count and signups))

    def page():
        return form_page(
            request,
            event,
            form,
            heading="Generate slots",
            submit="Generate slots",
            tab="slots",
            fields="events/forms/generate.html",
            actions="events/forms/generate_actions.html",
            refused="Nothing was generated; correct the fields marked below.",
            intro=(
                "Fills only the time that has no slot yet, in every position, and keeps every "
                "slot, seat count and sign-up. It makes operating slots only: setup and breakdown "
                "slots are added one at a time."
                + ("" if signups else " Regenerate slots replaces the whole grid instead.")
                if slot_count
                else "One slot per position per interval across every operating period, plus "
                "setup and breakdown slots at the ends."
            ),
            slot_count=slot_count,
            signups_exist=signups,
            **_preview_parts(_preview(event, positions, form, fill=bool(slot_count))),
        )

    if request.method != "POST":
        return page()
    # Adding to the empty hours keeps every slot, seat count and sign-up, so it needs neither a
    # confirmation nor an empty roster (#153, SK 2026-11-03). Replacing needs both.
    fill = request.POST.get("mode") == "fill"
    if not fill and signups:
        messages.error(request, "Members have signed up; the grid cannot be rebuilt under them.")
        return done(request, tab_url(pk, "slots"))
    if not form.is_valid():
        return page()
    # Before anything is deleted: replacing the grid with hours outside every period used to
    # delete the grid and then find nothing to build.
    windows = _windows(event, form)
    if windows == []:
        form.add_error("windows", "Those hours fall outside every operating period.")
        return page()
    if not fill and existing.exists() and request.POST.get("confirmed") != "yes":
        # Regenerating deletes every seat count, closed flag, and eligibility override on the
        # grid. It used to be the page's primary button, with nothing in between.
        partial = bool(request.headers.get("HX-Request"))
        return render(
            request,
            "events/confirm_regenerate.html",
            {
                "event": event,
                "slot_count": existing.count(),
                "partial": partial,
                "base_template": "events/_dialog_base.html" if partial else "base.html",
                "fields": [
                    (k, v) for k, v in request.POST.items() if k not in ("csrfmiddlewaretoken",)
                ],
            },
        )
    if not fill:
        existing.delete()
    created = generate_with_capacities(
        event,
        positions,
        form.cleaned_data["minutes"],
        form.cleaned_data.get("setup_slots", 0),
        form.cleaned_data.get("breakdown_slots", 0),
        form.capacities(),
        windows=windows,
        fill=fill,
    )
    record(
        request.user,
        "slots.generated",
        event,
        after={"count": len(created), "mode": "fill" if fill else "replace"},
    )
    if fill and not created:
        messages.info(request, "Every hour you asked for already has a slot; nothing added.")
        return done(request, tab_url(pk, "slots"))
    if fill:
        messages.success(
            request,
            f"Added {len(created)} slot{pluralize(len(created))} to the empty hours across "
            f"{len(positions)} position{pluralize(len(positions))}. The {slot_count} already on "
            "the roster are unchanged.",
        )
    else:
        messages.success(
            request, f"{len(created)} slots generated across {len(positions)} position(s)."
        )
    return done(request, reverse("event_detail", args=[pk]))


@login_required
@require_POST
def slots_preview(request, pk):
    """The generator's line, again, as its fields change (htmx, #168)."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    positions = list(Position.objects.filter(location__event=event))
    live = Slot.objects.filter(position__location__event=event, cancelled=False).exists()
    # The same form the page drew: without setup and breakdown once only filling is possible.
    form = GenerateForm(
        request.POST, roles=setting("slot_roles", []) or [], fill_only=live and has_signups(event)
    )
    return render(
        request,
        "events/forms/_preview.html",
        _preview_parts(_preview(event, positions, form, fill=live)),
    )


@login_required
@require_http_methods(["GET", "POST"])
def slot_add(request, pk):
    """One slot by hand, whether or not anyone has signed up: nothing else on the grid changes
    (FR-46). Its seats are set as it is made, which is when a captain knows them (FR-49)."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    form = AddSlotForm(request.POST or None, event=event, roles=setting("slot_roles", []) or [])
    if request.method != "POST" or not form.is_valid():
        return form_page(
            request,
            event,
            form,
            heading="Add a slot",
            submit="Add the slot",
            tab="slots",
            refused="No slot was added; correct the fields marked below.",
            intro="One slot, beside whatever is on the grid, people included. A slot added by "
            "mistake is canceled from its own page, which is also how one is re-timed.",
        )
    d = form.cleaned_data
    slot = Slot.objects.create(
        position=d["position"], start=d["start"], end=d["end"], kind=d["kind"]
    )
    seats = {role: n for role, n in form.capacities().items() if n > 0}
    RoleCapacity.objects.bulk_create(
        RoleCapacity(slot=slot, role=role, capacity=n) for role, n in seats.items()
    )
    record(
        request.user,
        "slot.added",
        slot,
        after={
            "position": str(d["position"]),
            "start": d["start"].isoformat(),
            "end": d["end"].isoformat(),
            "kind": d["kind"],
            "seats": seats,
        },
    )
    messages.success(
        request,
        format_html(
            'Slot added: <a href="{}">{} {}</a>.',
            reverse("slot_detail", args=[event.pk, slot.pk]),
            d["position"],
            f"{d['start']:%a %d %b %H:%M}–{d['end']:%H:%M} UTC",
        ),
    )
    return done(request, tab_url(pk, "slots"))


@login_required
@require_POST
def slot_toggle(request, slot_id):
    """FR-52: close (not bookable) or reopen a slot; cancel it outright."""
    slot = get_object_or_404(Slot, pk=slot_id)
    event = slot.event
    _captain_or_404(request.user, event)
    what = request.POST.get("what")
    if what == "close":
        slot.closed = not slot.closed
        slot.save(update_fields=["closed"])
        messages.success(request, "Slot closed." if slot.closed else "Slot reopened.")
    elif what == "cancel":
        if slot.signups.exists():
            reason = request.POST.get("reason", "").strip()[:300]
            if request.POST.get("confirmed") == "yes" and not reason:
                messages.error(request, "Give a reason; the people in the slot are told it.")
            elif request.POST.get("confirmed") == "yes":
                from .services.notify import cancel_slot_with_people

                n = cancel_slot_with_people(request.user, slot, reason)
                messages.success(request, f"Slot canceled; {n} person(s) told.")
            else:
                messages.error(
                    request,
                    "This slot has people in it. Cancel it from the slot page with a reason, so they are told; or remove the sign-ups first.",
                )
        else:
            slot.cancelled = True
            slot.save(update_fields=["cancelled"])
            record(request.user, "slot.cancelled", slot)
            messages.success(request, "Slot canceled.")
    if slot.cancelled:  # gone from the roster, so there is no slot to come back to
        return redirect("event_detail", pk=event.pk)
    return roster_or_slot(request, slot)


@login_required
@require_POST
def event_duplicate(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    copy = duplicate_event(event, request.user)
    record(request.user, "event.duplicated", copy, before={"from": event.pk})
    messages.success(request, "Copied as a draft. Fix the dates, then generate or keep the slots.")
    return to_tab(copy.pk, "setup")


@login_required
@require_POST
def event_cancel(request, pk):
    # Only an officer cancels an event; a member made captain runs it but cannot call it off
    # (SK, 2026-10-15).
    if not request.user.may("manage_events"):
        raise Http404
    event = get_object_or_404(Event, pk=pk)
    reason = request.POST.get("reason", "").strip()[:300]
    if request.POST.get("confirm") != "yes" or not reason:
        messages.error(request, "Give a reason and tick the confirmation to cancel the event.")
        return to_tab(pk, "status")
    from .services.notify import event_cancelled

    event.state = Event.State.CANCELLED
    event.save(update_fields=["state"])
    told = event_cancelled(request.user, event, reason)
    record(request.user, "event.cancelled", event, after={"reason": reason, "people_told": told})
    messages.success(
        request,
        f"Event canceled; {told} person(s) told. It stays in the record; members no longer see it as upcoming.",
    )
    return redirect("event_list")
