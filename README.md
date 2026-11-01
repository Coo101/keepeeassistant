# keepeeassistant

Tool to help you make menus and shopping lists for de chiro.
A summer camp meal planner — see [docs/SPEC.md](docs/SPEC.md) for the full specification.

## Setup

```powershell
uv sync   # creates .venv from pyproject.toml and uv.lock
Copy-Item .env.example .env   # then set DJANGO_DEBUG=1 for local development
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo   # optional: demo data + dev admin (admin/admin)
.\.venv\Scripts\python.exe manage.py runserver 8100
```

In PyCharm, use the shared **Dev server** run configuration (`.run/`), which
runs the same command. Then open http://localhost:8100/ — recipes, ingredients and camps are managed in
the [admin](http://localhost:8100/admin/); menu planning and shopping lists have
their own pages.

## Access

Browsing is open to everyone on the network — recipes, menu plans, the
runbook and shopping lists can be read without logging in, so a shared
tablet in the kitchen needs no password. **Changing** anything (menu
slots, day notes, shopping days, and the admin) requires a login. So does
reading the runbook's contact details: the kookploeg, location, contacts,
bakery and general notes are left out of the page and PDF for anonymous
visitors.

This is enforced by HTTP method in
[core/middleware.py](core/middleware.py): any non-GET request from an
anonymous visitor is redirected to the login page, so a new form added
later is protected automatically. Sessions last 30 days and refresh on
use, so each device logs in once per camp.

Create accounts for the kookploeg with:

```bash
docker compose exec web python manage.py createsuperuser
```

Use `createsuperuser` only for people who should also reach `/admin/`;
for planners who only edit menus, add a normal user in the admin. Set
`DJANGO_SECURE_COOKIES=1` in `.env` when serving over HTTPS.

## Features (v1)

- **Recipe library** — recipes with dish types, ingredients (piece/kg/liter),
  ordered steps with durations; managed in the Django admin.
- **Camps** — dates, headcount (children x0.7 / teens / staff), meal times.
- **Menu planner** — day x meal grid; each slot only offers recipes of the
  right dish type; shows quantities scaled to the camp's portions.
- **Shopping lists** — pick shopping days; one aggregated, category-grouped
  list per trip (a trip buys for the days *after* it, up to the next trip);
  uncovered days are flagged.
- **PDF export** — camp overview and shopping lists via WeasyPrint.
- **Budgeting** — per-camp cost estimate (`/camps/<id>/budget/`) from
  ingredient prices, which are set by hand in the
  [ingredient admin](http://localhost:8100/admin/recipes/ingredient/). See
  [docs/TODO.md](docs/TODO.md) for the prices that need checking.

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

- `dev` is where work happens; run it locally from PyCharm.
- Every push and PR runs the tests in Gitea Actions
  ([.gitea/workflows/ci-cd.yml](.gitea/workflows/ci-cd.yml)).
- A push to `main` also builds the image, pushes it to the Gitea registry
  and deploys it to the homelab Docker host. Merging into `main` therefore
  **is** a production release.

The open work is tracked in [docs/TODO.md](docs/TODO.md).

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest       # tests (scaling + shopping logic)
.\.venv\Scripts\python.exe -m ruff check . # lint
.\.venv\Scripts\python.exe -m black .      # format
```
