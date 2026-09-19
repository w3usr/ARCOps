"""The page where somebody changes the level their own session acts at."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.ops.audit import record

from .acting import (
    SYSADMIN,
    available_views,
    capabilities_of,
    current_view,
    full_capabilities,
    raises_privilege,
    set_view,
)


@login_required
@require_http_methods(["GET", "POST"])
def acting_view(request):
    user = request.user
    views = available_views(user)
    if len(views) < 2:
        # Nothing to choose between: either this is not a sysadmin's account, which has no
        # levels at all (§2.1), or it holds one level's worth of capabilities.
        raise Http404

    now = current_view(request)
    if request.method == "POST":
        wanted = request.POST.get("view", "")
        if wanted not in {v["key"] for v in views}:
            messages.error(request, "That is not a level your account can act at.")
            return redirect("acting_view")
        if wanted == now:
            return redirect(request.POST.get("next") or "dashboard")

        if raises_privilege(user, now, wanted):
            password = request.POST.get("password", "")
            if not user.check_password(password):
                record(user, "view.raise_refused", user, after={"to": wanted})
                messages.error(
                    request,
                    "That password is not right, so the level is unchanged.",
                )
                return redirect("acting_view")
            set_view(request, wanted)
            record(user, "view.raised", user, before={"from": now}, after={"to": wanted})
            messages.success(
                request,
                f"You are acting as {_label(views, wanted)}. Drop back when you are done.",
            )
        else:
            set_view(request, wanted)
            record(user, "view.lowered", user, before={"from": now}, after={"to": wanted})
            messages.success(
                request,
                f"You are acting as {_label(views, wanted)}. What this view cannot do is "
                "refused, not merely hidden.",
            )
        return redirect(request.POST.get("next") or "dashboard")

    held = full_capabilities(user)
    rows = []
    for view in views:
        granted = capabilities_of(view["key"]) if view["key"] != SYSADMIN else held
        rows.append(
            {
                **view,
                "current": view["key"] == now,
                "raises": bool(granted - (capabilities_of(now) if now else held)),
            }
        )
    return render(
        request,
        "accounts/acting_view.html",
        {"views": rows, "current": now, "next": request.GET.get("next", "")},
    )


def _label(views, key: str) -> str:
    for view in views:
        if view["key"] == key:
            return view["label"]
    return key
