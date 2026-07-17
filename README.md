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

### PDF export on Windows

WeasyPrint needs the GTK/Pango native libraries. Without them the app serves
the same documents as print-friendly HTML (use the browser's Print → Save as
PDF). To get native PDF output, install the
[GTK3 runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
and restart the server.

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest       # tests (scaling + shopping logic)
.\.venv\Scripts\python.exe -m ruff check . # lint
.\.venv\Scripts\python.exe -m black .      # format
```
