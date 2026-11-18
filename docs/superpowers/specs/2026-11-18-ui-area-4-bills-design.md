# UI move, area 4: bills and the financial report. Design

Date: 2026-11-18. Roadmap step 3, area 4. **Built; folded into `docs/spec/finance.md`.** Builds on
`docs/superpowers/specs/2026-11-16-ui-move-design.md`, whose rules all apply, and on
`docs/superpowers/specs/2026-11-18-bills-pdf-only-design.md`, which goes first on its
own branch. Area file: `docs/spec/finance.md`. Branch `ui/area-4-bills`.

## Intent

Move the bills list, the bill review and the financial report (page and the body it
shares with the PDF) to Bootstrap and the shared components. These pages are the
reporting stage: after the camp, someone reviews every bill on a PC, which sets the
camp's real prices, then reads the report. The review table is the densest screen in
the app and is built for a PC.

## Goals

- The three pages on Bootstrap, per the UI move design's "Done per area".
- The review table stays readable and quick on a PC at 1366px: every column
  visible without sideways scrolling, the header in view while scrolling down.
- The report page and the report PDF stay one template and both look right.

## Non-goals

- Reader or review behaviour (the PDF-only change is its own branch).
- A phone layout for the review table: at 375px it scrolls sideways inside its box.
- Splitting personal costs, deposits (roadmap).

## Anti-goals

- A review table that needs sideways scrolling on a PC, or hides columns.
- The report PDF losing its look because the shared body changed.

## Approaches

- **A. One shared report body on Bootstrap classes; the PDF's own CSS gets matching
  rules for the few classes it uses.** Picked by the user.
- B. Separate templates for the page and the PDF: every report change twice, and
  they drift.
- C. Keep the old class names styled in both places: keeps classes the UI move
  removes.

## Design

### Bills list

- Page header "Bills", meta the camp name; camp tabs (`active="bills"`); the
  example note.
- Summary line: paid for food, estimated (link to the budget), and the open bills
  as a warning badge.
- When there is spending: two cards side by side from `lg`, "Paid and estimated per
  shop" and "Paid per category", each a small table (amounts `text-end`).
- "Bills" card: a table (date `short_date:"year"`, shop, status as a badge, lines
  total `text-end`, a "Review" link); empty state (icon `receipt`) "No bills yet."
- "Add a bill" card: the privacy text as a warning alert, the form through crispy
  (file, shop, date), submit "Upload bill" (`btn-primary`, `bi-upload`).
- Status badges: To review `text-bg-warning`, Reviewed `text-bg-success`, Couldn't
  be read `text-bg-danger`.

### Bill review

- Back link "All bills"; page header with the bill (shop and date) as title and its
  status as badge; meta: lines total and, when printed, the printed total; example
  note.
- Alerts: "Couldn't be read" (danger, with the error), lines not adding up to the
  printed total (warning).
- The explanation as `form-text`.
- The review table: the same nine columns, inputs through `table_input`, the "new
  ingredient" button as a small outline icon button with `aria-label`, errors under
  the field, the formset's errors as an alert. It keeps a small `app.css` rule for the
  column widths and the sticky header (Bootstrap has no sticky table header), and the
  page keeps its full width.
- "Add a line": the shared "add a row" button (HTMX in place, plain post without
  JavaScript), as on the camp form, because typing lines by hand is now the fallback
  for unknown layouts. The row gets the ingredient and stock choices.
- Save review (`btn-primary`).
- File actions below in a toolbar: Download file (outline), Remove file, keep amounts
  (outline), Delete bill (`btn-outline-danger`, `bi-trash`). "The file was removed."
  as secondary text when there's no file.
- The new-ingredient dialog (area 2) keeps working unchanged.

### Financial report

- Page header "Financial report", meta the dates (`short_date`) and the headcount,
  action "Report PDF"; camp tabs (`active="report"`); example note.
- The shared body (`bills/_report_body.html`) uses Bootstrap classes: the check as a
  success line or a warning alert, tables as `table table-sm` with amounts `text-end
  text-nowrap`, the day total as `badge text-bg-secondary`, secondary text as
  `text-body-secondary`, empty states as secondary text (the PDF can't show icons).
- `bills/report_print.html` gets rules for those classes (`alert`, `alert-warning`,
  `text-body-secondary`, `badge`, `table`, `text-end`, `text-success`) so the PDF looks as
  today; it's checked in Docker.

### Roadmap

- A TODO under the finance step: test the reader with more real bills.

## Left to the builder

- Exact classes, spacing and icons within `DESIGN.md`.
- The exact PDF CSS lines, as long as the PDF looks as before.
- Which old `app.css` rules (`.report*`, `.ok`, `.with-button`, `.bill-lines*`
  except what the table still needs) go.
