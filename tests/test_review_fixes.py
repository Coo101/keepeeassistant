"""Regression tests for the fixes from the project review (docs/TODO.md)."""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.urls import reverse

from accounts.models import Membership, Role
from core.constants import DishType, MealType
from planning.models import MenuEntry
from recipes.models import Ingredient, RecipeIngredient
from shopping.models import ShoppingTrip
from tests.factories import (
    KG,
    PIECE,
    PRODUCE,
    account_client,
    assign,
    make_camp,
    make_recipe,
    member_client,
)

pytestmark = pytest.mark.django_db

AUG = lambda d: datetime.date(2026, 8, d)  # noqa: E731
SECRET = "Jan 0470 12 34 56"


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-1", "abc"])
def test_invalid_portions_show_the_unscaled_recipe(value: str) -> None:
    recipe = make_recipe("Soep", ingredients=[("Wortel", "2", KG, PRODUCE)])
    response = account_client().get(
        reverse("recipe_detail", args=[recipe.pk]), {"portions": value}
    )
    assert response.status_code == 200
    assert response.context["scale"] is None


def test_seed_demo_refuses_outside_debug() -> None:
    with pytest.raises(CommandError, match="admin/admin"):
        call_command("seed_demo")
    assert not User.objects.filter(username="admin").exists()


@pytest.mark.parametrize("url_name", ["runbook", "runbook_pdf"])
def test_contact_details_shown_to_members(monkeypatch, url_name: str) -> None:
    # Force the HTML fallback so the rendered text can be inspected.
    monkeypatch.setattr("core.pdf.weasyprint_available", lambda: False)
    camp = make_camp()
    for field in (
        "cook_team",
        "location",
        "contact_leader",
        "contact_rental",
        "bakery",
        "general_notes",
    ):
        setattr(camp, field, f"{field}: {SECRET}")
    camp.save()
    url = reverse(url_name, args=[camp.pk])

    assert member_client(camp).get(url).content.decode().count(SECRET) == 6


def test_recipe_unit_must_match_the_ingredient() -> None:
    recipe = make_recipe("Soep")
    ingredient = Ingredient.objects.create(name="Wortel", unit=KG)
    wrong = RecipeIngredient(
        recipe=recipe, ingredient=ingredient, quantity=Decimal("1"), unit=PIECE
    )
    with pytest.raises(ValidationError) as error:
        wrong.full_clean()
    assert "unit" in error.value.message_dict
    wrong.unit = KG
    wrong.full_clean()


def test_pages_warn_about_entries_outside_the_camp_dates() -> None:
    camp = make_camp()  # Aug 1-5
    recipe = make_recipe("Stoofpot", dish_type=DishType.HOT_MEAL)
    assign(camp, AUG(5), MealType.DINNER, recipe)
    url_names = ("planner", "shopping")
    client = member_client(camp)
    for url_name in url_names:
        content = client.get(reverse(url_name, args=[camp.pk])).content.decode()
        assert "Planned outside the camp dates" not in content

    camp.end_date = AUG(2)
    camp.save()

    for url_name in url_names:
        content = client.get(reverse(url_name, args=[camp.pk])).content.decode()
        assert "Planned outside the camp dates" in content
        assert "Stoofpot" in content
    assert MenuEntry.objects.count() == 1


def test_saving_shopping_days_keeps_trips_outside_the_form() -> None:
    camp = make_camp()  # Aug 1-5; the form offers Jul 29 - Aug 5
    logged_in = member_client(camp)
    early = datetime.date(2026, 7, 20)
    ShoppingTrip.objects.create(camp=camp, date=early)
    ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    url = reverse("shopping", args=[camp.pk])

    logged_in.post(url, {"trip_dates": [AUG(3).isoformat()]})

    dates = set(camp.shopping_trips.values_list("date", flat=True))
    assert dates == {early, AUG(3)}
    assert "Shopping days outside the dates" in logged_in.get(url).content.decode()


def test_seed_demo_creates_a_plain_member(settings) -> None:
    settings.DEBUG = True
    call_command("seed_demo")
    call_command("seed_demo")
    member = User.objects.get(username="member")
    assert not member.is_staff
    assert not member.is_superuser
    assert member.check_password("member")
    memberships = Membership.objects.filter(user=member)
    assert memberships.count() == 1
    assert memberships.get().chiro.name == "Demo Chiro"
    assert memberships.get().role == Role.MEMBER
