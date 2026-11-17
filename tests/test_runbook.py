"""Runbook (draaiboek) view: front-page info, day sections, notes."""

import datetime

import pytest
from django.conf import settings
from django.urls import reverse

from camps.models import DayNote
from core.constants import DishType, MealType
from tests.factories import KG, PRODUCE, assign, make_camp, make_recipe, member_client

pytestmark = pytest.mark.django_db

AUG_1 = datetime.date(2026, 8, 1)


def _camp_with_menu():
    camp = make_camp()  # Aug 1-5
    camp.cook_team = "Yonick +32 480 00 00 00"
    camp.location = "Chiro Testdorp\nKerkstraat 1"
    camp.bakery = "Bakkerij De Smedt"
    camp.save()
    recipe = make_recipe(
        "Stoofpot",
        dish_type=DishType.HOT_MEAL,
        teens=13,
        ingredients=[("Potatoes", "2.5", KG, PRODUCE)],
    )
    recipe.steps.create(order=1, instruction="Alles stoven.", duration_minutes=90)
    assign(camp, AUG_1, MealType.DINNER, recipe)
    return camp


def _dutch_client(camp):
    """The kookploeg reads the runbook in Dutch."""
    client = member_client(camp)
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "nl"
    return client


def test_runbook_shows_info_days_and_steps() -> None:
    camp = _camp_with_menu()
    response = _dutch_client(camp).get(reverse("runbook", args=[camp.pk]))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Chiro Testdorp" in content
    assert "Bakkerij De Smedt" in content
    # one titled, anchored section per camp day
    assert content.count("Dag ") >= 5
    assert 'id="day-2026-08-01"' in content
    assert "Stoofpot" in content
    assert "Alles stoven." in content
    # scaled quantities present (52 / 13 portions = x4 -> 10 kg), Dutch style
    assert "10,0" in content


def test_runbook_note_save_and_display() -> None:
    camp = _camp_with_menu()
    url = reverse("runbook", args=[camp.pk])
    client = member_client(camp)
    response = client.post(url, {"date": "2026-08-01", "text": "Te veel kiek."})
    assert response.status_code == 302
    note = DayNote.objects.get(camp=camp, date=AUG_1)
    assert note.text == "Te veel kiek."
    assert "Te veel kiek." in client.get(url).content.decode()


def test_runbook_note_rejects_non_camp_day() -> None:
    camp = _camp_with_menu()
    response = member_client(camp).post(
        reverse("runbook", args=[camp.pk]),
        {"date": "2030-01-01", "text": "nope"},
    )
    assert response.status_code == 404
    assert DayNote.objects.count() == 0


def test_runbook_pdf_falls_back_to_html(monkeypatch) -> None:
    monkeypatch.setattr("core.pdf.weasyprint_available", lambda: False)
    camp = _camp_with_menu()
    response = _dutch_client(camp).get(reverse("runbook_pdf", args=[camp.pk]))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Draaiboek kookploeg" in content
    assert "Stoofpot" in content


def test_menu_slot_outside_the_camp_dates_is_not_found() -> None:
    camp = _camp_with_menu()
    recipe = camp.menu_entries.get().recipe
    url = reverse("edit_slot", args=[camp.pk, "2030-01-01", MealType.DINNER])
    client = member_client(camp)
    assert client.get(url).status_code == 404
    assert client.post(url, {"recipe": recipe.pk}).status_code == 404
    assert camp.menu_entries.count() == 1
