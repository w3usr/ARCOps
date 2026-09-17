"""
The page where the club decides what each of its groups may do.

This is the half of the permission model that belongs to the club rather than to the code: the
capabilities are fixed (apps/ops/capabilities.py), and which of them a group holds is not. A
sysadmin can also make a group the application has never heard of, which is the point of the
advisor's design: a club with a Station Manager or an Archivist writes one down here instead of
asking for a new release.

Two things this page refuses, because neither is recoverable from inside the application: taking
the last "decide who may do what" away from everybody, and deleting a group somebody is still in.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .audit import record
from .capabilities import APP_LABEL, CAPABILITIES, LABELS
from .config import setting
from .groups import label_of


def _rows():
    configured = setting("access_groups", []) or []
    rows = []
    for group in Group.objects.order_by("name").prefetch_related("permissions"):
        held = {p.codename for p in group.permissions.all()}
        rows.append(
            {
                "group": group,
                "label": label_of(group, configured),
                "held": held,
                "members": group.user_set.count(),
                "capabilities": [
                    {"code": code, "label": label, "held": code in held}
                    for code, label in CAPABILITIES
                ],
            }
        )
    return rows


@login_required
@require_http_methods(["GET", "POST"])
def groups_page(request):
    if not request.user.may("manage_groups"):
        raise Http404

    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "new":
            name = (request.POST.get("name") or "").strip().lower().replace(" ", "_")[:60]
            if not name:
                messages.error(request, "A group needs a name.")
            elif Group.objects.filter(name=name).exists():
                messages.error(request, f"There is already a group called {name}.")
            else:
                Group.objects.create(name=name)
                record(request.user, "group.created", None, after={"group": name})
                messages.success(
                    request, f"{name} created. Tick what it may do, then save the page."
                )
            return redirect("groups_page")

        if action == "delete":
            group = Group.objects.filter(pk=request.POST.get("group")).first()
            if group is None:
                raise Http404
            if group.user_set.exists():
                messages.error(
                    request,
                    f"{group.name} still has members; move them to another group first.",
                )
            else:
                record(request.user, "group.deleted", None, before={"group": group.name})
                group.delete()
                messages.success(request, "Group deleted.")
            return redirect("groups_page")

        # Saving the grid: each group named by the form keeps exactly what is ticked for it. The
        # form says which groups it covers, because "no boxes ticked" and "this group was not on
        # the page" are different things and only one of them means "nothing".
        changed = []
        on_the_page = Group.objects.filter(pk__in=request.POST.getlist("groups_in_form"))
        for group in on_the_page:
            wanted = set(request.POST.getlist(f"caps_{group.pk}")) & set(LABELS)
            held = {p.codename for p in group.permissions.all()}
            if wanted == held:
                continue
            group.permissions.set(
                Permission.objects.filter(content_type__app_label=APP_LABEL, codename__in=wanted)
            )
            changed.append((group, sorted(held), sorted(wanted)))

        # nobody may save away the last account that can decide who may do what
        if not _anyone_assigns_groups():
            for group, held, _ in changed:
                group.permissions.set(
                    Permission.objects.filter(content_type__app_label=APP_LABEL, codename__in=held)
                )
            messages.error(
                request,
                "That would leave nobody able to decide who may do what, so nothing was saved.",
            )
            return redirect("groups_page")

        for group, held, wanted in changed:
            record(
                request.user,
                "group.capabilities_changed",
                None,
                before={"group": group.name, "capabilities": held},
                after={"group": group.name, "capabilities": wanted},
            )
        messages.success(
            request,
            f"Saved. {len(changed)} group{'s' if len(changed) != 1 else ''} changed."
            if changed
            else "Nothing to save.",
        )
        return redirect("groups_page")

    return render(
        request,
        "ops/groups.html",
        {"rows": _rows(), "capabilities": CAPABILITIES},
    )


def _anyone_assigns_groups() -> bool:
    from .groups import people_who_may

    return people_who_may("assign_groups").exists()
