# Kitchen Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phone screens for the kookploeg during the camp (day view with a shared
ingredient check, extra shopping list, cooking view with timers, evaluation notes,
day sheet PDF, pantry count) plus the menu evaluation after the camp.

**Architecture:** Everything new lives in the existing `kitchen` app, split into
small modules by job (`day.py` builds the day, `checks.py` the check and extra list,
`evaluation.py` notes and history, `pantry_count.py`). Views are server-rendered
Django with HTMX swaps that fall back to plain form posts. Timers are one plain JS
file. `recipes` gets one field, `Recipe.copied_from`.

**Tech Stack:** Django 5, Bootstrap 5.3, HTMX + django-htmx, crispy-bootstrap5,
WeasyPrint (via `core/pdf.py`), pytest, ruff, black.

**Spec:** `docs/superpowers/specs/2026-11-16-kitchen-mode-design.md` (read it
first), `docs/SPEC.md` (rules for every area), and `docs/spec/kitchen.md`,
`planning.md` (meal slots, scaling), `shopping.md` (pantry), `accounts.md` (access).

## Global Constraints

- Prerequisite: TODO step 4 (UI on Bootstrap and HTMX) should be done; at minimum
  use its components (`components/page_header.html`, `components/empty_state.html`).
- No JS except `static/js/kitchen_timers.js`; no inline scripts or `style=""`;
  custom CSS only in `static/css/app.css`; link own assets with `{% asset %}`.
- Every POST works without JS: HTMX requests (`request.htmx`) get a partial, plain
  posts get a redirect back (to the same anchor).
- Kitchen screens: base font ≥ 1.125rem, quantities and step text `fs-4` or larger,
  tap targets ≥ 44×44px, enlarged checkboxes/buttons.
- Access: every new view gets its camp through `camps.access.get_camp` (non-member →
  404, POST on an example camp → 403). A date outside the camp → 404 (`docs/SPEC.md`, Errors).
  No extra role needed for anything here.
- **Nothing in this plan writes to `Recipe`, `RecipeIngredient` or `RecipeStep`**,
  except `copy_recipe` setting `copied_from` on a new copy.
- Quantities: scale per entry with `core.portions.scale_factor(camp.demand_portions,
  recipe.base_portions)`, sum per ingredient within a meal, round **after** summing
  with `round_quantity`, display with `format_quantity`. No pantry subtraction.
- All user-facing text in English, marked for translation; Dutch added to
  `locale/nl/` (Task 12). Type hints, `logging` not `print`, ruff + black clean.
- Fixed query counts on the day view, extra list and menu evaluation (assert with
  `django_assert_max_num_queries` as in `tests/test_query_counts.py`).
- Commits: CLAUDE.md says commit only when the user asks. Each task ends with a
  commit step that runs only if the user has asked for commits; stage files by name.

## Review Focus

1. **Two phones press at once.** A double post for the same line must not raise
   `IntegrityError`: use `update_or_create` and expect 200/302. Test in Task 4.
2. **Menu changed after checking.** An ingredient no longer in the meal: its check is
   not shown and not counted; posting a check for it → 404; its extra-list line
   stays. Test in Task 4.
3. **Outsiders and examples on every new URL**, including the HTMX endpoints and
   the PDF: non-member 404, example POST 403. Parametrised test in Task 3, extended
   by each later task with its URLs.
4. **Notes stay private to the Chiro.** Recipe history on a shared recipe never shows
   another Chiro's camp notes, also through `copied_from`. Test in Task 9.
5. **Pantry count input.** `2.5` saves, negative is a form error, the same
   ingredient added twice is a form error (no 500), a blank line leaves its value
   alone. Tests in Task 10.

---

### Task 1: Kitchen models and `Recipe.copied_from`

**Files:**
- Modify: `kitchen/models.py`, `kitchen/admin.py`, `recipes/models.py`,
  `recipes/services.py` (`copy_recipe`)
- Create: migrations via `makemigrations kitchen recipes`
- Test: `tests/test_kitchen_mode_models.py`

**Interfaces:**
- Produces (all in `kitchen/models.py`):
  - `IngredientCheck(camp FK Camp CASCADE related_name="ingredient_checks", date,
    meal_type (MealType.CHOICES), ingredient FK CASCADE, status, checked_by FK user
    SET_NULL null, checked_at auto_now)`; `IngredientCheck.Status.THERE = "there"`,
    `.MISSING = "missing"` (TextChoices); unique `camp, date, meal_type, ingredient`
    named `unique_ingredient_check`.
  - `ExtraShoppingItem(camp FK CASCADE related_name="extra_items", ingredient FK
    null/blank CASCADE, text Char(200) blank, quantity Decimal(10,3) null,
    amount_text Char(50) blank, check OneToOne IngredientCheck null SET_NULL
    related_name="extra_item", meal_date Date null, meal_type blank, bought bool,
    bought_by FK user null SET_NULL, bought_at null, added_by FK user null
    SET_NULL, added_at auto_now_add)`; CheckConstraint
    `extra_item_has_ingredient_or_text`: ingredient not null OR text ≠ "".
    Ordering `["bought", "added_at"]`. `__str__` → ingredient name or text.
  - `DayEvaluation(camp, date, text TextField, updated_by, updated_at auto_now)`;
    unique `camp, date`.
  - `RecipeEvaluation(camp, date, recipe FK CASCADE related_name="evaluations", tag,
    text TextField blank, updated_by, updated_at auto_now)`; `RecipeEvaluation.Tag`
    TextChoices `GOOD="good"`, `TOO_LITTLE="too_little"`, `TOO_MUCH="too_much"`,
    `ADJUST="adjust"` (labels "Good", "Too little", "Too much", "Adjust recipe"),
    tag blank allowed; unique `camp, date, recipe`.
  - `Recipe.copied_from = ForeignKey("self", null, blank, SET_NULL,
    related_name="copies")` and `Recipe.lineage() -> list[Recipe]`: self first,
    then each ancestor, stopping at 20 or on a repeat.

- [ ] **Step 1: Write the failing tests**

```python
def test_one_check_per_meal_line(camp, onion): ...
    # second IngredientCheck.objects.create(same key) raises IntegrityError
def test_extra_item_needs_ingredient_or_text(camp): ...
    # ExtraShoppingItem(camp=camp) save -> IntegrityError; text="Afwasmiddel" saves
def test_copy_remembers_its_original(): ...
    # copy = copy_recipe(original, "Soep (kopie)", user); copy.copied_from == original
    # copy_recipe(copy, ...).lineage() == [copy2, copy, original]
def test_deleting_the_original_keeps_the_copy(): ...
    # original.delete() (no camp plans it); copy.refresh_from_db(); copied_from is None
```

- [ ] **Step 2: Run** `.venv/Scripts/python.exe -m pytest tests/test_kitchen_mode_models.py -q` → FAIL (import errors).
- [ ] **Step 3: Add the models, `lineage()`, set `copied_from=recipe` in `copy_recipe`, register the four models in `kitchen/admin.py`, run `DJANGO_DEBUG=1 .venv/Scripts/python.exe manage.py makemigrations kitchen recipes`.**
- [ ] **Step 4: Run** the tests → PASS; `makemigrations --check --dry-run` → "No changes detected".
- [ ] **Step 5: Commit** (if asked): `kitchen/ recipes/ tests/test_kitchen_mode_models.py`.

### Task 2: Building the day (`kitchen/day.py`)

**Files:**
- Create: `kitchen/day.py`
- Test: `tests/test_kitchen_day.py`

**Interfaces:**
- Consumes: `IngredientCheck` (Task 1); `camp.menu_entries`; `core.portions`.
- Produces:
  - `@dataclass IngredientLine: ingredient: Ingredient; quantity: Decimal (rounded);
    unit: str; status: str  # "" | "there" | "missing"`
  - `@dataclass MealPlan: meal_type: str; label: str; time: datetime.time | None;
    recipes: list[Recipe]; lines: list[IngredientLine]` with properties
    `missing_count: int`, `unchecked_count: int`, `all_there: bool` (lines and no
    missing/unchecked).
  - `day_plan(camp: Camp, date: datetime.date) -> list[MealPlan]`: all four meals in
    `MealType.ORDER`, with the camp's `breakfast_time` / `lunch_time` /
    `teatime_time` / `dinner_time`; recipes in course order (soup, main, extra,
    dessert per `docs/spec/planning.md`); lines sorted by category then name.
  - `meal_line(camp, date, meal_type, ingredient_id) -> IngredientLine | None`.

- [ ] **Step 1: Write the failing tests** (factories from `tests/factories.py`;
  camp of 30 teens + 20 children + 8 staff → 52 portions)

```python
def test_meal_lines_merge_recipes():
    # soup: Ui 1 kg per 10 teens, main: Ui 0.5 kg per 10 teens, both at lunch
    # -> one "Ui" line, quantity == round_quantity(Decimal("1.5") * Decimal("5.2"), "kg") == Decimal("7.8")
def test_rounding_happens_after_summing():
    # two recipes each 0.004 kg per 10 teens -> one line 0.1 kg (not 0.2)
def test_empty_meal_has_no_lines():
    # tea with nothing planned: recipes == [], lines == [], all_there is False
def test_status_comes_from_the_checks():
    # IngredientCheck(status="missing") for Ui at lunch -> line.status == "missing";
    # lunch.missing_count == 1, unchecked_count == number of other lines
def test_checks_for_ingredients_not_in_the_meal_are_ignored():
    # check row for "Wortel" at lunch, Wortel in no lunch recipe -> not in lines, not counted
def test_day_plan_query_count(django_assert_max_num_queries):
    # 4 meals x 3 recipes x 5 ingredients -> day_plan runs in <= 4 queries
```

- [ ] **Step 2: Run** `pytest tests/test_kitchen_day.py -q` → FAIL.
- [ ] **Step 3: Implement** with one entries query (`select_related("recipe")`,
  `prefetch_related("recipe__ingredients__ingredient")`) and one checks query for
  the day; sum unrounded `Decimal`s per `(meal_type, ingredient_id)` first.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** (if asked).

### Task 3: Day view, URLs and links

**Files:**
- Modify: `kitchen/urls.py`, `kitchen/views.py` (or create `kitchen/day_views.py`
  if `views.py` grows past ~250 lines), `templates/camps/` camp list template,
  `templates/planning/planner.html`, `static/css/app.css`
- Create: `templates/kitchen/day.html`, `templates/kitchen/_meal.html`
- Test: `tests/test_kitchen_views.py`

**Interfaces:**
- Consumes: `day_plan` (Task 2).
- Produces:
  - `get_camp_day(request, camp_id: int, day: str) -> tuple[Camp, datetime.date]` in
    `kitchen/views.py`: `get_camp` + ISO date parse; 404 if invalid or not in
    `camp.days`.
  - URL names: `kitchen_today` (`camps/<int:camp_id>/kitchen/`), `kitchen_day`
    (`camps/<int:camp_id>/kitchen/<str:day>/`).
  - `templates/kitchen/_meal.html` renders one `MealPlan` with id
    `meal-<meal_type>`; Task 4 swaps it.
  - Context of `kitchen_day`: `camp, day, meals, previous_day, next_day,
    is_last_day, extra_open_count` (Task 5 fills it; pass 0 until then).

- [ ] **Step 1: Write the failing tests**

```python
def test_today_opens_the_running_day(freezer or monkeypatch timezone.localdate):
    # camp 1-5 Aug, today 3 Aug -> 302 to kitchen_day 2026-08-03; today in March -> first day
def test_day_shows_meals_lines_and_counts():
    # contains "Ui", "7,8 kg" (Dutch default), "Lunch", camp lunch_time
def test_day_outside_camp_is_404(): ...   # 2026-08-09 and "nonsense"
def test_empty_meal_shows_empty_state(): ...
@pytest.mark.parametrize("url_name", ["kitchen_today", "kitchen_day"])
def test_outsiders_get_404(url_name): ...
def test_camp_list_and_planner_link_to_kitchen(): ...
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the views and templates per the design's day-view
  sketch: day nav (previous / next as links, a `<input type="date">` form with
  GET), meals with recipes linking to `kitchen_cook` (Task 7; use `#` until it
  exists, Task 7 replaces it), meal header counts, "Extra shopping" and "Print day"
  buttons (wired in Tasks 5 and 11), evaluation section placeholder (Task 6).
  "Kitchen" link on the camp list and the planner header.
- [ ] **Step 4: Run** → PASS; full `pytest -q` green.
- [ ] **Step 5: Commit** (if asked).

### Task 4: The check and missing marks feeding the extra list

**Files:**
- Create: `kitchen/checks.py`
- Modify: `kitchen/urls.py`, `kitchen/views.py`, `templates/kitchen/_meal.html`
- Test: `tests/test_kitchen_checks.py`

**Interfaces:**
- Consumes: `meal_line` (Task 2), models (Task 1), `get_camp_day` (Task 3).
- Produces:
  - `set_check(camp, date, meal_type, line: IngredientLine, status: str, user) ->
    None` in `kitchen/checks.py`. `status` is `"there"`, `"missing"` or `""`
    (clear). Rules:
    - "missing": `update_or_create` the check; ensure an `ExtraShoppingItem` with
      `check=`, `ingredient=`, `quantity=line.quantity`, `meal_date`, `meal_type`,
      `added_by` (don't duplicate if one exists).
    - "there" or "": delete the linked item if not `bought`; "there" updates the
      check, "" deletes it. A bought linked item stays (its `check` goes to null
      when the check row is deleted).
    - Wrapped in `transaction.atomic()`.
  - URL `kitchen_check`: POST
    `camps/<int:camp_id>/kitchen/<str:day>/<str:meal_type>/check/<int:ingredient_id>/`
    with field `status`. Pressing the active state posts `""`. Invalid meal_type or
    ingredient not in the meal → 404. HTMX → re-rendered `_meal.html`; else 302 to
    `kitchen_day#meal-<meal_type>`.

- [ ] **Step 1: Write the failing tests**

```python
def test_tick_is_shared(): # post status=there as user A; GET as user B shows it ticked
def test_missing_adds_an_extra_line_with_the_meal_quantity():
    # ExtraShoppingItem quantity == Decimal("7.8"), meal_type "lunch", meal_date set
def test_missing_twice_adds_one_line(): ...   # Review Focus 1, no IntegrityError
def test_undo_missing_removes_unbought_line(): ...
def test_undo_missing_keeps_bought_line(): ...
def test_check_for_ingredient_not_in_meal_is_404(): ...   # Review Focus 2
def test_menu_change_keeps_extra_line():
    # mark missing, remove the recipe from the meal -> extra line still there
def test_htmx_gets_the_meal_partial(): # HTTP_HX_REQUEST="true" -> 200, id="meal-lunch"
def test_plain_post_redirects_to_the_meal(): ...
def test_example_camp_check_is_403(): ...
def test_recipe_unchanged_after_checks(): # RecipeIngredient quantities identical
```

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `set_check`, the view, and two buttons per line in
  `_meal.html` (each a small `<form method="post">` with `hx-post`,
  `hx-target="#meal-<type>"`, `hx-swap="outerHTML"`; active state shown with
  `btn-success` / `btn-danger` and `aria-pressed`). Labels "There" / "Missing".
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** (if asked).

### Task 5: Extra shopping list page

**Files:**
- Create: `templates/kitchen/extra_shopping.html`, `kitchen/forms.py` additions
- Modify: `kitchen/urls.py`, `kitchen/views.py`, shopping page template (link),
  `templates/kitchen/day.html` (button + count)
- Test: `tests/test_extra_shopping.py`

**Interfaces:**
- Consumes: `ExtraShoppingItem` (Task 1).
- Produces:
  - URLs: `extra_shopping` (`camps/<int:camp_id>/extra-shopping/`, GET + POST add),
    `extra_item` (`.../extra-shopping/<int:item_id>/`, POST with `action` in
    `bought`, `unbought`, `delete`, `amount`), `extra_clear`
    (`.../extra-shopping/clear/`, POST: delete all bought).
  - `ExtraItemForm` (add): `ingredient` (optional, Chiro-agnostic `Ingredient`
    choice) + `quantity`, or `text` + `amount_text`; error if neither.
  - Day view `extra_open_count` = unbought items of the camp.

- [ ] **Step 1: Write the failing tests**

```python
def test_add_free_text_line(): # text="Vuilniszakken" -> listed, open count 1
def test_add_needs_ingredient_or_text(): # form error, no row
def test_change_amount_does_not_touch_recipe(): ...
def test_bought_lines_sink_and_clear_removes_them(): ...
def test_item_of_another_camp_is_404(): ...
def test_extra_list_query_count(django_assert_max_num_queries): ...  # 20 items, fixed
```
  Add the three URLs to the Task 3 outsider/example parametrised test.

- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** per the design sketch: open lines first (ingredient,
  formatted quantity + unit or amount text, "lunch ma 14 jul" or "added by hand"),
  bought lines greyed below with "Clear bought" (`btn-outline-danger`, set apart).
  HTMX swaps one row; plain posts redirect to the list. Link from the shopping page.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** (if asked).

### Task 6: Evaluation notes on the day

**Files:**
- Create: `kitchen/evaluation.py`, `templates/kitchen/_evaluation.html`
- Modify: `kitchen/urls.py`, `kitchen/views.py`, `kitchen/forms.py`,
  `templates/kitchen/day.html`
- Test: `tests/test_kitchen_evaluation.py`

**Interfaces:**
- Produces:
  - `save_day_evaluation(camp, date, text: str, recipe_notes: dict[int, tuple[str,
    str]], user) -> None` in `kitchen/evaluation.py`; `recipe_notes` maps recipe id
    → `(tag, text)`. Empty day text deletes the `DayEvaluation`; empty tag and text
    deletes that `RecipeEvaluation`. Recipe ids not planned that day are ignored.
  - URL `kitchen_evaluation`: POST `camps/<int:camp_id>/kitchen/<str:day>/evaluation/`
    → 302 to `kitchen_day#evaluation` (HTMX: the partial).
  - One form: day note textarea, then per distinct recipe planned that day a tag
    radio group (with "none") and a text input. Folded (`<details>`) when empty.

- [ ] **Step 1: Write the failing tests**

```python
def test_day_and_recipe_notes_saved(): ...
def test_past_day_can_be_evaluated(): # post for the camp's first day after it ended
def test_same_recipe_twice_in_a_day_has_one_note(): ...
def test_clearing_removes_the_rows(): ...
def test_recipe_not_planned_that_day_is_ignored(): ...
```
  Add the URL to the outsider/example test.

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** (if asked).

### Task 7: Cooking view (server side)

**Files:**
- Create: `templates/kitchen/cook.html`
- Modify: `kitchen/urls.py`, `kitchen/views.py`, `templates/kitchen/_meal.html`
  (recipe links)
- Test: `tests/test_kitchen_cook.py`

**Interfaces:**
- Produces: URL `kitchen_cook`
  `camps/<int:camp_id>/kitchen/<str:day>/<str:meal_type>/<int:recipe_id>/?step=<n>`
  (1-based, default 1, out of range → 404; recipe not planned in that meal → 404).
  Context: `camp, day, meal_type, recipe, step, step_number, step_count,
  previous_url, next_url, ingredients` (this recipe's lines scaled for the camp,
  rounded per line). The step element carries `data-timer-key="<camp>-<day>-
  <recipe>-<step order>"`, `data-duration-minutes` and `data-label="<recipe> ·
  step n"` for Task 8.

- [ ] **Step 1: Write the failing tests**

```python
def test_cook_shows_one_step_with_navigation(): # step 2 of 3, prev/next hrefs
def test_step_out_of_range_is_404(): ...
def test_recipe_not_in_meal_is_404(): ...
def test_duration_shown_as_text_without_js(): # "20 min" in the HTML
def test_step_without_duration_has_no_timer(): # no data-duration-minutes
def test_recipe_without_steps_shows_ingredients_and_empty_state(): ...
```
  Add the URL to the outsider test (GET only).

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (ingredients in a `<details>`
  "Ingredients (scaled for N)", where N = `format_quantity(camp.demand_portions)`).
  **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** (if asked).

### Task 8: Timers, wake lock and alert (`static/js/kitchen_timers.js`)

**Files:**
- Create: `static/js/kitchen_timers.js`, `static/audio/timer.mp3` (short, small,
  license-free; generate it, e.g. a sine beep, rather than downloading)
- Modify: `templates/kitchen/cook.html`, `templates/kitchen/day.html` (timer bar on
  both), `static/css/app.css`
- Test: browser check (no JS test runner in this project); one Django test that the
  script is included on the cooking and day pages.

**Behaviour (the decisions the implementer needs):**
- Storage key per timer: `data-timer-key`; state in `localStorage` under
  `kitchenTimers:<camp>-<day>` as `{key: {label, lengthSeconds, startedAt | null,
  remainingSeconds}}`. All storage access in try/catch; without it, timers work in
  the page only.
- Remaining time is computed from `startedAt` (`Date.now()`), never by counting
  ticks, so a locked phone keeps correct time.
- Controls per step: −1 min, start/pause, +1 min, reset (back to the step's
  duration). Adjusted length is kept in that day's storage only.
- Bar at the bottom of day and cooking pages lists running and paused timers of the
  same camp day (label + mm:ss + pause/resume), linking back to the step.
- At zero: play the sound (loop until dismissed), add a flashing class to the bar
  and the step, `navigator.vibrate?.(…)`. Dismiss button stops it.
- Wake lock: `navigator.wakeLock.request("screen")` when the first timer starts,
  release when none run; re-request on `visibilitychange` if timers run. Feature-
  detect; do nothing if missing.
- Old days' storage keys (other dates) are removed on load.

- [ ] **Step 1: Write the Django test** that `kitchen_timers.js` is linked via
  `{% asset %}` on `kitchen_day` and `kitchen_cook` → FAIL.
- [ ] **Step 2: Implement** the JS, markup and CSS → test PASS.
- [ ] **Step 3: Browser check** in Edge (CLAUDE.md "Browser testing", throwaway
  server on 8123): start two timers on different recipes, move between steps, reload,
  adjust ±, let a 1-minute timer end (sound + flash + dismiss), check
  `navigator.wakeLock` is held while running (log in console via
  `javascript_tool`). Phone width (≈390px, window not maximised).
- [ ] **Step 4: Commit** (if asked).

### Task 9: Menu evaluation page and recipe history

**Files:**
- Modify: `kitchen/evaluation.py`, `kitchen/urls.py`, `kitchen/views.py`,
  `recipes/views.py` (`_render_detail`), `templates/recipes/recipe_detail.html`,
  camp page / report template (link)
- Create: `templates/kitchen/menu_evaluation.html`,
  `templates/recipes/_evaluation_history.html`
- Test: `tests/test_menu_evaluation.py`

**Interfaces:**
- Consumes: `Recipe.lineage()` (Task 1), evaluation models.
- Produces:
  - `menu_evaluation(camp) -> tuple[list[DayEvaluation], list[RecipeReview]]`;
    `@dataclass RecipeReview: recipe: Recipe; notes: list[RecipeEvaluation]` sorted
    with any `adjust`, `too_little` or `too_much` tag first, then by recipe name.
  - `recipe_history(recipe, user) -> list[RecipeEvaluation]`: notes for every recipe
    in `recipe.lineage()`, only from camps whose Chiro the user is a member of
    (`camp__chiro__in=user.chiros.all()`), newest first, `select_related("camp",
    "recipe")`.
  - URL `menu_evaluation` (`camps/<int:camp_id>/menu-evaluation/`, GET). Per recipe:
    edit link if `recipe.can_edit(user)`, else the existing copy form posting to the
    recipe copy view (flags computed in the view).

- [ ] **Step 1: Write the failing tests**

```python
def test_page_lists_day_notes_and_flagged_recipes_first(): ...
def test_history_follows_copies(): # note on original shows on copy's detail page
def test_history_hides_other_chiros_notes(): # Review Focus 4, also via copied_from
def test_cannot_edit_offers_copy(): # recipe without author -> copy form, no edit link
def test_menu_evaluation_query_count(django_assert_max_num_queries): ...
```
  Add the URL to the outsider test.

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** (if asked).

### Task 10: Pantry count at the end of the camp

**Files:**
- Create: `kitchen/pantry_count.py`, `templates/kitchen/pantry_count.html`
- Modify: `kitchen/forms.py`, `kitchen/urls.py`, `kitchen/views.py`,
  `templates/kitchen/day.html` (button on the last day), camp page (link)
- Test: `tests/test_pantry_count.py`

**Interfaces:**
- Produces:
  - `pantry_count_rows(camp) -> list[tuple[Ingredient, Decimal | None]]`: the
    Chiro's `PantryItem`s with their quantity, then the camp's planned ingredients
    with `category == IngredientCategory.DRY_GOODS` not in the pantry, with `None`;
    each block sorted by name.
  - `apply_pantry_count(chiro, counts: dict[int, Decimal | None], touched: set[int])
    -> list[tuple[Ingredient, Decimal | None, Decimal | None]]` (ingredient, old,
    new) for changed rows only. Only ingredient ids in `touched` change; 0 or `None`
    deletes the `PantryItem`; otherwise `update_or_create`. Atomic.
  - URL `pantry_count` (`camps/<int:camp_id>/pantry-count/`, GET + POST). Form: one
    `DecimalField(min_value=0, required=False)` per row, prefilled; plus a small
    formset to add ingredient + quantity. A row counts as touched when its value
    differs from the initial. Duplicate ingredient (added twice, or added when
    already listed) → form error. After saving: redirect with a message listing the
    changes ("Rijst: 4 → 2,5 kg").

- [ ] **Step 1: Write the failing tests**

```python
def test_rows_are_pantry_then_dry_goods_of_the_camp(): # produce ingredient not offered
def test_count_replaces_stored_quantity(): # 4 -> 2.5
def test_zero_removes_item(): ...
def test_untouched_rows_keep_their_value(): ...
def test_negative_is_an_error(): ...            # Review Focus 5
def test_duplicate_ingredient_is_an_error(): ... # Review Focus 5, no 500
def test_button_only_on_last_day(): ...
def test_new_stock_reaches_shopping_lists(): # build_shopping_plan of a later camp subtracts it
```
  Add the URL to the outsider/example test.

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** (if asked).

### Task 11: Printable day sheet

**Files:**
- Create: `templates/kitchen/day_print.html` (own print CSS, DESIGN.md §7, like
  `planning/runbook_print.html`)
- Modify: `kitchen/urls.py`, `kitchen/views.py`, `templates/kitchen/day.html`
- Test: `tests/test_kitchen_views.py` (fallback HTML), `tests/test_pdf.py` (real
  render, runs in Docker)

**Interfaces:**
- Produces: URL `kitchen_day_pdf` (`camps/<int:camp_id>/kitchen/<str:day>/print/`)
  → `render_pdf(request, "kitchen/day_print.html", {"camp", "day", "meals",
  "steps"}, filename=_("%(camp)s-%(day)s.pdf"))`. Per meal: time, recipes, lines with
  empty tick boxes, then each recipe's steps with durations. No check state, no notes.

- [ ] **Step 1: Write the failing tests**: fallback HTML (monkeypatch
  `core.pdf.weasyprint_available` → False, as in `tests/test_kitchen.py`) contains
  the meal, an ingredient, a step and "20 min", and no "Missing"; real PDF test added
  next to the existing ones in `tests/test_pdf.py`. Add the URL to the outsider test.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS; run
  the PDF test in the Docker image (CLAUDE.md).
- [ ] **Step 5: Commit** (if asked).

### Task 12: Docs, translations, final checks and browser review

**Files:**
- Modify: `docs/spec/kitchen.md` (fold the design in: Data, Behaviour, Acceptance;
  D16 rewritten, dated; remove the Planned link), `docs/spec/recipes.md`
  (`copied_from`, notes follow copies), `docs/spec/shopping.md` (pantry count),
  `docs/spec/planning.md` (the "no shopping list" sentence), the design ("Built;
  folded into …"), `docs/TODO.md` (step 5 marked done),
  `pages/content/` help page for kitchen mode (EN + `.nl.md`), `README.md` if it
  lists pages, `locale/nl/LC_MESSAGES/django.po` + `.mo`.

- [ ] **Step 1:** Docs updates (can go to opencode `docs` agent with the list above;
  review what it changed).
- [ ] **Step 2:** Translations: run the README's `makemessages`/`msgfmt` Docker
  command, fill the Dutch for every new string (kitchen words as the kookploeg says
  them: "Heb je alles?", "Er", "Ontbreekt", "Extra boodschappen", "Evaluatie",
  "Voorraad bijwerken"), recompile.
- [ ] **Step 3:** Run all checks from CLAUDE.md: ruff, black --check, pytest -q,
  `makemigrations --check --dry-run` with `DJANGO_DEBUG=1` → all clean.
- [ ] **Step 4:** UI loop from CLAUDE.md: opencode `reviewer` on the new templates,
  then `ui-reviewer` on `kitchen_day`, `kitchen_cook`, `extra_shopping`,
  `menu_evaluation`, `pantry_count` at phone and laptop width, as a plain member,
  and an outsider check. Fix FAIL items; up to three rounds.
- [ ] **Step 5:** Commit (if asked), staging files by name.
