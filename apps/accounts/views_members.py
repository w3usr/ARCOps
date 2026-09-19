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
from .account import AccountForm, may_manage, profile_rows, readonly_rows, save_account
from .models import User
from .services import issue_temporary_password, set_access

# The classes the ladder does not hold: a station the FCC gives no operator class, and no
# license at all. The key narrows the directory; the letter is what the Class column shows.
STATION_CHOICES = (
    ("club", "Club station"),
    ("races", "RACES station"),
    ("military", "Military recreation"),
    ("none", "No license"),
)
STATION_FILTERS = {"club": "C", "races": "R", "military": "M", "none": "U"}


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
    return {"license": lic, "agreements": list(latest.values())}


# The directory's columns. `key` is what ?sort= carries, `full` marks the ones only an officer
# may see, and `sort` reads the value a reader actually sees, so a column sorts by what is in
# it rather than by the key stored behind it ("Community Member", not "community").
DIRECTORY_COLUMNS = [
    # The redacted name, and everybody gets it, officers included: it is how this person appears
    # to the rest of the club, so an officer can see at a glance what is on public view without
    # signing in as somebody else (NAF, 2026-09-19).
    {"key": "name", "label": "Name", "show": "all"},
    {"key": "first", "label": "First", "show": "full"},
    {"key": "last", "label": "Last", "show": "full"},
    {"key": "preferred", "label": "Preferred", "show": "full"},
    {"key": "callsign", "label": "Callsign", "show": "all"},
    {"key": "class", "label": "Class", "show": "all"},
    {"key": "category", "label": "Category", "show": "full"},
    {"key": "position", "label": "Position", "show": "all"},
    {"key": "access", "label": "Access", "show": "full"},
    {"key": "email", "label": "Email", "show": "full"},
    {"key": "phone", "label": "Phone", "show": "full"},
]


def _sort_keys(positions: dict, cats: dict):
    """One key function per column, over the displayed value.

    Sorting happens in Python rather than in SQL because three of these columns show a label
    the database does not hold: the category and position labels come from the club's
    configuration, and access is the groups an account is in. A club directory is tens of rows,
    or low hundreds; the honest sort is worth more here than the query.
    """

    def text(v) -> str:
        return (v or "").strip().lower()

    def settled(fn):
        """Every sort ends in the same tiebreaker, so no two rows ever compare equal.

        Without it the order among ties is whatever the database happened to return, which
        means reversing a column does not reverse the page and a reader watching two names
        swap places wonders what else moved.
        """
        return lambda m: (*fn(m), text(m.last_name), text(m.first_name), m.pk)

    ladder = [text(c) for c in (setting("license_ladder", []) or [])]
    return {key: settled(fn) for key, fn in _columns(text, positions, cats, ladder).items()}


# Below the ladder, in the order the rosters count them: the stations the FCC gives no
# operator class, then the accounts with no license at all.
STATION_ORDER = ["C", "R", "M"]


def _class_rank(m, ladder: list, text) -> int:
    cls = text(m.license_class)
    if cls in ladder:
        return ladder.index(cls)
    letter = m.license_letter
    if letter in STATION_ORDER:
        return len(ladder) + STATION_ORDER.index(letter)
    return len(ladder) + len(STATION_ORDER)


def _columns(text, positions: dict, cats: dict, ladder: list):
    return {
        "name": lambda m: (text(m.display_first), text(m.last_name)),
        "first": lambda m: (text(m.first_name), text(m.last_name)),
        "last": lambda m: (text(m.last_name), text(m.first_name)),
        "preferred": lambda m: (text(m.preferred_name), text(m.last_name)),
        # A blank is not a small callsign: no-callsign sorts after every callsign going up,
        # and before them coming down, rather than mixing in among the As.
        "callsign": lambda m: (not m.callsign, text(m.callsign)),
        # Up the ladder, not down the alphabet: Novice before Extra, because that is what the
        # class means. Sorting these as words would file Advanced above Technician. A club
        # station (C) holds no class at all, so it sorts after the ladder and ahead of the
        # accounts with no license.
        "class": lambda m: (_class_rank(m, ladder, text), text(m.license_class)),
        "category": lambda m: (text(cats.get(m.category, m.category)), text(m.last_name)),
        "position": lambda m: (
            not m.club_position,
            text(positions.get(m.club_position, m.club_position)),
            text(m.last_name),
        ),
        "access": lambda m: (text(m.access_label), text(m.last_name)),
        "email": lambda m: (
            not m.addresses.all(),
            text(min((a.address for a in m.addresses.all()), default="")),
        ),
        "phone": lambda m: (not m.cell_phone, text(m.cell_phone)),
    }


@login_required
def members(request):
    full = request.user.may("view_member_records")
    if not request.user.is_member:
        raise Http404  # FR-121: a Provisional member sees no directory
    q = request.GET.get("q", "").strip()
    # The directory is who the club has now. A former member is in the archive (FR-125), which
    # is read by a faculty advisor or a sysadmin, so they are out of this list for everyone. A
    # deleted account is out too: its row survives only so past rosters keep their shape, and it
    # was appearing here as "Deleted member" with no address and no access (NAF, 2026-09-19).
    current = User.objects.filter(archived_at__isnull=True, deleted_at__isnull=True)
    users = (
        # the directory shows every address an officer may write to, so they come in one query
        current.select_related("license").prefetch_related("addresses", "groups")
        if full
        else current.filter(groups__permissions__codename="view_directory")
        .distinct()
        .select_related("license")
    )
    if q:
        cond = (
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(preferred_name__icontains=q)
            | Q(callsign__icontains=q)
        )
        if full:
            cond |= Q(addresses__address__icontains=q)
        users = users.filter(cond).distinct()

    positions = {p["key"]: p["label"] for p in (setting("club_positions", []) or [])}
    cats = {c["key"]: c["label"] for c in (setting("member_categories", []) or [])}

    # Narrowing. Category and access are an officer's to filter by, because they are an
    # officer's to see; position is on the page for everyone.
    chosen = {
        "category": request.GET.get("category", "") if full else "",
        "position": request.GET.get("position", ""),
        # The class is on the page for everyone, so everyone can narrow by it.
        "license": request.GET.get("license", ""),
        "access": request.GET.get("access", "") if full else "",
    }
    if chosen["category"]:
        users = users.filter(category=chosen["category"])
    if chosen["position"]:
        users = users.filter(club_position=chosen["position"])

    rows = list(users)
    if chosen["license"]:
        want = chosen["license"].strip().lower()
        rows = [
            m
            for m in rows
            if (want in STATION_FILTERS and m.license_letter == STATION_FILTERS[want])
            or m.license_class.lower() == want
        ]
    if chosen["access"]:
        want = chosen["access"]
        rows = [
            m
            for m in rows
            if (want == "sysadmin" and m.is_superuser)
            or (want == "none" and not m.is_superuser and not m.groups.all())
            or any(g.name == want for g in m.groups.all())
        ]

    # Last name by default; a member has no last-name column, so theirs sorts by the name they
    # do see, which is that first name and initial.
    default_sort = "last" if full else "name"
    sort = request.GET.get("sort", default_sort)
    keys = _sort_keys(positions, cats)
    shown = {
        c["key"] for c in DIRECTORY_COLUMNS if c["show"] == "all" or (c["show"] == "full") == full
    }
    if sort not in keys or sort not in shown:
        sort = default_sort
    descending = request.GET.get("dir") == "desc"
    rows.sort(key=keys[sort], reverse=descending)

    columns = []
    for col in DIRECTORY_COLUMNS:
        if col["show"] != "all" and (col["show"] == "full") != full:
            continue
        here = col["key"] == sort
        params = request.GET.copy()
        params["sort"] = col["key"]
        # Clicking the column you are already sorted by turns it round.
        params["dir"] = "desc" if here and not descending else "asc"
        params.pop("page", None)
        columns.append(
            {
                **col,
                "url": f"?{params.urlencode()}",
                "here": here,
                "aria": ("descending" if descending else "ascending") if here else "none",
            }
        )

    license_choices = [(c, c) for c in (setting("license_ladder", []) or [])]
    license_choices += list(STATION_CHOICES)
    access_choices = [(g["key"], g["label"]) for g in (setting("access_groups", []) or [])]
    access_choices += [("sysadmin", "Sysadmin"), ("none", "No access")]
    return render(
        request,
        "accounts/members.html",
        {
            "members": rows,
            "q": q,
            "full": full,
            "positions": positions,
            "categories": cats,
            "columns": columns,
            "sort": sort,
            "dir": "desc" if descending else "asc",
            "chosen": chosen,
            "category_choices": sorted(cats.items(), key=lambda kv: kv[1]),
            "license_choices": license_choices,
            "position_choices": sorted(positions.items(), key=lambda kv: kv[1]),
            "access_choices": access_choices,
        },
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


def _preferences(user) -> dict:
    """What reaches this person: the controlled categories with their switches, the ones that
    are always sent, and the devices that have allowed browser notifications. The page shows it
    as text and the edit page as switches, from the one place."""
    from apps.comms.categories import CONTROLLED, MANDATORY

    prefs = {p.category: p for p in user.notification_preferences.all()}
    return {
        "notification_rows": [
            {
                "key": k,
                "label": label,
                "email": prefs[k].email if k in prefs else True,
                "push": prefs[k].push if k in prefs else True,
            }
            for k, label in CONTROLLED.items()
        ],
        "mandatory_labels": list(MANDATORY.values()),
        "push_subscriptions": user.push_subscriptions.order_by("-created"),
    }


def _member_or_404(request, pk):
    """The account this page is about, for a reader entitled to see it.

    Your own account is one of these pages: `/me/` redirects here (NAF, 2026-09-19, "These
    should be the same thing"), so a member who may read nobody else's record may always read
    their own.
    """
    member = get_object_or_404(User, pk=pk)
    if member == request.user:
        return member
    if not request.user.may("view_member_records"):
        raise Http404
    if member.is_archived and not request.user.may("view_archive"):
        raise Http404  # the archive is the advisor's to read, and so is a page within it
    return member


@login_required
def member_detail(request, pk):
    """A member's profile, read-only.

    Nothing here changes anything. NAF, 2026-09-19: a name in the directory should open "a
    read-only view of their profile page", with an Edit profile button for the people entitled
    to change it, because it "will allow for potential public views of profiles, as well as
    make it more difficult to accidentally change information". Every form that was on this
    page is now on `member_edit`.
    """
    member = _member_or_404(request, pk)
    actor = request.user
    is_self = member == actor
    return render(
        request,
        "accounts/member_detail.html",
        {
            "member": member,
            # The name is the heading, on your own page and on an officer's view alike.
            "rows": profile_rows(member, skip=("first_name",)),
            **(_preferences(member) if is_self else {}),
            "addresses": __import__("apps.accounts.addresses", fromlist=["state"]).state(member),
            "standing": _standing(member),
            "guardian_links": list(
                member.guardianships.select_related("guardian").order_by("-active", "created")
            ),
            "wards": list(member.wards.filter(active=True).select_related("minor")),
            "can_edit": may_manage(actor, member) and not _minor_readonly(request, member),
            "is_self": is_self,
        },
    )


def _minor_readonly(request, member) -> bool:
    """A member under 18 signs in read-only; a guardian acting for them does the editing
    (§2.4). The middleware refuses their POSTs; this keeps the page and the button away too."""
    return bool(
        member == request.user
        and member.under_18
        and getattr(request, "acting_guardian", None) is None
    )


@login_required
@require_http_methods(["GET", "POST"])
def member_edit(request, pk):
    """The same account with every control on it: the account fields, addresses, the license,
    guardians, access, archiving, and deletion. Reached from the profile page's Edit button."""
    member = _member_or_404(request, pk)
    actor = request.user
    if not may_manage(actor, member) or _minor_readonly(request, member):
        raise Http404
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
                    # Saving returns to the page that reads (docs/INTERFACE.md); the other
                    # actions on this page stay here, because they are usually done in a run.
                    return redirect("member_detail", pk=member.pk)
        elif views_addresses.handle(request, member):
            return redirect("member_edit", pk=member.pk)
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
            return redirect("member_edit", pk=member.pk)
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
            return redirect("member_edit", pk=pk)
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
                return redirect("member_edit", pk=pk)
            try:
                result = delete_account(actor, member, reason[:500])
            except DeletionRefused as exc:
                messages.error(request, f"Not deleted: {exc}.")
                return redirect("member_edit", pk=pk)
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
                return redirect("member_edit", pk=member.pk)
        elif action == "reopen" and actor.may("assign_groups"):
            set_access(actor, member, ["member"], "reopened")
            messages.success(request, f"{member.short_name} is a member again.")
            return redirect("member_edit", pk=member.pk)
        elif action == "archive" and actor.may("archive_members"):  # FR-125
            from .services import ArchiveRefused, archive_member

            if member == actor:
                messages.error(request, "You cannot archive your own account.")
                return redirect("member_edit", pk=member.pk)
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
            return redirect("member_edit", pk=member.pk)
        elif action == "restore" and actor.may("archive_members"):
            from .services import restore_member

            restore_member(actor, member)
            messages.success(request, f"{member.short_name} is a member again.")
            return redirect("member_edit", pk=member.pk)
        elif action == "admit" and member.is_provisional:  # FR-121: any officer reviews
            entry.admit(actor, member)
            messages.success(request, f"{member.short_name} is now a member.")
            return redirect("member_edit", pk=member.pk)
        elif action == "decline" and member.is_provisional:
            entry.decline(actor, member, request.POST.get("reason", "").strip()[:300])
            messages.success(request, f"{member.short_name} declined.")
            return redirect("member_edit", pk=member.pk)
        elif action == "mark_verified":  # FR-120: the officer's waiver
            entry.mark_verified(actor, member)
            messages.success(request, "Address marked verified.")
            return redirect("member_edit", pk=member.pk)
        else:
            raise Http404

    from apps.credentials.services import ladder

    ctx_ladder = ladder()
    return render(
        request,
        "accounts/member_edit.html",
        {
            "member": member,
            "form": form,
            "ladder": ctx_ladder,
            "readonly_rows": readonly_rows(actor, member, skip=("first_name",)),
            # What the card over these fields is called. On your own account they are your
            # details; on somebody else's they are what this officer may manage, which for most
            # officers is the club position alone.
            "manage_heading": "Details"
            if member == actor
            else ("Manage" if actor.may("edit_member_privileges") else "Club position"),
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
            **(_preferences(member) if member == actor else {}),
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
