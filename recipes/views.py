"""Recipes: list, one-pager with scaling, PDF, edit and copy (SPEC §9.1)."""

import logging
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.constants import DishType
from core.delete import confirm_delete
from core.pdf import render_pdf
from core.portions import format_quantity, round_quantity, scale_factor
from recipes.forms import (
    CopyRecipeForm,
    IngredientForm,
    IngredientFormSet,
    RecipeForm,
    StepFormSet,
)
from recipes.models import Ingredient, Recipe
from recipes.services import copy_recipe

logger = logging.getLogger(__name__)

# Keeps the add-ingredient dialog's fields apart from the recipe form's.
NEW_INGREDIENT_PREFIX = "new_ingredient"

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
    context["can_delete"] = recipe.can_manage_access(request.user)
    context["locked_by_others"] = not context["can_edit"] and (
        recipe.others_can_edit or recipe.author_id == request.user.pk
    )
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
            "planned_by_others": (
                recipe.pk and recipe.planned_by_other_chiros(request.user)
            ),
            "new_ingredient_form": IngredientForm(
                prefix=NEW_INGREDIENT_PREFIX, user=request.user
            ),
        },
    )


def recipe_create(request: HttpRequest) -> HttpResponse:
    return _recipe_form_page(request, Recipe(author=request.user))


def recipe_edit(request: HttpRequest, recipe_id: int) -> HttpResponse:
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    if not recipe.can_edit(request.user):
        raise PermissionDenied("This recipe can't be changed; save a copy instead.")
    return _recipe_form_page(request, recipe)


def recipe_delete(request: HttpRequest, recipe_id: int) -> HttpResponse:
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    if not recipe.can_manage_access(request.user):
        raise PermissionDenied("Only the author can delete this recipe.")
    # A count only: the camps may belong to other Chiros.
    camp_count = recipe.menuentry_set.values("camp").distinct().count()
    blocked_reason = ""
    if camp_count:
        blocked_reason = (
            f"It is planned in {camp_count} camp{pluralize(camp_count)}, which may "
            "include other Chiros' camps. It can only be deleted once no camp "
            "plans it."
        )
    return confirm_delete(
        request,
        recipe,
        cancel_url=reverse("recipe_detail", args=[recipe.pk]),
        success_url=reverse("recipe_list"),
        consequences=["Its ingredient list and steps"],
        blocked_reason=blocked_reason,
    )


def ingredient_list(request: HttpRequest) -> HttpResponse:
    """All ingredients; ?q= filters on name or product details."""
    query = request.GET.get("q", "").strip()
    ingredients = Ingredient.objects.with_latest_price()
    if query:
        ingredients = ingredients.filter(
            Q(name__icontains=query) | Q(product_details__icontains=query)
        )
    return render(
        request,
        "recipes/ingredient_list.html",
        {"ingredients": ingredients, "query": query},
    )


def _ingredient_form_page(
    request: HttpRequest, ingredient: Ingredient | None = None
) -> HttpResponse:
    data = request.POST if request.method == "POST" else None
    form = IngredientForm(data, instance=ingredient, user=request.user)
    if data is not None and form.is_valid():
        saved = form.save()
        logger.info("%s saved ingredient %s", request.user, saved.pk)
        return redirect("ingredient_list")
    return render(
        request,
        "recipes/ingredient_form.html",
        {
            "ingredient": ingredient,
            "form": form,
            "prices": ingredient.prices.all() if ingredient else [],
        },
    )


def ingredient_create(request: HttpRequest) -> HttpResponse:
    return _ingredient_form_page(request)


@require_POST
def ingredient_quick_add(request: HttpRequest) -> JsonResponse:
    """Add an ingredient from the recipe form, without leaving that page."""
    form = IngredientForm(request.POST, prefix=NEW_INGREDIENT_PREFIX, user=request.user)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    ingredient = form.save()
    logger.info("%s added ingredient %s", request.user, ingredient.pk)
    return JsonResponse(
        {"id": ingredient.pk, "label": str(ingredient), "unit": ingredient.unit},
        status=201,
    )


def ingredient_delete(request: HttpRequest, ingredient_id: int) -> HttpResponse:
    ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
    names = list(
        Recipe.objects.filter(ingredients__ingredient=ingredient).values_list(
            "name", flat=True
        )
    )
    blocked_reason = f"These recipes use it: {', '.join(names)}." if names else ""
    if not names and ingredient.prices.exclude(camp=None).exists():
        # A paid price is a camp's history, possibly another Chiro's.
        blocked_reason = "Camps have recorded prices for it."
    return confirm_delete(
        request,
        ingredient,
        cancel_url=reverse("ingredient_edit", args=[ingredient.pk]),
        success_url=reverse("ingredient_list"),
        consequences=[f"{ingredient.prices.count()} prices in its history"],
        blocked_reason=blocked_reason,
    )


def ingredient_edit(request: HttpRequest, ingredient_id: int) -> HttpResponse:
    return _ingredient_form_page(
        request, get_object_or_404(Ingredient, pk=ingredient_id)
    )


def recipe_pdf(request: HttpRequest, recipe_id: int) -> HttpResponse:
    context = _recipe_context(request, recipe_id)
    return render_pdf(
        request,
        "recipes/recipe_print.html",
        context,
        filename=f"{context['recipe'].name}.pdf",
    )
