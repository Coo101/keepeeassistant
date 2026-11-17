# UI move, area 2: recipes and ingredients. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the recipe and ingredient pages to Bootstrap, crispy forms and the shared
components, laid out for a PC and still usable at 375px, with the three HTMX pieces the
design names for this area: live recipe search, live ingredient search, and live
"scale to … portions".

**Architecture:** Templates first. Three views (`recipe_list`, `recipe_detail`,
`ingredient_list`) learn to return a fragment for an HTMX request through one shared
helper, `core/htmx.py`, which later areas reuse. Two small additions to area 1's
components (a badge next to the title, a second formset in the error summary), one new
component (tag checkboxes), and one small script (the print button). `tests/test_ui_move.py`
gets the recipe pages.

**Tech Stack:** Django 5.2 templates, Bootstrap 5.3, Bootstrap Icons, crispy-bootstrap5,
HTMX 2 with django-htmx, pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-ui-move-design.md` (area 2). Area file:
`docs/spec/recipes.md`. Branch: `ui/area-2-recipes` from `origin/dev` (049332a).

## Global Constraints

- Follow `docs/ui-guidelines.md` (behaviour) and `docs/DESIGN.md` (look). Paste the
  lines a task names into its brief.
- D19: planning views are designed for a **PC at 1366px**, then checked at **375px**:
  no horizontal page scroll, tables scroll inside `table-responsive`, forms in one
  column, nothing cut off. Two-column forms from `lg`.
- Tables stay tables on a PC; don't hide information behind clicks or cards.
- No behaviour, model, permission or business-logic changes. Every link, form and
  no-JavaScript path keeps working; all existing tests keep passing (a test may only
  change where this plan says so).
- HTMX only on the three pieces above. Each also works as a plain GET without
  JavaScript. Every HTMX element sets `hx-target` and `hx-swap` explicitly and has an
  `hx-indicator` (a `spinner-border spinner-border-sm htmx-indicator` with a
  `visually-hidden` "Loading…").
- Every visible text in `{% translate %}` / `{% blocktranslate %}`; new Dutch strings go
  in `locale/nl/LC_MESSAGES/django.po` and the `.mo` is recompiled (README).
- No inline `style=""`, no inline `<script>`, no `onclick`. Colours only from Bootstrap
  classes and the `--chiro-*` tokens. Destructive buttons `btn-outline-danger` with
  `bi-trash`. Badges only for status (`text-bg-success|warning|danger|secondary`).
- Icons next to text get `aria-hidden="true"`; icon-only controls get `aria-label`.
- Dates on screen through the `short_date` filter (`{% load ui %}`).
- Don't touch `recipes/recipe_print.html`. `confirm_delete.html` is area 5.
- Keep `static/js/ingredient_dialog.js` working without changes: it needs
  `#new-ingredient-dialog` with `data-selects` and `data-save-error`, a `form` inside it
  with an input whose name ends in `-name`, `#new-ingredient-errors` (toggled with the
  `hidden` attribute), `#new-ingredient-cancel`, and openers with `data-new-ingredient`.
  The dialog is also included by `bills/bill_detail.html` (area 4); it must keep working
  there.

## Review Focus

1. **Back button after a live search.** HTMX pushes `?q=stoof` into the history; going
   back and forward must show a whole page, never a bare fragment (HTMX's
   history-restore request, and the browser cache serving the fragment for the same
   URL). Tests in Task 1 (`HX-History-Restore-Request` gets the page; responses
   `Vary: HX-Request`).
2. **Scaling while typing odd values** ("0", "-4", "abc", "", "1e5", "2,5"): the live
   ingredient list shows the base quantities or the scaled ones, never a 500 and never
   an empty box. Test in Task 4.
3. **A recipe form posted with errors only in the steps** (a step with a duration but
   no instruction): the summary alert shows at the top, not just the inline error. Tests
   in Tasks 2 and 5.
4. **A search with no matches** in either list, live or not: the empty state with the
   query and a way back to the full list, inside the swapped box. Tests in Tasks 3 and 6.
5. **The new-ingredient dialog on the bill review page** still opens, saves and fills
   the select after the dialog's markup changes. Browser check in Task 9 (bill detail
   in the demo data, as `admin`).

---

## Page layouts (Claude with frontend-design)

Within `DESIGN.md`: sand-soft table and card headers, navy actions, the red rule only
in the page header.

**Recipe list (1366px):** the library is shared, so the page is a searchable index.

```
Recipes                                                   [+ New recipe]
The recipe library is shared between all Chiros.
───
[🔍 Search recipes or ingredients…        ] [Search] [Clear]   ⟳
┌ Soup · 4 ───────────────────────────────────────────────┐
│ Recipe                              Portions     Time    │
│ Tomatensoep                             24      45 min   │
└──────────────────────────────────────────────────────────┘
┌ Hot meal · 12 ──────────────────────────────────────────┐
```

One card per dish type (header `h2.h5` with the label and a count in
`span.text-body-secondary`), each a `table.table-hover.align-middle.mb-0`: name
(link, `fw-semibold`), portions and time `text-end`, time "—" when unknown. The search
form sits outside `#recipe-results`; the cards and the empty states are the fragment.
The input is a `form-control` in an `input-group` (`max-width` from a `col-lg-6`
wrapper), which also fixes the old roadmap item "recipe search box focus ring".

**Recipe page (1366px):**

```
← All recipes
Spaghetti bolognese  [read-only]                                  [✎ Edit]
Hot meal · base: 20 children + 10 teens = 24 portions · 45 min total · by jan
───
Scale to [ 24 ] portions [Scale] ⟳          [⇩ PDF] [🖨 Print]   [🗑 Delete]
(locked note, alert-secondary, when locked_by_others)
┌ Ingredients · 36 portions × 1,50  Reset ┐ ┌ Steps ─────────────────────┐
│ Prei                       1,5 kg       │ │ 1. Snij de prei (10 min)   │
└─────────────────────────────────────────┘ └────────────────────────────┘
┌ Notes ──────────┐
┌ Save a copy ────────────────────────────────┐
│ New name [Spaghetti bolognese (kopie)] [Save copy] │
└─────────────────────────────────────────────┘
```

Ingredients `col-lg-5`, steps `col-lg-7`. The ingredients card (`#recipe-ingredients`)
is the scaling fragment; the PDF link (`#recipe-pdf-link`) is updated out of band so
it keeps the typed portions. The Reset link moves into the ingredients card header,
so it shows and hides with the scale. Toolbar and copy card are `d-print-none`.

**Recipe form (1366px):**

```
← Back to the recipe            (new: ← All recipes)
Edit Spaghetti bolognese        (new: New recipe)
───
[⚠ Planned in 3 camps. …]                  (alert-warning, when camp_count)
[! Some fields need your attention; see below.]
┌ Recipe ─────────────────────────────────────────┐
│ Name [..............]     Dish type [.........] │
│ Children [..]             Teens [..]            │
│ Notes [....................................]    │
│ [x] Others can edit                             │
└─────────────────────────────────────────────────┘
┌ Ingredients ────────────────── [+ New ingredient]┐
│ rows table · [+ Add ingredient]                 │
└─────────────────────────────────────────────────┘
┌ Steps ──────────────────────────────────────────┐
│ rows table · [+ Add step]                       │
└─────────────────────────────────────────────────┘
                                     [✓ Save recipe]
```

Field columns: `name`, `dish_type`, `base_children`, `base_teens` `col-lg-6`; `notes`
and `others_can_edit` `col-12`.

**New-ingredient dialog:** native `<dialog>` (the script uses `showModal()`), Bootstrap
inside: `h2.h5`, intro `p.text-body-secondary`, error box `alert alert-danger`, fields
through crispy in `row g-3` (`col-md-6` each; tags and the checkbox `col-12`), buttons
bottom-right: Cancel `btn-outline-primary`, Add `btn-primary`.

**Ingredient list (1366px):**

```
Ingredients                                             [+ New ingredient]
Shared between all Chiros. A new price goes into the history …
───
[🔍 Search ingredients…        ] [Search] [Clear]   ⟳
┌ Ingredient │ Unit │ Category │ Shop │ Price │ Product │ Price date │      ┐
│ Wraps      │ stuk │ Bakery   │ Colr │ € 0,35│ …       │ ma 3 mrt 2026 │ [✎ Edit] │
│ Mais       │ kg   │ …        │      │ [⚠ no price]    │ —          │ [✎ Edit] │
└─────────────────────────────────────────────────────────────────────────┘
```

Name links to the edit page too. "no price" is a `badge text-bg-warning` with
`bi-exclamation-triangle` (a budget gap, so a status). Price `text-end`, `text-nowrap`.

**Ingredient form (1366px):** form and price history side by side on edit.

```
← All ingredients
Edit Wraps
The name and unit are fixed because recipes rely on them. …
───
┌ Ingredient (col-lg-7) ──────────────┐ ┌ Price history (col-lg-5) ┐
│ Name [....]       Unit [....]       │ │ Date      Price    Source│
│ Category          Shop              │ │ ma 3 mrt  € 0,35/stuk …  │
│ New price         Product details   │ └──────────────────────────┘
│ Contains: [ ]gluten [ ]lactose …    │
│ [x] Tags checked                    │
└─────────────────────────────────────┘
[🗑 Delete ingredient]          [✓ Save ingredient]
```

New ingredient: the form card full width (`col-12`), no history.

---

### Task 1: The fragment-or-page helper (Claude)

**Files:**
- Create: `core/htmx.py`
- Test: `tests/test_htmx_helper.py`

**Interfaces:**
- Produces: `render_page_or_fragment(request: HttpRequest, page: str, fragment: str,
  context: dict) -> HttpResponse` in `core/htmx.py`. Renders `fragment` when
  `request.htmx` is true and it is not a history-restore request
  (`request.htmx.history_restore_request`), else `page`. The context it renders gets
  `is_fragment` (True only for the fragment). Always adds `HX-Request` to the `Vary`
  header (`django.utils.cache.patch_vary_headers`).

- [ ] **Step 1: Failing tests.** Requests from `RequestFactory` with
  `request.htmx = HtmxDetails(request)` (`django_htmx.middleware`); templates from an
  `override_settings(TEMPLATES=[...])` whose only loader is
  `("django.template.loaders.locmem.Loader", {"page.html": "PAGE", "frag.html":
  "FRAG {{ is_fragment }}"})`:
  - `test_plain_request_gets_the_page`
  - `test_htmx_request_gets_the_fragment` (header `HX-Request: true`; body
    `FRAG True`)
  - `test_history_restore_gets_the_page` (headers `HX-Request: true` and
    `HX-History-Restore-Request: true`)
  - `test_response_varies_on_hx_request`: `"HX-Request" in response["Vary"]`.
- [ ] **Step 2:** Run `.venv/Scripts/python.exe -m pytest tests/test_htmx_helper.py -q`:
  FAIL (no module).
- [ ] **Step 3:** Write `core/htmx.py` (module docstring pointing at
  ui-guidelines "HTMX patterns").
- [ ] **Step 4:** Run: PASS.

### Task 2: Component additions (builder)

**Files:**
- Modify: `templates/components/page_header.html`, `templates/components/form_errors.html`
- Create: `templates/components/checkbox_chips.html`
- Test: `tests/test_ui_components.py`

**Interfaces:**
- Produces:
  - `page_header.html` optional `badge`: inside the `h1`, after the title,
    `<span class="badge text-bg-secondary fs-6 align-middle ms-2">{{ badge }}</span>`.
    Without it the output is unchanged.
  - `form_errors.html` optional `formset2`: the summary also shows when
    `formset2.total_error_count`.
  - `checkbox_chips.html` with `field` (a `MultipleChoiceField` with
    `CheckboxSelectMultiple`): a `fieldset` with `legend.form-label.fs-6` (the label),
    the options in `div.d-flex.flex-wrap.gap-3`, each `div.form-check` with a hand-written
    `<input class="form-check-input" type="checkbox" name="{{ choice.data.name }}"
    value="{{ choice.data.value }}" id="{{ choice.id_for_label }}"{% if
    choice.data.selected %} checked{% endif %}>` and `label.form-check-label`, then
    `div.form-text` with the help text and `div.invalid-feedback.d-block` per error.

- [ ] **Step 1: Failing tests:**
  - `test_page_header_badge`: with `badge="read-only"` the `h1` contains
    `text-bg-secondary` and "read-only"; without it, no `badge`.
  - `test_form_errors_sees_the_second_formset`: a valid form, `formset` valid, and an
    invalid `StepFormSet` (prefix `steps`, `TOTAL_FORMS=1`, row with
    `duration_minutes=5` and no instruction) as `formset2` renders `alert-danger`.
  - `test_checkbox_chips`: `IngredientForm(user=None, initial={"tags": [first tag]})`
    (`user` is only used on save) renders through the component with one `<legend`,
    one `form-check-input` per `FoodTag.CHOICES` entry, and `checked` on a choice passed
    as initial.
- [ ] **Step 2:** Run `tests/test_ui_components.py`: FAIL.
- [ ] **Step 3:** Write the three templates.
- [ ] **Step 4:** Run `tests/test_ui_components.py tests/test_ui_move.py
  tests/test_base_layout.py`: PASS. Add `"components/checkbox_chips.html"` to
  `CONVERTED_TEMPLATES`.

### Task 3: Recipe list with live search (ui-builder)

**Files:**
- Modify: `templates/recipes/recipe_list.html`, `recipes/views.py` (`recipe_list` only)
- Create: `templates/recipes/_recipe_results.html`
- Test: `tests/test_ui_move.py`, `tests/test_recipe_views.py`

**Interfaces:**
- Consumes: `render_page_or_fragment` (Task 1).
- Produces: `RECIPE_PAGES: list[tuple[str, Callable[[Recipe], list]]]` in
  `tests/test_ui_move.py` and `test_recipe_page_has_one_h1_and_the_red_rule`,
  parametrized over it: `client = account_client()`, then `recipe =
  make_recipe("Stoofpot", ingredients=[("Prei", "1", KG, PRODUCE)])` with `author` set
  to the user `kok` and saved (so `recipe_edit` is allowed), GET, status 200, one
  `<h1`, not empty, `page-rule` present. Tasks 4–7 append to it.

- [ ] **Step 1: Failing tests:** create `RECIPE_PAGES` with `("recipe_list", lambda r:
  [])` and its test; add both templates to `CONVERTED_TEMPLATES`. In
  `tests/test_recipe_views.py`:
  - `test_recipe_search_htmx_returns_the_results_only`: GET `?q=Stoof` with
    `HTTP_HX_REQUEST="true"`: no `<h1`, no `<html`, contains "Stoofpot", and
    `id="recipe-results"` is not in it (the fragment is the box's inside).
  - `test_recipe_search_without_matches`: `?q=zzz`, plain and HTMX: both contain
    `bi-search` and the text `No recipes match "zzz".` (HTML-escaped quotes allowed)
    and a link to `reverse("recipe_list")`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Layout per "Recipe list" above:
  - `page_header` title "Recipes", meta "The recipe library is shared between all
    Chiros." (new string, NL "De receptenbibliotheek is gedeeld door alle Chiro's."),
    action `recipe_create`, label "New recipe", icon `plus-lg`.
  - Search `form[method=get][role=search]` with `label.visually-hidden` "Search recipes"
    for `#recipe-search`, `input#recipe-search.form-control[type=search][name=q]`
    with `hx-get="{% url 'recipe_list' %}" hx-trigger="input changed delay:300ms,
    search" hx-target="#recipe-results" hx-swap="innerHTML" hx-push-url="true"
    hx-indicator="#recipe-search-busy"`, submit `btn btn-primary` "Search" with
    `bi-search`, Clear `btn btn-outline-primary` only with a query, the spinner.
  - `div#recipe-results` includes `_recipe_results.html`: the cards; no recipes at all →
    `empty_state` icon `journal` "No recipes yet." with action "Add the first one" to
    `recipe_create`; a query without matches → `empty_state` icon `search` with the
    `No recipes match "…".` text and action "Show all recipes" to `recipe_list`.
  - View: `return render_page_or_fragment(request, "recipes/recipe_list.html",
    "recipes/_recipe_results.html", {...})`; the context is unchanged.
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_recipe_views.py
  tests/test_query_counts.py tests/test_i18n.py`: PASS.

### Task 4: Recipe page with live scaling (ui-builder)

**Files:**
- Modify: `templates/recipes/recipe_detail.html`, `recipes/views.py` (`_render_detail`)
- Create: `templates/recipes/_recipe_ingredients.html`,
  `templates/recipes/_recipe_pdf_link.html`, `static/js/print.js`
- Test: `tests/test_ui_move.py`, `tests/test_recipe_views.py`

**Interfaces:**
- Consumes: `render_page_or_fragment` (Task 1), `page_header` `badge` (Task 2).
- Produces: `_recipe_pdf_link.html` with optional `oob`; when true the link carries
  `hx-swap-oob="true"`. `static/js/print.js`: every `[data-print]` button calls
  `window.print()` on click.

- [ ] **Step 1: Failing tests:** add `("recipe_detail", lambda r: [r.pk])` to
  `RECIPE_PAGES` and the four templates to `CONVERTED_TEMPLATES` (not the `.js`). In
  `tests/test_recipe_views.py`:
  - `test_recipe_scaling_htmx_returns_the_ingredients`: `?portions=20` with
    `HTTP_HX_REQUEST="true"`: contains "5 kg", `id="recipe-ingredients"`,
    `id="recipe-pdf-link"` with `hx-swap-oob="true"` and `portions=20`; no `<h1`.
  - `test_recipe_scaling_htmx_ignores_odd_values`: for `"0"`, `"-4"`, `"abc"`, `""`,
    `"1e5"`: status 200 and "2.5 kg" in the HTMX response; for `"2,5"` (read as 2.5
    portions, × 0,25) status 200 and "2.5 kg" not in it.
  - `test_recipe_page_has_no_inline_handlers`: the plain page has no `onclick` and has
    `data-print`.
  - Keep `tests/test_recipe_sharing.py:84` passing ("read-only" on the page).
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Layout per "Recipe page" above:
  - Back link "All recipes" (existing string "all recipes" stays for the print view;
    add "All recipes" if missing). `page_header` with `title=recipe.name`,
    `badge` "read-only" when not `can_edit`, meta: dish type, the base sentence (as
    today, without `<strong>`), total minutes, author; action Edit (`bi-pencil`,
    outline) when `can_edit`.
  - Toolbar `div.d-flex.flex-wrap.align-items-center.gap-2.mb-3.d-print-none`: the scale
    form (`form[method=get]` with `label.form-label.mb-0` "Scale to",
    `input#portions-input.form-control` in a fixed-width `input-group`
    (`input-group` with `w-auto` and the input `size` attribute, no `style`), the
    "portions" `input-group-text`, submit `btn btn-outline-primary` "Scale"), its
    spinner; then `ms-auto` the PDF link include, Print (`btn btn-outline-primary`,
    `bi-printer`, `type="button" data-print`), Delete (`btn btn-outline-danger`,
    `bi-trash`) when `can_delete`.
  - The scale form gets `hx-get="{% url 'recipe_detail' recipe.pk %}"
    hx-trigger="input changed delay:400ms from:#portions-input, submit"
    hx-target="#recipe-ingredients" hx-swap="outerHTML" hx-push-url="true"
    hx-indicator="#recipe-scale-busy"`.
  - Locked note: `div.alert.alert-secondary.d-print-none` with `bi-lock`.
  - `div.row.g-4`: `col-lg-5` includes `_recipe_ingredients.html`
    (`div#recipe-ingredients.card.shadow-sm`, header `h2.h5` "Ingredients" plus, when
    scaled, `span.text-body-secondary` "N portions · × S" and a Reset link
    `d-print-none` to the unscaled page; body `table.table.table-sm.mb-0`, quantity
    `text-end text-nowrap`; no rows → "No ingredients entered yet." in
    `p.text-body-secondary.fst-italic`). The fragment ends with
    `{% if is_fragment %}{% include "recipes/_recipe_pdf_link.html" with oob=True %}{% endif %}`,
    so the full page has one PDF link. `col-lg-7`: Steps card, `ol` with the minutes
    in `span.text-body-secondary`.
  - Notes card (`h2.h5`, body `{{ recipe.notes|linebreaks }}`), then the copy card
    `d-print-none`: `{{ copy_form.name|as_crispy_field }}` and `btn btn-outline-primary`
    "Save copy" (`bi-copy`) in a `row g-2 align-items-end`.
  - `{% block scripts %}{% load assets %}<script src="{% asset 'js/print.js' %}"
    defer></script>{% endblock %}`.
  - View: `_render_detail` returns `render_page_or_fragment(request,
    "recipes/recipe_detail.html", "recipes/_recipe_ingredients.html", context)`.
    `recipe_copy`'s error path still renders the whole page (a POST, not HTMX).
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_recipe_views.py
  tests/test_recipe_sharing.py tests/test_query_counts.py`: PASS.

### Task 5: Recipe form and the new-ingredient dialog (ui-builder)

**Files:**
- Modify: `templates/recipes/recipe_form.html`, `templates/recipes/_new_ingredient_dialog.html`
- Test: `tests/test_ui_move.py`, `tests/test_recipe_form_rows.py`

**Interfaces:**
- Consumes: `form_errors` `formset2`, `checkbox_chips` (Task 2).

- [ ] **Step 1: Failing tests:** add `("recipe_create", lambda r: [])` and
  `("recipe_edit", lambda r: [r.pk])` to `RECIPE_PAGES`, and both templates to
  `CONVERTED_TEMPLATES`. In `tests/test_recipe_form_rows.py`:
  - `test_step_errors_show_the_summary`: POST the new-recipe form with a valid recipe
    and one step row with `duration_minutes=5` and no instruction: 200,
    `alert-danger` and `is-invalid` in the HTML.
  - `test_dialog_keeps_its_script_hooks`: the new-recipe page contains
    `id="new-ingredient-dialog"`, `data-selects=`, `data-save-error=`,
    `id="new-ingredient-errors"`, `id="new-ingredient-cancel"`,
    `name="new_ingredient-name"` and `data-new-ingredient`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Layout per "Recipe form" above, `{% load crispy_forms_tags %}`:
  - back link and `page_header` as today's two branches; the camp warning as
    `div.alert.alert-warning` with `bi-exclamation-triangle` (same text);
    `form_errors` with `form=form formset=ingredients formset2=steps`.
  - Keep the hidden first submit button and its comment.
  - Recipe card: fields through `as_crispy_field` in the columns above.
  - Ingredients card: header `d-flex justify-content-between align-items-center` with
    `h2.h5.mb-0` and the "New ingredient" opener (`btn btn-sm btn-outline-primary`,
    `bi-plus-circle`, `type="button" data-new-ingredient`); the "Missing one?" line
    goes. Body: the `_formset.html` include exactly as today. Steps card the same
    without the opener.
  - Save: `div.d-flex.justify-content-end.mt-4`, `btn btn-primary`, `bi-check-lg`.
  - Dialog per "New-ingredient dialog" above; `tags` through `checkbox_chips`, every
    other field `as_crispy_field`. Keep every hook listed in Global Constraints.
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_recipe_form_rows.py
  tests/test_recipe_views.py tests/test_recipe_sharing.py tests/test_spec_features.py`:
  PASS. Also `tests/` matching `bill` (the bill page includes the dialog):
  `.venv/Scripts/python.exe -m pytest -q -k bill`.

### Task 6: Ingredient list with live search (builder)

**Files:**
- Modify: `templates/recipes/ingredient_list.html`, `recipes/views.py` (`ingredient_list` only)
- Create: `templates/recipes/_ingredient_results.html`
- Test: `tests/test_ui_move.py`, `tests/test_recipe_views.py`

**Interfaces:**
- Consumes: `render_page_or_fragment` (Task 1).

- [ ] **Step 1: Failing tests:** add `("ingredient_list", lambda r: [])` to
  `RECIPE_PAGES`, both templates to `CONVERTED_TEMPLATES`. In
  `tests/test_recipe_views.py`:
  - `test_ingredient_search_htmx_returns_the_table_only`: `?q=Pre` with
    `HTTP_HX_REQUEST="true"`: no `<h1`, contains "Prei".
  - `test_ingredient_without_price_is_flagged`: the list shows `text-bg-warning` and
    "no price" for an ingredient with no price; after `set_price("Prei", "1.20")` it
    shows `1.20` (the tests run in English).
  - `test_ingredient_search_without_matches`: `?q=zzz` shows `bi-search` and
    `No ingredients match "zzz".`
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Same search form as Task 3 with ids `ingredient-search`,
  `ingredient-results`, `ingredient-search-busy`, label "Search ingredients". Header:
  title "Ingredients", meta today's sentence, action `ingredient_create` "New
  ingredient" `plus-lg`. The table per "Ingredient list" above in
  `div.card.shadow-sm > div.table-responsive > table.table.table-hover.align-middle.mb-0`,
  header `scope="col"`, the last column header `span.visually-hidden` "Actions"; price
  date `{{ ingredient.latest_price_date|short_date:"year"|default:"—" }}` (check the
  filter returns "" for `None`; if not, guard with `{% if %}`). Empty states: none at
  all → icon `basket` "No ingredients yet." + "Add the first one"; no match → icon
  `search` + "Show all ingredients". View uses `render_page_or_fragment`.
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_recipe_views.py
  tests/test_camp_ingredient_screens.py tests/test_query_counts.py`: PASS.

### Task 7: Ingredient form (builder)

**Files:**
- Modify: `templates/recipes/ingredient_form.html`
- Test: `tests/test_ui_move.py`

**Interfaces:**
- Consumes: `form_errors`, `checkbox_chips` (Task 2).

- [ ] **Step 1: Failing tests:** add `("ingredient_create", lambda r: [])` and
  `("ingredient_edit", lambda r: [r.ingredients.first().ingredient_id])` to
  `RECIPE_PAGES`, the template to `CONVERTED_TEMPLATES`, and
  `test_ingredient_form_errors_show_a_summary`: POST `ingredient_create` with the name
  of an existing ingredient ("Prei"): 200, `alert-danger`, `is-invalid`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Layout per "Ingredient form" above: back link "All ingredients";
  `page_header` with today's titles and meta lines; `form_errors`; on edit
  `div.row.g-4` with the form card `col-lg-7` and the price history card `col-lg-5`
  (`table.table.table-sm.mb-0`, date `short_date:"year"`, price `text-end text-nowrap`),
  on create the form card alone. Fields `col-lg-6` except `tags`
  (`checkbox_chips`, `col-12`) and `tags_checked` (`col-12`). Disabled name and unit
  render through crispy as disabled inputs. Actions row like the camp form: delete
  (`btn-outline-danger`, `bi-trash`, edit only) first, save (`btn-primary`,
  `bi-check-lg`, `ms-auto`).
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_camp_ingredient_screens.py
  tests/test_delete_and_remove.py tests/test_spec_features.py`: PASS.

### Task 8: app.css and the static review (Claude, opencode reviewer)

**Files:**
- Modify: `static/css/app.css`

- [ ] **Step 1:** Scope the old global input rule so Bootstrap controls keep their own
  look: `select, input[type="text"], input[type="number"] { … }` and `select:focus`
  become `:where(select, input[type="text"], input[type="number"]):not(.form-control,
  .form-select)` (same body). Pages not yet moved keep the old look.
- [ ] **Step 2:** Delete `ul.recipe-grid`, `.recipe-card*`, `.recipe-columns` (both the
  rule, its media query and the print one), `.recipe-steps`, `.recipe-notes`. Keep
  `dialog` and `dialog::backdrop` (Bootstrap doesn't style `<dialog>`); change
  `dialog`'s border to `var(--bs-border-color)` and radius to `var(--bs-border-radius-lg)`,
  and `dialog h2 { margin-top: 0; }` can go (the heading uses `mt-0`).
- [ ] **Step 3:** `grep -rn "recipe-grid\|recipe-card\|recipe-columns\|recipe-steps\|
  recipe-notes\|no-print" templates/recipes static/css` shows only `recipe_print.html`
  and its own CSS (if it uses them).
- [ ] **Step 4:** opencode `reviewer` on the changed templates, three files per run
  (ui-guidelines template checks). Fix what it finds that holds up.
- [ ] **Step 5:** `.venv/Scripts/python.exe -m pytest tests/test_ui_move.py -q`: every
  case passes.

### Task 9: Browser review (ui-reviewer)

- [ ] **Step 1:** Throwaway server (CLAUDE.md "Browser testing") with `seed_demo`.
- [ ] **Step 2:** `ui-reviewer` at 1366px and 375px, as `member` and as `admin`, on:
  recipe list (type a search, then Back and Forward: Review Focus 1), a recipe page
  (type 0, 36 and 2,5 into the scale box; PDF link follows; Print opens the print
  dialog: check only that it's wired, then cancel), a recipe the member didn't write
  (read-only badge, no Edit/Delete), the recipe form (add an ingredient and a step row;
  save with a step error), the new-ingredient dialog (save one; error for a duplicate name),
  ingredient list (search, no-price badge), ingredient form (new and edit). Then the
  dialog on a bill's detail page as `admin` (Review Focus 5). DESIGN §9 checklist.
- [ ] **Step 3:** Fix FAIL items (`builder` for one file, `ui-builder` otherwise),
  re-run the reviewer with its previous report; at most three rounds.

### Task 10: Finish area 2 (Claude)

- [ ] **Step 1:** Help pages `pages/content/recipes.md` and `recipes.nl.md`: describe
  the search filtering as you type and the scale box updating as you type, if they
  describe either; mention the PDF follows the scale.
- [ ] **Step 2:** All checks: ruff, black, pytest, `makemigrations --check --dry-run`
  (CLAUDE.md "Checks"). Build the Docker image and run `tests/test_pdf.py` in it: the
  recipe PDF still renders.
- [ ] **Step 3:** Claude reviews the whole area diff; opencode `secret_reviewer` on the
  staged files.
- [ ] **Step 4:** In `docs/TODO.md`, tick area 2 and change step 3's "committed on
  `dev`" to "committed on its own branch and merged into `dev` by PR". Commit on
  `ui/area-2-recipes`, files staged by name:

```bash
git commit -m "Move the recipe and ingredient pages to Bootstrap (UI move, area 2)"
```

- [ ] **Step 5:** Push from WSL and open the PR into `dev` with `gt` (CLAUDE.md "Git"),
  body: what changed, how it was checked, what was parked.
