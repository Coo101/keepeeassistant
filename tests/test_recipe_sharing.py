"""Shared recipes: any account reads and copies; the author decides who edits."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from accounts.models import Chiro
from core.constants import DishType, MealType
from recipes.models import Ingredient, Recipe
from tests.factories import (
    KG,
    PRODUCE,
    account_client,
    assign,
    make_camp,
    make_recipe,
)

pytestmark = pytest.mark.django_db


def _recipe_data(name: str = "Stoemp", **extra) -> dict:
    """A valid POST for the recipe form, with empty formsets."""
    data = {
        "name": name,
        "dish_type": DishType.HOT_MEAL,
        "base_children": "0",
        "base_teens": "10",
        "notes": "",
    }
    for prefix in ("ingredients", "steps"):
        data[f"{prefix}-TOTAL_FORMS"] = "0"
        data[f"{prefix}-INITIAL_FORMS"] = "0"
    return {**data, **extra}


@pytest.fixture
def recipe() -> Recipe:
    recipe = make_recipe(
        "Stoofpot",
        dish_type=DishType.HOT_MEAL,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    recipe.steps.create(order=1, instruction="Alles stoven.", duration_minutes=90)
    return recipe


@pytest.fixture
def author_client(recipe: Recipe) -> Client:
    client = account_client("auteur")
    recipe.author = User.objects.get(username="auteur")
    recipe.save()
    return client


def test_recipes_need_an_account(recipe: Recipe) -> None:
    response = Client().get(reverse("recipe_detail", args=[recipe.pk]))
    assert response.status_code == 302
    assert reverse("login") in response["Location"]


def test_account_without_chiro_can_read_recipes(recipe: Recipe) -> None:
    client = account_client()
    assert client.get(reverse("recipe_list")).status_code == 200
    assert client.get(reverse("recipe_detail", args=[recipe.pk])).status_code == 200


def test_read_only_recipe_cannot_be_edited(author_client, recipe: Recipe) -> None:
    client = account_client("ander")
    url = reverse("recipe_edit", args=[recipe.pk])

    assert client.get(url).status_code == 403
    assert client.post(url, _recipe_data("Gekaapt")).status_code == 403

    recipe.refresh_from_db()
    assert recipe.name == "Stoofpot"
    detail = client.get(reverse("recipe_detail", args=[recipe.pk])).content.decode()
    assert url not in detail
    assert "read-only" in detail


def test_author_can_edit_and_open_up_a_recipe(author_client, recipe: Recipe) -> None:
    url = reverse("recipe_edit", args=[recipe.pk])
    data = _recipe_data("Stoofpot", others_can_edit="on")
    assert author_client.post(url, data).status_code == 302

    recipe.refresh_from_db()
    assert recipe.others_can_edit is True
    assert account_client("ander").get(url).status_code == 200


def test_other_editor_cannot_change_who_may_edit(author_client, recipe) -> None:
    recipe.others_can_edit = True
    recipe.save()
    client = account_client("ander")
    url = reverse("recipe_edit", args=[recipe.pk])

    assert "others_can_edit" not in client.get(url).content.decode()
    # Leaving out the box would read as "off" if the field were still there.
    assert client.post(url, _recipe_data("Nieuwe naam")).status_code == 302

    recipe.refresh_from_db()
    assert recipe.name == "Nieuwe naam"
    assert recipe.others_can_edit is True
    assert recipe.author.username == "auteur"


def test_recipe_without_author_is_for_staff_only(recipe: Recipe) -> None:
    url = reverse("recipe_edit", args=[recipe.pk])
    assert account_client("ander").get(url).status_code == 403
    assert account_client("baas", is_staff=True).get(url).status_code == 200


def test_create_makes_the_user_the_author() -> None:
    client = account_client()
    response = client.post(reverse("recipe_create"), _recipe_data())
    assert response.status_code == 302
    recipe = Recipe.objects.get(name="Stoemp")
    assert recipe.author.username == "kok"
    assert recipe.others_can_edit is False


def test_edit_saves_ingredients_and_steps(author_client, recipe: Recipe) -> None:
    item = recipe.ingredients.get()
    step = recipe.steps.get()
    carrots = Ingredient.objects.create(name="Wortel", unit=KG)
    data = _recipe_data(
        "Stoofpot",
        **{
            "ingredients-TOTAL_FORMS": "2",
            "ingredients-INITIAL_FORMS": "1",
            "ingredients-0-id": item.pk,
            "ingredients-0-ingredient": item.ingredient_id,
            "ingredients-0-quantity": "3",
            "ingredients-0-unit": KG,
            "ingredients-1-ingredient": carrots.pk,
            "ingredients-1-quantity": "1",
            "ingredients-1-unit": KG,
            "steps-TOTAL_FORMS": "1",
            "steps-INITIAL_FORMS": "1",
            "steps-0-id": step.pk,
            "steps-0-order": "1",
            "steps-0-instruction": "Alles stoven.",
            "steps-0-DELETE": "on",
        },
    )

    response = author_client.post(reverse("recipe_edit", args=[recipe.pk]), data)

    assert response.status_code == 302
    assert {ri.ingredient.name: ri.quantity for ri in recipe.ingredients.all()} == {
        "Potatoes": Decimal("3"),
        "Wortel": Decimal("1"),
    }
    assert not recipe.steps.exists()


def test_edit_rejects_a_unit_that_does_not_match(author_client, recipe) -> None:
    item = recipe.ingredients.get()
    data = _recipe_data(
        "Stoofpot",
        **{
            "ingredients-TOTAL_FORMS": "1",
            "ingredients-INITIAL_FORMS": "1",
            "ingredients-0-id": item.pk,
            "ingredients-0-ingredient": item.ingredient_id,
            "ingredients-0-quantity": "3",
            "ingredients-0-unit": "piece",
        },
    )
    response = author_client.post(reverse("recipe_edit", args=[recipe.pk]), data)
    assert response.status_code == 200
    assert "is measured in" in response.content.decode()
    item.refresh_from_db()
    assert item.quantity == Decimal("2.5")


def test_edit_warns_when_camps_use_the_recipe(author_client, recipe: Recipe) -> None:
    url = reverse("recipe_edit", args=[recipe.pk])
    assert "Planned in" not in author_client.get(url).content.decode()

    camp = make_camp(chiro=Chiro.objects.create(name="Andere Chiro"))
    assign(camp, camp.start_date, MealType.DINNER, recipe)

    assert "Planned in 1 camp." in author_client.get(url).content.decode()


def test_anyone_can_save_a_renamed_copy(author_client, recipe: Recipe) -> None:
    client = account_client("ander")

    response = client.post(
        reverse("recipe_copy", args=[recipe.pk]), {"name": "Mijn stoofpot"}
    )

    copy = Recipe.objects.get(name="Mijn stoofpot")
    assert response.status_code == 302
    assert response["Location"] == reverse("recipe_detail", args=[copy.pk])
    assert copy.author.username == "ander"
    assert copy.others_can_edit is False
    assert copy.ingredients.get().quantity == Decimal("2.5")
    assert copy.steps.get().instruction == "Alles stoven."
    # the copy is independent and editable by its new owner
    assert client.get(reverse("recipe_edit", args=[copy.pk])).status_code == 200
    copy.ingredients.all().delete()
    assert recipe.ingredients.count() == 1


def test_copy_needs_a_free_name(recipe: Recipe) -> None:
    client = account_client()
    url = reverse("recipe_copy", args=[recipe.pk])

    for name in ("stoofpot", "", "   "):
        response = client.post(url, {"name": name})
        assert response.status_code == 200
        assert response.context["copy_form"].errors

    assert Recipe.objects.count() == 1


def test_copy_refuses_get(recipe: Recipe) -> None:
    response = account_client().get(reverse("recipe_copy", args=[recipe.pk]))
    assert response.status_code == 405
