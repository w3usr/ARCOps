# Screen-reader walk (FR-117, FR-116)

Before each release a person walks the core member flows with a screen reader and records the
result here. v1 is not released until the walk passes. The automated check (`tools/a11y`, run
by CI on every push) catches what a machine can; this walk catches what it cannot: whether the
page makes sense read aloud, whether the important action comes first, whether a table reads as
a table. If a club member who uses a screen reader is willing, their walk counts for more than
anyone else's (FR-117).

> **Timing (the advisor, 2026-09-16):** "As much as I want screen reader accessibility, testing
> that is going to be a phase 2 or 3 thing. I wanted it built in place so it was thought about
> from the beginning, but I don't have time to test it before our first contest, and our people
> who are sight-impaired are not ready to use this site yet." The automated check runs on every
> push regardless; this walk is scheduled for the club's second or third phase, before members
> who use a screen reader are asked to rely on the site.

## How

- Screen reader: NVDA (Windows, free) or VoiceOver (macOS, iOS). Note which, and the browser.
- Use the seeded demo (`manage.py seed_demo`) or a test account on the installation; never a
  real member's account.
- Keyboard only: no mouse. Tab, Shift+Tab, Enter, Space, arrow keys, and the reader's own
  table and heading navigation.
- For each flow, note **Pass**, **Pass with notes**, or **Fail**, with what was heard when it
  was wrong. A failure becomes an issue with the `bug` and `accessibility` labels.

## The flows

| # | Flow | What must be true |
|---|---|---|
| 1 | Sign in | The email and password fields are announced with their labels; an error is announced; after sign-in the page title says where you are |
| 2 | Find an event | The event list reads as a list with one heading per event; each link's text names the event; the roster's status words (Open, Needs, Covered, Full) are read, not only coloured |
| 3 | Read the roster | The roster is a table: row and column headers are announced for each cell (time, position, who); a slot's dialog opens with focus inside it and closes with Escape, returning focus |
| 4 | Sign up | The role select and note field are labelled; the confirmation message is announced; the new state is read on return |
| 5 | Confirm | From the reminder's link or My schedule: the Confirm button is reachable first in the tab order and its result is announced |
| 6 | Check in | Inside the window, the big Check in button is the first thing after the page heading; one press, result announced |
| 7 | Sign an agreement | The agreement text reads in order with its headings; the typed-name field, the affirmation checkbox, and the Sign button are labelled; the outcome is announced |
| 8 | View the computer password | The reveal control is a button; the revealed password is read once and the copy control is announced |
| 9 | Messages | My messages reads as a list; unread state is read as text; the message body's headings are in order |
| 10 | Rich text (FR-115) | The editor (event description, announcement) is reachable and editable by keyboard; the toolbar is a toolbar with named buttons; the heading-order warning is announced |

## Record

Add a row per walk. Newest first.

| Date | Who | Reader and browser | Release or commit | Result | Notes and issues |
|---|---|---|---|---|---|
| | | | | | *(none yet)* |
