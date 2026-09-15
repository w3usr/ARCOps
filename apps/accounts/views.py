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
from apps.ops.config import institution_email_domain, setting

from .models import AccessLevel, Invitation, User
from .services import (
    admit_from_invitation,
    create_invitation,
    invitation_text,
    reissue_invitation,
    revoke_invitation,
)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "preferred_name",
            "callsign",
            "institution_email",
            "institution_email_delivery",
            "personal_email",
            "personal_email_delivery",
            "cell_phone",
            "student_level",
            "graduation_semester",
            "graduation_year",
        ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        domain = institution_email_domain()
        self.fields["institution_email"].label = (
            f"{domain} email" if domain else "Institution email"
        )
        self.fields["personal_email"].label = "Personal email"
        for f in ("institution_email_delivery", "personal_email_delivery"):
            self.fields[f].label = "Send club email here"
        if self.instance.category != "student":
            for f in ("student_level", "graduation_semester", "graduation_year"):
                self.fields.pop(f)


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            old_call = User.objects.get(pk=request.user.pk).callsign
            user = form.save(commit=False)
            new_call = (user.callsign or "").upper().strip()
            user.callsign = old_call  # apply_callsign owns the change
            user.save()
            if new_call != old_call:
                from .services import apply_callsign

                result = apply_callsign(user, new_call, previous=old_call)  # FR-102, FR-16
                if result["state"] == "pending":
                    messages.warning(
                        request,
                        f"The FCC lists {new_call} under the name {result['uls_name']}. Confirm below that this is you, or the callsign will not be kept.",
                    )
                elif result["state"] == "unverified":
                    messages.info(
                        request,
                        f"{new_call} is not in the FCC table yet; it is held as unverified until the nightly import finds it.",
                    )
            messages.success(request, "Profile saved.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
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
            "notification_rows": rows,
            "mandatory_labels": list(MANDATORY.values()),
            "push_subscriptions": request.user.push_subscriptions.order_by("-created"),
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
    email = forms.EmailField()
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
        else:
            data["guardian_email"] = ""
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
    password1 = forms.CharField(widget=forms.PasswordInput, label="Member's initial password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Member's password, again")
    consent = forms.BooleanField(
        label="I have read the privacy notice and consent on the member's behalf"
    )

    def __init__(self, *args, guardian_exists: bool, **kwargs):
        super().__init__(*args, **kwargs)
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
        if "guardian_password1" in self.fields:
            if data.get("guardian_password1") != data.get("guardian_password2"):
                self.add_error("guardian_password2", "Your passwords do not match.")
            elif data.get("guardian_password1"):
                validate_password(data["guardian_password1"])
        return data


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
    form = GuardianAcceptForm(request.POST or None, guardian_exists=existing is not None)
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
                category="guardian",
                access_level=AccessLevel.MEMBER,
            )
            record(guardian, "account.guardian_created", guardian, after={"invitation": inv.pk})
        minor = admit_from_invitation(
            inv,
            d["password1"],
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
