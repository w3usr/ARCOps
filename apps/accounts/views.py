"""Profile, invitations, and the invitation-accept (registration) flow."""

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.credentials.models import LicenseRecord
from apps.ops.audit import record
from apps.ops.config import setting

from .account import AccountForm, readonly_rows, save_account
from .models import AccessLevel, Invitation, User
from .services import (
    admit_from_invitation,
    create_invitation,
    invitation_text,
    reissue_invitation,
    revoke_invitation,
)


@login_required
def profile(request):
    """A member's own account: the same fields and the same save path an officer's view of them
    uses (apps.accounts.account), plus what is theirs alone: notifications, browser
    notifications, security, closing the account."""
    if request.method == "POST":
        form = AccountForm(request.POST, instance=request.user, actor=request.user)
        if form.is_valid():
            result = save_account(form, request.user, f"{request.scheme}://{request.get_host()}")
            call = result["callsign"]
            if call and call["state"] == "pending":
                messages.warning(
                    request,
                    f"The FCC lists {request.user.callsign} under the name {call['uls_name']}. "
                    "Confirm below that this is you, or the callsign will not be kept.",
                )
            elif call and call["state"] == "unverified":
                messages.info(
                    request,
                    f"{request.user.callsign} is not in the FCC table yet; it is held as "
                    "unverified until the nightly import finds it.",
                )
            if result["addresses_sent"]:
                messages.info(
                    request,
                    "Confirm "
                    + " and ".join(result["addresses_sent"])
                    + " from the link we sent there and you can sign in with "
                    + ("them" if len(result["addresses_sent"]) > 1 else "it")
                    + " too. Club email goes there either way.",
                )
            messages.success(request, "Profile saved.")
            return redirect("profile")
    else:
        form = AccountForm(instance=request.user, actor=request.user)
    licence = LicenseRecord.objects.filter(user=request.user).first()
    from apps.comms.categories import CONTROLLED, MANDATORY

    prefs = {p.category: p for p in request.user.notification_preferences.all()}
    rows = [
        {
            "key": k,
            "label": label,
            "email": prefs[k].email if k in prefs else True,
            "push": prefs[k].push if k in prefs else True,
        }
        for k, label in CONTROLLED.items()
    ]
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "licence": licence,
            "readonly_rows": readonly_rows(request.user, request.user),
            "notification_rows": rows,
            "mandatory_labels": list(MANDATORY.values()),
            "push_subscriptions": request.user.push_subscriptions.order_by("-created"),
            "addresses": addresses_state(request.user),
            "guardians": list(
                request.user.guardianships.filter(active=True).select_related("guardian")
            )
            if request.user.under_18
            else [],
        },
    )


@login_required
def notifications(request):
    """FR-71: one switch per controlled category; unticked means email off. Absence of a row
    means on, so a row is written only when the member turns something off (or back on)."""
    if request.method != "POST":
        return redirect("profile")
    from apps.comms.categories import CONTROLLED

    from .models import NotificationPreference

    wanted = set(request.POST.getlist("email")) & set(CONTROLLED)
    pushed = set(request.POST.getlist("push")) & set(CONTROLLED)
    for key in CONTROLLED:
        NotificationPreference.objects.update_or_create(
            user=request.user,
            category=key,
            defaults={"email": key in wanted, "push": key in pushed},
        )
    messages.success(request, "Notification settings saved.")
    return redirect(reverse("profile") + "#notifications")


class InviteForm(forms.Form):
    email = forms.EmailField(
        required=False,
        label="Invitee's email",
        help_text="Required for an adult. Optional for a member under 18, who need not have one: with none, they sign in with an address made from the guardian's.",
    )
    category = forms.ChoiceField()
    is_minor = forms.BooleanField(required=False, label="The invitee is under 18")
    guardian_email = forms.EmailField(
        required=False,
        label="Guardian's email",
        help_text="Required for a minor; the guardian receives the invitation and every message.",
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        cats = setting("member_categories", []) or []
        self.fields["category"].choices = [(c["key"], c["label"]) for c in cats]

    def clean(self):
        # The guardian field is shown only once "under 18" is ticked (templates/accounts/
        # invitations.html); the rule is enforced here regardless of what the page showed.
        data = super().clean()
        if data.get("is_minor"):
            if not data.get("guardian_email"):
                self.add_error("guardian_email", "A guardian's email is required for a minor.")
            elif (data.get("email") or "").lower() == data["guardian_email"].lower():
                self.add_error(
                    "email",
                    "The minor's address cannot be the guardian's; leave it blank if they have none.",
                )
        else:
            data["guardian_email"] = ""
            if not data.get("email"):
                self.add_error("email", "An adult's invitation needs their email address.")
        return data


@login_required
@require_http_methods(["GET", "POST"])
def invitations(request):
    if not request.user.is_officer:
        raise Http404
    created = None
    if request.method == "POST":
        form = InviteForm(request.POST)
        if form.is_valid():
            created = create_invitation(
                request.user,
                form.cleaned_data["email"],
                form.cleaned_data["category"],
                form.cleaned_data["is_minor"],
                form.cleaned_data["guardian_email"] or "",
                base_url=f"{request.scheme}://{request.get_host()}",
            )
            form = InviteForm()
    else:
        form = InviteForm()
    base = f"{request.scheme}://{request.get_host()}"
    recent = Invitation.objects.order_by("-created")[:25]
    return render(
        request,
        "accounts/invitations.html",
        {
            "form": form,
            "created": created,
            "created_text": invitation_text(created, base) if created else "",
            "created_link": f"{base}/me/invite/{created.token}/" if created else "",
            "recent": recent,
        },
    )


class AcceptForm(forms.Form):
    callsign = forms.CharField(
        max_length=12, required=False, help_text="Leave blank if you do not have one."
    )
    first_name = forms.CharField(max_length=80)
    middle_name = forms.CharField(max_length=80, required=False)
    last_name = forms.CharField(max_length=80)
    preferred_name = forms.CharField(max_length=80, required=False)
    cell_phone = forms.CharField(max_length=30, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Password, again")
    consent = forms.BooleanField(label="I have read the privacy notice")

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            raise forms.ValidationError("The passwords do not match.")
        if data.get("password1"):
            validate_password(data["password1"])
        return data


class GuardianAcceptForm(forms.Form):
    """§2.4: the guardian completes a minor's application. The guardian's own details are asked
    only when no account holds their address."""

    guardian_first_name = forms.CharField(max_length=80, label="Your first name")
    guardian_last_name = forms.CharField(max_length=80, label="Your last name")
    guardian_phone = forms.CharField(max_length=30, label="Your mobile number")
    relationship = forms.CharField(
        max_length=40, label="Your relationship to the member", help_text="Parent, guardian, …"
    )
    guardian_password1 = forms.CharField(
        widget=forms.PasswordInput, label="A password for your own account"
    )
    guardian_password2 = forms.CharField(widget=forms.PasswordInput, label="Your password, again")
    first_name = forms.CharField(max_length=80, label="Member's first name")
    middle_name = forms.CharField(max_length=80, required=False, label="Member's middle name")
    last_name = forms.CharField(max_length=80, label="Member's last name")
    preferred_name = forms.CharField(max_length=80, required=False, label="Member's preferred name")
    callsign = forms.CharField(
        max_length=12,
        required=False,
        label="Member's callsign",
        help_text="Leave blank if they do not have one.",
    )
    cell_phone = forms.CharField(
        max_length=30, required=False, label="Member's mobile number (optional)"
    )
    minor_email = forms.EmailField(
        required=False,
        label="Member's own email (optional)",
        help_text="If they have none, they sign in with an address made from yours and receive nothing directly; every message reaches you.",
    )
    password1 = forms.CharField(widget=forms.PasswordInput, label="Member's initial password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Member's password, again")
    consent = forms.BooleanField(
        label="I have read the privacy notice and consent on the member's behalf"
    )

    def __init__(self, *args, guardian_exists: bool, guardian_email: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.guardian_email = guardian_email.lower()
        if guardian_exists:
            for f in list(self.fields):
                if f.startswith("guardian_"):
                    self.fields.pop(f)

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            self.add_error("password2", "The member's passwords do not match.")
        elif data.get("password1"):
            validate_password(data["password1"])
        addr = (data.get("minor_email") or "").lower()
        if addr and addr == self.guardian_email:
            self.add_error(
                "minor_email", "That is your own address; leave it blank if the member has none."
            )
        elif addr and User.objects.filter(email=addr).exists():
            self.add_error("minor_email", "An account already uses that address.")
        if "guardian_password1" in self.fields:
            if data.get("guardian_password1") != data.get("guardian_password2"):
                self.add_error("guardian_password2", "Your passwords do not match.")
            elif data.get("guardian_password1"):
                validate_password(data["guardian_password1"])
        return data


def guardian_category() -> str:
    """A guardian is any adult with an account; guardianship is a relationship, not a membership
    category (the advisor, 2026-09-17). A parent who joins only to manage a minor's account is a
    community member where the club has that category, and uncategorised where it does not; an
    officer can set it to whatever is right."""
    keys = {c["key"] for c in (setting("member_categories", []) or [])}
    return "community" if "community" in keys else ""


def _accept_as_guardian(request, inv):
    """§2.4, FR-10: the invitation for a minor is completed by the guardian at
    `inv.guardian_email`. An existing account with that address signs in first; a new one is
    created here in the `guardian` category. The minor's own account is created read-only with
    the invitation's address as its sign-in."""
    from .guardian import link_guardian
    from .services import admit_from_invitation, apply_callsign

    existing = User.objects.filter(email=inv.guardian_email).first()
    if existing and (not request.user.is_authenticated or request.user.pk != existing.pk):
        return render(
            request,
            "accounts/invitation_guardian_signin.html",
            {"invitation": inv, "guardian": existing},
        )
    if not inv.opened_at:
        inv.opened_at = timezone.now()
        inv.save(update_fields=["opened_at"])
    form = GuardianAcceptForm(
        request.POST or None,
        guardian_exists=existing is not None,
        guardian_email=inv.guardian_email,
        initial={"minor_email": inv.email},
    )
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        guardian = existing
        if guardian is None:
            guardian = User.objects.create_user(
                email=inv.guardian_email,
                password=d["guardian_password1"],
                first_name=d["guardian_first_name"],
                last_name=d["guardian_last_name"],
                cell_phone=d["guardian_phone"],
                category=guardian_category(),
                access_level=AccessLevel.MEMBER,
            )
            record(guardian, "account.guardian_created", guardian, after={"invitation": inv.pk})
        from .guardian import sign_in_address

        own = (d.get("minor_email") or "").lower()
        minor = admit_from_invitation(
            inv,
            d["password1"],
            email=own or sign_in_address(guardian, d["first_name"]),
            sign_in_only_address=not own,
            first_name=d["first_name"],
            middle_name=d["middle_name"],
            last_name=d["last_name"],
            preferred_name=d["preferred_name"],
            callsign="",
            cell_phone=d["cell_phone"],
        )
        link_guardian(guardian, minor, guardian, d["relationship"])
        if d["callsign"].strip():
            apply_callsign(minor, d["callsign"])
        if not request.user.is_authenticated:
            login(request, guardian, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(
            request,
            f"{minor.display_first}'s account is ready. You act for them from your profile; they sign in read-only with {minor.email}.",
        )
        return redirect("profile")
    return render(
        request,
        "accounts/accept_invitation_guardian.html",
        {"form": form, "invitation": inv, "guardian": existing},
    )


@require_http_methods(["GET", "POST"])
def accept_invitation(request, token):
    inv = get_object_or_404(Invitation, token=token)
    if not inv.is_valid():
        return render(request, "accounts/invitation_invalid.html", {"invitation": inv}, status=410)
    if inv.is_minor:
        return _accept_as_guardian(request, inv)  # §2.4
    if not inv.opened_at:
        inv.opened_at = timezone.now()
        inv.save(update_fields=["opened_at"])
    if request.method == "POST":
        form = AcceptForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            user = admit_from_invitation(
                inv,
                d["password1"],
                first_name=d["first_name"],
                middle_name=d["middle_name"],
                last_name=d["last_name"],
                preferred_name=d["preferred_name"],
                callsign="",
                cell_phone=d["cell_phone"],
            )
            if d["callsign"].strip():
                from .services import apply_callsign

                result = apply_callsign(user, d["callsign"])  # FR-4, FR-16
                if result["state"] == "pending":
                    messages.warning(
                        request,
                        f"The FCC lists {user.callsign} under the name {result['uls_name']}. Confirm on your profile that this is you.",
                    )
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Welcome. Your account is ready.")
            return redirect("dashboard")
    else:
        form = AcceptForm()
    return render(request, "accounts/accept_invitation.html", {"form": form, "invitation": inv})


@login_required
@require_http_methods(["POST"])
def invitation_action(request, pk):
    """FR-3: revoke an unused invitation, or reissue it as a fresh link."""
    if not request.user.is_officer:
        raise Http404
    inv = get_object_or_404(Invitation, pk=pk)
    action = request.POST.get("action")
    if action == "revoke":
        revoke_invitation(request.user, inv)
        messages.success(request, f"Invitation to {inv.email} revoked.")
    elif action == "reissue":
        base = f"{request.scheme}://{request.get_host()}"
        new = reissue_invitation(request.user, inv, base_url=base)
        recent = Invitation.objects.order_by("-created")[:25]
        messages.success(
            request, f"New invitation issued to {new.email}; the old link no longer works."
        )
        return render(
            request,
            "accounts/invitations.html",
            {
                "form": InviteForm(),
                "created": new,
                "created_text": invitation_text(new, base),
                "created_link": f"{base}/me/invite/{new.token}/",
                "recent": recent,
            },
        )
    else:
        raise Http404
    return redirect("invitations")


@login_required
@require_http_methods(["POST"])
def uls_name_decide(request):
    """FR-16: the member confirms the ULS name is theirs, or refuses and loses the callsign."""
    from .services import decide_uls_name

    outcome = decide_uls_name(request.user, accept=request.POST.get("decision") == "yes")
    if outcome == "name replaced":
        messages.success(request, "Your name now matches the FCC record and comes from ULS.")
    elif outcome == "callsign rejected":
        messages.info(request, "That callsign was not kept. Check it and try again.")
    return redirect("profile")


@login_required
@require_http_methods(["POST"])
def request_closure(request):
    """FR-11: the member closes their own account (No access; retention clock starts)."""
    from django.contrib.auth import logout

    from .services import request_closure as close

    if request.POST.get("confirm") != "yes":
        messages.error(request, "Tick the confirmation to close your account.")
        return redirect("profile")
    close(request.user)
    logout(request)
    messages.info(
        request,
        "Your account is closed. The club keeps its records for the period in the privacy notice, then removes your contact details.",
    )
    return redirect("account_login")


@require_http_methods(["GET"])
def verify_address(request, token):
    """A member proves one of their own addresses by opening the link sent to it. From then on
    it signs them in as well as their usual address."""
    from . import addresses

    found = addresses.from_token(token)
    if not found:
        return render(request, "accounts/verify_address.html", {"outcome": "invalid"}, status=410)
    user, address = found
    try:
        addresses.mark_verified(user, address)
        outcome = "done"
    except addresses.AddressInUse:
        outcome = "taken"
    return render(
        request,
        "accounts/verify_address.html",
        {"outcome": outcome, "address": address, "person": user},
    )


def addresses_state(user):
    from . import addresses

    return addresses.state(user)


@login_required
@require_http_methods(["POST"])
def resend_address(request):
    """Send the confirmation link again, to the address itself."""
    from . import addresses

    address = request.POST.get("address", "").strip().lower()
    if address not in addresses.on_file(request.user):
        messages.error(request, "That address is not on your account.")
    elif address in addresses.verified(request.user):
        messages.info(request, f"{address} is already confirmed.")
    else:
        addresses.send_confirmation(
            request.user, address, f"{request.scheme}://{request.get_host()}"
        )
        messages.success(request, f"A confirmation link is on its way to {address}.")
    return redirect("profile")
