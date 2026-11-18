# UI move, area 3: shopping, budget and stock. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the shopping page, the budget, the Chiro stock page and the camp's kitchen
utilities page to Bootstrap and the shared components, with the shopping page's trip
lists readable on a phone at the Collect&Go pickup and one tap away through jump links.

**Architecture:** Templates first. One view change: `kitchen/views.py` gets area 1's
"add a row" handling (a plain post without JavaScript, a row URL for HTMX) for the
pantry and the camp's utilities, reusing `recipes/_formset.html`,
`partials/_formset_row.html` and `core.rows.row_index`. No new components. D20 goes into
`docs/SPEC.md` and `docs/ui-guidelines.md`.

**Tech Stack:** Django 5.2 templates, Bootstrap 5.3, Bootstrap Icons, HTMX 2 with
django-htmx, pytest.

**Spec:** `docs/superpowers/specs/2026-11-17-ui-area-3-shopping-design.md`, on top of
`docs/superpowers/specs/2026-11-16-ui-move-design.md`. Area files:
`docs/spec/shopping.md`, `docs/spec/kitchen.md`. Branch: `ui/area-3-shopping` from
`origin/dev` (6eb1723).

## Global Constraints

- Follow `docs/ui-guidelines.md` (behaviour) and `docs/DESIGN.md` (look). Paste the
  lines a task names into its brief.
- D19: the budget, the stock page, the camp utilities page and the shopping page's
  top part (day picker, warnings) are designed for a **PC at 1366px**, then checked at
  **375px**: no horizontal page scroll, tables scroll inside `table-responsive`,
  nothing cut off.
- **D20:** the shopping page's **trip lists** work equally at 375px and 1366px: no
  sideways scrolling inside a trip list on a phone, names wrap, quantities stay on one
  line (`text-nowrap`).
- Tables stay tables on a PC; don't hide information behind clicks.
- No behaviour, model, permission or business-logic changes beyond Task 1. Every link,
  form and no-JavaScript path keeps working; all existing tests keep passing (a test may
  only change where this plan says so). Read only: nothing on the trip lists can be
  ticked.
- HTMX only on the two "add a row" buttons. They also work as a plain post.
- Every visible text in `{% translate %}` / `{% blocktranslate %}`; new Dutch strings
  go in `locale/nl/LC_MESSAGES/django.po` (makemessages and msgfmt in Docker, README;
  fix any `#, fuzzy` entries by hand) and the `.mo` is recompiled.
- No inline `style=""`, no inline `<script>`, no `onclick`. Colours only from Bootstrap
  classes and the `--chiro-*` tokens. Destructive buttons `btn-outline-danger` with
  `bi-trash`. Badges only for status (`text-bg-success|warning|danger|secondary`).
- Icons next to text get `aria-hidden="true"`; icon-only controls get `aria-label`.
  Warnings are `alert alert-warning d-flex gap-2` with `bi-exclamation-triangle`, as in
  `planning/_outside_entries.html`; no emoji.
- Dates on screen through `short_date` (`{% load ui %}`): `short_date` for camp days,
  `short_date:"year"` for price dates.
- Don't touch `shopping/shopping_print.html` (it has its own CSS; area 6 checks it).
  `confirm_delete.html` is area 5.
- Keep `id="pantry"` on the stock page (the shopping page links to `#pantry`) and the
  utensil names `<datalist>` on the camp utilities page.

## Review Focus

1. **No shopping days yet:** the shopping page shows no jump links and no PDF/Budget
   buttons, but an empty state pointing at the day picker; the budget shows its empty
   state. Tests in Tasks 2 and 3.
2. **A trip with nothing to buy** (no menu entries in its days): its jump link and
   section are still there, the section says so, and nothing breaks. Test in Task 2.
3. **"Add a row" without JavaScript** with rows already typed, some invalid: the page
   comes back with one more empty row, everything typed kept, nothing saved, no error
   alert. Tests in Task 1.
4. **An example Chiro or camp:** the row URLs answer a GET (they change nothing), the
   add-row post is refused like any other change. Tests in Task 1.
5. **Long ingredient names and long quantities at 375px** in a trip list: they wrap,
   the page never scrolls sideways. Browser check in Task 6 (seed a long name).

---

## Page layouts (Claude with frontend-design)

Within `DESIGN.md`: sand-soft card and table headers, navy actions, the red rule only in
the page header.

**Shopping page (1366px):**

```
Shopping                                         (page_header, meta: camp name)
Kamp 2026
───
[Menu plan] [Shopping*] [Runbook] …                              (camp_nav)
(example note) (outside-dates alert)
Trips: [Tue 14 Jul · 3 shops] [Fri 17 Jul · 2 shops]   [⇩ PDF] [€ Budget]
Already have something? Add it to the pantry of … and it comes off these lists.
┌ Shopping days ─────────────────────────────────────────────┐
│ A trip buys for the days after it … (form-text)            │
│ [x] Sat 11 Jul (before camp)  [ ] Sun 12 Jul  [x] Tue 14 … │
│ [Save shopping days]                                       │
└────────────────────────────────────────────────────────────┘
(uncovered-days alert)
Shop on Tuesday 14 Jul                                  (h2, id="trip-<pk>")
Covers Wed 15 Jul – Fri 17 Jul (3 camp days)
┌ Colruyt · 24 items ┐ ┌ Bakker · 3 items ┐ ┌ Slager · 5 items ┐
│ Vegetables          │ │ Bread             │ │ Meat              │
│ Prei        1,5 kg  │ │ Brood    12 stuk  │ │ Gehakt    4,0 kg  │
└─────────────────────┘ └───────────────────┘ └───────────────────┘
↑ Back to top
Kitchen utilities to buy …
```

- Jump links: `<nav id="trip-links" aria-label="{% translate 'Shopping trips' %}"
  class="d-flex flex-wrap align-items-center gap-2 mb-4">`, one
  `a.btn.btn-outline-primary` per trip (`href="#trip-{{ tl.trip.pk }}"`, text
  "{{ date|short_date }} · N shops" with a plural, or "… · nothing to buy" when the
  trip list is empty), then PDF (`bi-file-earmark-pdf`) and Budget (`bi-currency-euro`)
  as `btn btn-outline-primary` in a `div.ms-lg-auto.d-flex.gap-2`. Only when
  `plan.trip_lists`.
- Day picker: a card, the dates as `form-check form-check-inline` checkboxes (label
  "(before camp)" in `text-body-secondary`), submit `btn btn-primary`.
- Each trip: `section#trip-<pk>` with `h2`, the covered days in `text-body-secondary`,
  then `div.row.g-3` with one `div.col-12.col-md-6.col-xl-4` per shop: a card, header
  `h3.h6.mb-0` "shop name" plus the item count in `text-body-secondary`, body a
  `table.table.table-sm.mb-0` with a `th[colspan=2]` category row per category (small,
  `text-body-secondary`) and rows `td` name / `td.text-end.text-nowrap` quantity. An
  empty trip: `p.text-body-secondary` "Nothing to buy — no menu entries in the covered
  days." Then `a.icon-link.small` (`bi-arrow-up`) "Back to top" to `#trip-links`.
- No trips: `components/empty_state.html` (icon `cart`) "No shopping days yet. Tick the
  days you shop on above." without an action (the form is right above it).
- Kitchen utilities to buy: `h2`, a small `table.table.table-sm` in a card (name,
  number `text-end`), then the existing explanation line in `text-body-secondary`.

At 375px the shop cards stack full width and each line stays one row: name left
(wraps), quantity right.

**Budget (1366px):**

```
← Shopping lists
Budget                                           (page_header, meta: camp name)
───
[camp_nav, active=shopping]
Estimated cost € 812,40 · € 3,12 per portion per day
Compare with the bills · prices are on the ingredients page
┌ Colruyt ┐ ┌ Bakker ┐ ┌ Slager           ┐
│ € 512,10│ │ € 48,30│ │ € 252,00         │
└─────────┘ └────────┘ │ + 2 without price│
                       └──────────────────┘
(alerts: no price yet / units differ / uncovered days)
Shop on Tuesday 14 Jul  [€ 402,10]
Covers Wed 15 Jul – Fri 17 Jul
┌ Colruyt · € 260,00 ───────────────────────────────────────┐
│ Vegetables                                                 │
│ Ingredient     Qty      Unit price                   Cost  │
│ Prei        1,5 kg   € 2,10/kg  latest, Mon 3 Mar 2026  € 3,15 │
│ Ui          2,0 kg   —                         [⚠ no price] │
└────────────────────────────────────────────────────────────┘
```

- Summary: `p.fs-5` with the total in `fw-semibold`, the per-portion cost after a
  `·`; the two links on the next line in `text-body-secondary`.
- Shop totals: `div.row.g-3` of `col-6 col-md-4 col-xl-2` small cards (label
  `text-body-secondary small`, value `fw-semibold`); partial ones get
  `border-warning` and the "+ N without price" note in `small`.
- Trip heading `h2` with the total as `badge text-bg-secondary`; per shop a card
  (header `h3.h6` with the shop total), per category a `h4.h6.text-body-secondary`
  and a `table.table.table-sm` in `table-responsive`: Qty, Unit price and Cost
  `text-end text-nowrap`; unit price with "this camp"/"latest" and the date
  (`short_date:"year"`) in `small text-body-secondary`; a line without a price gets
  "—" and, in Cost, the ingredient list's badge
  `<span class="badge text-bg-warning"><i class="bi bi-exclamation-triangle" aria-hidden="true"></i> no price</span>`.
- No trips: `empty_state` (icon `cart`) with an action to the shopping page.

**Chiro stock (1366px):**

```
← Chiro Testdorp                                 (only for members)
Stock                                            (page_header, meta: Chiro name)
───
(example alert)
┌ Kitchen utilities ─────────────────────────────────────────┐
│ What your Chiro owns: … (form-text)                         │
│ Name          In stock  Note          Needed by       Delete│
│ [Kookpot 50L] [2]       [..........]  Kamp 2026: 3    [ ]   │
│ [Save]                                                      │
└─────────────────────────────────────────────────────────────┘
┌ Pantry (id="pantry") ───────────────────────────────────────┐
│ Food your Chiro already has … (form-text)                   │
│ Ingredient            Quantity   Delete                     │
│ [Rijst ▾]             [5]        [ ]                        │
│ [+ Add a row]   [Save]                                      │
└─────────────────────────────────────────────────────────────┘
```

- Utilities table built by hand: `table.table.table-sm.align-middle` in
  `table-responsive`, inputs through `|table_input`, field errors as
  `invalid-feedback d-block`, the formset's non-form errors as `alert alert-danger`.
  "Needed by" read-only, "—" in `text-body-secondary`.
- Both cards: header `h2.h5.mb-0`, body: explanation `p.form-text`, the form, a
  `d-flex gap-2 mt-3` actions row (pantry: add-row button from the partial, then
  `btn btn-primary` Save with `bi-check-lg`).

**Camp kitchen utilities (1366px):**

```
Kitchen utilities                                (page_header, meta: camp name)
───
[camp_nav, active=utilities]
What this camp needs. It's compared with the stock of … (text-body-secondary)
┌ To buy ──────────────────────────────────┐   (or: ✓ Everything is in stock.)
│ Kitchen utility  Needed  In stock  To buy│
└──────────────────────────────────────────┘
┌ Needed for this camp ────────────────────┐
│ Kitchen utility        Needed   Delete    │
│ [Kookpot 50 L      ]   [3]      [ ]       │
│ [+ Add a row]   [Save]                    │
└──────────────────────────────────────────┘
```

- "Everything is in stock." as `p.text-success` with `bi-check-circle`, not a badge.
- To-buy numbers `text-end`, To buy `fw-semibold`.

---

### Task 1: "Add a row" for the pantry and the camp's utilities (Claude)

**Files:**
- Modify: `kitchen/views.py`, `kitchen/urls.py`
- Test: `tests/test_stock_rows.py` (new)

**Interfaces:**
- Consumes: `core.rows.row_index`, `partials/_formset_row.html` (context `row`,
  `formset`, `total_forms`), the pattern in `camps/views.py` (`_camp_form_page`,
  `camp_group_row`).
- Produces:
  - URL `pantry_row`: `chiros/<int:chiro_id>/stock/pantry-row/` →
    `pantry_row(request, chiro_id) -> HttpResponse`. `get_chiro` first, then one empty
    pantry row (prefix `pantry`), numbered by `?pantry-TOTAL_FORMS`, with the
    ingredient choices filled.
  - URL `camp_utensil_row`: `camps/<int:camp_id>/utensils/row/` →
    `camp_utensil_row(request, camp_id) -> HttpResponse`. `get_camp` first, then one
    empty `NeedFormSet` row (default prefix `form`), numbered by
    `?form-TOTAL_FORMS`.
  - `_ingredient_choices() -> list[tuple]` in `kitchen/views.py`: the
    `("", "---------")` plus one `(pk, str)` per ingredient list `chiro_stock` builds
    today; used by both the page and the row.
  - Templates (Tasks 4 and 5) use `add_url` = these URLs and the add-row button value
    = the formset prefix (`pantry`, `form`).
  - Without JavaScript: `chiro_stock` with POST `section=pantry` and `add_row=pantry`,
    and `camp_utensils` with POST `add_row=form`, bump that formset's `TOTAL_FORMS`
    by one (through `row_index`), render the page with what was typed, save nothing.

- [ ] **Step 1: Failing tests** (fixtures and clients as in `tests/test_kitchen.py`):
  - `test_pantry_row_gets_the_next_index`: GET `pantry_row?pantry-TOTAL_FORMS=4` → 200,
    `name="pantry-4-ingredient"` in the body, an `option` with an existing ingredient's
    name, and `id="id_pantry-TOTAL_FORMS"` with `value="5"` and `hx-swap-oob`.
  - `test_camp_utensil_row_gets_the_next_index`: GET
    `camp_utensil_row?form-TOTAL_FORMS=3` → `name="form-3-name"`, `list="utensil-names"`,
    TOTAL_FORMS `value="4"`.
  - `test_row_index_is_bounded`: `?form-TOTAL_FORMS=abc` → `form-0-name`;
    `=999999` → `form-1000-name`.
  - `test_pantry_add_row_without_javascript_keeps_what_was_typed`: POST to
    `chiro_stock` with `section=pantry`, `add_row=pantry`, one typed row with an
    ingredient and quantity `2`, and one invalid row (quantity `abc`) → 200, no
    `PantryItem` created, the typed quantity `value="2"` and `pantry-2-ingredient` (one
    more row) in the page, no `alert-danger`.
  - `test_camp_utensils_add_row_without_javascript`: POST `camp_utensils` with
    `add_row=form` and one typed row → 200, nothing saved (`camp_needs(camp)` empty),
    `form-1-name` in the page.
  - `test_rows_on_an_example_are_readable_but_add_row_posts_are_refused`: for an
    example Chiro and camp, as a plain member of another Chiro: both row URLs → 200;
    the two add-row posts → 403.
  - `test_row_urls_need_access`: a camp of another Chiro (not an example) → 404 for
    `camp_utensil_row`; another Chiro's `pantry_row` → 404.
- [ ] **Step 2:** Run `.venv/Scripts/python.exe -m pytest tests/test_stock_rows.py -q`:
  FAIL.
- [ ] **Step 3:** Implement in `kitchen/views.py` and add the two paths to
  `kitchen/urls.py`. The add-row check comes before validation; a bound formset whose
  `add_row` matches is never saved. Copy the POST data before bumping (`data.copy()`).
- [ ] **Step 4:** Run `tests/test_stock_rows.py tests/test_kitchen.py`: PASS.

### Task 2: Shopping page (ui-builder)

**Files:**
- Modify: `templates/shopping/shopping.html`
- Test: `tests/test_ui_move.py`, `tests/test_shopping.py`

**Interfaces:**
- Consumes: `page_header`, `camp_nav` (`active="shopping"`), `empty_state`,
  `camps/_example_note.html`, `planning/_outside_entries.html`; view context as today
  (`plan.trip_lists[i].trip.pk`, `.shop_sections`, `.covered_days`, `section.label`,
  `section.item_count`, `section.items_by_category`).

- [ ] **Step 1: Failing tests:**
  - In `tests/test_ui_move.py`: add `("shopping", lambda camp: [camp.pk])` to
    `CONVERTED_PAGES` and `"shopping/shopping.html"` to `CONVERTED_TEMPLATES`.
  - In `tests/test_shopping.py`:
    - `test_shopping_page_jumps_to_each_trip`: a camp with two trips and a menu
      entry in each trip's days → `id="trip-links"`, and for each trip both
      `href="#trip-<pk>"` and `id="trip-<pk>"`; `href="#trip-links"` (back to top)
      once per trip.
    - `test_shopping_page_without_trips_shows_the_empty_state`: no trips → no
      `trip-links`, no link to `shopping_pdf`, and `bi-cart` in the page.
    - `test_trip_with_nothing_to_buy`: one trip whose days have no menu entries → its
      `id="trip-<pk>"` and "Nothing to buy" are on the page.
    - `test_shopping_warnings_are_alerts`: a camp with an uncovered day →
      `alert-warning` and no `⚠️`.
- [ ] **Step 2:** Run those tests: FAIL.
- [ ] **Step 3:** Rewrite the template per "Shopping page" above. Keep every link,
  the day-picker form (field `trip_dates`, values `Y-m-d`) and the outside-trip remove
  forms (`btn btn-sm btn-outline-danger`, `bi-trash`). Back link removed (the camp nav
  replaces it, as on the planner).
- [ ] **Step 4:** Run `tests/test_shopping.py tests/test_ui_move.py
  tests/test_spec_features.py tests/test_delete_and_remove.py tests/test_i18n.py`:
  PASS.

### Task 3: Budget (builder)

**Files:**
- Modify: `templates/shopping/budget.html`
- Test: `tests/test_ui_move.py`, `tests/test_budget.py`

**Interfaces:**
- Consumes: `back_link` (to `shopping`, label "Shopping lists"), `page_header`,
  `camp_nav` (`active="shopping"`), `empty_state`; context as today (`budget.total`,
  `.cost_per_portion_day`, `.shop_totals`, `.missing`, `.unit_conflicts`,
  `.plan.uncovered_days`, `.trips[].trip_list`, `.trips[].shops[].lines_by_category`).

- [ ] **Step 1: Failing tests:** add `("budget", lambda camp: [camp.pk])` to
  `CONVERTED_PAGES` and the template to `CONVERTED_TEMPLATES`; in `tests/test_budget.py`
  `test_budget_marks_lines_without_a_price`: a trip with an unpriced ingredient →
  `badge text-bg-warning` and "no price"; `test_budget_without_trips_points_to_shopping`:
  no trips → a link to `reverse("shopping", args=[camp.pk])` and `bi-cart`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Rewrite per "Budget" above.
- [ ] **Step 4:** Run `tests/test_budget.py tests/test_ui_move.py`: PASS.

### Task 4: Chiro stock (builder)

**Files:**
- Modify: `templates/kitchen/stock.html`
- Test: `tests/test_ui_move.py`, `tests/test_kitchen.py`

**Interfaces:**
- Consumes: Task 1 (`pantry_row`, button value `pantry`), `recipes/_formset.html` with
  `add_url` and `add_label`, `back_link`, `page_header`, `|table_input`.

- [ ] **Step 1: Failing tests:** add the template to `CONVERTED_TEMPLATES`; in
  `tests/test_kitchen.py` `test_stock_page_layout`: GET `chiro_stock` as a member →
  one `<h1`, `page-rule`, `id="pantry"`, `hx-get="<pantry_row url>"`, and
  `form-control` on the utilities inputs.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Rewrite per "Chiro stock" above. The two forms keep their
  `section` hidden input and their own Save button.
- [ ] **Step 4:** Run `tests/test_kitchen.py tests/test_stock_rows.py
  tests/test_ui_move.py`: PASS.

### Task 5: Camp kitchen utilities (builder)

**Files:**
- Modify: `templates/kitchen/camp_utensils.html`
- Test: `tests/test_ui_move.py`, `tests/test_kitchen.py`

**Interfaces:**
- Consumes: Task 1 (`camp_utensil_row`, button value `form`), `recipes/_formset.html`
  with `add_url`/`add_label`, `page_header`, `camp_nav` (`active="utilities"`).

- [ ] **Step 1: Failing tests:** add `("camp_utensils", lambda camp: [camp.pk])` to
  `CONVERTED_PAGES` and the template to `CONVERTED_TEMPLATES`; in `tests/test_kitchen.py`
  `test_camp_utensils_offers_add_row`: the page has `hx-get="<camp_utensil_row url>"`
  and `<datalist id="utensil-names">`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Rewrite per "Camp kitchen utilities" above.
- [ ] **Step 4:** Run `tests/test_kitchen.py tests/test_ui_move.py`: PASS.

### Task 6: app.css, Dutch strings, static and browser review (Claude, opencode reviewer, ui-reviewer)

**Files:**
- Modify: `static/css/app.css`, `locale/nl/LC_MESSAGES/django.po` (+ `.mo`)

- [ ] **Step 1:** Delete from `app.css` the rules only area 3's old templates used:
  `ul.checkboxes` (all its rules), `.category-block`, `.shop-grid`, `.shop-section`
  (and its child rules), `.shop-title`, `.shop-totals`, `.shop-total*`,
  `.budget-table` (and its child rules), `tr.row-missing`. Check first:
  `grep -rn "<class>" templates` shows no use outside `shopping_print.html`, which
  has its own CSS.
- [ ] **Step 2:** makemessages and msgfmt in Docker; translate the new strings; no
  `#, fuzzy` left among them.
- [ ] **Step 3:** opencode `reviewer` on the five templates, two or three per run
  (ui-guidelines template checks). Fix what holds up.
- [ ] **Step 4:** Throwaway server (CLAUDE.md "Browser testing") with `seed_demo`; add
  an ingredient with a long name (60 characters) to a demo recipe that's on the menu.
  `ui-reviewer` at 1366px and 375px, as `member` and `admin`: shopping page (jump
  links reach each trip and back; trip lists at 375px: Review Focus 5; save shopping
  days), budget, Chiro stock (add a pantry row with and without HTMX, save), camp
  utilities (add a row, save, to-buy table), an example camp's shopping page as
  `member`. Give it the 375px fallback from memory (srcdoc iframe) up front. DESIGN §9
  checklist.
- [ ] **Step 5:** Fix FAIL items (`builder` for one file, `ui-builder` otherwise),
  restart the `--noreload` server, re-run the reviewer with its previous report; at
  most three rounds.

### Task 7: Finish area 3 (Claude)

**Files:**
- Modify: `docs/SPEC.md`, `docs/ui-guidelines.md`, `docs/spec/shopping.md`,
  `pages/content/shopping-and-budget.md`, `pages/content/shopping-and-budget.nl.md`,
  `docs/TODO.md`, `docs/superpowers/specs/2026-11-17-ui-area-3-shopping-design.md`

- [ ] **Step 1:** D20 in `docs/SPEC.md` after D19, worded as in the design; in
  `docs/ui-guidelines.md` the planning-views line gets "except the shopping page's trip
  lists, which work equally on a phone (D20)".
- [ ] **Step 2:** `docs/spec/shopping.md` "Shopping lists": the page links to each
  trip's list from the top, for reading at the pickup. Help pages (EN and NL): one
  line that the trip buttons at the top jump to a trip's list, handy on a phone at the
  pickup. Mark the design "Built; folded into `docs/spec/shopping.md`".
- [ ] **Step 3:** All checks (CLAUDE.md "Checks"); build the Docker image and run
  `tests/test_pdf.py` in it (the shopping PDF still renders).
- [ ] **Step 4:** Whole-area review by Claude (Opus); opencode `secret_reviewer` on the
  staged files, then a pattern scan of the staged diff myself.
- [ ] **Step 5:** In `docs/TODO.md` tick area 3 with the plan path and add a "Found in
  area 3's review" paragraph for what was parked. Commit on `ui/area-3-shopping`, files
  staged by name:

```bash
git commit -m "Move the shopping, budget and stock pages to Bootstrap (UI move, area 3)"
```

- [ ] **Step 6:** Push from Windows and open the PR into `dev` with `gh` (CLAUDE.md
  "Git"), body: what changed, how it was checked, what was parked. Wait for its checks
  (`gh pr checks <n> --watch`) and report them. The repo is public: nothing private in
  the commit or the PR (CLAUDE.md "GitHub").
