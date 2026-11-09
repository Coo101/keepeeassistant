# Camp Meal Planner (keepeeassistant): Project Specification

**Status:** v2.0. Built on `dev` except where a section says **Planned**.
**Author:** Yonick
**Last updated:** 2026-11-09

> The source of truth for the build. `.claude/CLAUDE.md` and the agents in
> `.claude/agents/` point here. Keep it up to date with the code: when a decision
> changes, change this file and `docs/TODO.md` in the same piece of work.

---

## 1. Overview

A web app for a Chiro's kitchen team (kookploeg) to cater summer camps. It keeps a
shared library of recipes and ingredients, plans a camp's meals day by day, scales
every recipe to the camp's headcount, makes shopping lists per shopping trip, and
follows the money from budget to bills to a financial report.

It's called **Camp Meal Planner** in English and **Kamp Maaltijd Planner** in Dutch.

The deliverables for a camp:
1. A **day-by-day meal plan** (which recipes at which meal, each day).
2. **Shopping lists**: one per shopping trip and shop, with summed quantities.
3. A **runbook** (draaiboek): practical info, then per day the menu, quantities,
   steps and notes. On screen and as a printed bundle.
4. A **budget** before the camp and a **financial report** after it.

**Out of scope:** a CMS, unit conversions, a single-page app or build step, online
payments, and automatic price fetching (§14).

### Glossary

| Term | Meaning |
|---|---|
| Chiro | A youth movement group. Camps, members, stock and pantry belong to one. |
| Kookploeg | The camp's kitchen team. |
| Draaiboek | The runbook: the camp's printed kitchen plan. |
| Standaardontbijt | The fixed bread breakfast, with optional extras (beleg, cornflakes). |
| Afdelingsbakken | Crates per age group, packed with what that group needs for a bread meal. |
| Klein Kamp | A shorter camp for the youngest groups. |
| Portion | One 12+ serving; see §4. |

## 2. Users and Goals

- **Users:** members of one or more Chiros. Within a Chiro, a member is an **admin**
  (invites and removes members, changes roles, deletes camps) or a **member** (plans
  and changes camps). Django **staff** run the site in the admin.
- **Contexts:** a **laptop** for planning (camps, menus, shopping, bills), and a
  **phone in the kitchen** for cooking (§9.19). See `docs/ui-guidelines.md`.
- **Scale:** camps are always **50+ people**.
- **Goals:** reuse recipes across camps and Chiros, no manual portion maths, a clean
  shopping list per shop run, and knowing what a camp really cost.

**Success criteria:** for a given camp, the app produces correct scaled shopping
lists per shopping trip, flags every day no trip covers, and compares what was paid
with what was planned, with no manual recalculation.

## 3. Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ (the Docker image uses 3.13) |
| Framework | Django 5.2 |
| Database | SQLite in WAL mode (decision in §13) |
| Templating | Django templates, server-rendered, no build step |
| UI | **Planned:** Bootstrap 5.3 and Bootstrap Icons, served from `static/vendor/`; HTMX with `django-htmx`; forms through `django-crispy-forms` + `crispy-bootstrap5`. **Now:** hand-written `static/css/app.css` and a little plain JS. See §12. |
| PDF export | WeasyPrint (HTML template to PDF); print-friendly HTML when its libraries are missing |
| Bill reading | `pdfplumber` for text PDFs; an Ollama vision model for scans and photos |
| Content | `markdown` for news posts and help pages |
| Serving | gunicorn + whitenoise in Docker |
| Testing | pytest + pytest-django |
| Lint/format | ruff + black |
| Type hints | Yes, throughout |

Dependencies are pinned in `pyproject.toml`; `requirements*.txt` are generated with
`uv export` and a test checks they match.

## 4. Core Concepts

- **Portion**: the unit of demand. One portion = one 12+/adult serving. An under-12
  is **0.7** portion. Staff count as a full portion. Recipes and camps both express
  their size in portions, so scaling is one division.
- **Recipe**: a reusable dish with ingredients and timed steps, written for a base
  number of under-12s and 12+, which gives its base portions.
- **Ingredient**: a shared master item with one unit (piece / kg / liter), a
  category, a shop, a price history and tags for what it contains.
- **Camp**: a multi-day event of one Chiro, with a headcount and four meal times.
- **Menu entry**: a recipe in one slot of a camp's day (§5).
- **Shopping trip**: a date on which you shop. It covers the meals of the days
  **after** it, up to and including the next trip day, never its own day.
- **Price**: a price per unit of an ingredient, either general or what one camp paid.

## 5. Meal Structure

This section is the only definition of the meal slots (`core/constants.py`,
`MEAL_SLOTS`); other sections refer to it.

| Meal | Slot (course) | Dish types allowed | Required |
|---|---|---|---|
| Breakfast | main | `bread_meal` | yes |
| | extra | `bread_meal_extra` | |
| Lunch (midday, large) | soup | `soup` | |
| | main | `hot_meal`, `bread_meal` | yes |
| | extra | `bread_meal_extra` | |
| | dessert | `dessert` | |
| Tea time | snack (main) | `snack_fruitveg`, `snack_savory`, `snack_sweet` | yes |
| Dinner (evening) | main | `hot_meal`, `bread_meal` | yes |
| | extra | `bread_meal_extra` | |
| | dessert | `dessert` | |

- Every slot is labelled in the planner grid. A required slot that is empty is
  flagged red.
- The planner only offers recipes whose `dish_type` fits the slot. `other` fits no
  slot.
- A bought item (cake, ice cream, fruit) is a recipe too, with the ingredient and no
  steps.

## 6. Data Model

Grouped by Django app. Derived values are marked as such and never stored.

### accounts
- **Chiro**: `name` (unique), `is_example` (§9.16). Created in the admin, or by
  approving a join request.
- **Membership**: `user`, `chiro` (unique together), `role` (member / admin). A user
  can belong to several Chiros. A Chiro keeps at least one admin.
- **Invitation**: `chiro`, `email`, `role`, `token`, `invited_by`, `created_at`,
  `accepted_at`. Valid for 14 days, used once.
- **JoinRequest**: `name`, `email`, `chiro_name`, `message`, `status`
  (open / approved / rejected), `created_at`.
- **RateLimitHit**: `key` (hashed), `at`. Failed logins and reset mails (§10).

### recipes
- **Ingredient**
  - `name` (unique), `unit` (piece / kg / liter, fixed set, no conversions). Both
    fixed after creation, except for staff in the admin.
  - `category`: produce / dairy / meat / bakery / dry goods / other.
  - `shop`: Van Zon / Colruyt / bakker / beenhouwer. Lists are split per shop.
  - `product_details`: free text describing the product the price is for.
  - `tags`: what it contains (gluten, lactose, nuts, egg, soy, fish, meat, pork,
    vegetable, fruit, high in sugar). `tags_checked`: someone confirmed the tags.
- **IngredientPrice**: `ingredient`, `price`, `unit`, `source` (by hand / earlier
  stored / bill), `date`, `created_by`, `camp` (optional).
  - Without a camp it's a general price; with one it's what that camp paid. Kept
    without a camp when the camp is deleted (except example camps, §9.16).
  - Only prices in the ingredient's current unit count. The latest price is the most
    recent one across all camps and Chiros. New prices add to the history; they never
    overwrite.
- **Recipe**
  - `name` (unique, so the planner can tell them apart), `dish_type` (soup / hot_meal
    / bread_meal / bread_meal_extra / dessert / snack_fruitveg / snack_savory /
    snack_sweet / other), `notes`.
  - `base_children` (under 12) and `base_teens` (12+) the quantities feed.
    `base_portions` (derived) = `base_teens + 0.7 * base_children`.
  - `author` (optional), `others_can_edit` (§9.9).
  - Has many **RecipeIngredient** and **RecipeStep**.
- **RecipeIngredient**: `recipe`, `ingredient`, `quantity`, `unit`. The unit must
  match the ingredient's unit (validated), because prices are per that unit.
- **RecipeStep**: `recipe`, `order`, `instruction`, `duration_minutes` (optional).

### camps
- **Camp**
  - `chiro`, `name`, `start_date`, `end_date`, `is_archived`.
  - `num_children` (under 12), `num_teens` (12+), `num_staff`: set from the camp's
    groups, never typed. `demand_portions` (derived) =
    `num_teens + num_staff + 0.7 * num_children`.
  - Meal times: `breakfast_time`, `lunch_time`, `teatime_time`, `dinner_time`.
  - Runbook info: `cook_team`, `location`, `contact_leader`, `contact_rental`,
    `bakery`, `general_notes`.
- **CampGroup**: `camp`, `name` (unique per camp), `kind` (under 12 / 12+ / staff),
  `count`. An afdeling or team at the camp (Ribbels, Tito's, Leiding, Kookploeg).
- **DayNote**: `camp`, `date`, `text`. Free runbook notes per camp day.
- **DietaryNeed**: `camp`, `diet` (gluten-free, lactose-free, nut / egg / soy / fish
  allergy, vegetarian, vegan, no pork), `count`, `note`.

### planning
- **MenuEntry**: `camp`, `date`, `meal_type` (breakfast / lunch / tea / dinner),
  `course` (empty for the main slot, else soup / main / extra / dessert, per §5),
  `recipe` (protected: a planned recipe can't be deleted).

### shopping
- **ShoppingTrip**: `camp`, `date`. Coverage is derived (§8).
- **PantryItem**: `chiro`, `ingredient`, `quantity`. Food already in stock, unique per
  Chiro and ingredient, in the ingredient's unit.
- **Shopping list line** (derived, not stored): `ingredient`, `total_quantity`,
  `unit`, `category`, `shop`.

### kitchen
- **Utensil**: `chiro`, `name` (unique per Chiro), `in_stock`, `note`.
- **CampUtensil**: `camp`, `utensil`, `needed`. To buy: `needed - in_stock`, at
  least 0.
- **IngredientCheck** (**Planned**, §9.19): `camp`, `date`, `meal_type`,
  `ingredient`, `checked_by`, `checked_at`. One row per ticked ingredient.

### bills
- **Bill**: `camp`, `file` (optional; empty once removed), `original_name`, `shop`,
  `date`, `status` (waiting to be read / couldn't be read / to review / reviewed),
  `error`, `printed_total`, `uploaded_by`, `uploaded_at`.
- **BillLine**: `bill`, `description`, `article` (the shop's number, if printed),
  `quantity`, `pack_amount` (per item, in the ingredient's unit), `line_total` (incl.
  VAT), `category` (camp food / kitchen utilities / activity / personal / other),
  `ingredient`, `skipped`, `utensil`, `price` (the IngredientPrice it set).
- **LineMatch**: `shop`, `key` (article number, else the normalised description),
  `ingredient`, `pack_amount`, `unit`. Remembered from reviews.

### pages
- **Post**: `title`, `slug`, `body` (Markdown), `is_published`, `published_at`.
  News, written in the admin.
- Help pages are files in `pages/content/<slug>.md`, with `<slug>.nl.md` in Dutch.

## 7. Scaling Logic

```
recipe.base_portions = base_teens + 0.7 * base_children
camp.demand_portions = num_teens + num_staff + 0.7 * num_children
scale = camp.demand_portions / recipe.base_portions
```

Each ingredient quantity is multiplied by `scale`. Units are only piece / kg / liter,
so totals add up with no conversion. The factor is `CHILD_PORTION_FACTOR` in
`core/constants.py`; the helpers are in `core/portions.py`.

**Rounding:** 1 decimal for kg and liter, whole numbers for pieces. A quantity above
zero rounds to at least 0.1 or 1 piece, so it stays on the list.

**Acceptance:**
- A recipe for 10 teens on a camp of 20 teens + 10 children + 5 staff scales by 3.2.
- 0.04 kg shows as 0.1 kg; 0.3 pieces shows as 1.

## 8. Shopping List Logic

A shopping trip buys for the days **after** it, up to and including the next trip
day, never its own day.

```
trips = sorted(shopping trip dates)
for i, trip_date in enumerate(trips):
    cover_start = trip_date + 1 day
    cover_end   = trips[i+1] if i+1 < len(trips) else camp.end_date   # inclusive
    covered_days = [d for d in camp_days if cover_start <= d <= cover_end]

    totals = {}   # keyed by (ingredient, unit)
    for entry in MenuEntry where camp=camp and date in covered_days:
        scale = camp.demand_portions / entry.recipe.base_portions
        for ri in entry.recipe.ingredients:
            totals[(ri.ingredient, ri.unit)] += ri.quantity * scale

    subtract the Chiro's pantry, starting with the first trip (§9.12)
    list = group totals by shop, then category, rounded per §7
```

**Coverage warning:** because a trip never covers its own day, the camp's opening
days up to and including the first shopping day are not covered by any trip. To
cover them, add a trip dated before the camp (an arrival-eve shop). The planner and
shopping page **flag every camp day no trip covers**.

**Acceptance:**
- Trips on day 2 and day 5 of a 7-day camp cover days 3–5 and 6–7; days 1–2 are
  flagged.
- Uncovered days are left out of every list and of the budget.

## 9. Features

### 9.1 Recipes
- List, add, edit, copy and delete recipes outside the admin.
- Fields: name, dish type, base children + teens, ingredients (an ingredient can be
  added from the recipe form without leaving it), ordered steps with optional time.
  "Add ingredient" and "Add step" add an empty row in place (HTMX); without
  JavaScript they post the form and show it again with one more row, saving nothing.
- Shows the total time (sum of the step durations).
- **One-pager:** a recipe page with ingredients and steps, scaled to any number of
  portions (`?portions=`; invalid values fall back to the base), also as a PDF.

### 9.2 Ingredients
- List, add and edit ingredients and their prices outside the admin.
- The ingredient's page shows its price history.

### 9.3 Camps
- Create, edit, archive and delete camps of your Chiros.
- Fields: name, dates, headcount per group, the four meal times, the runbook info,
  diets and allergies (§9.11) and kitchen utilities needed (§9.15).
- **Headcount per group:** every afdeling and team that comes, each counting as under
  12, 12+ or staff, with how many. The camp's three totals and its portions are the
  sums, shown live under the table (and without JavaScript after a save or an added
  row). Rows left at 0 aren't saved; a name is used once per camp.
  - A new camp starts with the groups of its Chiro's latest camp, numbers at 0. With
    none (or a user in several Chiros), it starts with Ribbels, Speelclub and Rakwi's
    (under 12), Tito's, Keti's and Aspi's (12+), and Leiding, Kookploeg and Technische
    ploeg (staff).
  - The runbook (page and PDF) lists the groups. In the admin the totals are read-only
    and follow the group rows.
  - Camps from before the groups got one row per total ("nog te verdelen"), to split
    into afdelingen.
- The day list comes from the start and end date.

### 9.4 Menu planner
- For a camp, a grid of days x meals with every slot of §5.
- Fill each slot from the recipes that fit it; empty required slots are red.
- Shows the scaled quantities per meal for the camp's demand.
- Warns about meals planned outside the camp dates, which members can remove.
- Shows the diet (§9.11) and balance (§9.13) warnings.
- The planner is where shopping happens: shopping days, lists and the budget are
  reached from it (§9.5, §9.6). Kitchen mode (§9.19) has no shopping list.

### 9.5 Shopping lists
- For a camp, pick which dates are shopping days. Trips outside the offered dates are
  kept and warned about, and can be removed.
- One summed list per trip, split per shop and grouped by category, using §8, minus
  the pantry (§9.12).
- Warns about uncovered camp days and lists the kitchen utilities the stock lacks
  (§9.15).

### 9.6 Budget
- Cost per shop, per trip and per camp: shopping-list quantity x ingredient price.
- A camp uses its own price for an ingredient if it has one, otherwise the latest
  price, and each line shows which. A camp's own price is history: it doesn't change
  when other camps get new prices.
- Ingredients without a price, or priced per a different unit than a recipe uses,
  are listed and left out of the total. Uncovered days are not in the budget, and the
  cost per portion per day divides by covered days only.

### 9.7 Output and print
- PDFs through WeasyPrint: camp/day overview, runbook, recipe one-pager, shopping
  lists (with the missing utilities) and the financial report.
- Filenames are escaped. Without WeasyPrint's libraries (Windows), the same documents
  are served as print-friendly HTML.

### 9.8 Runbook (draaiboek)
- Per camp: practical info, then per day the menu with scaled quantities, the recipe
  steps and editable notes. Headings per day, so you can jump to a day. Page and PDF.
- Contact details and notes need a login, like every camp page.

### 9.9 Access
- Every page needs a login (Django's `LoginRequiredMiddleware`), except the home
  page, news, help pages, joining, and the login, password reset and invitation
  pages. New pages are private by default; mark public ones with
  `login_not_required`.
- Accounts are by invitation (§9.14). Log in with a username or email address.
  Changing your address needs your password; addresses aren't verified by mail yet.
- **Camps:** only members of the camp's Chiro can see and change them; others get a
  404. Staff get no exception outside the admin. Members create and edit their
  Chiro's camps; only its admins delete them. A camp can't move to another Chiro
  outside the admin.
- **Recipes** are shared: anyone with an account can read them and save a copy, which
  needs a new name and belongs to whoever made it.
  - The author (or staff) chooses read-only or editable by every account. A recipe
    without an author can only be changed by staff.
  - While another Chiro has a current or future camp planning a recipe, only staff can
    change it, so that camp's lists and budget don't change under it; a copy can.
    Finished and archived camps don't lock it. The edit page warns about the camps a
    change affects.
  - The author (or staff) can delete it once no camp plans it.
- **Ingredients** are shared: anyone with an account can add one, add a price, and
  change its category, shop, product details and tags. Anyone can delete one no
  recipe uses.
- Deleting always asks for confirmation first.
- Example Chiros (§9.16): every account can look, only staff can change.

### 9.10 Public site and accounts
- Public home page, news posts (Markdown, written in the admin) and help pages
  (Markdown files in `pages/content/`). No CMS.
- Account page: your details, your Chiros, changing your password. Password resets
  by email; mail only prints to the log until `EMAIL_HOST` is set.

### 9.11 Diets and allergies
- Per camp: how many people have which diet or allergy. Ingredients are tagged with
  what they contain. The planner lists every planned meal that conflicts.
- It relies on the tags, so it also lists planned ingredients nobody marked as
  checked, and tells people to check the labels. It is a help, not a guarantee.

### 9.12 Pantry
- Per Chiro, on its stock page next to the kitchen utilities: food that's already
  there, in the ingredient's unit. Every camp of the Chiro takes it off its shopping
  lists and budget, starting with the first trip. Camps don't reserve it from each
  other.

### 9.13 Balance
- The planner flags hot meals and days without vegetables, days without fruit, and
  more than 2 sweet recipes a day. Missing vegetables or fruit is only flagged when no
  ingredient involved has unchecked tags, so unfinished tagging gives no false alarms.

### 9.14 Chiros, roles, invitations and join requests
- A Chiro's page lists its members. Its admins invite by email, remove members and
  change roles; a Chiro keeps at least one admin. Staff can also invite from the
  admin. The one-time link works for 14 days.
- Anyone can request access on the public site (`/join/`). Staff approve in the
  admin: that creates the Chiro if needed, with the requester as its admin, and sends
  the invitation.
- Camps can be archived and brought back. Archived camps stay available, are listed
  apart and don't lock recipes.

### 9.15 Kitchen utilities
- Per Chiro: a stock of kitchen utilities (pots, fire pits, gas bottles), with how
  many it has and a note. All members keep it up to date. An item a camp still needs
  can't be removed.
- Per camp: which utilities it needs and how many, reached from the planner and the
  camp's edit page. Typing a name that isn't in the stock adds it with none in stock.
- What the stock lacks is listed on the camp's utilities page, the shopping page and
  the shopping lists PDF. Camps of one Chiro each compare with the whole stock; they
  don't reserve items from each other.

### 9.16 Example camp
- `manage.py create_example_camp` makes an example Chiro with one camp, planned with
  the recipes in the database. Dates, headcount, contacts, stock, shopping days and
  bills are made up; `--reset` starts over.
- Every account sees it under its own heading on the camp list, with all pages and
  PDFs. Only staff can change it, and it has no members to show.
- It stays out of everyone's way: its prices are never another camp's estimate, it
  doesn't lock the recipes it plans, its bills teach no matches, and deleting it
  takes its prices along.

### 9.17 Bills
- Per camp: upload bills (PDF or photo) after a privacy warning. Only members of the
  camp's Chiro can open them, always as a download. A file can be removed while
  keeping the lines, and goes when its bill or camp is deleted.
- Reading:
  - PDFs with text are read in plain Python (`pdfplumber`), tuned for Collect&Go
    (Colruyt) and Van Zon invoices.
  - Scans and photos wait for an Ollama vision model (`manage.py read_bills`, the
    `bill-reader` service), and stay waiting while it's unreachable.
  - Lines can always be added by hand.
  - Invoices listing amounts without VAT get the VAT added per line, so the lines add
    up to what was paid; leftover cents go on a rounding line.
  - Where a bill prints article numbers, the remembered match per shop follows the
    number; otherwise the description.
- Review: a person checks every line (ingredient, amount per item in the ingredient's
  unit, category). Saving sets the camp's price (paid / total amount) and remembers
  the match per shop. Nothing changes a price before that. The review table fits the
  page, keeps its header in view, and can create a missing ingredient per line, named
  after the line.
- Categories: only camp food sets prices. Camp food and other (deposits, discounts)
  count towards the food total compared with the budget. Skipped lines count for
  nothing.
- A kitchen-utilities line can go into the Chiro's stock (§9.15), as a new item or
  onto an existing one, adding its quantity. A line is added once, however often the
  review is saved; deleting the line later doesn't take it out again.

### 9.18 Financial report
- Per camp, as a page and a PDF. It first checks the bills: open bills, planned
  ingredients not on any of this camp's bills, and ingredients without any price.
- Then the cost of every planned meal: its scaled recipe at the camp's prices from
  the bills. Missing ones use the latest known price and the meal is marked
  estimated; ingredients without a price are left out and named.
- A summary: paid for food, the planned meals' cost and the difference (leftovers,
  extras, waste), food per portion per day, paid per category, and per meal type the
  total and the cost per portion.
- Personal costs are listed apart, with their total. Dividing them is planned (§14).

### 9.19 Kitchen mode (Planned)
Phone screens for the cooks during the camp. They follow the kitchen rules in
`docs/ui-guidelines.md`: big text, big tap targets, usable with busy hands.

- **Today:** opens on the current camp day (any day can be picked), with each meal at
  its time and the recipes planned in it.
- **Ingredient check** ("Heb je alles?"): before cooking a meal, a list of every
  ingredient it needs, with the scaled quantity, grouped per recipe. The cook ticks
  off each one that is in the kitchen. Ticks are saved per camp, day, meal and
  ingredient (`IngredientCheck`), so everyone on the team sees the same list on their
  own phone; a tick can be undone. The meal shows how many are still unticked. This
  is a check, not a shopping list: buying is planned in the planner (§9.4, §9.5).
- **Cooking:** a recipe's steps one at a time, with big Previous / Next buttons and
  the scaled quantities used in that step's recipe in view. A step with a duration
  has a timer with start, pause and reset, and an audible and visual alert. Several
  timers can run at once and stay visible when moving between steps.
- Only members of the camp's Chiro (and example camps, read-only) can open it.
  Ticking needs no extra role.

**Acceptance:**
- Ticking an ingredient on one phone shows as ticked on another after a reload.
- A meal with nothing planned shows an empty state, not an error.
- Every tick and timer action also works without JavaScript (the tick as a form
  post; the timer shows the duration).

## 10. Non-functional Requirements

- **Logging:** Python `logging`, no `print`.
- **Errors:** validate at the model and form layer; fail loudly in dev. A request for
  something outside a camp's dates is a 404, never a 500.
- **Testing:** pytest. Cover scaling, shopping-list aggregation, coverage, budget and
  bill reading especially (the highest-risk code). Tests use `config/test_settings.py`
  and don't depend on the local `.env`. The real PDF test runs where WeasyPrint's
  libraries exist (the Docker image).
- **Style:** ruff + black, type hints throughout, small focused modules.
- **Performance:** pages with lists (planner, shopping, budget, report) use a fixed
  number of queries, whatever the size of the camp.
- **Security:**
  - Without a real `DJANGO_SECRET_KEY` (`change-me` doesn't count) the app refuses to
    start unless `DJANGO_DEBUG=1`. Debug is off unless enabled.
  - Failed logins are limited per account (10) and per address (50), reset mails per
    email (3) and per address (10), within 15 minutes. Behind a proxy the address
    comes from `DJANGO_CLIENT_IP_HEADER`.
  - `seed_demo` (login `admin` / `admin`) only runs with `DJANGO_DEBUG=1`.
  - The container runs as a non-root user (uid 1000).
  - Cookie and proxy settings for HTTPS: `DJANGO_SECURE_COOKIES`,
    `DJANGO_BEHIND_TLS_PROXY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`.
- **Privacy:** bills can show names, addresses and loyalty numbers. Uploading shows a
  warning, files are only served to the camp's Chiro as downloads, and photos are only
  sent to the Ollama server set in `OLLAMA_URL` (your own machine), never a cloud
  service.
- **Languages:** Dutch (default) and English. Text is written in English and marked for
  translation; the Dutch lives in `locale/nl/` (the compiled `.mo` is committed), help
  pages as `<slug>.nl.md`. The browser's language decides until someone picks NL or EN
  in the header. Numbers and dates follow the language (2,5 kg in Dutch); form fields
  and URLs keep a decimal point. Stored data (ingredient names, bill lines, error notes
  on a bill) stays as it was written.
- **Time zone:** `Europe/Brussels`.

## 11. Deployment and Operations

- **Branches:** work happens on `dev`, run locally from PyCharm (port 8100). Merging
  into `main` is a production release.
- **CI/CD:** Gitea Actions (`.gitea/workflows/ci-cd.yml`). Every push and PR runs ruff,
  black, Django checks and pytest. A push to `main` also builds the image, pushes it to
  the Gitea registry and deploys it to the homelab Docker host, checking that the image
  renders a PDF.
- **Containers** (`docker-compose.yml`): `web` (gunicorn) and `bill-reader`
  (`read_bills --loop`), sharing the data volume. Migrations run at start.
- **Data:** the SQLite database and uploaded bills live on one volume (`/data`, set by
  `DJANGO_DATA_DIR`). Back it up with `sqlite3 .backup`, or with the app stopped.
- **Network:** first on the LAN behind Caddy (`meals.dk-1.home.zx`). Going public
  means a Cloudflare tunnel, the HTTPS settings in §10, and mail (`EMAIL_*`).
- **Commands:** `migrate`, `createsuperuser`, `seed_demo` (dev only),
  `import_kamp_recipes` (the recipe library), `create_example_camp`, `read_bills`.
- All settings are listed in `.env.example`.

## 12. UI

`docs/ui-guidelines.md` is the reference for every screen. In short:

- Server-rendered Django templates on **Bootstrap 5.3** with Bootstrap Icons, both
  served from `static/vendor/` (no CDN: camp sites can have poor connectivity), and
  **HTMX** with `django-htmx` for small in-place actions. Forms through crispy-forms.
- Every HTMX action also works as a normal link or form post.
- Mobile first: kitchen screens optimise for reading and tapping, planning screens for
  overview and data entry.
- Light mode only, one accent colour, labelled inputs, WCAG AA contrast.
- The look follows `docs/DESIGN.md`: the Chiro movement colours from its house style.
  Navy is the primary colour, red the brand colour (navbar, the rule under page titles),
  sand tints the surfaces. No Chiro logo: the app isn't an official Chiro product.

**Status:** Bootstrap, Bootstrap Icons and HTMX are vendored and `base.html` uses them
(navbar, messages as alerts). The pages still use the hand-written `app.css`; they move
over one area at a time, as planned in `docs/TODO.md`, before kitchen mode (§9.19),
which is built on it.

## 13. Decisions

1. Under-12 portion factor = **0.7**. Staff eat and count as a full portion.
2. Recipes are entered as "serves X under-12 + Y 12+" and converted to base portions.
3. **Units are piece / kg / liter only.** No conversions. A recipe's unit must match
   its ingredient's unit.
4. A shopping day **doesn't** cover its own day; it buys for the following days up to
   and including the next shopping day. Uncovered days are flagged.
5. Meal slots are as in §5.
6. The spec stays Markdown; overviews, runbook, recipes, shopping lists and the
   financial report export to **PDF**.
7. Quantities are rounded to **1 decimal** (kg/liter) and whole pieces; camps are
   always 50+ people.
8. Framework is **Django**.
9. **SQLite stays**, in WAL mode so the web workers and the bill reader can share it.
   Revisit if it ever gets slow or needs several servers.
10. **Accounts by invitation only**; Chiros are created by staff or by approving a
    join request.
11. **Recipes and ingredients are shared** between all Chiros; camps, stock, pantry
    and bills belong to one Chiro.
12. **Prices are a history.** A camp's own price (from its bills) wins, otherwise the
    latest price. A new price never changes another camp's own price.
13. The automatic Colruyt price import was removed: the third-party product dump is
    unmaintained and its matches were unreliable. Prices come from people and bills.
14. **Bills are read on our own hardware** (Python, or Ollama on a local PC), never by
    a cloud AI.
15. **UI on Bootstrap and HTMX**, per `docs/ui-guidelines.md` (2026-11-05).
16. **Kitchen mode checks ingredients, it doesn't shop.** Shopping lists stay with the
    planner (2026-11-05).
17. **Chiro colours, not the Chiro logo**, per `docs/DESIGN.md`: navy primary, red for
    the brand only, so it never competes with `danger` (2026-11-09).
18. **The app's name is translated:** Camp Meal Planner in English, Kamp Maaltijd
    Planner in Dutch. Wide tables scroll inside their box on a phone; only tables used
    on a phone get a card layout (2026-11-09).

## 14. Future

- **Dividing personal costs:** a Splitwise-like page. Who paid which bill, who owes
  whom for the personal lines, and settling up. Bill lines need a person (or several)
  first.
- **Cloudflare Access login:** once you pass Cloudflare Access, the app logs you in by
  email, so you log in once. Built on the `cloudflare-access` branch, not merged.
- **Automatic price updates** from a reliable source, once one exists.
- **More bill layouts**, as real bills of other shops come in.
- **Email verification** when someone changes their address.
