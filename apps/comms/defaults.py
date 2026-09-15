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
        "body_html": (
            "<p>You are invited to join {{ club.name }}'s operations site.</p>"
            '<p>Open this link to create your account: <a href="{{ link }}">{{ link }}</a></p>'
            "<p>The link works once and expires on {{ expires|date:'j F Y' }}.</p>"
            "<p>Questions: {{ club.contact_email }}</p>"
        ),
        "variables": ["club.name", "club.contact_email", "link", "expires", "category"],
    },
    {
        "key": "account.verify_member",
        "subject": "Confirm your address for {{ club.short_name }}",
        "body_html": (
            "<p>Welcome to {{ club.short_name }}. Your account is ready; please confirm this is your "
            "address by opening the link below within {{ days }} days, or sign-in will pause until "
            "you do.</p>"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
        "variables": ["club.short_name", "link", "days", "user.display_first"],
    },
    {
        "key": "account.verify_provisional",
        "subject": "Confirm your address for {{ club.short_name }}",
        "body_html": (
            "<p>Thank you for offering to help {{ club.short_name }}. Open the link below to confirm "
            "your address; your account is created the moment you do, and a club officer will then "
            "review it.</p>"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
        "variables": ["club.short_name", "link", "days"],
    },
    {
        "key": "account.provisional_notice",
        "subject": "New provisional member for {{ club.short_name }}: {{ person.short_name }}",
        "body_html": (
            "<p>{{ person.full_name }}{% if person.callsign %} {{ person.callsign }}{% endif %} joined "
            "through {{ via }} and is waiting for review. Admit them as a member or decline on their "
            "page:</p>"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
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
        "body_html": (
            "<p>{{ person.full_name }}{% if person.callsign %} ({{ person.callsign }}"
            "{% if uls_name %}, ULS name {{ uls_name }}{% endif %}){% endif %} completed the invitation "
            "sent to {{ invited_email }} as {{ category }}.</p>"
            "<p>If that is not who you expected, set the account to No access from their page: "
            '<a href="{{ link }}">{{ link }}</a></p>'
        ),
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
        "body_html": (
            "<p>Your {{ club.short_name }} account is ready, {{ user.display_first }}. Sign in to see "
            "what is coming up, sign the access agreements, and pick your hours.</p>"
            '<p><a href="{{ site_url }}/">{{ site_url }}/</a></p>'
        ),
        "variables": ["club.name", "club.short_name", "user.display_first", "site_url"],
    },
    {
        "key": "agreement.submitted",
        "subject": "Agreement to review: {{ person.full_name }}, {{ title }}",
        "body_html": (
            "<p>{{ person.full_name }}{% if person.callsign %} {{ person.callsign }}{% endif %} signed "
            "<em>{{ title }}</em> and it awaits your approval.</p>"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
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
        "body_html": (
            "<p>Your <em>{{ title }}</em> was not approved.{% if reason %} Reason: {{ reason }}{% endif %}</p>"
            "<p>You can sign it again once the reason is addressed: "
            '<a href="{{ link }}">{{ link }}</a></p>'
        ),
        "variables": ["title", "reason", "link", "user.display_first"],
    },
    {
        "key": "signup.removed",
        "subject": "Your sign-up was removed: {{ event.title }}",
        "body_html": (
            "<p>{{ actor }} removed you from {{ event.title }}, {{ when }}, {{ position }} as {{ role }}."
            "{% if reason %} Reason: {{ reason }}{% endif %}</p>"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
        "variables": ["actor", "event.title", "when", "position", "role", "reason", "link"],
    },
    {
        "key": "signup.assigned",
        "subject": "You were signed up: {{ event.title }}",
        "body_html": (
            "<p>{{ actor }} signed you up for {{ event.title }}, {{ when }}, {{ position }} as {{ role }}. "
            "If that does not work for you, cancel from your schedule and the captains will be told.</p>"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
        "variables": ["actor", "event.title", "when", "position", "role", "link"],
    },
    {
        "key": "slot.cancelled",
        "subject": "Slot cancelled: {{ event.title }}, {{ when }}",
        "body_html": (
            "<p>The slot you held in {{ event.title }}, {{ when }}, {{ position }}, was cancelled by "
            "{{ actor }}.{% if reason %} Reason: {{ reason }}{% endif %}</p>"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
        "variables": ["actor", "event.title", "when", "position", "reason", "link"],
    },
    {
        "key": "event.cancelled",
        "subject": "Event cancelled: {{ event.title }}",
        "body_html": (
            "<p>{{ event.title }} was cancelled by {{ actor }}.{% if reason %} Reason: {{ reason }}{% endif %} "
            "Your sign-ups for it ({{ count }}) are withdrawn.</p>"
        ),
        "variables": ["actor", "event.title", "reason", "count"],
    },
    {
        "key": "captain.member_cancelled",
        "subject": "{% if late %}Late cancellation{% else %}Cancellation{% endif %}: {{ person }} left {{ when }}, {{ event.title }}",
        "body_html": (
            "<p>{{ person }} cancelled their {{ role }} sign-up for {{ event.title }}, {{ when }}, "
            "{{ position }}.{% if late %} This is inside the {{ cutoff }}-hour cutoff.{% endif %}</p>"
            "{% if broken %}<p>The slot is now <strong>{{ broken }}</strong>.</p>{% endif %}"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
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
        "body_html": (
            "<p>{{ person }}'s access was removed by {{ actor }}, so their future sign-ups in "
            "{{ event.title }} were withdrawn: {{ slots }}.</p>"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
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
        "body_html": (
            "<p>The slot you hold in {{ event.title }}, {{ when }}, {{ position }}, reads "
            "<strong>{{ status }}</strong>: {{ reasons }}.</p>"
            "<p>If you know someone who could fill it, ask them to sign up: "
            '<a href="{{ link }}">{{ link }}</a></p>'
        ),
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
        "body_html": (
            "<p>{{ minutes }} minutes into {{ when }}, {{ position }}, these confirmed people have not "
            "checked in: {{ names }}.</p>"
            '<p><a href="{{ link }}">{{ link }}</a></p>'
        ),
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
]

DEFAULTS_BY_KEY = {t["key"]: t for t in DEFAULT_TEMPLATES}
