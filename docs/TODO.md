# Roadmap

The steps in order; each builds on the ones before it. Status is one of: to
brainstorm, designed, planned, building, done. A step that changes the app gets a
design and a plan in `docs/superpowers/` before it's built (see `.claude/CLAUDE.md`);
manual steps keep a checklist here. What exists today is in `docs/SPEC.md` and
`docs/spec/`; what was done is in the git history. Last reviewed 2026-11-16.

### 1. Clean up the data: to do (manual)

Do this before the production copy (step 2). A corrected price is added to the
history; a wrong old one stays until you delete it on the ingredient's page in the
admin.

- [ ] Correct the prices that matched the wrong product:
  - Wraps: EUR 16.25 each, from a kebab meal kit (EUR 650 of the Klein Kamp budget)
  - Champignons: EUR 13.98/kg, from chicken schnitzels
  - Mais: EUR 21.19/kg, from a tuna salad
  - Vleesbouillon: EUR 20.80/liter, from a small OXO bottle
- [ ] BBQ-vlees (pak): recipes use pieces, but it's priced per kg (EUR 11.24), so it's
      left out of the budget. Change the unit to piece in the admin, with a price per pack
- [ ] Add the missing prices (8 ingredients in Klein Kamp, 14 in Kamp 2025)
- [ ] Review the other stored prices: they likely date from a March 2026 product dump
- [ ] Keep or clean `product_details`, which still describes the old automatic matches
- [ ] Run `migrate`, rename the placeholder Chiro `Mijn Chiro`, and move camps and users
      to the right Chiros
- [ ] Split the "nog te verdelen" headcount rows of Klein Kamp and Kamp 2025 into their
      afdelingen on the camp form (2025: 71 people, 2026: 58)
- [ ] Set an author on the existing recipes that should have one; recipes without an
      author can only be changed by staff

### 2. First deploy on the LAN: to do (manual)

- [ ] Check that the repo secret `REGISTRY_TOKEN` is set on keepeeassistant in Gitea
- [x] Merge `dev` into `main`: this runs the first build and deploy (PR #3, 2026-11-16)
- [ ] Check that the stack's healthcheck accepts `/` redirecting to the login page
- [ ] Copy the cleaned local database into the `keepeeassistant_data` volume. The
      production volume doesn't exist yet, so the data is only in the local `db.sqlite3`.
      Stop the dev server first, so nothing is left in `db.sqlite3-wal`, and copy `media/`
      too if it has bills. The container runs as uid 1000, so make the files its own:
      `docker run --rm -v keepeeassistant_data:/data alpine chown -R 1000 /data`
- [ ] Set `DJANGO_CLIENT_IP_HEADER=HTTP_X_FORWARDED_FOR` and stop publishing the app's
      port directly, so login limits apply per visitor behind Caddy
- [ ] Add the Caddy site `meals.dk-1.home.zx` -> `keepeeassistant:8000`
- [ ] Create or check the admin account:
      `docker exec -it keepeeassistant python manage.py createsuperuser`

### 3. UI move: in progress

Every page on Bootstrap and HTMX, core areas first, one plan and one review round per
area. Planning screens are designed for a PC (D19). After each area passes review it's
committed on its own branch and merged into `dev` by PR, and the next starts; issues
from testing go on Gitea.

- Design: `docs/superpowers/specs/2026-11-16-ui-move-design.md`
- [x] 1. Camps and planner (also: the camp list's empty-state icon and long dates, the
  theme check at phone width). Plan: `docs/superpowers/plans/2026-11-16-ui-area-1-camps-planner.md`
- [x] 2. Recipes and ingredients (also: the recipe search box focus ring). Plan:
  `docs/superpowers/plans/2026-11-17-ui-area-2-recipes.md`
- [ ] 3. Shopping, budget and stock
- [ ] 4. Bills and the financial report
- [ ] 5. Accounts and public pages (also: the home page skips from `h1` to `h3`)
- [ ] 6. Print check and `app.css` clean-up (also: `docs/DESIGN.md` §8 clean-up)

Found in area 1's review, for a later round: example camps show edit controls that
can't save (runbook note forms, slot links, no `read-only` badge next to the title);
the view should pass a flag and the pages hide them. The runbook shows very small
scaled amounts as "0,0 kg" (rounding, not UI).

Found in area 2's review: Bootstrap's danger red (`btn-outline-danger`) on the sand page
background is 4,3:1, under AA, on every page with a delete button; unchecked checkbox
borders are too faint on sand (under 3:1). Both are theme decisions for `app.css` and
`DESIGN.md` §3.4. The new-ingredient dialog is taller than a laptop screen and scrolls
inside; the live search's Clear button only follows a submitted search.

### 4. Going public: to brainstorm

Needed before the first camp that uses kitchen mode: phones at camp are on mobile
data, not the LAN.

- Add the Cloudflare tunnel, set `DJANGO_SECURE_COOKIES=1`, `DJANGO_BEHIND_TLS_PROXY=1`,
  `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`, set the `EMAIL_*` values,
  and check login and upload through the tunnel.
- Decide on Cloudflare Access login (log in once, by email): built on the
  `cloudflare-access` branch, not merged.

### 5. Kitchen mode: planned

Day view with a shared ingredient check, extra shopping list, cooking view with
timers, evaluation notes, menu evaluation after the camp, day sheet PDF, pantry
count. Needs step 3; going public (step 4) before it's used at a camp.
Starts once the user is satisfied with stages 1 and 3. Needs to work; polish comes
later.

- Design: `docs/superpowers/specs/2026-11-16-kitchen-mode-design.md`
- Plan: `docs/superpowers/plans/2026-11-16-kitchen-mode.md`

### 6. Deposits (waarborg, leeggoed): to brainstorm

Beer crates, Colruyt boxes and the like: what was paid as deposit and what came back.
Bills already mark these lines as "other".

### 7. Splitting personal costs: to brainstorm

A Splitwise-like page: who paid which bill, who owes whom for the personal lines, and
settling up. The bill lines need a person (or several) first; the financial report
already lists them apart.

## Needs you or something outside this project

- [ ] Mark ingredients with what they contain, for the diet and balance checks
- [ ] Fetch up-to-date ingredient prices automatically: needs a reliable source first
- [ ] Install an Ollama vision model; none is installed yet, so photos can't be read
- [ ] Send real bills of other shops, so the reader can be tuned to their layout
      (Collect&Go and Van Zon invoices are done)

## Later

- Email verification when someone changes their address.
