"""Camp and ingredient screens outside the admin (SPEC §9.2, §9.6)."""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from accounts.models import Chiro, Membership
from camps.models import Camp
from core.constants import IngredientCategory, Shop
from recipes.models import Ingredient
from tests.factories import KG, PIECE, account_client, make_camp, member_client

pytestmark = pytest.mark.django_db


def _camp_data(chiro: Chiro | None = None, **extra) -> dict:
    data = {
        "name": "Zomerkamp",
        "start_date": "2027-07-01",
        "end_date": "2027-07-10",
        "num_children": "20",
        "num_teens": "30",
        "num_staff": "8",
        "breakfast_time": "08:00",
        "lunch_time": "12:30",
        "teatime_time": "16:00",
        "dinner_time": "18:30",
    }
    if chiro:
        data["chiro"] = chiro.pk
    return {**data, **extra}


def _ingredient_data(**extra) -> dict:
    return {
        "name": "Wortel",
        "unit": KG,
        "category": IngredientCategory.PRODUCE,
        "shop": Shop.COLRUYT,
        "price_per_unit": "",
        "product_details": "",
        **extra,
    }


def _client_in(*chiros: Chiro) -> Client:
    client = account_client()
    user = User.objects.get(username="kok")
    for chiro in chiros:
        Membership.objects.create(user=user, chiro=chiro)
    return client


@pytest.fixture
def chiro() -> Chiro:
    return Chiro.objects.create(name="Chiro Opoeteren")


@pytest.fixture
def other_chiro() -> Chiro:
    return Chiro.objects.create(name="Andere Chiro")


def test_member_creates_a_camp_for_their_only_chiro(chiro: Chiro) -> None:
    client = _client_in(chiro)
    url = reverse("camp_create")
    assert 'type="hidden" name="chiro"' in client.get(url).content.decode()

    response = client.post(url, _camp_data(chiro))

    camp = Camp.objects.get()
    assert camp.chiro == chiro
    assert response["Location"] == reverse("planner", args=[camp.pk])


def test_member_of_two_chiros_picks_one(chiro: Chiro, other_chiro: Chiro) -> None:
    client = _client_in(chiro, other_chiro)
    url = reverse("camp_create")
    assert '<select name="chiro"' in client.get(url).content.decode()
    assert client.post(url, _camp_data()).status_code == 200
    assert client.post(url, _camp_data(other_chiro)).status_code == 302
    assert Camp.objects.get().chiro == other_chiro


def test_cannot_create_a_camp_for_someone_elses_chiro(
    chiro: Chiro, other_chiro: Chiro
) -> None:
    client = _client_in(chiro)
    response = client.post(reverse("camp_create"), _camp_data(other_chiro))
    assert response.status_code == 200
    assert not Camp.objects.exists()


def test_account_without_chiro_cannot_create_a_camp(chiro: Chiro) -> None:
    client = account_client()
    url = reverse("camp_create")
    assert client.get(url).status_code == 403
    assert client.post(url, _camp_data(chiro)).status_code == 403
    assert not Camp.objects.exists()
    list_page = client.get(reverse("camp_list")).content.decode()
    assert url not in list_page
    assert "isn't linked to a Chiro" in list_page


def test_camp_end_date_must_follow_start_date(chiro: Chiro) -> None:
    client = _client_in(chiro)
    response = client.post(
        reverse("camp_create"), _camp_data(chiro, end_date="2027-06-01")
    )
    assert response.status_code == 200
    assert "End date must be on or after start date." in response.content.decode()
    assert not Camp.objects.exists()


def test_edit_shows_saved_values_and_saves_changes() -> None:
    camp = make_camp()
    client = member_client(camp)
    url = reverse("camp_edit", args=[camp.pk])
    content = client.get(url).content.decode()
    assert 'value="2026-08-01"' in content
    assert 'value="08:00"' in content

    response = client.post(url, _camp_data(cook_team="Jan 0470"))

    camp.refresh_from_db()
    assert response.status_code == 302
    assert camp.name == "Zomerkamp"
    assert camp.start_date == datetime.date(2027, 7, 1)
    assert camp.cook_team == "Jan 0470"


def test_edit_cannot_move_a_camp_to_another_chiro(other_chiro: Chiro) -> None:
    camp = make_camp()
    original = camp.chiro
    client = member_client(camp)
    url = reverse("camp_edit", args=[camp.pk])

    assert 'name="chiro"' not in client.get(url).content.decode()
    client.post(url, _camp_data(other_chiro))

    camp.refresh_from_db()
    assert camp.chiro == original


def test_ingredients_need_an_account() -> None:
    response = Client().get(reverse("ingredient_list"))
    assert response.status_code == 302
    assert reverse("login") in response["Location"]


def test_account_without_chiro_can_add_an_ingredient() -> None:
    client = account_client()
    response = client.post(
        reverse("ingredient_create"), _ingredient_data(price_per_unit="1.20")
    )
    assert response.status_code == 302
    ingredient = Ingredient.objects.get()
    assert ingredient.name == "Wortel"
    assert ingredient.price_updated is not None
    assert "Wortel" in client.get(reverse("ingredient_list")).content.decode()


def test_ingredient_list_search() -> None:
    Ingredient.objects.create(name="Wortel", unit=KG, product_details="Boni bio")
    Ingredient.objects.create(name="Kaas", unit=KG)
    client = account_client()
    url = reverse("ingredient_list")

    for query in ("wort", "boni"):
        content = client.get(url, {"q": query}).content.decode()
        assert "Wortel" in content and "Kaas" not in content


def test_ingredient_name_is_unique_ignoring_case() -> None:
    Ingredient.objects.create(name="Wortel", unit=KG)
    response = account_client().post(
        reverse("ingredient_create"), _ingredient_data(name="wortel")
    )
    assert response.status_code == 200
    assert "already exists" in response.content.decode()
    assert Ingredient.objects.count() == 1


def test_negative_price_is_rejected() -> None:
    response = account_client().post(
        reverse("ingredient_create"), _ingredient_data(price_per_unit="-1")
    )
    assert response.status_code == 200
    assert not Ingredient.objects.exists()


def test_edit_changes_price_but_not_name_or_unit() -> None:
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)

    response = account_client().post(
        reverse("ingredient_edit", args=[ingredient.pk]),
        _ingredient_data(name="Kaas", unit=PIECE, price_per_unit="2.50"),
    )

    assert response.status_code == 302
    ingredient.refresh_from_db()
    assert ingredient.name == "Wortel"
    assert ingredient.unit == KG
    assert ingredient.price_per_unit == Decimal("2.50")
    assert ingredient.price_updated is not None


def test_price_updated_only_moves_when_the_price_changes() -> None:
    ingredient = Ingredient.objects.create(
        name="Wortel", unit=KG, price_per_unit=Decimal("1.2000")
    )
    account_client().post(
        reverse("ingredient_edit", args=[ingredient.pk]),
        _ingredient_data(price_per_unit="1.20", product_details="Boni"),
    )
    ingredient.refresh_from_db()
    assert ingredient.product_details == "Boni"
    assert ingredient.price_updated is None


def test_admin_sets_price_updated() -> None:
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)
    client = Client()
    client.force_login(User.objects.create_superuser("baas"))
    response = client.post(
        f"/admin/recipes/ingredient/{ingredient.pk}/change/",
        _ingredient_data(price_per_unit="3"),
    )
    assert response.status_code == 302
    ingredient.refresh_from_db()
    assert ingredient.price_updated is not None
