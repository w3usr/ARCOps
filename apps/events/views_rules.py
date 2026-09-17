"""Captain and officer tools that shape an event: state (FR-44), operating limits (FR-39,
FR-48), eligibility rules (FR-53), and openings (FR-54, FR-80)."""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.credentials.models import CredentialType
from apps.credentials.services import ladder
from apps.ops.audit import record
from apps.ops.config import setting

from .models import EligibilityRule, Event, Opening, OperatingLimit, Slot
from .services.lifecycle import set_state


def _captain_or_404(user, event):
    if not user.can_captain(event):
        raise Http404


@login_required
@require_POST
def event_state(request, pk):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    try:
        messages.success(request, set_state(request.user, event, request.POST.get("what", "")))
    except ValueError as exc:
        messages.error(request, str(exc).capitalize() + ".")
    return redirect("event_manage", pk=pk)


class LimitForm(forms.ModelForm):
    class Meta:
        model = OperatingLimit
        fields = ["max_hours_per_day", "day_basis", "max_total_hours", "min_break_minutes"]
        labels = {
            "max_hours_per_day": "Maximum on-air hours per day",
            "day_basis": "Day counted in",
            "max_total_hours": "Maximum on-air hours for the event",
            "min_break_minutes": "Shortest break that counts as off time (minutes)",
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


@login_required
@require_POST
def limits_save(request, pk):
    """FR-39: advisory limits; the roster warns and never refuses."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    limit = getattr(event, "limit", None) or OperatingLimit(event=event)
    form = LimitForm(request.POST, instance=limit)
    if form.is_valid():
        if not any(
            form.cleaned_data.get(f)
            for f in ("max_hours_per_day", "max_total_hours", "min_break_minutes")
        ):
            if limit.pk:
                limit.delete()
            messages.success(request, "Operating limits cleared.")
        else:
            form.save()
            messages.success(
                request, "Operating limits saved. The roster marks slots that push past them."
            )
        record(
            request.user,
            "event.limits",
            event,
            after={k: (str(v) if v is not None else None) for k, v in form.cleaned_data.items()},
        )
    else:
        messages.error(request, "; ".join(e for errs in form.errors.values() for e in errs))
    return redirect("event_manage", pk=pk)


def _rule_from_post(post, role: str) -> dict:
    return {
        "categories": [c for c in post.getlist(f"cat_{role}") if c],
        "min_license_class": post.get(f"class_{role}", "") or "",
        "required_credentials": [c for c in post.getlist(f"cred_{role}") if c],
        "minors_allowed": post.get(f"minors_{role}") == "on",
    }


def _rule_is_default(d: dict) -> bool:
    return (
        not d["categories"]
        and not d["min_license_class"]
        and not d["required_credentials"]
        and d["minors_allowed"]
    )


@login_required
@require_POST
def eligibility_save(request, pk):
    """FR-53: the event-level rule per role. A rule with nothing set is deleted, so the club's
    configured default (FR-122) applies again."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    roles = [r["key"] for r in (setting("slot_roles", []) or [])]
    changed = {}
    for role in roles:
        d = _rule_from_post(request.POST, role)
        existing = EligibilityRule.objects.filter(event=event, slot__isnull=True, role=role).first()
        if _rule_is_default(d):
            if existing:
                existing.delete()
                changed[role] = "default"
            continue
        if existing:
            for k, v in d.items():
                setattr(existing, k, v)
            existing.save()
        else:
            EligibilityRule.objects.create(event=event, role=role, **d)
        changed[role] = d
    record(request.user, "event.eligibility", event, after=changed)
    messages.success(request, "Who may sign up: saved.")
    return redirect("event_manage", pk=pk)


@login_required
@require_POST
def slot_eligibility(request, pk, slot_id):
    """FR-53: a per-slot override for one role, or its removal."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    slot = get_object_or_404(Slot, pk=slot_id, position__location__event=event)
    role = request.POST.get("role", "")
    if request.POST.get("clear"):
        EligibilityRule.objects.filter(slot=slot, role=role).delete()
        messages.success(request, f"Override for {role} removed; the event's rule applies.")
    else:
        d = _rule_from_post(request.POST, role)
        EligibilityRule.objects.update_or_create(
            slot=slot, role=role, defaults={"event": event, **d}
        )
        messages.success(request, f"Override for {role} saved on this slot.")
    record(request.user, "slot.eligibility", slot, after={"role": role})
    return redirect("slot_detail", pk=pk, slot_id=slot_id)


class OpeningForm(forms.Form):
    role = forms.CharField(max_length=20)
    opens_at = forms.DateTimeField(
        label="Opens at (UTC)", input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"]
    )
    announce = forms.BooleanField(
        required=False, label="Announce to the newly eligible when it opens"
    )


@login_required
@require_POST
def opening_add(request, pk):
    """FR-54: a (when, audience) pair for a role. Empty categories means everyone."""
    from django.utils import timezone

    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    form = OpeningForm(request.POST)
    if not form.is_valid():
        messages.error(request, "; ".join(e for errs in form.errors.values() for e in errs))
        return redirect("event_manage", pk=pk)
    opens = form.cleaned_data["opens_at"]
    if timezone.is_naive(opens):
        opens = timezone.make_aware(opens, timezone.utc)
    o = Opening.objects.create(
        event=event,
        role=form.cleaned_data["role"],
        opens_at=opens,
        categories=[c for c in request.POST.getlist("categories") if c],
        announce=form.cleaned_data["announce"],
    )
    record(
        request.user,
        "opening.added",
        o,
        after={"role": o.role, "opens_at": opens.isoformat(), "categories": o.categories},
    )
    messages.success(
        request,
        f"{o.role.capitalize()} opens {opens:%d %b %H:%M}Z to {', '.join(o.categories) or 'everyone'}.",
    )
    return redirect("event_manage", pk=pk)


@login_required
@require_POST
def opening_delete(request, pk, opening_id):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    Opening.objects.filter(pk=opening_id, event=event).delete()
    messages.success(request, "Opening removed.")
    return redirect("event_manage", pk=pk)


def rules_context(event) -> dict:
    """What the manage page needs to show the rules and openings."""
    roles = setting("slot_roles", []) or []
    rules = {r.role: r for r in EligibilityRule.objects.filter(event=event, slot__isnull=True)}
    return {
        "rule_roles": [
            {"key": r["key"], "label": r["label"], "rule": rules.get(r["key"])} for r in roles
        ],
        "categories": setting("member_categories", []) or [],
        "ladder": ladder(),
        "credential_types": list(
            CredentialType.objects.exclude(key="amateur_license").order_by("label")
        ),
        "openings": event.openings.order_by("opens_at"),
        "limit_form": LimitForm(instance=getattr(event, "limit", None)),
    }


@login_required
@require_POST
def contest_save(request, pk):
    """FR-37: the WA7BNM field set, entered by hand until the calendar import is authorized."""
    from .contest_fields import KEYS

    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    data = {k: request.POST.get(k, "").strip()[:500] for k in KEYS}
    event.contest_fields = {k: v for k, v in data.items() if v}
    if request.POST.get("calendar_ref", "").strip().isdigit():
        event.calendar_ref = int(request.POST["calendar_ref"])
    event.save(update_fields=["contest_fields", "calendar_ref"])
    record(
        request.user, "event.contest_fields", event, after={"fields": sorted(event.contest_fields)}
    )
    messages.success(request, "Contest details saved.")
    return redirect("event_manage", pk=pk)
