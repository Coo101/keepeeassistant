# Kitchen

## Purpose

The Chiro's kitchen stock (pots, fire pits, gas bottles), used before the camp to
see what to bring or buy. During the camp: kitchen mode, the phone screens for the
cooks (planned, see below).

## Data

- **Utensil**: `chiro`, `name` (unique per Chiro), `in_stock`, `note`. A kitchen
  utility the Chiro owns, shared by its camps.
- **CampUtensil**: `camp`, `utensil`, `needed`. To buy: `needed - in_stock`, at
  least 0. The camp side is described in [shopping](shopping.md).

## Behaviour

### Kitchen stock

- Per Chiro: a stock of kitchen utilities (pots, fire pits, gas bottles), with how
  many it has and a note. All members keep it up to date. An item a camp still needs
  can't be removed.
- The stock page also holds the Chiro's food pantry: see [shopping](shopping.md).
- A bill line in the category "kitchen utilities" can add to the stock: see
  [finance](finance.md).
- What a camp needs, and what the stock lacks, is described in
  [shopping](shopping.md).

## Acceptance

None yet.

## Decisions

- **D16** (2026-11-05): Kitchen mode checks ingredients, it doesn't shop. Shopping
  lists stay with the planner. *The kitchen mode design reverses this once built: it
  adds an extra shopping list for trips during the camp.*

## Planned

- **Kitchen mode**: day view with a shared ingredient check per meal, an extra
  shopping list, a cooking view with timers, evaluation notes, a printable day sheet
  and a pantry count at the end of the camp. Design:
  [kitchen mode design](../superpowers/specs/2026-11-16-kitchen-mode-design.md).
  Plan: [kitchen mode plan](../superpowers/plans/2026-11-16-kitchen-mode.md).
