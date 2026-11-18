# UI move, area 4: bills and the financial report. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the bills list, the bill review and the financial report (page and the
body it shares with the PDF) to Bootstrap and the shared components, with "Add a line"
on the review table.

**Architecture:** Templates first. The review table's row moves into its own partial
(`bills/_bill_line_row.html`) so the page and an HTMX row view render the same markup;
`bill_detail` learns the no-JS `add_row` post. The report body switches to Bootstrap
classes and the PDF's inline CSS learns those few classes. `ingredient_dialog.js`
listens for clicks at the document level so "+" works on added rows.

**Tech Stack:** Django 5.2 templates, Bootstrap 5.3, Bootstrap Icons, crispy-bootstrap5,
HTMX 2 with django-htmx, WeasyPrint (Docker), pytest.

**Spec:** `docs/superpowers/specs/2026-11-18-ui-area-4-bills-design.md` on top of
`docs/superpowers/specs/2026-11-16-ui-move-design.md`. Area file:
`docs/spec/finance.md`. Branch `ui/area-4-bills` from `origin/dev` once
`feature/bills-pdf-only` is merged; if it isn't yet, from `feature/bills-pdf-only`,
said in the PR.

## Global Constraints

- Follow `docs/ui-guidelines.md` and `docs/DESIGN.md`; paste the lines a task names.
- D19: these pages are designed for a **PC at 1366px**, checked at **375px**: no
  horizontal page scroll; the review table scrolls inside its box on a phone.
- At 1366px the review table shows all nine columns without sideways scrolling and its
  header stays in view while scrolling down.
- The report page and the report PDF stay **one** body template
  (`bills/_report_body.html`); the PDF must look as before (checked in Docker).
- No behaviour, model or permission changes beyond "Add a line". Every link, form and
  no-JavaScript path keeps working; existing tests keep passing (a test may change only
  where this plan says).
- HTMX only on "Add a line"; it also works as a plain post.
- Every visible text translated; Dutch in `django.po` (Docker; no fuzzy).
- No inline `style=""` on the page templates (the PDF's `<style>` block is its own),
  no inline `<script>`, no `onclick`. Destructive buttons `btn-outline-danger` with
  `bi-trash`. Badges only for status, plus the day total in the report (the design
  asks for it). Status badges: To review `text-bg-warning`, Reviewed
  `text-bg-success`, Couldn't be read `text-bg-danger`.
- Icons next to text `aria-hidden="true"`; icon-only buttons `aria-label`.
- Dates through `short_date` (`{% load ui %}`).
- The new-ingredient dialog keeps every hook `ingredient_dialog.js` needs
  (`#new-ingredient-dialog`, `data-selects`, `data-save-error`, the form, 
  `#new-ingredient-errors`, `#new-ingredient-cancel`, openers `data-new-ingredient` with
  `data-select` and `data-name-from`).
- `confirm_delete.html` is area 5. Don't touch `shopping_print.html`, `recipe_print.html`.

## Review Focus

1. **"+" (new ingredient) on a line added through HTMX** opens the dialog and fills
   that line's select. Browser check in Task 5 (the JS change in Task 1).
2. **"Add a line" without JavaScript with lines already edited**: the page comes back
   with one more empty line, edits kept, nothing saved, no price set. Test in Task 1.
3. **The report PDF after the body change**: same sections, warnings boxed, amounts
   right-aligned. Docker render in Task 4 (test_pdf plus a look at the PDF).
4. **A bill without a file and with status "Couldn't be read"**: the review page shows
   the error, "The file was removed.", and lines can be typed. Test in Task 2.
5. **A long bill (40 lines) at 1366px**: header stays in view, no sideways scroll.
   Browser check in Task 5.

---

## Page layouts

**Bills list (1366px):**

```
Bills                                              (page_header, meta: camp name)
───
[camp_nav active=bills]
Paid for food € 412,10 · estimated € 455,00 · [2 bills still open]   [Financial report]
┌ Paid and estimated per shop ─┐ ┌ Paid per category ─────────┐
│ Shop     Estimated   Paid    │ │ Camp food        € 380,00  │
│ Colruyt  € 300,00  € 280,00  │ │ Total            € 431,50  │
└──────────────────────────────┘ └────────────────────────────┘
┌ Bills ───────────────────────────────────────────────────────┐
│ Date         Shop     Status        Lines total              │
│ Sat 1 Aug 2026 Colruyt [To review]   € 102,30   Review →     │
└──────────────────────────────────────────────────────────────┘
┌ Add a bill ──────────────────────────────────────────────────┐
│ [⚠ Bills can hold personal data …]                           │
│ PDF with text [Choose file]  Shop [▾]  Date [....]           │
│ [⇧ Upload bill]                                              │
└──────────────────────────────────────────────────────────────┘
```

**Bill review (full width):**

```
← All bills
Colruyt, 1 Aug 2026 [To review]
Lines total € 102,30 · printed total € 102,30
───
(alert-danger: couldn't be read + error) (alert-warning: lines don't add up)
Check every line. … (form-text)
┌ table: Description | Ingredient [▾][+] | Category | Qty | Per item | Total | Skip | Stock | Delete ┐
[+ Add a line]                                                   [✓ Save review]
───
[⇩ Download file] [Remove file, keep amounts]                   [🗑 Delete bill]
```

**Financial report:** page header "Financial report", meta `{{ start|short_date }} –
{{ end|short_date:"year" }} · headcount`, action "Report PDF" (outline,
`bi-file-earmark-pdf`); camp_nav `active="report"`; then the body.

---

### Task 1: "Add a line" on the review table (Claude)

**Files:**
- Create: `templates/bills/_bill_line_row.html`
- Modify: `bills/views.py`, `bills/urls.py`, `static/js/ingredient_dialog.js`
- Test: `tests/test_bills.py`

**Interfaces:**
- Produces:
  - `templates/bills/_bill_line_row.html`, context `form` (a `BillLineForm`) and
    optional `total_forms`: one `<tr>` with the nine cells (inputs through
    `|table_input`, errors as `invalid-feedback d-block`, row errors `text-danger
    small`). The ingredient cell: `div.input-group.input-group-sm` with the select and
    a `btn btn-outline-secondary` button (`type="button"`, `data-new-ingredient`,
    `data-select="{{ form.ingredient.html_name }}"`, `data-name-from="{{
    form.description.html_name }}"`, `aria-label` and `title` "New ingredient",
    `bi-plus-lg`). The stock cell shows "In stock as {{ name }}" in
    `text-body-secondary` when `form.instance.utensil`. The delete cell only for saved
    lines. With `total_forms`, an out-of-band `id_form-TOTAL_FORMS` input as in
    `partials/_formset_row.html`.
  - URL `bill_line_row`: `camps/<int:camp_id>/bills/<int:bill_id>/line-row/` →
    `bill_line_row(request, camp_id, bill_id) -> HttpResponse`: `_bill` first, then one
    empty `BillLineFormSet` form numbered by `?form-TOTAL_FORMS` (`core.rows.row_index`),
    with the ingredient and stock choices `bill_detail` builds (move those two lists
    into one helper `_line_choices(chiro) -> tuple[list, list]`).
  - `bill_detail`: POST with `add_row=form` bumps `form-TOTAL_FORMS` (copy of the
    data), renders without saving and without `apply_review`.
  - `ingredient_dialog.js`: one `document.addEventListener("click", …)` that finds
    `event.target.closest("[data-new-ingredient]")` instead of binding each opener at
    load; behaviour otherwise unchanged.

- [ ] **Step 1: Failing tests:**
  - `test_bill_line_row_gets_the_next_index`: GET `bill_line_row?form-TOTAL_FORMS=3`
    → `name="form-3-description"`, `data-select="form-3-ingredient"`, an option with an
    existing ingredient's name, TOTAL_FORMS `value="4"` with `hx-swap-oob`.
  - `test_add_line_without_javascript_keeps_edits_and_saves_nothing`: upload the text
    bill, post `review_data(bill, **{"0_ingredient": carrots.pk, "0_pack_amount": "1"})`
    plus `add_row=form` → 200, `form-{n}-description` for n = number of lines (one more
    row), no `IngredientPrice`, bill status unchanged.
  - Add `"bill_line_row"` to `_bill_urls` (other Chiros 404, anonymous redirected).
- [ ] **Step 2:** Run `tests/test_bills.py`: FAIL.
- [ ] **Step 3:** Implement. The page template keeps working with its own row markup
  until Task 2 switches it to the partial.
- [ ] **Step 4:** Run `tests/test_bills.py tests/test_auth.py`: PASS.

### Task 2: Bill review page (ui-builder)

**Files:**
- Modify: `templates/bills/bill_detail.html`, `static/css/app.css` (bill rules only)
- Test: `tests/test_ui_move.py`, `tests/test_bills.py`

**Interfaces:**
- Consumes: Task 1's partial and URL; `back_link`, `page_header` (with `badge`),
  `camps/_example_note.html`, `recipes/_new_ingredient_dialog.html` (unchanged
  include).

- [ ] **Step 1: Failing tests:** add `"bills/bill_detail.html"` and
  `"bills/_bill_line_row.html"` to `CONVERTED_TEMPLATES`; in `tests/test_bills.py`:
  - `test_review_page_layout`: one `<h1`, `page-rule`, the status badge class for "To
    review", `hx-get="<bill_line_row url>"`, `btn-outline-danger` on Delete bill.
  - `test_failed_bill_without_file_can_be_typed` (Review Focus 4): unknown-layout
    upload, remove the file, GET → the error text, "The file was removed.",
    `form-0-description`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Rewrite per "Bill review" above. Title: `{{ bill }}`; badge: the
  status (class by status). The table keeps the `bill-lines` class and column classes;
  the add button is `btn btn-outline-primary btn-sm` `type="submit" name="add_row"
  value="form" formnovalidate` with `hx-get`, `hx-include="#id_form-TOTAL_FORMS"`,
  `hx-target="#bill-lines-rows"`, `hx-swap="beforeend"` (the `tbody` gets
  `id="bill-lines-rows"`). In `app.css`, keep the sticky header, column widths and
  full-width rule (renamed to the new wrapper if it changes); drop `.with-button`.
- [ ] **Step 4:** Run `tests/test_bills.py tests/test_ui_move.py tests/test_kitchen.py`:
  PASS.

### Task 3: Bills list (builder)

**Files:**
- Modify: `templates/bills/bill_list.html`
- Test: `tests/test_ui_move.py`, `tests/test_bills.py`

- [ ] **Step 1: Failing tests:** add `("bill_list", lambda camp: [camp.pk])` to
  `CONVERTED_PAGES` and the template to `CONVERTED_TEMPLATES`;
  `test_bill_list_shows_status_badges`: one uploaded text bill → `text-bg-warning`;
  `test_bill_list_empty_state`: no bills → `bi-receipt`. Keep
  `test_upload_page_shows_the_privacy_warning` passing.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Rewrite per "Bills list" above. The upload form through crispy
  (`{% crispy form %}` is not used in this app; render fields with `|as_crispy_field`
  in a `row g-3`, file `col-lg-6`, shop and date `col-lg-3`), `enctype` kept, errors
  through `components/form_errors.html`.
- [ ] **Step 4:** Run `tests/test_bills.py tests/test_ui_move.py`: PASS.

### Task 4: Financial report, page and PDF (ui-builder)

**Files:**
- Modify: `templates/bills/report.html`, `templates/bills/_report_body.html`,
  `templates/bills/report_print.html` (CSS block only)
- Test: `tests/test_ui_move.py`, `tests/test_report.py`

- [ ] **Step 1: Failing tests:** add `("financial_report", lambda camp: [camp.pk])` to
  `CONVERTED_PAGES`, both page templates to `CONVERTED_TEMPLATES`;
  `test_report_warnings_are_alerts`: a camp with an open bill → `alert-warning`, no
  `⚠️`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Rewrite per the design's "Financial report". In
  `report_print.html` add rules so the PDF keeps its look: `.alert` / `.alert-warning`
  (today's `.warning` box), `.text-body-secondary` (today's `.muted`), `.text-success`
  (today's `.ok`), `.badge` (as today), `.text-end` (right-aligned), `.table` (as the
  plain table rules). Remove the PDF rules for classes no longer used.
- [ ] **Step 4:** Run `tests/test_report.py tests/test_ui_move.py`: PASS. Build the
  Docker image and run `tests/test_pdf.py` in it; also render the report PDF of a demo
  camp to a file and look at it (sections, warning box, right-aligned amounts).

### Task 5: app.css, Dutch strings, static and browser review (Claude, opencode reviewer, ui-reviewer)

- [ ] **Step 1:** Remove the old report rules (`.report*`, `.ok`) and anything else
  only area 4's old templates used; grep before deleting.
- [ ] **Step 2:** makemessages and msgfmt in Docker; translate; no fuzzy.
- [ ] **Step 3:** opencode `reviewer` on the changed templates, two per run; my own
  read of anything it flags.
- [ ] **Step 4:** Throwaway server with `seed_demo`; upload a text bill (the test's
  Colruyt text) and add lines to reach 40. `ui-reviewer` at 1366px and 375px as
  `member` and `admin`: bills list (upload, refused photo), review (Review Focus 1, 5;
  add a line with and without HTMX; save; remove file; delete asks for confirmation),
  report page and its PDF link. 375px fallback (srcdoc iframe) given up front.
- [ ] **Step 5:** Fix, restart the `--noreload` server, re-check; at most three
  rounds.

### Task 6: Finish area 4 (Claude)

- [ ] **Step 1:** Help page `pages/content/bills.md` / `.nl.md`: "Add a line" on the
  review, if they describe typing lines.
- [ ] **Step 2:** All checks; PDF tests in Docker; whole-area review (Opus);
  `secret_reviewer` plus my own scan.
- [ ] **Step 3:** `docs/TODO.md`: tick area 4 with this plan's path; "Found in area 4's
  review" for what's parked. Mark the design "Built". Commit on `ui/area-4-bills`:

```bash
git commit -m "Move the bills and financial report pages to Bootstrap (UI move, area 4)"
```

- [ ] **Step 4:** Push from Windows, PR into `dev` with `gh`, wait for checks.
