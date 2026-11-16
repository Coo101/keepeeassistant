"""The financial report and the example camp
(docs/spec/finance.md, docs/spec/accounts.md)."""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse

from accounts.models import Chiro
from bills.models import Bill, BillLine
from bills.report import build_report
from bills.services import apply_review
from camps.models import Camp
from core.constants import DishType, MealType
from recipes.models import Ingredient, IngredientPrice, Recipe
from recipes.prices import resolve_prices
from tests.factories import (
    DRY,
    KG,
    PRODUCE,
    account_client,
    assign,
    make_camp,
    make_recipe,
    member_client,
    set_price,
)

pytestmark = pytest.mark.django_db

AUG_1 = datetime.date(2026, 8, 1)


@pytest.fixture
def camp() -> Camp:
    camp = make_camp()  # 52 portions
    stew = make_recipe(
        "Stoofpot",
        teens=13,  # x4
        ingredients=[("Potatoes", "2.5", KG, PRODUCE), ("Salt", "0.1", KG, DRY)],
    )
    assign(camp, AUG_1, MealType.DINNER, stew)
    return camp


def _bill(camp: Camp, *lines: tuple) -> Bill:
    """lines: (description, ingredient name or None, quantity, total, category)."""
    bill = Bill.objects.create(camp=camp, shop="colruyt", date=AUG_1)
    for description, name, quantity, total, category in lines:
        bill.lines.create(
            description=description,
            ingredient=Ingredient.objects.get(name=name) if name else None,
            quantity=Decimal(quantity),
            pack_amount=Decimal("1") if name else None,
            line_total=Decimal(total),
            category=category,
        )
    apply_review(bill)
    return bill


FOOD = BillLine.Category.FOOD


def test_meal_cost_uses_the_bill_prices(camp) -> None:
    _bill(
        camp,
        ("AARDAPPELEN", "Potatoes", "10", "15.00", FOOD),  # 1.50/kg
        ("ZOUT", "Salt", "1", "0.80", FOOD),
    )
    report = build_report(camp)
    meal = report.days[0].meals[0]
    # 10 kg potatoes x 1.50 + 0.4 kg salt x 0.80
    assert meal.cost == Decimal("15.32")
    assert meal.per_portion == Decimal("0.29")
    assert not meal.estimated
    assert report.is_complete
    assert report.planned_total == Decimal("15.32")
    assert report.not_explained == Decimal("15.80") - Decimal("15.32")


def test_ingredients_missing_from_the_bills_are_estimated(camp) -> None:
    _bill(camp, ("AARDAPPELEN", "Potatoes", "10", "15.00", FOOD))
    set_price("Salt", "1.00")  # a general price, not from this camp's bills
    report = build_report(camp)
    assert [i.name for i in report.not_in_bills] == ["Salt"]
    assert report.days[0].meals[0].estimated
    assert report.days[0].meals[0].cost == Decimal("15.40")
    assert not report.is_complete


def test_ingredients_without_any_price_are_left_out(camp) -> None:
    _bill(camp, ("AARDAPPELEN", "Potatoes", "10", "15.00", FOOD))
    report = build_report(camp)
    assert [i.name for i in report.unpriced] == ["Salt"]
    assert report.days[0].meals[0].unpriced == ["Salt"]
    assert report.days[0].meals[0].cost == Decimal("15.00")


def test_open_bills_make_the_report_incomplete(camp) -> None:
    Bill.objects.create(camp=camp, shop="colruyt", status=Bill.Status.REVIEW)
    assert build_report(camp).spending.open_bills == 1


def test_personal_costs_stay_apart(camp) -> None:
    _bill(
        camp,
        ("AARDAPPELEN", "Potatoes", "10", "15.00", FOOD),
        ("FRISDRANK LEIDING", None, "1", "9.20", BillLine.Category.PERSONAL),
    )
    report = build_report(camp)
    assert [line.description for line in report.personal_lines] == ["FRISDRANK LEIDING"]
    assert report.personal_total == Decimal("9.20")
    assert report.spending.food == Decimal("15.00")


def test_report_page_and_pdf(camp, monkeypatch) -> None:
    monkeypatch.setattr("core.pdf.weasyprint_available", lambda: False)
    _bill(camp, ("FRISDRANK", None, "1", "9.20", BillLine.Category.PERSONAL))
    client = member_client(camp)
    for name in ["financial_report", "report_pdf"]:
        response = client.get(reverse(name, args=[camp.pk]))
        assert response.status_code == 200
        html = response.content.decode()
        assert "Stoofpot" in html
        assert "Personal costs" in html
        assert "FRISDRANK" in html


# --- the example camp


@pytest.fixture
def recipes() -> None:
    make_recipe("Boterhammen", dish_type=DishType.BREAD_MEAL, ingredients=[])
    make_recipe(
        "Spaghetti",
        dish_type=DishType.HOT_MEAL,
        ingredients=[("Pasta", "1", KG, DRY), ("Tomaten", "2", KG, PRODUCE)],
    )
    set_price("Pasta", "2.00")
    set_price("Tomaten", "3.00")


def _example() -> Camp:
    call_command("create_example_camp")
    return Camp.objects.get(chiro__is_example=True)


def test_example_camp_is_planned_and_paid(recipes) -> None:
    camp = _example()
    assert camp.menu_entries.exists()
    assert camp.bills.exists()
    assert not camp.bills.exclude(status=Bill.Status.DONE).exists()
    report = build_report(camp)
    assert report.personal_lines
    assert report.planned_total > 0


def test_everyone_sees_the_example_but_cannot_change_it(recipes) -> None:
    camp = _example()
    client = account_client("nieuw")
    assert "Voorbeeldkamp" in client.get(reverse("camp_list")).content.decode()
    url = reverse("camp_utensils", args=[camp.pk])
    assert client.get(url).status_code == 200
    refused = client.post(url, {})
    assert refused.status_code == 403
    assert "This is an example" in refused.content.decode()
    stock = reverse("chiro_stock", args=[camp.chiro.pk])
    assert client.get(stock).status_code == 200
    assert client.post(stock, {}).status_code == 403


def test_example_prices_are_not_anyones_estimate(recipes) -> None:
    example = _example()
    pasta = Ingredient.objects.get(name="Pasta")
    assert IngredientPrice.objects.filter(camp=example, ingredient=pasta).exists()
    other = make_camp(chiro=Chiro.objects.create(name="Echte Chiro"))
    assert resolve_prices(other, [pasta.pk])[pasta.pk].price == Decimal("2.00")
    listed = Ingredient.objects.with_latest_price().get(pk=pasta.pk)
    assert listed.latest_price == Decimal("2.00")


def test_example_does_not_lock_recipes(recipes) -> None:
    example = _example()
    # Still to come, so only its being an example keeps the recipe open.
    Camp.objects.filter(pk=example.pk).update(end_date=datetime.date(2099, 1, 1))
    spaghetti = Recipe.objects.get(name="Spaghetti")
    author = User.objects.create(username="auteur")
    spaghetti.author = author
    spaghetti.save()
    assert spaghetti.menuentry_set.filter(camp__chiro__is_example=True).exists()
    assert spaghetti.can_edit(author)


def test_reset_starts_over_without_leaving_prices(recipes) -> None:
    first = _example()
    call_command("create_example_camp", reset=True)
    assert not IngredientPrice.objects.filter(camp_id=first.pk).exists()
    assert IngredientPrice.objects.filter(camp=None).count() == 2
    assert Camp.objects.filter(chiro__is_example=True).count() == 1
