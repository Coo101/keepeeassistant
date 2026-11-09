"""Comparing a camp's needs with its Chiro's stock (SPEC §9.15)."""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from accounts.models import Chiro
from camps.models import Camp
from kitchen.models import CampUtensil, Utensil

# The choice on a bill line that creates a stock item from its description.
NEW_ITEM = "new"


def camp_needs(camp: Camp) -> list[CampUtensil]:
    return list(camp.utensil_needs.select_related("utensil"))


def utensils_to_buy(camp: Camp) -> list[CampUtensil]:
    return [need for need in camp_needs(camp) if need.to_buy]


def _find_or_create(chiro: Chiro, name: str) -> Utensil:
    """A name not in the stock yet becomes an item with none in stock."""
    name = name.strip()
    utensil = chiro.utensils.filter(name__iexact=name).first()
    return utensil or Utensil.objects.create(chiro=chiro, name=name)


@transaction.atomic
def save_needs(camp: Camp, rows: list[tuple[str, int]]) -> None:
    """Replaces the camp's needs with (name, needed) rows."""
    camp.utensil_needs.all().delete()
    for name, needed in rows:
        CampUtensil.objects.create(
            camp=camp, utensil=_find_or_create(camp.chiro, name), needed=needed
        )


@transaction.atomic
def add_to_stock(chiro: Chiro, choice: str, name: str, quantity: Decimal) -> Utensil:
    """A bought utility goes into the stock: `choice` is an item's id, or NEW_ITEM
    for an item named after the bill line."""
    if choice == NEW_ITEM:
        utensil = _find_or_create(chiro, name[:200])
    else:
        utensil = chiro.utensils.get(pk=choice)
    count = int(quantity.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    # select_for_update: two reviews saved at once must both count.
    utensil = Utensil.objects.select_for_update().get(pk=utensil.pk)
    utensil.in_stock += max(1, count)
    utensil.save(update_fields=["in_stock"])
    return utensil
