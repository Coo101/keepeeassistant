"""Recipes: list, one-pager with scaling, PDF, edit and copy (SPEC §9.1)."""

import logging
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.constants import DishType
from core.pdf import render_pdf
from core.portions import format_quantity, round_quantity, scale_factor
from recipes.forms import CopyRecipeForm, IngredientFormSet, RecipeForm, StepFormSet
from recipes.models import Recipe
from recipes.services import copy_recipe

logger = logging.getLogger(__name__)

DISH_TYPE_LABELS = dict(DishType.CHOICES)


def recipe_list(request: HttpRequest) -> HttpResponse:
    """All recipes grouped by dish type; ?q= filters on recipe or ingredient."""
    query = request.GET.get("q", "").strip()
    recipes = Recipe.objects.prefetch_related("steps")
    if query:
        recipes = recipes.filter(
            Q(name__icontains=query) | Q(ingredients__ingredient__name__icontains=query)
        ).distinct()

    groups: list[dict] = []
    by_type: dict[str, list[Recipe]] = {}
    for recipe in recipes:
        by_type.setdefault(recipe.dish_type, []).append(recipe)
    for dish_type, label in DishType.CHOICES:
        if dish_type in by_type:
            groups.append({"label": label, "recipes": by_type[dish_type]})
    return render(
        request, "recipes/recipe_list.html", {"groups": groups, "query": query}
    )


def _parse_portions(request: HttpRequest) -> Decimal | None:
    raw = request.GET.get("portions", "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        portions = Decimal(raw)
    except InvalidOperation:
        return None
    # NaN can't be compared, so check is_finite before the range.
    return portions if portions.is_finite() and 0 < portions < 10000 else None


def _recipe_context(request: HttpRequest, recipe_id: int) -> dict:
    recipe = get_object_or_404(
        Recipe.objects.select_related("author").prefetch_related(
            "ingredients__ingredient", "steps"
        ),
        pk=recipe_id,
    )
    portions = _parse_portions(request)
    scale = scale_factor(portions, recipe.base_portions) if portions else None

    rows = []
    for ri in recipe.ingredients.all():
        if scale is None:
            quantity = ri.quantity_display
        else:
            quantity = format_quantity(round_quantity(ri.quantity * scale, ri.unit))
        rows.append({"name": ri.ingredient.name, "quantity": quantity, "unit": ri.unit})
    return {
        "recipe": recipe,
        "rows": rows,
        "portions": portions,
        "scale": scale,
    }


def _render_detail(
    request: HttpRequest, recipe_id: int, copy_form: CopyRecipeForm | None = None
) -> HttpResponse:
    context = _recipe_context(request, recipe_id)
    recipe = context["recipe"]
    context["can_edit"] = recipe.can_edit(request.user)
    context["copy_form"] = copy_form or CopyRecipeForm(
        initial={"name": f"{recipe.name} (kopie)"}
    )
    return render(request, "recipes/recipe_detail.html", context)


def recipe_detail(request: HttpRequest, recipe_id: int) -> HttpResponse:
    return _render_detail(request, recipe_id)


@require_POST
def recipe_copy(request: HttpRequest, recipe_id: int) -> HttpResponse:
    """Save any recipe under a new name, as the user's own."""
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    form = CopyRecipeForm(request.POST)
    if not form.is_valid():
        return _render_detail(request, recipe_id, copy_form=form)
    copy = copy_recipe(recipe, form.cleaned_data["name"], request.user)
    logger.info("%s copied recipe %s to %s", request.user, recipe.pk, copy.pk)
    return redirect("recipe_detail", recipe_id=copy.pk)


def _recipe_form_page(request: HttpRequest, recipe: Recipe) -> HttpResponse:
    data = request.POST if request.method == "POST" else None
    form = RecipeForm(data, instance=recipe, user=request.user)
    ingredients = IngredientFormSet(data, instance=recipe, prefix="ingredients")
    steps = StepFormSet(data, instance=recipe, prefix="steps")

    # A list, not a generator: show the errors of all three at once.
    if data is not None and all(
        [form.is_valid(), ingredients.is_valid(), steps.is_valid()]
    ):
        with transaction.atomic():
            saved = form.save()
            ingredients.save()
            steps.save()
        logger.info("%s saved recipe %s", request.user, saved.pk)
        return redirect("recipe_detail", recipe_id=saved.pk)

    camp_count = 0
    if recipe.pk:
        camp_count = recipe.menuentry_set.values("camp").distinct().count()
    return render(
        request,
        "recipes/recipe_form.html",
        {
            "recipe": recipe,
            "form": form,
            "ingredients": ingredients,
            "steps": steps,
            "camp_count": camp_count,
        },
    )


def recipe_create(request: HttpRequest) -> HttpResponse:
    return _recipe_form_page(request, Recipe(author=request.user))


def recipe_edit(request: HttpRequest, recipe_id: int) -> HttpResponse:
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    if not recipe.can_edit(request.user):
        raise PermissionDenied("This recipe is read-only; save a copy to change it.")
    return _recipe_form_page(request, recipe)


def recipe_pdf(request: HttpRequest, recipe_id: int) -> HttpResponse:
    context = _recipe_context(request, recipe_id)
    return render_pdf(
        request,
        "recipes/recipe_print.html",
        context,
        filename=f"{context['recipe'].name}.pdf",
    )
