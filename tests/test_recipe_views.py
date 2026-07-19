"""Recipe list and one-pager views (SPEC §9.1)."""

import pytest
from django.test import Client
from django.urls import reverse

from core.constants import DishType
from tests.factories import KG, PRODUCE, make_recipe

pytestmark = pytest.mark.django_db


def test_recipe_list_groups_by_dish_type() -> None:
    make_recipe("Stoemp", dish_type=DishType.HOT_MEAL)
    make_recipe("Tomatensoep", dish_type=DishType.SOUP)
    response = Client().get(reverse("recipe_list"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Stoemp" in content
    assert "Tomatensoep" in content
    assert content.index("Soup") < content.index("Hot meal")


def test_recipe_detail_shows_ingredients_and_steps() -> None:
    recipe = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=10,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    recipe.steps.create(order=1, instruction="Chop everything.", duration_minutes=20)
    response = Client().get(reverse("recipe_detail", args=[recipe.pk]))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Potatoes" in content
    assert "2.5 kg" in content
    assert "Chop everything." in content
    assert "20 min" in content


def test_recipe_detail_404_for_missing() -> None:
    response = Client().get(reverse("recipe_detail", args=[99999]))
    assert response.status_code == 404


def test_recipe_list_search_filters_by_name_and_ingredient() -> None:
    make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        ingredients=[("Potatoes", "2", KG, PRODUCE)],
    )
    make_recipe("Pancakes", dish_type=DishType.SNACK_SWEET)

    content = Client().get(reverse("recipe_list"), {"q": "stew"}).content.decode()
    assert "Stew" in content and "Pancakes" not in content

    # matches via ingredient name too
    content = Client().get(reverse("recipe_list"), {"q": "potato"}).content.decode()
    assert "Stew" in content and "Pancakes" not in content


def test_recipe_detail_scales_to_requested_portions() -> None:
    # base 10 teens = 10 portions; scale to 20 -> x2
    recipe = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=10,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    response = Client().get(
        reverse("recipe_detail", args=[recipe.pk]), {"portions": "20"}
    )
    content = response.content.decode()
    assert "5 kg" in content
    assert "2.5 kg" not in content


def test_recipe_detail_ignores_invalid_portions() -> None:
    recipe = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=10,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    for bad in ["0", "-4", "abc"]:
        response = Client().get(
            reverse("recipe_detail", args=[recipe.pk]), {"portions": bad}
        )
        assert response.status_code == 200
        assert "2.5 kg" in response.content.decode()


def test_recipe_pdf_endpoint_serves_scaled_document() -> None:
    recipe = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=10,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    response = Client().get(reverse("recipe_pdf", args=[recipe.pk]), {"portions": "20"})
    assert response.status_code == 200
    if response["Content-Type"].startswith("application/pdf"):
        assert response.content[:4] == b"%PDF"
    else:  # HTML fallback when WeasyPrint's native libs are missing
        assert "5 kg" in response.content.decode()
