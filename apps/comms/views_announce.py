"""Announcements (FR-75, FR-106) and the unsubscribe path (FR-81)."""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from tinymce.widgets import TinyMCE

from apps.events.models import Event
from apps.events.services.roster import display_zone
from apps.ops.config import setting
from apps.ops.templatetags.richtext import sanitise

from . import announce
from .models import Announcement


class AnnounceForm(forms.Form):
    subject = forms.CharField(max_length=200)
    body_html = forms.CharField(widget=TinyMCE(attrs={"rows": 10}), label="Message")  # FR-115
    day = forms.CharField(required=False)
    role = forms.CharField(required=False)
    status = forms.CharField(required=False)
    confirmation = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)

    def clean_body_html(self):
        text = self.cleaned_data["body_html"].strip()
        if "<" not in text:  # plain text typed in: paragraphs
            text = "".join(f"<p>{p.strip()}</p>" for p in text.split("\n\n") if p.strip())
        return sanitise(text)

    def filters(self, categories):
        return {
            k: v
            for k, v in {
                "day": self.cleaned_data.get("day", ""),
                "role": self.cleaned_data.get("role", ""),
                "status": self.cleaned_data.get("status", ""),
                "confirmation": self.cleaned_data.get("confirmation", ""),
                "categories": categories,
            }.items()
            if v
        }


def _filters_from_get(request):
    return {
        k: v
        for k, v in {
            "day": request.GET.get("day", ""),
            "role": request.GET.get("role", ""),
            "status": request.GET.get("status", ""),
            "confirmation": request.GET.get("confirmation", ""),
            "categories": [c for c in request.GET.getlist("categories") if c],
        }.items()
        if v
    }


@login_required
@require_http_methods(["GET", "POST"])
def announce_view(request, pk=None):
    """Compose to an event's participants (captains) or to every member (officers)."""
    event = get_object_or_404(Event, pk=pk) if pk else None
    if event is not None and not request.user.can_captain(event):
        raise Http404
    if event is None and not request.user.is_officer:
        raise Http404
    categories = setting("member_categories", []) or []
    roles = setting("slot_roles", []) or []
    if request.method == "POST":
        form = AnnounceForm(request.POST)
        cats = [c for c in request.POST.getlist("categories") if c]
        if form.is_valid():
            filters = form.filters(cats)
            if request.POST.get("action") == "outside":
                ann = announce.send_announcement(
                    request.user,
                    event,
                    filters,
                    form.cleaned_data["subject"],
                    form.cleaned_data["body_html"],
                    outside=True,
                )
                addrs, _ = announce.outside_copy(request.user, event, filters)
                return render(
                    request,
                    "comms/announce_outside.html",
                    {"ann": ann, "addresses": ", ".join(addrs), "event": event},
                )
            ann = announce.send_announcement(
                request.user,
                event,
                filters,
                form.cleaned_data["subject"],
                form.cleaned_data["body_html"],
            )
            messages.success(request, f"Announcement sent to {ann.recipient_count} recipient(s).")
            return (
                redirect("announcements")
                if event is None
                else redirect("event_detail", pk=event.pk)
            )
        filters = form.filters(cats)
    else:
        form = AnnounceForm(
            initial={
                k: v
                for k, v in request.GET.items()
                if k in ("subject", "day", "role", "status", "confirmation")
            }
        )
        filters = _filters_from_get(request)
    recipients = announce.resolve_audience(event, filters)
    days = []
    if event is not None:
        zone = display_zone(event)
        seen = set()
        from apps.events.models import Slot

        for s in Slot.objects.filter(position__location__event=event, cancelled=False).order_by(
            "start"
        ):
            d = s.start.astimezone(zone)
            key = d.strftime("%Y-%m-%d")
            if key not in seen:
                seen.add(key)
                days.append((key, d.strftime("%A %-d %B")))
    return render(
        request,
        "comms/announce.html",
        {
            "form": form,
            "event": event,
            "filters": filters,
            "recipients": recipients,
            "days": days,
            "roles": roles,
            "categories": categories,
            "statuses": [
                ("open", "Open (nobody yet)"),
                ("needs", "Needs someone"),
                ("thin", "Covered, depends on one person"),
                ("covered", "Covered"),
            ],
        },
    )


@login_required
def announcements(request):
    """FR-75: every announcement, visible to officers afterwards."""
    if not request.user.is_officer:
        raise Http404
    qs = Announcement.objects.select_related("sender", "event")
    return render(request, "comms/announcements.html", {"announcements": qs[:200]})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def unsubscribe(request, token):
    """FR-81: the link in every announcement, and the one-click POST that mail clients send.
    Only the announcement category is affected; notices about the member's own slots and
    account keep coming (FR-71)."""
    user = announce.user_from_unsubscribe_token(token)
    if user is None:
        return render(request, "comms/unsubscribe.html", {"state": "invalid"}, status=410)
    if request.method == "POST":
        announce.set_announcement_email(user, on=False)
        if request.POST.get("List-Unsubscribe") == "One-Click":
            return HttpResponse("unsubscribed", content_type="text/plain")
        return render(request, "comms/unsubscribe.html", {"state": "done", "person": user})
    return render(
        request, "comms/unsubscribe.html", {"state": "confirm", "person": user, "token": token}
    )
