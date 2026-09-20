"""Officer and sysadmin pages for credentials: the shared password (FR-32, FR-34), access
rosters (FR-31, FR-84), signed-agreement PDFs (FR-23), and revocation (FR-29)."""

from __future__ import annotations

import csv
import datetime as dt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.ops.audit import record
from apps.ops.config import setting
from apps.ops.tables import chosen, export_url, sorted_columns, summary

from .models import CredentialType, SharedSecret, SignedAgreement
from .services import revoke, rotate_shared_secret, store_agreement_pdf
from .views import _is_approver


@login_required
def password_manage(request):
    """FR-32: set or rotate the shared computer password from a page."""
    if not request.user.may("rotate_shared_secret"):
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


# Who holds access, one row per approved agreement. Every column sorts and every column
# narrows, in the words the members directory uses, because a reader who has learned one table
# has learned this one (the advisor, 2026-09-20, issue #92).
ROSTER_COLUMNS = [
    {"key": "credential", "label": "Credential"},
    {"key": "first", "label": "First"},
    {"key": "last", "label": "Last"},
    {"key": "callsign", "label": "Callsign"},
    {"key": "category", "label": "Category"},
    {"key": "approved", "label": "Approved"},
    {"key": "approver", "label": "Approver"},
    {"key": "expires", "label": "Expires"},
    {"key": "days", "label": "Days"},
]

# How long until expiry, in the buckets the panel offers. Ticking none is every row.
EXPIRY_BUCKETS = [
    ("30", "Within 30 days"),
    ("60", "31 to 60 days"),
    ("90", "61 to 90 days"),
    ("later", "More than 90 days"),
    ("none", "No expiry date"),
]


def _bucket(days: int | None) -> str:
    if days is None:
        return "none"
    if days <= 30:
        return "30"
    if days <= 60:
        return "60"
    if days <= 90:
        return "90"
    return "later"


@login_required
def access_rosters(request):
    """FR-31, FR-84: who holds station and computer access, with expiry; sortable, filterable, CSV."""
    if not request.user.may("view_reports"):
        raise Http404
    today = timezone.now().date()
    q = request.GET.get("q", "").strip()
    picked = chosen(request, "credential", "category", "approver", "expiring")

    qs = SignedAgreement.objects.filter(state=SignedAgreement.State.APPROVED).select_related(
        "user", "credential", "approver", "template"
    )
    if q:
        qs = qs.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__preferred_name__icontains=q)
            | Q(user__callsign__icontains=q)
        ).distinct()
    if picked["credential"]:
        qs = qs.filter(credential__key__in=picked["credential"])
    if picked["category"]:
        qs = qs.filter(user__category__in=picked["category"])
    if picked["approver"]:
        qs = qs.filter(approver__public_id__in=picked["approver"])

    rows = [{"a": a, "days": (a.expires_on - today).days if a.expires_on else None} for a in qs]
    wanted = set(picked["expiring"])
    if wanted:
        rows = [r for r in rows if _bucket(r["days"]) in wanted]

    def text(value) -> str:
        return (value or "").strip().lower()

    def settled(fn):
        # Every sort ends the same way, so reversing a column truly reverses the page.
        return lambda r: (
            *fn(r),
            text(r["a"].user.last_name),
            text(r["a"].user.first_name),
            r["a"].pk,
        )

    keys = {
        "credential": settled(lambda r: (text(r["a"].credential.label),)),
        "first": settled(lambda r: (text(r["a"].user.first_name),)),
        "last": settled(lambda r: (text(r["a"].user.last_name),)),
        "callsign": settled(lambda r: (not r["a"].user.callsign, text(r["a"].user.callsign))),
        "category": settled(lambda r: (text(r["a"].user.category),)),
        "approved": settled(
            lambda r: (r["a"].approved_at is None, r["a"].approved_at or dt.datetime.min)
        ),
        "approver": settled(
            lambda r: (text(r["a"].approver.last_name if r["a"].approver else ""),)
        ),
        "expires": settled(lambda r: (r["a"].expires_on is None, r["a"].expires_on or dt.date.max)),
        "days": settled(lambda r: (r["days"] is None, r["days"] if r["days"] is not None else 0)),
    }
    sort, descending, columns = sorted_columns(request, ROSTER_COLUMNS, keys, "last")
    rows.sort(key=keys[sort], reverse=descending)

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
        # The export is what is on the screen: it follows the search, every filter and the sort.
        record(
            request.user,
            "report.access_rosters_exported",
            after={"rows": len(rows), "narrowed": bool(q or any(picked.values()))},
        )
        return resp

    credential_choices = [
        (c.key, c.label)
        for c in CredentialType.objects.filter(established_by="agreement").order_by("label")
    ]
    category_choices = [
        (c["key"], c.get("label", c["key"])) for c in (setting("member_categories", []) or [])
    ]
    approver_choices = sorted(
        {(str(a.approver.public_id), a.approver.short_name) for a in qs if a.approver},
        key=lambda pair: pair[1].lower(),
    )
    return render(
        request,
        "credentials/access_rosters.html",
        {
            "rows": rows,
            "today": today,
            "q": q,
            "chosen": picked,
            "columns": columns,
            "sort": sort,
            "dir": "desc" if descending else "asc",
            "credential_choices": credential_choices,
            "category_choices": category_choices,
            "approver_choices": approver_choices,
            "expiry_choices": EXPIRY_BUCKETS,
            "summaries": {
                "credential": summary(credential_choices, picked["credential"], "credential"),
                "category": summary(category_choices, picked["category"], "category"),
                "approver": summary(approver_choices, picked["approver"], "approver"),
                "expiring": summary(EXPIRY_BUCKETS, picked["expiring"], "expiry"),
            },
            "narrowed": bool(q or any(picked.values())),
            "csv_url": export_url(request),
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
    if not request.user.may("view_reports"):
        raise Http404
    users = (
        User.objects.with_access()
        .select_related("license", "joined_via")
        .prefetch_related("addresses")
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
            "positions",
            "student_level",
            "graduation",
            "access",
            "credentials",
            "last_sign_in",
        ]
        if contacts:
            head += ["addresses", "cell_phone"]
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
                "; ".join(u.club_positions or []),
                u.student_level or "",
                f"{u.graduation_semester or ''} {u.graduation_year or ''}".strip(),
                ", ".join(g.name for g in u.groups.all()) or "none",
                "; ".join(r["credentials"]),
                u.last_login.isoformat() if u.last_login else "",
            ]
            if contacts:
                line += [
                    " ".join(a.address for a in u.addresses.all()),
                    u.cell_phone,
                ]
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
