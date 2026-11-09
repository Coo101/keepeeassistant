"""Forms for the menu planner (SPEC §9.3)."""

from django import forms
from django.utils.translation import gettext_lazy as _

from core.constants import allowed_dish_types
from recipes.models import Recipe


class SlotForm(forms.Form):
    """Pick a recipe for one (date, meal, course) slot; empty clears the slot."""

    recipe = forms.ModelChoiceField(
        queryset=Recipe.objects.none(),
        required=False,
        empty_label=_("— no recipe (clear slot) —"),
    )

    def __init__(self, *args, meal_type: str, course: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        dish_types = allowed_dish_types(meal_type, course)
        self.fields["recipe"].queryset = Recipe.objects.filter(dish_type__in=dish_types)
