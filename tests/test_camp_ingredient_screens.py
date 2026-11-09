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
        "groups-TOTAL_FORMS": "0",
        "groups-INITIAL_FORMS": "0",
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
        "price": "",
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
    response = client.post(reverse("ingredient_create"), _ingredient_data(price="1.20"))
    assert response.status_code == 302
    ingredient = Ingredient.objects.get()
    assert ingredient.name == "Wortel"
    assert ingredient.prices.get().price == Decimal("1.20")
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
        reverse("ingredient_create"), _ingredient_data(price="-1")
    )
    assert response.status_code == 200
    assert not Ingredient.objects.exists()


def test_edit_adds_a_price_but_keeps_name_and_unit() -> None:
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)

    response = account_client().post(
        reverse("ingredient_edit", args=[ingredient.pk]),
        _ingredient_data(name="Kaas", unit=PIECE, price="2.50"),
    )

    assert response.status_code == 302
    ingredient.refresh_from_db()
    assert ingredient.name == "Wortel"
    assert ingredient.unit == KG
    price = ingredient.prices.get()
    assert price.price == Decimal("2.50")
    assert price.created_by.username == "kok"
    assert price.camp is None


def test_new_price_goes_into_the_history() -> None:
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)
    client = account_client()
    url = reverse("ingredient_edit", args=[ingredient.pk])
    client.post(url, _ingredient_data(price="1.20"))
    client.post(url, _ingredient_data(price="1.50"))

    assert [p.price for p in ingredient.prices.all()] == [
        Decimal("1.50"),
        Decimal("1.20"),
    ]
    content = client.get(url).content.decode()
    assert "Price history" in content and "1.20" in content
    listing = Ingredient.objects.with_latest_price().get(pk=ingredient.pk)
    assert listing.latest_price == Decimal("1.50")


def test_empty_or_same_price_adds_nothing() -> None:
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)
    ingredient.prices.create(price=Decimal("1.2000"))
    client = account_client()
    url = reverse("ingredient_edit", args=[ingredient.pk])

    client.post(url, _ingredient_data(price="", product_details="Boni"))
    client.post(url, _ingredient_data(price="1.20", product_details="Boni"))

    ingredient.refresh_from_db()
    assert ingredient.product_details == "Boni"
    assert ingredient.prices.count() == 1


def test_ingredient_admin_pages_work() -> None:
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)
    ingredient.prices.create(price=Decimal("3"))
    client = Client()
    client.force_login(User.objects.create_superuser("baas"))
    assert client.get("/admin/recipes/ingredient/").status_code == 200
    change = f"/admin/recipes/ingredient/{ingredient.pk}/change/"
    assert client.get(change).status_code == 200


def test_same_price_on_a_later_day_confirms_it() -> None:
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)
    ingredient.prices.create(price=Decimal("1.20"), date=datetime.date(2026, 3, 1))
    account_client().post(
        reverse("ingredient_edit", args=[ingredient.pk]),
        _ingredient_data(price="1.20"),
    )
    assert ingredient.prices.count() == 2
    assert ingredient.prices.first().date > datetime.date(2026, 3, 1)


def test_admin_price_records_who_added_it() -> None:
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)
    client = Client()
    client.force_login(User.objects.create_superuser("baas"))
    response = client.post(
        f"/admin/recipes/ingredient/{ingredient.pk}/change/",
        {
            **_ingredient_data(),
            "prices-TOTAL_FORMS": "1",
            "prices-INITIAL_FORMS": "0",
            "prices-0-price": "3",
            "prices-0-source": "manual",
            "prices-0-date": "2026-11-01",
        },
    )
    assert response.status_code == 302
    price = ingredient.prices.get()
    assert price.created_by.username == "baas"
    assert price.unit == KG


def test_ingredient_with_camp_prices_cannot_be_deleted() -> None:
    camp = make_camp()
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)
    price = ingredient.prices.create(price=Decimal("1"), camp=camp)
    client = account_client()
    url = reverse("ingredient_delete", args=[ingredient.pk])

    assert client.post(url).status_code == 409
    assert Ingredient.objects.filter(pk=ingredient.pk).exists()

    price.camp = None
    price.save()
    assert client.post(url).status_code == 302
    assert not Ingredient.objects.filter(pk=ingredient.pk).exists()
