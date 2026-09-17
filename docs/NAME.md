# The name: ARCOps

**Decided by the faculty advisor, N. A. Frissell (W2NAF), on 2026-09-13.**

| | |
|---|---|
| **Product** | **ARCOps**, for *Amateur Radio Club Operations*. Spelled out in full wherever the name is first met (README, this file, the footer, the repository description): the advisor's standing rule for acronyms (2026-09-16) |
| **Repository** | `github.com/w3usr/arcops` (renamed from `ops.w3usr.org` the same day; GitHub redirects the old name) |
| **Attribution** | Every installation's footer reads *Powered by ARCOps, free software from W3USR*, linking to the repository. This is the software's credit, shown on other clubs' installations too; it is set in `apps/ops/branding.py`, the one file in the code allowed to name W3USR. |
| **Feature name** | **Sked**: the schedule and roster inside the application. "Sked" is amateur-radio slang for a scheduled contact, so members read it at once. It is a feature name only, never a hostname. |
| **Hostname** | The W3USR installation stays at `ops.w3usr.org`. Another club chooses its own. |

## How it was chosen

The advisor's first proposal, verbatim:

> I'm thinking we should brand this software with a name... how about "W3USR ClubOps"? every
> page can have a footer that points back to our github repo saying "Powered by W3USR ClubOps",
> even non-W3USR installation. i realize this may involve renaming repository, but that is ok.
> what do you think? are there any collisions in the software namespace I need to worry about?

The collision check (2026-09-13) against GitHub repositories and organizations, PyPI, npm, the
web, and domain registrations:

| Candidate | Finding |
|---|---|
| ClubOps | A commercial sports-club management app of that name (TransactBox, UK; App Store and Google Play; its terms assert trademark rights), plus a golf-maintenance product, a WordPress facility platform, and a poker-club product. GitHub organizations `clubops` and `club-ops` taken; 15+ repositories. **Rejected**: the short form would always land on someone else's product in the same category. |
| Sked | Apt, but taken everywhere (GitHub user, PyPI, npm, 30 repositories). Kept as the feature name. |
| OpSked, ShackOps, ClubSked, HamSked | Free everywhere. ClubSked was weighed and set aside because the product is already more than scheduling (credentials, agreements, the shared password, license sync, reports). |
| **ARCOps** | No amateur-radio product uses it. One sound-alike in the community, **arcOS**, a ham Linux distribution: spoken, the names are neighbours; written, they are distinct; the products are unrelated. Unrelated noise elsewhere (GitHub users `arcops` and `arc-ops`, ~17 repositories in cloud, AI, and security; the obvious domains registered). PyPI and npm free. **Chosen**: it names the whole scope and tells another club at a glance that the software is for them. |

The advisor's reasoning on scope, verbatim:

> maybe ClubSked isn't too bad. the thing is what happens when we do things besides just
> scheduling? maybe that is ok?

and on the hostname:

> like the url ops.w3usr.org. if we did sked.w3usr.org, that would look like a place you are
> going to schedule a qso

## Rules that follow

- Code and templates never name a club; the club comes from configuration (TR-40). The
  attribution line is the single exception and lives in `branding.py`.
- The product name is `ARCOps` in prose and `arcops` in identifiers, package names, and URLs.
- If a club's installation needs a different attribution (a fork with substantial changes, for
  example), it edits `branding.py`; the GPL requires the original credit to remain in the
  repository's `NOTICE` regardless.
