"""The recipe form's "add ingredient" and "add step" buttons."""

import pytest
from django.test import Client
from django.urls import reverse

from core.constants import DishType
from recipes.models import Ingredient, Recipe
from tests.factories import KG, PRODUCE, account_client, make_recipe

pytestmark = pytest.mark.django_db


def _form_data(**extra: str) -> dict:
    """A new recipe with one typed ingredient row out of three."""
    ingredient = Ingredient.objects.create(name="Wortelen", unit=KG, category=PRODUCE)
    data = {
        "name": "Stoemp",
        "dish_type": DishType.HOT_MEAL,
        "base_children": "0",
        "base_teens": "10",
        "notes": "",
        "ingredients-TOTAL_FORMS": "3",
        "ingredients-INITIAL_FORMS": "0",
        "ingredients-0-ingredient": str(ingredient.pk),
        "ingredients-0-quantity": "2",
        "ingredients-0-unit": KG,
        "steps-TOTAL_FORMS": "3",
        "steps-INITIAL_FORMS": "0",
    }
    return {**data, **extra}


def test_row_is_numbered_by_total_forms_and_bumps_it() -> None:
    url = reverse("recipe_formset_row", args=["ingredients"])
    response = account_client().get(url, {"ingredients-TOTAL_FORMS": "3"})
    html = response.content.decode()
    assert response.status_code == 200
    assert 'name="ingredients-3-ingredient"' in html
    assert 'name="ingredients-3-quantity"' in html
    assert 'name="ingredients-TOTAL_FORMS" value="4"' in html
    assert 'hx-swap-oob="true"' in html


def test_step_row() -> None:
    url = reverse("recipe_formset_row", args=["steps"])
    html = account_client().get(url, {"steps-TOTAL_FORMS": "5"}).content.decode()
    assert 'name="steps-5-instruction"' in html
    assert 'name="steps-TOTAL_FORMS" value="6"' in html


@pytest.mark.parametrize("total", ["", "abc", "-4"])
def test_row_with_a_bad_count_starts_at_zero(total: str) -> None:
    url = reverse("recipe_formset_row", args=["steps"])
    html = account_client().get(url, {"steps-TOTAL_FORMS": total}).content.decode()
    assert 'name="steps-0-instruction"' in html


def test_row_for_an_unknown_list_is_404() -> None:
    url = reverse("recipe_formset_row", args=["bills"])
    assert account_client().get(url).status_code == 404


def test_row_needs_a_login() -> None:
    url = reverse("recipe_formset_row", args=["steps"])
    assert Client().get(url).status_code == 302


def test_form_shows_both_add_buttons() -> None:
    html = account_client().get(reverse("recipe_create")).content.decode()
    assert 'name="add_row" value="ingredients"' in html
    assert 'name="add_row" value="steps"' in html


def test_add_row_without_javascript_keeps_the_input_and_saves_nothing() -> None:
    data = _form_data(add_row="ingredients")
    response = account_client().post(reverse("recipe_create"), data)
    html = response.content.decode()
    assert response.status_code == 200
    assert not Recipe.objects.exists()
    assert 'name="ingredients-TOTAL_FORMS" value="4"' in html
    assert 'name="ingredients-3-ingredient"' in html
    assert 'value="Stoemp"' in html
    # The new, empty row isn't flagged as incomplete.
    assert "errorlist" not in html


def test_an_added_row_is_saved_on_edit() -> None:
    recipe = make_recipe("Puree")
    recipe.others_can_edit = True
    recipe.save()
    data = _form_data(
        name="Puree",
        **{
            "steps-TOTAL_FORMS": "4",
            "steps-3-order": "1",
            "steps-3-instruction": "Aardappelen koken.",
        },
    )
    url = reverse("recipe_edit", args=[recipe.pk])
    assert account_client().post(url, data).status_code == 302
    assert recipe.steps.get().instruction == "Aardappelen koken."
