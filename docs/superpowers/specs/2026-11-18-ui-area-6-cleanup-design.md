# UI move, area 6: print check and clean-up. Design

Date: 2026-11-18. Roadmap step 3, area 6, the last one. **Built; folded into `docs/DESIGN.md` §3.3, §3.4 and §8.** Builds on
`docs/superpowers/specs/2026-11-16-ui-move-design.md`. Branch `ui/area-6-cleanup`,
built on `ui/area-5-accounts` (needs area 5's templates off the old classes). Two
stacked PRs: area 5's into `dev`, area 6's says it builds on area 5 and is merged after it.

## Intent

Close the UI move: every PDF still renders, `app.css` keeps only the Chiro theme and
what Bootstrap can't do, and `DESIGN.md` describes the theme as it now is. The user
picked the narrow scope (option A): clean-up plus a few cheap fixes; the behaviour
fixes parked in areas 1–4 wait for their own step.

## Goals

- `app.css` holds: the `:root` tokens Bootstrap reads, the button/form overrides
  Bootstrap compiles in, the navbar and red rule, the heading font, focus rings, and
  the few rules still used (planner slot chips, the bill review table, the dialog,
  `.table-responsive` positioning, `.prose`, `.runbook-day`). Every other rule goes.
- No template uses a class that only the removed rules defined.
- All five PDFs render in the Docker image and look as before.
- Two contrast fixes from area 2's review: the danger red and the checkbox border.
- Two small leftovers: `alert-link` in `planning/_outside_entries.html`, and
  `camps/camp_form.html` loading `headcount.js` through `{% asset %}`.

## Non-goals

- The print templates' look (they keep their own `<style>`; only checked).
- Example controls, save confirmations, Enter in row tables: a later step.
- A new visual style.

## Anti-goals

- A page that changes look because a rule it still needed was removed.
- A PDF that breaks or changes because of the clean-up.

## Approaches

- **A. Clean-up plus the cheap fixes.** Picked by the user.
- B. A plus the parked behaviour fixes (views in three areas): its own step instead.

## Design (Claude's calls)

### `app.css`

- Remove the old tokens (`--accent*`, `--bg`, `--surface`, `--text`, `--border`,
  `--warn-*`; keep `--muted` only if still used, else rely on `--bs-secondary-color`),
  and the rules only old classes used: the old `.btn` family (`.btn:not(…)`,
  `.btn-outline`, `.btn-small`, `.btn-danger*` overrides), `.card`, the element
  `table`/`th`/`td` rules for non-Bootstrap tables, `table.compact`, `.muted`,
  `.page-meta`, `.back-link`, `.warning`, `.empty-slot`, `.badge`, `.table-scroll`,
  `.actions`, `.outside-list`, `.stacked-form`, `.form-row`, the unstyled
  `select`/`input` fallback, `.login-card`, `.toc`, `.hero`, `.feature-grid`,
  `.header-auth`, `.prewrap` and `.card h3`, each after a `grep` over `templates/`
  and `static/js/` shows no user left. A rule still used stays, with a comment
  saying why.
- The element rules for `h1`–`h3` and `a` stay only where they set the theme (the
  heading font); sizes and margins that fight Bootstrap's go.
- Contrast: `btn-outline-danger`, `btn-danger`, `text-danger` and `text-bg-danger`
  use a darker red, `#B02A37` (Bootstrap's red-600), set through `--bs-danger`,
  `--bs-danger-rgb` and the two buttons' `--bs-btn-*` variables (the subtle
  background and text-emphasis variables, used by `alert-danger` and the missing
  slot chip, are already dark enough and stay), so danger text and
  outlines reach 4.5:1 on sand-faint. `.form-check-input` gets a border colour of at
  least 3:1 on white and sand-faint (`#6C757D` or darker).
- A test keeps it clean: every class selector in `app.css` is used somewhere in
  `templates/`, `static/js/` or the project's own Python files (not `.venv/`, not
  `tests/`), so widget `attrs` and message tags count. Classes Bootstrap's or HTMX's
  JavaScript add at run time (`show`, `collapsing`, `htmx-request`, …) go in an
  allow-list in the test, each with the reason.

### PDFs

- Render the recipe, menu overview, runbook, shopping and report PDFs in the Docker
  image (`tests/test_pdf.py` plus a look at each rendered file) and compare with
  `dev`. All five have their own `<style>` and none links `app.css` (checked with
  `grep`), so nothing should change; a break is fixed in
  that template's own `<style>`.

### `DESIGN.md`

- §8 describes `app.css` as it now is: the token block, the overrides and why, the
  few app rules that remain; the "old green tokens" migration bullets go.
- §3.3/§3.4: `danger` becomes `#B02A37` with its ratios; a line for the checkbox
  border.

### Browser check

- One round with `ui-reviewer` over a sample of every area's pages at 1366px and
  375px (camp list, planner, recipe, shopping, stock, bill review, report, account,
  login, home, a doc), looking only for regressions from the CSS removal and the new
  danger red.

### Roadmap

- Area 6 ticked and step 3 marked done; the parked items from areas 1–4 move into a
  new short step after step 3 ("UI fixes from the move"), minus the two fixed here and
  the contrast items.

## Left to the builder

- The exact order and comments in `app.css`.
- Whether `--muted` survives (only if something still uses it).
