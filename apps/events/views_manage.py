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
from django.db.models import Count, Prefetch, Q
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

from .form_pages import done, form_page, step_url
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
from .services.slots import held_only_by, limit_report
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

    class Meta:
        model = Event
        fields = [
            "title",
            "type",
            "description_html",
            "rules_url",
            "min_license_class",
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
        }
        widgets = {"description_html": TinyMCE(attrs={"rows": 8})}  # FR-115

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


class KbygForm(forms.ModelForm):
    """Know before you go, a step of its own (#174): written last, once the location's
    arrangements are known, and what participants read before they come."""

    def clean_kbyg_html(self):
        return sanitise(self.cleaned_data.get("kbyg_html") or "")

    class Meta:
        model = Event
        fields = ["kbyg_html"]
        labels = {"kbyg_html": "Know before you go"}
        help_texts = {
            "kbyg_html": "Shown under the roster and in each reminder: where to go, what to bring, "
            "who to call. A heading with nothing under it is left out."
        }
        widgets = {"kbyg_html": TinyMCE(attrs={"rows": 16})}

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


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

    def __init__(self, *args, editing=False, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        if editing:  # positions are added and renamed on their own
            del self.fields["position"]


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
    """New event (#173): the Details step of an event not made yet. Saving makes the draft and
    goes on to Operating periods; the first period is added there like any other."""
    if not request.user.may("manage_events"):
        raise Http404
    form = EventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.created_by = request.user
        event.kbyg_html = kbyg_outline()  # FR-77: it starts with the outline (#174)
        event.save()
        Captaincy.objects.get_or_create(event=event, user=request.user)
        record(request.user, "event.created", event, after={"title": event.title})
        messages.success(request, "Draft created.")
        return to_step(event.pk, "periods")
    return render(
        request,
        "events/stages/new.html",
        {"event": None, "form": form, "steps": stages(None), "step": stages(None)[0]},
    )


@login_required
def event_manage(request, pk, step=None):
    """Manage, one step at a time (#172). `/manage/` opens on the step to do next."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    if step is None:
        return to_step(pk, _landing(event))
    if step in OLD_TABS:
        return redirect("event_step", pk=pk, step=OLD_TABS[step], permanent=True)
    if step not in STEP_NAMES:
        raise Http404
    if step == "kbyg":
        return _kbyg(request, event)
    if step == "slots":
        return _step_page(request, event, step, **_on_air_context(event))
    return _step_page(request, event, step)


def _kbyg(request, event):
    """The Know before you go step: a page with the editor, as Edit details is (its menus need
    the page, docs/INTERFACE.md), saved here and back to the step."""
    form = KbygForm(request.POST or None, instance=event)
    if request.method == "POST" and form.is_valid():
        form.save()
        record(request.user, "event.edited", event, after={"kbyg_html": "changed"})
        messages.success(request, "Saved.")
        return to_step(event.pk, "kbyg")
    return _step_page(request, event, "kbyg", form=form)


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
        return to_step(pk, "details")
    return form_page(
        request,
        event,
        form,
        heading="Edit details",
        submit="Save details",
        step="details",
        fields="events/forms/_one_per_line.html",  # unrelated fields: one a line (#176)
        editor=True,
    )


def _details(event) -> list[tuple[str, str]]:
    """Setup's read of the event's details, label and value, in the form's order (#168)."""
    from apps.ops.templatetags.richtext import richtext

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
    ]
    if event.display_only:
        rows.append(
            ("Display only", f"Yes: on the calendar, no roster. {event.recurrence_text}".strip())
        )
    return rows


def _summary(event, steps, captains) -> list[dict]:
    """The Publish step's check of every step while the event is a draft (#175; GOV.UK's Check
    answers): one row per step, what it holds, and a link to change it. A required step not done
    reads "Not done yet"; publishing stays allowed, as it was."""
    from apps.ops.templatetags.labels import role_label

    def fmt(t):
        return f"{t:%a %d %b %H:%M}"

    periods = list(event.periods.order_by("start"))
    span = (
        f"{len(periods)} period{pluralize(len(periods))}, {fmt(periods[0].start)} to "
        f"{fmt(max(p.end for p in periods))} UTC"
        if periods
        else ""
    )
    places = "; ".join(
        f"{loc.name}: {', '.join(p.name for p in loc.positions.all())}"
        for loc in event.locations.prefetch_related("positions").order_by("order")
    )
    slots = Slot.objects.filter(position__location__event=event, cancelled=False).count()
    held = f"{slots} slot{pluralize(slots)}" if slots else ""
    lim = getattr(event, "limit", None)
    limits = [
        f"{lim.max_hours_per_day:g} h a day" if lim and lim.max_hours_per_day else "",
        f"{lim.max_total_hours:g} h in all" if lim and lim.max_total_hours else "",
        f"breaks of {lim.min_break_minutes} min" if lim and lim.min_break_minutes else "",
    ]
    if held and any(limits):
        held += "; limits: " + ", ".join(x for x in limits if x)
    rules = event.eligibility_rules.filter(slot__isnull=True)
    openings = event.openings.count()
    said = (
        [f"who may sign up set for {', '.join(role_label(r.role) for r in rules)}"] if rules else []
    )
    said += [f"{openings} opening{pluralize(openings)}"] if openings else []
    holds = {
        "details": f"{event.title}, {dict(_types()).get(event.type, event.type)}",
        "periods": span,
        "locations": places,
        "slots": held,
        "rules": "; ".join(said).capitalize() if said else "Club defaults",
    }
    rows = []
    for st in steps:
        if st["key"] == "publish":
            continue
        value = holds.get(st["key"]) or st["word"]
        if st["key"] in ("details", "periods", "locations", "slots") and not holds[st["key"]]:
            value = "None" if st.get("optional") else "Not done yet"
        rows.append(
            {
                "key": st["key"],
                "name": st["name"],
                "value": value,
                "missing": value == "Not done yet",
            }
        )
    names = ", ".join(c.user.full_name for c in captains) or "None"
    rows.append({"key": "publish", "name": "Captains", "value": names, "anchor": "cap"})
    return rows


# Manage as steps under one progress bar (#172, SK 2026-11-03), in place of #167's tabs and the
# four-step guide beside them, which had drifted apart. One list, so the bar, the page you land on
# and each step's foot cannot disagree. Each step is a page of its own, drawn by the server, so it
# works with JavaScript off and can be linked to. docs/INTERFACE.md, "A page that edits many things".
STEP_NAMES = {
    "details": "Details",
    "periods": "Operating periods",
    "locations": "Locations",
    "slots": "Slots",
    "publish": "Publish",
    "rules": "Sign-up rules",
    "contest": "Contest details",
    "kbyg": "Know before you go",
}
# The tabs' addresses before #172: bookmarks and pages left open still land.
OLD_TABS = {"setup": "details", "status": "publish"}
LIVE = (Event.State.PUBLISHED, Event.State.LOCKED, Event.State.COMPLETED)


def stages(event, positions: bool = False, slot_count: int = 0) -> list[dict]:
    """Every step of setting `event` up, in order: the required ones numbered, then the optional.

    Each says whether it is done, whether it can be opened yet, and one word of state. A
    display-only event (a net, a meeting) has no roster, so no locations, slots or sign-up rules,
    and an operating period is optional for it. With no event, it is one being created (#173):
    Details is the step you are on, and nothing else can be opened until it is saved."""
    if event is None:
        new = [
            {"key": k, "done": False, "open": k == "details", "after": "Details"}
            for k in STEP_NAMES
        ]
        new = [s for s in new if s["key"] not in ("rules", "contest", "kbyg")]
        for n, s in enumerate(new, 1):
            s.update(name=STEP_NAMES[s["key"]], number=n, next=s["key"] == "details")
            s["word"] = "Next" if s["open"] else "After Details"
        return new
    periods = event.periods.exists()
    shown_only = event.display_only
    steps = [
        {"key": "details", "done": True},
        {"key": "periods", "done": periods, "optional": shown_only},
    ]
    if not shown_only:
        steps += [
            {"key": "locations", "done": positions},
            {
                "key": "slots",
                "done": bool(slot_count),
                "open": periods and positions,
                "after": "Locations" if not positions else "Operating periods",
            },
        ]
    steps.append({"key": "publish", "done": event.state in LIVE, "word": event.get_state_display()})
    nxt = next((s for s in steps if not s["done"] and not s.get("optional")), None)
    for n, s in enumerate(steps, 1):
        s.update(name=STEP_NAMES[s["key"]], number=n, next=s is nxt)
        s.setdefault("open", True)
        if "word" not in s:
            s["word"] = (
                "Done"
                if s["done"]
                else f"After {s['after']}"
                if not s["open"]
                else "Next"
                if s["next"]
                else "Optional"
                if s.get("optional")
                else "To do"
            )
    extras = []
    if not shown_only:
        rules = (
            event.eligibility_rules.filter(slot__isnull=True).exists() or event.openings.exists()
        )
        extras.append({"key": "rules", "word": "Set" if rules else "Club defaults"})
        filled = bool(event.contest_fields or event.calendar_ref)
        if event.type == "contest" or filled:
            extras.append({"key": "contest", "word": "Filled in" if filled else "Not filled in"})
        from .services.notify import drop_empty_sections

        written = bool(re.sub(r"<[^>]+>|&nbsp;|\s", "", drop_empty_sections(event.kbyg_html or "")))
        extras.append({"key": "kbyg", "word": "Written" if written else "Outline only"})
    for s in extras:
        s.update(name=STEP_NAMES[s["key"]], optional=True, extra=True, open=True)
    return steps + extras


def not_ready(event, steps) -> str:
    """Why a draft cannot be published yet, as the end of a sentence; "" when it can. Publishing
    waits for the required steps (SK, 2026-11-10), so nobody sees an event with nothing to sign
    up for; and a roster event whose every period has ended is not published, so nobody is told
    about one that is over (SK, 2026-11-10). The Publish button is greyed with this line, and the
    server refuses the same."""
    names = [
        s["name"]
        for s in steps
        if not s.get("extra") and not s.get("optional") and not s["done"] and s["key"] != "publish"
    ]
    if names:
        listed = f"{', '.join(names[:-1])} and {names[-1]}" if len(names) > 1 else names[0]
        return f"{listed} {'are' if len(names) > 1 else 'is'} not done yet."
    end = event.ends_at()
    if not event.display_only and end and end <= timezone.now():
        return f"it ended on {end:%a %d %b %Y %H:%M} UTC."
    return ""


def publish_blocker(event) -> str:
    """not_ready() for an event, working out its steps."""
    positions = Position.objects.filter(location__event=event).exists()
    slots = Slot.objects.filter(position__location__event=event, cancelled=False).count()
    return not_ready(event, stages(event, positions, slots))


def to_step(pk, step):
    """Back to the step a form was on."""
    return redirect("event_step", pk=pk, step=step)


def _landing(event) -> str:
    """`/manage/` opens on the first required step not done, else Publish."""
    positions = Position.objects.filter(location__event=event).exists()
    slots = Slot.objects.filter(position__location__event=event, cancelled=False).count()
    nxt = next((s for s in stages(event, positions, slots) if s.get("next")), None)
    return nxt["key"] if nxt else "publish"


def _step_page(request, event, step, **extra):
    """One step of Manage. Its forms are pages of their own (#168), so it binds none."""
    positions = (
        Position.objects.filter(location__event=event)
        .select_related("location")
        .order_by("location__order", "order")
    )
    slot_count = Slot.objects.filter(position__location__event=event, cancelled=False).count()
    all_steps = stages(event, positions.exists(), slot_count)
    captains = event.captaincies.select_related("user").order_by("user__last_name")
    periods = list(event.periods.order_by("start"))
    if step == "periods":  # what removing each one takes, said in its confirmation
        for p in periods:
            held = held_only_by(p)
            p.held, p.people = len(held), SignUp.objects.filter(slot__in=held).count()
    here = next((s for s in all_steps if s["key"] == step), None)
    if here is None or not here["open"]:
        raise Http404
    # The foot walks the numbered steps only; the optional ones are not a sequence.
    seq = [s for s in all_steps if not s.get("extra")]
    i = seq.index(here) if here in seq else None
    back = seq[i - 1] if i else None
    onward = seq[i + 1] if i is not None and i + 1 < len(seq) else None
    return render(
        request,
        f"events/stages/{step}.html",
        {
            "event": event,
            "step": here,
            "steps": [s for s in all_steps if not s.get("extra")],
            "extras": [s for s in all_steps if s.get("extra")],
            "back": back,
            "onward": onward if onward and onward["open"] else None,
            "details": _details(event),
            "periods": periods,
            # each position with its slot count, for the Locations step's rows (#233)
            "locations": event.locations.prefetch_related(
                Prefetch(
                    "positions",
                    queryset=Position.objects.annotate(
                        live_slots=Count("slots", filter=Q(slots__cancelled=False))
                    ),
                )
            ).order_by("order"),
            "positions": positions,
            "captains": captains,
            # Appointing captains (§2.2) and cancelling the event (SK, 2026-10-15) are officers'.
            "may_manage_events": request.user.may("manage_events"),
            "slot_count": slot_count,
            "signups_exist": has_signups(event),
            "limits": limit_report(event),
            "contest_fields": __import__(
                "apps.events.contest_fields", fromlist=["CONTEST_FIELDS"]
            ).CONTEST_FIELDS,
            **rules_context(event),
            "missing": not_ready(event, all_steps) if event.state == Event.State.DRAFT else "",
            "summary": _summary(event, all_steps, captains)
            if step == "publish" and event.state == Event.State.DRAFT
            else None,
            **extra,
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
        end = form.cleaned_data["end"]
        if end <= timezone.now():  # most often a wrong year (SK, 2026-11-10)
            messages.warning(
                request,
                f"This period ended on {end:%a %d %b %Y %H:%M} UTC, before now. Check the year.",
            )
        return done(request, step_url(pk, "periods"))
    return form_page(
        request, event, form, heading="Add an operating period", submit="Add period", step="periods"
    )


@login_required
@require_POST
def period_delete(request, pk, period_id):
    """Removing a period cancels the slots only it held, as every slot is canceled and never
    deleted (FR-102); while anybody is signed up in one, nothing goes, as with the bulk cancel:
    their captain removes them, or cancels the slot and tells them, first (SK, 2026-11-10)."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    period = get_object_or_404(OperatingPeriod, pk=period_id, event=event)
    slots = held_only_by(period)
    people = SignUp.objects.filter(slot__in=slots).count()
    if people:
        messages.error(
            request,
            f"Nothing was removed: {people} {'person is' if people == 1 else 'people are'} signed "
            "up in its slots. Remove them from their slots, or cancel those slots and tell them, "
            "first.",
        )
        return to_step(pk, "periods")
    n = Slot.objects.filter(pk__in=[s.pk for s in slots]).update(cancelled=True)
    record(
        request.user,
        "event.edited",
        event,
        before={"period": f"{period.start:%Y-%m-%d %H:%M}–{period.end:%Y-%m-%d %H:%M} UTC"},
        after={"period": None, "slots canceled": n},
    )
    period.delete()
    with_it = f"; {n} slot{pluralize(n)} canceled with it." if n else "."
    messages.success(request, f"Operating period removed{with_it}")
    return to_step(pk, "periods")


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
        return done(request, step_url(pk, "locations"))
    return form_page(
        request, event, form, heading="Add a location", submit="Add location", step="locations"
    )


@login_required
@require_http_methods(["GET", "POST"])
def location_edit(request, pk, location_id):
    """FR-51: a location's name, address and club-station mark, put right after it is added."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    loc = get_object_or_404(Location, pk=location_id, event=event)
    fields = ("name", "address", "is_club_station")
    form = LocationForm(
        request.POST or None, editing=True, initial={f: getattr(loc, f) for f in fields}
    )
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        before = {f: getattr(loc, f) for f in fields}
        loc.name, loc.address = d["name"].strip(), d["address"].strip()
        loc.is_club_station = d["is_club_station"]
        loc.save(update_fields=list(fields))
        after = {f: getattr(loc, f) for f in fields}
        changed = [f for f in fields if before[f] != after[f]]
        if changed:
            record(
                request.user,
                "event.edited",
                event,
                before={"location": before["name"], **{f: before[f] for f in changed}},
                after={"location": loc.name, **{f: after[f] for f in changed}},
            )
        messages.success(request, f"Location “{loc.name}” saved.")
        return done(request, step_url(pk, "locations"))
    return form_page(
        request, event, form, heading=f"Edit {loc.name}", submit="Save location", step="locations"
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
        return done(request, step_url(pk, "locations"))
    return form_page(
        request,
        event,
        form,
        heading=f"Add a position at {loc.name}",
        submit="Add position",
        step="locations",
    )


@login_required
@require_http_methods(["GET", "POST"])
def position_edit(request, pk, position_id):
    """A position renamed; its slots and sign-ups stay with it."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    pos = get_object_or_404(Position, pk=position_id, location__event=event)
    form = PositionForm(request.POST or None, initial={"name": pos.name})
    form.fields["name"].required = True  # adding fills in a name; renaming to nothing would not
    if request.method == "POST" and form.is_valid():
        old, pos.name = pos.name, form.cleaned_data["name"].strip()
        if pos.name != old:
            pos.save(update_fields=["name"])
            record(
                request.user,
                "event.edited",
                event,
                before={"position": old, "location": pos.location.name},
                after={"position": pos.name},
            )
        messages.success(request, f"Position “{pos.name}” saved.")
        return done(request, step_url(pk, "locations"))
    return form_page(
        request, event, form, heading=f"Rename {pos.name}", submit="Save position", step="locations"
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
    return to_step(pk, "locations")


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
        return done(request, step_url(pk, "publish"))
    return form_page(
        request,
        event,
        form,
        heading="Appoint a captain",
        submit="Appoint captain",
        step="publish",
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
        return to_step(pk, "publish")
    captaincy.delete()
    record(request.user, "captain.removed", event, before={"user": user_id})
    messages.success(request, "Captain removed.")
    return to_step(pk, "publish")


def _preview(event, positions, form, fill) -> str:
    """The generator's line before anything is made (#168), for the fields as they stand."""
    from .services.slots import chosen, describe

    if form.is_bound and not form.is_valid():
        return ""
    d = form.cleaned_data if form.is_bound else {name: f.initial for name, f in form.fields.items()}
    stretches = len(chosen(event))
    text = describe(
        event,
        positions,
        minutes=int(d.get("minutes") or 60),
        setup_slots=int(d.get("setup_slots") or 0),
        breakdown_slots=int(d.get("breakdown_slots") or 0),
        fill=fill,
    )
    if stretches:  # the club's own hours, not the whole event (#247)
        text = f"{text.rstrip('.')}, in the on-air hours ({stretches} stretch{pluralize(stretches, 'es')})."
    return text


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
        return done(request, step_url(pk, "slots"))
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
            step="slots",
            fields="events/forms/generate.html",
            actions="events/forms/generate_actions.html",
            refused="Nothing was generated; correct the fields marked below.",
            intro=(
                "Fills only the time that has no slot yet, in every position, and keeps every "
                "slot, seat count and sign-up. It makes operating slots only: setup and breakdown "
                "slots are added one at a time."
                + ("" if signups else " Regenerate slots replaces the whole grid instead.")
                if slot_count
                else "One slot per position per interval across the on-air hours (set above the "
                "generator on Slots; the whole event unless chosen), plus setup and breakdown slots "
                "at the ends."
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
        return done(request, step_url(pk, "slots"))
    if not form.is_valid():
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
                "slot_count": slot_count,  # on the roster; canceled ones go too, unseen
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
        return done(request, step_url(pk, "slots"))
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


def _on_air_context(event, **forms_) -> dict:
    """What the Slots step needs to show the on-air hours (#247, ranges only since #248): the
    stretches in words, the hours against the whole event, and the slots that fall outside them."""
    from .services.slots import chosen, clip, periods_of

    stretches, periods = chosen(event), periods_of(event)

    def hours(spans):
        return sum((b - a).total_seconds() for a, b in spans) / 3600

    def label(a, b):
        return f"{a:%a %-d %b %H:%M} to {b:%a %-d %b %H:%M} UTC"

    outside = 0
    if stretches:
        for slot in Slot.objects.filter(
            position__location__event=event, cancelled=False, kind="operating"
        ):
            if clip([(slot.start, slot.end)], stretches) != [(slot.start, slot.end)]:
                outside += 1
    return {
        "on_air_stretches": [{"i": i, "label": label(a, b)} for i, (a, b) in enumerate(stretches)],
        "on_air_hours": hours(stretches) if stretches else hours(periods),
        "event_hours": hours(periods),
        "slots_outside": outside,
        "range_form": forms_.get("range_form") or PeriodForm(auto_id="onair-%s"),
    }


@login_required
@require_POST
def on_air_save(request, pk):
    """Save the on-air hours (#247, A15; A16 since #248), each back to the Slots step in place
    (#177): a range typed to the minute, added to the stretches; one stretch removed; or the
    whole event again. Slots are never touched."""
    from .services.slots import chosen, clip, periods_of, set_on_air

    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    what = request.POST.get("what", "")
    base = chosen(event)  # [] means the whole event: a range added to that starts afresh

    def saved(spans, note=""):
        kept = set_on_air(event, spans)
        record(request.user, "event.on_air_set", event, after={"stretches": len(kept)})
        if kept:
            hours = sum((b - a).total_seconds() for a, b in kept) / 3600
            messages.success(
                request,
                f"On-air hours saved: {hours:g} hour{pluralize(hours)} in {len(kept)} "
                f"stretch{pluralize(len(kept), 'es')}.{note}",
            )
        else:
            messages.success(request, "On the air for the whole event." + note)
        return to_step(pk, "slots")

    if what == "whole":
        return saved([])
    if what == "remove":
        i = int(request.POST.get("i", -1)) if request.POST.get("i", "").isdigit() else -1
        if not 0 <= i < len(base):
            raise Http404
        rest = base[:i] + base[i + 1 :]
        if not rest:
            return saved([], " The last stretch is gone, so the whole event is on the air again.")
        return saved(rest)
    if what == "range":
        form = PeriodForm(request.POST, auto_id="onair-%s")
        if form.is_valid():
            asked = (form.cleaned_data["start"], form.cleaned_data["end"])
            inside = clip([asked], periods_of(event))
            if not inside:
                form.add_error("start", "That range falls outside every operating period.")
            else:
                note = "" if inside == [asked] else " The range was cut to the operating periods."
                return saved(base + inside, note)
        return _step_page(request, event, "slots", **_on_air_context(event, range_form=form))
    raise Http404


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
            step="slots",
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
    return done(request, step_url(pk, "slots"))


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
    """FR-42: a copy on new dates. The dialog asks when the copy starts, in UTC, and every date
    moves by the difference from this event's start; with no start given, the dates stay."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    shift, typed, was = timedelta(0), request.POST.get("start", "").strip(), event.starts_at()
    if typed and was:
        try:
            start = forms.DateTimeField().clean(typed)
        except forms.ValidationError:
            messages.error(request, "Nothing was copied: the start was not a date and time.")
            return to_step(pk, "publish")
        start = (
            start.replace(tzinfo=UTC) if timezone.is_naive(start) else start
        )  # the form says UTC
        shift = start - was
    copy = duplicate_event(event, request.user, shift=shift)
    now = copy.starts_at()
    record(
        request.user,
        "event.duplicated",
        copy,
        before={"from": event.pk},
        after={"starts": now.isoformat() if now else None},
    )
    when = f", starting {now:%a %d %b %Y %H:%M} UTC" if now else ""
    messages.success(
        request,
        f"Copied as a draft{when}. The periods, on-air hours, slots and openings moved with it.",
    )
    return to_step(copy.pk, "periods")


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
        return to_step(pk, "publish")
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
