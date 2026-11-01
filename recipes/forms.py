"""Forms for recipes and ingredients (SPEC §9.1, §9.6)."""

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils import timezone

from recipes.models import Ingredient, Recipe, RecipeIngredient, RecipeStep


def _validate_name_is_free(name: str, recipe_pk: int | None = None) -> None:
    # The library is shared, so two recipes with one name can't be told apart
    # in the planner's dropdowns.
    if Recipe.objects.filter(name__iexact=name).exclude(pk=recipe_pk).exists():
        raise ValidationError("A recipe with this name already exists.")


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = [
            "name",
            "dish_type",
            "base_children",
            "base_teens",
            "notes",
            "others_can_edit",
        ]

    def __init__(self, *args, user, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not self.instance.can_manage_access(user):
            del self.fields["others_can_edit"]

    def clean_name(self) -> str:
        name = self.cleaned_data["name"]
        _validate_name_is_free(name, self.instance.pk)
        return name


class CopyRecipeForm(forms.Form):
    name = forms.CharField(max_length=200, label="New name")

    def clean_name(self) -> str:
        name = self.cleaned_data["name"]
        _validate_name_is_free(name)
        return name


class IngredientForm(forms.ModelForm):
    """Ingredients are shared by all recipes, so an existing one keeps its name
    and unit here: changing those would alter other people's recipes."""

    class Meta:
        model = Ingredient
        fields = [
            "name",
            "unit",
            "category",
            "shop",
            "price_per_unit",
            "product_details",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["name"].disabled = True
            self.fields["unit"].disabled = True

    def clean_name(self) -> str:
        name = self.cleaned_data["name"]
        duplicates = Ingredient.objects.filter(name__iexact=name)
        if duplicates.exclude(pk=self.instance.pk).exists():
            raise ValidationError("An ingredient with this name already exists.")
        return name

    def clean_price_per_unit(self) -> Decimal | None:
        price = self.cleaned_data["price_per_unit"]
        if price is not None and price < 0:
            raise ValidationError("A price can't be negative.")
        return price

    def save(self, commit: bool = True) -> Ingredient:
        if "price_per_unit" in self.changed_data:
            self.instance.price_updated = timezone.now()
        return super().save(commit)


IngredientFormSet = inlineformset_factory(
    Recipe,
    RecipeIngredient,
    fields=["ingredient", "quantity", "unit"],
    extra=3,
)

StepFormSet = inlineformset_factory(
    Recipe,
    RecipeStep,
    fields=["order", "instruction", "duration_minutes"],
    widgets={"instruction": forms.Textarea(attrs={"rows": 2})},
    extra=3,
)
