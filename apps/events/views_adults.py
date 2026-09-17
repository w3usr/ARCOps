"""FR-64: the responsible adults accompanying a minor for one slot. The guardian names them
(fresh, from the adults they have named before, or a member by name); captains and officers
edit the designation on the guardian's behalf. An adult takes no seat and is not counted."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import AccessLevel, Guardianship, User
from apps.ops.audit import record

from .models import ResponsibleAdult, SignUp


def may_designate(viewer, su: SignUp) -> bool:
    real = getattr(viewer, "acting_guardian", None) or viewer
    if viewer.can_captain(su.slot.event):
        return True
    return Guardianship.objects.filter(minor=su.user, guardian=real, active=True).exists()


def previously_named(su: SignUp) -> list[dict]:
    """Adults named before for this minor or for any ward of their guardians, deduplicated."""
    guardians = Guardianship.objects.filter(minor=su.user, active=True).values_list(
        "guardian_id", flat=True
    )
    minors = Guardianship.objects.filter(guardian_id__in=guardians, active=True).values_list(
        "minor_id", flat=True
    )
    seen, out = set(), []
    for a in (
        ResponsibleAdult.objects.filter(signup__user_id__in=list(minors) + [su.user_id])
        .exclude(signup=su)
        .order_by("-id")
    ):
        key = (a.name.lower(), a.email.lower(), a.phone, a.member_id)
        if key in seen:
            continue
        seen.add(key)
        out.append({"name": a.name, "email": a.email, "phone": a.phone, "member_id": a.member_id})
    return out


@login_required
@require_http_methods(["GET", "POST"])
def adults(request, signup_id):
    su = get_object_or_404(
        SignUp.objects.select_related("user", "slot__position__location__event"), pk=signup_id
    )
    if not su.user.under_18 or not may_designate(request.user, su):
        raise Http404
    if request.method == "POST":
        action = request.POST.get("action", "add")
        if action == "remove":
            a = get_object_or_404(ResponsibleAdult, pk=request.POST.get("adult"), signup=su)
            record(request.user, "responsible_adult.removed", su, before={"name": a.name})
            a.delete()
            messages.success(request, f"{a.name} removed.")
        elif action == "pick":  # from the saved list: "name|email|phone|member_id"
            name, email, phone, member_id = (request.POST.get("saved", "") + "|||").split("|")[:4]
            member = User.objects.filter(pk=member_id).first() if member_id else None
            if name.strip():
                ResponsibleAdult.objects.create(
                    signup=su,
                    name=name.strip(),
                    email=email.strip(),
                    phone=phone.strip(),
                    member=member,
                )
                record(request.user, "responsible_adult.named", su, after={"name": name.strip()})
                messages.success(request, f"{name.strip()} will accompany {su.user.display_first}.")
        elif action == "member":
            member = get_object_or_404(User, pk=request.POST.get("member"), under_18=False)
            if member.access_level == AccessLevel.NONE:
                raise Http404
            ResponsibleAdult.objects.create(
                signup=su,
                name=member.full_name,
                email=member.email,
                phone=member.cell_phone,
                member=member,
            )
            record(
                request.user,
                "responsible_adult.named",
                su,
                after={"name": member.full_name, "member": member.pk},
            )
            messages.success(request, f"{member.full_name} will accompany {su.user.display_first}.")
        else:
            name, email, phone = (
                request.POST.get(k, "").strip() for k in ("name", "email", "phone")
            )
            if not name or not phone:
                messages.error(request, "A name and a phone number are needed.")
            else:
                ResponsibleAdult.objects.create(
                    signup=su, name=name[:120], email=email[:254], phone=phone[:30]
                )
                record(request.user, "responsible_adult.named", su, after={"name": name})
                messages.success(request, f"{name} will accompany {su.user.display_first}.")
        return redirect("signup_adults", signup_id=su.pk)
    return render(
        request,
        "events/adults.html",
        {
            "su": su,
            "event": su.slot.event,
            "slot": su.slot,
            "adults": list(su.responsible_adults.all()),
            "saved": previously_named(su),
            "members": User.objects.filter(under_18=False)
            .exclude(access_level=AccessLevel.NONE)
            .order_by("last_name", "first_name"),
        },
    )
