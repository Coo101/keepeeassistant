# keepeeassistant

Tool to help you make menus and shopping lists for de chiro.
A summer camp meal planner — see [docs/SPEC.md](docs/SPEC.md) for the full specification.

## Setup

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "Django>=5.1,<6" weasyprint pytest pytest-django ruff black
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo   # optional: demo data + dev admin (admin/admin)
.\.venv\Scripts\python.exe manage.py runserver 8100
```

Then open http://localhost:8100/ — recipes, ingredients and camps are managed in
the [admin](http://localhost:8100/admin/); menu planning and shopping lists have
their own pages.

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
  ingredient prices. `manage.py import_colruyt_prices` fills prices from
  the nightly public Colruyt product dump
  ([colruyt-products-scraper](https://github.com/BelgianNoise/colruyt-products-scraper)),
  preferring the Everyday/Boni house brands and the fresh assortment.
  Review matches in the ingredient admin; pin a `colruyt_product_id` to
  lock an ingredient to a specific product, or set prices manually.
  `--rematch` redoes the matching from scratch.

### PDF export on Windows

WeasyPrint needs the GTK/Pango native libraries. Without them the app serves
the same documents as print-friendly HTML (use the browser's Print → Save as
PDF). To get native PDF output, install the
[GTK3 runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
and restart the server.

## Docker

```bash
docker compose up -d --build
```

Then open http://localhost:8000/. The SQLite database lives on the named
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

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest       # tests (scaling + shopping logic)
.\.venv\Scripts\python.exe -m ruff check . # lint
.\.venv\Scripts\python.exe -m black .      # format
```
