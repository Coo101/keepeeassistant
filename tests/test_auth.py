"""Access control: everything needs a login; camps stay within their Chiro."""

import datetime

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import URLPattern, reverse

from accounts.models import Chiro, Membership
from camps.models import DayNote
from camps.urls import urlpatterns as camp_urls
from core.constants import DishType, MealType
from planning.models import MenuEntry
from planning.urls import urlpatterns as planning_urls
from shopping.models import ShoppingTrip
from shopping.urls import urlpatterns as shopping_urls
from tests.factories import (
    account_client,
    make_camp,
    make_recipe,
    member_client,
)

pytestmark = pytest.mark.django_db

AUG_1 = datetime.date(2026, 8, 1)
PATH_ARGS = {"date": AUG_1.isoformat(), "meal_type": MealType.DINNER}


def _camp_url_names() -> list[str]:
    """Every page under a camp, so a new page is covered automatically. The
    POST-only remove URLs are tested in test_delete_and_remove.py."""
    patterns: list[URLPattern] = [*camp_urls, *planning_urls, *shopping_urls]
    return [
        p.name
        for p in patterns
        if "camp_id" in p.pattern.converters
        and not p.name.startswith("remove_outside_")
    ]


def _camp_url(url_name: str, camp) -> str:
    pattern = next(
        p for p in [*camp_urls, *planning_urls, *shopping_urls] if p.name == url_name
    ).pattern
    kwargs = {k: PATH_ARGS[k] for k in pattern.converters if k != "camp_id"}
    return reverse(url_name, kwargs={"camp_id": camp.pk, **kwargs})


@pytest.fixture
def camp():
    return make_camp()  # Aug 1-5


def test_camp_urls_are_found() -> None:
    assert len(_camp_url_names()) == 10


@pytest.mark.parametrize("url_name", _camp_url_names())
def test_camp_pages_need_a_login(camp, url_name) -> None:
    response = Client().get(_camp_url(url_name, camp))
    assert response.status_code == 302
    assert reverse("login") in response["Location"]


@pytest.mark.parametrize("url_name", _camp_url_names())
def test_camp_pages_open_for_members(camp, url_name) -> None:
    assert member_client(camp).get(_camp_url(url_name, camp)).status_code == 200


@pytest.mark.parametrize("url_name", _camp_url_names())
def test_camp_pages_hidden_from_other_chiros(camp, url_name) -> None:
    other = make_camp(chiro=Chiro.objects.create(name="Andere Chiro"))
    client = member_client(other)
    assert client.get(_camp_url(url_name, camp)).status_code == 404


def test_camp_list_only_shows_own_chiro(camp) -> None:
    other = make_camp(chiro=Chiro.objects.create(name="Andere Chiro"))
    other.name = "Kamp van de buren"
    other.save()

    content = member_client(camp).get(reverse("camp_list")).content.decode()

    assert camp.name in content
    assert other.name not in content


def test_account_without_chiro_sees_no_camps(camp) -> None:
    response = account_client().get(reverse("camp_list"))
    assert response.status_code == 200
    assert camp.name not in response.content.decode()


def test_staff_get_no_exception_outside_the_admin(camp) -> None:
    client = account_client("baas", is_staff=True, is_superuser=True)
    assert client.get(reverse("planner", args=[camp.pk])).status_code == 404


def test_user_in_two_chiros_sees_both_camps_once(camp) -> None:
    other = make_camp(chiro=Chiro.objects.create(name="Andere Chiro"))
    client = member_client(camp)
    Membership.objects.create(user=User.objects.get(username="kok"), chiro=other.chiro)

    response = client.get(reverse("camp_list"))

    pks = [c.pk for c in response.context["camps"]]
    assert sorted(pks) == sorted([camp.pk, other.pk])


def test_other_chiro_cannot_write_to_a_camp(camp) -> None:
    recipe = make_recipe("Stoofpot", dish_type=DishType.HOT_MEAL)
    other = make_camp(chiro=Chiro.objects.create(name="Andere Chiro"))
    client = member_client(other)

    assert (
        client.post(_camp_url("edit_slot", camp), {"recipe": recipe.pk}).status_code
        == 404
    )
    assert (
        client.post(
            reverse("runbook", args=[camp.pk]),
            {"date": AUG_1.isoformat(), "text": "stiekem"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            reverse("shopping", args=[camp.pk]), {"trip_dates": [AUG_1.isoformat()]}
        ).status_code
        == 404
    )
    assert MenuEntry.objects.count() == 0
    assert DayNote.objects.count() == 0
    assert ShoppingTrip.objects.count() == 0


def test_anonymous_post_changes_nothing(camp) -> None:
    recipe = make_recipe("Stoofpot", dish_type=DishType.HOT_MEAL)
    response = Client().post(_camp_url("edit_slot", camp), {"recipe": recipe.pk})
    assert response.status_code == 302
    assert reverse("login") in response["Location"]
    assert MenuEntry.objects.count() == 0


def test_member_can_write(camp) -> None:
    recipe = make_recipe("Stoofpot", dish_type=DishType.HOT_MEAL)
    client = member_client(camp)

    assert (
        client.post(_camp_url("edit_slot", camp), {"recipe": recipe.pk}).status_code
        == 302
    )
    assert MenuEntry.objects.count() == 1

    assert (
        client.post(
            reverse("runbook", args=[camp.pk]),
            {"date": AUG_1.isoformat(), "text": "te veel kiek"},
        ).status_code
        == 302
    )
    assert DayNote.objects.get().text == "te veel kiek"


def test_admin_link_only_for_staff(camp) -> None:
    url = reverse("camp_list")
    assert 'href="/admin/"' not in member_client(camp).get(url).content.decode()
    staff = account_client("baas", is_staff=True)
    assert 'href="/admin/"' in staff.get(url).content.decode()


def test_admin_still_requires_its_own_login() -> None:
    response = Client().get("/admin/", follow=True)
    assert response.status_code == 200
    # bounced to the admin login form, not into the admin itself
    assert "/admin/login/" in response.redirect_chain[-1][0]


def test_admin_rejects_non_staff(camp) -> None:
    response = member_client(camp).get("/admin/", follow=True)
    assert "/admin/login/" in response.redirect_chain[-1][0]


def test_admin_login_form_works_anonymously() -> None:
    User.objects.create_superuser("baas", password="soep-en-brood")
    response = Client().post(
        "/admin/login/", {"username": "baas", "password": "soep-en-brood"}
    )
    assert response.status_code == 302


def test_login_page_is_reachable_and_accepts_credentials() -> None:
    User.objects.create_user("kok", password="soep-en-brood")
    assert Client().get(reverse("login")).status_code == 200
    response = Client().post(
        reverse("login"), {"username": "kok", "password": "soep-en-brood"}
    )
    assert response.status_code == 302


def test_logout_after_session_expired_does_not_bounce_through_login() -> None:
    response = Client().post(reverse("logout"))
    assert response.status_code == 302
    assert "next=" not in response["Location"]
