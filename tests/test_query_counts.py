"""Guard against N+1 regressions: page cost must not grow with camp size.

The ceilings are deliberately loose — they catch "one query per menu entry"
style regressions, not small refactors.
"""

import datetime

import pytest
from django.test import Client
from django.urls import reverse

from core.constants import DishType, MealType
from shopping.models import ShoppingTrip
from tests.factories import KG, PIECE, PRODUCE, assign, make_camp, make_recipe

pytestmark = pytest.mark.django_db

AUG = lambda d: datetime.date(2026, 8, d)  # noqa: E731


def _busy_camp():
    """A camp with every day fully planned, as in a real draaiboek."""
    camp = make_camp(start=AUG(1), days=8)
    breakfast = make_recipe(
        "Standaardontbijt",
        dish_type=DishType.BREAD_MEAL,
        teens=13,
        ingredients=[("Bread", "8", PIECE, PRODUCE), ("Butter", "1", KG, PRODUCE)],
    )
    soup = make_recipe(
        "Soep",
        dish_type=DishType.SOUP,
        teens=13,
        ingredients=[("Carrots", "2", KG, PRODUCE)],
    )
    main = make_recipe(
        "Stoofpot",
        dish_type=DishType.HOT_MEAL,
        teens=13,
        ingredients=[("Potatoes", "5", KG, PRODUCE), ("Onions", "2", KG, PRODUCE)],
    )
    for recipe in (breakfast, soup, main):
        for order in range(1, 4):
            recipe.steps.create(
                order=order, instruction=f"Stap {order}", duration_minutes=10
            )
    for day in camp.days:
        assign(camp, day, MealType.BREAKFAST, breakfast)
        assign(camp, day, MealType.LUNCH, soup, course="soup")
        assign(camp, day, MealType.LUNCH, main, course="main")
        assign(camp, day, MealType.DINNER, main)
    for day in (AUG(1), AUG(4)):
        ShoppingTrip.objects.create(camp=camp, date=day)
    return camp


@pytest.mark.parametrize(
    ("url_name", "max_queries"),
    [
        ("planner", 6),
        ("runbook", 12),
        ("shopping", 12),
        ("budget", 12),
        ("overview_pdf", 12),
    ],
)
def test_page_query_count_is_bounded(
    django_assert_max_num_queries, url_name, max_queries
) -> None:
    camp = _busy_camp()
    url = reverse(url_name, args=[camp.pk])
    with django_assert_max_num_queries(max_queries):
        assert Client().get(url).status_code == 200


def test_recipe_list_does_not_query_per_recipe(
    django_assert_max_num_queries,
) -> None:
    for i in range(15):
        recipe = make_recipe(f"Recept {i}", dish_type=DishType.HOT_MEAL, teens=10)
        recipe.steps.create(order=1, instruction="Koken", duration_minutes=20)
    with django_assert_max_num_queries(4):
        assert Client().get(reverse("recipe_list")).status_code == 200
