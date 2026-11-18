# UI move, area 6: print check and clean-up. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the UI move: `app.css` keeps only the theme and what's still used, the
danger red and checkbox borders reach AA on sand, the PDFs still render, `DESIGN.md`
describes the theme as it is.

**Architecture:** A test lists every class selector in `app.css` and fails when one
has no user; the clean-up removes rules until it passes. Contrast is fixed through
Bootstrap's CSS variables. No template changes except the two leftovers.

**Tech Stack:** CSS (Bootstrap 5.3 variables), Django templates, pytest, WeasyPrint
(Docker).

**Spec:** `docs/superpowers/specs/2026-11-18-ui-area-6-cleanup-design.md` on top of
`docs/superpowers/specs/2026-11-16-ui-move-design.md`. Branch `ui/area-6-cleanup` from
`ui/area-5-accounts` (stacked; the PR says so and is merged after area 5's).

## Global Constraints

- No page may change look except through the danger red and the checkbox border.
- Danger: `#B02A37` (Bootstrap's red-600), rgb `176, 42, 55`, set through
  `--bs-danger`, `--bs-danger-rgb` and the `--bs-btn-*` variables of `.btn-danger` and
  `.btn-outline-danger`. `--bs-danger-text-emphasis` and `--bs-danger-bg-subtle` stay.
- `.form-check-input` border at least 3:1 on white and on `#FBF8EF` (`#6C757D` or
  darker).
- The print templates keep their own `<style>`; none links `app.css`. Change one only
  if its PDF breaks.
- Light mode only. No new classes in `app.css` unless a template uses them.

## Review Focus

1. **A class added at run time** (Bootstrap's `show`/`collapsing`, HTMX's
   `htmx-request`/`htmx-swapping`) or only in Python (widget `attrs`, message tags) is
   not reported as unused. Test in Task 1.
2. **The navbar on a phone after the clean-up**: the collapse still opens, links stay
   white on red. Browser check in Task 4.
3. **Headings after the element rules shrink**: `h1`–`h3` keep the condensed heading
   font and their sizes on every area's pages. Browser check in Task 4.
4. **The planner's missing-recipe chip** with the new danger red keeps readable text.
   Browser check in Task 4.
5. **Each PDF** renders with the same sections as on `dev`. Docker in Task 3.

---

### Task 1: The unused-rule test, then the clean-up (Claude)

**Files:**
- Modify: `static/css/app.css`
- Test: `tests/test_ui_move.py`

**Interfaces:**
- Produces: `css_classes(css: str) -> set[str]` (every `.name` in a selector, comments
  and `url(...)` stripped) and `used_classes() -> str` (the text of all files under
  `templates/`, `static/js/` and the project's own `*.py` outside `.venv/` and
  `tests/`), both in `tests/test_ui_move.py`. `RUNTIME_CLASSES: dict[str, str]`
  maps a class to why it's added at run time.

- [ ] **Step 1: Failing test:** `test_css_classes`: `css_classes(".a, .b:hover > .c
  {}\n/* .d */")` → `{"a", "b", "c"}`. `test_every_app_css_class_is_used`: for each
  class from `css_classes(app.css)` not in `RUNTIME_CLASSES` and not a Bootstrap
  class the vendored `bootstrap.min.css` defines (the theme overrides `.btn-primary`
  etc.), `re.search(rf"\b{re.escape(name)}\b", used_classes())` must match; the
  failure lists the unused ones.
- [ ] **Step 2:** Run: FAIL, listing the old rules.
- [ ] **Step 3:** Remove those rules from `app.css`, and the old tokens (`--accent*`,
  `--bg`, `--surface`, `--text`, `--border`, `--warn-*`; `--muted` only if nothing
  uses it). Shrink the element rules: `h1, h2, h3` keep the heading font and sizes,
  lose margins that fight Bootstrap's spacing utilities; the plain `table`, `th`,
  `td` rules and the `select`/`input` fallback go once no template has an unclassed
  table or field (`grep -n "<table>" templates` and `<table class=` without `table`).
- [ ] **Step 4:** Run the whole suite: PASS.

### Task 2: Contrast and the two leftovers (Claude)

**Files:**
- Modify: `static/css/app.css`, `templates/planning/_outside_entries.html`,
  `templates/camps/camp_form.html`
- Test: `tests/test_ui_move.py`

- [ ] **Step 1: Failing tests:** `test_danger_red_is_dark_enough`: `app.css` contains
  `--bs-danger: #B02A37` and `--bs-danger-rgb: 176, 42, 55`;
  `test_outside_entries_links_use_alert_link`: every `<a ` in
  `_outside_entries.html` has `alert-link`; `test_camp_form_scripts_are_versioned`:
  `camp_form.html` has no `{% static 'js/` and loads `headcount.js` through
  `{% asset`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Implement per Global Constraints (danger variables, both buttons'
  `--bs-btn-color`/`-border-color`/`-hover-bg`/`-active-bg` etc., checkbox border);
  `{% load assets %}` in `camp_form.html`.
- [ ] **Step 4:** Run `tests/test_ui_move.py tests/test_camp_groups.py`: PASS.

### Task 3: PDFs in Docker (Claude)

- [ ] **Step 1:** Build the image, copy the repo in, run `tests/test_pdf.py
  tests/test_report.py`: PASS.
- [ ] **Step 2:** Render the recipe, menu overview, runbook, shopping and report PDFs
  of a demo camp on this branch and on `dev`; compare page counts and look at each
  (Review Focus 5). A difference gets fixed in that template's `<style>`.

### Task 4: Browser regression round (ui-reviewer)

- [ ] **Step 1:** Throwaway server with `seed_demo`; `ui-reviewer` at 1366px and
  375px as `admin`: camp list, planner (a missing-recipe chip, Review Focus 4),
  runbook, a recipe and the recipe form, ingredients, shopping, stock, a bill review,
  the report, account, Chiro page, a delete confirmation; logged out: home, a help
  page, login, the navbar collapse at 375px (Review Focus 2). Only regressions from
  this branch count; Review Focus 3 on every page.
- [ ] **Step 2:** Fix, restart the server, re-check; at most three rounds.

### Task 5: DESIGN.md, roadmap, finish (Claude)

- [ ] **Step 1:** `docs/DESIGN.md` §8: the token block and overrides as in `app.css`
  now, the remaining app rules with one line each on why Bootstrap can't do it; drop
  the old-tokens bullets. §3.3: `danger` `#B02A37`; §3.4: its ratios on white and
  sand-faint, and the checkbox border line.
- [ ] **Step 2:** `docs/TODO.md`: tick area 6, mark step 3 done; new step after it,
  "UI fixes from the move", with the parked items from areas 1–4 except the two fixed
  here and the contrast items. Mark the design "Built"; fold anything lasting into
  `docs/ui-guidelines.md` if a guideline changed (danger colour).
- [ ] **Step 3:** All checks; whole-branch review (Opus); `secret_reviewer` plus my
  own scan. Commit on `ui/area-6-cleanup`:

```bash
git commit -m "Clean up app.css and fix the danger red contrast (UI move, area 6)"
```

- [ ] **Step 4:** Push from Windows, PR into `dev` (built on area 5's PR, said in the
  body) with `gh`, wait for checks.
