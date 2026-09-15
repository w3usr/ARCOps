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
]

DEFAULTS_BY_KEY = {t["key"]: t for t in DEFAULT_TEMPLATES}
