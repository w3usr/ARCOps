"""Entry links: the officer's page to make and manage them; the public join, verification, and
mentor-needs pages (FR-119, FR-120, FR-123)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.events.models import Event
from apps.events.services.mentors import mentor_needs
from apps.ops.audit import record
from apps.ops.config import setting

from . import entry
from .models import EntryLink, User


def _base(request) -> str:
    return f"{request.scheme}://{request.get_host()}"


class LinkForm(forms.Form):
    label = forms.CharField(
        max_length=80,
        help_text="The course or the organisation; recorded on every account that joins.",
    )
    kind = forms.ChoiceField(choices=EntryLink.Kind.choices)
    required_domain = forms.ChoiceField(required=False, label="Required email domain (class links)")
    expires_at = forms.DateField(label="Expires on", widget=forms.DateInput(attrs={"type": "date"}))
    cap = forms.IntegerField(
        required=False, min_value=1, max_value=500, label="Cap on accounts (optional)"
    )
    landing_event = forms.ModelChoiceField(
        queryset=Event.objects.none(), required=False, label="Land on this event (optional)"
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        domains = entry.trusted_domains()
        self.fields["required_domain"].choices = [("", "None")] + [(d, d) for d in domains]
        self.fields["landing_event"].queryset = Event.objects.exclude(
            state=Event.State.CANCELLED
        ).order_by("-id")

    def clean(self):
        d = super().clean()
        if d.get("kind") == EntryLink.Kind.CLASS and not d.get("required_domain"):
            self.add_error(
                "required_domain",
                "A class link needs a trusted domain; add one to the club configuration if the list is empty.",
            )
        if d.get("expires_at") and d["expires_at"] <= timezone.now().date():
            self.add_error("expires_at", "Choose a date in the future.")
        return d


@login_required
@require_http_methods(["GET", "POST"])
def entry_links(request):
    if not request.user.is_officer:
        raise Http404
    created = None
    form = LinkForm()
    if request.method == "POST":
        form = LinkForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            expires = datetime.combine(d["expires_at"], datetime.max.time()).replace(tzinfo=UTC)
            created = entry.create_link(
                request.user,
                label=d["label"],
                kind=d["kind"],
                required_domain=d["required_domain"],
                expires_at=expires,
                cap=d["cap"],
                landing_event=d["landing_event"],
            )
            form = LinkForm()
    links = EntryLink.objects.select_related("created_by", "landing_event").all()[:50]
    base = _base(request)
    return render(
        request,
        "accounts/entry_links.html",
        {
            "form": form,
            "links": links,
            "created": created,
            "base": base,
            "created_link": f"{base}/join/{created.token}/" if created else "",
        },
    )


@login_required
@require_POST
def entry_link_action(request, pk):
    if not request.user.is_officer:
        raise Http404
    link = get_object_or_404(EntryLink, pk=pk)
    action = request.POST.get("action")
    if action == "pause":
        link.state = EntryLink.State.PAUSED
    elif action == "resume":
        link.state = EntryLink.State.ACTIVE
    elif action == "revoke":
        link.state = EntryLink.State.REVOKED
    elif action == "extend":
        link.expires_at = max(link.expires_at, timezone.now()) + timedelta(days=30)
    elif action == "verify_all":
        n = 0
        for u in link.joined.filter(email_verified_at__isnull=True):
            entry.mark_verified(request.user, u)
            n += 1
        messages.success(request, f"{n} account{'s' if n != 1 else ''} marked verified.")
        return redirect("entry_links")
    else:
        raise Http404
    link.save()
    record(request.user, f"entry_link.{action}", link)
    messages.success(
        request,
        f"Link “{link.label}”: {action}d."
        if action != "extend"
        else f"Link “{link.label}” now runs to {link.expires_at:%d %b %Y}.",
    )
    return redirect("entry_links")


class JoinForm(forms.Form):
    """The invitation's join form plus the address, the category (class links), and the age question."""

    email = forms.EmailField(label="Email address")
    callsign = forms.CharField(
        max_length=12,
        required=False,
        help_text="If you hold one. Your name and license come from the FCC record.",
    )
    first_name = forms.CharField(max_length=80)
    middle_name = forms.CharField(max_length=80, required=False)
    last_name = forms.CharField(max_length=80)
    preferred_name = forms.CharField(max_length=80, required=False)
    cell_phone = forms.CharField(max_length=30, required=False)
    category = forms.ChoiceField(required=False)
    under_18 = forms.BooleanField(required=False, label="I am under 18")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Password, again")
    consent = forms.BooleanField(label="I have read the privacy notice")

    def __init__(self, *args, link: EntryLink, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        self.link = link
        if link.kind == EntryLink.Kind.CLASS:
            cats = [
                c
                for c in (setting("member_categories", []) or [])
                if c.get("key") in ("student", "faculty", "staff")
            ]
            self.fields["category"].choices = [(c["key"], c["label"]) for c in cats] or [
                ("student", "Student")
            ]
            self.fields["category"].initial = "student"
            self.fields["email"].help_text = f"Your {link.required_domain} address."
        else:
            self.fields.pop("category")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if self.link.required_domain and email.rsplit("@", 1)[-1] != self.link.required_domain:
            raise forms.ValidationError(f"This link is for {self.link.required_domain} addresses.")
        return email

    def clean(self):
        d = super().clean()
        if d.get("password1") != d.get("password2"):
            raise forms.ValidationError("The passwords do not match.")
        if d.get("password1"):
            validate_password(d["password1"])
        return d


def _link_or_page(request, token):
    link = get_object_or_404(EntryLink, token=token)
    why = link.why_closed()
    if why:
        return link, render(
            request, "accounts/join_closed.html", {"link": link, "why": why}, status=410
        )
    return link, None


def join(request, token):
    """A class link goes straight to the form; a community link shows the mentor-needs page first."""
    link, closed = _link_or_page(request, token)
    if closed:
        return closed
    if link.kind == EntryLink.Kind.COMMUNITY:
        return redirect("mentor_needs", token=token)
    return redirect("join_form", token=token)


def mentor_needs_page(request, token):
    link, closed = _link_or_page(request, token)
    if closed:
        return closed
    viewer_is_member = request.user.is_authenticated and request.user.is_member
    return render(
        request,
        "accounts/mentors.html",
        {
            "link": link,
            "needs": mentor_needs(viewer_is_member=viewer_is_member),
            "viewer_is_member": viewer_is_member,
        },
    )


@require_http_methods(["GET", "POST"])
def join_form(request, token):
    link, closed = _link_or_page(request, token)
    if closed:
        return closed
    if request.method == "POST":
        form = JoinForm(request.POST, link=link)
        if form.is_valid():
            d = form.cleaned_data
            if d.get("under_18"):
                return render(request, "accounts/invitation_minor.html", {"link": link}, status=200)
            existing = User.objects.filter(email=d["email"]).first()
            if existing:
                # The same page as success (FR-107); the person is told by email instead.
                from apps.comms.services import send

                send("account.address_in_use", existing, "account")
                return render(
                    request, "accounts/join_sent.html", {"link": link, "email": d["email"]}
                )
            user = entry.join_through_link(
                link,
                email=d["email"],
                password=d["password1"],
                category=d.get("category") or "student",
                base_url=_base(request),
                first_name=d["first_name"],
                middle_name=d["middle_name"],
                last_name=d["last_name"],
                preferred_name=d["preferred_name"],
                callsign=d["callsign"].upper().strip(),
                cell_phone=d["cell_phone"],
            )
            if user.callsign:
                from .services import apply_callsign

                call = user.callsign
                user.callsign = ""
                apply_callsign(user, call)  # FR-4, FR-16: lookup, name, or a pending confirmation
            if link.kind == EntryLink.Kind.CLASS:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                messages.success(
                    request,
                    f"Welcome. Confirm your address from the email we sent within {entry.verification_days()} days.",
                )
                if link.landing_event_id:
                    return redirect("event_detail", pk=link.landing_event_id)
                return redirect("event_list")
            return render(request, "accounts/join_sent.html", {"link": link, "email": d["email"]})
    else:
        form = JoinForm(link=link)
    return render(request, "accounts/join.html", {"form": form, "link": link})


def verify_email(request, token):
    user = entry.user_from_token(token)
    if not user:
        return render(request, "accounts/verify_result.html", {"outcome": "invalid"}, status=410)
    if user.email_verified_at:
        outcome = "already"
    else:
        outcome = entry.complete_verification(user, _base(request))
    if request.user.is_authenticated and request.user.pk != user.pk:
        pass  # someone else's link opened while signed in: show the result, change nothing else
    elif not request.user.is_authenticated and user.is_active:
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return render(request, "accounts/verify_result.html", {"outcome": outcome, "person": user})
