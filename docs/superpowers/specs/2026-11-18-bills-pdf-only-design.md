# Bills: PDFs with text only, no AI. Design

Date: 2026-11-18. **Built; folded into `docs/spec/finance.md` (D21).** Before UI move area 4 (roadmap step 3), on its own branch
`feature/bills-pdf-only`. Area file: `docs/spec/finance.md`.

## Intent

The server has no AI, and the user won't let other users spend their credits on one.
Photos of receipts are turned into a PDF with text by another tool before upload. So
the app reads bills only from PDFs that hold real text, in plain Python, and refuses
anything else at upload with a clear error. Import stays what it is: the existing
reader (tuned for Collect&Go and Van Zon) fills in the lines and links as many as it
can through the remembered matches per shop. The current options are fine for now.

## Goals

- Upload accepts only PDFs with extractable text; an image, a PDF without text or a
  damaged file is refused with a form error, nothing stored.
- A text PDF the reader recognises is filled in as today (lines, matches, status "To
  review").
- A text PDF in a layout the reader doesn't know is accepted with no lines and the
  status "Couldn't be read", with the message that its layout isn't known yet and the
  lines can be added by hand.
- The Ollama path is gone: no vision reader, no `read_bills` command, no `bill-reader`
  service, no `OLLAMA_*` settings, no "Try again" button.

## Non-goals

- Better parsing or new layouts. The user tests the reader with more bills later
  (roadmap TODO).
- Changes to the review, prices, matches or the report.

## Anti-goals

- Losing an existing bill or its lines. Bills already "waiting" stay, as "Couldn't be
  read", so their lines can be typed in.

## Approaches

- **Refuse at upload, remove the AI path.** Picked: the user asked for an error when
  a PDF has no text.
- Keep image upload with hand entry only: rejected, it leaves a status nobody can
  leave except by typing, and invites uploads the reader can't use.
- Keep the Ollama code switched off: rejected, dead code and a service that does
  nothing.

## Decisions

- **D21** (2026-11-18): **Bills are PDFs with text, read in plain Python; no AI.**
  Replaces D14. Recorded in `docs/spec/finance.md` (D14 marked "replaced by D21") and
  in `docs/SPEC.md` where D14 is mentioned.

## Design

- **Upload form** (`bills/forms.py`): the file field is "PDF with text"
  (`accept=".pdf"`). `clean_file` checks the `.pdf` suffix, the 15 MB limit, the
  `%PDF-` header, and that pdfplumber finds text on at least one page (the same
  page limit the reader uses). Errors:
  - not a `.pdf`: "Upload a PDF. Turn a photo into a PDF with text first."
  - no text or unreadable: "This PDF has no text the app can read. Make a PDF with
    text (with text recognition), or ask for the shop's digital invoice."
- **Reading** (`bills/reading.py`): only `read_text_pdf` stays. After upload it
  stores the parsed lines (status "To review") or, when no lines are recognised, sets
  status "Couldn't be read" with the error "This shop's layout isn't known yet: add
  the lines by hand." The Ollama functions, `OllamaUnavailable`, the prompt and the
  Pillow/pdfium image code go.
- **Model** (`bills/models.py`): the `WAITING` choice goes; the default status
  becomes `REVIEW`. A data migration sets every waiting bill to `FAILED` with the
  error "Waiting for the AI reader, which is gone: add the lines by hand." Then the
  field's choices and default change (same migration or the next).
- **Views and URLs:** `bill_retry` and its URL go. `bill_remove_file` and
  `apply_review` drop their `WAITING` checks (`FAILED` stays: a failed bill without
  lines stays failed when saved empty).
- **Template** (`bills/bill_detail.html`): the "Waiting to be read" block and the
  "Try again" form go. The "Couldn't be read" alert stays with the error. (The full
  Bootstrap move is area 4.)
- **Removed:** `bills/management/commands/read_bills.py`, the `bill-reader` service
  in `docker-compose.yml`, `OLLAMA_URL`, `OLLAMA_VISION_MODEL`, `OLLAMA_TIMEOUT` in
  `config/settings.py` (and `config/test_settings.py` if set there), their lines in
  `.env.example` and the README.
- **Docs:** `docs/spec/finance.md` "Reading" and the upload privacy text (no AI model
  any more), `docs/spec/operations.md` (no bill-reader), `docs/SPEC.md`, the help
  page on bills (EN + NL), the privacy warning on the bills page, and a roadmap item
  "Test the bill reader with more real bills (Collect&Go, Van Zon, other shops) and
  add layouts that come up".
- **Tests:** image upload refused; PDF without text refused; damaged PDF refused; a
  text PDF in the known layout gets lines; a text PDF in an unknown layout is
  accepted as failed with no lines; the migration turns a waiting bill into failed;
  the retry URL is gone. Existing reader tests that use Ollama are removed.

## Left to the builder

- How the "has text" check shares code with `read_text_pdf` (one helper).
- Whether choices and default change in the data migration or a second one.
- Test fixtures: small text PDFs generated in the test (as the existing tests do).

## Outside this repo

The production stack lives in the homelab repo (`hetzner-prod/`). If it runs a
`bill-reader` container or sets `OLLAMA_*`, the user removes them there.
