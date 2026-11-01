"""Deleting, removing stray entries, and adding an ingredient from a recipe."""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from accounts.models import Chiro
from camps.models import Camp, DayNote
from core.constants import DishType, IngredientCategory, MealType, Shop
from planning.models import MenuEntry
from recipes.models import Ingredient, Recipe, RecipeIngredient
from shopping.models import ShoppingTrip
from tests.factories import (
    KG,
    PRODUCE,
    account_client,
    assign,
    make_camp,
    make_recipe,
    member_client,
)

pytestmark = pytest.mark.django_db

AUG = lambda d: datetime.date(2026, 8, d)  # noqa: E731


def _foreign_client() -> Client:
    other = make_camp(chiro=Chiro.objects.create(name="Andere Chiro"))
    return member_client(other, username="buur")


def _planned_camp() -> tuple[Camp, Recipe]:
    camp = make_camp()  # Aug 1-5
    recipe = make_recipe("Stoofpot", dish_type=DishType.HOT_MEAL)
    assign(camp, AUG(5), MealType.DINNER, recipe)
    return camp, recipe


def _stray_entry() -> tuple[Camp, MenuEntry]:
    camp, _ = _planned_camp()
    camp.end_date = AUG(2)
    camp.save()
    return camp, MenuEntry.objects.get()


def _quick_add_data(**extra) -> dict:
    data = {
        "name": "Wortel",
        "unit": KG,
        "category": IngredientCategory.PRODUCE,
        "shop": Shop.COLRUYT,
        **extra,
    }
    return {f"new_ingredient-{key}": value for key, value in data.items()}


def test_camp_delete_asks_first_then_removes_everything() -> None:
    camp, recipe = _planned_camp()
    ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    DayNote.objects.create(camp=camp, date=AUG(1), text="notitie")
    client = member_client(camp)
    url = reverse("camp_delete", args=[camp.pk])

    content = client.get(url).content.decode()
    assert "1 planned meals" in content
    assert Camp.objects.filter(pk=camp.pk).exists()

    response = client.post(url)

    assert response["Location"] == reverse("camp_list")
    assert not Camp.objects.filter(pk=camp.pk).exists()
    assert not MenuEntry.objects.exists()
    assert not ShoppingTrip.objects.exists()
    assert not DayNote.objects.exists()
    assert Recipe.objects.filter(pk=recipe.pk).exists()


def test_camp_delete_is_limited_to_members() -> None:
    camp = make_camp()
    url = reverse("camp_delete", args=[camp.pk])
    assert _foreign_client().post(url).status_code == 404
    assert Client().post(url).status_code == 302
    assert Camp.objects.filter(pk=camp.pk).exists()


def test_recipe_delete_only_for_author_or_staff() -> None:
    recipe = make_recipe("Stoofpot")
    author_client = account_client("auteur")
    recipe.author = User.objects.get(username="auteur")
    recipe.others_can_edit = True  # editing doesn't include deleting
    recipe.save()
    url = reverse("recipe_delete", args=[recipe.pk])
    detail = reverse("recipe_detail", args=[recipe.pk])

    other = account_client("ander")
    assert other.post(url).status_code == 403
    assert url not in other.get(detail).content.decode()
    assert url in author_client.get(detail).content.decode()
    assert Recipe.objects.filter(pk=recipe.pk).exists()

    assert account_client("baas", is_staff=True).get(url).status_code == 200
    assert author_client.post(url).status_code == 302
    assert not Recipe.objects.filter(pk=recipe.pk).exists()


def test_planned_recipe_cannot_be_deleted() -> None:
    camp, recipe = _planned_camp()
    client = account_client("baas", is_staff=True)
    url = reverse("recipe_delete", args=[recipe.pk])

    page = client.get(url)
    assert "planned in 1 camp," in page.content.decode()
    assert camp.name not in page.content.decode()
    assert 'type="submit">Delete' not in page.content.decode()

    assert client.post(url).status_code == 409
    assert Recipe.objects.filter(pk=recipe.pk).exists()


def test_recipe_delete_takes_its_lines_but_keeps_the_ingredient() -> None:
    recipe = make_recipe("Soep", ingredients=[("Wortel", "1", KG, PRODUCE)])
    client = account_client("baas", is_staff=True)
    client.post(reverse("recipe_delete", args=[recipe.pk]))
    assert not RecipeIngredient.objects.exists()
    assert Ingredient.objects.filter(name="Wortel").exists()


def test_ingredient_delete_blocked_while_a_recipe_uses_it() -> None:
    recipe = make_recipe("Soep", ingredients=[("Wortel", "1", KG, PRODUCE)])
    ingredient = Ingredient.objects.get(name="Wortel")
    client = account_client()
    url = reverse("ingredient_delete", args=[ingredient.pk])

    assert "Soep" in client.get(url).content.decode()
    assert client.post(url).status_code == 409
    assert Ingredient.objects.filter(pk=ingredient.pk).exists()

    recipe.delete()
    assert client.post(url).status_code == 302
    assert not Ingredient.objects.filter(pk=ingredient.pk).exists()


def test_stray_entry_can_be_removed_and_returns_to_the_right_page() -> None:
    camp, entry = _stray_entry()
    client = member_client(camp)
    url = reverse("remove_outside_entry", args=[camp.pk, entry.pk])
    assert url in client.get(reverse("planner", args=[camp.pk])).content.decode()
    assert url in client.get(reverse("shopping", args=[camp.pk])).content.decode()

    response = client.post(url, {"back": "shopping"})

    assert response["Location"] == reverse("shopping", args=[camp.pk])
    assert not MenuEntry.objects.exists()


def test_entry_inside_the_camp_dates_cannot_be_removed_this_way() -> None:
    camp, _ = _planned_camp()
    entry = MenuEntry.objects.get()
    url = reverse("remove_outside_entry", args=[camp.pk, entry.pk])
    assert member_client(camp).post(url).status_code == 404
    assert MenuEntry.objects.exists()


def test_stray_entry_removal_is_post_only_and_for_members() -> None:
    camp, entry = _stray_entry()
    url = reverse("remove_outside_entry", args=[camp.pk, entry.pk])
    assert member_client(camp).get(url).status_code == 405
    assert _foreign_client().post(url).status_code == 404
    assert Client().post(url).status_code == 302
    assert MenuEntry.objects.exists()


def test_stray_trip_can_be_removed() -> None:
    camp = make_camp()  # the form offers Jul 29 - Aug 5
    stray = ShoppingTrip.objects.create(camp=camp, date=datetime.date(2026, 7, 20))
    kept = ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    client = member_client(camp)
    url = reverse("remove_outside_trip", args=[camp.pk, stray.pk])
    assert url in client.get(reverse("shopping", args=[camp.pk])).content.decode()

    assert client.post(url).status_code == 302
    assert list(camp.shopping_trips.all()) == [kept]


def test_trip_on_the_form_cannot_be_removed_this_way() -> None:
    camp = make_camp()
    trip = ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    url = reverse("remove_outside_trip", args=[camp.pk, trip.pk])
    assert member_client(camp).post(url).status_code == 404
    assert ShoppingTrip.objects.exists()


def test_stray_trip_removal_is_post_only_and_for_members() -> None:
    camp = make_camp()
    trip = ShoppingTrip.objects.create(camp=camp, date=datetime.date(2026, 7, 20))
    url = reverse("remove_outside_trip", args=[camp.pk, trip.pk])
    assert member_client(camp).get(url).status_code == 405
    assert _foreign_client().post(url).status_code == 404
    assert Client().post(url).status_code == 302
    assert ShoppingTrip.objects.exists()


def test_quick_add_returns_the_new_ingredient() -> None:
    response = account_client().post(
        reverse("ingredient_quick_add"), _quick_add_data(price="1.5")
    )
    ingredient = Ingredient.objects.get()
    assert response.status_code == 201
    assert response.json() == {
        "id": ingredient.pk,
        "label": "Wortel (kg)",
        "unit": KG,
    }
    assert ingredient.prices.get().price == Decimal("1.5")


def test_quick_add_reports_errors_as_json() -> None:
    Ingredient.objects.create(name="Wortel", unit=KG)
    response = account_client().post(
        reverse("ingredient_quick_add"), _quick_add_data(name="wortel")
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["errors"]["name"][0]["message"]
    assert Ingredient.objects.count() == 1


def test_quick_add_needs_an_account_and_post() -> None:
    url = reverse("ingredient_quick_add")
    assert Client().post(url, _quick_add_data()).status_code == 302
    assert account_client().get(url).status_code == 405
    assert not Ingredient.objects.exists()


def test_recipe_form_has_the_dialog_with_its_own_field_names() -> None:
    content = account_client().get(reverse("recipe_create")).content.decode()
    assert 'id="new-ingredient-dialog"' in content
    assert 'name="new_ingredient-name"' in content
    assert 'name="name"' in content
    assert "js/recipe_form.js" in content
