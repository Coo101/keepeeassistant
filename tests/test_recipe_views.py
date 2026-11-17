"""Recipe list and one-pager views (docs/spec/recipes.md)."""

import pytest
from django.urls import reverse

from core.constants import DishType
from tests.factories import KG, PRODUCE, account_client, make_recipe, set_price

pytestmark = pytest.mark.django_db


def test_recipe_list_groups_by_dish_type() -> None:
    make_recipe("Stoemp", dish_type=DishType.HOT_MEAL)
    make_recipe("Tomatensoep", dish_type=DishType.SOUP)
    response = account_client().get(reverse("recipe_list"))
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
    response = account_client().get(reverse("recipe_detail", args=[recipe.pk]))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Potatoes" in content
    assert "2.5 kg" in content
    assert "Chop everything." in content
    assert "20 min" in content


def test_recipe_detail_404_for_missing() -> None:
    response = account_client().get(reverse("recipe_detail", args=[99999]))
    assert response.status_code == 404


def test_recipe_list_search_filters_by_name_and_ingredient() -> None:
    make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        ingredients=[("Potatoes", "2", KG, PRODUCE)],
    )
    make_recipe("Pancakes", dish_type=DishType.SNACK_SWEET)

    content = (
        account_client().get(reverse("recipe_list"), {"q": "stew"}).content.decode()
    )
    assert "Stew" in content and "Pancakes" not in content

    # matches via ingredient name too
    content = (
        account_client().get(reverse("recipe_list"), {"q": "potato"}).content.decode()
    )
    assert "Stew" in content and "Pancakes" not in content


def test_recipe_detail_scales_to_requested_portions() -> None:
    # base 10 teens = 10 portions; scale to 20 -> x2
    recipe = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=10,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    response = account_client().get(
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
        response = account_client().get(
            reverse("recipe_detail", args=[recipe.pk]), {"portions": bad}
        )
        assert response.status_code == 200
        assert "2.5 kg" in response.content.decode()


def test_recipe_pdf_falls_back_to_scaled_html(monkeypatch) -> None:
    monkeypatch.setattr("core.pdf.weasyprint_available", lambda: False)
    recipe = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=10,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    response = account_client().get(
        reverse("recipe_pdf", args=[recipe.pk]), {"portions": "20"}
    )
    assert response.status_code == 200
    assert "5 kg" in response.content.decode()


def test_recipe_search_htmx_returns_the_results_only() -> None:
    make_recipe("Stoofpot")
    make_recipe("Tomatensoep", dish_type=DishType.SOUP)
    response = account_client().get(
        reverse("recipe_list"), {"q": "Stoof"}, HTTP_HX_REQUEST="true"
    )
    content = response.content.decode()
    assert "<h1" not in content
    assert "<html" not in content
    assert "Stoofpot" in content
    assert "Tomatensoep" not in content
    assert 'id="recipe-results"' not in content


@pytest.mark.parametrize("htmx", [False, True])
def test_recipe_search_without_matches(htmx: bool) -> None:
    make_recipe("Stoofpot")
    extra = {"HTTP_HX_REQUEST": "true"} if htmx else {}
    response = account_client().get(reverse("recipe_list"), {"q": "zzz"}, **extra)
    content = response.content.decode()
    assert "bi-search" in content
    assert "No recipes match" in content
    assert "zzz" in content
    assert f'href="{reverse("recipe_list")}"' in content


def _scalable_recipe():
    # base 10 teens = 10 portions; 2.5 kg of potatoes
    return make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=10,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )


def test_recipe_scaling_htmx_returns_the_ingredients() -> None:
    recipe = _scalable_recipe()
    response = account_client().get(
        reverse("recipe_detail", args=[recipe.pk]),
        {"portions": "20"},
        HTTP_HX_REQUEST="true",
    )
    content = response.content.decode()
    assert "5 kg" in content
    assert 'id="recipe-ingredients"' in content
    assert 'id="recipe-pdf-link"' in content
    assert 'hx-swap-oob="true"' in content
    assert "portions=20" in content
    assert "<h1" not in content


def test_recipe_page_has_one_pdf_link() -> None:
    recipe = _scalable_recipe()
    response = account_client().get(
        reverse("recipe_detail", args=[recipe.pk]), {"portions": "20"}
    )
    content = response.content.decode()
    assert content.count('id="recipe-pdf-link"') == 1
    assert "hx-swap-oob" not in content
    assert "portions=20" in content


@pytest.mark.parametrize("bad", ["0", "-4", "abc", "", "1e5"])
def test_recipe_scaling_htmx_ignores_odd_values(bad: str) -> None:
    recipe = _scalable_recipe()
    response = account_client().get(
        reverse("recipe_detail", args=[recipe.pk]),
        {"portions": bad},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    assert "2.5 kg" in response.content.decode()


def test_recipe_scaling_htmx_reads_a_comma() -> None:
    recipe = _scalable_recipe()
    response = account_client().get(
        reverse("recipe_detail", args=[recipe.pk]),
        {"portions": "2,5"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    assert "2.5 kg" not in response.content.decode()


def test_recipe_page_has_no_inline_handlers() -> None:
    recipe = _scalable_recipe()
    content = (
        account_client()
        .get(reverse("recipe_detail", args=[recipe.pk]))
        .content.decode()
    )
    assert "onclick" not in content
    assert "data-print" in content


def test_ingredient_search_htmx_returns_the_table_only() -> None:
    make_recipe("Stoofpot", ingredients=[("Prei", "1", KG, PRODUCE)])
    response = account_client().get(
        reverse("ingredient_list"), {"q": "Pre"}, HTTP_HX_REQUEST="true"
    )
    content = response.content.decode()
    assert "<h1" not in content
    assert "Prei" in content
    assert 'id="ingredient-results"' not in content


def test_ingredient_without_price_is_flagged() -> None:
    make_recipe("Stoofpot", ingredients=[("Prei", "1", KG, PRODUCE)])
    client = account_client()
    content = client.get(reverse("ingredient_list")).content.decode()
    assert "text-bg-warning" in content
    assert "no price" in content
    set_price("Prei", "1.20")
    content = client.get(reverse("ingredient_list")).content.decode()
    assert "1.20" in content


@pytest.mark.parametrize("htmx", [False, True])
def test_ingredient_search_without_matches(htmx: bool) -> None:
    make_recipe("Stoofpot", ingredients=[("Prei", "1", KG, PRODUCE)])
    extra = {"HTTP_HX_REQUEST": "true"} if htmx else {}
    response = account_client().get(reverse("ingredient_list"), {"q": "zzz"}, **extra)
    content = response.content.decode()
    assert "bi-search" in content
    assert "No ingredients match" in content
    assert "zzz" in content
    assert f'href="{reverse("ingredient_list")}"' in content
