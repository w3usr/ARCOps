"""Agreements: sign in one workflow (FR-22), approve (FR-25), view the computer password (FR-33)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ops.audit import record
from apps.ops.config import setting

from .models import AgreementTemplate, SignedAgreement
from .services import approve, holds, reveal_shared_secret


def _is_approver(user) -> bool:
    positions = setting("club_positions", []) or []
    approver_keys = {p["key"] for p in positions if p.get("approver")}
    return user.is_sysadmin or user.club_position in approver_keys


def _applicable_templates(user):
    return [
        t
        for t in AgreementTemplate.objects.filter(is_current=True)
        if user.category in (t.audience or [])
    ]


@login_required
def agreements(request):
    if not request.user.is_member:
        raise Http404  # FR-121: Provisional members neither see nor sign agreements
    if request.user.under_18:
        return render(request, "credentials/minor.html")  # minors do not sign (FR-22)
    templates = _applicable_templates(request.user)
    mine = {
        a.template_id: a
        for a in SignedAgreement.objects.filter(user=request.user).order_by("signed_at")
    }
    rows = [(t, mine.get(t.pk)) for t in templates]
    return render(request, "credentials/agreements.html", {"rows": rows})


@login_required
@require_POST
def sign(request, template_id):
    if not request.user.is_member:
        raise Http404
    if request.user.under_18:
        raise Http404
    t = get_object_or_404(AgreementTemplate, pk=template_id, is_current=True)
    if request.user.category not in (t.audience or []):
        raise Http404
    if (
        request.POST.get("affirm") != "on"
        or request.POST.get("signer_name", "").strip().lower() != request.user.full_name.lower()
    ):
        messages.error(request, "Type your full name exactly and tick the affirmation to sign.")
        return redirect("agreements")
    a = SignedAgreement.objects.create(
        user=request.user,
        template=t,
        credential=t.credential,
        signer_name=request.POST["signer_name"].strip(),
        signer_ip=request.META.get("REMOTE_ADDR"),
        content_hash=t.content_hash,
    )
    record(request.user, "agreement.signed", a, after={"template": t.key, "version": t.version})
    messages.success(request, f"Signed: {t.title}. It now awaits approval.")
    return redirect("agreements")


@login_required
def approvals(request):
    if not _is_approver(request.user):
        raise Http404
    queue = SignedAgreement.objects.filter(state=SignedAgreement.State.SIGNED).select_related(
        "user", "template", "credential"
    )
    return render(request, "credentials/approvals.html", {"queue": queue})


@login_required
@require_POST
def decide(request, pk):
    if not _is_approver(request.user):
        raise Http404
    a = get_object_or_404(SignedAgreement, pk=pk, state=SignedAgreement.State.SIGNED)
    if request.POST.get("decision") == "approve":
        if a.user.category == "community" and a.credential.key == "station_access":
            # FR-27: the institution's address is the evidence HR is done
            addr = (
                (request.POST.get("institution_email") or a.user.institution_email or "")
                .strip()
                .lower()
            )
            domain = next(
                (
                    c.get("email_domain")
                    for c in setting("member_categories", []) or []
                    if c["key"] == "student"
                ),
                None,
            )
            if not addr or (domain and not addr.endswith("@" + domain)):
                messages.error(
                    request,
                    "A community member needs an institution email address on file before approval.",
                )
                return redirect("approvals")
            if addr != a.user.institution_email:
                a.user.institution_email = addr
                a.user.save(update_fields=["institution_email"])
        approve(request.user, a)
        messages.success(request, f"Approved; expires {a.expires_on:%d %B %Y}.")
    else:
        a.state = SignedAgreement.State.DECLINED
        a.decision_reason = request.POST.get("reason", "")
        a.approver = request.user
        a.approved_at = timezone.now()
        a.save()
        record(request.user, "agreement.declined", a, after={"reason": a.decision_reason})
        messages.info(request, "Declined.")
    return redirect("approvals")


@login_required
def computer_password(request):
    today = timezone.now().date()
    if request.user.under_18 or not holds(request.user, "it_access", today):
        return render(request, "credentials/password_denied.html", status=403)
    secret = None
    if request.method == "POST" and request.user.check_password(request.POST.get("password", "")):
        try:
            secret = reveal_shared_secret(request.user)
        except RuntimeError:
            messages.error(request, "The encryption key is not configured on this server.")
    elif request.method == "POST":
        messages.error(request, "That password did not match.")
    return render(request, "credentials/password.html", {"secret": secret})
