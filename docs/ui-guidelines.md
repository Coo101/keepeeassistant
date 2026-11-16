# UI guidelines – Camp Meal Planner

Reference for every frontend change: how screens behave. How they look (colours, type, brand) is in `docs/DESIGN.md`. The Claude agents `ui-builder` and `ui-reviewer` and opencode's `builder`, `reviewer` and `planner` follow both files. If something here conflicts with a request, ask before deviating.

## Users and context

- **Phone in the kitchen** – cooks reading recipe steps, running timers, checking quantities, ticking off the ingredients a meal needs ("Heb je alles?"). Wet or busy hands, glancing at the screen from a distance, often bad light.
- **Laptop for planning** – the kookploeg lead setting up camps, choosing menus, generating shopping lists, checking bills. Lots of data, tables and forms. Shopping lists belong here, with the planner, not in the kitchen screens.
- **Visitors** – the public pages (home, news, help pages, login, request access) on any device. Read-only, short, and the first impression of the app.

Design rule of thumb: **kitchen screens optimise for reading and tapping, planning screens optimise for overview and data entry.**

What each screen does is in the area files in `docs/spec/` (kitchen mode: `docs/spec/kitchen.md`). Printed output (runbook, shopping lists, report) is rendered by WeasyPrint with its own CSS and is out of scope unless a task says otherwise; its look follows `docs/DESIGN.md` §7.

## Stack

- Django 5.x templates – no SPA, no React/Vue, no build step.
- **Bootstrap 5.3** served from `static/vendor/bootstrap/` (no CDN – camp sites may have poor connectivity).
- **Bootstrap Icons** from `static/vendor/bootstrap-icons/`.
- **HTMX** from `static/vendor/htmx/` with `django-htmx` middleware.
- Forms rendered with `django-crispy-forms` + `crispy-bootstrap5`.
- Custom CSS only in `static/css/app.css`. Keep it small; prefer Bootstrap utilities. No inline `style=""`.
- Plain JavaScript only where HTMX can't do the job (timers, a dialog), as files in `static/js/`. No inline scripts, no npm packages.
- Link our own CSS and JS with `{% load assets %}{% asset 'css/app.css' %}`, not `{% static %}`: in debug it adds the file's modification time, so browsers never keep an old copy (production hashes the file names).

## Template structure

```
templates/
  base.html               # layout, navbar, messages, scripts
  components/             # reusable includes (empty state, messages, page header)
  partials/               # fragments shared between apps, named _thing.html
  <app>/<page>.html       # full pages extend base.html
  <app>/_thing.html       # fragments used by one app
```

- Every page extends `base.html` and fills `{% block title %}` and `{% block content %}`.
- The title names the page, then the camp or the app: `{{ camp.name }} — {% translate "Bills" %}` or `{% translate "Camps" %} — {% translate "Camp Meal Planner" %}`.
- The app's name is always translated, never typed as plain text: **Camp Meal Planner** in English, **Kamp Maaltijd Planner** in Dutch.
- Every full page starts with the page header: one `h1`, optional meta line, the red rule (`docs/DESIGN.md` §5.2).
- Anything returned by an HTMX request is a fragment (`partials/` or `<app>/_thing.html`) and never extends `base.html`.
- Reuse `components/` before writing new markup. If the same markup appears twice, make it a component.

## Look and feel – clean and practical

Follow `docs/DESIGN.md` and its review checklist. In short:

- Bootstrap themed with the Chiro movement colours, light mode only (`data-bs-theme="light"`).
- One accent: Bootstrap `primary`, which is **Chiro navy**. `success` / `warning` / `danger` only for their meaning (done, attention, destructive/error).
- **Chiro red** is the brand colour: the navbar and the red rule under each page title. Never on buttons, links, badges or text.
- No gradients, no decorative images, no Chiro logo.
- Icons accompany text labels; icon-only buttons need `aria-label` and a tooltip.
- Spacing with Bootstrap utilities (`gap-*`, `mb-3`, `p-3`); don't invent margins in CSS.

## Layout and breakpoints

- Mobile first. Design at **375px** wide, then enhance for **≥992px (lg)**.
- No horizontal scroll on the page itself at 375px. A wide table may scroll inside its own box.
- The navbar collapses below `lg`.
- **Kitchen views** (today's menu, ingredient check per meal, recipe steps):
  - Linked from the camp list and the planner; inside kitchen mode, Today, the ingredient check and the cooking view are one tap apart.
  - Base font at least 1.125rem; quantities and step text larger (`fs-4` or more).
  - One recipe step at a time on mobile, with big Previous / Next buttons.
  - Tap targets at least 44×44px; checkboxes enlarged (scale `form-check-input` up in `app.css`).
  - Timers clearly visible, with start/pause/reset buttons and an audible + visual alert.
- **Planning views** (camps, planner, recipes, shopping, budget, bills):
  - Tables in `table-responsive`: on a phone they scroll sideways inside their box. Only tables people really use on a phone get a card layout below `lg`.
  - Forms in a single column on mobile, two columns from `lg`.
  - The page's main action sits next to the title from `lg`, under it on phones. A form's submit button sits bottom-right; destructive actions are set apart, in `btn-outline-danger`.

## Permissions in the UI

- Hide actions the user can't take (edit, delete, invite, change roles) rather than showing them disabled. The view decides and passes flags such as `can_edit`, `can_delete`, `is_admin`; templates never work out permissions themselves.
- A page someone can see but not change says so once, with a `read-only` badge next to the title (shared recipes they didn't write, example camps).
- Hiding a button is not the protection: the view refuses the request too. That part is outside UI tasks.

## HTMX patterns

- CSRF: `<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>` in `base.html`.
- Use HTMX for: ticking off items, changing headcount/portions with live rescale, inline add/remove rows, filtering lists.
- Always set `hx-target` and `hx-swap` explicitly. Show feedback with `hx-indicator` (a small spinner).
- Every HTMX action must also work as a normal form POST/link without JavaScript (progressive enhancement). Views check `request.htmx` to choose fragment vs full page.
- After a successful change, show a Bootstrap toast or update the element in place – never a full reload for small actions.

## Language and i18n

- Dutch (nl-BE) and English, with an NL/EN switch in the header. The browser's language decides until someone picks one; Dutch is the default.
- Write the text in English and mark it: `{% translate %}` / `{% blocktranslate %}` with `{% load i18n %}` in templates, `gettext_lazy as _` in Python. The Dutch goes in `locale/nl/LC_MESSAGES/django.po`; recompile the committed `django.mo` (README).
- No unmarked text in templates: in Dutch, every label, button and message must show in Dutch. Code, comments and variable names stay in English.
- Data people entered (ingredient names, bill lines, notes) shows as it was written, untranslated.
- Numbers and dates via Django localisation: decimal comma on screen (`2,5 kg`), dates as `ma 14 jul`. Form fields and URLs keep a decimal point. Quantities show 1 decimal max, units as `stuk`, `kg`, `liter`.
- Tone: short, informal, `je`-form. Buttons are verbs: "Opslaan", "Menu kiezen", "Boodschappenlijst maken".
- Help pages are Markdown in `pages/content/<slug>.md` and `<slug>.nl.md`. When a screen changes how something works, update both.

## Feedback and states

- Every list has an empty state (`components/empty_state.html`: icon + one sentence + the action to add the first item).
- Form errors show inline under the field (crispy handles this) plus a summary alert at the top.
- Destructive actions need confirmation: the shared confirmation page (`templates/confirm_delete.html`), a modal, or `hx-confirm` for small inline removals.
- Uncovered days on the shopping planner are visibly flagged with a `warning` badge and explanation.
- Status is never shown by colour alone: add an icon or a word.

## Accessibility baseline

- Every input has a `<label>`; placeholders are never the only label.
- Text contrast meets WCAG AA. Use only the colour pairs `docs/DESIGN.md` §3.4 allows; don't lighten text colours.
- Headings in order (one `h1` per page). Landmarks: `nav`, `main`.
- Focus visible on all interactive elements; everything reachable by keyboard.

## Out of scope for UI tasks

- Models, migrations, business logic (scaling, shopping-day coverage) and permission checks in views – UI tasks don't change these. If a UI change needs new data or a new flag, stop and report what's needed.
