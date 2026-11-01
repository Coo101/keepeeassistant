# TODO

In the order to tackle them. From the project review of 2026-11-01.

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

## 0. Make it workable for normal users (SPEC §9.9)

- [ ] Rename the placeholder Chiro `Mijn Chiro` in the admin and move camps and
      users to the right Chiros
- [ ] Screens for camps (create, edit), so users don't need the admin
- [ ] A way to add ingredients without the admin; recipes can only pick existing ones
- [ ] Delete a recipe (blocked while a camp plans it)
- [ ] Decide how to protect camps from changes to a shared recipe: the edit page
      warns, but a changed recipe still changes other Chiros' shopping lists
- [ ] Home page with posts, a getting started page and docs; move the camp list off `/`
- [ ] Mail backend, then "Mijn account": email login, password reset, invitations,
      list of your Chiros

## 1. First production deploy

- [ ] Check that the repo secret `REGISTRY_TOKEN` is set on keepeeassistant in Gitea
- [ ] Merge `dev` into `main`: this runs the first build and deploy
- [ ] Copy the local database into the `keepeeassistant_data` volume, or start empty.
      The production volume doesn't exist yet, so the stored prices and camps are
      only in the local `db.sqlite3` until this is done
- [ ] Add the Caddy site `meals.dk-1.home.zx` -> `keepeeassistant:8000`
- [ ] Create the admin account: `docker exec -it keepeeassistant python manage.py createsuperuser`

## 2. Set prices by hand

All prices now have to be maintained manually. The stored ones came from the old
import, so don't trust the budget totals until these are done.

- [ ] Correct the prices that matched the wrong product:
  - Wraps: EUR 16.25 each, from a kebab meal kit (EUR 650 of the Klein Kamp budget)
  - Champignons: EUR 13.98/kg, from chicken schnitzels
  - Mais: EUR 21.19/kg, from a tuna salad
  - Vleesbouillon: EUR 20.80/liter, from a small OXO bottle
- [ ] BBQ-vlees (pak): recipes use pieces, but it's priced per kg (EUR 11.24), so it's
      left out of the budget. Set the ingredient to piece, with a price per pack
- [ ] Add the missing prices (8 ingredients in Klein Kamp, 14 in Kamp 2025)
- [ ] Review the other stored prices: they likely date from a March 2026 product dump
- [ ] Make the admin set `price_updated` when a price is edited; nothing updates it now
- [ ] Decide whether to keep or clean `product_details`, which still describes the
      old automatic matches

## 3. Bugs

- [ ] Posting a menu slot for a date outside the camp returns a 500
      (`planning/views.py`, `entry.full_clean()`)
- [ ] Small quantities can round to `0` on shopping lists (below 0.05 kg/liter or
      0.5 piece); consider showing or rounding them up
- [ ] Check the PDF filename with special characters in a camp or recipe name
      (`core/pdf.py`); not verified with native PDF output

## 4. Tests and tooling

- [ ] Test native PDF output: the PDF tests also accept the HTML fallback
- [ ] Tests fail with `DJANGO_DEBUG=0` (missing static manifest); make them independent
      of the local `.env`
- [ ] Keep dependencies in one place (`requirements.txt` and `pyproject.toml` differ)
      and pin exact versions

## 5. Hardening

- [ ] Run the container as a non-root user
- [ ] Rate-limit login attempts
- [ ] Production is plain HTTP on the LAN, so logins and sessions aren't encrypted.
      Going public through a Cloudflare tunnel handles TLS, but Django still needs
      `DJANGO_SECURE_COOKIES=1`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
      and `SECURE_PROXY_SSL_HEADER` (not in settings yet)
- [ ] Before going public, decide whether SQLite is still enough
- [ ] Set `TIME_ZONE` to `Europe/Brussels` (currently UTC)

## Future features

- [ ] Fetch up-to-date ingredient prices automatically, from a reliable source
- [ ] The other ideas in `docs/SPEC.md` §13
