"""
The member directory (FR-13) and the per-member page where accounts are managed (FR-6, FR-7,
§2.1 to §2.3) without the Django admin.

Who sees what: every member sees the directory as short names and callsigns (FR-67). Officers
and sysadmins see full names, contact details, and each member's standing. Sysadmins edit the
privilege fields (category, access level, club position, minor flag, and the name when it was not
taken from the FCC record), issue a one-time temporary password, and close an account. Officers
set club position (§2.3) and nothing else on another account.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.credentials.models import LicenseRecord, SignedAgreement
from apps.credentials.views import _is_approver
from apps.ops.audit import record
from apps.ops.config import setting

from . import entry, views_addresses
from .account import AccountForm, readonly_rows, save_account
from .models import User
from .services import issue_temporary_password, set_access


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
    full = request.user.may("view_member_records")
    q = request.GET.get("q", "").strip()
    # The directory is who the club has now. A former member is in the archive (FR-125), which
    # is read by a faculty advisor or a sysadmin, so they are out of this list for everyone.
    current = User.objects.filter(archived_at__isnull=True)
    users = (
        # the directory shows every address an officer may write to, so they come in one query
        current.select_related("joined_via", "license").prefetch_related("addresses")
        if full
        else current.filter(groups__permissions__codename="view_directory")
        .distinct()
        .select_related("license")
    )
    if not request.user.is_member:
        raise Http404  # FR-121: a Provisional member sees no directory
    if q:
        cond = (
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(preferred_name__icontains=q)
            | Q(callsign__icontains=q)
        )
        if full:
            cond |= Q(addresses__address__icontains=q)
        users = users.filter(cond)
    users = users.order_by("last_name", "first_name")
    positions = {p["key"]: p["label"] for p in (setting("club_positions", []) or [])}
    cats = {c["key"]: c["label"] for c in (setting("member_categories", []) or [])}
    return render(
        request,
        "accounts/members.html",
        {"members": users, "q": q, "full": full, "positions": positions, "categories": cats},
    )


def _still_assigns_groups(form, actor, member) -> bool:
    """Whoever is editing keeps the capability that assigns capabilities. Without this, one save
    can leave a club with nobody able to give anyone access, and no way back but the shell."""
    if "groups" not in form.changed_data or member != actor or actor.is_superuser:
        return True  # a superuser cannot lose it, and nobody else's account is at stake here
    wanted = form.cleaned_data.get("groups") or []
    return any(g.permissions.filter(codename="assign_groups").exists() for g in wanted)


@login_required
def archive(request):
    """The club's record of its former members (FR-125). Only a faculty advisor or a sysadmin
    reads it: it holds contact details and history for people who have left, which is the most
    that anyone here holds about someone who is no longer around to ask."""
    if not request.user.may("view_archive"):
        raise Http404
    from .services import archived_members

    q = request.GET.get("q", "").strip()
    people = archived_members().select_related("license").prefetch_related("addresses")
    if q:
        people = people.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(preferred_name__icontains=q)
            | Q(callsign__icontains=q)
            | Q(addresses__address__icontains=q)
            | Q(archived_reason__icontains=q)
        ).distinct()
    record(request.user, "archive.viewed", None, after={"search": q} if q else None)
    cats = {c["key"]: c["label"] for c in (setting("member_categories", []) or [])}
    return render(request, "accounts/archive.html", {"people": people, "q": q, "categories": cats})


@login_required
@require_http_methods(["GET", "POST"])
def member_detail(request, pk):
    if not request.user.may("view_member_records"):
        raise Http404
    member = get_object_or_404(User, pk=pk)
    actor = request.user
    if member.is_archived and not actor.may("view_archive"):
        raise Http404  # the archive is the advisor's to read, and so is a page within it
    temp_password = None
    form = AccountForm(instance=member, actor=actor)

    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "save":
            form = AccountForm(request.POST, instance=member, actor=actor)
            if form.is_valid():
                keeps_the_keys = _still_assigns_groups(form, actor, member)
                if not keeps_the_keys:
                    form.add_error(
                        "groups",
                        "You cannot take away your own ability to decide who may do what.",
                    )
                else:
                    result = save_account(form, actor, f"{request.scheme}://{request.get_host()}")
                    call = result["callsign"]
                    if call and call["state"] == "pending":
                        messages.warning(
                            request,
                            f"The FCC lists {member.callsign} under the name {call['uls_name']}. "
                            f"{member.display_first} is asked to confirm it on their profile "
                            "before it is kept.",
                        )
                    elif call and call["state"] == "unverified":
                        messages.info(
                            request,
                            f"{member.callsign} is not in the FCC table yet; it is held as "
                            "unverified until the nightly import finds it.",
                        )
                    messages.success(request, "Saved.")
                    return redirect("member_detail", pk=member.pk)
        elif views_addresses.handle(request, member):
            return redirect("member_detail", pk=member.pk)
        elif action == "license_lookup":  # any officer: FR-14, the local FCC table
            from apps.credentials.models import UlsLicense
            from apps.credentials.services import refresh_license_from_local_table

            if not member.callsign:
                messages.error(request, "This member has no callsign to look up.")
            else:
                found = UlsLicense.objects.filter(callsign=member.callsign.upper()).exists()
                lic = refresh_license_from_local_table(member)
                record(actor, "license.looked_up", member, after={"callsign": member.callsign})
                if found:
                    messages.success(
                        request,
                        f"{member.callsign}: {lic.operator_class or 'no class'}, {lic.status}"
                        + (f", expires {lic.expiry_date}" if lic.expiry_date else "")
                        + f" ({lic.licensee_name}).",
                    )
                else:
                    messages.warning(
                        request,
                        f"{member.callsign} is not in the local FCC table. The nightly import may "
                        "not have reached it yet; a sysadmin can set an override below.",
                    )
            return redirect("member_detail", pk=member.pk)
        elif action == "license_override" and actor.may("override_license"):  # FR-15, FR-20
            from apps.credentials.models import LicenseRecord
            from apps.credentials.services import apply_override, lift_override

            lic, _ = LicenseRecord.objects.get_or_create(
                user=member, defaults={"callsign": member.callsign}
            )
            if request.POST.get("lift"):
                lift_override(actor, lic)
                messages.success(request, "Override lifted; the FCC record applies.")
            elif not request.POST.get("override_reason", "").strip():
                messages.error(request, "An override needs a reason.")
            else:
                from django.utils.dateparse import parse_date

                apply_override(
                    actor,
                    lic,
                    {
                        "override_class": request.POST.get("override_class", "")[:20],
                        "override_status": request.POST.get("override_status", "")[:20],
                        "override_expiry": parse_date(request.POST.get("override_expiry", "") or "")
                        or None,
                        "override_name": request.POST.get("override_name", "")[:120],
                        "override_country": request.POST.get("override_country", "")[:60],
                        "override_reason": request.POST.get("override_reason", "")[:500],
                    },
                )
                messages.success(
                    request,
                    "License override saved; it shows as such wherever the value appears and the nightly import leaves it alone.",
                )
            return redirect("member_detail", pk=pk)
        elif action == "convert_adult" and member.under_18 and actor.may("convert_minor_accounts"):
            from .guardian import convert_to_adult

            temp_password = convert_to_adult(actor, member)
            messages.success(
                request,
                f"{member.display_first} now holds their own account; the guardians have been told. Pass on the temporary password below.",
            )
        elif (
            action == "link_guardian" and actor.may("edit_member_privileges") and member.under_18
        ):  # §2.4
            from .guardian import link_guardian

            g = User.objects.by_address(request.POST.get("guardian_email", "")).first()
            if g is None or g.under_18 or g == member:
                messages.error(
                    request,
                    "No adult account holds that address. Guardians without an account join through the minor's invitation.",
                )
            else:
                link_guardian(actor, member, g, request.POST.get("relationship", "").strip()[:40])
                messages.success(request, f"{g.full_name} linked as guardian.")
        elif action == "unlink_guardian" and actor.may("edit_member_privileges"):
            from .guardian import unlink_guardian
            from .models import Guardianship

            link = get_object_or_404(
                Guardianship, pk=request.POST.get("link"), minor=member, active=True
            )
            if member.under_18 and member.guardianships.filter(active=True).count() == 1:
                messages.error(
                    request,
                    "A member under 18 keeps at least one guardian; link another first, or convert the account.",
                )
            else:
                unlink_guardian(actor, link)
                messages.success(request, f"{link.guardian.full_name} unlinked.")
        elif action == "delete" and actor.may("delete_accounts"):  # FR-118
            from .services import DeletionRefused, delete_account

            reason = request.POST.get("reason", "").strip()
            if request.POST.get("confirm") != "yes" or not reason:
                messages.error(request, "Deletion needs the confirmation ticked and a reason.")
                return redirect("member_detail", pk=pk)
            try:
                result = delete_account(actor, member, reason[:500])
            except DeletionRefused as exc:
                messages.error(request, f"Not deleted: {exc}.")
                return redirect("member_detail", pk=pk)
            messages.success(
                request,
                f"Account deleted. {result['withdrawn']} future sign-up(s) withdrawn; {result['agreements']} signed agreement(s) kept.",
            )
            return redirect("members")
        elif action == "temporary_password" and actor.may("issue_temporary_password"):
            temp_password = issue_temporary_password(actor, member)
            hours = int(setting("defaults.temporary_password_expiry_hours", 72))
            messages.success(
                request,
                f"Temporary password issued. It works once, within {hours} hours, and is shown only here.",
            )
        elif action == "close" and actor.may("assign_groups"):
            if member == actor:
                messages.error(request, "You cannot close your own account.")
            else:
                set_access(actor, member, [], request.POST.get("reason", ""))
                messages.success(request, f"{member.short_name} no longer has access.")
                return redirect("member_detail", pk=member.pk)
        elif action == "reopen" and actor.may("assign_groups"):
            set_access(actor, member, ["member"], "reopened")
            messages.success(request, f"{member.short_name} is a member again.")
            return redirect("member_detail", pk=member.pk)
        elif action == "archive" and actor.may("archive_members"):  # FR-125
            from .services import ArchiveRefused, archive_member

            if member == actor:
                messages.error(request, "You cannot archive your own account.")
                return redirect("member_detail", pk=member.pk)
            try:
                archive_member(actor, member, request.POST.get("reason", ""))
            except ArchiveRefused as exc:
                messages.error(request, f"Not archived: {exc}.")
            else:
                messages.success(
                    request,
                    f"{member.short_name} is in the archive. Nothing of theirs was deleted, and "
                    "an advisor can bring them back.",
                )
            return redirect("member_detail", pk=member.pk)
        elif action == "restore" and actor.may("archive_members"):
            from .services import restore_member

            restore_member(actor, member)
            messages.success(request, f"{member.short_name} is a member again.")
            return redirect("member_detail", pk=member.pk)
        elif action == "admit" and member.is_provisional:  # FR-121: any officer reviews
            entry.admit(actor, member)
            messages.success(request, f"{member.short_name} is now a member.")
            return redirect("member_detail", pk=member.pk)
        elif action == "decline" and member.is_provisional:
            entry.decline(actor, member, request.POST.get("reason", "").strip()[:300])
            messages.success(request, f"{member.short_name} declined.")
            return redirect("member_detail", pk=member.pk)
        elif action == "mark_verified":  # FR-120: the officer's waiver
            entry.mark_verified(actor, member)
            messages.success(request, "Address marked verified.")
            return redirect("member_detail", pk=member.pk)
        else:
            raise Http404

    from apps.credentials.services import ladder

    ctx_ladder = ladder()
    return render(
        request,
        "accounts/member_detail.html",
        {
            "member": member,
            "form": form,
            "ladder": ctx_ladder,
            "readonly_rows": readonly_rows(actor, member, skip=("first_name",)),
            "manage_heading": "Manage" if actor.may("edit_member_privileges") else "Club position",
            "addresses": __import__("apps.accounts.addresses", fromlist=["state"]).state(member),
            "address_subject_is_self": member == actor,
            "deletion": __import__(
                "apps.accounts.services", fromlist=["deletion_effects"]
            ).deletion_effects(member)
            if actor.may("delete_accounts")
            else None,
            "can_revoke": __import__(
                "apps.credentials.views", fromlist=["_is_approver"]
            )._is_approver(actor),
            "temp_password": temp_password,
            "standing": _standing(member),
            "guardian_links": list(
                member.guardianships.select_related("guardian").order_by("-active", "created")
            ),
            "wards": list(member.wards.filter(active=True).select_related("minor")),
            "is_approver": _is_approver(actor),
            "can_convert": actor.may("convert_minor_accounts"),
            "is_self": member == actor,
        },
    )


@login_required
def hours(request):
    """FR-124: credited hours per member for one entry-link label (a course), with CSV."""
    if not request.user.may("view_reports"):
        raise Http404
    from django.http import HttpResponse

    from apps.events.services.hours import course_report

    from .models import EntryLink

    labels = list(EntryLink.objects.order_by("label").values_list("label", flat=True).distinct())
    label = request.GET.get("course", "") or (labels[0] if labels else "")
    report = course_report(label) if label else {"label": "", "rows": [], "totals": []}
    if request.GET.get("format") == "csv" and label:
        import csv

        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="hours-{label}.csv"'.replace(" ", "_")
        w = csv.writer(resp)
        w.writerow(
            [
                "Last name",
                "First name",
                "Callsign",
                "Email",
                "Event",
                "Slot start (UTC)",
                "Slot end (UTC)",
                "Checked in (UTC)",
                "No-show",
                "Credited hours",
            ]
        )
        for r in report["rows"]:
            su = r["signup"]
            w.writerow(
                [
                    su.user.last_name,
                    su.user.first_name,
                    su.user.callsign,
                    su.user.email,
                    su.slot.event.title,
                    su.slot.start.strftime("%Y-%m-%d %H:%M"),
                    su.slot.end.strftime("%Y-%m-%d %H:%M"),
                    su.checked_in_at.strftime("%Y-%m-%d %H:%M") if su.checked_in_at else "",
                    "yes" if su.no_show else "",
                    r["hours"],
                ]
            )
        w.writerow([])
        for u, total in report["totals"]:
            w.writerow(
                [
                    u.last_name,
                    u.first_name,
                    u.callsign,
                    u.email,
                    "TOTAL",
                    "",
                    "",
                    "",
                    "",
                    round(total, 2),
                ]
            )
        return resp
    return render(
        request, "accounts/hours.html", {"labels": labels, "label": label, "report": report}
    )
