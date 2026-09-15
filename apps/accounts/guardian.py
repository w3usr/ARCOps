"""
Guardians and minors (REQUIREMENTS §2.4, FR-10, FR-109).

A guardian *acts for* a linked minor: the session carries the minor's id, the middleware renders
every request as the minor with the guardian remembered on the user object, and the audit log
names both. A minor's own sign-in is read-only: every state-changing request is refused except
changing their own password, signing out, and marking messages read. Conversion at 18 ends the
links and hands the account to the member.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ops.audit import record

from .models import Guardianship, User

SESSION_KEY = "acting_for_minor_id"
STOP_PATH = "/me/act/stop/"
MINOR_MAY_POST = ("/accounts/password/change/", "/accounts/logout/", "/me/messages/", STOP_PATH)


def wards_of(user) -> list[User]:
    if not getattr(user, "is_authenticated", False):
        return []
    return [
        g.minor
        for g in user.wards.filter(active=True)
        .select_related("minor")
        .order_by("minor__first_name")
    ]


def guardians_of(minor, active_only: bool = True):
    qs = minor.guardianships.select_related("guardian").order_by("-active", "created")
    return qs.filter(active=True) if active_only else qs


class ActingForMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        request.acting_guardian = None
        if user is not None and user.is_authenticated:
            minor_id = request.session.get(SESSION_KEY)
            if minor_id:
                link = (
                    Guardianship.objects.filter(minor_id=minor_id, guardian=user, active=True)
                    .select_related("minor")
                    .first()
                )
                if link is None:
                    request.session.pop(SESSION_KEY, None)
                else:
                    minor = link.minor
                    minor.acting_guardian = user
                    request.acting_guardian = user
                    request.user = minor
                    user = minor
            if user.under_18 and getattr(user, "acting_guardian", None) is None:
                if request.method not in ("GET", "HEAD", "OPTIONS") and not request.path.startswith(
                    MINOR_MAY_POST
                ):
                    return HttpResponseForbidden(
                        "A member under 18 signs in read-only; a guardian acts for them (REQUIREMENTS §2.4). Ask your guardian to do this from their account."
                    )
        return self.get_response(request)


def context(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    acting = getattr(request, "acting_guardian", None)
    return {
        "acting_guardian": acting,
        "minor_readonly": bool(user.under_18 and acting is None),
        "my_wards": wards_of(acting or user) if not user.under_18 or acting else [],
    }


@login_required
@require_POST
def act_start(request, pk):
    real = getattr(request, "acting_guardian", None) or request.user
    link = (
        Guardianship.objects.filter(minor_id=pk, guardian=real, active=True)
        .select_related("minor")
        .first()
    )
    if link is None:
        raise Http404
    request.session[SESSION_KEY] = link.minor.pk
    record(real, "guardian.acting_started", link.minor)
    messages.info(
        request,
        f"You are acting for {link.minor.display_first}. Everything you do now is on their behalf.",
    )
    return redirect(request.POST.get("next") or "dashboard")


@login_required
@require_POST
def act_stop(request):
    real = getattr(request, "acting_guardian", None) or request.user
    minor_id = request.session.pop(SESSION_KEY, None)
    if minor_id:
        record(real, "guardian.acting_stopped", User.objects.filter(pk=minor_id).first())
    return redirect("dashboard")


@login_required
@require_POST
def ward_password(request, pk):
    """§2.4: the guardian resets the minor's password from their own account, as FR-7."""
    from .services import issue_temporary_password

    real = getattr(request, "acting_guardian", None) or request.user
    link = (
        Guardianship.objects.filter(minor_id=pk, guardian=real, active=True)
        .select_related("minor")
        .first()
    )
    if link is None:
        raise Http404
    password = issue_temporary_password(real, link.minor)
    return render(
        request, "accounts/ward_password.html", {"minor": link.minor, "password": password}
    )


# ------------------------------------------------------------------------------- services ---


def sign_in_address(guardian: User, first_name: str) -> str:
    """§2.4: a minor with no address signs in with a plus-address made from the guardian's
    (`parent+kim@example.org`): unique, never the guardian's own, and delivered to the guardian
    by most providers if anyone ever writes to it. Marked sign-in-only, it is never messaged."""
    import re

    local, _, domain = guardian.email.partition("@")
    local = local.split("+")[0]
    slug = re.sub(r"[^a-z0-9]", "", first_name.lower()) or "member"
    addr, n = f"{local}+{slug}@{domain}", 2
    while User.objects.filter(email=addr).exists():
        addr, n = f"{local}+{slug}{n}@{domain}", n + 1
    return addr


@login_required
@require_POST
def ward_email(request, pk):
    """The guardian gives the minor their own address once they have one; messages then reach
    it too (FR-70)."""
    real = getattr(request, "acting_guardian", None) or request.user
    link = (
        Guardianship.objects.filter(minor_id=pk, guardian=real, active=True)
        .select_related("minor")
        .first()
    )
    if link is None:
        raise Http404
    addr = request.POST.get("email", "").strip().lower()
    if not addr or "@" not in addr:
        messages.error(request, "Enter an email address.")
    elif addr == real.email or User.objects.filter(email=addr).exclude(pk=link.minor.pk).exists():
        messages.error(request, "That address belongs to another account.")
    else:
        before = link.minor.email
        link.minor.email, link.minor.sign_in_only_address = addr, False
        link.minor.save(update_fields=["email", "sign_in_only_address"])
        record(
            real,
            "account.email_changed",
            link.minor,
            before={"email": before},
            after={"email": addr},
        )
        messages.success(
            request,
            f"{link.minor.display_first} now signs in with {addr} and receives messages there as well as through you.",
        )
    return redirect("profile")


def link_guardian(actor, minor: User, guardian: User, relationship: str = "") -> Guardianship:
    link, created = Guardianship.objects.get_or_create(
        minor=minor, guardian=guardian, defaults={"relationship": relationship}
    )
    if not created and not link.active:
        link.active, link.ended, link.relationship = True, None, relationship or link.relationship
        link.save(update_fields=["active", "ended", "relationship"])
    record(
        actor,
        "guardian.linked",
        minor,
        after={"guardian": guardian.pk, "relationship": relationship},
    )
    return link


def unlink_guardian(actor, link: Guardianship) -> None:
    link.active, link.ended = False, timezone.now()
    link.save(update_fields=["active", "ended"])
    record(actor, "guardian.unlinked", link.minor, after={"guardian": link.guardian_id})


def convert_to_adult(actor, user: User) -> str:
    """FR-109: clear the flag, end every link (kept), issue a one-time temporary password, tell
    the guardians and the member. Returns the password, shown once to the approver."""
    from apps.comms.services import send

    from .services import issue_temporary_password

    guardians = [g.guardian for g in guardians_of(user)]
    user.guardianships.filter(active=True).update(active=False, ended=timezone.now())
    user.under_18 = False
    user.save(update_fields=["under_18"])
    password = issue_temporary_password(actor, user)
    record(
        actor,
        "account.converted_to_adult",
        user,
        after={"guardians_ended": [g.pk for g in guardians]},
    )
    for g in guardians:
        send("guardian.converted", g, "account", {"minor": user})
    send("account.converted", user, "account", {"advisor": actor})
    return password
