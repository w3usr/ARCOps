"""
Creating and running an event without the Django admin (§2.2, FR-42, FR-44, FR-46 to FR-52).

Officers create events. An event's captains (every officer is one by definition; a member
becomes one by appointment) edit it from a single manage page: the details, the operating
periods, the locations and positions, the captains, and the slot grid, which is generated from
the periods and can be regenerated freely until someone has signed up.
"""

from __future__ import annotations

from datetime import UTC

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import AccessLevel, User
from apps.credentials.services import ladder
from apps.ops.audit import record
from apps.ops.config import setting

from .models import Captaincy, Event, Location, OperatingPeriod, Position, SignUp, Slot
from .services.manage import duplicate_event, generate_with_capacities, has_signups

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
    class Meta:
        model = Event
        fields = [
            "title",
            "type",
            "description_html",
            "rules_url",
            "min_license_class",
            "kbyg_html",
        ]
        labels = {
            "description_html": "Description",
            "rules_url": "Rules link",
            "min_license_class": "Minimum license class",
            "kbyg_html": "Know before you go",
        }
        widgets = {
            "description_html": forms.Textarea(attrs={"rows": 5}),
            "kbyg_html": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        self.fields["type"] = forms.ChoiceField(choices=_types())
        self.fields["min_license_class"] = forms.ChoiceField(
            choices=[("", "Any")] + [(c, c) for c in ladder()], required=False
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


class GenerateForm(forms.Form):
    minutes = forms.IntegerField(
        label="Slot length (minutes)", min_value=15, max_value=720, initial=60
    )
    setup_slots = forms.IntegerField(
        label="Setup slots before", min_value=0, max_value=6, initial=1
    )
    breakdown_slots = forms.IntegerField(
        label="Breakdown slots after", min_value=0, max_value=6, initial=1
    )

    def __init__(self, *args, roles, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        for r in roles:
            self.fields[f"cap_{r['key']}"] = forms.IntegerField(
                label=f"{r['label']} seats per slot",
                min_value=0,
                max_value=20,
                initial=int(r.get("default_capacity", 1)),
            )

    def capacities(self) -> dict[str, int]:
        return {k[4:]: v for k, v in self.cleaned_data.items() if k.startswith("cap_")}


@login_required
@require_http_methods(["GET", "POST"])
def event_create(request):
    if not request.user.is_officer:
        raise Http404
    form = EventForm(request.POST or None)
    period = PeriodForm(request.POST or None)
    if request.method == "POST" and form.is_valid() and period.is_valid():
        event = form.save(commit=False)
        event.created_by = request.user
        event.save()
        OperatingPeriod.objects.create(
            event=event, start=period.cleaned_data["start"], end=period.cleaned_data["end"]
        )
        Captaincy.objects.get_or_create(event=event, user=request.user)
        record(request.user, "event.created", event, after={"title": event.title})
        messages.success(
            request, "Event created as a draft. Add its location and generate the slots."
        )
        return redirect("event_manage", pk=event.pk)
    return render(request, "events/form.html", {"form": form, "period": period})


@login_required
@require_http_methods(["GET", "POST"])
def event_manage(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    roles = setting("slot_roles", []) or []
    form = EventForm(instance=event)
    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
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
            return redirect("event_manage", pk=pk)
    positions = (
        Position.objects.filter(location__event=event)
        .select_related("location")
        .order_by("location__order", "order")
    )
    slot_count = Slot.objects.filter(position__location__event=event, cancelled=False).count()
    candidates = (
        User.objects.exclude(access_level=AccessLevel.NONE)
        .exclude(captaincies__event=event)
        .order_by("last_name", "first_name")
    )
    return render(
        request,
        "events/manage.html",
        {
            "event": event,
            "form": form,
            "period_form": PeriodForm(),
            "periods": event.periods.order_by("start"),
            "locations": event.locations.prefetch_related("positions").order_by("order"),
            "positions": positions,
            "captains": event.captaincies.select_related("user").order_by("user__last_name"),
            "candidates": candidates,
            "generate_form": GenerateForm(roles=roles),
            "slot_count": slot_count,
            "signups_exist": has_signups(event),
        },
    )


@login_required
@require_POST
def period_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    form = PeriodForm(request.POST)
    if form.is_valid():
        OperatingPeriod.objects.create(
            event=event, start=form.cleaned_data["start"], end=form.cleaned_data["end"]
        )
        messages.success(request, "Operating period added.")
    else:
        messages.error(request, "; ".join(e for errs in form.errors.values() for e in errs))
    return redirect("event_manage", pk=pk)


@login_required
@require_POST
def period_delete(request, pk, period_id):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    OperatingPeriod.objects.filter(pk=period_id, event=event).delete()
    messages.success(
        request, "Operating period removed. Regenerate the slots if they were built from it."
    )
    return redirect("event_manage", pk=pk)


@login_required
@require_POST
def location_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    name = request.POST.get("name", "").strip()[:120]
    if not name:
        messages.error(request, "A location needs a name.")
        return redirect("event_manage", pk=pk)
    order = event.locations.count() + 1
    loc = Location.objects.create(
        event=event,
        name=name,
        is_club_station=request.POST.get("is_club_station") == "on",
        address=request.POST.get("address", "").strip()[:200],
        order=order,
    )
    Position.objects.create(
        location=loc, name=request.POST.get("position", "").strip()[:60] or "Station", order=1
    )
    messages.success(request, f"Location “{name}” added with its first position.")
    return redirect("event_manage", pk=pk)


@login_required
@require_POST
def position_add(request, pk, location_id):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    loc = get_object_or_404(Location, pk=location_id, event=event)
    name = request.POST.get("name", "").strip()[:60] or f"Position {loc.positions.count() + 1}"
    Position.objects.create(location=loc, name=name, order=loc.positions.count() + 1)
    messages.success(request, f"Position “{name}” added.")
    return redirect("event_manage", pk=pk)


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
    return redirect("event_manage", pk=pk)


@login_required
@require_POST
def captain_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    user = get_object_or_404(User, pk=request.POST.get("user"))
    _, created = Captaincy.objects.get_or_create(event=event, user=user)
    if created:
        record(request.user, "captain.added", event, after={"user": user.pk})
        messages.success(request, f"{user.short_name} is now a captain of this event.")
    return redirect("event_manage", pk=pk)


@login_required
@require_POST
def captain_remove(request, pk, user_id):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    Captaincy.objects.filter(event=event, user_id=user_id).delete()
    record(request.user, "captain.removed", event, before={"user": user_id})
    messages.success(request, "Captain removed.")
    return redirect("event_manage", pk=pk)


@login_required
@require_POST
def slots_generate(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    roles = setting("slot_roles", []) or []
    form = GenerateForm(request.POST, roles=roles)
    positions = list(Position.objects.filter(location__event=event))
    if not event.periods.exists() or not positions:
        messages.error(request, "Add an operating period and a location first.")
        return redirect("event_manage", pk=pk)
    if has_signups(event):
        messages.error(request, "Members have signed up; the grid cannot be rebuilt under them.")
        return redirect("event_manage", pk=pk)
    if not form.is_valid():
        messages.error(request, "; ".join(e for errs in form.errors.values() for e in errs))
        return redirect("event_manage", pk=pk)
    Slot.objects.filter(position__location__event=event).delete()
    created = generate_with_capacities(
        event,
        positions,
        form.cleaned_data["minutes"],
        form.cleaned_data["setup_slots"],
        form.cleaned_data["breakdown_slots"],
        form.capacities(),
    )
    record(request.user, "slots.generated", event, after={"count": len(created)})
    messages.success(
        request, f"{len(created)} slots generated across {len(positions)} position(s)."
    )
    return redirect("event_detail", pk=pk)


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
            messages.error(
                request,
                "Remove the sign-ups first; people should hear from you before the slot vanishes.",
            )
        else:
            slot.cancelled = True
            slot.save(update_fields=["cancelled"])
            record(request.user, "slot.cancelled", slot)
            messages.success(request, "Slot cancelled.")
    return redirect("event_detail", pk=event.pk)


@login_required
@require_POST
def event_duplicate(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    copy = duplicate_event(event, request.user)
    record(request.user, "event.duplicated", copy, before={"from": event.pk})
    messages.success(request, "Copied as a draft. Fix the dates, then generate or keep the slots.")
    return redirect("event_manage", pk=copy.pk)


@login_required
@require_POST
def event_cancel(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    if request.POST.get("confirm") != "yes":
        messages.error(request, "Tick the confirmation to cancel the event.")
        return redirect("event_manage", pk=pk)
    event.state = Event.State.CANCELLED
    event.save(update_fields=["state"])
    record(request.user, "event.cancelled", event)
    messages.success(
        request, "Event cancelled. It stays in the record; members no longer see it as upcoming."
    )
    return redirect("event_list")
