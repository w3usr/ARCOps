"""Profile, invitations, and the invitation-accept (registration) flow."""

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.credentials.models import LicenseRecord
from apps.ops.config import institution_email_domain, setting

from .models import Invitation, User
from .services import admit_from_invitation, create_invitation, invitation_text


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
        self.fields["institution_email"].label = f"{domain} email" if domain else "Institution email"
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
            user.callsign = user.callsign.upper().strip()
            user.save()
            if user.callsign != old_call and old_call:
                from .models import CallsignHistory

                CallsignHistory.objects.create(user=user, callsign=old_call)
            messages.success(request, "Profile saved.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    licence = LicenseRecord.objects.filter(user=request.user).first()
    return render(request, "accounts/profile.html", {"form": form, "licence": licence})


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


@require_http_methods(["GET", "POST"])
def accept_invitation(request, token):
    inv = get_object_or_404(Invitation, token=token)
    if not inv.is_valid():
        return render(request, "accounts/invitation_invalid.html", {"invitation": inv}, status=410)
    if inv.is_minor:
        # The guardian flow (§2.4) is not built yet; a minor must not self-register.
        return render(request, "accounts/invitation_minor.html", {"invitation": inv}, status=200)
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
                callsign=d["callsign"].upper().strip(),
                cell_phone=d["cell_phone"],
            )
            if user.callsign:
                from apps.credentials.services import refresh_license_from_local_table

                refresh_license_from_local_table(user)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Welcome. Your account is ready.")
            return redirect("dashboard")
    else:
        form = AcceptForm()
    return render(request, "accounts/accept_invitation.html", {"form": form, "invitation": inv})
