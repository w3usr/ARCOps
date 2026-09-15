"""My messages (FR-82, FR-108), the officer outbox (FR-105), and template editing (FR-78)."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from tinymce.widgets import TinyMCE

from apps.ops.audit import record
from apps.ops.config import setting
from apps.ops.templatetags.richtext import sanitise

from .defaults import DEFAULTS_BY_KEY
from .models import MessageTemplate, Outbox
from .services import render_message, seed_templates


@login_required
def my_messages(request):
    qs = Outbox.objects.filter(user=request.user)
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    unread_ids = {m.pk for m in page.object_list if m.read_at is None}
    for m in page.object_list:
        m.was_unread = m.pk in unread_ids
    if unread_ids:
        Outbox.objects.filter(pk__in=unread_ids).update(read_at=timezone.now())
    return render(request, "comms/my_messages.html", {"page": page})


@login_required
def outbox(request):
    if not request.user.is_officer:
        raise Http404
    state = request.GET.get("state", "")
    qs = Outbox.objects.select_related("user")
    if state:
        qs = qs.filter(state=state)
    since = timezone.now() - timezone.timedelta(days=30)
    recent = Outbox.objects.filter(created__gte=since)
    counts = {
        "total": recent.count(),
        "sent": recent.filter(state=Outbox.State.SENT).count(),
        "failed": recent.filter(state=Outbox.State.FAILED).count(),
        "not_sent": recent.filter(state=Outbox.State.NOT_SENT).count(),
        "skipped": recent.filter(state=Outbox.State.SKIPPED).count(),
    }
    return render(
        request,
        "ops/outbox.html",
        {
            "page": Paginator(qs, 100).get_page(request.GET.get("page")),
            "state": state,
            "states": Outbox.State.choices,
            "counts": counts,
            "delivery_mode": str(setting("defaults.email_delivery", "off")).lower(),
        },
    )


class TemplateForm(forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = ["subject", "body_html"]
        widgets = {"body_html": TinyMCE(attrs={"rows": 14})}  # FR-115
        labels = {"body_html": "Body (HTML)"}

    def clean_body_html(self):
        return sanitise(self.cleaned_data["body_html"])


SAMPLE_CONTEXT = {
    "link": "https://example.org/me/invite/abc123/",
    "expires": timezone.now() + timezone.timedelta(days=14),
    "days": 7,
    "via": "an example course link",
    "reason": "example reason",
    "person": {
        "full_name": "Sample Person",
        "short_name": "Sample N0CALL (T)",
        "callsign": "N0CALL",
    },
    "user": {"display_first": "Sample", "full_name": "Sample Person"},
}


@login_required
def message_templates(request):
    if not request.user.is_sysadmin:
        raise Http404
    seed_templates()  # a fresh installation sees the shipped set at once
    return render(
        request, "ops/templates.html", {"templates": MessageTemplate.objects.order_by("key")}
    )


@login_required
def message_template_edit(request, key):
    if not request.user.is_sysadmin:
        raise Http404
    seed_templates()
    tpl = get_object_or_404(MessageTemplate, key=key)
    if request.method == "POST":
        if request.POST.get("reset") and key in DEFAULTS_BY_KEY:
            d = DEFAULTS_BY_KEY[key]
            before = {"subject": tpl.subject, "body_html": tpl.body_html}
            tpl.subject, tpl.body_html, tpl.edited = d["subject"], d["body_html"], False
            tpl.save()
            record(request.user, "template.reset", tpl, before=before)
            messages.success(request, "Shipped default restored.")
            return redirect("message_template_edit", key=key)
        form = TemplateForm(request.POST, instance=tpl)
        if form.is_valid():
            before = {"subject": tpl.subject, "body_html": tpl.body_html}
            tpl = form.save(commit=False)
            tpl.edited = True
            tpl.save()
            record(
                request.user,
                "template.edited",
                tpl,
                before=before,
                after={"subject": tpl.subject, "body_html": tpl.body_html},
            )
            messages.success(request, "Template saved.")
            return redirect("message_template_edit", key=key)
    else:
        form = TemplateForm(instance=tpl)
    try:
        preview_subject, preview_body = render_message(key, SAMPLE_CONTEXT)
    except Exception as exc:  # noqa: BLE001 - a broken template must still be editable
        preview_subject, preview_body = "(template error)", f"<p>{exc}</p>"
    return render(
        request,
        "ops/template_edit.html",
        {
            "template": tpl,
            "form": form,
            "preview_subject": preview_subject,
            "preview_body": preview_body,
        },
    )
