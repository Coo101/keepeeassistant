"""Recipe browsing: list, one-pager detail with scaling, PDF (SPEC §9.1)."""

from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from core.constants import DishType
from core.pdf import render_pdf
from core.portions import format_quantity, round_quantity, scale_factor
from recipes.models import Recipe

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
    return portions if 0 < portions < 10000 else None


def _recipe_context(request: HttpRequest, recipe_id: int) -> dict:
    recipe = get_object_or_404(
        Recipe.objects.prefetch_related("ingredients__ingredient", "steps"),
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


def recipe_detail(request: HttpRequest, recipe_id: int) -> HttpResponse:
    context = _recipe_context(request, recipe_id)
    return render(request, "recipes/recipe_detail.html", context)


def recipe_pdf(request: HttpRequest, recipe_id: int) -> HttpResponse:
    context = _recipe_context(request, recipe_id)
    return render_pdf(
        request,
        "recipes/recipe_print.html",
        context,
        filename=f"{context['recipe'].name}.pdf",
    )
