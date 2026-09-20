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

| Style | Use |
|---|---|
| Solid | The one action that commits the form. One per form. |
| Outline (`.secondary`) | Adds a row, navigates, or commits a small side form. |
| Link (`.linklike`) | An action on one row of a list or table. |

If a page seems to need two solid buttons, it is two forms, or one of them is not the primary
action. The safe choice comes first in the source order, so the keyboard reaches it first.

A page drawn by a library takes the same controls. The sign-in library renders its own
two-step-verification, passkey and Confirm Access pages, and its shipped controls carry no
styling at all, so two of them in a row read as one underlined phrase. Its button element is
overridden once, in `templates/allauth/elements/button.html`, which maps the tags the library
passes onto the three styles above; nothing on those pages is styled page by page.

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

## Destructive actions

Three tiers, and the friction matches what is lost. (After GitLab's Pajamas and the VA design
system, both of which say the same thing.)

1. **Reversible** (close a slot, archive a member): an ordinary control. No confirmation.
2. **Irreversible, but an officer can put it back** (remove somebody's sign-up, decline an
   agreement): a red link, and a confirmation page that names who is affected and what they
   are told. Destructive controls carry `.danger` and are underlined, because color alone
   never carries meaning (FR-62).
3. **Irreversible and unrecoverable** (cancel slots, replace the slot grid, delete an account):
   a solid red button, and a confirmation page that names what is lost, how many people hear
   about it, and offers the safe option first.

A destructive control never sits between two reversible ones styled the same way.

## Forms

- Label, then input, then one line of help, then the error. In that order.
- A form that comes back with an error comes back with **everything the person typed**. A view
  that validates and redirects throws their work away; render the bound form instead.
- Nothing is saved when part of the form is wrong. Half-saving is worse than not saving,
  because the person cannot tell which half.
- Mark required fields. Put the error beside its field, and mark the field itself.
- A form with a text field and two submit buttons submits the **first** one when somebody
  presses Enter. If that button is the dangerous one, split the form in two.

## Tables

Every `<td>` carries `data-label` with its column's name, because under 40rem the header row is
taken off screen and the label is what replaces it. A table with a header row and no
`data-label` loses its meaning entirely on a phone.

Every table stacks there. Letting a wide one keep its shape and scroll sideways inside a
wrapper was tried, and it pushed the whole page sideways at 390px, which FR-95 forbids.

## Feedback

Four levels, each with a word as well as a tint: **Done** (success), **Note** (info),
**Careful** (warning), **Problem** (error). The list of messages is focused when the page
loads, because a live region that is already there when the page arrives announces nothing.

A standing fact ("you are acting for a member under 18") is a banner, not a flash message. A
flash message is something that just happened.

**Say nothing when the page already says it.** "Successfully signed in as Kay Craigie" above a
page headed "Hello, Kay", with the account named in the sidebar, tells the reader what they can
see. Worse, it costs more than nothing: a bar that usually carries noise is a bar people learn
to skim, and the warnings share it. Confirm an action when its result is **not** visible (a
password changed, mail sent, a setting saved) and stay quiet when it is.

## Checking the work

`tools/check.sh` runs all of it in about two minutes:

- `pytest apps` — the permission matrix is the guard that no gate moved.
- `pytest tools/a11y` — axe across eight roles at 1280px and 390px, serious and critical.
- `tools/check_interface.sh` — the rules above that a grep can see.
- `tools/check_club_neutral.sh`, `tools/check_no_requirement_ids.sh` — no club name in code, no
  FR- or TR- numbers in the interface.
