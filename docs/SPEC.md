# Summer Camp Meal Planner — Project Specification

**Status:** v1.0 — Ready for build (via Claude Code)
**Author:** Yonick
**Last updated:** 2026-11-01

> This document is the source of truth for the build. Keep it in the repo (e.g.
> `docs/SPEC.md`) and reference it from `../CLAUDE.md` so the coding agent always
> has the full picture.

---

## 1. Overview

A tool to plan catering for summer camps. It lets you maintain a library of
recipes, define camps with their attendees and meal schedule, assign recipes to
each meal across the camp's days, automatically scale recipe quantities to the
number of people, and generate shopping lists grouped by shopping trip.

The end deliverables for a camp are:
1. A **day-by-day meal plan** (which recipes at which meal, each day).
2. **Shopping lists** — one per shopping trip, with aggregated quantities.

## 2. Users & Goals

- **Primary user:** camp organiser / cook planning meals for a multi-day camp.
- **Scale:** camps are always **50+ people**.
- **Goals:** reuse recipes across camps, avoid manual portion maths, get a
  clean shopping list per shop run.

**Success criteria:** For a given camp, the tool produces a correct scaled
shopping list per selected shopping day with no manual recalculation.

## 3. Tech Stack

**Framework: Django** (confirmed). CRUD-heavy relational app that needs
data-entry screens — Django admin, ORM, migrations, and server-rendered
templates fit it well.

| Layer | Choice |
|---|---|
| Language | Python 3.12+ (the Docker image uses 3.13) |
| Framework | Django 5.x |
| Database | SQLite (dev) -> Postgres if ever multi-user |
| Templating | Django templates (+ HTMX optional for snappier UI) |
| PDF export | WeasyPrint (HTML template -> PDF) |
| Testing | pytest + pytest-django |
| Lint/format | ruff + black |
| Type hints | Yes, throughout |

## 4. Core Concepts

- **Portion** — the unit of demand. One portion = one 12+/adult serving. An
  under-12 = **0.7** portion. Staff = a full portion. Both recipes and camps
  express their size in portions, so scaling is a single division.
- **Recipe** — a reusable dish with ingredients and timed steps, defined for a
  base number of under-12s + 12+ (which converts to base portions).
- **Ingredient** — a master item with a canonical unit (piece / kg / liter) and
  a category, used to organise shopping lists.
- **Camp** — a multi-day event with a headcount and a daily meal schedule.
- **Menu entry** — a recipe assigned to a specific (camp, date, meal, course).
- **Shopping trip** — a date on which you shop; it covers the meals of the days
  **after** it, up to and including the next trip day (never its own day).

## 5. Meal Structure

Meals are not uniform — each meal type has its own shape:

| Meal | Structure | Slots |
|---|---|---|
| **Breakfast** | Bread meal (standaardontbijt), plus optional extra (beleg, cornflakes, ...) | main + extra |
| **Lunch** (midday, large) | Soup, hot or bread meal, optional extra, dessert | soup + main + extra + dessert |
| **Tea time** | Afternoon snack — fruit/veg, savory **or** sweet | snack |
| **Dinner** (evening) | Hot meal **or** bread meal, optional extra and dessert | main + extra + dessert |

Every slot is labelled in the planner grid; the **main** slot of each meal
(and the tea snack) is required and flagged red while empty.

A recipe carries a `dish_type` so the planner only offers appropriate recipes
for each slot (e.g. only `soup` recipes for the lunch soup slot; only
`snack_fruitveg` / `snack_savory` for tea; only `hot_meal` / `bread_meal` for
dinner).

## 6. Data Model

### Chiro
- `name` (unique); created in the admin only

### Membership
- `user`, `chiro` (unique together); a user can belong to several Chiros

### Ingredient
- `name` (unique)
- `unit` — one of **{piece, kg, liter}** (fixed set; no conversions)
- `category` — produce / dairy / meat / bakery / dry goods / other (for grouping)
- `shop` — Van Zon / Colruyt / bakker / beenhouwer (lists are split per shop)
- `price_per_unit` — EUR per `unit`, optional, set by hand
- `product_details` — free text describing the product the price is for
- `price_updated` — when the price was last updated

### Recipe
- `name`
- `dish_type` — soup / hot_meal / bread_meal / bread_meal_extra / dessert /
  snack_fruitveg / snack_savory / snack_sweet / other. Breakfast slots take
  `bread_meal` (+ optional `bread_meal_extra`); the lunch main course and the
  dinner main slot both take `hot_meal` (dinner also accepts `bread_meal`).
- `base_children` — under-12 count the entered quantities feed
- `base_teens` — 12+ count the entered quantities feed
- `base_portions` (derived) = `base_teens + 0.7 * base_children`
- `notes`
- `author` (optional), `others_can_edit` (see §9.8)
- has many **RecipeIngredient**, many **RecipeStep**

### RecipeIngredient
- `recipe`, `ingredient`, `quantity`, `unit`
- `unit` must match the ingredient's unit (validated), because the price is per
  that unit and there are no conversions.

### RecipeStep
- `recipe`, `order`, `instruction`, `duration_minutes` (optional)

### Camp
- `chiro`, `name`, `start_date`, `end_date`
- `num_children` (under 12), `num_teens` (12+), `num_staff`
- meal times: `breakfast_time`, `lunch_time`, `teatime_time`, `dinner_time`
- `demand_portions` (derived) = `num_teens + num_staff + 0.7 * num_children`
- runbook info: `cook_team`, `location`, `contact_leader`, `contact_rental`,
  `bakery`, `general_notes`

### DayNote
- `camp`, `date`, `text` — free-form runbook notes per camp day

### MenuEntry
- `camp`, `date`, `meal_type` (breakfast/lunch/tea/dinner)
- `course` (nullable; used for lunch: soup/main/dessert)
- `recipe`
- One meal can hold several entries (lunch = 3 courses); breakfast/tea/dinner
  normally one each.

### ShoppingTrip
- `camp`, `date`
- Coverage is derived (see §8).

### ShoppingListItem (computed)
- `ingredient`, `total_quantity`, `unit`, `category`

## 7. Scaling Logic

Both sides are in portions, so:

```
recipe.base_portions = base_teens + 0.7 * base_children
camp.demand_portions = num_teens + num_staff + 0.7 * num_children
scale = camp.demand_portions / recipe.base_portions
```

Each ingredient quantity is multiplied by `scale`. Because units are only
piece / kg / liter, totals add up directly with no conversion.

**Rounding:** round quantities to **1 decimal** for kg/liter; whole numbers for
piece. Camps are always 50+ people, so fine-grained precision isn't needed.

## 8. Shopping List Logic

A shopping trip buys for the days **after** it, up to and including the next
trip day — never its own day.

```
trips = sorted(selected shopping dates)
for i, trip_date in enumerate(trips):
    cover_start = trip_date + 1 day
    cover_end   = trips[i+1] if i+1 < len(trips) else camp.end_date   # inclusive
    covered_days = [d for d in camp_days if cover_start <= d <= cover_end]

    totals = {}   # keyed by (ingredient, unit)
    for entry in MenuEntry where camp=camp and date in covered_days:
        scale = camp.demand_portions / entry.recipe.base_portions
        for ri in entry.recipe.ingredients:
            totals[(ri.ingredient, ri.unit)] += ri.quantity * scale

    list = group totals by ingredient.category, rounded per §7
```

**Coverage warning (important):** because a trip never covers its own day, the
camp's **opening days up to and including the first shopping day are not covered
by any trip.** To cover them, add a shopping trip dated *before* those days
(e.g. an arrival-eve shop). The planner must **flag any camp day that no trip
covers** so nothing silently falls through the cracks.

## 9. Features (MVP)

### 9.1 Recipe management
- List / add / edit / delete recipes.
- Fields: name, dish_type, base children + teens, ingredients (ingredient + qty
  + unit from the fixed set), ordered steps with optional per-step time.
- Show total estimated time (sum of step durations).

### 9.2 Camp management
- Create / edit multiple camps.
- Fields: name, start/end date, headcount (children / teens / staff), the four
  meal times.
- Derive the day list from start/end date.

### 9.3 Menu planning
- For a chosen camp, show a grid of days x meals.
- Fill each slot with the appropriate recipe(s): breakfast (1), lunch (soup +
  main + dessert), tea (1), dinner (1: hot or bread).
- Only offer recipes whose `dish_type` fits the slot.
- Show scaled quantities per meal for the camp's demand.

### 9.4 Shopping lists
- For a chosen camp, select which dates are shopping days.
- Generate one aggregated, category-grouped list per shopping day using §8.
- Warn about any uncovered camp days.

### 9.5 Output / print
- **Camp / day overview** -> **PDF** (WeasyPrint) for printing.
- **Shopping lists** -> printable, PDF export as well.

### 9.6 Budget
- Cost per shop, per trip and per camp: shopping-list quantity x ingredient price.
- Prices are entered by hand in the admin.
- Ingredients without a price, or priced per a different unit than a recipe uses,
  are listed and left out of the total. Uncovered days are not in the budget, and
  the cost per portion per day divides by covered days only.

### 9.7 Runbook (draaiboek)
- Per camp: practical info, then per day the menu with scaled quantities, the
  recipe steps and editable notes. Available as a page and a PDF.

### 9.8 Access
- Every page needs a login; new pages are private by default. Access is by
  invitation: staff create accounts and Chiros in the admin.
- A user belongs to one or more Chiros. Camps can only be seen and changed by
  members of the camp's Chiro; other users get a 404. Staff get no exception
  outside the admin.
- Recipes are shared: anyone with an account can read and copy them. A copy
  needs a new name and belongs to the user who made it.
- A recipe's author (or staff) chooses between read-only and editable by everyone
  with an account. A recipe without an author can only be changed by staff.
- Editing a recipe affects every camp that plans it, also those of other Chiros.
  The edit page warns about this and points to saving a copy instead.
- Recipe names are unique, so they can be told apart in the planner.

### 9.9 Planned: public site and accounts
- Public home page with posts, a getting started page and docs (no CMS: a `Post`
  model edited in the admin, and Markdown files for the docs).
- "Mijn account": log in by email, reset a password, see your Chiros. Needs a
  mail backend.
- Screens for camps and ingredients, so normal users no longer need the admin.

## 10. Non-functional Requirements

- **Logging:** Python `logging`, no `print`.
- **Errors:** validate at model/form layer; fail loudly in dev.
- **Testing:** pytest; cover the scaling and shopping-list aggregation logic
  especially (highest-risk code).
- **Style:** ruff + black, type hints throughout, small focused modules.

## 11. Proposed Project Structure

```
campmealplanner/
├── manage.py
├── config/                 # settings, urls, wsgi
├── recipes/                # Recipe, Ingredient, RecipeIngredient, RecipeStep
├── camps/                  # Camp, meal schedule
├── planning/               # MenuEntry, the day x meal grid
├── shopping/               # ShoppingTrip + list generation
├── core/                   # shared: portion/scaling helpers, constants
├── templates/
└── tests/
```

Suggested shared constant: `CHILD_PORTION_FACTOR = 0.7` in `core/`.

## 12. Resolved Decisions

1. Under-12 portion factor = **0.7**. Staff eat and count as a full portion.
2. Recipes entered as "serves X under-12 + Y 12+", converted to base portions.
3. **Canonical units only: piece / kg / liter.** No conversions.
4. A shopping day **does not** cover its own day; it buys for the following
   days up to and including the next shopping day. Uncovered opening days are
   flagged.
5. Lunch has three distinct courses (soup / main / dessert); breakfast = one
   variant; dinner = hot meal or bread meal; tea = snack (fruit/veg or savory).
6. Spec stays as `.md`; camp/day overview and shopping lists export to **PDF**.
7. Quantities rounded to **1 decimal** (kg/liter); camps are always 50+ people.
8. Framework is **Django**.

## 13. Out of Scope for v1 (future)

- **Nutrition / balance tracker.** Flag whether a meal and a day are balanced —
  e.g. enough vegetables, not too much sugar. Likely approach: per-ingredient
  nutrition tags (is-vegetable, sugar level, food group, etc.) rolled up per
  meal and per day, with simple threshold warnings in the planner.
- Dietary restrictions / allergies handling.
- "Pantry on hand" subtraction (exclude what you already have).
- **Automatic price updates.** Fetch up-to-date ingredient prices from a
  reliable source. An earlier import from a third-party Colruyt product dump
  was removed: it is unmaintained and its product matches were unreliable.
- Roles within a Chiro, and recipe edit rights per user.
- Open sign-up and creating a Chiro without staff.
