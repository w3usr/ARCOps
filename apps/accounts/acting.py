"""
Acting at a lower level than you hold.

The advisor, 2026-09-17: *"I don't always like being logged in with the superuser view, even
though my account has superuser capabilities. I want it so that supervisors can change the view
level of their account view easily... By default, it is set to the highest level below superuser.
To get superuser, the user has to explicitly change the view and re-authenticate."*

So a session carries a **view**: a group whose capabilities are the ones that count for this
session, chosen from the groups whose capabilities this account actually holds. A sysadmin signs
in acting as the configured everyday view (Faculty advisor here), and raising back to Sysadmin
asks for the password again.

The point of it is that the lower view is **real**. It is not a filter over what the pages draw:
`User.has_perm` answers from the view, so a request the view does not allow is refused exactly as
it would be for somebody who genuinely held that group. A view that only hid buttons would be
worse than none, because it would be trusted.

What it protects against: a session someone else picks up, a stray click on a page that deletes
things, and a mistake made while tired. What it does not protect against: somebody who has the
password, since they can raise the view too. It is a seatbelt, not a lock.
"""

from __future__ import annotations

from django.contrib.auth.models import Group
from django.utils.deprecation import MiddlewareMixin

from apps.ops.capabilities import APP_LABEL

SESSION_KEY = "acting_view"
SYSADMIN = "sysadmin"  # the view that holds everything; the same thing as being a superuser


def full_capabilities(user) -> set[str]:
    """Everything this account holds, ignoring whatever view it is acting at."""
    if user.is_superuser:
        from apps.ops.capabilities import CODENAMES

        return set(CODENAMES)
    return {
        codename
        for perm in user.get_all_permissions()
        for app, codename in [perm.split(".", 1)]
        if app == APP_LABEL
    }


def capabilities_of(view: str) -> set[str]:
    """What a named view grants. The sysadmin view grants everything."""
    if view == SYSADMIN:
        from apps.ops.capabilities import CODENAMES

        return set(CODENAMES)
    group = Group.objects.filter(name=view).first()
    if group is None:
        return set()
    return {p.codename for p in group.permissions.all()}


def available_views(user) -> list[dict]:
    """The views this account may act at: every group whose capabilities it already holds, and
    the sysadmin view for a sysadmin. Nobody can pick a view above themselves, because a view is
    only offered when its capabilities are a subset of what the account holds."""
    from apps.ops.config import setting
    from apps.ops.groups import label_of

    held = full_capabilities(user)
    views = []
    for group in Group.objects.order_by("name"):
        capabilities = {p.codename for p in group.permissions.all()}
        if capabilities <= held:
            views.append(
                {
                    "key": group.name,
                    "label": label_of(group, setting("access_groups", []) or []),
                    "count": len(capabilities),
                    "raises": False,
                }
            )
    views.sort(key=lambda v: v["count"])  # smallest first, so the list reads as a ladder
    if user.is_superuser:
        views.append({"key": SYSADMIN, "label": "Sysadmin", "count": len(held), "raises": True})
    return views


def default_view(user) -> str | None:
    """What an account acts at when it signs in: the club's configured everyday view, when this
    account holds everything that view grants. Anyone who does not hold it acts as themselves,
    because dropping somebody to a view they could not otherwise reach would be surprising."""
    from apps.ops.config import setting

    wanted = str(setting("defaults.default_view", "") or "").strip()
    if not wanted:
        return None
    if wanted == SYSADMIN:
        return SYSADMIN if user.is_superuser else None
    held = full_capabilities(user)
    granted = capabilities_of(wanted)
    if granted and granted < held:  # strictly smaller, or it is no reduction at all
        return wanted
    return None


def current_view(request) -> str | None:
    """The view this session is acting at, or None for "everything this account holds"."""
    return request.session.get(SESSION_KEY)


def set_view(request, view: str | None) -> None:
    if view is None:
        request.session.pop(SESSION_KEY, None)
    else:
        request.session[SESSION_KEY] = view


def raises_privilege(user, from_view: str | None, to_view: str | None) -> bool:
    """Whether moving between these views grants anything it did not grant before. Going up asks
    for the password again; going down never does."""
    before = full_capabilities(user) if from_view is None else capabilities_of(from_view)
    after = full_capabilities(user) if to_view is None else capabilities_of(to_view)
    return bool(after - before)


class ActingViewMiddleware(MiddlewareMixin):
    """Put the session's view on the user object, where `has_perm` reads it."""

    def process_request(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        view = request.session.get(SESSION_KEY)
        if view is None:
            view = default_view(user)
            if view is not None:
                request.session[SESSION_KEY] = view
        if view is None or view == SYSADMIN:
            user.acting_view = view
            user.acting_capabilities = None  # everything this account holds
            return None
        granted = capabilities_of(view) & full_capabilities(user)
        user.acting_view = view
        user.acting_capabilities = granted
        return None


def context(request):
    """The level this session is acting at, for the sidebar on every page."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or getattr(request, "impersonator", None):
        return {}
    views = available_views(user)
    now = current_view(request)
    label = next((v["label"] for v in views if v["key"] == now), "")
    if not label and views:
        label = "Everything your account holds"
    return {"acting_views": len(views), "acting_label": label, "acting_now": now}
