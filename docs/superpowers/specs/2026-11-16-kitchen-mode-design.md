# Kitchen mode: design

Date: 2026-11-16. Replaces the outline in SPEC §9.19 once approved.

## Intent

The app supports the kookploeg before, during and after the camp:

1. **Before:** plan the menu per day and get the shopping lists from it. This works.
2. **During:** open the day, see what each meal needs, get it out of the pantry (or
   check it the day before), and prep and cook. The point is to **notice missing
   things early**, not halfway through cooking. Extra shopping trips happen during
   the camp, and their bills are uploaded to the camp (this already works). Each
   evening there is a short evaluation meeting, and its notes need a place.
3. **After:** review the bills for the financial report (exists), and review the
   **menu evaluation**: which recipes need changing. The team then changes those
   recipes deliberately on the recipe pages.

Kitchen mode is stage 2, plus the menu evaluation page of stage 3 that reads what
stage 2 wrote.

## Goals

- A day view per camp, usable on a phone or tablet in the kitchen or pantry.
- A shared check per meal: each ingredient is there, missing, or not checked yet.
- Missing items land on an extra shopping list for the camp, which also takes
  free-text items.
- A cooking view with one step at a time and optional, adjustable timers.
- Evaluation notes per day, with optional notes per recipe, reviewed after the camp.
- A printable day sheet as a paper fallback.
- At the end of the camp, update the Chiro's pantry with the dry goods that are left.

## Non-goals

- Splitting personal costs, and tracking deposits (waarborg/leeggoed: crates,
  Colruyt boxes). These are separate stage 3 work, to brainstorm on their own.
- Offline use. Pages need a connection; see Approaches.
- Linking recipe steps to the ingredients they use.
- Changing how the trip shopping lists or the budget are calculated.

## Anti-goals

- **Nothing done on the camp day changes a recipe.** Ticks, missing marks, amounts
  changed on the extra list, timer lengths and evaluation notes never write to
  `Recipe`, `RecipeIngredient` or `RecipeStep`. Recipe changes happen on the recipe
  pages, by a person, usually after reading the menu evaluation.
- Timers must not become a chore or a blocker: durations are guidelines (cooking in
  a tent with several pots differs a lot from a kitchen). Nothing starts on its own.
- Kitchen screens are not planning screens: no tables or dense forms on them.

## Constraints

- Stack per SPEC §3 and `docs/ui-guidelines.md`: Django templates, Bootstrap 5.3,
  HTMX, plain JS files in `static/js/` only where HTMX can't do it (timers, wake
  lock). No build step, no npm, vendored assets.
- Kitchen screen rules (ui-guidelines "Kitchen views"): base font at least 1.125rem,
  quantities and step text `fs-4` or larger, tap targets at least 44x44px, enlarged
  checkboxes, Today / check / cooking one tap apart, linked from the camp list and
  the planner.
- Every action works without JavaScript (a tick or missing mark is a form post; a
  timer shows its duration as text).
- Access per SPEC §9.9: only members of the camp's Chiro, others get a 404. Example
  camps are read-only for everyone except staff. Ticking, marking missing, the extra
  list and notes need no extra role.
- Quantities scale per SPEC §7 (`core/portions.py`), with its rounding. The day view
  shows what the meal needs; it does **not** subtract the pantry (that belongs to the
  trip lists).
- **Reachability:** the app is on the LAN only for now. Kitchen mode is only useful
  once the app is public (Cloudflare tunnel, HTTPS settings, login checked through
  it, TODO "Before going public"). That step must be done before the first camp that
  uses kitchen mode. It's a deployment dependency, not part of this build.
- Step 4 of the TODO (UI on Bootstrap and HTMX) comes first; kitchen mode builds on
  its components.

## Approaches

Considered for how the pages work with a weak signal at the camp site:

- **A. Online pages like the rest of the app.** Server-rendered, HTMX for ticks
  without reload. Fits the stack; the server holds the shared ticks, so no sync
  rules. Without signal a tick fails visibly; an open page stays readable, and the
  cooking view's steps and timers keep working because they run on the phone.
- **B. A plus a printable day sheet.** The same, plus a PDF of the day using the
  existing WeasyPrint setup: a paper fallback for camps without signal, or for the
  kitchen wall.
- **C. Offline-first.** The phone keeps a copy and queues ticks to sync later. Most
  robust, but several times the work, needs conflict rules for two phones ticking
  offline, and departs from how the app is built.

**Picked: B** (A plus the printable day sheet). C costs too much for a tick list.

Also decided in the conversation:
- Ticks per meal, not one merged list for the day (you cook per meal). Within a
  meal, an ingredient used by several recipes is one line with the summed quantity.
- A missing item goes onto an extra shopping list; that list also takes free text.
- Evaluation: a day note plus optional notes per recipe, rather than one note per day.
- Timer adjustments are kept for that day only and never touch the recipe.

## Design

### Day view

URL per camp and date, e.g. `/camps/<id>/kitchen/<date>/`; `/camps/<id>/kitchen/`
opens today while the camp runs, else its first day. Previous / next day, and a day
picker. Any camp day can be opened, including past ones (to check the day before, or
to write yesterday's evaluation).

```
Kamp 2026 · ma 14 jul        ‹ day ›
Breakfast 08:00          all 9 there ✓
Lunch 12:00              1 missing · 3 to check
  Groentesoep · Macaroni ham-kaas  ->  (tap opens the cooking view)
  [✓][✗] Onions        3 kg
  [✓][✗] Bread         6 pieces
  ...
Dinner 18:00             11 to check
[Extra shopping (2)]   [Print day]
Evaluation ▸
```

- Meals in order (breakfast, lunch, tea, dinner) with the camp's meal times. Each
  meal lists its planned recipes (link to the cooking view), then one ingredient list
  merged over those recipes: per ingredient, the sum of the scaled quantities, in its
  unit, rounded per §7.
- A meal with nothing planned shows an empty state, not an error.
- The meal header counts missing and still-to-check lines; "all there" when done.

### The check

Three states per line: not checked, **there**, **missing**. Two buttons per line
(there / missing); pressing the active one again returns it to not checked. Each is
a form post that HTMX swaps in place.

Storage: one row per checked line, keyed `camp, date, meal_type, ingredient`, with
`status` (there / missing), `checked_by`, `checked_at`. This is the planned
`IngredientCheck` with a `status` added. Because the key has no recipe, the merged
line per meal maps to exactly one row. If the menu changes and an ingredient leaves
the meal, its row is ignored (not shown); it can stay or be cleaned up, builder's
choice.

Shared: every phone shows the same state after a reload. No live push.

### Extra shopping list

One per camp, one tap from the day view and linked from the camp's shopping page.

```
Extra shopping · Kamp 2026
☐ Onions       3 kg      lunch ma 14 jul
☐ Dish soap              (added by hand)
— bought —
☑ Bread        6 pieces  dinner ma 14 jul        [Clear bought]
```

- A line is either an ingredient (with quantity in its unit) or free text (with an
  optional free-text amount). Fields: `camp`, `ingredient` (optional), `text`
  (optional; one of the two is required), `quantity` (optional), `source check`
  (optional link to the missing mark that created it), `bought` (+ who/when),
  `added_by`, `added_at`.
- Marking an ingredient missing adds a line with the meal's quantity and which meal
  it's for. The quantity can be changed on the list (you may have half).
- Undoing the missing mark removes its line if it isn't bought yet; a bought line
  stays.
- Anyone in the Chiro can add free-text lines, edit amounts, tick bought, delete a
  line, and clear bought lines.
- No link back: after buying, the cook marks the ingredient "there" in the day view.
- The list doesn't touch prices or the budget. The trip's bill is uploaded to the
  camp as now and reviewed in stage 3.

### Cooking view

From a recipe in the day view: `/camps/<id>/kitchen/<date>/<meal>/<recipe>/`
(step via query or path, builder's choice).

```
Macaroni ham-kaas · step 3 of 6
Spirelli koken met 2 blokjes tuinkruiden.
[−] [ ▶ 20:00 ] [+]
▸ Ingredients (scaled for 58)
[ ‹ Previous ]          [ Next › ]
─ Groentesoep 04:12 ⏸ · Oven 31:40 ─
```

- One step per screen, big text, big Previous / Next. The recipe's scaled ingredient
  list folds out on every step.
- A step with a duration shows a timer set to that duration, with − / + (1 minute)
  before and while running, start, pause and reset. Steps without a duration show no
  timer.
- Several timers can run at once. Running timers show in a bar at the bottom, named
  after recipe and step, and stay there across steps and recipes of the same camp
  day. At zero: a sound and a flashing bar until dismissed.
- Timers run in the phone (JS in `static/js/`), kept in browser storage so they
  survive page loads. A changed length is remembered on that phone for that camp day
  only, never on the server, never on the recipe. If storage isn't available, timers
  still work within the page.
- **Screen stays on** while at least one timer runs (Screen Wake Lock API), released
  when the last one stops. Where the browser doesn't support it, nothing happens.
- Known limit: a locked phone may delay the sound; the remaining time stays correct
  because it's computed from the start time.
- Without JavaScript: the step shows "20 min" as text, Previous / Next are links.

### Evaluation notes

On the day view, below the meals (folded when empty).

- A **day note**: free text, one per camp day, optional.
- **Recipe notes**: for any recipe planned that day, an optional free-text note plus
  an optional quick tag: *good*, *too little*, *too much*, *adjust recipe*. One note
  per recipe per day (lunch and dinner using the same recipe the same day share it).
- Anyone in the Chiro can write and edit them, on any camp day, during or after the
  camp. Stored with who wrote them and when.
- Separate from `DayNote` (runbook notes written before the camp and printed in the
  draaiboek).

### Menu evaluation (stage 3)

A page per camp, linked from the camp and next to the financial report:

- The day notes in date order.
- The recipes that got notes, with their tags and notes per day, recipes tagged
  *adjust recipe* or *too little/too much* first, each linking to the recipe page.
- On a recipe's page: notes about it from earlier camps, limited to camps of the
  Chiros the viewer belongs to (camp data stays private to its Chiro; recipes are
  shared). Shown as read-only history next to the recipe.
- **Notes follow copies.** Recipes get a `copied_from` link (nullable, `SET_NULL`),
  set by "save a copy". A recipe's history shows its own notes plus those of the
  recipes it was copied from, up the chain, each labelled with the recipe and camp.
  Copies made before this change have no link; that's accepted.
- In the menu evaluation, a recipe the viewer can edit links to its edit page; one
  they can't edit (read-only, no author, locked by another Chiro's camp) offers
  "save a copy" there, using the existing copy form. Permission flags come from the
  view, per ui-guidelines.

### Pantry count at the end of the camp

Leftover dry goods last until next year. The Chiro's pantry (`PantryItem`, SPEC
§9.12) already holds this and every later camp subtracts it from its lists, so the
end of the camp updates that pantry rather than keeping anything new.

- The day view of the **last camp day** shows "Update the pantry". The page stays
  reachable from the camp page afterwards, so the count can also be done at home.
- One form, phone-friendly, listing:
  - every ingredient in the Chiro's pantry now, prefilled with its stored quantity;
  - the camp's planned ingredients in category *dry goods* not in the pantry yet,
    empty;
  - "add another ingredient" for anything else.
- What you enter is **what is left**: it replaces the stored quantity (the old stock
  was used by this camp's lists). Empty or 0 removes the item from the pantry. Lines
  left untouched keep their value.
- Anyone in the Chiro can do it, as on the stock page. Saving shows what changed.
- It changes the Chiro's pantry, never a recipe, so it fits the anti-goal above.
  Another camp of the same Chiro planned later sees the new stock on its lists right
  away, as pantry changes already do.

### Printable day sheet

"Print day" on the day view: a PDF via the existing WeasyPrint setup, with its own
print CSS (DESIGN.md §7). Per meal: time, recipes, the merged ingredient list with
empty tick boxes, then each recipe's steps with durations. It doesn't include check
state or notes; it's the plan for the day.

### Links

- Camp list and planner: a "Kitchen" link to the camp's day view.
- Inside kitchen mode: day view <-> cooking view <-> extra list, one tap apart.

## Data (summary)

New, in the `kitchen` app:
- `IngredientCheck`: `camp`, `date`, `meal_type`, `ingredient`, `status`,
  `checked_by`, `checked_at`; unique on `camp, date, meal_type, ingredient`.
- `ExtraShoppingItem`: as above.
- `DayEvaluation`: `camp`, `date`, `text`, `updated_by`, `updated_at`; unique on
  `camp, date`.
- `RecipeEvaluation`: `camp`, `date`, `recipe`, `tag` (optional), `text`,
  `updated_by`, `updated_at`; unique on `camp, date, recipe`. A recipe with notes
  stays deletable; the note keeps working or goes with it, builder's choice
  (`CASCADE` is fine).

Changed, in the `recipes` app:
- `Recipe.copied_from`: optional link to the recipe it was copied from, set by
  `copy_recipe`. Migration needed.

Docs to update with the build: SPEC §6 (recipes, kitchen), §9.1 (copies) and §9.19, TODO step 5, help pages
(EN + NL).

**This reverses SPEC §13 decision 16** ("Kitchen mode checks ingredients, it doesn't
shop") and the §9.4 sentence "Kitchen mode has no shopping list". Rewrite both, dated
2026-11-16: the trip shopping lists stay with the planner; kitchen mode adds an extra
shopping list for trips during the camp, filled from missing marks and free text. It
never touches prices, the budget or the trip lists.

## Left to the builder

- URL shapes, view and template names, how HTMX swaps are scoped.
- Whether a meal's list is grouped by category or kept in recipe order (pick what
  reads best on a phone; category is a reasonable default for a pantry run).
- The timer sound file (vendored, small) and bar styling, within DESIGN.md.
- Ordering of the work, with the day view and check first and timers last.
- Clean-up of check rows for ingredients no longer in a meal.
