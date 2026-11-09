# TODO

In the order to tackle them; each step builds on the ones before it. Last reviewed
against the code on 2026-11-09.

## 2. Clean up the data

Do this before the production copy (step 3). A corrected price is added to the history;
a wrong old one stays until you delete it on the ingredient's page in the admin.

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

## 3. First deploy on the LAN

- [ ] Check that the repo secret `REGISTRY_TOKEN` is set on keepeeassistant in Gitea
- [ ] Merge `dev` into `main`: this runs the first build and deploy
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

## 4. UI on Bootstrap and HTMX

Per `docs/ui-guidelines.md`, `docs/DESIGN.md` and SPEC §12. Kitchen mode (step 5) builds on
this.

- [ ] Check the Chiro theme at phone width: the browser review could only run at laptop
      width (Edge was maximised)
- [ ] Move the pages over one area at a time, shrinking `app.css` as you go: camps and
      planner, recipes and ingredients, shopping and budget, bills and report, kitchen
      stock, accounts and public pages. Per page: the page header component, Bootstrap
      `btn btn-primary` / `btn-outline-*` instead of the old `.btn`, `form-control` on
      inputs (the recipe search box has no navy focus ring yet), an icon in the empty
      state (the camp list has none). Also known: the home page skips from `h1` to `h3`,
      and the camp list shows long dates ("3 augustus 2026") instead of `ma 14 jul`
- [ ] Forms through crispy: single column on mobile, two from `lg`
- [ ] HTMX where the guidelines name it (inline add/remove rows, live rescale, filters),
      each also working as a plain link or form post
- [ ] Check the PDFs still render: print templates keep their own CSS

## 5. Kitchen mode

SPEC §9.19. Needs step 4.

- [ ] `IngredientCheck` model and migration, with tests for who can tick
- [ ] Today page per camp: the day's meals at their times, with the planned recipes
- [ ] Ingredient check per meal: scaled quantities per recipe, tick and untick through
      HTMX (a form post without JS), count of what's still unticked
- [ ] Cooking view: one step at a time, Previous/Next, timers with start/pause/reset and
      a sound and visual alert, several at once
- [ ] Links from the planner and the camp list to kitchen mode

## Next

- [ ] A Splitwise-like page to divide the personal costs: who paid which bill, who
      owes whom for the personal lines, and settling up. The bill lines need a
      person (or several) first; the financial report already lists them apart.

## Needs you or something outside this project

- [ ] Mark ingredients with what they contain, for the diet and balance checks

- [ ] Fetch up-to-date ingredient prices automatically: needs a reliable source first
- [ ] Install an Ollama vision model; none is installed yet, so photos can't be read
- [ ] Send real bills of other shops, so the reader can be tuned to their layout
      (Collect&Go and Van Zon invoices are done)
- [ ] Before going public: add the Cloudflare tunnel, set `DJANGO_SECURE_COOKIES=1`,
      `DJANGO_BEHIND_TLS_PROXY=1`, `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`, set the `EMAIL_*` values,
      and check login and upload through the tunnel

## Done on `dev`

- [x] Headcount per afdeling on the camp form; the -12, 12+ and staff totals follow it

- [x] Remove the Colruyt price import and scraper code, and the linked product IDs
      (stored prices are kept)
- [x] `?portions=NaN` no longer crashes the recipe page
- [x] `seed_demo` (login `admin/admin`) only runs with `DJANGO_DEBUG=1`
- [x] The `change-me` placeholder is no longer accepted as a secret key
- [x] Runbook contact details and general notes need a login (page and PDF)
- [x] Recipe units must match the ingredient; mismatches are reported in the
      budget instead of being costed wrongly
- [x] Warn about meals planned outside the camp dates
- [x] Saving shopping days no longer deletes trips outside the offered dates, and
      the page warns about them
- [x] Cost per portion per day counts covered days only
- [x] CI: test job starts without secrets; ruff, black and the tests run on every push
- [x] README and spec updated (spec rewritten as v2.0 on 2026-11-05)
- [x] Every page needs a login; camps are limited to the members of their Chiro
- [x] Recipes shared between Chiros: author, read-only or editable, save a copy
- [x] Recipe create and edit screens outside the admin
- [x] Logging out after the session expired no longer ends in a 405
- [x] Screens for camps (create, edit), so users don't need the admin
- [x] Screens for ingredients (list, create, edit price and shop)
- [x] Delete a camp, a recipe (blocked while a camp plans it) and an ingredient
      (blocked while a recipe uses it)
- [x] Remove a menu entry or shopping day outside the camp dates without the admin
- [x] Set `price_updated` when a price is edited, on the ingredients page and in the admin
- [x] A menu slot outside the camp dates returns a 404 instead of a 500
- [x] Small quantities no longer round to `0` on shopping lists
- [x] PDF filenames are escaped
- [x] `TIME_ZONE` is `Europe/Brussels`
- [x] Tests no longer depend on the local `.env` (`config/test_settings.py`)
- [x] Real PDF output is tested where WeasyPrint's libraries exist, and the deploy job
      checks that the image renders a PDF
- [x] Dependencies are pinned in `pyproject.toml`; the requirements files are generated
- [x] The recipe form uses the same stacked layout as the camp form
- [x] Prices per camp: price history, a camp's own price wins, otherwise the latest,
      and the budget shows which one it used
- [x] Financing: upload bills with a privacy warning, read PDFs in Python and scans
      through Ollama, review lines, set camp prices, remember matches, compare paid
      with estimated per shop
- [x] Purchase categories: camp food, activity, personal and other
- [x] A recipe another Chiro has planned can't be changed, except by staff
- [x] Decision: anyone with an account may change a shared ingredient's category, shop
      and product details. Prices no longer affect other camps' own prices
- [x] Mail backend, email login, password reset, account page and invitations
- [x] Public home page, news and docs; the camp list moved to `/camps/`
- [x] Login and reset-mail rate limits; the container runs as a non-root user
- [x] Decision: SQLite stays for now, with WAL mode for the workers and bill reader.
      Back up the data volume, which also holds the bills, with `sqlite3 .backup`
      or with the app stopped
- [x] Roles within a Chiro, and a Chiro page to invite and manage members
- [x] Diets and allergies, and balance checks in the planner
- [x] Pantry on hand comes off the shopping lists and budget
- [x] Archive camps
- [x] Requests to join, approved by staff
- [x] The site in Dutch and English, with a language switch in the header
- [x] Kitchen utilities: a stock per Chiro, needs per camp, what to buy on the shopping
      page, and a bill category that can add to the stock
- [x] Bill review fits the page with its header in view, and can add a missing
      ingredient per line
- [x] Financial report per camp: checks the bills first, cost per planned meal,
      personal costs apart
- [x] Read-only example camp for every account (`manage.py create_example_camp`)
- [x] The pantry belongs to the Chiro, on its stock page
- [x] Bootstrap 5.3, Bootstrap Icons and HTMX vendored in `static/vendor/`; `django-htmx`
      and crispy-forms with `crispy-bootstrap5` installed
- [x] `base.html` on Bootstrap: collapsing navbar, messages as alerts, the NL/EN switch,
      the HTMX CSRF header; `templates/components/` (messages, empty state) and
      `templates/partials/`
- [x] Chiro theme (`docs/DESIGN.md` §8): tokens and Bootstrap overrides in `app.css`, the
      old green tokens on navy and sand, red navbar with the egg icon and the current
      page marked, focus rings (white on the navbar), `components/page_header.html` with
      the red rule, used on the camp list
