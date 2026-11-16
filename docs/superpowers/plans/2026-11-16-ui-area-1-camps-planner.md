# UI move, area 1: camps and planner. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the camp and planner pages to Bootstrap, crispy forms and the shared
components, laid out for a PC and still usable at 375px.

**Architecture:** Templates only, plus four shared pieces later areas reuse
(components `back_link`, `form_errors` and `camp_nav`, the `pages/templatetags/ui.py`
filters) and one test file, `tests/test_ui_move.py`, that checks every converted
template has no old classes and every converted page has one `h1` and the red rule.
Views stay as they are, except one form label (Task 11) and one dev login (Task 3).

**Tech Stack:** Django 5.2 templates, Bootstrap 5.3, Bootstrap Icons, crispy-bootstrap5,
HTMX (django-htmx), pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-ui-move-design.md` (area 1). Area files:
`docs/spec/planning.md`, `docs/spec/accounts.md` (Task 3).

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
- Every visible text in `{% translate %}` / `{% blocktranslate %}`; new Dutch strings go
  in `locale/nl/LC_MESSAGES/django.po` and the `.mo` is recompiled (README).
- No inline `style=""`, no inline `<script>`. Colours only from Bootstrap classes and
  the `--chiro-*` tokens. Destructive buttons `btn-outline-danger` with `bi-trash`.
  Badges only for status (`text-bg-success|warning|danger|secondary`).
- Icons next to text get `aria-hidden="true"`; icon-only controls get `aria-label`.
- Dates on screen through the `short_date` filter (Task 4): `za 1 aug` in Dutch.
- Don't touch `*_print.html` or `templates/kitchen/`.
- Keep `static/js/headcount.js` working: it needs `[data-group-totals]`,
  `[data-total="children|teens|staff|portions"]`, `data-child-factor` and
  `input[data-group-count]`.

## Review Focus

1. **A camp form posted with errors** (end date before start date): the page shows a
   summary alert at the top, the field marked `is-invalid` with its message, and what
   was typed. Test in Task 8.
2. **An example camp opened by a plain member**: the planner, camp form and runbook
   render with the example alert and no crash. Test in Task 10.
3. **Dutch dates**: `za 1 aug` on the planner and camp list, not `01 Aug` or
   `1 augustus 2026`. Tests in Tasks 4, 7 and 10 (the existing `test_i18n.py`
   assertion changes from `"za 01 Aug"` to `"za 1 aug"`).
4. **A 375px phone on the planner and runbook**: no horizontal page scroll; the
   planner grid and camp menu scroll inside their box. Browser check in Task 14.
5. **A camp of 14 days with every slot filled**: the planner stays readable at 1366px
   (columns don't collapse, chips wrap). Browser check in Task 14 on a camp edited to
   14 days.

---

## Page layouts (Claude with frontend-design)

Within `DESIGN.md`: sand-soft table headers and card headers, navy actions, the red
rule only in the page header. The camp's pages share one navigation bar (`camp_nav`),
so moving between planner, shopping, runbook and bills is one click on a PC; later
areas add it to their pages.

**Camp nav** (under the page header on every camp page):

```
[▦ Menu plan] [🛒 Shopping] [📖 Runbook] [🧾 Bills] [📈 Report] [⚠ Diets] [🔧 Utilities] [✎ Edit]
```

`nav nav-pills`, active one filled navy, `flex-nowrap overflow-x-auto` so on a phone it
scrolls inside its own row.

**Camp list (1366px):**

```
Camps                                                   [+ New camp]
───
┌ Camp ─────────────── Dates ───────────── <12  12+  Staff  Portions  ──────────────────────────┐
│ Zomerkamp 2026       za 1 aug – zo 10 aug 2026   45   38    20    79,5   [Shopping][Runbook][Bills][Edit] │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
Example camp   (list group: name · year · Chiro)
Archive        (list group: name · year)
```

The camp name links to the planner. Numbers right-aligned. No camps: empty state
`calendar-event`, "No camps for your Chiro yet.", button "New camp". No Chiro: empty
state `people`, the existing sentence, no button.

**Camp form (1366px):** cards with a sand header, fields in two columns.

```
← Back to the menu plan
Edit Zomerkamp 2026
───
[camp nav]                                   (edit only)
[! Some fields need your attention.]         (only with errors)
┌ Camp ───────────────────────────────────────┐
│ Name [.................]  Chiro [......]     │
│ Start [date]              End [date]         │
└──────────────────────────────────────────────┘
┌ Headcount per group ─────────────────────────┐
│ table of rows · [+ Add group] · Total: …     │
└──────────────────────────────────────────────┘
┌ Meal times ───────────────────────────────────┐
│ Breakfast [..] Lunch [..] Tea [..] Dinner [..] │
└──────────────────────────────────────────────┘
┌ Runbook info ─────────────────────────────────┐
│ Cook team [...]     Location [...]            │
│ Contact leaders [.] Contact rental [.]        │
│ Bakery [...]                                  │
│ General info [.............................]  │
└──────────────────────────────────────────────┘
[🗑 Delete camp]                       [✓ Save camp]
┌ Kitchen utilities ┐  ┌ Archive ─────────────┐
│ text · [link]     │  │ text · [Archive camp]│
└───────────────────┘  └──────────────────────┘
```

**Planner (1366px):** the grid is the page.

```
Zomerkamp 2026                                        [⇩ Overview PDF]
za 1 aug – zo 10 aug 2026 · 45 children + 38 teens + 20 staff = 79,5 portions
───
[camp nav]
[archived alert] [outside-dates alert] [diet conflicts alert]    (only when present)
┌ Day ──── Breakfast 08:00 ── Lunch 12:30 ──── Tea 16:00 ──── Dinner 18:30 ─┐
│ za 1 aug  (Bread breakfast)  SOUP (Tomato…)   (pick…)        MAIN (Stew)   │
│                              MAIN (Pasta)                    DESSERT ⓘpick │
└────────────────────────────────────────────────────────────────────────────┘
Balance (card, list per day)          · unchecked-ingredients line
```

Diet conflicts move above the grid: on a long camp they were out of sight below it.

**Edit slot (1366px):** two columns from `lg`: the recipe picker on the left
(`col-lg-5`), the scaled ingredients and steps on the right (`col-lg-7`).

**Runbook (1366px):** header with "Runbook PDF"; camp nav; a sticky row of day pills;
an "Info" `h2` with the info cards in a grid (1 / 2 / 3 per row at sm / md / xl); one
section per day: menu table, steps, notes form.

---

### Task 1: Record D19 and update the roadmap (Claude)

**Files:**
- Modify: `docs/SPEC.md` (UI section and "Decisions for every area")
- Modify: `docs/ui-guidelines.md` ("Layout and breakpoints", first bullet)
- Modify: `docs/TODO.md` (steps 3 and 5)

- [ ] **Step 1:** In `docs/SPEC.md` UI, replace "Mobile first: kitchen screens…" with
  "Planning screens are designed for a PC and checked on a phone; kitchen screens for a
  phone or tablet (D19)." Change "New ones continue from D19." to "from D20." Add:
  `- **D19** (2026-11-16): **Planning on a PC, the kitchen on a phone or tablet.**
  Planning views (stages 1 and 3) are designed at 1366px and checked at 375px; kitchen
  views (stage 2) at 375px and 768px; public pages work at both.`
- [ ] **Step 2:** In `docs/ui-guidelines.md`, replace "Mobile first. Design at
  **375px** wide, then enhance for **≥992px (lg)**." with the three D19 lines from the
  design ("Layout rule change (D19)").
- [ ] **Step 3:** In `docs/TODO.md`, step 3 becomes "### 3. UI move: in progress" with a
  link to the design, the six areas as a checklist, and the known items under their
  area (design "Known items from the old roadmap"). Step 5 gets: "Starts once the user
  is satisfied with stages 1 and 3. Needs to work; polish comes later."
- [ ] **Step 4:** `grep -n "Mobile first" docs/` shows nothing outside
  `docs/superpowers/`.

### Task 2: The UI move test file (Claude)

**Files:**
- Create: `tests/test_ui_move.py`

**Interfaces:**
- Produces: `CONVERTED_TEMPLATES: list[str]` (paths under `templates/`),
  `CONVERTED_PAGES: list[tuple[str, Callable[[Camp], list]]]` (URL name, args from a
  camp), `old_classes(template_text: str) -> set[str]`. Later tasks append to the two
  lists.

- [ ] **Step 1:** Write `old_classes()` and its tests. It finds every `class="…"`
  attribute, splits it on whitespace, ignores tokens containing `{` or `%`, and returns:
  - tokens in `OLD = {"back-link", "stacked-form", "form-row", "actions", "warning",
    "page-meta", "muted", "table-scroll", "compact", "btn-outline", "btn-small",
    "btn-danger-outline", "empty-slot", "missing", "toc", "outside-list", "note-form",
    "runbook-info-grid", "runbook-menu", "planner-table", "slot", "slot-course",
    "step-block", "qty"}`;
  - `"btn"` when an attribute has `btn` but no token starting with `btn-`;
  - `"badge"` when an attribute has `badge` but no token starting with `text-bg-` or
    `bg-`.

```python
def test_old_classes_finds_the_old_ones():
    assert old_classes('<a class="btn">x</a>') == {"btn"}
    assert old_classes('<a class="btn btn-outline-primary">') == set()
    assert old_classes('<p class="muted page-meta">') == {"muted", "page-meta"}
    assert old_classes('<span class="badge">') == {"badge"}
    assert old_classes('<span class="badge text-bg-warning">') == set()
    assert old_classes('<a class="slot-chip{% if x %} slot-chip-empty{% endif %}">') == set()
```

- [ ] **Step 2:** `test_converted_template_has_no_old_classes(path)` parametrized over
  `CONVERTED_TEMPLATES`, asserting `old_classes(text) == set()`, and
  `test_converted_page_has_one_h1_and_the_red_rule(url_name, args)` parametrized over
  `CONVERTED_PAGES`: GET as `member_client(make_camp())`, status 200,
  `html.count("<h1") == 1`, `"page-rule" in html`. Both lists start empty.
- [ ] **Step 3:** `.venv/Scripts/python.exe -m pytest tests/test_ui_move.py -q`: the
  `old_classes` test passes, the two parametrized tests are skipped (empty lists).

### Task 3: A plain member login in seed_demo (builder)

**Files:**
- Modify: `camps/management/commands/seed_demo.py:207-215`
- Test: `tests/test_review_fixes.py`

- [ ] **Step 1: Failing test** `test_seed_demo_creates_a_plain_member(settings)`: with
  `settings.DEBUG = True`, `call_command("seed_demo")` twice; `User.objects.get(
  username="member")` is not staff and not superuser, `check_password("member")`, and
  has exactly one `Membership` in "Demo Chiro" with `role == Role.MEMBER`.
- [ ] **Step 2:** Run it: FAIL (`User.DoesNotExist`).
- [ ] **Step 3:** After the admin block, create `member` / `member` with
  `User.objects.create_user` when missing and `Membership.objects.get_or_create(user=…,
  chiro=chiro, defaults={"role": Role.MEMBER})`; print "Created dev login
  member/member". Update the module docstring and `help` to mention both logins, and
  the CommandError text to "admin/admin and member/member" (the existing test matches
  on "admin/admin", which still holds).
- [ ] **Step 4:** Run `tests/test_review_fixes.py`: PASS. Add one line to
  `.claude/CLAUDE.md` "Browser testing" step 2: "…`admin` / `admin` (superuser and
  Chiro admin) and `member` / `member` (plain member)." (Claude does this line.)

### Task 4: Shared components and filters (builder)

**Files:**
- Modify: `templates/components/page_header.html`, `templates/components/empty_state.html`
- Create: `templates/components/back_link.html`, `templates/components/form_errors.html`,
  `pages/templatetags/ui.py`
- Test: `tests/test_ui_components.py`

**Interfaces:**
- Produces:
  - `page_header.html` with optional `action_url`, `action_label`, `action_icon`: a
    `btn btn-primary` (`action_style="outline"` makes it `btn-outline-primary`) next to
    the `h1` from `lg` (`d-lg-flex justify-content-between align-items-center`), under
    it on a phone. Without `action_url` the output is unchanged.
  - `back_link.html` with `url`, `label`: `<a class="icon-link link-secondary mb-2"
    href="{{ url }}"><i class="bi bi-arrow-left" aria-hidden="true"></i> {{ label }}</a>`
    in a `<p class="mb-1">`.
  - `form_errors.html` with `form` and optional `formset`: when `form.errors` or
    `formset.total_error_count`, a `div.alert.alert-danger` with `role="alert"`,
    `bi-exclamation-triangle`, the text "Some fields need your attention; see below."
    and `form.non_field_errors` as a list. Nothing otherwise.
  - `empty_state.html`: icon `text-primary` (navy, DESIGN §6) with `aria-hidden`.
  - `{% load ui %}`: filter `short_date(value: date, arg: str = "") -> str`: Dutch
    `D j b` ("za 1 aug"), other languages `D j M` ("Sat 1 Aug"); with `arg == "year"`
    a space and the year are added. Filter `table_input(field: BoundField) -> str`: the
    widget rendered with `form-select form-select-sm` (select), `form-check-input`
    (checkbox) or `form-control form-control-sm` (anything else), plus `is-invalid` when
    the field has errors and `aria-label` set to the field's label. Use
    `field.as_widget(attrs=…)`, merging any existing `class`.

- [ ] **Step 1: Failing tests** in `tests/test_ui_components.py`:
  - `test_short_date_in_dutch`: under `translation.override("nl")`,
    `short_date(date(2026, 8, 1)) == "za 1 aug"` and `short_date(…, "year") ==
    "za 1 aug 2026"`.
  - `test_short_date_in_english`: `"Sat 1 Aug"`.
  - `test_table_input_classes`: on a form with a `CharField`, a `ChoiceField` and a
    `BooleanField` labelled "Name", "Kind", "Delete": the output contains
    `class="form-control form-control-sm"` / `form-select form-select-sm` /
    `form-check-input`, and `aria-label="Name"`; a bound invalid form adds `is-invalid`.
  - `test_page_header_action`: `render_to_string` with `title`, `action_url="/x/"`,
    `action_label="New"` contains `href="/x/"` and `btn btn-primary`; without them it has
    no `<a`.
  - `test_form_errors_only_with_errors`: an invalid form renders `alert-danger`, a valid
    one renders an empty string (after `strip()`).
- [ ] **Step 2:** Run: FAIL (no `ui` library, no templates).
- [ ] **Step 3:** Write the files above. Add the Dutch for "Some fields need your
  attention; see below." ("Enkele velden moeten nog aangepast worden; zie hieronder.")
  and recompile the `.mo`.
- [ ] **Step 4:** Run `tests/test_ui_components.py` and `tests/test_base_layout.py`:
  PASS. Add the five component paths to `CONVERTED_TEMPLATES`.

### Task 5: The camp nav (builder)

**Files:**
- Create: `templates/components/camp_nav.html`
- Test: `tests/test_ui_components.py`

**Interfaces:**
- Produces: `{% include "components/camp_nav.html" with camp=camp active="plan" %}`.
  `active` is one of `plan`, `shopping`, `runbook`, `bills`, `report`, `diets`,
  `utilities`, `edit`.

- [ ] **Step 1: Failing test** `test_camp_nav_marks_the_active_page`: rendered for a
  camp with `active="runbook"`, it has eight links to `planner`, `shopping`, `runbook`,
  `bill_list`, `financial_report`, `camp_diets`, `camp_utensils`, `camp_edit` (in that
  order), and only the runbook link has `aria-current="page"` and `active`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** `<nav aria-label="{% translate 'Camp' %}" class="mb-4">` around
  `ul.nav.nav-pills.flex-nowrap.overflow-x-auto.text-nowrap.gap-1`. Labels and icons:
  Menu plan `bi-calendar3`, Shopping `bi-cart`, Runbook `bi-journal-text`, Bills
  `bi-receipt`, Financial report `bi-graph-up`, Diets and allergies
  `bi-exclamation-diamond`, Kitchen utilities `bi-tools`, Edit camp `bi-pencil`. Reuse
  the existing translated strings (they're already in the `.po`).
- [ ] **Step 4:** Run: PASS. Add the path to `CONVERTED_TEMPLATES`.

### Task 6: Bootstrap inputs in the row tables (builder)

**Files:**
- Modify: `templates/partials/_formset_row.html`, `templates/recipes/_formset.html`

**Interfaces:**
- Consumes: `table_input` (Task 4).

This also changes the recipe form's ingredient and step rows (area 2): a gain there too.

- [ ] **Step 1: Failing test** in `tests/test_camp_groups.py`:
  `test_group_rows_use_bootstrap_inputs`: the camp create page (`_client_in(chiro)`)
  contains `form-control form-control-sm`, `form-select form-select-sm` and
  `aria-label="` on the group inputs, and the table has class `table`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** In `_formset_row.html`, render each field with `{{ field|table_input }}`
  and its errors as `<div class="invalid-feedback d-block">`. In `_formset.html`:
  `div.table-responsive` around `table.table.table-sm.align-middle.mb-0`, header cells
  `scope="col"`, `non_form_errors` in an `alert alert-danger`. Keep the add-row
  button's attributes exactly; keep the ids `{prefix}-rows` and the OOB `TOTAL_FORMS`
  input.
- [ ] **Step 4:** Run `tests/test_camp_groups.py tests/test_recipe_form_rows.py
  tests/test_recipe_views.py`: PASS. Add both paths to `CONVERTED_TEMPLATES`.

### Task 7: Camp list (builder)

**Files:**
- Modify: `templates/camps/camp_list.html`
- Test: `tests/test_ui_move.py`, `tests/test_camp_ingredient_screens.py`

- [ ] **Step 1: Failing tests:** add `"camps/camp_list.html"` to `CONVERTED_TEMPLATES`
  and `("camp_list", lambda camp: [])` to `CONVERTED_PAGES`. In
  `tests/test_ui_move.py`, `test_camp_list_dates_are_short`: a Dutch member client sees
  `za 1 aug – wo 5 aug 2026` for `make_camp()`; and `test_camp_list_empty_states`: a
  member of a Chiro with no camps sees `bi-calendar-event` and a link to `camp_create`;
  `account_client()` sees `bi-people` and "isn't linked to a Chiro".
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Layout per "Camp list" above. Page header with
  `action_url` = `camp_create`, label "New camp", icon `plus-lg`, only when
  `has_chiro`. Table in `div.card.shadow-sm > div.table-responsive >
  table.table.table-hover.align-middle.mb-0`; number columns `text-end`; portions bold,
  not a badge; dates `{{ camp.start_date|short_date }} – {{ camp.end_date|short_date:"year" }}`;
  actions in `div.btn-group.btn-group-sm` of `btn-outline-primary` links with icon and
  text (Shopping `bi-cart`, Runbook `bi-journal-text`, Bills `bi-receipt`, Edit
  `bi-pencil`). Example and archive lists as `ul.list-group` with
  `small.text-body-secondary` for year and Chiro. Empty states via
  `components/empty_state.html`.
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_camp_ingredient_screens.py
  tests/test_auth.py tests/test_base_layout.py tests/test_report.py`: PASS.

### Task 8: Camp form (ui-builder)

**Files:**
- Modify: `templates/camps/camp_form.html`, `templates/camps/_groups.html`,
  `templates/camps/_example_note.html`
- Test: `tests/test_ui_move.py`

- [ ] **Step 1: Failing tests:** add the three templates to `CONVERTED_TEMPLATES` and
  `("camp_create", lambda camp: [])`, `("camp_edit", lambda camp: [camp.pk])` to
  `CONVERTED_PAGES`. Add `test_camp_form_errors_show_a_summary_and_keep_input`: posting
  the edit form with `end_date` before `start_date` (use `_camp_data` from
  `tests/test_camp_groups.py`, or build the same dict) returns 200 with `alert-danger`,
  `is-invalid` and the typed name in the HTML.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Layout per "Camp form" above, with `{% load crispy_forms_tags %}`:
  - back link: edit → planner "Back to the menu plan"; new → camp list "All camps".
  - `page_header` (title as today); camp nav `active="edit"` on edit only;
    `_example_note.html` becomes `div.alert.alert-info` with `bi-eye`; `form_errors`
    with `form` and `formset=groups`.
  - each section a `div.card.shadow-sm.mb-4` with `div.card-header` holding
    `h2.h5.mb-0`, body `div.row.g-3`; each visible field `{{ field|as_crispy_field }}`
    in a column: `col-6 col-lg-3` when `field.widget_type == "time"`, `col-12` for
    `general_notes`, else `col-lg-6`. Hidden fields render bare.
  - `_groups.html` becomes the same card (header "Headcount per group"), the intro as
    `p.text-body-secondary`, the totals line keeps every `data-*` attribute.
  - actions row `d-flex flex-wrap gap-2 mt-4`: delete (`btn-outline-danger`,
    `bi-trash`, only with `can_delete`) first, then save (`btn-primary`,
    `bi-check-lg`, `ms-auto`).
  - edit only, below: `div.row.g-3.mt-4` with two `col-lg-6` cards, "Kitchen
    utilities" (text + `btn-outline-primary` link) and "Archive" (text + the archive
    form with a `btn-outline-primary` and `bi-archive`/`bi-box-arrow-up`).
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_camp_groups.py
  tests/test_camp_ingredient_screens.py tests/test_spec_features.py
  tests/test_delete_and_remove.py`: PASS.

### Task 9: Diets page (builder)

**Files:**
- Modify: `templates/camps/rows_page.html`

- [ ] **Step 1: Failing test:** add the template to `CONVERTED_TEMPLATES` and
  `("camp_diets", lambda camp: [camp.pk])` to `CONVERTED_PAGES`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Back link to the planner; `page_header` with `title=title`,
  `meta=camp.name`; camp nav `active="diets"`; example note. No `form_errors` include:
  the page has only a formset, and `_formset.html` already shows its
  `non_form_errors` (Task 6). `p` with `intro`; the formset in a `div.card.shadow-sm >
  div.card-body`; save button `btn-primary` with `bi-check-lg`, right-aligned
  (`d-flex justify-content-end mt-3`). No add-row button (design: no new inputs).
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_spec_features.py`: PASS.

### Task 10: Planner (ui-builder)

**Files:**
- Modify: `templates/planning/planner.html`, `templates/planning/_outside_entries.html`,
  `templates/planning/_headcount.html`, `static/css/app.css` (slot chip only)
- Modify test: `tests/test_i18n.py:72`
- Test: `tests/test_ui_move.py`

- [ ] **Step 1: Failing tests:** add the three templates to `CONVERTED_TEMPLATES` and
  `("planner", lambda camp: [camp.pk])` to `CONVERTED_PAGES`. Change
  `tests/test_i18n.py` `"za 01 Aug"` to `"za 1 aug"`. Add
  `test_example_camp_pages_render_for_a_member`: a camp in a Chiro with
  `is_example=True`, viewed by `account_client()` (plain user, not staff): `planner`,
  `camp_edit` and `runbook` return 200 and contain `alert-info`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Layout per "Planner" above:
  - `page_header` with title `camp.name`, meta = dates (`short_date`, end with year)
    and `_headcount.html`; action "Overview PDF", `bi-file-earmark-pdf`,
    `action_style="outline"`. Camp nav `active="plan"`.
  - Alerts in this order, each with an icon: archived (`alert-secondary`,
    `bi-archive`), outside entries (`alert-warning`, `bi-exclamation-triangle`; remove
    buttons `btn btn-sm btn-outline-danger` with `bi-trash`, list as
    `ul.list-unstyled`), diet conflicts (`alert-warning`, heading
    `h2.h6` "Diets and allergies", same text and list as today).
  - Grid in `div.card.shadow-sm > div.table-responsive > table.table.table-bordered.
    align-top.mb-0`; header cells `scope="col"` with the meal time in
    `span.fw-normal.text-body-secondary.small`; day cells `th scope="row"
    class="text-nowrap"` with `short_date`. Each slot: `div.mb-1`, course label in
    `div.small.text-uppercase.text-body-secondary`, then the chip link.
  - Chip classes: `slot-chip`, plus `slot-chip-empty` when no entry, plus
    `slot-chip-missing` when the slot is required. A missing chip shows
    `bi-exclamation-circle` (`aria-hidden`) before "pick…" so it isn't colour alone.
  - Below the grid: Balance card (`h2.h5` in the card header) and the unchecked line in
    `p.small.text-body-secondary.mt-3`.
  - `app.css`: replace the `.slot-chip*` rules with DESIGN §6 "Planner chip":
    `--chiro-sand-soft` background and navy text, `.slot-chip-empty` dashed
    `var(--bs-border-color)` and muted italic, `.slot-chip-missing` in
    `var(--bs-danger)` text and border on `var(--bs-danger-bg-subtle)`, hover per
    DESIGN, a visible navy focus ring. Delete `.slot`, `.slot-course`,
    `.planner-table*`.
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_i18n.py
  tests/test_spec_features.py tests/test_delete_and_remove.py tests/test_auth.py`: PASS.

### Task 11: Edit slot (builder)

**Files:**
- Modify: `templates/planning/edit_slot.html`, `planning/forms.py:13`
- Test: `tests/test_ui_move.py`

- [ ] **Step 1: Failing tests:** add the template to `CONVERTED_TEMPLATES` and
  `("edit_slot", lambda camp: [camp.pk, camp.start_date.isoformat(), "dinner"])` to
  `CONVERTED_PAGES`; `test_edit_slot_select_has_a_label`: the page has
  `<label for="id_recipe"`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** `SlotForm.recipe` gets `label=_("Recipe")`. Template: back link to
  the planner; `page_header` with title `{{ day|short_date }} — {{ meal_label }}`
  (plus course as today), meta camp name and portions; example note. `div.row.g-4`:
  `col-lg-5` card with the form (`{{ form.recipe|as_crispy_field }}`, save
  `btn-primary` right-aligned); `col-lg-7` with the scaled table (`table.table.table-sm`,
  quantity `text-end`), heading `h2.h5` "Scaled for N portions" followed by
  `span.text-body-secondary` "× 2,60" (not a badge), the recipe-page `icon-link`, and
  the steps card with the total minutes as `span.text-body-secondary`.
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_runbook.py tests/test_scaling.py`:
  PASS.

### Task 12: Runbook (ui-builder)

**Files:**
- Modify: `templates/planning/runbook.html`, `static/css/app.css`
- Test: `tests/test_ui_move.py`

- [ ] **Step 1: Failing tests:** add the template to `CONVERTED_TEMPLATES` and
  `("runbook", lambda camp: [camp.pk])` to `CONVERTED_PAGES`;
  `test_runbook_note_has_a_label`: the page has a `<label` whose `for` matches the
  first note textarea's `id`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Layout per "Runbook" above:
  - `page_header` title "Cook team runbook — {camp}", meta dates and headcount,
    action "Runbook PDF" (`bi-file-earmark-pdf`). Camp nav `active="runbook"`.
  - Day pills: `nav.nav.nav-pills.flex-nowrap.overflow-x-auto.sticky-top.bg-body.py-2
    .mb-3.d-print-none` with `aria-label` "Days", links to `#info` and each
    `#day-YYYY-MM-DD`.
  - `section#info` with `h2` "Info" and `div.row.row-cols-1.row-cols-md-2.
    row-cols-xl-3.g-3` of `div.card.h-100.shadow-sm > div.card-body`, card titles
    `h3.h6`, empty values `span.text-body-secondary` "—" (the cook-team hint keeps its
    link). Text fields keep `class="prewrap"`.
  - Each day: `section.runbook-day.border-top.border-3.border-primary.pt-3.mt-5` with
    the id, `h2`; the menu in `div.table-responsive > table.table.table-sm`; column
    widths with `w-25` on the menu header, no inline `style`; ingredient items as
    `span.text-nowrap`.
  - Steps: `h3.h5` "Step by step", each block `div.mb-3` with `h4.h6`.
  - Notes form `d-print-none`: a `label.form-label` ("Notes for day N", Dutch
    "Notities voor dag N") tied to a `textarea.form-control` with an id per day, save
    `btn btn-primary btn-sm` right-aligned.
  - `app.css`: delete `.runbook-info-grid*`, `.runbook-menu .qty`, `.step-block*`,
    `.note-form*` and the `.runbook-day` border and margins; keep `.prewrap` and
    `.runbook-day { scroll-margin-top: 4rem; }` (the sticky pills would cover the day
    title).
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_runbook.py
  tests/test_camp_groups.py tests/test_review_fixes.py`: PASS.

### Task 13: Static review and app.css check (opencode reviewer, Claude)

- [ ] **Step 1:** opencode `reviewer` on each task's templates in groups of up to three
  files, with the ui-guidelines template checks (its step 5 and 6).
- [ ] **Step 2:** Claude: `grep -n "slot-course\|planner-table\|runbook-info-grid\|
  step-block\|note-form\|empty-slot" static/css/app.css templates/` shows only what
  other areas still use (`empty-slot` stays while other areas use it).
- [ ] **Step 3:** `.venv/Scripts/python.exe -m pytest tests/test_ui_move.py -q`: every
  parametrized case passes.

### Task 14: Browser review (ui-reviewer)

- [ ] **Step 1:** Throwaway server (CLAUDE.md "Browser testing") with `seed_demo`.
  Edit the demo camp to 14 days and fill most slots for Review Focus 5.
- [ ] **Step 2:** `ui-reviewer` at 1366px and 375px, as `member` and as `admin`, on:
  camp list, new camp, camp edit (with a validation error), diets, planner, edit slot,
  runbook; also the example camp's planner as `member` if the demo has one. Include
  the DESIGN §9 checklist and the theme check at phone width (old roadmap item).
- [ ] **Step 3:** Fix FAIL items (`builder` for one file, `ui-builder` otherwise), re-run
  the reviewer with its previous report; at most three rounds (CLAUDE.md "The UI loop").

### Task 15: Finish area 1 (Claude)

- [ ] **Step 1:** Help pages: if `pages/content/planning*.md` or
  `getting-started*.md` describe the old buttons above the planner, describe the camp
  nav instead (EN and NL).
- [ ] **Step 2:** All checks: ruff, black, pytest, `makemigrations --check --dry-run`
  (CLAUDE.md "Checks"). Build the Docker image and run `tests/test_pdf.py` in it: the
  runbook and overview PDFs still render.
- [ ] **Step 3:** Claude reviews the whole area diff (more than three files);
  opencode `secret_reviewer` on the staged files.
- [ ] **Step 4:** In `docs/TODO.md`, tick area 1. Commit on `dev`, files staged by name:

```bash
git commit -m "Move the camp and planner pages to Bootstrap (UI move, area 1)"
```
