# Recipes

## Purpose

Before the camp: the shared library of recipes and ingredients, with prices, that
every Chiro plans from. Recipes and ingredients are shared between all Chiros (D11 in
[SPEC](../SPEC.md)); camps are not.

## Data

- **Ingredient**
  - `name` (unique), `unit` (piece / kg / liter, fixed set, no conversions). Both
    fixed after creation, except for staff in the admin.
  - `category`: produce / dairy / meat / bakery / dry goods / other.
  - `shop`: Van Zon / Colruyt / bakker / beenhouwer. Lists are split per shop.
  - `product_details`: free text describing the product the price is for.
  - `tags`: what it contains (gluten, lactose, nuts, egg, soy, fish, meat, pork,
    vegetable, fruit, high in sugar). `tags_checked`: someone confirmed the tags.
- **IngredientPrice**: `ingredient`, `price`, `unit`, `source` (by hand / earlier
  stored / bill), `date`, `created_by`, `camp` (optional).
  - Without a camp it's a general price; with one it's what that camp paid. Kept
    without a camp when the camp is deleted (except example camps, see
    [accounts](accounts.md)).
  - Only prices in the ingredient's current unit count. The latest price is the most
    recent one across all camps and Chiros. New prices add to the history; they never
    overwrite.
- **Recipe**
  - `name` (unique, so the planner can tell them apart), `dish_type` (soup / hot_meal
    / bread_meal / bread_meal_extra / dessert / snack_fruitveg / snack_savory /
    snack_sweet / other), `notes`.
  - `base_children` (under 12) and `base_teens` (12+) the quantities feed.
    `base_portions` (derived) = `base_teens + 0.7 * base_children`.
  - `author` (optional), `others_can_edit` (see Access below).
  - Has many **RecipeIngredient** and **RecipeStep**.
- **RecipeIngredient**: `recipe`, `ingredient`, `quantity`, `unit`. The unit must
  match the ingredient's unit (validated), because prices are per that unit.
- **RecipeStep**: `recipe`, `order`, `instruction`, `duration_minutes` (optional).

## Behaviour

### Recipes

- List, add, edit, copy and delete recipes outside the admin.
- Fields: name, dish type, base children + teens, ingredients (an ingredient can be
  added from the recipe form without leaving it), ordered steps with optional time.
  "Add ingredient" and "Add step" add an empty row in place (HTMX); without
  JavaScript they post the form and show it again with one more row, saving nothing.
- Shows the total time (sum of the step durations).
- **One-pager:** a recipe page with ingredients and steps, scaled to any number of
  portions (`?portions=`; invalid values fall back to the base), also as a PDF.
  Scaling: see [planning](planning.md).

### Ingredients

- List, add and edit ingredients and their prices outside the admin.
- The ingredient's page shows its price history.
- Bills add camp prices: see [finance](finance.md).

### Access

Login and camp access: see [accounts](accounts.md).

- **Recipes** are shared: anyone with an account can read them and save a copy, which
  needs a new name and belongs to whoever made it.
  - The author (or staff) chooses read-only or editable by every account. A recipe
    without an author can only be changed by staff.
  - While another Chiro has a current or future camp planning a recipe, only staff can
    change it, so that camp's lists and budget don't change under it; a copy can.
    Finished and archived camps don't lock it. The edit page warns about the camps a
    change affects.
  - The author (or staff) can delete it once no camp plans it.
- **Ingredients** are shared: anyone with an account can add one, add a price, and
  change its category, shop, product details and tags. Anyone can delete one no
  recipe uses.
- Deleting always asks for confirmation first.

## Acceptance

None yet.

## Decisions

- **D2**: Recipes are entered as "serves X under-12 + Y 12+" and converted to base
  portions.
- **D3**: **Units are piece / kg / liter only.** No conversions. A recipe's unit must
  match its ingredient's unit.
- **D12**: **Prices are a history.** A camp's own price (from its bills) wins,
  otherwise the latest price. A new price never changes another camp's own price.
- **D13**: The automatic Colruyt price import was removed: the third-party product
  dump is unmaintained and its matches were unreliable. Prices come from people and
  bills.

## Planned

None yet.
