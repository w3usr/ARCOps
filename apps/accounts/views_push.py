"""Browser-notification subscriptions (FR-112): one per device, revocable from the profile."""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import PushSubscription


@login_required
@require_POST
def push_subscribe(request):
    """The browser posts its PushSubscription JSON after the person grants permission."""
    try:
        data = json.loads(request.body or b"{}")
        endpoint = data["endpoint"]
        keys = data["keys"]
        p256dh, auth = keys["p256dh"], keys["auth"]
    except (ValueError, KeyError, TypeError):
        return HttpResponseBadRequest("subscription JSON expected")
    if not endpoint.startswith("https://") or len(endpoint) > 1000:
        return HttpResponseBadRequest("bad endpoint")
    sub, created = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh[:200],
            "auth": auth[:100],
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
        },
    )
    return JsonResponse({"ok": True, "created": created, "id": sub.pk})


@login_required
@require_POST
def push_revoke(request, pk):
    sub = get_object_or_404(PushSubscription, pk=pk, user=request.user)
    sub.delete()
    messages.success(request, "That device will get no more browser notifications.")
    return redirect(reverse("profile_edit") + "#notifications")


@login_required
@require_POST
def push_toggle(request):
    """The member's own switch for browser notifications as a whole (FR-112)."""
    request.user.push_enabled = request.POST.get("push_enabled") == "on"
    request.user.save(update_fields=["push_enabled"])
    messages.success(
        request,
        "Browser notifications on." if request.user.push_enabled else "Browser notifications off.",
    )
    return redirect(reverse("profile_edit") + "#notifications")
