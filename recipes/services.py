"""Recipe sharing logic (docs/spec/recipes.md)."""

from django.db import transaction

from recipes.models import Recipe, RecipeIngredient, RecipeStep


@transaction.atomic
def copy_recipe(recipe: Recipe, name: str, author) -> Recipe:
    """A renamed copy with its ingredients and steps, owned by `author`."""
    copy = Recipe.objects.create(
        name=name,
        dish_type=recipe.dish_type,
        base_children=recipe.base_children,
        base_teens=recipe.base_teens,
        notes=recipe.notes,
        author=author,
    )
    RecipeIngredient.objects.bulk_create(
        RecipeIngredient(
            recipe=copy,
            ingredient=ri.ingredient,
            quantity=ri.quantity,
            unit=ri.unit,
        )
        for ri in recipe.ingredients.all()
    )
    RecipeStep.objects.bulk_create(
        RecipeStep(
            recipe=copy,
            order=step.order,
            instruction=step.instruction,
            duration_minutes=step.duration_minutes,
        )
        for step in recipe.steps.all()
    )
    return copy
