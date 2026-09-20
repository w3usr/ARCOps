"""Agreements: sign in one workflow (FR-22), approve (FR-25), view the computer password (FR-33)."""

import datetime as dt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from apps.accounts.reauth import is_confirmed, spend
from apps.ops.audit import record
from apps.ops.config import setting
from apps.ops.tables import chosen, export_url, sorted_columns, summary

from .models import AgreementTemplate, CredentialDecision, CredentialType, SignedAgreement
from .services import approve, holds, log_decision, reveal_shared_secret

# How long a decline can still be turned round from the log. Past it, the member signs again;
# a decision nobody corrected within a month was a decision rather than a slip.
DECLINED_WINDOW_DAYS = 30

# The record of what has been decided, under the queue. Every column sorts and every column
# narrows, in the words the members directory uses (NAF, 2026-09-20: "I think we need a
# searchable, filterable, sortable log on this page of what approval actions have been taken").
DECISION_COLUMNS = [
    {"key": "at", "label": "When"},
    {"key": "member", "label": "Member"},
    {"key": "callsign", "label": "Callsign"},
    {"key": "agreement", "label": "Agreement"},
    {"key": "action", "label": "Action"},
    {"key": "by", "label": "By"},
]


def _is_approver(user) -> bool:
    """Who may approve access to the station: a faculty advisor or a sysadmin.

    This used to be a flag on the club position, so an elected officer holding a marked position
    could approve. The advisor asked on 2026-09-17 for it to follow the access level instead:
    "Faculty Advisors should have the ability to approve access agreements. Club officers should
    not." Station access is the club's answer to the University, so it belongs to the level the
    University appoints, not to a position the club votes on."""
    return user.may("approve_agreements")


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
    notice_days = int(setting("defaults.agreement_expiry_notice_days", 30))
    today = timezone.now().date()
    # the member's latest signature per agreement key, whichever version it was on
    latest = {}
    for a in (
        SignedAgreement.objects.filter(user=request.user)
        .select_related("template")
        .order_by("signed_at")
    ):
        if a.template:
            latest[a.template.key] = a
    rows = []
    for t in templates:
        a = mine.get(t.pk) or latest.get(t.key)
        if a is not None:
            a.expiring_soon = bool(
                a.state == SignedAgreement.State.APPROVED
                and a.expires_on
                and (a.expires_on - today).days <= notice_days
            )
        rows.append((t, a))
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
    try:
        from .services import store_agreement_pdf

        store_agreement_pdf(a)  # FR-23: the text as signed, kept immutably
    except Exception:  # noqa: BLE001 - the signature stands even if the renderer is unavailable
        import logging

        logging.getLogger(__name__).exception("agreement PDF not rendered for %s", a.pk)
    from django.conf import settings as dj

    from apps.comms.services import send

    from .services import approvers

    link = (getattr(dj, "SITE_URL", "") or "") + reverse("approvals")
    for ap in approvers():
        send(
            "agreement.submitted",
            ap,
            "agreement",
            {"person": request.user, "title": t.title, "link": link},
        )
    messages.success(request, f"Signed: {t.title}. It now awaits approval.")
    return redirect("agreements")


# Which credentials may not be approved without an institution address on the account. Station
# and computer access both open a real door, and an address at the institution's own domain is
# the evidence that somebody has been through the institution's own checks.
#
# The advisor, 2026-09-20, having approved station access for somebody holding no institution
# address and finding that he could: the workflow should require one first, for the computer
# agreement as well as the station one, so that everybody granted real access has been through
# the institution's own checks or is at least in its directory.
#
# It was asked of a community member's station access alone (FR-27), which let everybody else
# through: a student or a faculty member with only a personal address was approved without one.


def institution_domains() -> list[str]:
    """The domains that count as the institution's own, from the club's configuration."""
    domains = [
        str(d).strip().lower().lstrip("@") for d in (setting("trusted_email_domains", []) or [])
    ]
    if domains:
        return [d for d in domains if d]
    # Older configurations carried it on the student category instead.
    for c in setting("member_categories", []) or []:
        if c.get("key") == "student" and c.get("email_domain"):
            return [str(c["email_domain"]).strip().lower().lstrip("@")]
    return []


def needs_institution_email(agreement) -> bool:
    """Whether this credential may not be granted without one."""
    wanted = setting("credentials_needing_institution_email", ["station_access", "it_access"]) or []
    return agreement.credential.key in set(wanted) and bool(institution_domains())


def institution_address_ok(address: str) -> bool:
    address = (address or "").strip().lower()
    return any(address.endswith("@" + d) for d in institution_domains())


@login_required
def approvals(request):
    if not _is_approver(request.user):
        raise Http404
    queue = SignedAgreement.objects.filter(state=SignedAgreement.State.SIGNED).select_related(
        "user", "template", "credential"
    )
    # the institution address is a row on the account now, so the page is handed it per agreement
    rows = [
        {
            "a": a,
            "institution_address": _institution_address(a.user),
            "needs_institution": needs_institution_email(a)
            and not institution_address_ok(_institution_address(a.user, confirmed_only=True)),
        }
        for a in queue
    ]
    if request.GET.get("format") == "csv" and request.GET.get("report") == "decisions":
        return _decisions_csv(request)
    return render(
        request,
        "credentials/approvals.html",
        {"queue": rows, **_decision_log(request)},
    )


def _decisions_csv(request):
    """The log as a file: the search, both filters and the sort, the same as the screen."""
    import csv

    from django.http import HttpResponse

    context = _decision_log(request)
    rows = context["log"].paginator.object_list
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="access-decisions.csv"'
    w = csv.writer(resp)
    w.writerow(
        [
            "when_utc",
            "last_name",
            "first_name",
            "callsign",
            "agreement",
            "action",
            "by",
            "expires_on",
            "note",
        ]
    )
    for d in rows:
        a = d.agreement
        w.writerow(
            [
                d.at.strftime("%Y-%m-%d %H:%M"),
                a.user.last_name,
                a.user.first_name,
                a.user.callsign,
                a.template.title if a.template else a.credential.label,
                d.get_action_display(),
                d.actor_label,
                d.expires_on.isoformat() if d.expires_on else "",
                d.note,
            ]
        )
    record(
        request.user,
        "report.decisions_exported",
        after={"rows": len(rows), "narrowed": context["log_narrowed"]},
    )
    return resp


def _decision_log(request) -> dict:
    """The log under the queue: what has been decided, searchable, filterable, sortable.

    It is the approver's own record of their own work, which is why it lives on their page and
    not in the admin behind `view_audit_log` (§2.1). The rows come from `CredentialDecision`,
    which keeps every decision rather than only the latest, so a decline and the approval that
    corrected it are both here, in order.
    """
    q = request.GET.get("q", "").strip()
    picked = chosen(request, "action", "credential")

    qs = CredentialDecision.objects.select_related(
        "agreement__user", "agreement__credential", "agreement__template", "actor"
    )
    if q:
        qs = qs.filter(
            Q(agreement__user__first_name__icontains=q)
            | Q(agreement__user__last_name__icontains=q)
            | Q(agreement__user__preferred_name__icontains=q)
            | Q(agreement__user__callsign__icontains=q)
            | Q(agreement__template__title__icontains=q)
            | Q(agreement__credential__label__icontains=q)
        ).distinct()
    if picked["action"]:
        qs = qs.filter(action__in=picked["action"])
    if picked["credential"]:
        qs = qs.filter(agreement__credential__key__in=picked["credential"])

    order = {
        "at": "at",
        "member": "agreement__user__last_name",
        "callsign": "agreement__user__callsign",
        "agreement": "agreement__credential__label",
        "action": "action",
        "by": "actor_label",
    }
    sort, descending, columns = sorted_columns(request, DECISION_COLUMNS, order, "at")
    field = order[sort]
    # Every sort ends the same way, so reversing a column truly reverses the page.
    qs = qs.order_by(f"{'-' if descending else ''}{field}", "-at", "-pk")

    action_choices = list(CredentialDecision.Action.choices)
    credential_choices = [
        (c.key, c.label)
        for c in CredentialType.objects.filter(established_by="agreement").order_by("label")
    ]
    narrowed = bool(q or any(picked.values()))
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    # A decline is reversible from its own row, while it is still what stands and still recent.
    since = timezone.now() - dt.timedelta(days=DECLINED_WINDOW_DAYS)
    for d in page:
        d.reversible = (
            d.action == CredentialDecision.Action.DECLINED
            and d.agreement.state == SignedAgreement.State.DECLINED
            and d.at >= since
        )
        d.needs_institution = (
            d.reversible
            and needs_institution_email(d.agreement)
            and not (institution_address_ok(_institution_address(d.agreement.user)))
        )
    pager = request.GET.copy()
    pager.pop("page", None)
    return {
        "log": page,
        "log_q": q,
        "log_chosen": picked,
        "log_columns": columns,
        "log_sort": sort,
        "log_dir": "desc" if descending else "asc",
        "log_narrowed": narrowed,
        "log_pager": pager.urlencode(),
        "action_choices": action_choices,
        "log_credential_choices": credential_choices,
        "log_summaries": {
            "action": summary(action_choices, picked["action"], "action"),
            "credential": summary(credential_choices, picked["credential"], "credential"),
        },
        "log_csv_url": export_url(request, report="decisions"),
    }


@login_required
@require_POST
def decide(request, pk):
    if not _is_approver(request.user):
        raise Http404
    # A declined signature can still be approved: the decline may have been a slip, and making
    # the member sign again to undo somebody else's mistake is the wrong way round (FR-22).
    a = get_object_or_404(
        SignedAgreement,
        pk=pk,
        state__in=[SignedAgreement.State.SIGNED, SignedAgreement.State.DECLINED],
    )
    was_declined = a.state == SignedAgreement.State.DECLINED
    if was_declined and request.POST.get("decision") != "approve":
        messages.error(request, "That agreement is already declined.")
        return redirect("approvals")
    if request.POST.get("decision") == "approve":
        if needs_institution_email(a):
            # FR-27, tightened 2026-09-20. The evidence is a **confirmed** institution address,
            # and approving is not where an address gets confirmed: the advisor asked for the
            # standard to be confirmation, with a manual confirmation as the override. That
            # override already exists, on the member's own page, where "Confirm it myself" is
            # an officer's waiver that needs no mail (FR-126). Typing an address here used to
            # stand in for it, which meant one person's address could be evidence about
            # another, and meant nobody had ever stood behind the address at all.
            held = _institution_address(a.user, confirmed_only=True)
            if not institution_address_ok(held):
                domains = ", ".join(institution_domains())
                messages.error(
                    request,
                    format_html(
                        "{} has no confirmed {} address, so there is nothing to show they are "
                        "in the institution's directory. Add and confirm one on "
                        '<a href="{}">their page</a>, then approve this.',
                        a.user.display_first,
                        domains,
                        reverse("member_edit", args=[a.user.pk]),
                    ),
                )
                return redirect("approvals")
        if was_declined:
            # Reversing a decline says why, so the record tells a mis-click from a change of
            # mind. Both are legitimate; only one of them is an error, and a log that cannot
            # tell them apart is the thing that made the reversal feel unsafe (NAF, 2026-09-20).
            why = (request.POST.get("reversal_reason") or "").strip()
            if not why:
                messages.error(
                    request,
                    "Say why the decision is being reversed: a slip and a change of mind "
                    "read the same in the record otherwise.",
                )
                return redirect("approvals")
        else:
            why = ""
        a.decision_reason = ""  # the reason it was declined for no longer describes it
        approve(request.user, a, note=why)
        messages.success(
            request,
            ("Decision reversed. Approved, expires " if was_declined else "Approved; expires ")
            + f"{a.expires_on:%d %B %Y}.",
        )
    else:
        a.state = SignedAgreement.State.DECLINED
        a.decision_reason = request.POST.get("reason", "")
        a.approver = request.user
        a.approved_at = timezone.now()
        a.save()
        record(request.user, "agreement.declined", a, after={"reason": a.decision_reason})
        log_decision(a, CredentialDecision.Action.DECLINED, request.user, note=a.decision_reason)
        from django.conf import settings as dj

        from apps.comms.services import send

        send(
            "agreement.declined",
            a.user,
            "agreement",
            {
                "title": a.template.title,
                "reason": a.decision_reason,
                "link": (getattr(dj, "SITE_URL", "") or "") + reverse("agreements"),
            },
        )
        messages.info(request, "Declined.")
    return redirect("approvals")


@login_required
def computer_password(request):
    """FR-33: the shared password, behind Confirm Access, asked for every single time.

    This page used to ask for the account's own password in a box of its own, which took a
    password and nothing else while the rest of the site had moved on to passkeys (NAF,
    2026-09-20: "the new one for looking up the station password only accepts a password, no
    passkey"). It is the same Confirm Access the level step-up uses now, so there is one screen
    and one implementation; `apps.accounts.reauth` is what makes the proof good for this one
    view and no more, so a reload asks again.
    """
    today = timezone.now().date()
    if request.user.under_18 or not holds(request.user, "it_access", today):
        return render(request, "credentials/password_denied.html", status=403)
    if not is_confirmed(request):
        back = request.get_full_path()
        return redirect(f"{reverse('account_reauthenticate')}?{urlencode({'next': back})}")
    try:
        secret = reveal_shared_secret(request.user)
    except RuntimeError:
        messages.error(request, "The encryption key is not configured on this server.")
        secret = None
    if secret:
        spend(request)  # good for this view of it, not for the next
    return render(request, "credentials/password.html", {"secret": secret})


def _institution_address(user, *, confirmed_only: bool = False) -> str:
    """The institution address on the account, if there is one (FR-27).

    `confirmed_only` is what the credential gate asks for: an address nobody has stood behind
    is not evidence that anybody is in the institution's directory.
    """
    rows = user.addresses.filter(kind="institution")
    if confirmed_only:
        rows = rows.filter(confirmed=True)
    row = rows.first()
    return row.address if row else ""
