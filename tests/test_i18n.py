"""Dutch and English: picking a language, and what changes with it (docs/SPEC.md)."""

import datetime
from decimal import Decimal

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import translation

from core.constants import DishType, MealType, Unit
from core.portions import format_quantity
from pages.views import DOCS
from tests.factories import KG, PRODUCE, assign, make_camp, make_recipe, member_client

pytestmark = pytest.mark.django_db


def test_browser_language_picks_dutch() -> None:
    content = Client(headers={"accept-language": "nl-BE,nl;q=0.9"}).get("/")
    html = content.content.decode()
    assert '<html lang="nl"' in html
    assert "Inloggen" in html
    assert "Log in" not in html


def test_dutch_without_a_browser_preference(settings) -> None:
    settings.LANGUAGE_CODE = "nl"
    assert "Inloggen" in Client().get("/").content.decode()


def test_switch_language_without_logging_in() -> None:
    client = Client(headers={"accept-language": "nl"})
    response = client.post(reverse("set_language"), {"language": "en", "next": "/"})
    assert response.status_code == 302
    assert response.cookies[settings.LANGUAGE_COOKIE_NAME].value == "en"
    assert "Log in" in client.get("/").content.decode()


def test_header_offers_both_languages() -> None:
    html = Client().get("/").content.decode()
    assert 'name="language" value="nl"' in html
    assert 'name="language" value="en"' in html


@pytest.mark.parametrize("slug", DOCS)
def test_every_doc_has_a_dutch_version(slug: str) -> None:
    client = Client()
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "nl"
    dutch = client.get(reverse("doc", args=[slug])).content.decode()
    english = Client().get(reverse("doc", args=[slug])).content.decode()
    assert dutch != english
    assert "Aan de slag" in dutch  # the table of contents is translated too


def test_planner_in_dutch() -> None:
    camp = make_camp()
    recipe = make_recipe(
        "Stoofpot",
        dish_type=DishType.HOT_MEAL,
        teens=13,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    assign(camp, datetime.date(2026, 8, 1), MealType.DINNER, recipe)
    client = member_client(camp)
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "nl"
    html = client.get(reverse("planner", args=[camp.pk])).content.decode()
    assert "Ontbijt" in html
    assert "Avondmaal" in html
    assert "hoofdgerecht" in html
    assert "za 1 aug" in html  # Dutch day names


def test_choices_and_quantities_follow_the_language() -> None:
    labels = dict(Unit.CHOICES)
    with translation.override("nl"):
        assert labels[Unit.PIECE] == "stuk"
        assert format_quantity(Decimal("2.500")) == "2,5"
    with translation.override("en"):
        assert labels[Unit.PIECE] == "piece"
        assert format_quantity(Decimal("2.500")) == "2.5"


def test_recipe_scaling_link_keeps_a_decimal_point() -> None:
    """The page shows 12,5 in Dutch, but the input and URL need 12.5."""
    camp = make_camp()
    recipe = make_recipe("Soep", dish_type=DishType.SOUP, teens=10, ingredients=[])
    client = member_client(camp)
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "nl"
    url = reverse("recipe_detail", args=[recipe.pk])
    html = client.get(url, {"portions": "12.5"}).content.decode()
    assert 'value="12.5"' in html
    assert "?portions=12.5" in html
