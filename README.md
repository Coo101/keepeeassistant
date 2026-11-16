# keepeeassistant

Tool to help you make menus and shopping lists for de chiro.
A summer camp meal planner — see [docs/SPEC.md](docs/SPEC.md) for what it does, with one file per area in [docs/spec/](docs/spec/).

## Setup

```powershell
uv sync   # creates .venv from pyproject.toml and uv.lock
Copy-Item .env.example .env   # then set DJANGO_DEBUG=1 for local development
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo   # optional: demo data + dev admin (admin/admin)
.\.venv\Scripts\python.exe manage.py runserver 8100
```

Dependencies are pinned in `pyproject.toml`. After changing one, regenerate the files
that Docker and CI install from (a test checks they match):

```powershell
uv lock
uv export --no-dev --no-hashes --no-emit-project -o requirements.txt
uv export --only-dev --no-hashes --no-emit-project -o requirements-dev.txt
```

In PyCharm, use the shared **Dev server** run configuration (`.run/`), which
runs the same command. Then open http://localhost:8100/. Chiros, staff and news are managed in the
[admin](http://localhost:8100/admin/); everything else has its own pages.

## Access

The home page, news and docs are public. Every other page needs a login, enforced by
Django's `LoginRequiredMiddleware`, so a new page is private by default. Mark a public page
with `login_not_required`.

- **Accounts** are by invitation: a Chiro's admins invite from the Chiro's page, and staff
  from the admin. Anyone can request access at `/join/`, and staff approve in the admin. Log in
  with a username or email address. Failed logins are rate limited.
- **Camps** belong to a Chiro. Only its members can see or change them, and staff get no
  exception outside the admin. Only a Chiro's admins can delete a camp.
- **Recipes** are shared between all accounts, who can read them and save a renamed copy.
  The author chooses whether others can edit. While another Chiro has a current camp planning
  a recipe, only staff can change it.
- **Ingredients** are shared. Anyone can add one and add prices. The name and unit are fixed
  after creation, except for staff.

Create the first administrator with:

```bash
docker compose exec web python manage.py createsuperuser
```

Mails only print to the log until `EMAIL_HOST` is set. See `.env.example` for all settings,
including those for running behind a proxy.

## Features

- **Recipes and ingredients**, with dish types, units (piece/kg/liter) and ordered steps.
- **Camps**: dates, headcount (children x0.7 / teens / staff), meal times, archive.
- **Menu planner**: day x meal grid, with warnings for diets, allergies and balance.
- **Shopping lists**: one per trip and shop, minus what's in the Chiro's pantry. Uncovered
  days are flagged.
- **Budget**: uses a camp's own price if it has one, otherwise the latest price.
- **Bills**: upload PDFs and photos, review the lines, set camp prices and compare what you
  paid with the estimate. Text PDFs are read in Python. Scans and photos wait for an Ollama
  vision model, through `manage.py read_bills --loop` (the `bill-reader` service in
  `docker-compose.yml`).
- **Kitchen utilities and pantry**: a stock per Chiro (pots, fire pits, and food
  already there) and what each camp needs; what's missing goes on the shopping lists,
  and bought utilities on a bill can be added to the stock.
- **Financial report**: per camp, the cost of every planned meal from the bills, after
  checking that every planned ingredient is on one. Personal costs are listed apart.
- **Example camp**: `manage.py create_example_camp` makes a read-only camp from the
  existing recipes, which every account can look at.
- **PDF export**: camp overview, draaiboek, recipes and shopping lists through WeasyPrint.
- **Public site**: home page, news (written in the admin) and docs (`pages/content/`).
- **Dutch and English**: Dutch by default, English when the browser asks for it. The
  NL/EN switch in the header remembers the choice in a cookie.

See [docs/SPEC.md](docs/SPEC.md) and the area files in [docs/spec/](docs/spec/) for the details, and the roadmap in [docs/TODO.md](docs/TODO.md) for what's open. Designs and plans for changes are in `docs/superpowers/`.

### PDF export on Windows

WeasyPrint needs the GTK/Pango native libraries. Without them the app serves
the same documents as print-friendly HTML (use the browser's Print → Save as
PDF). To get native PDF output, install the
[GTK3 runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
and restart the server.

## Docker

This compose file builds the production image for a local check with
Docker Desktop; production itself is deployed by CI (see below).

```bash
docker compose up -d --build
```

Then open http://localhost:8010/. The SQLite database lives on the named
volume `campdata` (mounted at `/data`), so it survives rebuilds and
restarts. Migrations run automatically at container start, and the image
includes the Pango libraries, so PDF export works natively.

Secrets live in a git-ignored `.env` file (loaded by both Django via
python-dotenv and docker compose). First time: copy
[.env.example](.env.example) to `.env`, generate a `DJANGO_SECRET_KEY`,
and put your host's name/IP in `DJANGO_ALLOWED_HOSTS` (plus
`DJANGO_CSRF_TRUSTED_ORIGINS` when serving via a domain/proxy).

`DJANGO_DEBUG` is **off** unless explicitly enabled, and without a
`DJANGO_SECRET_KEY` the app refuses to start rather than falling back to a
key that is public in this repo. So a missing or incomplete `.env` fails
loudly at startup instead of quietly running an insecure instance. Compose
pins `DJANGO_DEBUG=0` for the container even if your local `.env` turns it
on for development.

First-time setup inside the container:

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py import_kamp_recipes   # load the recipe library
```

Or copy an existing local database into the volume instead:

```bash
docker compose cp db.sqlite3 web:/data/db.sqlite3 && docker compose restart web
```

## Branches and deployment

- Every change gets its own branch from `dev` (`ui/area-2-recipes`,
  `feature/kitchen-mode`, `fix/...`) and a pull request into `dev`; run `dev` locally
  from PyCharm. `dev` goes into `main` through a PR `dev` → `main`, merged with
  **Fast-forward only**, so `main` and `dev` never drift apart.
- Gitea enforces this: no direct pushes to `dev` or `main`, only `yonick` merges, the
  `test` check must pass, a PR into `main` must come from `dev` (`branch-guard`), and `dev`
  must not be behind `main`.
- Every push and PR runs the tests in Gitea Actions
  ([.gitea/workflows/ci-cd.yml](.gitea/workflows/ci-cd.yml)).
- A push to `main` also builds the image, pushes it to the Gitea registry
  and deploys it to the homelab Docker host. Merging into `main` therefore
  **is** a production release.

The open work is the roadmap in [docs/TODO.md](docs/TODO.md).

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest       # tests (scaling + shopping logic)
.\.venv\Scripts\python.exe -m ruff check . # lint
.\.venv\Scripts\python.exe -m black .      # format
```

### Translations

Write text in English and mark it: `{% translate %}` or `{% blocktranslate %}` in
templates, `gettext_lazy` in models and forms, `gettext` in views. The Dutch is in
`locale/nl/LC_MESSAGES/django.po`; the compiled `django.mo` is committed, so the image
and the dev server need no gettext. A help page gets its Dutch version next to it, as
`pages/content/<slug>.nl.md`.

Windows has no gettext, so update the catalog in a container. This adds new strings to
the `.po` file (fill in their `msgstr`) and compiles it:

```bash
docker run --rm -v "$PWD:/app" -w /app -e DJANGO_DEBUG=1 python:3.13-slim sh -c "apt-get update -qq && apt-get install -y -qq gettext && pip install -q -r requirements.txt && python manage.py makemessages -l nl -e html,txt,py --add-location=file --ignore=.venv --ignore=staticfiles --ignore=media --ignore=tests && msgfmt --check -o locale/nl/LC_MESSAGES/django.mo locale/nl/LC_MESSAGES/django.po"
```
