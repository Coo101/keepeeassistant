"""Access control: reading is public, writing requires a login."""

import datetime

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from camps.models import DayNote
from core.constants import DishType, MealType
from planning.models import MenuEntry
from shopping.models import ShoppingTrip
from tests.factories import KG, PRODUCE, make_camp, make_recipe

pytestmark = pytest.mark.django_db

AUG_1 = datetime.date(2026, 8, 1)


@pytest.fixture
def camp():
    return make_camp()  # Aug 1-5


@pytest.fixture
def cook(db):
    return User.objects.create_user("kok", password="soep-en-brood")


def _logged_in(cook) -> Client:
    client = Client()
    assert client.login(username="kok", password="soep-en-brood")
    return client


@pytest.mark.parametrize(
    "url_name",
    ["camp_list", "recipe_list"],
)
def test_public_pages_readable_anonymously(url_name) -> None:
    assert Client().get(reverse(url_name)).status_code == 200


@pytest.mark.parametrize(
    "url_name",
    ["planner", "shopping", "budget", "runbook", "overview_pdf"],
)
def test_camp_pages_readable_anonymously(camp, url_name) -> None:
    response = Client().get(reverse(url_name, args=[camp.pk]))
    assert response.status_code == 200


def test_anonymous_post_to_slot_is_redirected_and_changes_nothing(camp) -> None:
    recipe = make_recipe(
        "Stoofpot",
        dish_type=DishType.HOT_MEAL,
        ingredients=[("Potatoes", "2", KG, PRODUCE)],
    )
    url = reverse("edit_slot", args=[camp.pk, AUG_1.isoformat(), MealType.DINNER])

    response = Client().post(url, {"recipe": recipe.pk})

    assert response.status_code == 302
    assert reverse("login") in response["Location"]
    assert MenuEntry.objects.count() == 0


def test_anonymous_post_to_runbook_note_is_blocked(camp) -> None:
    response = Client().post(
        reverse("runbook", args=[camp.pk]),
        {"date": AUG_1.isoformat(), "text": "stiekem"},
    )
    assert response.status_code == 302
    assert reverse("login") in response["Location"]
    assert DayNote.objects.count() == 0


def test_anonymous_post_to_shopping_days_is_blocked(camp) -> None:
    response = Client().post(
        reverse("shopping", args=[camp.pk]), {"trip_dates": [AUG_1.isoformat()]}
    )
    assert response.status_code == 302
    assert ShoppingTrip.objects.count() == 0


def test_logged_in_user_can_write(camp, cook) -> None:
    recipe = make_recipe("Stoofpot", dish_type=DishType.HOT_MEAL)
    client = _logged_in(cook)

    slot_url = reverse("edit_slot", args=[camp.pk, AUG_1.isoformat(), MealType.DINNER])
    assert client.post(slot_url, {"recipe": recipe.pk}).status_code == 302
    assert MenuEntry.objects.count() == 1

    assert (
        client.post(
            reverse("runbook", args=[camp.pk]),
            {"date": AUG_1.isoformat(), "text": "te veel kiek"},
        ).status_code
        == 302
    )
    assert DayNote.objects.get().text == "te veel kiek"


def test_read_only_pages_hide_the_edit_forms(camp) -> None:
    content = Client().get(reverse("shopping", args=[camp.pk])).content.decode()
    assert "Save shopping days" not in content
    assert "to change the shopping days" in content

    content = Client().get(reverse("runbook", args=[camp.pk])).content.decode()
    assert "Bewaar notities" not in content


def test_admin_still_requires_its_own_login() -> None:
    response = Client().get("/admin/", follow=True)
    assert response.status_code == 200
    # bounced to the admin login form, not into the admin itself
    assert "/admin/login/" in response.redirect_chain[-1][0]


def test_login_page_is_reachable_and_accepts_credentials(cook) -> None:
    assert Client().get(reverse("login")).status_code == 200
    response = Client().post(
        reverse("login"), {"username": "kok", "password": "soep-en-brood"}
    )
    assert response.status_code == 302
