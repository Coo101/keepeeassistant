# Shopping

## Purpose

Before the camp: turn the menu ([planning](planning.md)) into shopping lists per
trip, minus the Chiro's pantry, and estimate the budget. Also lists the kitchen
utilities a camp needs and the stock lacks.

## Data

- **ShoppingTrip**: `camp`, `date`. Coverage is derived (see Shopping list logic).
- **PantryItem**: `chiro`, `ingredient`, `quantity`. Food already in stock, unique per
  Chiro and ingredient, in the ingredient's unit.
- **Shopping list line** (derived, not stored): `ingredient`, `total_quantity`,
  `unit`, `category`, `shop`.
- **CampUtensil** (a camp's needed utilities) is defined in [kitchen](kitchen.md).

## Behaviour

### Shopping list logic

A shopping trip buys for the days **after** it, up to and including the next trip
day, never its own day.

```
trips = sorted(shopping trip dates)
for i, trip_date in enumerate(trips):
    cover_start = trip_date + 1 day
    cover_end   = trips[i+1] if i+1 < len(trips) else camp.end_date   # inclusive
    covered_days = [d for d in camp_days if cover_start <= d <= cover_end]

    totals = {}   # keyed by (ingredient, unit)
    for entry in MenuEntry where camp=camp and date in covered_days:
        scale = camp.demand_portions / entry.recipe.base_portions
        for ri in entry.recipe.ingredients:
            totals[(ri.ingredient, ri.unit)] += ri.quantity * scale

    subtract the Chiro's pantry, starting with the first trip (see Pantry)
    list = group totals by shop, then category, rounded per planning.md
```

**Coverage warning:** because a trip never covers its own day, the camp's opening
days up to and including the first shopping day are not covered by any trip. To
cover them, add a trip dated before the camp (an arrival-eve shop). The planner and
shopping page **flag every camp day no trip covers**.

### Shopping lists

- For a camp, pick which dates are shopping days. Trips outside the offered dates are
  kept and warned about, and can be removed.
- One summed list per trip, split per shop and grouped by category, using the logic
  above, minus the pantry.
- Warns about uncovered camp days and lists the kitchen utilities the stock lacks.

### Budget

- Cost per shop, per trip and per camp: shopping-list quantity x ingredient price.
- A camp uses its own price for an ingredient if it has one, otherwise the latest
  price, and each line shows which. A camp's own price is history: it doesn't change
  when other camps get new prices. (Prices: see [recipes](recipes.md).)
- Ingredients without a price, or priced per a different unit than a recipe uses,
  are listed and left out of the total. Uncovered days are not in the budget, and the
  cost per portion per day divides by covered days only.

### Pantry

- Per Chiro, on its stock page next to the kitchen utilities: food that's already
  there, in the ingredient's unit. Every camp of the Chiro takes it off its shopping
  lists and budget, starting with the first trip. Camps don't reserve it from each
  other.

### Kitchen utilities a camp needs

- Per camp: which utilities it needs and how many, reached from the planner and the
  camp's edit page. Typing a name that isn't in the stock adds it with none in stock.
- What the stock lacks is listed on the camp's utilities page, the shopping page and
  the shopping lists PDF. Camps of one Chiro each compare with the whole stock; they
  don't reserve items from each other.
- The Chiro's utility stock: see [kitchen](kitchen.md).

## Acceptance

- **Coverage:** trips on day 2 and day 5 of a 7-day camp cover days 3-5 and 6-7;
  days 1-2 are flagged.
- **Coverage:** uncovered days are left out of every list and of the budget.

## Decisions

- **D4**: A shopping day **doesn't** cover its own day; it buys for the following
  days up to and including the next shopping day. Uncovered days are flagged.

## Planned

None yet.
