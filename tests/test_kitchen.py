"""Kitchen utilities: the Chiro's stock, a camp's needs and bills
(docs/spec/kitchen.md)."""

from decimal import Decimal

import pytest
from django.urls import reverse

from accounts.models import Chiro
from bills.models import Bill, BillLine
from bills.services import camp_spending
from camps.models import Camp
from kitchen.models import CampUtensil, Utensil
from tests.factories import account_client, make_camp, member_client

pytestmark = pytest.mark.django_db


@pytest.fixture
def camp() -> Camp:
    return make_camp()


@pytest.fixture
def pot(camp: Camp) -> Utensil:
    return Utensil.objects.create(chiro=camp.chiro, name="Kookpot 50 L", in_stock=3)


def _stock_data(rows: list[dict], initial: int = 0) -> dict:
    data = {"form-TOTAL_FORMS": str(len(rows)), "form-INITIAL_FORMS": str(initial)}
    for index, row in enumerate(rows):
        for field, value in row.items():
            data[f"form-{index}-{field}"] = value
    return data


def _needs_data(rows: list[tuple[str, int]]) -> dict:
    return _stock_data([{"name": name, "needed": needed} for name, needed in rows])


def test_members_keep_the_chiros_stock(camp) -> None:
    client = member_client(camp)
    url = reverse("chiro_stock", args=[camp.chiro.pk])
    response = client.post(
        url,
        _stock_data([{"name": "Vuurkorf", "in_stock": "2", "note": "in de kelder"}]),
    )
    assert response.status_code == 302
    fire_pit = Utensil.objects.get()
    assert (fire_pit.chiro, fire_pit.in_stock) == (camp.chiro, 2)
    assert "Vuurkorf" in client.get(url).content.decode()


def test_other_chiros_cannot_see_the_stock(camp) -> None:
    url = reverse("chiro_stock", args=[camp.chiro.pk])
    assert account_client().get(url).status_code == 404


def test_stock_names_are_unique_without_case(camp) -> None:
    response = member_client(camp).post(
        reverse("chiro_stock", args=[camp.chiro.pk]),
        _stock_data(
            [
                {"name": "Pollepel", "in_stock": "1"},
                {"name": "pollepel", "in_stock": "2"},
            ]
        ),
    )
    assert response.status_code == 200
    assert not Utensil.objects.exists()


def test_an_item_a_camp_needs_cannot_be_removed(camp, pot) -> None:
    CampUtensil.objects.create(camp=camp, utensil=pot, needed=5)
    response = member_client(camp).post(
        reverse("chiro_stock", args=[camp.chiro.pk]),
        _stock_data(
            [{"id": pot.pk, "name": pot.name, "in_stock": "3", "DELETE": "on"}],
            initial=1,
        ),
    )
    assert response.status_code == 200
    assert "Test Camp" in response.content.decode()
    assert Utensil.objects.filter(pk=pot.pk).exists()


def test_camp_needs_are_compared_with_the_stock(camp, pot) -> None:
    client = member_client(camp)
    url = reverse("camp_utensils", args=[camp.pk])
    response = client.post(url, _needs_data([("kookpot 50 l", 5), ("Gasvuur", 2)]))
    assert response.status_code == 302
    # A known name finds the stock item; a new one joins the stock with none in it.
    burner = Utensil.objects.get(name="Gasvuur")
    assert (burner.chiro, burner.in_stock) == (camp.chiro, 0)
    to_buy = {need.utensil.name: need.to_buy for need in camp.utensil_needs.all()}
    assert to_buy == {"Kookpot 50 L": 2, "Gasvuur": 2}
    shopping = client.get(reverse("shopping", args=[camp.pk])).content.decode()
    assert "Gasvuur" in shopping


def test_camp_needs_reject_a_name_twice(camp) -> None:
    response = member_client(camp).post(
        reverse("camp_utensils", args=[camp.pk]),
        _needs_data([("Pan", 1), ("pan", 2)]),
    )
    assert response.status_code == 200
    assert not CampUtensil.objects.exists()


def test_saving_needs_replaces_them(camp, pot) -> None:
    CampUtensil.objects.create(camp=camp, utensil=pot, needed=5)
    client = member_client(camp)
    client.post(reverse("camp_utensils", args=[camp.pk]), _needs_data([]))
    assert not CampUtensil.objects.exists()
    assert Utensil.objects.filter(pk=pot.pk).exists()  # the stock stays


def test_shopping_pdf_lists_utilities_to_buy(camp, pot, monkeypatch) -> None:
    monkeypatch.setattr("core.pdf.weasyprint_available", lambda: False)
    CampUtensil.objects.create(camp=camp, utensil=pot, needed=4)
    content = member_client(camp).get(reverse("shopping_pdf", args=[camp.pk]))
    assert "Kookpot 50 L" in content.content.decode()


def _bill_with_line(camp: Camp, **line) -> Bill:
    bill = Bill.objects.create(camp=camp, shop="colruyt", status=Bill.Status.REVIEW)
    bill.lines.create(
        **{"description": "KOOKPOT INOX", "line_total": Decimal("40.00"), **line}
    )
    return bill


def _review(bill: Bill, **fields) -> dict:
    line = bill.lines.get()
    data = {
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "1",
        "form-0-id": line.pk,
        "form-0-description": line.description,
        "form-0-quantity": line.quantity,
        "form-0-line_total": line.line_total,
        "form-0-category": BillLine.Category.UTENSILS,
    }
    data.update({f"form-0-{field}": value for field, value in fields.items()})
    return data


def test_a_bought_utility_goes_into_the_stock_once(camp) -> None:
    bill = _bill_with_line(camp, quantity=Decimal("2"))
    client = member_client(camp)
    url = reverse("bill_detail", args=[camp.pk, bill.pk])
    assert client.post(url, _review(bill, stock="new")).status_code == 302
    utensil = Utensil.objects.get()
    assert (utensil.name, utensil.in_stock) == ("KOOKPOT INOX", 2)
    # Saving the review again doesn't count it twice.
    assert client.post(url, _review(bill, stock="new")).status_code == 302
    utensil.refresh_from_db()
    assert utensil.in_stock == 2
    assert bill.lines.get().utensil == utensil


def test_a_bought_utility_adds_to_an_existing_item(camp, pot) -> None:
    bill = _bill_with_line(camp)
    client = member_client(camp)
    client.post(
        reverse("bill_detail", args=[camp.pk, bill.pk]), _review(bill, stock=pot.pk)
    )
    pot.refresh_from_db()
    assert pot.in_stock == 4


def test_only_kitchen_utilities_go_into_the_stock(camp, pot) -> None:
    bill = _bill_with_line(camp)
    response = member_client(camp).post(
        reverse("bill_detail", args=[camp.pk, bill.pk]),
        _review(bill, stock=pot.pk, category=BillLine.Category.ACTIVITY),
    )
    assert response.status_code == 200
    pot.refresh_from_db()
    assert pot.in_stock == 3


def test_another_chiros_item_cannot_be_chosen(camp) -> None:
    other = Utensil.objects.create(
        chiro=Chiro.objects.create(name="Other"), name="Pan", in_stock=1
    )
    bill = _bill_with_line(camp)
    response = member_client(camp).post(
        reverse("bill_detail", args=[camp.pk, bill.pk]), _review(bill, stock=other.pk)
    )
    assert response.status_code == 200
    other.refresh_from_db()
    assert other.in_stock == 1


def test_utilities_have_their_own_total(camp) -> None:
    _bill_with_line(camp, category=BillLine.Category.UTENSILS)
    spending = camp_spending(camp)
    assert spending.food == 0
    assert dict(spending.by_category)["Kitchen utilities"] == Decimal("40.00")


def test_bill_review_offers_a_new_ingredient_per_line(camp) -> None:
    bill = _bill_with_line(camp)
    html = (
        member_client(camp)
        .get(reverse("bill_detail", args=[camp.pk, bill.pk]))
        .content.decode()
    )
    assert 'id="new-ingredient-dialog"' in html
    assert 'data-select="form-0-ingredient"' in html
    # The script reads this selector as is: quotes inside it once broke it.
    assert 'data-selects="select[name^=form-][name$=-ingredient]"' in html
    assert "js/ingredient_dialog.js" in html
