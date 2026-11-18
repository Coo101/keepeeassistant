# UI move, area 5: accounts and public pages. Design

Date: 2026-11-18. Roadmap step 3, area 5. **Built; folded into `docs/spec/accounts.md`.** Builds on
`docs/superpowers/specs/2026-11-16-ui-move-design.md`, whose rules all apply. Area
file: `docs/spec/accounts.md`. Branch `ui/area-5-accounts` from `origin/dev`.

## Intent

Move the last pages still on the old hand-written classes to Bootstrap and the shared
components: the account and Chiro pages, the invitation and request-access pages,
login and the password pages, the public pages (home, news, help) and the two shared
pages (`confirm_delete.html`, `403.html`). After this area only the print templates
keep their own CSS, and area 6 can strip the old rules from `app.css`.

## Goals

- Every template below passes the UI move's "Done per area": page header, Bootstrap
  buttons and form controls, crispy forms, empty states with an icon, one `h1`,
  headings in order, short dates.
- Public pages (home, news, help, login, join, invitations, password pages) work
  equally at 375px and 1366px (D19). The account and Chiro pages are planning views:
  designed for a PC, checked at 375px.
- The home page no longer skips from `h1` to `h3`.

## Non-goals

- Behaviour, permissions, forms' fields or validation, the invitation flow, the login
  rate limit. No new pages, no new inputs.
- The help and news texts themselves.
- `registration/password_reset_email.html` (a plain-text mail) and the print templates.
- The parked behaviour fixes from areas 1–4 (example controls, save confirmations,
  Enter in row tables): their own step later.

## Anti-goals

- A login or join page that's harder to use on a phone than today.
- The request-access honeypot field (`website`, a `HiddenInput`) becoming visible.
- Invitation links that overflow the page on a phone.

## Approaches

The UI move design settles the approach (area by area onto Bootstrap and the shared
components, picked by the user). Nothing else was open; the per-page layout below is
Claude's call within `DESIGN.md`.

## Design (Claude's calls)

Shared for all forms here: a narrow column (`col-md-8 col-lg-6`, login `col-md-6
col-lg-4`), fields through crispy filters (`{{ form|crispy }}` or
`{{ field|as_crispy_field }}`), `components/form_errors.html` above the form, submit as
`btn btn-primary`. Hidden fields stay hidden. Secondary text `text-body-secondary`;
warnings `alert alert-warning` with a `bi-exclamation-triangle` icon, no emoji.

### Account (`accounts/account.html`)

- Page header "Your account", meta "Logged in as **name**".
- "Your Chiros": a `list-group` of links to each Chiro page; empty state (icon
  `people`) with the existing "You aren't linked to a Chiro yet…" text.
- "Your details": the no-email warning alert, then the crispy form, "Save details".
- "Password": "Change password" (`btn-outline-primary`, `bi-key`).

### Chiro page (`accounts/chiro_detail.html`)

- Back link "Your account" (`components/back_link.html`); page header with the Chiro's
  name, action "Stock: kitchen utilities and food" (outline, `bi-box-seam`).
- "Members": `table table-sm` inside `table-responsive`. For admins each row's role
  cell holds the existing form: `form-select form-select-sm` (keeps its `aria-label`),
  "Save" `btn-sm btn-outline-primary`, "Remove" `btn-sm btn-outline-danger`
  (`bi-person-dash`). Same names and values as today.
- Admins: "Invite someone" with the crispy form, "Send invitation"; "Open invitations"
  as a `list-group`, each item the address, the link in `<code class="text-break">`
  (wraps on a phone) and "Cancel" (`btn-sm btn-outline-secondary`).
- Stacked on a PC too: the members table needs the width.

### Invitations, request access, thanks

- `invitation_join`, `invitation_login`, `invitation_signup`, `invitation_closed`,
  `invitation_wrong_account`, `join_request`, `join_thanks`: page header with the
  existing title (and the existing intro as `meta` where there is one), text as
  paragraphs, forms per the shared rule. "Join …" and "Create account" `btn-primary`.

### Login and passwords (`registration/`)

- `login.html`: page header "Log in" with the existing meta; a `card` in the login
  column with the error as `alert alert-danger`, the two fields as Bootstrap fields
  (label "Username or email" stays, `autocomplete` kept), "Log in" `btn-primary
  w-100`, then "Forgot your password?". The rate-limit error still shows.
- The four form pages (change, reset form, reset confirm) and three "done" pages: page
  header, crispy, primary submit; the invalid-link text stays.

### Public pages (`pages/`)

- `home.html`: the hero (Bootstrap utilities, no `.hero` class) keeps its `h1`, gets
  the red rule under it (the existing `.page-rule`), the lead text
  (`lead`), "Go to your camps"/"Log in" `btn-primary` and "How it works"
  `btn-outline-primary`, the request-access line as secondary text. The four features
  in a `row row-cols-1 row-cols-md-2 row-cols-lg-4 g-3` of cards whose titles are `h2`
  with class `h5` (fixes the `h1`→`h3` skip). News: `h2` "News", then cards with the
  title as `h3` and the date `short_date:"year"`.
- `post_list.html`: page header "News"; each post a card (title link, date
  `short_date:"year"`); empty state (icon `newspaper`) "No news yet."
- `post_detail.html`: back link "All news"; page header with the title and the date as
  meta; the body in `.prose`.
- `doc.html`: page header with the document's title; the contents list as a
  `list-group` in a side column from `lg` (`col-lg-3`, the current page `active` with
  `aria-current`), the body in `col-lg-9`; on a phone the list sits above the body.
  The markdown files start with `# Title`; the `doc` view takes that first line as
  the page title (falling back to the `DOCS` label) and renders the rest, so there's
  one `h1`. No content file changes: all ten files (EN and NL) start with `# Title`
  today (checked); a file without one keeps the `DOCS` label and its full body.

### Shared pages

- `confirm_delete.html`: page header "Delete …?". Blocked: `alert alert-warning` with
  the reason, "Back" outline. Otherwise a card with "This can't be undone." and the
  consequences list, then "Delete" (`btn btn-danger`, `bi-trash`: this page is the
  confirmation, so the solid red button is the final step) and "Cancel"
  (`btn-outline-secondary`).
- `403.html`: page header "Not allowed", the reason, "Back" (`btn-outline-primary`,
  `bi-arrow-left`). Both pages keep today's targets: `history.back()` on the 403
  page, the view's `cancel_url` on the delete page.

### Tests and docs

- Every template above joins `CONVERTED_TEMPLATES`; the logged-in pages (account,
  Chiro page) and public pages (home, news, a doc) get a one-`h1`/red-rule check.
- `test_home_news_and_docs_are_public` checks for an `h1` with or without attributes.
- The `doc` view's title: a test that the page has one `h1` with the file's title.
- Help pages change only where a screen works differently (none expected).

## Left to the builder

- Exact spacing, icons and card use within `DESIGN.md`.
- Whether a form uses `{{ form|crispy }}` or per-field `as_crispy_field`, as long as
  hidden fields stay hidden and labels stay as they are.
