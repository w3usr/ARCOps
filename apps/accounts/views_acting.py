"""The page where somebody changes the level their own session acts at.

Raising the level asks the person to prove who they are, and that proof is the sign-in
library's, not ours: it accepts a password **or a passkey**, whichever the account carries.

> I should be able to use a passkey in addition to a password here. — NAF, 2026-09-20

So the page holds no password field. Choosing a level that can do more sends the person to
Confirm Access, which offers whatever they have enrolled, and brings them back here to finish
the change. Someone who confirmed a moment ago is not asked twice, which is the same window
that guards adding a second factor (TR-17).
"""

from __future__ import annotations

from urllib.parse import urlencode

# The public module of this name is a deprecation shim around the same function; the
# library's own views import it from here.
from allauth.account.internal.flows.reauthentication import did_recently_authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
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

PENDING = "acting_view_pending"  # the level asked for, while Confirm Access happens


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
    pending = request.session.get(PENDING)
    if request.method == "GET" and pending:
        # Back from Confirm Access. The library says whether the person proved who they are;
        # how they proved it, by password or by passkey, is its business and not ours.
        request.session.pop(PENDING, None)
        wanted = pending.get("view", "")
        if wanted not in {v["key"] for v in views}:
            raise Http404
        if not did_recently_authenticate(request):
            record(user, "view.raise_refused", user, after={"to": wanted})
            messages.error(request, "That was not confirmed, so the level is unchanged.")
            return redirect("acting_view")
        return _raise_to(request, views, now, wanted, pending.get("next") or "")

    if request.method == "POST":
        wanted = request.POST.get("view", "")
        if wanted not in {v["key"] for v in views}:
            messages.error(request, "That is not a level your account can act at.")
            return redirect("acting_view")
        if wanted == now:
            return redirect(request.POST.get("next") or "dashboard")

        if raises_privilege(user, now, wanted):
            nxt = request.POST.get("next") or ""
            if did_recently_authenticate(request):
                return _raise_to(request, views, now, wanted, nxt)
            request.session[PENDING] = {"view": wanted, "next": nxt}
            back = reverse("acting_view")
            return redirect(f"{reverse('account_reauthenticate')}?{urlencode({'next': back})}")
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


def _raise_to(request, views, now, wanted: str, nxt: str):
    """Put the session at a level that can do more, the proof already given."""
    set_view(request, wanted)
    record(request.user, "view.raised", request.user, before={"from": now}, after={"to": wanted})
    messages.success(
        request, f"You are acting as {_label(views, wanted)}. Drop back when you are done."
    )
    return redirect(nxt or "dashboard")


def _label(views, key: str) -> str:
    for view in views:
        if view["key"] == key:
            return view["label"]
    return key
