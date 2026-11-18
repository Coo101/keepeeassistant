# UI move, area 5: accounts and public pages. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the account, Chiro, invitation, request-access, login, password, home,
news, help, delete-confirmation and 403 pages to Bootstrap and the shared components.

**Architecture:** Templates only, plus one small change in the `doc` view (the help
file's first `# ` line becomes the page title). Forms render through crispy filters;
headers through `components/page_header.html`.

**Tech Stack:** Django 5.2 templates, Bootstrap 5.3, Bootstrap Icons, crispy-bootstrap5,
pytest.

**Spec:** `docs/superpowers/specs/2026-11-18-ui-area-5-accounts-public-design.md` on top
of `docs/superpowers/specs/2026-11-16-ui-move-design.md`. Area file:
`docs/spec/accounts.md`. Branch `ui/area-5-accounts` from `origin/dev`.

## Global Constraints

- Follow `docs/ui-guidelines.md` and `docs/DESIGN.md`; paste the lines a task names.
- D19: public pages (home, news, help, login, join, invitations, password pages) work
  equally at 375px and 1366px; the account and Chiro pages are designed for 1366px and
  checked at 375px. No horizontal page scroll at 375px.
- No behaviour, form-field, validation, permission or URL changes, except the `doc`
  view's title (Task 1) and the login form's label moving from the template into the
  form (Task 5). Every link, form and hidden field keeps working; existing
  tests keep passing (a test may change only where this plan says).
- Forms: a narrow column (`col-md-8 col-lg-6`; login `col-md-6 col-lg-4`), fields
  through `{{ form|crispy }}` or `{{ field|as_crispy_field }}` (`{% load
  crispy_forms_tags %}`), `components/form_errors.html` above, submit `btn
  btn-primary`. Hidden fields stay hidden (the join form's `website` honeypot!).
- Every visible text translated; existing strings kept word for word where the design
  doesn't change them. Dutch in `django.po` (Docker; no fuzzy).
- No inline `style=""`, no inline `<script>`, no emoji. Warnings `alert alert-warning`
  with `bi-exclamation-triangle`. Secondary text `text-body-secondary`.
- Icons next to text `aria-hidden="true"`; icon-only buttons `aria-label`.
- Dates through `short_date:"year"` (`{% load ui %}`).
- Don't touch `registration/password_reset_email.html` or any `*_print.html`.

## Review Focus

1. **The join form's honeypot** (`website`, `HiddenInput`) stays a hidden input after
   the crispy move. Test in Task 4.
2. **A long invitation link on a 375px phone** wraps inside the page. Browser check in
   Task 7 (`text-break` in Task 3).
3. **Login with a wrong password, and after too many tries** shows the error as an
   alert, and `next` survives. Test in Task 5.
4. **A help file without a leading `# ` line** still renders, titled with the `DOCS`
   label and its full body. Test in Task 1.
5. **A Chiro admin changing a role or removing a member** posts the same names and
   values as before (`role`, `remove=1`). Test in Task 3.

---

### Task 1: Help pages: title from the file, new layout (Claude)

**Files:**
- Modify: `pages/views.py` (`doc`), `templates/pages/doc.html`
- Test: `tests/test_accounts_and_pages.py`, `tests/test_ui_move.py`

**Interfaces:**
- Produces: `split_title(text: str) -> tuple[str | None, str]` in `pages/views.py`:
  when the first non-blank line starts with `# `, returns (that line without `# `,
  the rest of the text); otherwise `(None, text)`. `doc` passes `title` (the split
  title or `DOCS[slug]`) and `body` (the rest, rendered).

- [ ] **Step 1: Failing tests:**
  - `test_split_title`: `split_title("# Aan de slag\n\nTekst")` → `("Aan de slag",
    "\nTekst")` (rest starts after the title line); `split_title("Tekst")` →
    `(None, "Tekst")`; `split_title("\n# T\nx")` → `("T", "x")`.
  - `test_home_news_and_docs_are_public`: change `assert "<h1>" in …` to
    `html.count("<h1") == 1` and `"page-rule" in html`.
  - `test_doc_title_comes_from_the_file`: GET `doc` `getting-started` in Dutch
    (`HTTP_ACCEPT_LANGUAGE="nl"` or `translation.override` + cookie as other i18n
    tests do) → one `<h1`, containing "Aan de slag".
  - Add `pages/doc.html` to `CONVERTED_TEMPLATES`.
- [ ] **Step 2:** Run `tests/test_accounts_and_pages.py tests/test_ui_move.py`: FAIL.
- [ ] **Step 3:** Implement `split_title` and use it in `doc`. `doc.html`:
  `page_header` with `title`; `row g-4`: `nav.col-lg-3` with `aria-label` "Help
  pages" holding a `list-group` (`list-group-item list-group-item-action`, the current
  one `active` + `aria-current="page"`), body `div.col-lg-9.prose`. On a phone the
  list sits above the body.
- [ ] **Step 4:** Run the two test files: PASS.

### Task 2: Home and news (builder)

**Files:**
- Modify: `templates/pages/home.html`, `templates/pages/post_list.html`,
  `templates/pages/post_detail.html`
- Test: `tests/test_ui_move.py`

- [ ] **Step 1: Failing tests:** add the three templates to `CONVERTED_TEMPLATES`; add
  `"hero"`, `"feature-grid"`, `"login-card"`, `"prewrap"` to `OLD`. New
  `PUBLIC_PAGES: list[tuple[str, list]] = [("home", []), ("post_list", []), ("login",
  []), ("password_reset", []), ("join_request", [])]` and
  `test_public_page_has_one_h1_and_the_red_rule` (anonymous `Client()`, one `<h1`, not
  empty, `page-rule`). `test_home_headings_in_order`: GET `home`, the heading levels in
  order of appearance (regex `<h([1-6])`) never jump by more than one.
  `test_post_pages`: a published `Post` → list and detail 200, detail has one `<h1`
  with its title, and the list shows `short_date:"year"` of its date; with no posts the
  list shows `bi-newspaper`.
- [ ] **Step 2:** Run `tests/test_ui_move.py`: FAIL (login, password_reset and
  join_request stay failing until Tasks 4–5).
- [ ] **Step 3:** Rewrite per the design's "Public pages": hero with Bootstrap
  utilities (`py-4`, `col-lg-8`), `h1`, `hr.page-rule`, `p.lead`, buttons
  `btn-primary` / `btn-outline-primary` (`bi-box-arrow-in-right` on Log in), the
  request-access line `text-body-secondary`. Features `row row-cols-1 row-cols-md-2
  row-cols-lg-4 g-3`, each `col > div.card.h-100 > div.card-body` with `h2.h5` and
  text. News `h2`, post cards with `h3.h5` link and date. `post_list`: `page_header`
  "News", cards, `empty_state` icon `newspaper` "No news yet.". `post_detail`:
  `back_link` "All news", `page_header` title + date meta, `div.prose`.
- [ ] **Step 4:** Run `tests/test_ui_move.py -k "home or post or old"`: PASS.

### Task 3: Account and Chiro page (ui-builder)

**Files:**
- Modify: `templates/accounts/account.html`, `templates/accounts/chiro_detail.html`
- Test: `tests/test_ui_move.py`, `tests/test_accounts_and_pages.py`

- [ ] **Step 1: Failing tests:** both templates in `CONVERTED_TEMPLATES`;
  `test_account_and_chiro_pages_have_one_h1`: `member_client(camp, role=Role.ADMIN)`
  GET `account` and `chiro_detail` (camp's Chiro) → one `<h1`, `page-rule`.
  `test_chiro_page_member_form_unchanged` (Review Focus 5): as admin, the page has
  `name="role"` in a `form-select`, a button `name="remove" value="1"` with
  `btn-outline-danger`; an open invitation's link is inside `<code
  class="text-break">`. `test_account_without_chiro_shows_empty_state`:
  `account_client()` → `bi-people`.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Rewrite per the design's "Account" and "Chiro page". The role form
  keeps `action`, `name="role"`, its options and `aria-label`; layout `d-flex gap-2
  align-items-center` inside the cell.
- [ ] **Step 4:** Run `tests/test_accounts_and_pages.py tests/test_ui_move.py
  tests/test_auth.py`: PASS.

### Task 4: Invitations and request access (ui-builder)

**Files:**
- Modify: `templates/accounts/invitation_closed.html`, `invitation_join.html`,
  `invitation_login.html`, `invitation_signup.html`, `invitation_wrong_account.html`,
  `join_request.html`, `join_thanks.html`
- Test: `tests/test_ui_move.py`, `tests/test_accounts_and_pages.py`

- [ ] **Step 1: Failing tests:** the seven in `CONVERTED_TEMPLATES`;
  `test_join_form_honeypot_stays_hidden` (Review Focus 1): GET `join_request` →
  `type="hidden"` with `name="website"`, and no `<label` for it.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Rewrite per the design's "Invitations, request access, thanks": each
  `page_header` with the existing title; intro text as `meta` where the page has one
  (`join_request`, `invitation_signup`); forms per Global Constraints.
- [ ] **Step 4:** Run `tests/test_accounts_and_pages.py tests/test_ui_move.py`: PASS.

### Task 5: Login and password pages (Claude: login is on the keep-for-yourself list)

**Files:**
- Modify: `accounts/ratelimit.py` (label only), `templates/registration/login.html`,
  `password_change_form.html`,
  `password_change_done.html`, `password_reset_form.html`, `password_reset_done.html`,
  `password_reset_confirm.html`, `password_reset_complete.html`
- Test: `tests/test_ui_move.py`, `tests/test_accounts_and_pages.py`

- [ ] **Step 1: Failing tests:** the seven in `CONVERTED_TEMPLATES`;
  `test_login_error_is_an_alert` (Review Focus 3): POST a wrong password with
  `next=/camps/` → `alert-danger`, `value="/camps/"` on the hidden `next`, label text
  "Username or email". Keep the rate-limit tests passing.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** `LimitedLoginForm.__init__` (in `accounts/ratelimit.py`) sets the
  username field's label to `_("Username or email")` (the text the template shows
  today; the msgid already exists), so `login.html` renders both fields with
  `|as_crispy_field` and keeps the widgets' `autocomplete`/`autofocus`. Rewrite the
  seven templates per the design's "Login and passwords"; the hidden `next` input
  stays.
- [ ] **Step 4:** Run `tests/test_accounts_and_pages.py tests/test_ui_move.py
  tests/test_auth.py`: PASS.

### Task 6: Delete confirmation and 403 (builder)

**Files:**
- Modify: `templates/confirm_delete.html`, `templates/403.html`
- Test: `tests/test_ui_move.py`, `tests/test_delete_and_remove.py`

- [ ] **Step 1: Failing tests:** both in `CONVERTED_TEMPLATES`;
  `test_confirm_delete_page`: `member_client(camp, role=Role.ADMIN)` GET `camp_delete`
  → one `<h1`, `page-rule`, `btn btn-danger` with `bi-trash`, the cancel link's
  `href` the camp list; a blocked delete (whatever `test_delete_and_remove.py` already
  uses) → `alert-warning`, no ⚠️.
- [ ] **Step 2:** Run: FAIL.
- [ ] **Step 3:** Rewrite per the design's "Shared pages"; targets unchanged
  (`cancel_url`, `javascript:history.back()`).
- [ ] **Step 4:** Run `tests/test_delete_and_remove.py tests/test_ui_move.py`: PASS.

### Task 7: Dutch, static and browser review (Claude, opencode reviewer, ui-reviewer)

- [ ] **Step 1:** makemessages and msgfmt in Docker; translate new strings ("Help
  pages", "All news", …); `msgcat` to keep the wrapping; no fuzzy.
- [ ] **Step 2:** opencode `reviewer` on the changed templates, two or three per run;
  my own read of anything it flags.
- [ ] **Step 3:** Throwaway server with `seed_demo`. `ui-reviewer` at 1366px and 375px
  (375px fallback: srcdoc iframe, given up front): logged out (home, news, a post,
  each help page, login with a wrong password, request access, password reset), as
  `member` (account, Chiro page, 403 by opening another Chiro's camp), as `admin`
  (Chiro page with an open invitation, Review Focus 2; change a role; delete a camp's
  confirmation page). Create a news post and an invitation first through the shell.
- [ ] **Step 4:** Fix, restart the `--noreload` server, re-check; at most three rounds.

### Task 8: Finish area 5 (Claude)

- [ ] **Step 1:** Help pages only if a screen works differently (none expected).
- [ ] **Step 2:** All checks; whole-area review (Opus); `secret_reviewer` plus my own
  scan.
- [ ] **Step 3:** Fold the design into `docs/spec/accounts.md` (what the pages now look
  like, briefly), mark it "Built; folded into …"; `docs/TODO.md`: tick area 5 with
  this plan's path. Commit on `ui/area-5-accounts`:

```bash
git commit -m "Move the account and public pages to Bootstrap (UI move, area 5)"
```

- [ ] **Step 4:** Push from Windows, PR into `dev` with `gh`, wait for checks.
