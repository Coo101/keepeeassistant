# Accounts

## Purpose

Who can use the app and see what: Chiros, members and roles, invitations and join
requests, login, the public site and the example camp. Not tied to a camp stage.
The short rules every area follows are in [SPEC](../SPEC.md); this file has the
details.

## Data

- **Chiro**: `name` (unique), `is_example` (see Example camp). Created in the admin,
  or by approving a join request.
- **Membership**: `user`, `chiro` (unique together), `role` (member / admin). A user
  can belong to several Chiros. A Chiro keeps at least one admin.
- **Invitation**: `chiro`, `email`, `role`, `token`, `invited_by`, `created_at`,
  `accepted_at`. Valid for 14 days, used once.
- **JoinRequest**: `name`, `email`, `chiro_name`, `message`, `status`
  (open / approved / rejected), `created_at`.
- **RateLimitHit**: `key` (hashed), `at`. Failed logins and reset mails (limits: see
  [operations](operations.md)).
- **Post**: `title`, `slug`, `body` (Markdown), `is_published`, `published_at`.
  News, written in the admin.
- Help pages are files in `pages/content/<slug>.md`, with `<slug>.nl.md` in Dutch.

## Behaviour

### Access

- Every page needs a login (Django's `LoginRequiredMiddleware`), except the home
  page, news, help pages, joining, and the login, password reset and invitation
  pages. New pages are private by default; mark public ones with
  `login_not_required`.
- Accounts are by invitation. Log in with a username or email address. Changing your
  address needs your password; addresses aren't verified by mail yet.
- **Camps:** only members of the camp's Chiro can see and change them; others get a
  404. Staff get no exception outside the admin. Members create and edit their
  Chiro's camps; only its admins delete them. A camp can't move to another Chiro
  outside the admin.
- Who can change recipes and ingredients: see [recipes](recipes.md).
- Deleting always asks for confirmation first.
- Example Chiros: every account can look, only staff can change.

### Public site and accounts

- Public home page, news posts (Markdown, written in the admin) and help pages
  (Markdown files in `pages/content/`). No CMS.
- Account page: your details, your Chiros, changing your password. Password resets
  by email; mail only prints to the log until `EMAIL_HOST` is set.
- The public pages (home, news, help, login, request access, invitations, password
  pages) work as well on a phone as on a PC (D19); the account and Chiro pages are
  planning views, designed for a PC. Help pages take their title from the file's
  first `# ` line and list the other help pages beside the text (above it on a
  phone). An open invitation's link wraps on a phone.

### Chiros, roles, invitations and join requests

- A Chiro's page lists its members. Its admins invite by email, remove members and
  change roles; a Chiro keeps at least one admin. Staff can also invite from the
  admin. The one-time link works for 14 days.
- Anyone can request access on the public site (`/join/`). Staff approve in the
  admin: that creates the Chiro if needed, with the requester as its admin, and sends
  the invitation.
- Camps can be archived and brought back. Archived camps stay available, are listed
  apart and don't lock recipes.

### Example camp

- `manage.py create_example_camp` makes an example Chiro with one camp, planned with
  the recipes in the database. Dates, headcount, contacts, stock, shopping days and
  bills are made up; `--reset` starts over.
- Every account sees it under its own heading on the camp list, with all pages and
  PDFs. Only staff can change it, and it has no members to show.
- It stays out of everyone's way: its prices are never another camp's estimate, it
  doesn't lock the recipes it plans, its bills teach no matches, and deleting it
  takes its prices along.

## Acceptance

None yet.

## Decisions

- **D10**: **Accounts by invitation only**; Chiros are created by staff or by
  approving a join request.

## Planned

- **Email verification** when someone changes their address.
- Cloudflare Access login: see [operations](operations.md).
