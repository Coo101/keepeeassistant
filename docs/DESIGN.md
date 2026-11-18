# Web design: Camp Meal Planner

**Status:** v1.0, 2026-11-09. The theme is in `app.css` and `base.html`; the pages move over to it per `docs/TODO.md` step 4.

> How the app looks: colours, type, brand elements and how they map onto Bootstrap.
> `docs/ui-guidelines.md` covers how screens behave (layout, HTMX, language, states) and
> points here for the look. When the two disagree, fix one of them.

---

## 1. Idea

The app should feel like it belongs to the Chiro, without pretending to be an official
Chiro product. We get there with the movement's own colours and a few quiet references
to its house style, not with its logo.

Three rules carry the whole design:

1. **Recognisably Chiro.** Red, navy and sand, the colours of the Chiro uniform.
2. **Colour means something.** Navy is "you can act here". Red is "this is the Chiro".
   Green, yellow and danger-red keep their usual meaning (done, attention, destructive).
3. **Practical first.** Kitchen screens are read from a distance with wet hands;
   planning screens hold a lot of data. Decoration never costs readability.

## 2. Source: the Chiro house style

Chirojeugd Vlaanderen's house style guide (*onze huisstijl opgefrist, een
adviesboekje*, chiro.be, 2017) defines three movement colours, "based on the colours
of the movement clothing", and calls its rules advice, not obligations. What we take
from it:

| From the guide | In the app |
|---|---|
| The three movement colours, exact values | The palette, §3 |
| A white logo on a red field | The red navbar with white text |
| The horizontal red line ("streepje") that joins a group's name to the Chiro logo | A short red rule under every page title |
| Condensed type: Myriad Pro (Mac), Arial Narrow (PC); titles bold condensed | Condensed bold headings, §4 |
| Black-and-white printing: the red field becomes 70% black | Print rule, §7 |

What we don't take: **the Chiro logo itself.** The guide asks for no variants or
composite logos, and this app is made for Chiros, not by Chirojeugd Vlaanderen. Using
the logo would suggest an endorsement we don't have. If the movement ever adopts the
app, revisit this.

## 3. Colour

### 3.1 Movement colours

| Token | Name | Hex | RGB | CMYK | PMS |
|---|---|---|---|---|---|
| `--chiro-red` | Chiro red | `#E1143C` | 225 20 60 | 0 96 65 4 | 186 |
| `--chiro-navy` | Chiro navy | `#00124D` | 0 18 77 | 100 80 0 60 | 282 |
| `--chiro-sand` | Chiro sand | `#E4D096` | 228 208 150 | 2 10 41 13 | 467 |

### 3.2 Roles

- **Navy: the primary colour.** Bootstrap's `primary`: buttons, links, focus rings,
  checked boxes, active tabs and pills, headings' colour. It has the best contrast of
  the three (17.6:1 on white), which matters most in the kitchen.
- **Red: the brand colour.** The navbar, the brand mark and the red rule under the page
  title. **Red is never used for buttons, links, badges or body text.** Inside the
  content area, the page-title rule is the only red that isn't a warning, so any other
  red there means error or destructive.
- **Sand: warmth.** Tints of sand for the page background, table headers, card headers
  and planner chips. Full-strength sand only as a small accent (a highlighted row, a
  marker); never as a text colour.

### 3.3 Tokens

Defined once on `:root` in `app.css`; everything else uses these names.

| Token | Value | Use |
|---|---|---|
| `--chiro-red` | `#E1143C` | Navbar, brand mark, page-title rule |
| `--chiro-red-dark` | `#BF1133` | Navbar hover and active items, red on white where small text is unavoidable |
| `--chiro-navy` | `#00124D` | Primary: buttons, links, headings, focus |
| `--chiro-navy-hover` | `#263668` | Hover and pressed state of navy buttons and links |
| `--chiro-navy-soft` | `#EBECF1` | Hover background of outline buttons, selected list items |
| `--chiro-sand` | `#E4D096` | Small accents only |
| `--chiro-sand-soft` | `#F7F1E0` | Table headers, card headers, planner chips |
| `--chiro-sand-faint` | `#FBF8EF` | Page background (cards stay white on it) |
| `--bs-secondary-color` | `#5C636A` | Secondary text (`text-body-secondary`), meta lines, empty slots. Darker than Bootstrap's `#6C757D`, which falls under 4.5:1 on the sand tints |
| `--bs-danger` | `#B02A37` | Destructive buttons, errors (also set as the form-error red). Bootstrap's red-600: its default `#DC3545` is 4.3:1 on sand-faint, under AA |

Body text stays Bootstrap's `#212529`. The other status colours stay Bootstrap's
defaults: `success` `#198754`, `warning` `#FFC107` (always with dark text), `info` only
for neutral notices.

### 3.4 Contrast

WCAG AA asks 4.5:1 for normal text and 3:1 for large text and UI parts.

| Pair | Ratio | Verdict |
|---|---|---|
| Navy on white | 17.6 | Any text |
| White on navy | 17.6 | Any text |
| Navy on sand-faint | 16.6 | Any text |
| Navy on sand-soft | 15.6 | Any text |
| Navy on sand | 11.5 | Any text |
| Body text on sand | 10.1 | Any text |
| Muted on sand-soft | 5.4 | Any text (Bootstrap's grey would be 4.2: too low) |
| White on red-dark | 6.3 | Any text |
| White on red | 4.8 | Any text; keep the navbar text at 1rem or more |
| Red on white | 4.8 | Passes, but red isn't a text colour here (§3.2) |
| Danger on white | 6.5 | Any text (outline danger buttons, error text) |
| Danger on sand-faint | 6.1 | Any text |
| White on danger | 6.5 | Any text (the solid Delete button) |
| Checkbox border `#6C757D` on white | 4.7 | UI part (needs 3:1) |
| Checkbox border `#6C757D` on sand-faint | 4.4 | UI part (needs 3:1) |
| Red on navy | 3.7 | Large text only: don't combine |
| Red on sand | 3.2 | Large text only: don't combine |

### 3.5 Age-group colours (optional)

Chiro age groups each have a colour on their badge: ribbels purple, speelclub yellow,
rakwi green, tito red, keti blue, aspi orange. This comes from one secondary source and
isn't in the house style guide, so check it before relying on it. The app has no age
groups yet; if afdelingsbakken labels ever get them, show the colour as a small dot or
stripe **next to the name**, never as the only cue.

## 4. Type

### 4.1 Fonts

No webfonts are loaded (no CDN, and camp sites have poor connectivity), so both stacks
use fonts already on the device.

```css
--font-body: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
--font-heading: "Myriad Pro Condensed", "Myriad Pro", "Arial Narrow", "Roboto Condensed",
  "sans-serif-condensed", "Helvetica Neue", Arial, sans-serif;
```

- **Body text in the system font.** Condensed type is harder to read in long text and
  at a distance, so the guide's fonts stay with headings.
- **Headings condensed and bold** (`font-weight: 700`, `font-stretch: condensed`), as
  in the guide. Where no condensed font exists they fall back to the bold system font,
  which is fine.
- Vendoring an open-licence condensed font (for example Barlow Semi Condensed, OFL)
  into `static/vendor/` would make headings look the same everywhere. It's optional;
  decide when the pages have moved over.

### 4.2 Scale

| Element | Planning | Kitchen |
|---|---|---|
| Page title (`h1`) | 1.75rem, 2rem from `lg` | 2rem |
| Section (`h2`) | 1.375rem | 1.5rem |
| Sub-section (`h3`) | 1.125rem | 1.25rem |
| Body | 1rem | 1.125rem |
| Quantities, step text | 1rem | `fs-4` (1.5rem) or larger |
| Small print, meta | 0.875rem | 1rem |

- Titles in sentence case, not capitals: capitals are harder to scan and translate.
  Small capitalised labels (`text-uppercase small`, letter-spacing `0.05em`) are fine
  for column and course labels, as the planner already does.
- Numbers in tables and totals use `font-variant-numeric: tabular-nums` and align
  right.

## 5. Brand elements

### 5.1 Navbar

- Background `--chiro-red`, text and icons white, at least 1rem. Hover underlines;
  the active page gets `--chiro-red-dark` behind it and `aria-current="page"`.
- Brand at the left: a Bootstrap icon (`bi-fire` or `bi-egg-fried`) and the app name
  in the heading font: Camp Meal Planner in English, Kamp Maaltijd Planner in Dutch. It replaces the 🏕️ emoji, which looks different on every
  system.
- Below the navbar, nothing: the red field ends straight, no shadow.

### 5.2 Page header and the red rule

Every page starts with the same header (a `components/page_header.html` include):
title, optional one-line meta below it in `--muted`, then a red rule: **3px high,
3rem wide, `--chiro-red`, 0.75rem below the title.** It's the guide's horizontal
"streepje" and the one recurring Chiro touch in the content. The page's main action
sits at the right of the title from `lg`, below it on phones.

### 5.3 Shape and depth

- Corners: Bootstrap's default radius, `0.375rem`, on cards, inputs and buttons. Chips
  and badges fully rounded.
- Depth: cards `shadow-sm` on the sand-faint background. No gradients, no textures.
- The guide calls the logo's red field "playful". The app keeps the playfulness for the
  public home page and empty states (a friendly icon and one sentence), not for working
  screens.

## 6. Components

All of these are Bootstrap components with the tokens above; `app.css` only sets
variables and the few things Bootstrap can't take from a variable (§8).

| Component | Look |
|---|---|
| Primary button | Navy background, white text; hover `--chiro-navy-hover` |
| Secondary button | `btn-outline-primary`: navy border and text; hover `--chiro-navy-soft` |
| Destructive button | `btn-outline-danger` with `bi-trash` and a verb, set apart from the other actions, always confirmed; the confirmation page's final button is solid `btn-danger` |
| Link | Navy, underlined in body text; hover `--chiro-navy-hover` |
| Focus ring | Navy at 25% opacity, 0.25rem, on every interactive element; on the red navbar the ring is white at 60% |
| Form controls | White, grey border; focus border navy; checked boxes and radios navy |
| Card | White, `shadow-sm`; optional header in `--chiro-sand-soft` with navy heading |
| Table | Header row `--chiro-sand-soft`, navy text, `fw-semibold`; rows white, hover `--chiro-sand-faint` |
| Planner chip | `--chiro-sand-soft` background, navy text; empty slot dashed grey border, muted italic; missing recipe danger |
| Tabs and pills | Active: navy (pills filled, tabs underlined navy) |
| Badge | Status colours only (`success`, `warning` with dark text, `danger`, `secondary`); never red or sand for decoration |
| Alert and toast | Bootstrap's own, by meaning |
| Empty state | Navy outline icon (`fs-1`), one sentence, primary button |

## 7. Kitchen, planning and print

- **Kitchen screens** use the same palette at the larger sizes of §4.2. Navy on white
  only for quantities and steps: no sand behind text people read from a distance.
  Ticked items turn `success` with a check icon, never colour alone.
- **Planning screens** use sand tints to group: table headers, card headers, the
  planner grid.
- **Print (WeasyPrint)** keeps its own CSS, but follows the same idea: navy headings, a
  red rule under the document title, sand-soft table headers. Everything must still
  read in black and white: the red rule prints as 70% black, as the guide says, and no
  information depends on colour.

## 8. Implementation

Bootstrap is vendored as compiled CSS, with no Sass build step, so the theme is set
with CSS variables in `app.css`, after `bootstrap.min.css`. Bootstrap 5.3 reads most
colours from variables, but buttons, form focus and checked inputs have values compiled
in and need their own rules:

```css
:root {
  --chiro-red: #E1143C;
  --chiro-red-dark: #BF1133;
  --chiro-navy: #00124D;
  --chiro-navy-hover: #263668;
  --chiro-navy-soft: #EBECF1;
  --chiro-sand: #E4D096;
  --chiro-sand-soft: #F7F1E0;
  --chiro-sand-faint: #FBF8EF;

  --font-body: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-heading: "Myriad Pro Condensed", "Myriad Pro", "Arial Narrow", "Roboto Condensed",
    "sans-serif-condensed", "Helvetica Neue", Arial, sans-serif;

  --bs-primary: var(--chiro-navy);
  --bs-primary-rgb: 0, 18, 77;
  --bs-primary-text-emphasis: var(--chiro-navy);
  --bs-primary-bg-subtle: var(--chiro-navy-soft);
  --bs-primary-border-subtle: #B3B8CA;
  --bs-link-color: var(--chiro-navy);
  --bs-link-color-rgb: 0, 18, 77;
  --bs-link-hover-color: var(--chiro-navy-hover);
  --bs-link-hover-color-rgb: 38, 54, 104;
  --bs-focus-ring-color: rgba(0, 18, 77, 0.25);
  --bs-body-bg: var(--chiro-sand-faint);
  --bs-body-font-family: var(--font-body);
  /* Darker than Bootstrap's #6c757d, which drops under 4.5:1 on the sand tints. */
  --bs-secondary-color: #5c636a;
  /* Bootstrap's red-600: Bootstrap's own #dc3545 is 4.3:1 on sand-faint, under AA.
     The subtle background and text-emphasis variables are dark enough and stay. */
  --bs-danger: #B02A37;
  --bs-danger-rgb: 176, 42, 55;
  /* Field errors (invalid-feedback, is-invalid borders) have their own fixed red. */
  --bs-form-invalid-color: #B02A37;
  --bs-form-invalid-border-color: #B02A37;
}

.btn-primary {
  --bs-btn-bg: var(--chiro-navy);
  --bs-btn-border-color: var(--chiro-navy);
  --bs-btn-hover-bg: var(--chiro-navy-hover);
  --bs-btn-hover-border-color: var(--chiro-navy-hover);
  --bs-btn-active-bg: var(--chiro-navy-hover);
  --bs-btn-active-border-color: var(--chiro-navy-hover);
  --bs-btn-disabled-bg: var(--chiro-navy);
  --bs-btn-disabled-border-color: var(--chiro-navy);
  --bs-btn-focus-shadow-rgb: 0, 18, 77;
}

.btn-outline-primary {
  --bs-btn-color: var(--chiro-navy);
  --bs-btn-border-color: var(--chiro-navy);
  --bs-btn-hover-color: var(--chiro-navy);
  --bs-btn-hover-bg: var(--chiro-navy-soft);
  --bs-btn-hover-border-color: var(--chiro-navy);
  --bs-btn-active-color: #fff;
  --bs-btn-active-bg: var(--chiro-navy);
  --bs-btn-active-border-color: var(--chiro-navy);
  --bs-btn-disabled-color: var(--chiro-navy);
  --bs-btn-disabled-border-color: var(--chiro-navy);
  --bs-btn-focus-shadow-rgb: 0, 18, 77;
}

/* The danger buttons have Bootstrap's red compiled in; these follow --bs-danger. */
.btn-danger {
  --bs-btn-bg: #B02A37;
  --bs-btn-border-color: #B02A37;
  --bs-btn-hover-bg: #8E2230;
  --bs-btn-hover-border-color: #8E2230;
  --bs-btn-active-bg: #8E2230;
  --bs-btn-active-border-color: #842029;
  --bs-btn-disabled-bg: #B02A37;
  --bs-btn-disabled-border-color: #B02A37;
  --bs-btn-focus-shadow-rgb: 176, 42, 55;
}

.btn-outline-danger {
  --bs-btn-color: #B02A37;
  --bs-btn-border-color: #B02A37;
  --bs-btn-hover-bg: #B02A37;
  --bs-btn-hover-border-color: #B02A37;
  --bs-btn-active-bg: #8E2230;
  --bs-btn-active-border-color: #8E2230;
  --bs-btn-disabled-color: #B02A37;
  --bs-btn-disabled-border-color: #B02A37;
  --bs-btn-focus-shadow-rgb: 176, 42, 55;
}

/* Unchecked boxes: Bootstrap's #dee2e6 border is under 3:1 on white and sand. */
.form-check-input { border-color: #6C757D; }
.form-control:focus,
.form-select:focus,
.form-check-input:focus {
  border-color: var(--chiro-navy);
  box-shadow: 0 0 0 0.25rem rgba(0, 18, 77, 0.25);
}
.form-check-input:checked {
  background-color: var(--chiro-navy);
  border-color: var(--chiro-navy);
}

/* Badges fully rounded (DESIGN §6). */
.badge { --bs-badge-border-radius: var(--bs-border-radius-pill); }

.navbar-chiro { background-color: var(--chiro-red); }
.page-rule { width: 3rem; height: 3px; background: var(--chiro-red); border: 0; opacity: 1; }
```

- `base.html`: the navbar's `bg-primary` becomes `navbar-chiro`, keeping
  `data-bs-theme="dark"` and the white link colours already in `app.css`.
- The rest of `app.css` is what Bootstrap's utilities can't express, one line each:
  - the navbar: white links on red (Bootstrap's dark navbar dims them), the active
    item, 44px tap targets;
  - `h1`–`h3`: the condensed heading font in navy, and their sizes;
  - tables' sand-soft header row, navy active pills and list items, and the focus rings (navy, red on
    danger buttons, white on the navbar);
  - `dialog`: Bootstrap 5.3 doesn't style it (the new-ingredient dialog);
  - the planner's slot chips (dashed empty chip, hover states);
  - `.prewrap` (Bootstrap has no `white-space: pre-line` utility), `.prose` (line
    length of help pages and news, and the plain tables and headings their Markdown
    renders to), `.runbook-day` (scroll margin under the sticky
    pills), `.table-responsive` positioning (a visually-hidden heading otherwise
    widens the page on a phone);
  - print rules for the recipe page, and the bill review's fixed-layout table.
- A test (`tests/test_ui_move.py`) fails when a class in `app.css` has no user in the
  templates, the JavaScript or the project's Python; classes that JavaScript adds at
  run time are listed there with the reason.
- Light mode only; there is no dark theme to keep in step.

## 9. Review checklist

For `ui-reviewer` and anyone checking a page:

- [ ] No red in the content area except the page-title rule and real errors or
      destructive actions
- [ ] Primary actions navy; no other accent colour introduced
- [ ] No sand or red used as a text colour
- [ ] Focus ring visible and navy on every interactive element, including form fields
      and checkboxes
- [ ] Page header with the red rule on every full page
- [ ] Status shown with an icon or word as well as colour
- [ ] No Chiro logo, or anything shaped like it
