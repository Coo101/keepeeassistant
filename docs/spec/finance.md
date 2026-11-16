# Finance

## Purpose

During the camp: upload the bills of every shopping trip to the camp. After the
camp: review them, which sets the camp's real prices, and produce the financial
report. Budget estimates before the camp are in [shopping](shopping.md).

## Data

- **Bill**: `camp`, `file` (optional; empty once removed), `original_name`, `shop`,
  `date`, `status` (waiting to be read / couldn't be read / to review / reviewed),
  `error`, `printed_total`, `uploaded_by`, `uploaded_at`.
- **BillLine**: `bill`, `description`, `article` (the shop's number, if printed),
  `quantity`, `pack_amount` (per item, in the ingredient's unit), `line_total` (incl.
  VAT), `category` (camp food / kitchen utilities / activity / personal / other),
  `ingredient`, `skipped`, `utensil`, `price` (the IngredientPrice it set).
- **LineMatch**: `shop`, `key` (article number, else the normalised description),
  `ingredient`, `pack_amount`, `unit`. Remembered from reviews.

## Behaviour

### Bills

- Per camp: upload bills (PDF or photo) after a privacy warning. Only members of the
  camp's Chiro can open them, always as a download. A file can be removed while
  keeping the lines, and goes when its bill or camp is deleted. (Privacy rules: see
  [SPEC](../SPEC.md).)
- Reading:
  - PDFs with text are read in plain Python (`pdfplumber`), tuned for Collect&Go
    (Colruyt) and Van Zon invoices.
  - Scans and photos wait for an Ollama vision model (`manage.py read_bills`, the
    `bill-reader` service), and stay waiting while it's unreachable.
  - Lines can always be added by hand.
  - Invoices listing amounts without VAT get the VAT added per line, so the lines add
    up to what was paid; leftover cents go on a rounding line.
  - Where a bill prints article numbers, the remembered match per shop follows the
    number; otherwise the description.
- Review: a person checks every line (ingredient, amount per item in the ingredient's
  unit, category). Saving sets the camp's price (paid / total amount) and remembers
  the match per shop. Nothing changes a price before that. The review table fits the
  page, keeps its header in view, and can create a missing ingredient per line, named
  after the line. (Prices: see [recipes](recipes.md).)
- Categories: only camp food sets prices. Camp food and other (deposits, discounts)
  count towards the food total compared with the budget. Skipped lines count for
  nothing.
- A kitchen-utilities line can go into the Chiro's stock ([kitchen](kitchen.md)), as a
  new item or onto an existing one, adding its quantity. A line is added once, however
  often the review is saved; deleting the line later doesn't take it out again.

### Financial report

- Per camp, as a page and a PDF. It first checks the bills: open bills, planned
  ingredients not on any of this camp's bills, and ingredients without any price.
- Then the cost of every planned meal: its scaled recipe at the camp's prices from
  the bills. Missing ones use the latest known price and the meal is marked
  estimated; ingredients without a price are left out and named.
- A summary: paid for food, the planned meals' cost and the difference (leftovers,
  extras, waste), food per portion per day, paid per category, and per meal type the
  total and the cost per portion.
- Personal costs are listed apart, with their total. Dividing them is planned (see
  below).

## Acceptance

None yet.

## Decisions

- **D14**: **Bills are read on our own hardware** (Python, or Ollama on a local PC),
  never by a cloud AI.

## Planned

- **Splitting personal costs**: a Splitwise-like page (who paid which bill, who owes
  whom for the personal lines, settling up). Bill lines need a person, or several,
  first. No design yet; see the roadmap in `docs/TODO.md`.
- **Deposits** (waarborg, leeggoed: beer crates, Colruyt boxes): tracking what is
  paid and returned. No design yet; see the roadmap.
- **More bill layouts**, as real bills of other shops come in.
