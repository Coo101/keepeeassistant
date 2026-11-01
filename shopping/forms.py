"""The camp's pantry (SPEC §9.12)."""

from django.forms import modelformset_factory

from core.rows import UniqueRowsFormSet
from shopping.models import PantryItem


class _PantryFormSet(UniqueRowsFormSet):
    unique_field = "ingredient"


PantryFormSet = modelformset_factory(
    PantryItem,
    formset=_PantryFormSet,
    fields=["ingredient", "quantity"],
    extra=3,
    can_delete=True,
)
