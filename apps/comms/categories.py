"""
Message categories (FR-71).

A member controls the email switch for the categories in CONTROLLED. The categories in MANDATORY
go out regardless, because they change something the member relies on or protect their account
(FR-71: cancellations, moves by others, account security, agreement decisions). The in-application
copy (FR-82) is always kept, whatever the switch says.
"""

CONTROLLED: dict[str, str] = {
    "reminder": "Slot reminders, 24 hours before each slot you hold",
    "warning": "At-risk warnings for slots you hold",
    "opening": "Announcements that a role has opened for sign-up",
    "announcement": "General announcements from officers and captains",
    "digest": "The weekly digest",
    "license_expiry": "Notices that your license is about to expire",
}

MANDATORY: dict[str, str] = {
    "cancellation": "Cancellation of a slot, event, or sign-up you hold",
    "moved": "A sign-up of yours moved, removed, or re-timed by someone else",
    "security": "Account security: password reset, temporary password, sign-in lockout",
    "agreement": "Agreement decisions and expiry",
    "account": "Account messages: invitations, address verification, review decisions",
}

ALL = {**CONTROLLED, **MANDATORY}

# Categories whose unread messages earn a Home banner (FR-108): the ones that would otherwise
# have been a warning email.
BANNER = ("warning", "agreement", "security", "cancellation", "moved")
