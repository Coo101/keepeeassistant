# TODO

In the order to tackle them; each step builds on the ones before it. Last reviewed
against the code on 2026-11-01.

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
- [ ] Set an author on the existing recipes that should have one; recipes without an
      author can only be changed by staff

## 3. First deploy on the LAN

- [ ] Check that the repo secret `REGISTRY_TOKEN` is set on keepeeassistant in Gitea
- [ ] Merge `dev` into `main`: this runs the first build and deploy
- [ ] Check that the stack's healthcheck accepts `/` redirecting to the login page
- [ ] Copy the cleaned local database into the `keepeeassistant_data` volume. The
      production volume doesn't exist yet, so the data is only in the local `db.sqlite3`
- [ ] Add the Caddy site `meals.dk-1.home.zx` -> `keepeeassistant:8000`
- [ ] Create or check the admin account:
      `docker exec -it keepeeassistant python manage.py createsuperuser`

## 7. Before inviting other Chiros

- [ ] Protect camps from changes to a shared recipe: the edit page warns, but a changed
      recipe still changes other Chiros' shopping lists. A recipe that another Chiro has
      planned also can't be deleted by its author
- [ ] Decide who may change a shared ingredient's category, shop and product details;
      today it's anyone with an account
- [ ] Mail backend, then "Mijn account": email login, password reset, invitations and a
      list of your Chiros
- [ ] Home page with posts, a getting started page and docs; move the camp list off `/`

## 8. Going public through the Cloudflare tunnel

- [ ] Rate-limit login attempts
- [ ] Run the container as a non-root user
- [ ] Set `DJANGO_SECURE_COOKIES=1`, `DJANGO_ALLOWED_HOSTS` and
      `DJANGO_CSRF_TRUSTED_ORIGINS`, and add `SECURE_PROXY_SSL_HEADER` to the settings.
      Until then production is plain HTTP on the LAN, so logins aren't encrypted
- [ ] Decide whether SQLite is still enough
- [ ] Add the Cloudflare tunnel and check the whole login and upload flow through it

## 9. Remaining features from the spec (§13)

- [ ] Roles within a Chiro: who may invite members and delete camps
- [ ] Dietary restrictions and allergies: per camp headcounts and per recipe flags,
      with warnings in the planner
- [ ] Nutrition and balance: tags per ingredient, rolled up per meal and day, with
      simple warnings in the planner
- [ ] Pantry on hand: subtract what a camp already has from its shopping lists
- [ ] Archive camps instead of deleting them for good
- [ ] Requests to join: sign-up that staff approve, and a request for a new Chiro

## Needs you or something outside this project

- [ ] Fetch up-to-date ingredient prices automatically: needs a reliable source first
- [ ] Install an Ollama vision model; none is installed yet, so photos can't be read
- [ ] Send real bills, so the reader can be tuned to their layout

## Done on `dev`

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
- [x] README and spec updated
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
