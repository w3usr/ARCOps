"""Captain and officer tools that shape an event: state (FR-44), operating limits (FR-39,
FR-48), eligibility rules (FR-53), and openings (FR-54, FR-80)."""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods, require_POST

from apps.credentials.models import CredentialType
from apps.credentials.services import ladder
from apps.ops.audit import record
from apps.ops.config import setting
from apps.ops.templatetags.labels import role_label

from .form_pages import done, form_page, step_url
from .models import EligibilityRule, Event, Opening, OperatingLimit, Slot
from .services.eligibility import club_default_rule, same_rule
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
    return redirect("event_step", pk=pk, step="publish")


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
        # Sized to what they hold, one a line (#176); a decimal keypad for the hours.
        widgets = {
            "max_hours_per_day": forms.TextInput(
                attrs={"inputmode": "decimal", "class": "num", "size": 4}
            ),
            "max_total_hours": forms.TextInput(
                attrs={"inputmode": "decimal", "class": "num", "size": 5}
            ),
            "min_break_minutes": forms.TextInput(
                attrs={"inputmode": "numeric", "class": "num", "size": 3}
            ),
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
    return redirect("event_step", pk=pk, step="slots")


def _rule_from_post(post, role: str) -> dict:
    """A rule as the form gives it. "Any class" is a valid license of any class: the license
    among the required credentials, which is how the club's default states it (#277)."""
    cls = post.get(f"class_{role}", "") or ""
    creds = [c for c in post.getlist(f"cred_{role}") if c and c != "amateur_license"]
    if cls == "any":
        cls, creds = "", ["amateur_license", *creds]
    return {
        "categories": [c for c in post.getlist(f"cat_{role}") if c],
        "min_license_class": cls,
        "required_credentials": creds,
        "minors_allowed": post.get(f"minors_{role}") == "on",
    }


def _as_dict(rule) -> dict:
    return {
        "categories": list(rule.categories or []),
        "min_license_class": rule.min_license_class or "",
        "required_credentials": list(rule.required_credentials or []),
        "minors_allowed": rule.minors_allowed,
    }


def event_rule(event, role: str) -> dict:
    """The rule the event applies to `role`: its own, else the club's (FR-53, FR-122)."""
    own = EligibilityRule.objects.filter(event=event, slot__isnull=True, role=role).first()
    return _as_dict(own) if own else club_default_rule(role)


def shown(rule: dict) -> dict:
    """A rule as the form draws it: "any" in the class box for a license of any class."""
    any_class = "amateur_license" in rule["required_credentials"] and not rule["min_license_class"]
    return rule | {
        "class": "any" if any_class else rule["min_license_class"],
        "credentials": [c for c in rule["required_credentials"] if c != "amateur_license"],
    }


@login_required
@require_POST
def eligibility_save(request, pk):
    """FR-53: the event-level rule per role. A rule saved equal to the club's (FR-122), as the
    form shows it until changed, is not stored: the event follows the club (#277)."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    roles = [r["key"] for r in (setting("slot_roles", []) or [])]
    changed = {}
    for role in roles:
        d = _rule_from_post(request.POST, role)
        existing = EligibilityRule.objects.filter(event=event, slot__isnull=True, role=role).first()
        if same_rule(d, club_default_rule(role)):
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
    return redirect("event_step", pk=pk, step="rules")


@login_required
@require_POST
def slot_eligibility(request, pk, slot_id):
    """FR-53: a per-slot override for one role, or its removal."""
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    slot = get_object_or_404(Slot, pk=slot_id, position__location__event=event)
    role = request.POST.get("role", "")
    d = _rule_from_post(request.POST, role)
    if request.POST.get("clear") or same_rule(d, event_rule(event, role)):
        # cleared, or saved as the event's own rule, which the form starts from (#277): none
        EligibilityRule.objects.filter(slot=slot, role=role).delete()
        messages.success(
            request, f"Override for {role_label(role)} removed; the event's rule applies."
        )
    else:
        EligibilityRule.objects.update_or_create(
            slot=slot, role=role, defaults={"event": event, **d}
        )
        messages.success(request, f"Override for {role_label(role)} saved on this slot.")
    record(request.user, "slot.eligibility", slot, after={"role": role})
    return redirect("slot_detail", pk=pk, slot_id=slot_id)


class OpeningForm(forms.Form):
    role = forms.ChoiceField(label="Role")
    opens_at = forms.DateTimeField(
        label="Opens at (UTC)",
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    categories = forms.MultipleChoiceField(
        label="To",
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="None ticked: everyone.",
    )
    announce = forms.BooleanField(required=False, label="Announce when it opens")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        kwargs.setdefault("auto_id", "op-%s")
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (r["key"], r["label"]) for r in setting("slot_roles", []) or []
        ]
        self.fields["categories"].choices = [
            (c["key"], c["label"]) for c in setting("member_categories", []) or []
        ]


@login_required
@require_http_methods(["GET", "POST"])
def opening_add(request, pk):
    """FR-54: a (when, audience) pair for a role. Empty categories means everyone."""
    from django.utils import timezone

    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    form = OpeningForm(request.POST or None)
    if request.method != "POST" or not form.is_valid():
        return form_page(
            request,
            event,
            form,
            heading="Add an opening",
            submit="Add opening",
            step="rules",
            intro="When a role opens, and to whom. List several to open a role to students "
            "first and everyone later.",
        )
    opens = form.cleaned_data["opens_at"]
    if timezone.is_naive(opens):
        opens = timezone.make_aware(opens, timezone.utc)
    o = Opening.objects.create(
        event=event,
        role=form.cleaned_data["role"],
        opens_at=opens,
        categories=form.cleaned_data["categories"],
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
    return done(request, step_url(pk, "rules"))


@login_required
@require_POST
def opening_delete(request, pk, opening_id):
    event = get_object_or_404(Event, pk=pk)
    _captain_or_404(request.user, event)
    Opening.objects.filter(pk=opening_id, event=event).delete()
    messages.success(request, "Opening removed.")
    return redirect("event_step", pk=pk, step="rules")


def rules_context(event) -> dict:
    """What the manage page needs to show the rules and openings."""
    roles = setting("slot_roles", []) or []
    rules = {r.role: r for r in EligibilityRule.objects.filter(event=event, slot__isnull=True)}
    return {
        # Each role's form starts from the rule it applies, the club's where the event has none,
        # tagged so (#277; NAF, 2026-11-12).
        "rule_roles": [
            {
                "key": r["key"],
                "label": r["label"],
                "rule": shown(
                    _as_dict(rules[r["key"]]) if r["key"] in rules else club_default_rule(r["key"])
                ),
                "is_default": r["key"] not in rules,
            }
            for r in roles
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
    return redirect("event_step", pk=pk, step="contest")
