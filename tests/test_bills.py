"""Bills: upload, reading, review, prices and access (SPEC §9.10)."""

import datetime
import io
import json
import urllib.error
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from PIL import Image

from accounts.models import Chiro, Role
from bills.models import Bill, BillLine, LineMatch
from bills.parsing import parse_pack, parse_text
from bills.reading import read_with_ollama
from bills.services import apply_review, camp_spending, store_parsed_bill
from camps.models import Camp
from core.constants import PriceSource, Shop, Unit
from recipes.models import Ingredient, IngredientPrice
from shopping.budget import build_budget
from tests.factories import KG, LITER, PIECE, make_camp, member_client

pytestmark = pytest.mark.django_db

BILL_TEXT = [
    "Colruyt Halle",
    "2 x BONI WORTEL 1KG 3,58",
    "MELK 6X1L 5,10",
    "LEEGGOED 0,50",
    "KORTING -1,00",
    "TOTAAL 8,18",
    "BTW 6% 0,46",
    "Bancontact 8,18",
]


def text_pdf(lines: list[str] = BILL_TEXT) -> bytes:
    """A small but valid PDF with real text."""
    body = "BT /F1 10 Tf 40 780 Td 14 TL " + " ".join(
        f"({line}) Tj T*" for line in lines
    )
    stream = body + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, content in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{content}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF"
    ).encode()
    return out


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


def upload(client: Client, camp: Camp, name="bill.pdf", content=None, **extra):
    return client.post(
        reverse("bill_list", args=[camp.pk]),
        {
            "file": SimpleUploadedFile(
                name, text_pdf() if content is None else content
            ),
            "shop": Shop.COLRUYT,
            "date": "2026-08-01",
            **extra,
        },
    )


def review_data(bill: Bill, **changes) -> dict:
    """The review form as it stands; changes are `<line index>_<field>`."""
    lines = list(bill.lines.all())
    data = {
        "form-TOTAL_FORMS": str(len(lines)),
        "form-INITIAL_FORMS": str(len(lines)),
    }
    for index, line in enumerate(lines):
        values = {
            "id": line.pk,
            "description": line.description,
            "quantity": line.quantity,
            "pack_amount": line.pack_amount or "",
            "line_total": line.line_total,
            "category": line.category,
            "ingredient": line.ingredient_id or "",
        }
        if line.skipped:
            values["skipped"] = "on"
        for field, value in values.items():
            data[f"form-{index}-{field}"] = value
    for key, value in changes.items():
        index, field = key.split("_", 1)
        data[f"form-{index}-{field}"] = value
    return data


@pytest.fixture
def camp() -> Camp:
    return make_camp()


@pytest.fixture
def client(camp: Camp) -> Client:
    return member_client(camp)


@pytest.fixture
def carrots() -> Ingredient:
    return Ingredient.objects.create(name="Wortel", unit=KG)


def test_parse_text_finds_lines_and_total() -> None:
    parsed = parse_text("\n".join(BILL_TEXT))
    assert [line.description for line in parsed.lines] == [
        "BONI WORTEL 1KG",
        "MELK 6X1L",
        "LEEGGOED",
        "KORTING",
    ]
    assert parsed.lines[0].quantity == 2
    assert parsed.lines[0].line_total == Decimal("3.58")
    assert [line.is_other for line in parsed.lines] == [False, False, True, True]
    assert parsed.printed_total == Decimal("8.18")


def test_parse_text_handles_quantity_and_unit_price_columns() -> None:
    (line,) = parse_text("BLOEM 3 1,20 3,60").lines
    assert line.description == "BLOEM"
    assert line.quantity == 3
    assert line.line_total == Decimal("3.60")


INVOICE_TEXT = [
    "BTW BE0123456789",
    "EENH. PRIJS EXC BEDRAG EXC",
    "BTW ART. NR OMSCHRIJVING HOEV.",
    "A 16840 BONI smeerkaas 24st 400g 10 2.54 25.38",
    "C 5021 CRISTAL pils 5.0%vol 24x25cl 2 12.69 25.37",
    "leeggoed 5021 2 4.50 9.00",
    "A000313903-SCP- Korting B0101843 33.34% -3.35",
    "S_0",
    "A 5154 VERSE KIPFILET ±1kg 15.084 6.60 99.60",
    "A 29809 trostomaten 5.000 1.09 5.47",
    "25633 WAARBORG PLUS BOX COGO 10 6.95 69.50",
    "A 9191 Servicekost Collect&Go 1 6.56 6.56",
    "Totale korting met Xtra: € 3.35",
    "BTW BEDRAG EXC BEDRAG BTW TOTAAL",
    "A 6% € 137.01 € 8.22 € 145.23",
    "C 21% € 25.37 € 5.33 € 30.70",
    "Totaal goederen € 162.38 € 13.55 € 175.93",
    "Totaal leeggoed € 78.50 € 0.00 € 78.50",
    "TOTAAL € 240.88 € 13.55 € 254.43",
    "Totaal bonnen € -3.55",
    "Te betalen: € 250.89",
    "14:07:47 Bancontact € 250.89",
]


def test_parse_text_reads_an_invoice_without_vat() -> None:
    parsed = parse_text("\n".join(INVOICE_TEXT))
    assert [
        (line.description, line.quantity, line.line_total, line.is_other)
        for line in parsed.lines
    ] == [
        ("BONI smeerkaas 24st 400g", 10, Decimal("26.90"), False),
        ("CRISTAL pils 5.0%vol 24x25cl", 2, Decimal("30.70"), False),
        ("leeggoed 5021", 2, Decimal("9.00"), True),
        ("Korting B0101843 33.34%", 1, Decimal("-3.55"), True),
        ("VERSE KIPFILET ±1kg", Decimal("15.084"), Decimal("105.58"), False),
        ("trostomaten", 5, Decimal("5.80"), False),
        ("WAARBORG PLUS BOX COGO", 10, Decimal("69.50"), True),
        ("Servicekost Collect&Go", 1, Decimal("6.95"), True),
        ("VAT rounding", 1, Decimal("0.01"), True),
    ]
    assert [line.weighed for line in parsed.lines[4:6]] == [True, True]
    assert parsed.printed_total == Decimal("250.89")
    assert sum(line.line_total for line in parsed.lines) == parsed.printed_total


def test_invoice_lines_keep_their_article_number() -> None:
    parsed = parse_text("\n".join(INVOICE_TEXT))
    assert [line.article for line in parsed.lines] == [
        "16840",
        "5021",
        "",  # a deposit that prints no article of its own
        "",  # a discount's promotion code isn't an article
        "5154",
        "29809",
        "25633",
        "9191",
        "",
    ]


def test_a_match_follows_the_article_number_when_the_name_changes(camp) -> None:
    cheese = Ingredient.objects.create(name="Smeerkaas", unit=KG)
    old = Bill.objects.create(camp=camp, shop=Shop.COLRUYT)
    store_parsed_bill(old, parse_text("\n".join(INVOICE_TEXT)))
    line = old.lines.get(article="16840")
    line.ingredient, line.pack_amount = cheese, Decimal("0.400")
    line.save()
    apply_review(old)
    assert LineMatch.objects.get(ingredient=cheese).key == "16840"

    renamed = "\n".join(INVOICE_TEXT).replace("BONI smeerkaas", "BONI kaasportie")
    new = Bill.objects.create(camp=camp, shop=Shop.COLRUYT)
    store_parsed_bill(new, parse_text(renamed))
    line = new.lines.get(article="16840")
    assert line.ingredient == cheese
    assert line.pack_amount == Decimal("0.400")


WHOLESALE_TEXT = [
    "Art. Nr. Omschrijving Aantal Eh Ehp Promo Subtotaal korting Totaal Code",
    "51640 BRANDPASTA BLIKJE 200G 4 CU 1,2354 4,94 5,00 4,69 21 %",
    "75467 NACHO SALSA MILD DIP 2 CU 1,8409 3,68 5,00 3,50 6 %",
    "300G",
    "37597 GEBAKKEN HAM 1/2 PPKG 2,424 WUK 11,9460 28,96 5,00 27,51 6 %",
    "962 VISTIP 24X125G 3 CU 28,4956 3,00 82,92 5,00 78,78 6 %",
    "Alle BIO producten van Inkoopcentra",
    "497,11 24,86 109,79 6,59 6 116,38 EUR",
    "4,94 0,25 4,69 0,98 21 5,67 EUR",
    "502,05 25,11 114,48 7,57 122,06 EUR",
]


def test_parse_text_reads_a_wholesale_invoice() -> None:
    parsed = parse_text("\n".join(WHOLESALE_TEXT))
    assert [
        (line.article, line.description, line.quantity, line.line_total, line.weighed)
        for line in parsed.lines
    ] == [
        ("51640", "BRANDPASTA BLIKJE 200G", 4, Decimal("5.67"), False),
        ("75467", "NACHO SALSA MILD DIP 300G", 2, Decimal("3.71"), False),
        ("37597", "GEBAKKEN HAM 1/2 PPKG", Decimal("2.424"), Decimal("29.16"), True),
        ("962", "VISTIP 24X125G", 3, Decimal("83.51"), False),
        ("", "VAT rounding", 1, Decimal("0.01"), False),
    ]
    assert parsed.printed_total == Decimal("122.06")
    assert sum(line.line_total for line in parsed.lines) == parsed.printed_total


def test_invoice_that_is_far_off_keeps_the_difference_visible() -> None:
    text = "\n".join(INVOICE_TEXT).replace(
        "Te betalen: € 250.89", "Te betalen: € 300.00"
    )
    parsed = parse_text(text)
    assert "VAT rounding" not in [line.description for line in parsed.lines]
    assert sum(line.line_total for line in parsed.lines) != parsed.printed_total


def test_invoice_lines_suggest_amounts(camp) -> None:
    chicken = Ingredient.objects.create(name="Kipfilet", unit=KG)
    cheese = Ingredient.objects.create(name="Smeerkaas", unit=KG)
    tomatoes = Ingredient.objects.create(name="Trostomaten", unit=KG)
    bill = Bill.objects.create(camp=camp, shop=Shop.COLRUYT)
    store_parsed_bill(bill, parse_text("\n".join(INVOICE_TEXT)))
    # The weight is the quantity, so one item is one kg of it.
    line = bill.lines.get(ingredient=chicken)
    assert (line.quantity, line.pack_amount) == (Decimal("15.084"), 1)
    assert line.unit_price == Decimal("6.9995")
    assert bill.lines.get(ingredient=tomatoes).pack_amount == 1
    # 400 g counts for a price per kg, not the 24 portions.
    assert bill.lines.get(ingredient=cheese).pack_amount == Decimal("0.400")


@pytest.mark.parametrize(
    ("text", "unit", "expected"),
    [
        ("KAAS 24ST 400G", Unit.KG, (Decimal("0.400"), Unit.KG)),
        ("KAAS 24ST 400G", Unit.PIECE, (Decimal("24"), Unit.PIECE)),
        ("KAAS 400G", Unit.LITER, None),
    ],
)
def test_parse_pack_in_a_unit(text: str, unit: str, expected) -> None:
    assert parse_pack(text, unit) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("WORTEL 1KG", (Decimal("1"), Unit.KG)),
        ("KAAS 500G", (Decimal("0.500"), Unit.KG)),
        ("COLA 6X1,5L", (Decimal("9.0"), Unit.LITER)),
        ("BIER 24 X 33CL", (Decimal("7.92"), Unit.LITER)),
        ("EIEREN 12 ST", (Decimal("12"), Unit.PIECE)),
        ("APPELS", None),
    ],
)
def test_parse_pack(text: str, expected) -> None:
    assert parse_pack(text) == expected


def test_upload_reads_a_text_pdf_and_changes_no_price(client, camp, carrots) -> None:
    response = upload(client, camp)

    bill = Bill.objects.get()
    assert response["Location"] == reverse("bill_detail", args=[camp.pk, bill.pk])
    assert bill.status == Bill.Status.REVIEW
    assert bill.printed_total == Decimal("8.18")
    assert bill.uploaded_by.username == "kok"
    assert "bill" not in Path(bill.file.name).name
    first, *_ = bill.lines.all()
    assert first.ingredient == carrots
    assert first.pack_amount == Decimal("1")
    assert not IngredientPrice.objects.exists()


def test_scan_without_text_waits_for_ollama(client, camp) -> None:
    upload(client, camp, name="photo.png", content=png_bytes())
    bill = Bill.objects.get()
    assert bill.status == Bill.Status.WAITING
    page = client.get(reverse("bill_detail", args=[camp.pk, bill.pk]))
    assert "Waiting to be read" in page.content.decode()


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("bill.exe", b"MZ"),
        ("bill.pdf", b"not a pdf"),
        ("bill.png", b"not an image"),
        ("bill.svg", b"<svg onload='alert(1)'/>"),
    ],
)
def test_upload_rejects_other_files(client, camp, name, content) -> None:
    assert upload(client, camp, name=name, content=content).status_code == 200
    assert not Bill.objects.exists()


def test_upload_page_shows_the_privacy_warning(client, camp) -> None:
    page = client.get(reverse("bill_list", args=[camp.pk])).content.decode()
    assert "Bills can hold personal data" in page
    assert "enctype=" in page


def test_review_sets_the_camps_price_and_remembers_the_match(
    client, camp, carrots
) -> None:
    upload(client, camp)
    bill = Bill.objects.get()

    # 2 bags of 1 kg for 3.58: 1.79/kg
    response = client.post(
        reverse("bill_detail", args=[camp.pk, bill.pk]),
        review_data(bill, **{"1_category": "activity"}),
    )

    assert response.status_code == 302
    price = IngredientPrice.objects.get()
    assert price.price == Decimal("1.79")
    assert price.camp == camp
    assert price.source == PriceSource.BILL
    assert price.date == datetime.date(2026, 8, 1)
    assert price.bill_line.bill == bill
    assert LineMatch.objects.get().ingredient == carrots
    bill.refresh_from_db()
    assert bill.status == Bill.Status.DONE


def test_a_second_bill_uses_the_remembered_match(client, camp, carrots) -> None:
    other = Ingredient.objects.create(name="Bio peen", unit=KG)
    upload(client, camp)
    bill = Bill.objects.get()
    client.post(
        reverse("bill_detail", args=[camp.pk, bill.pk]),
        review_data(
            bill,
            **{
                "0_ingredient": other.pk,
                "0_pack_amount": "2",
                "1_category": "personal",
            },
        ),
    )

    upload(client, camp, date="2026-08-03")

    newest = Bill.objects.order_by("-pk").first()
    first = newest.lines.first()
    assert first.ingredient == other
    assert first.pack_amount == Decimal("2")


def test_saving_again_updates_the_price_instead_of_adding_one(
    client, camp, carrots
) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    url = reverse("bill_detail", args=[camp.pk, bill.pk])
    client.post(url, review_data(bill, **{"1_category": "other"}))
    client.post(url, review_data(bill, **{"0_pack_amount": "2", "1_category": "other"}))

    assert IngredientPrice.objects.get().price == Decimal("0.895")


@pytest.mark.parametrize(
    "change", [{"0_category": "personal"}, {"0_skipped": "on"}, {"0_ingredient": ""}]
)
def test_undoing_a_line_removes_its_price(client, camp, carrots, change) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    url = reverse("bill_detail", args=[camp.pk, bill.pk])
    client.post(url, review_data(bill))
    assert IngredientPrice.objects.count() == 1

    client.post(url, review_data(bill, **change))

    assert not IngredientPrice.objects.exists()


def test_food_line_needs_an_amount(client, camp, carrots) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    response = client.post(
        reverse("bill_detail", args=[camp.pk, bill.pk]),
        review_data(bill, **{"0_pack_amount": ""}),
    )
    assert response.status_code == 200
    assert "How much is one item" in response.content.decode()
    assert not IngredientPrice.objects.exists()


def test_unmatched_food_line_keeps_the_bill_open(client, camp) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    client.post(reverse("bill_detail", args=[camp.pk, bill.pk]), review_data(bill))
    bill.refresh_from_db()
    assert bill.status == Bill.Status.REVIEW


def test_a_line_can_be_added_by_hand(client, camp, carrots) -> None:
    upload(client, camp, name="photo.png", content=png_bytes())
    bill = Bill.objects.get()
    response = client.post(
        reverse("bill_detail", args=[camp.pk, bill.pk]),
        {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-0-description": "Wortel 5 kg",
            "form-0-quantity": "1",
            "form-0-pack_amount": "5",
            "form-0-line_total": "6.00",
            "form-0-category": "food",
            "form-0-ingredient": carrots.pk,
        },
    )
    assert response.status_code == 302
    bill.refresh_from_db()
    assert bill.status == Bill.Status.DONE
    assert IngredientPrice.objects.get().price == Decimal("1.2")


def test_deleting_a_line_removes_its_price(client, camp, carrots) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    url = reverse("bill_detail", args=[camp.pk, bill.pk])
    client.post(url, review_data(bill))
    client.post(url, review_data(bill, **{"0_DELETE": "on"}))
    assert not IngredientPrice.objects.exists()
    assert bill.lines.count() == 3


def test_camp_budget_uses_a_price_from_a_bill_and_other_camps_do_not(
    client, camp, carrots
) -> None:
    other_camp = make_camp()
    carrots.prices.create(price=Decimal("5"), date=datetime.date(2026, 9, 1))
    upload(client, camp)
    bill = Bill.objects.get()
    client.post(reverse("bill_detail", args=[camp.pk, bill.pk]), review_data(bill))

    from recipes.prices import resolve_prices

    assert resolve_prices(camp, [carrots.pk])[carrots.pk].price == Decimal("1.79")
    assert resolve_prices(other_camp, [carrots.pk])[carrots.pk].price == Decimal("5")


def test_spending_splits_categories_and_only_food_compares(
    client, camp, carrots
) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    client.post(
        reverse("bill_detail", args=[camp.pk, bill.pk]),
        review_data(bill, **{"1_category": "activity"}),
    )
    spending = camp_spending(camp)
    categories = dict(spending.by_category)
    assert categories["Camp food"] == Decimal("3.58")
    assert categories["Activity"] == Decimal("5.10")
    assert categories["Other (deposit, discount, fee)"] == Decimal("-0.50")
    assert spending.total == Decimal("8.18")
    assert spending.food == Decimal("3.08")
    assert spending.shops[0].paid == Decimal("3.08")
    assert spending.open_bills == 0
    assert build_budget(camp).total == spending.estimate


def test_skipped_lines_count_for_nothing(client, camp, carrots) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    client.post(
        reverse("bill_detail", args=[camp.pk, bill.pk]),
        review_data(bill, **{"1_skipped": "on"}),
    )
    assert camp_spending(camp).total == Decimal("3.08")


def test_page_warns_when_lines_do_not_match_the_printed_total(client, camp) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    url = reverse("bill_detail", args=[camp.pk, bill.pk])
    assert "don't add up" not in client.get(url).content.decode()
    bill.lines.first().delete()
    assert "don't add up" in client.get(url).content.decode()


def _bill_urls(camp: Camp, bill: Bill) -> list[str]:
    return [
        reverse(name, args=[camp.pk, bill.pk])
        for name in (
            "bill_detail",
            "bill_file",
            "bill_retry",
            "bill_remove_file",
            "bill_delete",
        )
    ]


def test_other_chiros_cannot_reach_a_bill(client, camp) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    other = make_camp(chiro=Chiro.objects.create(name="Andere Chiro"))
    outsider = member_client(other, username="buur")

    for url in _bill_urls(camp, bill):
        assert outsider.get(url).status_code in {404, 405}
        assert outsider.post(url).status_code == 404
    assert outsider.get(reverse("bill_list", args=[camp.pk])).status_code == 404
    assert outsider.post(reverse("bill_list", args=[camp.pk])).status_code == 404
    bill.refresh_from_db()
    assert bill.file


def test_a_bill_cannot_be_reached_through_another_of_your_camps(client, camp) -> None:
    second = make_camp(chiro=camp.chiro)
    upload(client, camp)
    bill = Bill.objects.get()
    response = client.get(reverse("bill_file", args=[second.pk, bill.pk]))
    assert response.status_code == 404


def test_review_cannot_touch_lines_of_another_bill(client, camp, carrots) -> None:
    upload(client, camp)
    upload(client, camp, date="2026-08-03")
    first, second = Bill.objects.order_by("pk")
    data = review_data(second)  # ids of the second bill, posted to the first
    client.post(reverse("bill_detail", args=[camp.pk, first.pk]), data)
    assert second.lines.count() == 4
    assert not second.lines.exclude(bill=second).exists()
    assert first.lines.count() == 4
    assert not IngredientPrice.objects.filter(bill_line__bill=second).exists()


def test_anonymous_cannot_reach_a_bill(client, camp) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    for url in _bill_urls(camp, bill):
        assert Client().get(url).status_code == 302


def test_file_is_always_a_download(client, camp) -> None:
    upload(client, camp, name="rekening jan.pdf")
    bill = Bill.objects.get()
    response = client.get(reverse("bill_file", args=[camp.pk, bill.pk]))
    assert response["Content-Disposition"].startswith("attachment")
    assert b"".join(response.streaming_content).startswith(b"%PDF")


def test_remove_file_keeps_the_amounts(client, camp) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    path = Path(bill.file.path)
    assert path.exists()

    client.post(reverse("bill_remove_file", args=[camp.pk, bill.pk]))

    bill.refresh_from_db()
    assert not bill.file
    assert not path.exists()
    assert bill.lines.count() == 4
    assert client.get(reverse("bill_file", args=[camp.pk, bill.pk])).status_code == 404


def test_delete_bill_removes_file_lines_and_prices(client, camp, carrots) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    path = Path(bill.file.path)
    client.post(reverse("bill_detail", args=[camp.pk, bill.pk]), review_data(bill))

    response = client.post(reverse("bill_delete", args=[camp.pk, bill.pk]))

    assert response.status_code == 302
    assert not path.exists()
    assert not Bill.objects.exists()
    assert not IngredientPrice.objects.exists()


def test_delete_camp_removes_files_but_keeps_prices(client, camp, carrots) -> None:
    upload(client, camp)
    bill = Bill.objects.get()
    path = Path(bill.file.path)
    client.post(reverse("bill_detail", args=[camp.pk, bill.pk]), review_data(bill))

    member_client(camp, role=Role.ADMIN).post(reverse("camp_delete", args=[camp.pk]))

    assert not path.exists()
    assert not BillLine.objects.exists()
    assert IngredientPrice.objects.get().camp is None


class _Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _waiting_bill(client, camp) -> Bill:
    upload(client, camp, name="photo.png", content=png_bytes())
    return Bill.objects.get()


def test_ollama_answer_becomes_lines(client, camp, carrots, monkeypatch, settings):
    settings.OLLAMA_URL = "http://ollama.test"
    bill = _waiting_bill(client, camp)
    answer = {
        "lines": [
            {"description": "Wortel 2KG", "quantity": 1, "line_total": 3.5},
            {"description": "", "quantity": 1, "line_total": 1},
            {"description": "kapot", "line_total": "x"},
            "rommel",
        ],
        "total": 3.5,
    }
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data)
        return _Answer(json.dumps({"response": json.dumps(answer)}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    call_command("read_bills")

    bill.refresh_from_db()
    assert bill.status == Bill.Status.REVIEW
    assert bill.printed_total == Decimal("3.50")
    line = bill.lines.get()
    assert line.ingredient == carrots
    assert line.pack_amount == Decimal("2")
    assert seen["body"]["images"]
    assert not IngredientPrice.objects.exists()


def test_bill_keeps_waiting_while_ollama_is_off(client, camp, monkeypatch, settings):
    settings.OLLAMA_URL = "http://ollama.test"
    bill = _waiting_bill(client, camp)

    def refuse(request, timeout):
        raise urllib.error.URLError("refused")

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    call_command("read_bills")

    bill.refresh_from_db()
    assert bill.status == Bill.Status.WAITING


def test_bad_ollama_answer_marks_the_bill_and_it_can_retry(
    client, camp, monkeypatch, settings
):
    settings.OLLAMA_URL = "http://ollama.test"
    bill = _waiting_bill(client, camp)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Answer(
            json.dumps({"response": "geen json"}).encode()
        ),
    )
    read_with_ollama(bill)

    bill.refresh_from_db()
    assert bill.status == Bill.Status.FAILED
    assert bill.error
    client.post(reverse("bill_retry", args=[camp.pk, bill.pk]))
    bill.refresh_from_db()
    assert bill.status == Bill.Status.WAITING


def test_read_bills_leaves_bills_with_lines_alone(client, camp, settings) -> None:
    settings.OLLAMA_URL = ""
    bill = _waiting_bill(client, camp)
    BillLine.objects.create(
        bill=bill, description="Met de hand", line_total=Decimal("1")
    )
    call_command("read_bills")
    assert bill.lines.count() == 1


def test_piece_ingredient_defaults_to_one_item(client, camp) -> None:
    Ingredient.objects.create(name="Wortel", unit=PIECE)
    Ingredient.objects.create(name="Melk", unit=LITER)
    upload(client, camp)
    first, milk, *_ = Bill.objects.get().lines.all()
    assert first.pack_amount == Decimal("1")  # the 1KG doesn't fit a piece
    assert milk.pack_amount == Decimal("6")


@pytest.mark.parametrize(
    ("text", "description", "quantity"),
    [
        ("COLA 1,50 3,00", "COLA", Decimal("2")),
        ("Coca Cola 33 1,20", "Coca Cola 33", Decimal("1")),
        ("KAAS 1,33 2,50", "KAAS", Decimal("1")),
    ],
)
def test_numbers_before_the_total(text, description, quantity) -> None:
    (line,) = parse_text(text).lines
    assert (line.description, line.quantity) == (description, quantity)


def test_words_inside_product_names_do_not_trigger_rules() -> None:
    parsed = parse_text(
        "Cashewnoten 3,50\nJambon 2,50\nBonbon 1,20\nTotaalreiniger 4,00\nBon 1,00"
    )
    assert [line.description for line in parsed.lines] == [
        "Cashewnoten",
        "Jambon",
        "Bonbon",
        "Totaalreiniger",
        "Bon",
    ]
    assert parsed.printed_total is None
    assert [line.is_other for line in parsed.lines] == [False] * 4 + [True]


def test_absurd_pack_size_is_ignored() -> None:
    assert parse_pack("999x9999kg") is None


def test_short_ingredient_name_needs_a_whole_word(client, camp) -> None:
    Ingredient.objects.create(name="Ui", unit=PIECE)
    upload(client, camp, content=text_pdf(["Fruitsap 1L 2,00", "UI 1,00"]))
    juice, onion = Bill.objects.get().lines.all()
    assert juice.ingredient is None
    assert onion.ingredient.name == "Ui"


def test_saving_an_empty_review_keeps_a_scan_in_the_queue(client, camp) -> None:
    bill = _waiting_bill(client, camp)
    client.post(
        reverse("bill_detail", args=[camp.pk, bill.pk]),
        {"form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "0"},
    )
    bill.refresh_from_db()
    assert bill.status == Bill.Status.WAITING


def test_read_finishing_after_hand_entry_changes_nothing(
    client, camp, monkeypatch, settings
):
    settings.OLLAMA_URL = "http://ollama.test"
    bill = _waiting_bill(client, camp)
    answer = {"lines": [{"description": "X", "quantity": 1, "line_total": 1}]}

    def slow_read(request, timeout):
        BillLine.objects.create(bill=bill, description="Hand", line_total=Decimal("2"))
        Bill.objects.filter(pk=bill.pk).update(status=Bill.Status.DONE)
        return _Answer(json.dumps({"response": json.dumps(answer)}).encode())

    monkeypatch.setattr("urllib.request.urlopen", slow_read)
    read_with_ollama(bill)

    bill.refresh_from_db()
    assert bill.status == Bill.Status.DONE
    assert [line.description for line in bill.lines.all()] == ["Hand"]


def test_worker_stops_the_round_when_ollama_is_off(client, camp, monkeypatch, settings):
    settings.OLLAMA_URL = "http://ollama.test"
    _waiting_bill(client, camp)
    _waiting_bill_two = upload(client, camp, name="two.png", content=png_bytes())
    assert _waiting_bill_two.status_code == 302
    calls = []

    def refuse(request, timeout):
        calls.append(1)
        raise OSError("off")

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    call_command("read_bills")
    assert len(calls) == 1


def test_one_bad_bill_does_not_stop_the_others(client, camp, monkeypatch, settings):
    settings.OLLAMA_URL = "http://ollama.test"
    upload(client, camp, name="one.png", content=png_bytes())
    upload(client, camp, name="two.png", content=png_bytes())
    seen = []

    def crash_once(bill):
        seen.append(bill.pk)
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "bills.management.commands.read_bills.read_with_ollama", crash_once
    )
    call_command("read_bills")
    assert len(seen) == 2


def test_sideways_photo_is_turned_upright(client, camp) -> None:
    from bills.reading import _page_images

    buffer = io.BytesIO()
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees to display
    Image.new("RGB", (20, 10)).save(buffer, format="JPEG", exif=exif)
    upload(client, camp, name="photo.jpg", content=buffer.getvalue())

    (png,) = _page_images(Bill.objects.get())

    assert Image.open(io.BytesIO(png)).size == (10, 20)


def test_deleting_a_bill_in_the_admin_removes_its_prices(client, camp, carrots):
    from django.contrib.auth.models import User

    upload(client, camp)
    bill = Bill.objects.get()
    client.post(reverse("bill_detail", args=[camp.pk, bill.pk]), review_data(bill))
    assert IngredientPrice.objects.exists()

    admin = Client()
    admin.force_login(User.objects.create_superuser("baas"))
    response = admin.post(f"/admin/bills/bill/{bill.pk}/delete/", {"post": "yes"})

    assert response.status_code == 302
    assert not IngredientPrice.objects.exists()
