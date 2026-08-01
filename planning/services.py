"""Scaled quantities for menu entries (SPEC §7, §9.3)."""

import logging
from dataclasses import dataclass
from decimal import Decimal

from camps.models import Camp
from core.portions import round_quantity, scale_factor
from planning.models import MenuEntry
from recipes.models import Ingredient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScaledIngredient:
    ingredient: Ingredient
    quantity: Decimal
    unit: str


@dataclass(frozen=True)
class ScaledEntry:
    entry: MenuEntry
    scale: Decimal
    ingredients: list[ScaledIngredient]


def scale_entry(entry: MenuEntry, camp: Camp) -> ScaledEntry:
    """Scale one menu entry's recipe quantities to the camp's demand."""
    scale = scale_factor(camp.demand_portions, entry.recipe.base_portions)
    # .all() (not .select_related()) so a prefetched cache is reused; callers
    # that render many entries prefetch recipe__ingredients__ingredient.
    scaled = [
        ScaledIngredient(
            ingredient=ri.ingredient,
            quantity=round_quantity(ri.quantity * scale, ri.unit),
            unit=ri.unit,
        )
        for ri in entry.recipe.ingredients.all()
    ]
    return ScaledEntry(entry=entry, scale=scale, ingredients=scaled)
