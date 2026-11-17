# UI move, area 3: shopping, budget and stock. Design

Date: 2026-11-17. Roadmap step 3, area 3. **Built; folded into `docs/spec/shopping.md`
(and D20 into `docs/SPEC.md`).** Builds on
`docs/superpowers/specs/2026-11-16-ui-move-design.md`, whose rules (goals, done per
area, the per-area way of working) all apply. This note only adds what area 3 decides
on top of them.

## Intent

Move the shopping page, the budget, the Chiro stock page and the camp's kitchen
utilities page to Bootstrap and the shared components (`templates/shopping/`,
`templates/kitchen/`; `shopping_print.html` is only checked, area 6).

The shopping trips are **Collect&Go pickups**. The page is used at two moments:

- **Planning, on a PC:** pick the shopping days, read the warnings, place each trip's
  order shop by shop.
- **At the pickup, on a phone:** someone opens the trip's list to see that everything
  is there. The order comes preloaded and the shopkeeper checks it too, so this is a
  check on sight, not ticking lines off.

## Goals

- The five pages on Bootstrap, per the UI move design's "Done per area".
- The shopping page's **trip lists** read well on a phone as well as on a PC, and
  someone at the pickup gets to the right trip's list in one tap.

## Non-goals

- Ticking lines off, in the browser or shared (the user chose read only). A shared
  check belongs with kitchen mode, if ever.
- A separate page or link per trip. That would be a new view; it could be its own
  roadmap step later.
- Changes to the shopping logic, the budget, the PDF or the models.

## Anti-goals

- The phone list fixed at the cost of the PC: on a PC the page keeps its order (days,
  then warnings, then lists) and the shops of a trip side by side.
- A list you have to scroll sideways on a phone, or names cut off.

## Approaches

- **A. Jump links at the top.** One button per trip under the page header, jumping to
  that trip's list; a "back to top" link per list. Same page and order. **Picked by
  the user.**
- B. Lists first, settings after: faster on a phone, but on a PC you set the days and
  then read the result, and the uncovered-days warning would end up below the lists.
- C. A separate page per trip: cleanest on a phone, but a new view and URL, which the
  UI move rules out.

## Decisions

- **D20** (2026-11-17): **The shopping page's trip lists work equally on a phone and
  a PC**, an exception to D19, because they're read at the Collect&Go pickup. The day
  picker, the warnings, the budget and the stock pages stay PC-first. Recorded in
  `docs/SPEC.md` next to D19, with the guideline line in `docs/ui-guidelines.md`
  updated.

## Design

### Shopping page

- Page header with the camp name and "Shopping", actions: shopping lists PDF and
  budget (as now, only when there are trip lists).
- **Trip jump links** right under the header (only when there are trip lists): one
  button per trip, with the day and date and the number of shops, e.g.
  "Tue 14 Jul · 3 shops", linking to `#trip-<id>`. They wrap on a phone. Plain links,
  no JavaScript.
- Then, in today's order: outside-dates warning, pantry line, shopping days (a card
  with the date checkboxes), uncovered-days warning, the trip lists, the kitchen
  utilities to buy.
- **Each trip list** is a section with `id="trip-<id>"`: heading "Shop on …", the
  covered days, then one card per shop (shop name and item count in the card header),
  the categories as small headings inside, and the lines as name plus quantity. On a
  PC the shop cards of one trip sit side by side (`row` with columns from `lg`); on a
  phone they stack, each line on one row with the quantity right-aligned, names
  wrapping rather than cut off. A "back to top" link closes each trip.
- Warnings become Bootstrap alerts (warning) with an icon instead of the emoji;
  "Remove" on an outside trip is a small outline button.

### Budget

- Page header with the camp name and "Budget"; the estimated total and cost per
  portion per day as the summary under it, with the links to the bills and the
  ingredients page.
- Shop totals as a row of small cards (a "+ N without price" note in the partial
  ones).
- Warnings (no price, unit conflict, uncovered days) as alerts.
- Per trip: heading with its total as a badge, per shop a card with the shop total,
  and per category a table (Ingredient, Qty, Unit price with "this camp"/"latest" and
  date, Cost) in `table-responsive`; lines without a price marked as on the
  ingredient list (warning badge "no price"). PC-first.

### Chiro stock

- Page header with the Chiro name and "Stock"; the example note as an alert.
- Two cards, "Kitchen utilities" and "Pantry" (keeps `id="pantry"`, which the
  shopping page links to), each with its explanation, its form and its own Save
  button. The two forms stay separate posts (`section` field), as now.
- The utilities table stays built by hand, because of its read-only "Needed by"
  column, but gets Bootstrap form controls and table classes. The pantry uses the
  shared formset partial.

### Camp kitchen utilities

- Page header with the camp name and "Kitchen utilities".
- "To buy" as a table in a card; "Everything is in stock." as a success line.
- The needs form through the shared formset partial, with the datalist kept.

### Adding rows

The pantry and the camp's utilities form turn on the shared partial's existing "add a
row" button (HTMX in place, a plain post without JavaScript), as the camp form does.
This reuses area 1's mechanism: the views get the same `add_row` handling the camp
form has (`camps/views.py`), plus a small row URL for the HTMX request, like the camp
form's group row. The stock page's hand-built utilities table keeps its spare empty rows.

## Left to the builder

- The exact Bootstrap classes, spacing and icons, within `DESIGN.md`.
- How the jump links look (button group or a row of small outline buttons), as long
  as they wrap at 375px and are tap-sized.
- Which old `app.css` rules (`.shop-grid`, `.shop-section`, `.shop-totals`,
  `.budget-table`, `.category-block`, …) can go once nothing uses them; the PDF's own
  CSS is not touched.
- Splitting the work into tasks (the plan).
