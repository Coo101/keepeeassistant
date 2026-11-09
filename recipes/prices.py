"""Which price a camp uses for an ingredient (SPEC §9.6)."""

import datetime
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import F, Q

from camps.models import Camp
from recipes.models import IngredientPrice


@dataclass(frozen=True)
class ResolvedPrice:
    price: Decimal
    date: datetime.date
    is_camp_price: bool


def resolve_prices(
    camp: Camp, ingredient_ids: Iterable[int]
) -> dict[int, ResolvedPrice]:
    """The camp's own latest price per ingredient, otherwise the latest of all."""
    resolved: dict[int, ResolvedPrice] = {}
    # Newest first, so the first price seen per ingredient and kind is the latest.
    prices = IngredientPrice.objects.filter(
        ingredient_id__in=ingredient_ids, unit=F("ingredient__unit")
    ).filter(Q(camp=camp) | Q(pk__in=IngredientPrice.objects.shared()))
    for price in prices:
        is_camp_price = price.camp_id == camp.pk
        current = resolved.get(price.ingredient_id)
        if current is None or (is_camp_price and not current.is_camp_price):
            resolved[price.ingredient_id] = ResolvedPrice(
                price.price, price.date, is_camp_price
            )
    return resolved
