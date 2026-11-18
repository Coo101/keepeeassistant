# Camp Meal Planner (keepeeassistant)

**Status:** v3.0, split per area on 2026-11-16. Built on `dev` except what an area
file lists under **Planned**. **Author:** Yonick.

> The entry point to what the app does. Each area has its own file in `docs/spec/`;
> read this file plus the one area file a task is about. How changes are made
> (brainstorm, design, plan, build, review) is in `.claude/CLAUDE.md`; designs and
> plans live in `docs/superpowers/`.

## What it is

A web app for a Chiro's kitchen team (kookploeg) to cater summer camps. It keeps a
shared library of recipes and ingredients, plans a camp's meals day by day, scales
every recipe to the camp's headcount, makes shopping lists per shopping trip, and
follows the money from budget to bills to a financial report. It's called **Camp
Meal Planner** in English and **Kamp Maaltijd Planner** in Dutch.

The deliverables for a camp: a **day-by-day meal plan**, **shopping lists** (one per
trip and shop, summed), a **runbook** (draaiboek: practical info, then per day the
menu, quantities, steps and notes, on screen and printed), a **budget** before the
camp and a **financial report** after it.

**Users:** members of one or more Chiros. Within a Chiro, a member is an **admin**
(invites and removes members, changes roles, deletes camps) or a **member** (plans
and changes camps). Django **staff** run the site in the admin. Camps are always
**50+ people**. Planning happens on a **laptop**; cooking with a **phone in the
kitchen** (`docs/ui-guidelines.md`).

**Goals:** reuse recipes across camps and Chiros, no manual portion maths, a clean
shopping list per shop run, and knowing what a camp really cost. **Success:** for a
camp, the app produces correct scaled shopping lists per trip, flags every day no
trip covers, and compares what was paid with what was planned, with no manual
recalculation.

**Out of scope:** a CMS, unit conversions, a single-page app or build step, online
payments, automatic price fetching.

## The three stages

| Stage | What happens | Area files |
|---|---|---|
| Before the camp | Recipes and ingredients, the camp and its headcount, the menu per day, shopping lists per trip, the budget, the runbook, the kitchen stock | [recipes](spec/recipes.md), [planning](spec/planning.md), [shopping](spec/shopping.md), [kitchen](spec/kitchen.md) |
| During the camp | Kitchen mode (day view, ingredient check, extra shopping, cooking, evaluation), bills of extra trips uploaded | [kitchen](spec/kitchen.md), [finance](spec/finance.md) |
| After the camp | Bill review, the financial report, the menu evaluation, the pantry count | [finance](spec/finance.md), [kitchen](spec/kitchen.md) |

Across stages: [accounts](spec/accounts.md) (who sees what) and
[operations](spec/operations.md) (deployment, security).

## Glossary

| Term | Meaning |
|---|---|
| Chiro | A youth movement group. Camps, members, stock and pantry belong to one. |
| Kookploeg | The camp's kitchen team. |
| Draaiboek | The runbook: the camp's printed kitchen plan. |
| Standaardontbijt | The fixed bread breakfast, with optional extras (beleg, cornflakes). |
| Afdelingsbakken | Crates per age group, packed with what that group needs for a bread meal. |
| Klein Kamp | A shorter camp for the youngest groups. |
| Portion | One 12+ serving; see Core concepts. |

## Core concepts

- **Portion**: the unit of demand. One portion = one 12+/adult serving. An under-12
  is **0.7** portion. Staff count as a full portion. Recipes and camps both express
  their size in portions, so scaling is one division ([planning](spec/planning.md)).
- **Recipe**: a reusable dish with ingredients and timed steps, written for a base
  number of under-12s and 12+, which gives its base portions.
- **Ingredient**: a shared master item with one unit (piece / kg / liter), a
  category, a shop, a price history and tags for what it contains.
- **Camp**: a multi-day event of one Chiro, with a headcount and four meal times.
- **Menu entry**: a recipe in one slot of a camp's day.
- **Shopping trip**: a date on which you shop. It covers the meals of the days
  **after** it, up to and including the next trip day, never its own day.
- **Price**: a price per unit of an ingredient, either general or what one camp paid.

## Tech stack

Python 3.12+ (the Docker image uses 3.13), Django 5.2, SQLite in WAL mode, Django
templates (server-rendered, no build step), Bootstrap 5.3, Bootstrap Icons and HTMX
vendored in `static/vendor/` with `django-htmx` and crispy-forms
(`crispy-bootstrap5`), WeasyPrint for PDFs (print-friendly HTML when its libraries
are missing), `pdfplumber` for bills (PDFs with text only, D21), `markdown` for news
and help pages, gunicorn + whitenoise in Docker, pytest + pytest-django, ruff +
black. Dependencies are pinned in `pyproject.toml`; `requirements*.txt` are
generated with `uv export` and a test checks they match.

## Rules for every area

- **Access:** every page needs a login, except the public pages. Camps, stock,
  pantry and bills belong to one Chiro: only its members see them, others get a 404.
  Recipes and ingredients are shared. Example Chiros: everyone looks, only staff
  changes. Deleting always asks for confirmation. Details:
  [accounts](spec/accounts.md), [recipes](spec/recipes.md).
- **Errors:** validate at the model and form layer; fail loudly in dev. A request for
  something outside a camp's dates is a 404, never a 500.
- **Logging:** Python `logging`, no `print`.
- **Testing:** pytest. Cover scaling, shopping-list aggregation, coverage, budget and
  bill reading especially (the highest-risk code). Tests use `config/test_settings.py`
  and don't depend on the local `.env`. The real PDF test runs where WeasyPrint's
  libraries exist (the Docker image).
- **Style:** ruff + black, type hints throughout, small focused modules.
- **Performance:** pages with lists (planner, shopping, budget, report) use a fixed
  number of queries, whatever the size of the camp.
- **Privacy:** bills can show names, addresses and loyalty numbers. Uploading shows a
  warning, files are only served to the camp's Chiro as downloads, and bills are read
  in plain Python on the server, never by an AI service (D21).
- **Languages:** Dutch (default) and English. Text is written in English and marked
  for translation; the Dutch lives in `locale/nl/` (the compiled `.mo` is committed),
  help pages as `<slug>.nl.md`. The browser's language decides until someone picks NL
  or EN in the header. Numbers and dates follow the language (2,5 kg in Dutch); form
  fields and URLs keep a decimal point. Stored data (ingredient names, bill lines,
  error notes on a bill) stays as it was written.
- **Time zone:** `Europe/Brussels`.
- **Security:** see [operations](spec/operations.md).

## UI

`docs/ui-guidelines.md` (behaviour) and `docs/DESIGN.md` (look) are the reference for
every screen. Server-rendered templates on Bootstrap 5.3 with HTMX for small in-place
actions; every HTMX action also works as a normal link or form post. Planning
screens are designed for a PC and checked on a phone; kitchen screens for a phone or
tablet (D19). Kitchen screens optimise for reading and tapping, planning screens for
overview and data entry. Light mode only, labelled inputs, WCAG AA contrast. The Chiro movement
colours, no Chiro logo. Status: `base.html` and the theme are on Bootstrap; the pages
move over one area at a time (roadmap in `docs/TODO.md`).

## Decisions for every area

Numbered decisions keep their number wherever they live; area decisions are in the
area files. New ones continue from D20.

- **D6**: The spec stays Markdown; overviews, runbook, recipes, shopping lists and
  the financial report export to **PDF**.
- **D8**: Framework is **Django**.
- **D9**: **SQLite stays**, in WAL mode so the web workers and the bill reader can
  share it. Revisit if it ever gets slow or needs several servers.
- **D11**: **Recipes and ingredients are shared** between all Chiros; camps, stock,
  pantry and bills belong to one Chiro.
- **D15** (2026-11-05): **UI on Bootstrap and HTMX**, per `docs/ui-guidelines.md`.
- **D17** (2026-11-09): **Chiro colours, not the Chiro logo**, per `docs/DESIGN.md`:
  navy primary, red for the brand only, so it never competes with `danger`.
- **D18** (2026-11-09): **The app's name is translated:** Camp Meal Planner in
  English, Kamp Maaltijd Planner in Dutch. Wide tables scroll inside their box on a
  phone; only tables used on a phone get a card layout.
- **D19** (2026-11-16): **Planning on a PC, the kitchen on a phone or tablet.**
  Planning views (stages 1 and 3) are designed at 1366px and checked at 375px; kitchen
  views (stage 2) at 375px and 768px; public pages work at both.
- **D20** (2026-11-17): **The shopping page's trip lists work equally on a phone and
  a PC**, an exception to D19, because they're read at the Collect&Go pickup. The day
  picker, the warnings, the budget and the stock pages stay PC-first.

## Index

- `docs/spec/planning.md`, `shopping.md`, `recipes.md`, `kitchen.md`, `finance.md`,
  `accounts.md`, `operations.md`: what each area does now.
- `docs/TODO.md`: the roadmap.
- `docs/ui-guidelines.md`, `docs/DESIGN.md`: how screens behave and look.
- `docs/superpowers/specs/`, `docs/superpowers/plans/`: dated designs and plans.
- `README.md`: setup and running the app.
