# The interface

How a page in ARCOps reads and behaves. One file, so a page written next semester matches the
ones written this one.

The application was built requirement by requirement, and for a while nothing said how a page
should read. The result was an interface that showed the shape of the code: a level offered as
"Faculty Advisor · 16 capabilities", where the number was a row count from a database table; a
heading reading "Where we write, and how you sign in" where "Email" would do. The advisor's
verdict on 2026-09-17 was "no self-respecting UI would do that", and he was right.

These rules exist so that judgment does not have to be made again from scratch on every page.

## Words

**American English.** Color, license, canceled, organization, authorize, gray. The exception is
an identifier: a database column, a state key, an audit action, or an HTML attribute keeps the
spelling it was created with, because changing it is a migration and not a proofread.

**Headings are plain nouns.** "Email", not "Where we write, and how you sign in". "Guardians",
not "The adults who can act for you". The heading names the thing; the sentence under it, if
one is needed at all, explains it.

**Nothing from inside the program reaches a page.** No counts of database rows, no dotted
setting keys, no enum values, no state names, no Python `timedelta` strings, no file format
names. A role stored as `operator` reaches the reader as its configured label. A level is
described by what it lets you do, never by how many permissions it holds.

**One sentence of help, under the field it helps.** Not a paragraph, not a `title=` attribute.
A `title` is invisible on a phone, invisible to the keyboard, and unreliable to a screen
reader, so it is never the only place something is explained.

**Say what happens, not what the code does.** "Everyone in the slot is told" beats "sends
notifications to signups".

## Controls

**Everything that does something is a button that looks like one** (SK, 2026-11-06, #221: D2,
D3, D6). Underlined words read as text, and a reader should never have to scrub the screen to find
what can be clicked (Nielsen Norman Group). The vocabulary is shadcn/ui's, written into `app.css`
by hand; the library itself is React and is not used.

| Style | Class | Use |
|---|---|---|
| Primary | a plain `button` | The one action that commits the form, in the club's color. One per form. |
| Secondary | `.secondary` | Neutral, outlined: adds a row, navigates, opens a dialog, commits a small side form. |
| Ghost | `.ghost` | No border until the pointer is over it: a quiet action in a toolbar or a panel's header. |
| Destructive, recoverable | `.ghost.danger` | Red, with a bin: tier 2 below. |
| Destructive, in a Danger zone | `.danger-outline` | Red outline: opens the confirmation of a tier 3 act. |
| Destructive, final | `.danger` | Solid red: the confirming button inside a tier 3 confirmation. |
| Link | `.linklike` | An action inside a sentence, where a button would break the line. Rare. |

- **Sizes:** the default, and `.small` for an action on one row of a list or table.
- **A row's actions** are buttons at the end of the row: the frequent act a small button with its
  icon and its word, the rare ones in a ⋮ menu (Menus, below). A row with one act has no menu:
  Approvals' Reverse this decision is a small button on its row (SK, 2026-11-10: "keep the button,
  because a menu holding one item hides it behind an extra tap").
- **Icons** (D6) go before the word: Material Symbols Outlined, weight 400, 24 px, filled in the
  text color, from `apps/ops/templatetags/nav.py` (#145; SK, 2026-11-11). A new one is copied from
  the same set, never drawn by hand, so they stay one family. The word is always there, so an icon is never the only sign.
  The exceptions are the ⋮ that opens a menu and the ? that opens a key: `.icon-only`, named with
  `aria-label`, and the same name shown beside it on hover and focus, drawn by CSS from that
  label. Never a `title`, which a phone and the keyboard never show.
- **The club's color is on one button per form**, the primary. Every other button is neutral
  (D3), so the one that commits is the one that stands out.

If a page seems to need two solid buttons, it is two forms, or one of them is not the primary
action. The safe choice comes first in the source order, so the keyboard reaches it first.

**Restyle, don't rename.** A control that changes look keeps its accessible name and role
(Remove stays "Remove", Generate slots stays a button named "Generate slots"), so the scenario
scripts and the sweep keep finding it. Where an action moves into a ⋮ menu, it keeps its name
there.

## Menus

A ⋮ menu (D7) is a button that opens a `popover` list of buttons and links: plain HTML, opened
by `popovertarget` with no script, closed by Escape or a click outside (technical addendum A10).
The menu sits under its button by CSS anchor positioning; a few lines of `app.js` place it in a
browser older than that. Its entries are the rare acts of the row or page, each with its icon
and its word. A destructive entry is red and opens its confirmation dialog; it never acts at
once. A form inside a menu posts as any form does.

## Links

**A link is underlined where it sits in running text**, because there its color is the only
other sign and color alone never carries meaning (WCAG 1.4.1). **It is not underlined where its
place already says it is a link** (D5): the sidebar, the crumbs, the tabs, the step bar, a name
that leads a table row, a card's title. It underlines under the pointer and on focus, except the
sidebar, the tabs, the steps and the optional steps, which take the state-layer veil instead
(SK, 2026-11-11).

A table row has **one link**, on the thing the row is (a member's name, an event's title); the
row's actions are buttons at its end (#230). A column of underlined names, emails and callsigns
reads as a wall of links.

A page drawn by a library takes the same controls. The sign-in library renders its own
two-step-verification, passkey and Confirm Access pages, and its shipped controls carry no
styling at all, so two of them in a row read as one underlined phrase. Its button element is
overridden once, in `templates/allauth/elements/button.html`, which maps the tags the library
passes onto the styles above; nothing on those pages is styled page by page.

## Reading and editing

A page that shows a person's record **reads**; the controls that change it live on a page of
its own, reached by an **Edit profile** button that appears only for a reader entitled to use
it. The profile, the officer's view of a member, and any public view later are the same page.

> When you click on someone's name, it should take the person to a read-only view of their
> profile page. If they have the permission to edit a profile (such as a member looking at
> their own page, an officer, or a sysadmin), there should be a button to "Edit Profile". This
> will allow for potential public views of profiles, as well as make it more difficult to
> accidentally change information. — NAF, 2026-09-19

Saving returns to the reading page. What decides whether the button is there is
`apps.accounts.account.may_manage`, so the button and the page it opens cannot disagree.

## Refusals

A page the session may not open answers **404**, so that a page nobody may see and a page you
may not see look alike from outside. It is still one of the club's own pages: it says which
level you are acting at, and offers Home and the level page, because the commonest reason for
landing there is your own level.

> When I am on a page that requires a certain permission level, and then I switch to a lower
> level permission. I want to either see a nicely themed permission denied screen, or just be
> redirected back to my home. I don't want a Not Found. — NAF, 2026-09-19

## The installed app

The same pages run in a window with no browser chrome, so the system's status and navigation
bars sit over them rather than beside them. Any edge of the page that meets one pays for it
with `env(safe-area-inset-*)`; in a browser those are zero. A page shorter than the screen is
where this shows first, because its footer lands exactly where the navigation bar is.
A phone that draws its bars over the page may report those insets as zero, so the page is
measured against the viewport it is actually showing rather than the tallest one it could show
with the bars hidden.

The home-screen icon is cropped to whatever shape the launcher uses. An icon offered for that
crop is drawn to the edge of the tile with its mark inside the middle eight tenths; one that is
not gets shrunk onto a tile the launcher draws, with a margin nobody asked for.

## One word for one thing

A word that already means something in the club does not get a second meaning in the interface.
**Access** is what a member signs an agreement for and an advisor approves: the station, the
computer. What the application grants an account is a **permission level**, which is what the
member page, the directory column, its filter and the sysadmin page all call it. The code keeps
its own names (`groups`, `access_groups`), because those are Django's and the reader never sees
them.

**One word for one thing, on every page a member sees, including the ones a dependency draws.**
The club's word for a WebAuthn credential is **passkey**, which is what the FIDO Alliance has
called it since 2023; the sign-in library still says "security key", which now means the
hardware. Where the application draws the page, it says passkey. Where a dependency draws it, the
message catalogue says it for us (TR-45): one small file, no forked markup, deleted whole when
the library catches up.

> And I do want our UI to always say Passkey instead of Security key. — NAF, 2026-09-20

*(This supersedes "a library's own pages keep the library's words", earlier the same day. That
was decided when the only alternative on the table was forking six templates; the catalogue is
the third option, and it reaches the library's mail as well.)* A library's page is still never
**copied** for the sake of a word: copying is for behaviour the library cannot be asked for, such
as offering the passkey on the page that asks rather than behind a link to a second one.

**The account page is "your profile", and "their profile" when it is somebody else's.** Lower
case, both words: it is a description, not a brand. The sidebar item is **Profile** and the
button is **Edit profile**, and prose that names the page some third way sends a reader hunting
the sidebar for words that are not on it. "Profile Management Page", "your account page" and
"their page" were each tried and are each gone (2026-09-22).

A link names the destination the way the destination names itself — and where the reader is
being sent to *do* something, it names the thing to do and carries an anchor, because `/me/` is
the member page and the controls are on `/me/edit/`. "Confirm it on your profile" pointed at
`#addresses` lands on the card with the button on it; "visit your Profile Management Page" lands
them a click short and looking for a heading that does not exist.

## Filters

A filter that can sensibly take two answers takes a set: a disclosure holding a checkbox each,
with the summary naming what is ticked. One panel is open at a time. A drop-down that holds one
answer is for a choice that is genuinely one of a kind.

**An empty panel is a filter that is off**, and it starts empty. A panel that opens with its
boxes already ticked, under a summary reading "Any status", tells the reader two different
things at once.

The exception is a panel whose *unnarrowed* state is itself a narrowing: the members list leaves
the archive out until somebody asks for it, so the Archive panel opens with **Not archived**
ticked and says so in its summary. The tick is honest there, and its absence would not be. The
test is what the page is showing: a tick that describes the list is right, and a tick that only
repeats "everything" is noise.

**Where an act cannot be done yet, a line saying why stands in place of its button** (SK,
2026-11-10, after trying a greyed button on a phone): Publish before the required steps are done
reads "Not ready to publish: Slots is not done yet." where the Publish form would be, and the
steps it names have their Change links beside them. A greyed button reads as broken and its reason
as small print; the line is the thing to read.

## Destructive actions

Three tiers, and the friction matches what is lost. (After GitLab's Pajamas and the VA design
system, both of which say the same thing.)

1. **Reversible** (close a slot, archive a member): an ordinary control. No confirmation.
2. **Irreversible, but an officer can put it back** (remove somebody's sign-up, decline an
   agreement, remove a period): a red ghost button with a bin and its word (`.ghost.danger`,
   SK 2026-11-06, D4), and a confirmation that names who is affected and what they are told
   where anybody is. The bin and the word carry it, because color alone never carries meaning
   (FR-62); it was a red underlined word before.
3. **Irreversible and unrecoverable** (cancel slots, replace the slot grid, delete an account):
   a solid red button, and a confirmation that names what is lost, how many people hear
   about it, and offers the safe option first.

A destructive control never sits between two reversible ones styled the same way.

**A destructive state is not a value in a menu.** Where taking something away has to carry a
reason, the menu grants and a named act removes: the Access drop-down offers the levels and not
"No access", because closing and suspending are what record who decided and why. Once the thing
is gone the menu goes with it, so that editing something else on the same page cannot quietly
put it back.

**Everything that takes an account out of service lives in one place**, the bordered **Danger
zone** at the foot of the page: closing, suspending, archiving, deleting. A member's page had
closing and archiving in a card of their own, above it, which read as ordinary editing (the
advisor, 2026-09-20). Where one of those acts is the step after another, the later one appears
only once the earlier has happened, rather than sitting there refusing.

**Each act in a Danger zone is a row**: its name, one line on what it does, and on the right a
button outlined in red that opens its confirmation. A phone puts the button under the words.

**A confirmation opens in a dialog over the page** (SK, 2026-11-03): its question as the heading
("Delete this account?"), what is lost and who is told, the reason, then the safe choice before
the solid red one, named for what it keeps ("Keep the account", not "Cancel"). The dialog is
written into the page and its button opens it with `commandfor` (TECHNICAL_REQUIREMENTS A9); a
form inside posts as any form does. A confirmation that is a step of a larger form (replacing
the slot grid) stays a page of its own, because it carries what was typed there. A confirmation
is never a click-to-expand in place: it read as a link and opened into the page around it. It
has no ✕: Escape and the safe choice close it, and the safe choice says what closing keeps (SK,
2026-11-10: "no ✕").

## Something more to read

A disclosure (`<details>`) folds away what is read on demand: the agreement's text, what a level
can do, a contest's details, a message in a list. They all look the same: a chevron in the action
color that turns as it opens, and what opens set in under a thin rule. A whole message or
announcement folded into its card keeps the card instead of the rule. A disclosure never holds a
form somebody fills in to change something: that is a button and a dialog. The one exception is
inside a dialog already (the slot's override): a short confirmation may open over a dialog
(canceling a slot from it), but a form to fill in does not open a second one.

## Forms

- Label, then input, then one line of help, then the error. In that order.
- A form that comes back with an error comes back with **everything the person typed**. A view
  that validates and redirects throws their work away; render the bound form instead.
- Nothing is saved when part of the form is wrong. Half-saving is worse than not saving,
  because the person cannot tell which half.
- Mark required fields. Put the error beside its field, and mark the field itself.
- A form with a text field and two submit buttons submits the **first** one when somebody
  presses Enter. If that button is the dangerous one, split the form in two.
- **A field that has a default shows it filled in**, never an empty box with help text saying
  that blank means the default (NAF, 2026-11-12, #272, #277). A small tag beside it says where
  the value comes from while it holds it: **Club default**, or **Same as a slot** for a setup or
  breakdown length, which follows the slot length until typed in. Left as it is, nothing is
  stored and the event **follows** the default, so a later change to the club's setting reaches
  it (SK, 2026-11-12: "Follow"); a value equal to the default is the default. A rule (who may
  sign up, what a slot at a location needs) starts from the rule that applies, ticked as it is.
  `tools/check_interface.sh` rejects help text that says otherwise.

## A page that edits many things

**A page that edits more than a few things is split into steps under one progress bar** (SK,
2026-11-03, #172; it replaced #167's tabs of 2026-11-02). Manage was one page of fourteen sections
and about fifteen forms; it is now Details, Operating periods, Locations, Slots and Publish, with
Sign-up rules and Contest details as optional steps beside them. Tabs and a guide to what to do
next had been two lists of one page, and they drifted apart; one list cannot.

- Each step is a page of its own, at its own address, drawn by the server: a list of links with
  `aria-current="step"` on the one you are on. It works with JavaScript off, and a step can be
  linked to. The page's own address opens on the first required step not done, else the last.
- The bar is a stepper on the canvas (SK, 2026-11-11; it was a strip of square marks in a panel,
  #172 and #233): round marks joined by a thin line. The step you are on is the one filled mark,
  in the club's color, its name bold; a done step is a green outline and check; the next step a
  dark outline with its word bold; a step that cannot be opened yet a dashed mark (not a link).
  Under each name is one word of state (*Done*, *Next*, *To do*, *After Locations*), so color is
  never the only sign. Required steps are numbered; optional ones are not, because they are not a
  sequence.
- The optional steps are chips under the bar, after a muted *Optional* (SK, 2026-11-11): Material
  3's outlined chips, 32 px, `--r-card` corners, the whole chip the link and its state inside it
  (*Contest details: filled in*), a check when the step holds something of its own. The one you
  are on takes the sidebar's soft fill and a bold name.
- Each step ends with **Back to** the step before and **Continue to** the next, both secondary
  buttons with a chevron (#233; Back was a link), Continue left out when the next cannot be
  opened yet.
- Saving a form returns to the step it was on, and a form that comes back with an error comes
  back on its own step, with everything typed (Forms, above).
- **A small form opens in a dialog** (SK, 2026-11-02, #168): a button on the step, and the form in
  a dialog over it. Every dialog keeps a page of its own behind it: the button is a link to that
  page, and htmx opens it in the dialog instead when it can. A refusal comes back inside the
  dialog with everything typed; a save closes it by loading the step, with its message. Focus goes
  into the dialog on opening, to the problem on a refusal, and back to the button on closing.
- **What is read first is read, then edited**: the event's details show as label and value, and
  **Edit details** opens the form. A form with a rich text editor is a page, not a dialog: the
  editor puts its menus on the page body, where a modal dialog would hide them.

## In place, with htmx

htmx changes part of a page without leaving it, and only ever as a shortcut for something the
page already does without it.

- **Every element with an `hx-` attribute keeps its `href` or `action`.** With JavaScript off,
  or before htmx has loaded, the link opens its page and the form posts and redirects as it
  always did.
- The server tells the two apart by the `HX-Request` header and answers htmx with the part of
  the page that changed. A view that does sets `Vary: HX-Request`, so a cache never hands one
  answer to the other.
- No `hx-on` and no `js:` values: the security policy blocks them, and htmx is configured not to
  run them.
- After a swap, focus goes where the reader's attention should be (usually the heading of what
  was replaced), and a flash message is still announced.
- **A step's own forms save in place** (SK, 2026-11-03, #177): on Manage, the forms that change
  the step you are on (Save limits, Save who may sign up, Save contest details, Lock, Unlock,
  Mark completed, and **Remove** on a period, a position, a captain or an opening) carry one set
  of attributes (`templates/events/stages/_in_place.html`). The view still redirects to its
  step; htmx follows it and swaps the step and the bar out of that page, so there is no partial
  template, no `HX-Request` branch, and no history entry (`hx-push-url="false"`). The step's
  message, or its refusal, comes inside the swap, and focus goes to it. Moving between steps,
  Publish, Duplicate, the pages with an editor, and the dialogs are not boosted. The attributes
  go on each form, never on a wrapper, where the dialog links would inherit `hx-select`.

## Color

The club's color marks **the one primary action, links in running text, and where you are**
(the active menu entry, the current tab and step); a control under the pointer takes a veil of its
own color (SK, 2026-11-06, D3; before, every button was the club's color). Everything else is
neutral, never tinted from the club's color (SK, 2026-10-30, #160): a club whose color happens to
be the one a design system ships as its default still looks like itself.

**Three neutral surfaces** (D1, which changes #160's one surface):

| Token | For |
|---|---|
| `--canvas` | The ground of the page, a light grey: what panels stand on. |
| `--panel` | A panel, a card, a dialog, a menu, a field: white in the light theme. |
| `--panel-head` | A panel's header and footer band, the sidebar, a table's header row. |

- **A state is a word with a colored edge or a colored word**, not a club-tinted fill: an info
  message and a banner take a neutral tint, with the club's color on the icon and the word (SK,
  2026-11-11); an **Open** tag and an open slot take it on the word. Where you are takes it as the navigation draws it: the
  sidebar's and an optional step's soft fill, the current tab's indicator, the current step's
  filled mark (SK, 2026-11-11).
- **A state badge** (`.tag`, #226) is a word on a tint of its status color: `--ok`, `--warn`,
  `--bad`, the club's color for information, neutral otherwise. Always a word.
- **An unread message keeps its dot**, not a badge (SK, 2026-11-10: "keep the dot, since a badge
  on every unread row is noisy and the dot is the familiar convention. A screen reader is told in
  words either way"). The dot is drawn by CSS and kept from a screen reader, which hears a hidden
  "Unread:" before the subject.
- **One panel is the club's color**: the sign-in page's, the page that introduces the club.

## Type

One family, served from this site: **Atkinson Hyperlegible Next**, in two weights, Regular
(400) and Bold (700). It was chosen for what this application prints most: callsigns and times
(SK, 2026-10-30, #160).

- **Its zero is slashed.** N0CAN, KD0OOO and WB0LIL read one way only; in the system faces a
  zero and a capital O are nearly the same shape. Its I, l and 1 also differ, where the system
  faces draw I and l as the same bar.
- **Numbers that are compared line up.** The face's own figures are proportional, so times and
  tables carry `font-variant-numeric: tabular-nums` and every digit is the same width. Running
  text keeps the proportional figures.
- **Two weights, no more:** 400 and 700. Labels are 400; headings, names that lead a row, and a
  button's words are 700.
- **Five sizes, no more** (SK, 2026-10-30), each a token in `app.css`:

  | Token | Size | For |
  |---|---|---|
  | `--t-small` | 14 px | tags, badges, help, errors, legends, table headers, a roster's second lines |
  | `--t-body` | 16 px | everything read as text |
  | `--t-lede` | 18 px | `h3`, a page's opening line, an event's time, a card's title |
  | `--t-h2` | 20 px | `h2`, the slot dialog's heading, a password shown to be copied |
  | `--t-h1` | 30 px | `h1`, the sign-in page's callsign |

  Something that seems to need a sixth size usually needs a different structure instead.
  Nothing is set in capitals to look like a label: a group in the sidebar is named in small
  bold words, as written. `tools/check_interface.sh` refuses any other size or weight.

## Shape

**Corners by hierarchy** (SK, 2026-10-30, #160): the smaller and more numerous a thing, the
squarer it is. `tools/check_interface.sh` refuses any other radius.

| Token | Radius | For |
|---|---|---|
| `--r-field` | 4 px | a field, a select, a badge, a slot's state |
| `--r-button` | 6 px | a button, a menu entry, a switch, a tab's focus ring; never a pill |
| `--r-card` | 8 px | a panel, a card, a message, a banner, a dialog, a menu, a chip (an optional step) |
| `--r-pill` | full | the navigation's entries only: sidebar, rail and drawer (#145) |

**The navigation is Material 3's** (SK, 2026-11-11, #145): a drawer entry 48 px high (M3 says
56; SK chose 48 so a long menu fits) with a 24 px icon and a 14 px label, the rail 80 px wide with
each icon in a 56 by 32 px pill, and the entry for this page in a pill of the club's soft color,
its label bold as well. The pill is the one exception to the corners above, and
`tools/check_interface.sh` allows it there alone.

**A page's parts are panels on the canvas** (SK, 2026-11-06, D1; it replaces #160's sections on
white paper). A panel (`.panel`) is one part of the page with a job: its header names it and holds
its actions (Add location, Generate slots), with one line under the name if one is needed; its
body holds the list, the table or the form; a footer, when there is one, holds a form's save at
the right and a note at the left. A page without parts (a short form, a message) is one panel.

A part with a heading and no actions of its own may stay a **section** (`.section`): since
phase 5 of the redesign it draws as a panel without a header band, white on the canvas, and as a
plain part again when it sits inside a panel or a card.

**The time in UTC is always in sight** (D9): a clock at the top of every signed-in page, drawn by
the server and kept current by a few lines of `app.js`, reading "UTC" so it never passes for local.

**A card is a thing that stands on its own inside a panel or a list**: a message, an
announcement, an agreement, an event in a list, a result to copy (a new link, a new invitation),
the slot's **Captain** controls, the **Danger zone**. A card around a whole page's form frames
nothing; that is a panel.

**The event is a workspace** (D8): one header for the event page, Manage and Who took part (the
title with its state badge, a line of facts with icons, Announce and a ⋮ menu at the right) and
**Roster**, **Manage** and **Who took part** as tabs under it: Material 3's primary tabs (SK,
2026-11-11), 14 px labels at 400, the current one bold with a 3 px indicator in the club's color
under its label; on a phone they share the width without icons. The sidebar marks Events on every
tab. The step bar stays on Manage; it keeps its own state words beside the header's badge.

## Material 3, in our terms

Material 3 is the design approach, written into `app.css` by hand; none of Google's code is
used (technical addendum A8). Its roles, by our names:

| Material 3 | Here |
|---|---|
| primary, on-primary | `--accent`, `--accent-fg`: buttons, links |
| primary container, on-primary container | `--accent-soft`, `--accent-soft-fg`: the active menu entry |
| surface, surface container low, surface container | `--panel`, `--panel-head`, `--canvas`: neutral, never mixed with the club's color |
| outline, outline variant | `--line-strong` (a secondary button's edge), `--line` (a panel's edge, a rule) |
| error | `--bad`; success and warning are ours, `--ok` and `--warn` |
| headline, title, body large, body, body small and label | `--t-h1`, `--t-h2`, `--t-lede`, `--t-body`, `--t-small` (label and body small share it) |
| corner small, medium, large | `--r-field`, `--r-button`, `--r-card` |
| filled, outlined and text buttons | a plain `button`, `.secondary`, `.ghost`; no tonal or elevated buttons |
| state layers | a veil of the control's own text color: 8% under the pointer, 10% focused or pressed; CSS only. Focus also keeps its ring and halo; a link in a line of text underlines instead |

The primary roles are mixed from the club's color with `color-mix(in oklab, …)`, in light and
dark. `apps/ops/config.py` makes the same mixes and refuses a club color under which any text
they carry would read below 4.5:1, falling back to the application's own.

**Where Material 3 and these rules disagree, these win:**
- A message stays in the list at the top of the page and takes focus; no snackbar that
  disappears on a timer (WCAG 2.2.1).
- A destructive action carries a bin or a red outline and its word, never color alone (FR-62).
- One solid button per form.
- No ripple: it needs JavaScript, and every page works without it.
- No pill buttons, and surfaces are not tinted from the club's color (#160, D1). The
  navigation's entries are the one pill (#145).

## Tables

Every `<td>` carries `data-label` with its column's name, because under 40rem the header row is
taken off screen and the label is what replaces it. A table with a header row and no
`data-label` loses its meaning entirely on a phone.

Every table stacks there. Letting a wide one keep its shape and scroll sideways inside a
wrapper was tried, and it pushed the whole page sideways at 390px, which FR-95 forbids.

## Feedback

Four levels, each with a word as well as a tint: **Done** (success), **Note** (info),
**Careful** (warning), **Problem** (error). Drawn in Material 3's tonal style (SK, 2026-11-11; they
had a thick colored left edge and an outline): the level's tint and no border, its icon at the start
(check, info, warning, error, Material Symbols drawn by CSS) and its word in the level's color.
Note's tint is neutral, since the club's soft fill means where you are. A banner is drawn the same
way: a Note, except a draft and viewing as somebody else, which are Careful; so is the generator's
estimate of what it will make, a Note. In forced colors all three keep an outline. The list of messages is focused when the page
loads, because a live region that is already there when the page arrives announces nothing.

A standing fact ("you are acting for a member under 18") is a banner, not a flash message. A
flash message is something that just happened.

**Say nothing when the page already says it.** "Successfully signed in as Kay Craigie" above a
page with the account named in the sidebar tells the reader what they can see. Worse, it costs more than nothing: a bar that usually carries noise is a bar people learn
to skim, and the warnings share it. Confirm an action when its result is **not** visible (a
password changed, mail sent, a setting saved) and stay quiet when it is.

## Checking the work

**The kit is a page**: `/ops/components/`, for sysadmins, shows every part above drawn by the
same CSS the pages use, each with its one-line contract (#231). A part changes there first.

`tools/check.sh` runs all of it in about two minutes:

- `pytest apps` — the permission matrix is the guard that no gate moved.
- `pytest tools/a11y` — axe across eight roles at 1280px and 390px, serious and critical.
- `tools/check_interface.sh` — the rules above that a grep can see.
- `tools/check_club_neutral.sh`, `tools/check_no_requirement_ids.sh` — no club name in code, no
  FR- or TR- numbers in the interface.
