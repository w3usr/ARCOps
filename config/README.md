# Club configuration and generic defaults

This directory is what makes the application **usable by any club out of the box**, and what a
club replaces to make it its own. The code never names a club; everything club-specific comes
from here or from an overlay directory laid over it at deploy time (TR-40 and TR-41 in
[`../docs/TECHNICAL_REQUIREMENTS.md`](../docs/TECHNICAL_REQUIREMENTS.md)).

```
config/
|-- README.md
|-- club.example.yaml         <- every configuration key, with generic values; the seed
|-- assets/                   <- a neutral logo and icons that work on day one
|   `-- club-logo.svg
`-- agreements/               <- EXAMPLE agreement templates, to be reviewed before use
    |-- station-access.example.html
    `-- it-access.example.html
```

## Two ways to make it yours

**Fork and edit** (another club): copy `club.example.yaml` to `club.yaml`, fill in your
values, replace the files in `assets/` and `agreements/` with your own, commit to your fork.
`manage.py club_import config/` loads them. Nothing else in the repository needs to change.

**Overlay** (how W3USR deploys): keep this repository unmodified and point the deploy at a
directory with the same layout (`club.yaml`, `static/club/…`, `agreements/…`) held elsewhere.
The application reads the overlay first and these defaults second. W3USR's overlay lives in
the club's private orchestration repository because its agreement texts carry the University's
seal and are the club's documents; the mechanism is the same for anyone.

## About the example agreements

`agreements/*.example.html` are **illustrations of the form** a station-access or computer-use
agreement takes, written so that the application demonstrates the signing, approval, and
expiry flow (FR-21 to FR-30) with realistic content. They are not legal advice and were not
reviewed by any institution's counsel. A club adopting the application replaces them with
agreements its own advisor or institution has approved. The application shows a banner on any
agreement whose template key still ends in `.example` so this cannot be forgotten.

## The rule the build enforces

CI greps `apps/`, `templates/`, and `static/` for the string `w3usr` (case-insensitive) and
fails if it finds one. A club-specific string in code is a portability bug; it belongs in
`club.yaml` or an overlay. (`web/`, the pre-application holding page, is exempt and is
retired when the application serves the root.)
