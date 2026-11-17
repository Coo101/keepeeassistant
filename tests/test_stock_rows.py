""" "Add a row" on the pantry and on a camp's kitchen utilities: in place through
HTMX, or by posting the form without JavaScript (docs/spec/kitchen.md)."""

import pytest
from django.urls import reverse

from accounts.models import Chiro
from camps.models import Camp
from core.constants import IngredientCategory, Unit
from kitchen.services import camp_needs
from recipes.models import Ingredient
from shopping.models import PantryItem
from tests.factories import account_client, make_camp, member_client

pytestmark = pytest.mark.django_db


@pytest.fixture
def camp() -> Camp:
    return make_camp()


@pytest.fixture
def rice() -> Ingredient:
    return Ingredient.objects.create(
        name="Rijst", unit=Unit.KG, category=IngredientCategory.DRY_GOODS
    )


@pytest.fixture
def example_camp() -> Camp:
    return make_camp(chiro=Chiro.objects.create(name="Voorbeeld", is_example=True))


def _pantry_row_url(chiro: Chiro, total: str) -> str:
    return reverse("pantry_row", args=[chiro.pk]) + f"?pantry-TOTAL_FORMS={total}"


def _utensil_row_url(camp: Camp, total: str) -> str:
    return reverse("camp_utensil_row", args=[camp.pk]) + f"?form-TOTAL_FORMS={total}"


def test_pantry_row_gets_the_next_index(camp, rice) -> None:
    html = member_client(camp).get(_pantry_row_url(camp.chiro, "4")).content.decode()
    assert 'name="pantry-4-ingredient"' in html
    assert ">Rijst" in html
    assert 'id="id_pantry-TOTAL_FORMS"' in html
    assert 'value="5"' in html
    assert "hx-swap-oob" in html


def test_camp_utensil_row_gets_the_next_index(camp) -> None:
    html = member_client(camp).get(_utensil_row_url(camp, "3")).content.decode()
    assert 'name="form-3-name"' in html
    assert 'list="utensil-names"' in html
    assert 'id="id_form-TOTAL_FORMS"' in html
    assert 'value="4"' in html


def test_row_index_is_bounded(camp) -> None:
    client = member_client(camp)
    assert (
        'name="form-0-name"'
        in client.get(_utensil_row_url(camp, "abc")).content.decode()
    )
    assert (
        'name="form-1000-name"'
        in client.get(_utensil_row_url(camp, "999999")).content.decode()
    )


def test_pantry_add_row_without_javascript_keeps_what_was_typed(camp, rice) -> None:
    response = member_client(camp).post(
        reverse("chiro_stock", args=[camp.chiro.pk]),
        {
            "section": "pantry",
            "add_row": "pantry",
            "pantry-TOTAL_FORMS": "2",
            "pantry-INITIAL_FORMS": "0",
            "pantry-0-ingredient": str(rice.pk),
            "pantry-0-quantity": "2",
            "pantry-1-quantity": "abc",
        },
    )
    assert response.status_code == 200
    assert not PantryItem.objects.exists()
    html = response.content.decode()
    assert 'name="pantry-0-quantity" value="2"' in html
    assert 'name="pantry-2-ingredient"' in html
    assert "alert-danger" not in html


def test_camp_utensils_add_row_without_javascript(camp) -> None:
    response = member_client(camp).post(
        reverse("camp_utensils", args=[camp.pk]),
        {
            "add_row": "form",
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-0-name": "Vuurkorf",
            "form-0-needed": "2",
        },
    )
    assert response.status_code == 200
    assert camp_needs(camp) == []
    html = response.content.decode()
    assert 'value="Vuurkorf"' in html
    assert 'name="form-1-name"' in html


def test_rows_on_an_example_are_readable_but_add_row_posts_are_refused(
    camp, example_camp
) -> None:
    client = member_client(camp)
    assert client.get(_pantry_row_url(example_camp.chiro, "0")).status_code == 200
    assert client.get(_utensil_row_url(example_camp, "0")).status_code == 200
    stock = client.post(
        reverse("chiro_stock", args=[example_camp.chiro.pk]),
        {
            "section": "pantry",
            "add_row": "pantry",
            "pantry-TOTAL_FORMS": "0",
            "pantry-INITIAL_FORMS": "0",
        },
    )
    utensils = client.post(
        reverse("camp_utensils", args=[example_camp.pk]),
        {"add_row": "form", "form-TOTAL_FORMS": "0", "form-INITIAL_FORMS": "0"},
    )
    assert (stock.status_code, utensils.status_code) == (403, 403)


def test_row_urls_need_access(camp) -> None:
    other = account_client("buiten")
    assert other.get(_utensil_row_url(camp, "0")).status_code == 404
    assert other.get(_pantry_row_url(camp.chiro, "0")).status_code == 404
