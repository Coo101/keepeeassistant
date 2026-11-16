# UI move to Bootstrap and HTMX: design

Date: 2026-11-16. Roadmap step 3.

## Intent

The app's two core jobs are **planning** (stage 1: camps, recipes, menu, shopping
lists, budget) and **financial reporting** (stage 3: bills and the report). They
must work well before anything else; kitchen mode (stage 2) only comes once the user
is satisfied with stages 1 and 3, and then only needs to work, not be polished.

Today the pages are half-converted: about 55 templates, about 31 still on the old
`.btn`, about 18 with some Bootstrap, no crispy forms, HTMX in two templates, and a
568-line `app.css` with 127 own classes. The theme, `base.html` and the components
(page header, empty state, messages) are done. This step moves every page to
Bootstrap and HTMX per `docs/ui-guidelines.md` and `docs/DESIGN.md`, core areas
first, so planning and reporting are consistent, clear and pleasant to use on a PC.

The user is not a front-end developer and leaves the UI how to Claude, working with
the frontend-design plugin and the UI agents. The user tests and reports problems as
issues on Gitea.

## Goals

- Every page on Bootstrap: page header, Bootstrap buttons and form controls, crispy
  forms, empty states with an icon, HTMX where the guidelines name it.
- Planning pages designed for a **PC** (laptop or desktop), still usable on a phone.
- `app.css` shrinks to the theme plus what Bootstrap can't do.
- Each area passes the browser review before the next one starts.

## Non-goals

- Kitchen mode (roadmap step 5): not part of this step, and its screens aren't
  touched.
- A new visual style. `DESIGN.md` (Chiro colours, navy primary, red rule, no logo)
  stays; frontend-design works within it.
- Changing behaviour, models, permissions or business logic. A page that needs new
  data stops and reports it (ui-guidelines "Out of scope").
- Print templates' look: they keep their own CSS and only get checked.

## Anti-goals

- A page that looks better but is harder to use for planning: no hiding dense
  information behind clicks or cards on a PC. Tables stay tables on a PC.
- Breaking something that works today: every converted page keeps its links, forms
  and no-JavaScript behaviour, and the tests keep passing.
- Half-converted areas left behind: an area is done in full before the next starts.

## Approaches

- **A. Full move first, area by area, core areas first.** Picked by the user.
- B. Kitchen mode first, then the planning pages: rejected; planning and reporting
  must be right before stage 2 gets attention.
- C. A fresh visual redesign: rejected; `DESIGN.md` already settles the look.

## Design

### Order of the areas

Each area is one plan (via writing-plans) and one round of review.

1. **Camps and planner**: camp list, camp form (with groups), planner and slot
   editing, runbook page, diets. (`templates/camps/`, `templates/planning/` except
   print.)
2. **Recipes and ingredients**: recipe list, one-pager, recipe form (ingredients and
   steps), ingredient list and form, the new-ingredient dialog.
   (`templates/recipes/` except print.)
3. **Shopping and budget**: shopping days and lists, budget, the Chiro stock and
   pantry page, camp utilities. (`templates/shopping/`, `templates/kitchen/` except
   print.)
4. **Bills and financial report**: bill list, bill detail and review table, report.
   (`templates/bills/` except print.)
5. **Accounts and public pages**: account, Chiro page, invitations, join request,
   login and password pages, home, news, help pages, confirm delete, 403.
   (`templates/accounts/`, `templates/registration/`, `templates/pages/`, root
   templates.)
6. **Print check and clean-up**: every PDF still renders (Docker), and `app.css`
   keeps only the theme and what's still needed.

### Layout rule change (D19)

`docs/ui-guidelines.md` now says "Mobile first, design at 375px". That changes to:

- **Planning views** (stage 1 and 3: camps, planner, recipes, ingredients, shopping,
  budget, bills, report, stock, accounts) are designed for a **PC at 1366px wide**,
  then checked at 375px: no horizontal page scroll, tables scroll inside their box,
  forms in one column, nothing cut off. Two-column forms from `lg`.
- **Kitchen views** (stage 2) are designed for a **phone at 375px and a tablet at
  768px**.
- **Public pages** (home, news, help, login, join) work equally at both.

Recorded as **D19** in `docs/SPEC.md` (UI) with the date, and the guideline lines
updated. The kitchen mode design gets "phone or tablet" where it says phone.

### Per area: how the work goes

1. **Look (Claude with frontend-design):** read the area's templates and the area
   file in `docs/spec/`, then decide the layout for each page within `DESIGN.md`:
   what's the main action, what goes in the header, which tables, which forms in
   one or two columns, where HTMX applies. Written down as a short per-page note in
   the area's plan, with a text sketch for pages whose layout changes.
2. **Plan (Claude):** tasks of one page or one partial each, with the layout note,
   the guideline and DESIGN lines that matter, and the URLs to check.
3. **Build:** opencode `builder` for one template or form per task; `ui-builder`
   for pages with a larger layout change or HTMX wiring across view and template.
4. **Static check:** opencode `reviewer` on the changed templates (translation,
   labels, HTMX attributes, colours, danger buttons, the app's name).
5. **Browser review:** `ui-reviewer` at 1366px and 375px, as a plain member and as
   a Chiro admin (and a logged-out visitor for public pages), up to three rounds of
   fixes (CLAUDE.md "The UI loop"). Area 1's plan adds a plain member login to
   `seed_demo` (dev only, `DJANGO_DEBUG=1`), next to the existing `admin`.
6. **Finish:** remove the area's now-unused rules from `app.css`, run the checks and
   the opencode `secret_reviewer`, update the help pages if a screen works
   differently. Then commit the area on its own branch (`ui/area-N-<name>`, from
   `origin/dev`; files staged by name), push it and open a PR into `dev` (CLAUDE.md
   "Branches"), and start the next area without waiting. The user chose this: they
   review and merge the PRs, test when it suits them and open issues on Gitea, which
   go into the next round or the next area's plan. Area 1 was committed straight on
   `dev` (6b8e60d), before this branch rule existed.

### Done per area

- No old `.btn` or old layout classes in the area's templates; `grep` shows none.
- Every full page uses `components/page_header.html`; every list has an empty state
  with an icon.
- Forms through crispy (`crispy-bootstrap5`); inline errors plus a summary alert.
- HTMX only where something already exists to enhance: the recipe page's "scale to …
  portions" form updates live; the existing recipe and ingredient searches (`?q=`)
  filter as you type; inline add/remove rows on the recipe and camp forms. No new
  filters or new inputs. Each also works as a plain post or link; views choose
  fragment vs page with `request.htmx`.
- Dates as `ma 14 jul`, one `h1` per page, headings in order, labels on every input.
- `ui-reviewer` passes at 1366px and 375px; all tests pass; the area's PDFs render.

### Known items from the old roadmap

Folded into their area: the recipe search box focus ring (area 2), the camp list's
empty-state icon and long dates (area 1), the home page jumping from `h1` to `h3`
(area 5), the theme check at phone width (area 1, first review), `DESIGN.md` §8
clean-up (area 6).

### Roadmap changes

- Step 3 becomes "UI move" with the six areas as a checklist and a link to this
  design; its status follows the areas.
- Step 5 (kitchen mode) gets a line: "Starts once the user is satisfied with stages 1
  and 3. Needs to work; polish comes later."

## Left to Claude per area

- The concrete layout of each page (within `DESIGN.md` and this design).
- Which tasks go to opencode `builder` and which to `ui-builder`.
- New components when the same markup appears twice.
- Splitting an area into two plans if it's too big for one.
