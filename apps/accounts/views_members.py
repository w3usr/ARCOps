"""
The member directory (FR-13) and the per-member page where accounts are managed (FR-6, FR-7,
§2.1 to §2.3) without the Django admin.

Who sees what: every member sees the directory as short names and callsigns (FR-67). Officers
and sysadmins see full names, contact details, and each member's standing. Sysadmins edit the
privilege fields (category, access level, club position, minor flag, and the name when it was not
taken from the FCC record), issue a one-time temporary password, and close an account. Officers
set club position (§2.3) and nothing else on another account.
"""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.credentials.models import LicenseRecord, SignedAgreement
from apps.ops.audit import record
from apps.ops.config import setting

from .models import AccessLevel, User
from .services import issue_temporary_password, set_access_level

PRIVILEGE_FIELDS = ("category", "club_position", "access_level", "under_18", "callsign")
NAME_FIELDS = ("first_name", "middle_name", "last_name")


class MemberForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [*NAME_FIELDS, *PRIVILEGE_FIELDS]

    def __init__(self, *args, actor: User, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        cats = setting("member_categories", []) or []
        positions = setting("club_positions", []) or []
        self.fields["category"] = forms.ChoiceField(
            choices=[(c["key"], c["label"]) for c in cats], required=False
        )
        self.fields["club_position"] = forms.ChoiceField(
            choices=[("", "None")] + [(p["key"], p["label"]) for p in positions], required=False
        )
        self.fields["access_level"] = forms.ChoiceField(choices=AccessLevel.choices)
        self.fields["under_18"].label = "Under 18"
        if self.instance.name_from_uls:
            for f in NAME_FIELDS:  # FR-4: the FCC record's name is read-only
                self.fields.pop(f)
        if not actor.is_sysadmin:  # §2.3: an officer sets club position, nothing else
            for f in list(self.fields):
                if f != "club_position":
                    self.fields.pop(f)


def _standing(user) -> dict:
    """What an officer needs at a glance: license and agreements."""
    lic = LicenseRecord.objects.filter(user=user).first()
    agreements = (
        SignedAgreement.objects.filter(user=user)
        .select_related("template")
        .order_by("template__title", "-id")
    )
    latest = {}
    for a in agreements:
        latest.setdefault(a.template_id, a)
    return {"licence": lic, "agreements": list(latest.values())}


@login_required
def members(request):
    full = request.user.is_officer
    q = request.GET.get("q", "").strip()
    users = User.objects.all() if full else User.objects.exclude(access_level=AccessLevel.NONE)
    if q:
        cond = (
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(preferred_name__icontains=q)
            | Q(callsign__icontains=q)
        )
        if full:
            cond |= Q(email__icontains=q) | Q(institution_email__icontains=q) | Q(personal_email__icontains=q)
        users = users.filter(cond)
    users = users.order_by("last_name", "first_name")
    positions = {p["key"]: p["label"] for p in (setting("club_positions", []) or [])}
    cats = {c["key"]: c["label"] for c in (setting("member_categories", []) or [])}
    return render(
        request,
        "accounts/members.html",
        {"members": users, "q": q, "full": full, "positions": positions, "categories": cats},
    )


@login_required
@require_http_methods(["GET", "POST"])
def member_detail(request, pk):
    if not request.user.is_officer:
        raise Http404
    member = get_object_or_404(User, pk=pk)
    actor = request.user
    temp_password = None
    form = MemberForm(instance=member, actor=actor)

    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "save":
            form = MemberForm(request.POST, instance=member, actor=actor)
            if form.is_valid():
                before = {f: getattr(User.objects.get(pk=member.pk), f) for f in form.changed_data}
                if (
                    "access_level" in form.changed_data
                    and member == actor
                    and form.cleaned_data["access_level"] != AccessLevel.SYSADMIN
                ):
                    form.add_error("access_level", "You cannot remove your own sysadmin access.")
                else:
                    user = form.save(commit=False)
                    user.callsign = (user.callsign or "").upper().strip()
                    user.save()
                    if form.changed_data:
                        record(
                            actor,
                            "member.edited",
                            user,
                            before=before,
                            after={f: getattr(user, f) for f in form.changed_data},
                        )
                    messages.success(request, "Saved.")
                    return redirect("member_detail", pk=member.pk)
        elif action == "temporary_password" and actor.is_sysadmin:
            temp_password = issue_temporary_password(actor, member)
            hours = int(setting("defaults.temporary_password_expiry_hours", 72))
            messages.success(
                request,
                f"Temporary password issued. It works once, within {hours} hours, and is shown only here.",
            )
        elif action == "close" and actor.is_sysadmin:
            if member == actor:
                messages.error(request, "You cannot close your own account.")
            else:
                set_access_level(actor, member, AccessLevel.NONE, request.POST.get("reason", ""))
                messages.success(request, f"{member.short_name} no longer has access.")
                return redirect("member_detail", pk=member.pk)
        elif action == "reopen" and actor.is_sysadmin:
            set_access_level(actor, member, AccessLevel.MEMBER, "reopened")
            messages.success(request, f"{member.short_name} is a member again.")
            return redirect("member_detail", pk=member.pk)
        else:
            raise Http404

    return render(
        request,
        "accounts/member_detail.html",
        {
            "member": member,
            "form": form,
            "temp_password": temp_password,
            "standing": _standing(member),
            "is_self": member == actor,
        },
    )
