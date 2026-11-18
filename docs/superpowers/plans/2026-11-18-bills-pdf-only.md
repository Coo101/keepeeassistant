# Bills: PDFs with text only. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bills are uploaded only as PDFs with text and read in plain Python; the
Ollama image reader, its command, service, settings and the "waiting" status go.

**Architecture:** One text helper in `bills/reading.py` serves both the upload form
(refuse a PDF without text) and the read after upload (lines, or "Couldn't be read"
for an unknown layout). A migration turns waiting bills into failed ones and drops the
choice. Everything Ollama is deleted. Claude builds all of it (models, migration,
settings, compose: CLAUDE.md "keep for yourself").

**Tech Stack:** Django 5.2, pdfplumber, pytest.

**Spec:** `docs/superpowers/specs/2026-11-18-bills-pdf-only-design.md`. Area file:
`docs/spec/finance.md`. Branch `feature/bills-pdf-only` from `origin/dev` (2fd43a9).

## Global Constraints

- **D21:** bills are PDFs with text, read in plain Python; no AI. Replaces D14.
- Upload errors, verbatim:
  - not a `.pdf`: "Upload a PDF. Turn a photo into a PDF with text first."
  - no text or unreadable: "This PDF has no text the app can read. Make a PDF with
    text (with text recognition), or ask for the shop's digital invoice."
  - the existing 15 MB message stays.
- Unknown layout error on the bill, verbatim: "This shop's layout isn't known yet:
  add the lines by hand."
- Migrated waiting bills get the error, verbatim: "Waiting for the AI reader, which
  is gone: add the lines by hand."
- No existing bill or line is lost. Review, prices, matches and the report don't
  change.
- No new dependencies (Pillow stays: WeasyPrint needs it). The repo is public: nothing
  private in code, docs or tests.
- New user-facing strings translated in `locale/nl/LC_MESSAGES/django.po` (Docker
  makemessages/msgfmt, README; no `#, fuzzy` left).

## Review Focus

1. **A PDF that's an image wrapped in a PDF** (a phone scan without text
   recognition): refused at upload with the no-text message, nothing stored. Test in
   Task 1.
2. **A text PDF with only whitespace or a page number** (no purchase lines): accepted
   only if it has text; with no recognised lines it becomes "Couldn't be read" with
   the layout message, and the review page lets you add lines. Test in Task 1.
3. **A damaged PDF that starts with `%PDF-`**: refused with the no-text message, not a
   500. Test in Task 1.
4. **A bill that was waiting before the upgrade, with lines typed by hand**: after the
   migration it's failed, its lines kept; saving the review makes it "To review" or
   "Reviewed" as for any bill. Test in Task 2.
5. **Saving an empty review on a failed bill**: it stays failed (no lines, nothing to
   review). Test in Task 2.

---

### Task 1: Upload accepts only PDFs with text (Claude)

**Files:**
- Modify: `bills/reading.py`, `bills/forms.py`, `bills/services.py`, `bills/views.py`
- Test: `tests/test_bills.py`

**Interfaces:**
- Produces in `bills/reading.py`:
  - `pdf_text(handle: BinaryIO) -> str`: the text of the first `MAX_PAGES * 4` pages
    (as today), `""` when pdfplumber can't open or read it (any exception, logged).
  - `read_text_pdf(bill: Bill) -> None`: reads `bill.file` with `pdf_text`, then
    `store_parsed_bill` when `parse_text` finds lines, else sets status `FAILED` and
    the layout error. (No return value any more.)
- `store_parsed_bill(bill, parsed)` guard becomes "the bill still exists and has no
  lines" (status no longer checked: reading is synchronous now).
- `BillUploadForm`: field label "PDF with text", `accept=".pdf"`; `clean_file` checks
  suffix, size, `%PDF-` header and `pdf_text(upload).strip()`, then `upload.seek(0)`.

- [ ] **Step 1: Failing tests** in `tests/test_bills.py` (drop `png_bytes` and the
  PIL import once unused):
  - `test_upload_refuses_a_photo`: `upload(..., name="photo.png", content=<any
    bytes>)` → 200, no `Bill`, "Upload a PDF. Turn a photo into a PDF with text first."
    in the page.
  - `test_upload_refuses_a_pdf_without_text`: `text_pdf([])` (a valid PDF, no text)
    → 200, no `Bill`, "This PDF has no text the app can read." in the page.
  - `test_upload_refuses_a_damaged_pdf`: content `b"%PDF-1.4 garbage"` → 200, no
    `Bill`, the no-text message.
  - `test_unknown_layout_is_accepted_for_typing`: `text_pdf(["Bakkerij Testdorp",
    "Dank u wel"])` → redirect to the bill; `status == FAILED`, `error` is the layout
    message, no lines; the review page shows the error.
  - Update `test_upload_rejects_other_files`: the `.png` row stays (refused); add
    nothing else.
  - Delete `test_scan_without_text_waits_for_ollama`.
- [ ] **Step 2:** Run `.venv/Scripts/python.exe -m pytest tests/test_bills.py -q`:
  the new tests FAIL.
- [ ] **Step 3:** Implement the interfaces above. `bill_list` keeps calling
  `read_text_pdf(bill)` after saving.
- [ ] **Step 4:** Run `tests/test_bills.py`: the new tests and the reader tests that
  don't use Ollama PASS (Task 2 removes the Ollama ones).

### Task 2: Remove the AI reader and the waiting status (Claude)

**Files:**
- Modify: `bills/models.py`, `bills/reading.py`, `bills/services.py`, `bills/views.py`,
  `bills/urls.py`, `templates/bills/bill_detail.html`, `config/settings.py`,
  `config/test_settings.py`, `docker-compose.yml`, `.env.example`
- Create: `bills/migrations/0005_bills_pdf_only.py`
- Delete: `bills/management/commands/read_bills.py`
- Test: `tests/test_bills.py`, `tests/test_auth.py` (if it counts bill URLs)

**Interfaces:**
- `Bill.Status` loses `WAITING`; `status` default `Status.REVIEW`.
- Migration `0005_bills_pdf_only`: `RunPython` sets `status="failed"` and the
  migrated-bill error on every `status="waiting"` bill (reverse: no-op), then
  `AlterField` for the new choices and default.
- `bill_retry` view and URL `bill_retry` removed. `bill_remove_file` turns a `FAILED`
  bill into `REVIEW` (as today, minus `WAITING`). `apply_review` keeps a `FAILED` bill
  without lines failed.

- [ ] **Step 1: Failing tests:**
  - `test_waiting_bills_become_failed_by_the_migration`: with
    `django.db.migrations.executor.MigrationExecutor`, migrate `bills` to `0004`,
    create a bill row with `status="waiting"` and one line through the historical
    models, migrate to `0005`; the bill is `"failed"` with the migrated error, the
    line still there.
  - `test_retry_url_is_gone`: `reverse("bill_retry", ...)` raises `NoReverseMatch`.
  - `test_saving_an_empty_review_keeps_a_failed_bill_failed` (replaces
    `test_saving_an_empty_review_keeps_a_scan_in_the_queue`): a bill from the unknown
    layout upload, empty review post → still `FAILED`.
  - Delete: `test_ollama_answer_becomes_lines`, `test_bill_keeps_waiting_while_ollama_is_off`,
    `test_bad_ollama_answer_marks_the_bill_and_it_can_retry`,
    `test_read_bills_leaves_bills_with_lines_alone`,
    `test_read_finishing_after_hand_entry_changes_nothing`,
    `test_worker_stops_the_round_when_ollama_is_off`, `_waiting_bill`, `_Answer`, and
    `"bill_retry"` from `_bill_urls`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Make the changes listed under Files: delete the Ollama code,
  prompt, image helpers and `OllamaUnavailable`/`BillUnreadable` from `reading.py`;
  the command; the `bill-reader` service; `OLLAMA_URL`, `OLLAMA_VISION_MODEL`,
  `OLLAMA_TIMEOUT` (settings, test settings, `.env.example` incl.
  `OLLAMA_URL_FROM_DOCKER`); in `bill_detail.html` the "Waiting to be read" block and
  the "Try again" form (the "Couldn't be read" alert with `bill.error` stays). Write
  the migration by hand (`makemigrations` would only produce the `AlterField`).
- [ ] **Step 4:** Run the full suite and
  `DJANGO_DEBUG=1 .venv/Scripts/python.exe manage.py makemigrations --check --dry-run`:
  PASS, "No changes detected". `grep -rni "ollama\|read_bills\|bill-reader\|WAITING"
  --include=*.py --include=*.html --include=*.yml .` (outside `.venv` and old
  migrations) finds nothing.

### Task 3: Docs, translations and finish (Claude)

**Files:**
- Modify: `docs/spec/finance.md`, `docs/spec/operations.md`, `docs/SPEC.md`,
  `README.md`, `pages/content/bills.md`, `pages/content/bills.nl.md`,
  `templates/bills/bill_list.html` (privacy text only), `docs/TODO.md`,
  `locale/nl/LC_MESSAGES/django.po` (+ `.mo`), the design (mark built)

- [ ] **Step 1:** `finance.md`: "Reading" says PDFs with text only, refused otherwise,
  unknown layouts become "Couldn't be read" for typing; the status list loses "waiting
  to be read"; D14 gets "(replaced by D21)" and D21 is added. `SPEC.md`: the stack line
  and the privacy line no longer mention Ollama; it points at D21. `operations.md`:
  no `bill-reader`, no `read_bills`. README: the bills paragraph and any Ollama setup.
  Help pages (EN + NL): upload a PDF with text; photos first into a PDF with text
  recognition; unknown shops are typed in.
- [ ] **Step 2:** `bill_list.html` privacy warning: drop the sentence about scans and
  photos read by an AI model; the rest stays (the full Bootstrap move is area 4).
- [ ] **Step 3:** `docs/TODO.md`: replace "Install an Ollama vision model …" with "Test
  the bill reader with more real bills (Collect&Go, Van Zon, other shops) and add the
  layouts that come up". Mark the design "Built; folded into `docs/spec/finance.md`".
- [ ] **Step 4:** makemessages and msgfmt in Docker; translate the new strings; no
  fuzzy entries.
- [ ] **Step 5:** All checks (CLAUDE.md "Checks"); the PDF tests in Docker. Whole-plan
  review by Claude (Opus); `secret_reviewer` plus my own pattern scan of the staged
  diff.
- [ ] **Step 6:** Commit on `feature/bills-pdf-only`, files staged by name:

```bash
git commit -m "Bills: PDFs with text only, read in Python; drop the AI reader"
```

- [ ] **Step 7:** Push from Windows, open the PR into `dev` with `gh` (CLAUDE.md
  "Git"), wait for its checks. The PR body names what the user removes outside this
  repo: a `bill-reader` container or `OLLAMA_*` settings in the production stack.
