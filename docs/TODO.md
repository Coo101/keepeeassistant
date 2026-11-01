# TODO

In the order to tackle them; each step builds on the ones before it. Last reviewed
against the code on 2026-11-01.

## 1. Finish and stabilise the current work

- [x] Check the new screens in a browser, including the ingredient dialog on the recipe form
- [ ] The top of the recipe form looks rough next to the camp form: labels sit beside
      the fields and the notes box is out of line. Use the same stacked layout

## 2. Clean up the data

Do this before the production copy (step 3) and the price history (step 4), so wrong
prices don't end up in either.

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

## 4. Prices per camp

The building block for financing: bills add prices to a camp and leave other camps alone.

- [ ] Price history model: ingredient, price, date, camp (optional), and later the bill
      line it came from. Existing prices move over as starting prices without a camp
- [ ] Latest price of an ingredient: the most recent one, across all camps and Chiros
- [ ] Budget: use the camp's own price for an ingredient, otherwise the latest price, and
      show which of the two was used
- [ ] Ingredients page: show the latest price and its date plus the price history;
      entering a price adds to the history instead of overwriting it
- [ ] Remove `Ingredient.price_per_unit` and `price_updated`, or derive them from the
      history, and update the admin, budget and forms
- [ ] Update `docs/SPEC.md` §6 and §9.6

## 5. Financing: bills and actual costs

Upload a camp's bills, read them, record the prices on that camp and compare actual cost
with the budget.

- [ ] Test on real bills first: Collect&Go PDFs, other PDFs and photos, including a bad
      one. Which Ollama vision model reads them well enough?
- [ ] Bill model and upload per camp, visible only to that camp's Chiro. Limit file type
      and size, store files on the data volume, never under `static/`, and serve them
      only through a view that checks access
- [ ] Privacy warning on the upload form: bills can include names, addresses and loyalty
      card numbers; say where they're stored and who can see them. Decide how long to
      keep them and include them in deleting a camp
- [ ] Read text PDFs in plain Python (`pdfplumber`); send scans and photos to Ollama
- [ ] Ollama runs on a PC that isn't always on: make the URL and model settings, keep a
      bill waiting with a clear status until it can be read, and retry. There's no
      background worker yet, so choose how this runs. Check the server can reach the PC
- [ ] Review screen: match each line to an ingredient, convert pack size to the price
      per kg, liter or piece, skip deposits and discounts, and let a person confirm.
      Nothing changes a price without that
- [ ] Remember confirmed matches per shop, so the next bill needs less checking
- [ ] Show total paid per camp and per shop, next to the budget

## 6. Purchase categories

- [ ] Split bill lines into camp food, activities (pizza evening, marshmallows at the
      campfire) and personal items, so only camp food counts towards the meal budget
      and only camp food updates ingredient prices

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

## Future features

- [ ] Archive camps instead of deleting them for good
- [ ] Fetch up-to-date ingredient prices automatically, from a reliable source
- [ ] The other ideas in `docs/SPEC.md` §13

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
