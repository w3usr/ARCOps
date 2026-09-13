# ARCOps

**Operations software for amateur radio clubs**: scheduling members into operating slots with a
roster that knows who may legally and physically run the station, access agreements with approval
and expiry, the shared station-computer password, FCC license sync, and the reports a club owes
its institution. Free software (GPL-3.0-or-later) from **W3USR**, the amateur radio club of the
University of Scranton, whose installation runs at **https://ops.w3usr.org**. Any club can run it:
see [`config/README.md`](config/README.md). The name is explained in [`docs/NAME.md`](docs/NAME.md).

> **Status: first build, 2026-09-13.** A Django application on the decided stack
> ([`docs/TECHNICAL_REQUIREMENTS.md`](docs/TECHNICAL_REQUIREMENTS.md)) implementing the core
> of [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md): accounts and invitations, credentials and
> agreements, events with slots and a viability-checked roster, check-in, the club overlay.
> Formal adoption of both documents is pending the advisor's read; the build began on his
> instruction.

## Run it locally

```bash
git clone https://github.com/w3usr/arcops.git && cd arcops
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate && python manage.py club_import && python manage.py seed_demo
python manage.py runserver        # http://localhost:8000, sign in as ada@example.org / demo-password-please-change
pytest && ruff check .            # what CI runs
```

No Node, no Docker. Email goes to the console in development. The generic club's configuration
is `config/`; a real club supplies its own (see `config/README.md`).

## Repository layout

```
arcops/
|-- docs/REQUIREMENTS.md      <- functional requirements; start here
|-- docs/TECHNICAL_REQUIREMENTS.md  <- proposed stack and technical decisions
|-- manage.py, config/        <- Django project: settings (base/dev/test/prod), urls; club.example.yaml, assets/, agreements/
|-- apps/                     <- ops, accounts, credentials, events, comms: models, services, views, tests
|-- templates/, static/       <- server-rendered pages, CSS, service worker, manifest
|-- docs/ONBOARDING.md        <- for new club members
|-- web/                      <- what nginx serves today: the holding page
|   |-- index.html
|   |-- favicon.ico
|   `-- assets/
|-- ai/ai_usage_log.md        <- log of every substantive AI-assisted session
|-- .claude/rules/            <- working rules this project follows
|-- LICENSE                   <- GNU GPL v3
`-- NOTICE
```

## Deployment

This repository holds the application (W3USR's installation is at `ops.w3usr.org`). It holds **no credentials, host details, or deploy
configuration**; those live in the club's private orchestration repository, which carries this
repository as a submodule and owns the server setup.

The server deploys by pulling this repository's `main` branch. A push to `main` becomes live
only when someone runs the deployment from the orchestration repo, so `main` should always be
in a state that is safe to serve.

## Contributing

Club members: read [`docs/ONBOARDING.md`](docs/ONBOARDING.md) first. It covers the Generative
AI Use Agreement you sign before using AI tools on club work, and the working loop.

Two rules matter more than the rest:

1. **Never commit a secret to this repository.** It is public. Credentials, tokens, host
   names, and deploy keys belong in the private orchestration repo.
2. **Log every substantive AI-assisted session** in `ai/ai_usage_log.md` before committing.
   The `/commit` workflow does this for you.

Never publish member contact details, student records, or photographs of identifiable people
without permission. Callsigns and names are public in the FCC ULS database and are fine.

## License

Free software under the **GNU General Public License, version 3 or later**. See
[`LICENSE`](LICENSE) for the full text and [`NOTICE`](NOTICE) for copyright and attribution.

The W3USR club seal in `web/assets/` is the club's own artwork, reproduced here with the
club's permission. The University of Scranton's name, seal, and logos are the University's
marks and are not licensed by this repository.

73 de W3USR
