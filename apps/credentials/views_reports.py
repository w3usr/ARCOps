"""Officer and sysadmin pages for credentials: the shared password (FR-32, FR-34), access
rosters (FR-31, FR-84), signed-agreement PDFs (FR-23), and revocation (FR-29)."""

from __future__ import annotations

import csv
import datetime as dt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.accounts.models import AccessLevel, User
from apps.ops.audit import record

from .models import CredentialType, SharedSecret, SignedAgreement
from .services import revoke, rotate_shared_secret, store_agreement_pdf
from .views import _is_approver


@login_required
def password_manage(request):
    """FR-32: set or rotate the shared computer password from a page, sysadmins only."""
    if not request.user.is_sysadmin:
        raise Http404
    current = SharedSecret.objects.filter(name="computer_account").first()
    if request.method == "POST":
        pw = request.POST.get("password", "")
        confirm = request.POST.get("password2", "")
        eff = parse_date(request.POST.get("effective_date", "") or "") or timezone.now().date()
        if len(pw) < 8 or pw != confirm:
            messages.error(request, "Type the new password twice, at least eight characters.")
        else:
            try:
                result = rotate_shared_secret(request.user, pw, eff)
            except RuntimeError as exc:
                messages.error(request, str(exc))
                return redirect("password_manage")
            messages.success(
                request,
                f"Password set, effective {eff:%d %B %Y}. {result['notified']} member(s) with current computer access told; "
                f"{len(result['former'])} former viewer(s) without access listed in your messages.",
            )
            return redirect("password_manage")
    return render(request, "credentials/password_manage.html", {"current": current})


@login_required
def access_rosters(request):
    """FR-31, FR-84: who holds station and computer access, with expiry; filterable; CSV."""
    if not request.user.is_officer:
        raise Http404
    today = timezone.now().date()
    within = request.GET.get("expiring", "")
    qs = (
        SignedAgreement.objects.filter(state=SignedAgreement.State.APPROVED)
        .select_related("user", "credential", "approver", "template")
        .order_by("credential__label", "expires_on", "user__last_name")
    )
    if within.isdigit():
        qs = qs.filter(expires_on__lte=today + dt.timedelta(days=int(within)))
    rows = [
        {
            "a": a,
            "days": (a.expires_on - today).days if a.expires_on else None,
        }
        for a in qs
    ]
    if request.GET.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="access-rosters.csv"'
        w = csv.writer(resp)
        w.writerow(
            [
                "credential",
                "last_name",
                "first_name",
                "callsign",
                "category",
                "approved_on",
                "approver",
                "expires_on",
                "days_remaining",
            ]
        )
        for r in rows:
            a = r["a"]
            w.writerow(
                [
                    a.credential.label,
                    a.user.last_name,
                    a.user.first_name,
                    a.user.callsign,
                    a.user.category,
                    a.approved_at.date().isoformat() if a.approved_at else "",
                    a.approver.full_name if a.approver else "",
                    a.expires_on.isoformat() if a.expires_on else "",
                    r["days"],
                ]
            )
        record(request.user, "report.access_rosters_exported", after={"rows": len(rows)})
        return resp
    return render(
        request,
        "credentials/access_rosters.html",
        {
            "rows": rows,
            "within": within,
            "credentials": CredentialType.objects.filter(established_by="agreement").order_by(
                "label"
            ),
            "today": today,
        },
    )


@login_required
def agreement_pdf(request, pk):
    """FR-23: the signer and the approvers can download the signed agreement as a tagged PDF."""
    a = get_object_or_404(SignedAgreement, pk=pk)
    if a.user != request.user and not _is_approver(request.user):
        raise Http404
    if not a.pdf:
        store_agreement_pdf(a)
        a.refresh_from_db()
    record(request.user, "agreement.pdf_downloaded", a)
    return FileResponse(
        a.pdf.open("rb"),
        content_type="application/pdf",
        as_attachment=True,
        filename=a.pdf.name.rsplit("/", 1)[-1],
    )


@login_required
@require_POST
def agreement_revoke(request, pk):
    """FR-29: an approver revokes an approval with a reason."""
    if not _is_approver(request.user):
        raise Http404
    a = get_object_or_404(SignedAgreement, pk=pk, state=SignedAgreement.State.APPROVED)
    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "A revocation needs a reason; the member is told it.")
    else:
        revoke(request.user, a, reason[:500])
        messages.success(request, f"Revoked; {a.user.short_name} has been told.")
    return redirect(request.POST.get("next") or "access_rosters")


def _member_roster_rows(users):
    today = timezone.now().date()
    approved = SignedAgreement.objects.filter(
        state=SignedAgreement.State.APPROVED, user__in=users
    ).select_related("credential")
    creds: dict[int, list[str]] = {}
    for a in approved:
        creds.setdefault(a.user_id, []).append(
            f"{a.credential.label} to {a.expires_on:%Y-%m-%d}"
            if a.expires_on
            else a.credential.label
        )
    rows = []
    for u in users:
        lic = getattr(u, "license", None)
        rows.append(
            {
                "u": u,
                "credentials": creds.get(u.pk, []),
                "lic": lic,
                "graduated": _graduation_passed(u, today),
            }
        )
    return rows


def _graduation_passed(u, today) -> bool:
    if u.category != "student" or not u.graduation_year:
        return False
    sem_end = {"spring": (5, 31), "summer": (8, 15), "fall": (12, 31)}.get(
        (u.graduation_semester or "spring").lower(), (5, 31)
    )
    return dt.date(int(u.graduation_year), *sem_end) < today


@login_required
def member_roster(request):
    """FR-87: the officers' roster with credentials, graduation, and last sign-in; the past-
    graduation filter; contact details only through the separate, audited export."""
    if not request.user.is_officer:
        raise Http404
    users = (
        User.objects.exclude(access_level=AccessLevel.NONE)
        .select_related("license", "joined_via")
        .order_by("last_name", "first_name")
    )
    rows = _member_roster_rows(list(users))
    if request.GET.get("graduated") == "1":
        rows = [r for r in rows if r["graduated"]]
    if request.GET.get("format") == "csv":
        contacts = request.GET.get("contacts") == "1"
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = (
            f'attachment; filename="members{"-contacts" if contacts else ""}.csv"'
        )
        w = csv.writer(resp)
        head = [
            "last_name",
            "first_name",
            "callsign",
            "class",
            "license_expires",
            "category",
            "position",
            "student_level",
            "graduation",
            "access_level",
            "credentials",
            "last_sign_in",
        ]
        if contacts:
            head += ["email", "institution_email", "personal_email", "cell_phone"]
        w.writerow(head)
        for r in rows:
            u, lic = r["u"], r["lic"]
            line = [
                u.last_name,
                u.first_name,
                u.callsign,
                lic.effective_class if lic else "",
                lic.effective_expiry.isoformat() if lic and lic.effective_expiry else "",
                u.category,
                u.club_position,
                u.student_level or "",
                f"{u.graduation_semester or ''} {u.graduation_year or ''}".strip(),
                u.access_level,
                "; ".join(r["credentials"]),
                u.last_login.isoformat() if u.last_login else "",
            ]
            if contacts:
                line += [u.email, u.institution_email, u.personal_email, u.cell_phone]
            w.writerow(line)
        record(
            request.user,
            "report.member_roster_exported",
            after={"rows": len(rows), "contacts": contacts},
        )
        return resp
    return render(
        request,
        "accounts/roster.html",
        {"rows": rows, "graduated": request.GET.get("graduated") == "1"},
    )
