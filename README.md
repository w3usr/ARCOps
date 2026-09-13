# ops.w3usr.org

Web application to support contests and operations for **W3USR**, the amateur radio club of
the University of Scranton.

Live at **https://ops.w3usr.org**.

> **Status: requirements drafted, nothing built yet.** The site currently serves a holding
> page. What the application will do is in [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md)
> (FR-1 to FR-118, every open question answered, adoption pending). How it will be built is
> proposed in [`docs/TECHNICAL_REQUIREMENTS.md`](docs/TECHNICAL_REQUIREMENTS.md) (TR-1 to
> TR-39), awaiting the advisor's decisions in its section 10.

## Repository layout

```
ops.w3usr.org/
|-- docs/REQUIREMENTS.md      <- functional requirements; start here
|-- docs/TECHNICAL_REQUIREMENTS.md  <- proposed stack and technical decisions
|-- config/                   <- generic club configuration, logo, and example agreements (works out of the box)
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

This repository holds the application. It holds **no credentials, host details, or deploy
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
