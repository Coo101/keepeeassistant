"""Forms for creating, editing and copying recipes (SPEC §9.1)."""

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from recipes.models import Recipe, RecipeIngredient, RecipeStep


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
