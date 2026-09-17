"""
The messages the application sends, as templates a sysadmin can edit in the interface (FR-78).

`club_import` seeds these into MessageTemplate rows; `render_message` falls back to them when a
row is missing, so a fresh installation sends sensible mail before anyone has edited anything.
Subject and body are Django templates. `variables` documents what each may use; it is shown
beside the template on the editing page and is not enforced.

Bodies are HTML limited to the richtext allow-list. Keep them short and plain: they are read in
mail clients and in "My messages", and every one gets a generated plain-text alternative.
"""

DEFAULT_TEMPLATES: list[dict] = [
    {
        "key": "invitation",
        "subject": "You are invited to join {{ club.name }}",
        "body_html": "<p>You are invited to join {{ club.name }}'s operations site.</p><p>Open this link to create your account: <a href=\"{{ link }}\">Accept the invitation</a></p><p>The link works once and expires on {{ expires|date:'j F Y' }}.</p><p>Questions: {{ club.contact_email }}</p>",
        "variables": ["club.name", "club.contact_email", "link", "expires", "category"],
    },
    {
        "key": "account.verify_member",
        "subject": "Confirm your address for {{ club.short_name }}",
        "body_html": '<p>Welcome to {{ club.short_name }}. Your account is ready; please confirm this is your address by opening the link below within {{ days }} days, or sign-in will pause until you do.</p><p><a href="{{ link }}">Confirm my address</a></p>',
        "variables": ["club.short_name", "link", "days", "user.display_first"],
    },
    {
        "key": "account.verify_provisional",
        "subject": "Confirm your address for {{ club.short_name }}",
        "body_html": '<p>Thank you for offering to help {{ club.short_name }}. Open the link below to confirm your address; your account is created the moment you do, and a club officer will then review it.</p><p><a href="{{ link }}">Confirm my address</a></p>',
        "variables": ["club.short_name", "link", "days"],
    },
    {
        "key": "account.provisional_notice",
        "subject": "New provisional member for {{ club.short_name }}: {{ person.short_name }}",
        "body_html": '<p>{{ person.full_name }}{% if person.callsign %} {{ person.callsign }}{% endif %} joined through {{ via }} and is waiting for review. Admit them as a member or decline on their page:</p><p><a href="{{ link }}">Review their request</a></p>',
        "variables": ["club.short_name", "person.full_name", "person.callsign", "via", "link"],
    },
    {
        "key": "account.admitted",
        "subject": "Welcome to {{ club.short_name }}",
        "body_html": (
            "<p>A club officer has reviewed your account: you are now a member of "
            "{{ club.short_name }}. Sign in to see the roster and the agreements.</p>"
        ),
        "variables": ["club.short_name", "user.display_first"],
    },
    {
        "key": "account.declined",
        "subject": "Your {{ club.short_name }} account",
        "body_html": (
            "<p>A club officer has reviewed your request and has not admitted you at this time."
            "{% if reason %} Reason: {{ reason }}{% endif %}</p>"
        ),
        "variables": ["club.short_name", "reason"],
    },
    {
        "key": "account.address_in_use",
        "subject": "Your {{ club.short_name }} account",
        "body_html": (
            "<p>Someone used this address on a join link, but it already has an account. Sign in, "
            "or use “Forgot your username or password?” on the sign-in page.</p>"
        ),
        "variables": ["club.short_name"],
    },
    {
        "key": "account.completed",
        "subject": "{{ person.full_name }} joined {{ club.short_name }}",
        "body_html": '<p>{{ person.full_name }}{% if person.callsign %} ({{ person.callsign }}{% if uls_name %}, ULS name {{ uls_name }}{% endif %}){% endif %} completed the invitation sent to {{ invited_email }} as {{ category }}.</p><p>If that is not who you expected, set the account to No access from their page: <a href="{{ link }}">Open their page</a></p>',
        "variables": [
            "person.full_name",
            "person.callsign",
            "uls_name",
            "invited_email",
            "category",
            "link",
        ],
    },
    {
        "key": "account.welcome",
        "subject": "Welcome to {{ club.name }}",
        "body_html": '<p>Your {{ club.short_name }} account is ready, {{ user.display_first }}. Sign in to see what is coming up, sign the access agreements, and pick your hours.</p><p><a href="{{ site_url }}/">Open the site</a></p>',
        "variables": ["club.name", "club.short_name", "user.display_first", "site_url"],
    },
    {
        "key": "agreement.submitted",
        "subject": "Agreement to review: {{ person.full_name }}, {{ title }}",
        "body_html": '<p>{{ person.full_name }}{% if person.callsign %} {{ person.callsign }}{% endif %} signed <em>{{ title }}</em> and it awaits your approval.</p><p><a href="{{ link }}">Review and approve</a></p>',
        "variables": ["person.full_name", "person.callsign", "title", "link"],
    },
    {
        "key": "agreement.approved",
        "subject": "Approved: {{ title }}",
        "body_html": (
            "<p>Your <em>{{ title }}</em> was approved by {{ approver }} and is current until "
            "{{ expires|date:'j F Y' }}.</p>"
        ),
        "variables": ["title", "approver", "expires", "user.display_first"],
    },
    {
        "key": "agreement.declined",
        "subject": "Not approved: {{ title }}",
        "body_html": '<p>Your <em>{{ title }}</em> was not approved.{% if reason %} Reason: {{ reason }}{% endif %}</p><p>You can sign it again once the reason is addressed: <a href="{{ link }}">Open Agreements</a></p>',
        "variables": ["title", "reason", "link", "user.display_first"],
    },
    {
        "key": "signup.removed",
        "subject": "Your sign-up was removed: {{ event.title }}",
        "body_html": '<p>{{ actor }} removed you from {{ event.title }}, {{ when }}, {{ position }} as {{ role }}.{% if reason %} Reason: {{ reason }}{% endif %}</p><p><a href="{{ link }}">Open the slot</a></p>',
        "variables": ["actor", "event.title", "when", "position", "role", "reason", "link"],
    },
    {
        "key": "signup.assigned",
        "subject": "You were signed up: {{ event.title }}",
        "body_html": '<p>{{ actor }} signed you up for {{ event.title }}, {{ when }}, {{ position }} as {{ role }}. If that does not work for you, cancel from your schedule and the captains will be told.</p><p><a href="{{ link }}">Open the slot</a></p>',
        "variables": ["actor", "event.title", "when", "position", "role", "link"],
    },
    {
        "key": "slot.cancelled",
        "subject": "Slot canceled: {{ event.title }}, {{ when }}",
        "body_html": '<p>The slot you held in {{ event.title }}, {{ when }}, {{ position }}, was canceled by {{ actor }}.{% if reason %} Reason: {{ reason }}{% endif %}</p><p><a href="{{ link }}">Open the event</a></p>',
        "variables": ["actor", "event.title", "when", "position", "reason", "link"],
    },
    {
        "key": "event.cancelled",
        "subject": "Event canceled: {{ event.title }}",
        "body_html": (
            "<p>{{ event.title }} was canceled by {{ actor }}.{% if reason %} Reason: {{ reason }}{% endif %} "
            "Your sign-ups for it ({{ count }}) are withdrawn.</p>"
        ),
        "variables": ["actor", "event.title", "reason", "count"],
    },
    {
        "key": "captain.member_cancelled",
        "subject": "{% if late %}Late cancellation{% else %}Cancellation{% endif %}: {{ person }} left {{ when }}, {{ event.title }}",
        "body_html": '<p>{{ person }} canceled their {{ role }} sign-up for {{ event.title }}, {{ when }}, {{ position }}.{% if late %} This is inside the {{ cutoff }}-hour cutoff.{% endif %}</p>{% if broken %}<p>The slot is now <strong>{{ broken }}</strong>.</p>{% endif %}<p><a href="{{ link }}">Open the slot</a></p>',
        "variables": [
            "person",
            "role",
            "event.title",
            "when",
            "position",
            "late",
            "cutoff",
            "broken",
            "link",
        ],
    },
    {
        "key": "captain.access_removed",
        "subject": "{{ person }} lost access; {{ count }} sign-up(s) withdrawn from {{ event.title }}",
        "body_html": '<p>{{ person }}\'s access was removed by {{ actor }}, so their future sign-ups in {{ event.title }} were withdrawn: {{ slots }}.</p><p><a href="{{ link }}">Open the event</a></p>',
        "variables": ["person", "actor", "count", "event.title", "slots", "link"],
    },
    {
        "key": "reminder",
        "subject": "Tomorrow: {{ event.title }}, {{ when_lead }}",
        "body_html": (
            "<p>You are signed up as <strong>{{ role }}</strong> for {{ event.title }}.</p>"
            "<p><strong>When:</strong> {{ when_local }}<br>{{ when_utc }}<br>"
            "<strong>Where:</strong> {{ location }}, {{ position }}"
            "{% if control_operator %}<br><strong>Control operator:</strong> {{ control_operator }}{% endif %}"
            "{% if others %}<br><strong>With you:</strong> {{ others }}{% endif %}</p>"
            '<p><a href="{{ confirm_link }}">Confirm you will be there</a> · '
            '<a href="{{ cannot_link }}">I cannot make it</a></p>'
            "{% if kbyg %}<h2>Know before you go</h2>{{ kbyg|safe }}{% endif %}"
            "<h2>Who to contact</h2><p>{% for c in captains %}{{ c }}<br>{% endfor %}"
            "{% if advisors %}Faculty advisor: {% for a in advisors %}{{ a }}{% if not forloop.last %}; {% endif %}{% endfor %}{% endif %}</p>"
        ),
        "variables": [
            "event.title",
            "role",
            "when_lead",
            "when_local",
            "when_utc",
            "location",
            "position",
            "control_operator",
            "others",
            "confirm_link",
            "cannot_link",
            "kbyg",
            "captains",
            "advisors",
        ],
    },
    {
        "key": "warning.person",
        "subject": "Your slot needs help: {{ event.title }}, {{ when }}",
        "body_html": '<p>The slot you hold in {{ event.title }}, {{ when }}, {{ position }}, reads <strong>{{ status }}</strong>: {{ reasons }}.</p><p>If you know someone who could fill it, ask them to sign up: <a href="{{ link }}">Open the slot</a></p>',
        "variables": ["event.title", "when", "position", "status", "reasons", "link"],
    },
    {
        "key": "warning.captains",
        "subject": "{{ count }} slot(s) at risk in the next {{ horizon }} hours",
        "body_html": (
            "<p>Slots that cannot run, depend on one person, or have an unconfirmed sign-up within 24 hours:</p>"
            "<ul>{% for s in slots %}<li><strong>{{ s.event }}</strong>, {{ s.when }}, {{ s.position }}: "
            "{{ s.status }}, {{ s.reasons }}{% if s.notes %}<br><em>Notes:</em> {{ s.notes }}{% endif %} "
            '<a href="{{ s.link }}">open</a></li>{% endfor %}</ul>'
        ),
        "variables": ["count", "horizon", "slots"],
    },
    {
        "key": "captain.no_show",
        "subject": "Not checked in: {{ names }}, {{ event.title }}",
        "body_html": '<p>{{ minutes }} minutes into {{ when }}, {{ position }}, these confirmed people have not checked in: {{ names }}.</p><p><a href="{{ link }}">Open the slot</a></p>',
        "variables": ["names", "event.title", "minutes", "when", "position", "link"],
    },
    {
        "key": "digest.weekly",
        "subject": "{{ club.short_name }} this fortnight: {{ events|length }} event(s), {{ open_slots }} open slot(s)",
        "body_html": (
            "<p>Hello {{ user.display_first }}.</p>"
            "{% if events %}<h2>Coming up</h2><ul>{% for e in events %}<li><strong>{{ e.title }}</strong>, {{ e.when }}: "
            '{{ e.open }} open, {{ e.needs }} needing someone <a href="{{ e.link }}">roster</a></li>{% endfor %}</ul>'
            "{% else %}<p>Nothing published for the next two weeks.</p>{% endif %}"
            "{% if mine %}<h2>Your slots</h2><ul>{% for m in mine %}<li>{{ m }}</li>{% endfor %}</ul>{% endif %}"
        ),
        "variables": ["user.display_first", "events", "open_slots", "mine"],
    },
    {
        "key": "event.published",
        "subject": "New on the calendar: {{ event.title }}",
        "body_html": '<p>{{ event.title }} is published{% if when %}, {{ when }}{% endif %}. Roles open on the schedule the captains set; have a look at the roster.</p><p><a href="{{ link }}">Open the roster</a></p>',
        "variables": ["event.title", "when", "link"],
    },
    {
        "key": "captain.role_changed",
        "subject": "Role change inside the cutoff: {{ person }}, {{ when }}, {{ event.title }}",
        "body_html": '<p>{{ person }} changed from {{ old_role }} to {{ new_role }} in {{ event.title }}, {{ when }}, {{ position }}, inside the {{ cutoff }}-hour cutoff.{% if broken %} The slot now reads <strong>{{ broken }}</strong>.{% endif %}</p><p><a href="{{ link }}">Open the slot</a></p>',
        "variables": [
            "person",
            "old_role",
            "new_role",
            "event.title",
            "when",
            "position",
            "cutoff",
            "broken",
            "link",
        ],
    },
    {
        "key": "opening.announced",
        "subject": "{{ role|capfirst }} slots now open: {{ event.title }}",
        "body_html": '<p>{{ role|capfirst }} sign-ups for {{ event.title }} are open to you as of now. Pick your hours on the roster.</p><p><a href="{{ link }}">Open the roster</a></p>',
        "variables": ["role", "event.title", "link"],
    },
    {
        "key": "waitlist.offer",
        "subject": "A {{ role }} place opened: {{ event.title }}, {{ when }}",
        "body_html": (
            "<p>You were waiting for a {{ role }} place in {{ event.title }}, {{ when }}, "
            "{{ position }}. One has opened and it is yours until {{ expires|date:'j M H:i' }} UTC.</p>"
            '<p><a href="{{ link }}">Take it</a>; after that it passes to the next person.</p>'
        ),
        "variables": ["role", "event.title", "when", "position", "expires", "link"],
    },
    {
        "key": "license.expiring",
        "subject": "Your license {{ callsign }} expires in {{ days }} days",
        "body_html": (
            "<p>{{ user.display_first }}, the FCC shows your {{ license_class }} license {{ callsign }} "
            "expiring on {{ expiry|date:'j F Y' }}. Renew through the FCC's licensing system; the "
            "roster needs a valid license for the slots you operate.</p>"
        ),
        "variables": ["user.display_first", "callsign", "license_class", "expiry", "days"],
    },
    {
        "key": "license.expired",
        "subject": "Your license {{ callsign }} has expired",
        "body_html": (
            "<p>{{ user.display_first }}, the FCC shows your license {{ callsign }} expired on "
            "{{ expiry|date:'j F Y' }}. Until it is renewed the roster treats you as unlicensed; "
            "the grace period for renewal is the FCC's, not the club's.</p>"
        ),
        "variables": ["user.display_first", "callsign", "expiry"],
    },
    {
        "key": "agreement.expiring",
        "subject": "Your {{ club.short_name }} access agreements expire {{ expires|date:'j F' }}",
        "body_html": "<p>{{ user.display_first }}, these agreements of yours expire on {{ expires|date:'j F Y' }}:</p><ul>{% for t in titles %}<li>{{ t }}</li>{% endfor %}</ul><p>Sign in and re-sign all of them in one visit, so your station and computer access carries on without a gap: <a href=\"{{ link }}\">Open Agreements</a></p>",
        "variables": ["user.display_first", "expires", "titles", "link"],
    },
    {
        "key": "agreement.expired_notice",
        "subject": "Your {{ club.short_name }} access agreements expired today",
        "body_html": "<p>{{ user.display_first }}, these agreements expired on {{ expires|date:'j F Y' }} and no longer satisfy a slot's requirements:</p><ul>{% for t in titles %}<li>{{ t }}</li>{% endfor %}</ul><p>Re-sign them here: <a href=\"{{ link }}\">Open Agreements</a></p>",
        "variables": ["user.display_first", "expires", "titles", "link"],
    },
    {
        "key": "agreement.expiry_summary",
        "subject": "{{ count }} member(s) with agreements {% if expired %}expired today{% else %}expiring {{ expires|date:'j F' }}{% endif %}",
        "body_html": "<p>{% if expired %}These members' agreements expired today{% else %}These members' agreements expire on {{ expires|date:'j F Y' }}{% endif %}; the re-sign queue on Approvals is built to be worked through in bulk:</p><ul>{% for m in members %}<li>{{ m }}</li>{% endfor %}</ul><p><a href=\"{{ link }}\">Open Access rosters</a></p>",
        "variables": ["count", "expired", "expires", "members", "link"],
    },
    {
        "key": "agreement.revoked",
        "subject": "Revoked: {{ title }}",
        "body_html": '<p>Your approval for <em>{{ title }}</em> was revoked by {{ approver }}.{% if reason %} Reason: {{ reason }}{% endif %} Slots that depended on it are flagged; you can sign again once the reason is addressed: <a href="{{ link }}">Open Agreements</a></p>',
        "variables": ["title", "approver", "reason", "link", "user.display_first"],
    },
    {
        "key": "password.rotated",
        "subject": "The {{ club.short_name }} station computer password has changed",
        "body_html": "<p>{{ user.display_first }}, a new password for the shared station computer account is in effect from {{ effective|date:'j F Y' }}. View it in the application after re-entering your own password; it is never sent by email: <a href=\"{{ link }}\">View the password</a></p>",
        "variables": ["user.display_first", "effective", "link"],
    },
    {
        "key": "password.rotation_summary",
        "subject": "Computer password rotated: {{ notified }} told, {{ cut_off }} former holder(s) cut off",
        "body_html": (
            "<p>The shared computer password was rotated, effective {{ effective|date:'j F Y' }}. "
            "{{ notified }} member(s) with current computer access were told.</p>"
            "{% if former %}<p>These people viewed the previous password and no longer hold computer access; "
            "the rotation cuts them off: </p><ul>{% for f in former %}<li>{{ f }}</li>{% endfor %}</ul>{% endif %}"
        ),
        "variables": ["effective", "notified", "cut_off", "former"],
    },
    {
        "key": "account.closure_requested",
        "subject": "{{ person.full_name }} asked to close their account",
        "body_html": (
            "<p>{{ person.full_name }}{% if person.callsign %} {{ person.callsign }}{% endif %} asked to close their "
            "account. It has no access now, and their record is kept as the club's own. Nothing else "
            "is needed unless you want to archive it, or to delete it outright from their page.</p>"
        ),
        "variables": ["person.full_name", "person.callsign"],
    },
    {
        "key": "guardian.converted",
        "subject": "{{ minor.full_name }}'s account is now their own",
        "body_html": (
            "<p>A faculty advisor has converted {{ minor.full_name }}'s account to an adult's. Your "
            "guardian link has ended and is kept in the club's records; from now on messages go to "
            "{{ minor.display_first }} directly, and they manage their own account and sign-ups. "
            "The advisor is passing them a one-time password to set their own.</p>"
        ),
        "variables": ["minor.full_name", "minor.display_first"],
    },
    {
        "key": "account.converted",
        "subject": "Your account is now your own",
        "body_html": (
            "<p>{{ advisor.full_name }} has converted your account to an adult's: your guardian no "
            "longer acts for you, messages come to you directly, and you sign yourself up for "
            "slots. You will receive a one-time password from the advisor; sign in with it and set "
            "your own. As an adult member you can now sign the club's access agreements from "
            "<strong>Agreements</strong>.</p>"
        ),
        "variables": ["advisor.full_name", "user.display_first"],
    },
    {
        "key": "account.verify_address",
        "subject": "Confirm {{ address }} for {{ club.short_name }}",
        "body_html": (
            "<p>{{ address }} is listed on your {{ club.short_name }} account. Confirm it and you "
            "can sign in with it:</p>"
            '<p><a href="{{ link }}">Confirm this address</a></p>'
            "<p>Until you do, club email still comes to it; it simply does not sign you in. If you "
            "did not add it, ignore this message and tell a club officer.</p>"
        ),
        "variables": ["address", "link", "club.short_name"],
    },
]

# What each message is, and who gets it, for the templates page. The page listed the keys
# ("slot.cancelled") and nothing else, which named the code rather than the message.
TEMPLATE_WORDS: dict[str, tuple[str, str]] = {
    "invitation": ("Invitation to join", "the person being invited"),
    "account.verify_member": ("Confirm your address", "a new member"),
    "account.verify_provisional": (
        "Confirm your address (provisional)",
        "somebody who joined through a community link",
    ),
    "account.provisional_notice": ("Somebody is waiting for review", "the officers"),
    "account.admitted": ("Admitted as a member", "the person admitted"),
    "account.declined": ("Not admitted", "the person who was declined"),
    "account.address_in_use": ("That address is already on an account", "whoever tried to use it"),
    "account.completed": ("Somebody finished joining", "the officers and whoever invited them"),
    "account.welcome": ("Welcome", "the new member"),
    "agreement.submitted": ("An agreement is waiting for approval", "the faculty advisors"),
    "agreement.approved": ("Agreement approved", "the member who signed it"),
    "agreement.declined": ("Agreement not approved", "the member who signed it"),
    "signup.removed": ("A captain removed your sign-up", "the member removed"),
    "signup.assigned": ("A captain signed you up", "the member signed up"),
    "slot.cancelled": ("A slot was canceled", "everybody in the slot"),
    "event.cancelled": ("An event was canceled", "everybody signed up for it"),
    "captain.member_cancelled": ("Somebody gave up a slot", "the captains"),
    "captain.access_removed": ("Somebody lost access", "the captains of events they were in"),
    "reminder": ("Your slot is tomorrow", "the member holding the slot"),
    "warning.person": ("Your slot is short of people", "the members in the slot"),
    "warning.captains": ("Slots at risk", "the captains"),
    "captain.no_show": ("Somebody did not check in", "the captains"),
    "digest.weekly": ("The fortnightly digest", "every member"),
    "event.published": ("A new event is on the calendar", "every member"),
    "captain.role_changed": ("A role changed close to the slot", "the captains"),
    "opening.announced": ("Seats opened in an event", "the members who may take them"),
    "waitlist.offer": ("A place opened for you", "the member at the front of the waitlist"),
    "license.expiring": ("Your license expires soon", "the license holder"),
    "license.expired": ("Your license has expired", "the license holder"),
    "agreement.expiring": ("Your access agreements expire soon", "the agreement holder"),
    "agreement.expired_notice": ("Your access agreements have expired", "the agreement holder"),
    "agreement.expiry_summary": ("Agreements expiring", "the faculty advisors"),
    "agreement.revoked": ("An approval was revoked", "the member who held it"),
    "password.rotated": (
        "The station computer password changed",
        "everybody who holds computer access",
    ),
    "password.rotation_summary": ("The password rotation ran", "the sysadmins"),
    "account.closure_requested": ("Somebody asked to close their account", "the faculty advisors"),
    "guardian.converted": ("A minor's account is now their own", "the guardians"),
    "account.converted": ("Your account is now your own", "the member who turned 18"),
    "account.verify_address": ("Confirm an address", "whoever added it"),
}


DEFAULTS_BY_KEY = {t["key"]: t for t in DEFAULT_TEMPLATES}
