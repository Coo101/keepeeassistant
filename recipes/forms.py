"""Forms for recipes and ingredients (docs/spec/recipes.md)."""

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.constants import FoodTag
from recipes.models import Ingredient, Recipe, RecipeIngredient, RecipeStep


def _validate_name_is_free(name: str, recipe_pk: int | None = None) -> None:
    # The library is shared, so two recipes with one name can't be told apart
    # in the planner's dropdowns.
    if Recipe.objects.filter(name__iexact=name).exclude(pk=recipe_pk).exists():
        raise ValidationError(_("A recipe with this name already exists."))


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
    name = forms.CharField(max_length=200, label=_("New name"))

    def clean_name(self) -> str:
        name = self.cleaned_data["name"]
        _validate_name_is_free(name)
        return name


class IngredientForm(forms.ModelForm):
    """Ingredients are shared by all recipes, so an existing one keeps its name
    and unit here: changing those would alter other people's recipes."""

    price = forms.DecimalField(
        required=False,
        max_digits=8,
        decimal_places=4,
        min_value=0,
        label=_("Price"),
        help_text=_("EUR per kg/liter/piece"),
    )
    tags = forms.MultipleChoiceField(
        required=False,
        choices=FoodTag.CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label=_("Contains"),
        help_text=_("For the diet and balance checks in the planner"),
    )

    class Meta:
        model = Ingredient
        fields = [
            "name",
            "unit",
            "category",
            "shop",
            "product_details",
            "tags",
            "tags_checked",
        ]

    field_order = [
        "name",
        "unit",
        "category",
        "shop",
        "price",
        "product_details",
        "tags",
        "tags_checked",
    ]

    def __init__(self, *args, user, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user = user
        if self.instance.pk:
            self.fields["name"].disabled = True
            self.fields["unit"].disabled = True
            self.fields["price"].label = _("New price")
            self.fields["price"].help_text = _(
                "EUR per kg/liter/piece. Added to the price history; "
                "leave empty to keep the current price."
            )

    def clean_name(self) -> str:
        name = self.cleaned_data["name"]
        duplicates = Ingredient.objects.filter(name__iexact=name)
        if duplicates.exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("An ingredient with this name already exists."))
        return name

    @transaction.atomic
    def save(self, commit: bool = True) -> Ingredient:
        ingredient = super().save(commit)
        price = self.cleaned_data["price"]
        if commit and price is not None:
            # Entering the same price on a later day confirms it's still right.
            today = timezone.localdate()
            if not ingredient.prices.filter(
                price=price, date=today, camp=None
            ).exists():
                ingredient.prices.create(price=price, created_by=self.user)
        return ingredient


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
