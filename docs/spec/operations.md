# Operations

## Purpose

How the app is run, deployed, secured and backed up. Not tied to a camp stage.

## Data

- The SQLite database and uploaded bills live on one volume (`/data`, set by
  `DJANGO_DATA_DIR`).
- **RateLimitHit** (failed logins and reset mails) is described in
  [accounts](accounts.md).

## Behaviour

### Branches and releases

- Each roadmap step or feature is built on its own branch from `dev`
  (`<kind>/<short-name>`, such as `ui/area-2-recipes`), pushed to Gitea, and merged
  into `dev` through a pull request after the checks and reviews pass.
- `dev` is the integration branch, run locally from PyCharm (port 8100).
- `main` only changes through a pull request from `dev`; merging it is a production
  release (CI deploys it).

### CI/CD

- Gitea Actions (`.gitea/workflows/ci-cd.yml`). Every push and PR runs ruff, black,
  Django checks and pytest. A push to `main` also builds the image, pushes it to the
  Gitea registry and deploys it to the homelab Docker host, checking that the image
  renders a PDF.

### Containers

- `docker-compose.yml`: `web` (gunicorn) and `bill-reader` (`read_bills --loop`),
  sharing the data volume. Migrations run at start.
- The container runs as a non-root user (uid 1000).

### Data and backups

- Back up the data volume with `sqlite3 .backup`, or with the app stopped. The volume
  also holds the bills.

### Network

- First on the LAN behind Caddy (`meals.dk-1.home.zx`).
- Going public means a Cloudflare tunnel, the HTTPS settings below, and mail
  (`EMAIL_*`). Kitchen mode needs this before the first camp that uses it.

### Security

- Without a real `DJANGO_SECRET_KEY` (`change-me` doesn't count) the app refuses to
  start unless `DJANGO_DEBUG=1`. Debug is off unless enabled.
- Failed logins are limited per account (10) and per address (50), reset mails per
  email (3) and per address (10), within 15 minutes. Behind a proxy the address comes
  from `DJANGO_CLIENT_IP_HEADER`.
- `seed_demo` (login `admin` / `admin`) only runs with `DJANGO_DEBUG=1`.
- Cookie and proxy settings for HTTPS: `DJANGO_SECURE_COOKIES`,
  `DJANGO_BEHIND_TLS_PROXY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`.

### Commands

- `migrate`, `createsuperuser`, `seed_demo` (dev only), `import_kamp_recipes` (the
  recipe library), `create_example_camp`, `read_bills`.

### Settings

- All settings are listed in `.env.example`.

## Acceptance

None yet.

## Decisions

- SQLite and WAL mode: D9 in [SPEC](../SPEC.md).

## Planned

- Going public: see the roadmap in `docs/TODO.md`.
- Cloudflare Access login (log in once through Cloudflare Access, by email): built on
  the `cloudflare-access` branch, not merged. See the roadmap.
