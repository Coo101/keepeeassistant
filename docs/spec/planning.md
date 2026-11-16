# Planning

## Purpose
Before the camp: set up a camp and its headcount, plan the menu per day and meal,
scale the recipes to the camp, and print the overview and runbook. Shopping lists
and the budget come from this plan: see [shopping](shopping.md).

## Data
- **Camp**: `chiro`, `name`, `start_date`, `end_date`, `is_archived`.
  `num_children` (under 12), `num_teens` (12+), `num_staff`: set from the camp's groups, never typed. `demand_portions` (derived) = `num_teens + num_staff + 0.7 * num_children`.
  Meal times: `breakfast_time`, `lunch_time`, `teatime_time`, `dinner_time`.
  Runbook info: `cook_team`, `location`, `contact_leader`, `contact_rental`, `bakery`, `general_notes`.
- **CampGroup**: `camp`, `name` (unique per camp), `kind` (under 12 / 12+ / staff), `count`. An afdeling or team at the camp (Ribbels, Tito's, Leiding, Kookploeg).
- **DayNote**: `camp`, `date`, `text`. Free runbook notes per camp day.
- **DietaryNeed**: `camp`, `diet` (gluten-free, lactose-free, nut / egg / soy / fish allergy, vegetarian, vegan, no pork), `count`, `note`.
- **MenuEntry**: `camp`, `date`, `meal_type` (breakfast / lunch / tea / dinner), `course` (empty for main, else soup / main / extra / dessert), `recipe` (protected: a planned recipe can't be deleted).

## Behaviour
### Meal slots definition
| Meal | Slot (course) | Dish types allowed | Required |
|---|---|---|---|
| Breakfast | main | `bread_meal` | yes |
| | extra | `bread_meal_extra` | |
| Lunch (midday, large) | soup | `soup` | |
| | main | `hot_meal`, `bread_meal` | yes |
| | extra | `bread_meal_extra` | |
| | dessert | `dessert` | |
| Tea time | snack (main) | `snack_fruitveg`, `snack_savory`, `snack_sweet` | yes |
| Dinner (evening) | main | `hot_meal`, `bread_meal` | yes |
| | extra | `bread_meal_extra` | |
| | dessert | `dessert` | |

- Every slot is labelled in the planner grid. A required slot that is empty is flagged red.
- The planner only offers recipes whose `dish_type` fits the slot. `other` fits no slot.
- A bought item (cake, ice cream, fruit) is a recipe too, with the ingredient and no steps.

### Camps and groups
- **Create, edit, archive and delete** camps of your Chiros.
- Fields: name, dates, headcount per group, the four meal times, the runbook info, diets and allergies, and kitchen utilities needed (see [shopping](shopping.md)).
- **Headcount per group**: every afdeling and team that comes, each counting as under 12, 12+ or staff, with how many. The camp's three totals and its portions are the sums, shown live under the table (and without JavaScript after a save or an added row). Rows left at 0 aren't saved; a name is used once per camp.
  - A new camp starts with the groups of its Chiro's latest camp, numbers at 0. With none (or a user in several Chiros), it starts with Ribbels, Speelclub and Rakwi's (under 12), Tito's, Keti's and Aspi's (12+), and Leiding, Kookploeg and Technische ploeg (staff).
  - The runbook (page and PDF) lists the groups. In the admin the totals are read-only and follow the group rows.
  - Camps from before the groups got one row per total ("nog te verdelen"), to split into afdelingen.
- The day list comes from the start and end date.

### Scaling logic
```
recipe.base_portions = base_teens + 0.7 * base_children
camp.demand_portions = num_teens + num_staff + 0.7 * num_children
scale = camp.demand_portions / recipe.base_portions
```

Each ingredient quantity is multiplied by `scale`. Units are only piece / kg / liter, so totals add up with no conversion. The factor is `CHILD_PORTION_FACTOR` in `core/constants.py`; the helpers are in `core/portions.py`.

**Rounding:** 1 decimal for kg and liter, whole numbers for pieces. A quantity above zero rounds to at least 0.1 or 1 piece, so it stays on the list.

### Menu planner grid
- For a camp, a grid of days × meals with every slot of the meal structure.
- Fill each slot from the recipes that fit it; empty required slots are red.
- Shows the scaled quantities per meal for the camp's demand.
- Warns about meals planned outside the camp dates, which members can remove.
- Shows the diet and balance warnings.
- The planner is where shopping happens: shopping days, lists and the budget are reached from it ([shopping](shopping.md)). Kitchen mode
  has no shopping list (D16, [kitchen](kitchen.md)).

### Output and print
- PDFs through WeasyPrint: camp/day overview, runbook, recipe one-pager, shopping lists (with the missing utilities) and the financial report.
- Filenames are escaped. Without WeasyPrint's libraries (Windows), the same documents are served as print-friendly HTML.

### Runbook
- Per camp: practical info, then per day the menu with scaled quantities, the recipe steps and editable notes. Headings per day, so you can jump to a day. Page and PDF.
- Contact details and notes need a login, like every camp page.

### Diets and allergies
- Per camp: how many people have which diet or allergy. Ingredients are tagged with what they contain. The planner lists every planned meal that conflicts.
- It relies on the tags, so it also lists planned ingredients nobody marked as checked, and tells people to check the labels. It is a help, not a guarantee.

### Balance
- The planner flags hot meals and days without vegetables, days without fruit, and more than 2 sweet recipes a day. Missing vegetables or fruit is only flagged when no ingredient involved has unchecked tags, so unfinished tagging gives no false alarms.

## Acceptance
- **Scaling logic**:
  - A recipe for 10 teens on a camp of 20 teens + 10 children + 5 staff scales by 3.2.
  - 0.04 kg shows as 0.1 kg; 0.3 pieces shows as 1.

## Decisions
- **D1**: Under-12 portion factor = **0.7**. Staff eat and count as a full portion.
- **D5**: Meal slots are as in the meal structure.
- **D7**: Quantities are rounded to **1 decimal** (kg/liter) and whole pieces; camps are always 50+ people.

## Planned
None yet.
