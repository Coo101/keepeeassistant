"""PDF output (SPEC §9.5). The native tests need WeasyPrint's system libraries;
the deploy job also checks that the Docker image can render a PDF."""

import sys
from types import SimpleNamespace

import pytest
from django.urls import reverse

from core.constants import DishType, MealType
from core.pdf import weasyprint_available
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


@pytest.fixture
def fake_weasyprint(monkeypatch) -> None:
    """Exercise the PDF response without the native libraries."""

    def html(**kwargs) -> SimpleNamespace:
        return SimpleNamespace(write_pdf=lambda: b"%PDF-fake")

    monkeypatch.setitem(sys.modules, "weasyprint", SimpleNamespace(HTML=html))
    monkeypatch.setattr("core.pdf.weasyprint_available", lambda: True)


@pytest.mark.parametrize(
    ("name", "header"),
    [
        ("Soep", 'inline; filename="Soep.pdf"'),
        ('Soep "extra"', 'inline; filename="Soep \\"extra\\".pdf"'),
        ("Soep\r\nX-Evil: 1", 'inline; filename="Soep X-Evil: 1.pdf"'),
        ("Crème", "inline; filename*=utf-8''Cr%C3%A8me.pdf"),
    ],
)
def test_pdf_filename_is_safe(fake_weasyprint, name: str, header: str) -> None:
    recipe = make_recipe(name)
    response = account_client().get(reverse("recipe_pdf", args=[recipe.pk]))
    assert response.status_code == 200
    assert response["Content-Disposition"] == header


@pytest.mark.skipif(
    not weasyprint_available(), reason="WeasyPrint's system libraries are missing"
)
def test_every_pdf_endpoint_renders_a_real_pdf() -> None:
    camp = make_camp()
    recipe = make_recipe(
        "Stoofpot",
        dish_type=DishType.HOT_MEAL,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    assign(camp, camp.start_date, MealType.DINNER, recipe)
    client = member_client(camp)
    urls = [
        reverse("recipe_pdf", args=[recipe.pk]),
        reverse("overview_pdf", args=[camp.pk]),
        reverse("runbook_pdf", args=[camp.pk]),
        reverse("shopping_pdf", args=[camp.pk]),
    ]
    for url in urls:
        response = client.get(url)
        assert response["Content-Type"] == "application/pdf"
        assert response.content[:4] == b"%PDF"
