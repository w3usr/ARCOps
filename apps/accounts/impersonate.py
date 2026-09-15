"""
FR-94: a sysadmin views the application as a member, read-only, to reproduce what the member
reports seeing. The real sysadmin stays signed in; the session carries the member's id; every
request renders as the member; every state-changing request is refused; start and stop are
audited. Never for another sysadmin's account.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.http import require_POST

from apps.ops.audit import record

from .models import User

SESSION_KEY = "impersonate_user_id"
STOP_PATH = "/me/view-as/stop/"


class ImpersonationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        target_id = request.session.get(SESSION_KEY)
        real = getattr(request, "user", None)
        if not target_id or real is None or not real.is_authenticated or not real.is_sysadmin:
            request.impersonator = None
            return None
        target = User.objects.filter(pk=target_id).first()
        if target is None or target.is_sysadmin:
            request.session.pop(SESSION_KEY, None)
            request.impersonator = None
            return None
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.path != STOP_PATH:
            return HttpResponseForbidden(
                "Viewing as a member is read-only: nothing can be changed from this view. Stop viewing as them first."
            )
        request.impersonator = real
        request.user = target
        return None


@login_required
@require_POST
def start(request, pk):
    if not request.user.is_sysadmin or getattr(request, "impersonator", None):
        raise Http404
    target = get_object_or_404(User, pk=pk)
    if target.is_sysadmin:
        messages.error(request, "Another sysadmin's view cannot be impersonated.")
        return redirect("member_detail", pk=pk)
    request.session[SESSION_KEY] = target.pk
    record(request.user, "impersonation.started", target)
    messages.info(
        request,
        f"You are now viewing the application as {target.short_name}. Nothing can be changed until you stop.",
    )
    return redirect("dashboard")


@require_POST
def stop(request):
    real = getattr(request, "impersonator", None) or request.user
    target_id = request.session.pop(SESSION_KEY, None)
    if target_id and real.is_authenticated:
        record(real, "impersonation.stopped", User.objects.filter(pk=target_id).first())
    return redirect(reverse("member_detail", args=[target_id]) if target_id else "dashboard")


def is_impersonating(request) -> bool:
    return getattr(request, "impersonator", None) is not None


def context(request):
    """Template context: the banner needs to know."""
    imp = getattr(request, "impersonator", None)
    return {"impersonator": imp} if imp else {}
