"""Roles, archive, pantry, diets, balance and join requests
(docs/spec/accounts.md, docs/spec/planning.md, docs/spec/shopping.md)."""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client
from django.urls import reverse

from accounts.models import Chiro, Invitation, JoinRequest, Membership, Role
from camps.models import Camp, DietaryNeed
from core.constants import Diet, DishType, FoodTag, MealType
from planning.checks import menu_checks
from recipes.models import Ingredient
from shopping.budget import build_budget
from shopping.models import PantryItem, ShoppingTrip
from shopping.services import build_shopping_plan
from tests.factories import (
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

AUG = lambda d: datetime.date(2026, 8, d)  # noqa: E731


@pytest.fixture
def camp() -> Camp:
    return make_camp()  # Aug 1-5


def _tag(name: str, *tags: str) -> None:
    Ingredient.objects.filter(name=name).update(tags=list(tags))


def _rows(prefix_values: list[dict], initial: int = 0) -> dict:
    data = {
        "form-TOTAL_FORMS": str(len(prefix_values)),
        "form-INITIAL_FORMS": str(initial),
    }
    for index, values in enumerate(prefix_values):
        for field, value in values.items():
            data[f"form-{index}-{field}"] = value
    return data


# --- roles


def test_only_chiro_admins_can_delete_a_camp(camp) -> None:
    member = member_client(camp, "lid")
    url = reverse("camp_delete", args=[camp.pk])
    edit = reverse("camp_edit", args=[camp.pk])
    assert url not in member.get(edit).content.decode()
    assert member.post(url).status_code == 403
    assert Camp.objects.filter(pk=camp.pk).exists()

    admin = member_client(camp, "baas", role=Role.ADMIN)
    assert url in admin.get(edit).content.decode()
    assert admin.post(url).status_code == 302
    assert not Camp.objects.filter(pk=camp.pk).exists()


def test_members_see_their_chiro_outsiders_get_nothing(camp) -> None:
    url = reverse("chiro_detail", args=[camp.chiro.pk])
    member = member_client(camp, "lid")
    page = member.get(url).content.decode()
    assert "lid" in page
    assert "Invite someone" not in page
    assert member.post(url, {"email": "a@example.com"}).status_code == 403
    assert account_client("vreemd").get(url).status_code == 404
    assert Client().get(url).status_code == 302
    assert not Invitation.objects.exists()


def test_admin_invites_from_the_chiro_page(camp) -> None:
    admin = member_client(camp, "baas", role=Role.ADMIN)
    url = reverse("chiro_detail", args=[camp.chiro.pk])

    response = admin.post(url, {"email": "jan@example.com", "role": Role.MEMBER})

    assert response.status_code == 302
    invitation = Invitation.objects.get()
    assert invitation.chiro == camp.chiro
    assert invitation.token in mail.outbox[0].body
    assert invitation.token in admin.get(url).content.decode()
    # a second one for the same address is refused
    assert (
        admin.post(url, {"email": "JAN@example.com", "role": "member"}).status_code
        == 200
    )
    assert Invitation.objects.count() == 1


def test_invitation_gives_the_chosen_role(camp) -> None:
    invitation = Invitation.objects.create(
        chiro=camp.chiro, email="jan@example.com", role=Role.ADMIN
    )
    password = "soep-en-brood-42"
    Client().post(
        reverse("invitation_accept", args=[invitation.token]),
        {"username": "jan", "password1": password, "password2": password},
    )
    assert Membership.objects.get(user__username="jan").role == Role.ADMIN


def test_admin_changes_roles_and_removes_members(camp) -> None:
    admin = member_client(camp, "baas", role=Role.ADMIN)
    member_client(camp, "lid")
    membership = Membership.objects.get(user__username="lid")
    url = reverse("chiro_member", args=[camp.chiro.pk, membership.pk])

    admin.post(url, {"role": Role.ADMIN})
    membership.refresh_from_db()
    assert membership.role == Role.ADMIN

    admin.post(url, {"remove": "1"})
    assert not Membership.objects.filter(pk=membership.pk).exists()


def test_the_last_admin_stays(camp) -> None:
    admin = member_client(camp, "baas", role=Role.ADMIN)
    membership = Membership.objects.get(user__username="baas")
    url = reverse("chiro_member", args=[camp.chiro.pk, membership.pk])

    admin.post(url, {"remove": "1"})
    admin.post(url, {"role": Role.MEMBER})

    membership.refresh_from_db()
    assert membership.role == Role.ADMIN


def test_members_cannot_manage_members(camp) -> None:
    member_client(camp, "baas", role=Role.ADMIN)
    target = Membership.objects.get(user__username="baas")
    client = member_client(camp, "lid")
    url = reverse("chiro_member", args=[camp.chiro.pk, target.pk])
    assert client.post(url, {"remove": "1"}).status_code == 403
    assert Membership.objects.filter(pk=target.pk).exists()


def test_admin_of_one_chiro_cannot_touch_another(camp) -> None:
    member_client(camp, "lid")
    target = Membership.objects.get(user__username="lid")
    other = make_camp(chiro=Chiro.objects.create(name="Andere Chiro"))
    client = member_client(other, "buur", role=Role.ADMIN)
    url = reverse("chiro_member", args=[other.chiro.pk, target.pk])
    assert client.post(url, {"remove": "1"}).status_code == 404
    url = reverse("chiro_member", args=[camp.chiro.pk, target.pk])
    assert client.post(url, {"remove": "1"}).status_code == 404
    assert Membership.objects.filter(pk=target.pk).exists()


# --- archive


def test_archive_and_bring_back(camp) -> None:
    client = member_client(camp)
    listing = reverse("camp_list")
    url = reverse("camp_archive", args=[camp.pk])

    assert client.post(url).status_code == 302
    camp.refresh_from_db()
    assert camp.is_archived
    page = client.get(listing)
    assert list(page.context["camps"]) == []
    assert list(page.context["archived"]) == [camp]
    planner = client.get(reverse("planner", args=[camp.pk])).content.decode()
    assert "This camp is archived" in planner

    client.post(url)
    camp.refresh_from_db()
    assert not camp.is_archived


def test_archive_is_post_only_and_for_members(camp) -> None:
    url = reverse("camp_archive", args=[camp.pk])
    assert member_client(camp).get(url).status_code == 405
    assert account_client("vreemd").post(url).status_code == 404
    camp.refresh_from_db()
    assert not camp.is_archived


def test_archived_camp_does_not_lock_a_recipe() -> None:
    recipe = make_recipe("Stoofpot", dish_type=DishType.HOT_MEAL)
    other = make_camp(
        start=datetime.date(2099, 8, 1),
        chiro=Chiro.objects.create(name="Andere Chiro"),
    )
    assign(other, other.start_date, MealType.DINNER, recipe)
    client = account_client("auteur")
    recipe.author = User.objects.get(username="auteur")
    recipe.save()
    url = reverse("recipe_edit", args=[recipe.pk])
    assert client.get(url).status_code == 403
    other.is_archived = True
    other.save()
    assert client.get(url).status_code == 200


# --- pantry


def _pantry_camp():
    camp = make_camp(children=0, teens=10, staff=0)
    recipe = make_recipe("Stew", teens=10, ingredients=[("Potatoes", "4", KG, PRODUCE)])
    assign(camp, AUG(2), MealType.DINNER, recipe)
    assign(camp, AUG(4), MealType.DINNER, recipe)
    ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    ShoppingTrip.objects.create(camp=camp, date=AUG(3))
    return camp


def _quantities(camp) -> list[list[Decimal]]:
    return [
        [
            item.quantity
            for section in trip.shop_sections
            for items in section.items_by_category.values()
            for item in items
        ]
        for trip in build_shopping_plan(camp).trip_lists
    ]


def _add_pantry(camp, quantity: str) -> None:
    PantryItem.objects.create(
        chiro=camp.chiro,
        ingredient=Ingredient.objects.get(name="Potatoes"),
        quantity=Decimal(quantity),
    )


def test_pantry_comes_off_the_first_trip_first() -> None:
    camp = _pantry_camp()
    assert _quantities(camp) == [[Decimal("4.0")], [Decimal("4.0")]]
    _add_pantry(camp, "1")
    assert _quantities(camp) == [[Decimal("3.0")], [Decimal("4.0")]]


def test_pantry_carries_over_to_the_next_trip() -> None:
    camp = _pantry_camp()
    _add_pantry(camp, "5")
    assert _quantities(camp) == [[], [Decimal("3.0")]]


def test_pantry_larger_than_the_need_empties_the_lists() -> None:
    camp = _pantry_camp()
    _add_pantry(camp, "100")
    assert _quantities(camp) == [[], []]


def test_pantry_lowers_the_budget() -> None:
    camp = _pantry_camp()
    set_price("Potatoes", "1.00")
    assert build_budget(camp).total == Decimal("8.00")
    _add_pantry(camp, "3")
    assert build_budget(camp).total == Decimal("5.00")


def _pantry_rows(rows: list[dict]) -> dict:
    data = {
        key.replace("form-", "pantry-", 1): value for key, value in _rows(rows).items()
    }
    return {"section": "pantry", **data}


def test_pantry_page_saves_and_rejects_duplicates(camp) -> None:
    make_recipe("Stew", ingredients=[("Potatoes", "4", KG, PRODUCE)])
    potatoes = Ingredient.objects.get(name="Potatoes")
    client = member_client(camp)
    url = reverse("chiro_stock", args=[camp.chiro.pk])
    assert client.get(url).status_code == 200

    row = {"ingredient": potatoes.pk, "quantity": "2"}
    assert client.post(url, _pantry_rows([row, row])).status_code == 200
    assert not PantryItem.objects.exists()

    assert client.post(url, _pantry_rows([row])).status_code == 302
    assert PantryItem.objects.get().chiro == camp.chiro


def test_pantry_page_is_limited_to_members(camp) -> None:
    url = reverse("chiro_stock", args=[camp.chiro.pk])
    assert account_client("vreemd").get(url).status_code == 404


def test_the_pantry_serves_every_camp_of_the_chiro() -> None:
    camp = _pantry_camp()
    other = make_camp(chiro=camp.chiro)
    _add_pantry(other, "1")
    assert _quantities(camp) == [[Decimal("3.0")], [Decimal("4.0")]]


# --- diets


def _dinner_with(camp, *tags) -> None:
    recipe = make_recipe(
        "Stoofpot",
        dish_type=DishType.HOT_MEAL,
        ingredients=[("Kip", "1", KG, PRODUCE)],
    )
    _tag("Kip", *tags)
    assign(camp, AUG(2), MealType.DINNER, recipe)


def test_planner_warns_about_a_diet_conflict(camp) -> None:
    _dinner_with(camp, FoodTag.MEAT)
    DietaryNeed.objects.create(camp=camp, diet=Diet.VEGETARIAN, count=3)
    (conflict,) = menu_checks(camp).conflicts
    assert conflict.recipe == "Stoofpot"
    assert conflict.people == 3
    assert conflict.contains == "Meat"
    page = member_client(camp).get(reverse("planner", args=[camp.pk]))
    assert "These meals need an alternative" in page.content.decode()


def test_no_conflict_when_the_diet_allows_it(camp) -> None:
    _dinner_with(camp, FoodTag.VEGETABLE, FoodTag.GLUTEN)
    DietaryNeed.objects.create(camp=camp, diet=Diet.VEGETARIAN, count=3)
    assert menu_checks(camp).conflicts == []


def test_every_diet_has_rules() -> None:
    assert {code for code, _ in Diet.CHOICES} == set(Diet.FORBIDS)


def test_diets_page_saves_and_rejects_duplicates(camp) -> None:
    client = member_client(camp)
    url = reverse("camp_diets", args=[camp.pk])
    assert client.get(url).status_code == 200
    row = {"diet": Diet.VEGAN, "count": "2", "note": "Jan, An"}
    assert client.post(url, _rows([row, row])).status_code == 200
    assert client.post(url, _rows([row])).status_code == 302
    assert DietaryNeed.objects.get().camp == camp
    assert account_client("vreemd").get(url).status_code == 404


def test_ingredient_form_saves_tags() -> None:
    client = account_client()
    client.post(
        reverse("ingredient_create"),
        {
            "name": "Kaas",
            "unit": KG,
            "category": "dairy",
            "shop": "colruyt",
            "tags": [FoodTag.LACTOSE],
        },
    )
    assert Ingredient.objects.get().tags == [FoodTag.LACTOSE]


# --- balance


def test_day_without_vegetables_or_fruit_is_flagged(camp) -> None:
    _dinner_with(camp, FoodTag.MEAT)
    warnings = menu_checks(camp).balance[AUG(2)]
    assert "Stoofpot has no vegetables" in warnings
    assert "No vegetables this day" in warnings
    assert "No fruit this day" in warnings


def test_balanced_day_has_no_warnings(camp) -> None:
    _dinner_with(camp, FoodTag.VEGETABLE, FoodTag.FRUIT)
    assert menu_checks(camp).balance == {}


def test_too_many_sweet_recipes_are_flagged(camp) -> None:
    make_recipe(
        "Cake",
        dish_type=DishType.DESSERT,
        ingredients=[("Suiker", "1", KG, PRODUCE)],
    )
    _tag("Suiker", FoodTag.SUGAR)
    from recipes.models import Recipe

    cake = Recipe.objects.get(name="Cake")
    assign(camp, AUG(2), MealType.LUNCH, cake, course="dessert")
    assign(camp, AUG(2), MealType.DINNER, cake, course="dessert")
    assert not any(
        "A lot of sugar" in warning for warning in menu_checks(camp).balance[AUG(2)]
    )
    snack = make_recipe(
        "Koek",
        dish_type=DishType.SNACK_SWEET,
        ingredients=[("Suiker", "1", KG, PRODUCE)],
    )
    assign(camp, AUG(2), MealType.TEA, snack)
    assert any(
        "A lot of sugar" in warning for warning in menu_checks(camp).balance[AUG(2)]
    )


def test_no_balance_warnings_before_anything_is_tagged(camp) -> None:
    _dinner_with(camp)
    checks = menu_checks(camp)
    assert checks.balance == {}
    assert checks.unchecked == ["Kip"]


def test_checked_ingredient_without_tags_is_not_reported(camp) -> None:
    _dinner_with(camp)
    Ingredient.objects.filter(name="Kip").update(tags_checked=True)
    assert menu_checks(camp).unchecked == []


def test_tagged_but_unchecked_ingredient_is_still_reported(camp) -> None:
    _dinner_with(camp, FoodTag.VEGETABLE)
    assert menu_checks(camp).unchecked == ["Kip"]


# --- join requests


def _join_data(**extra) -> dict:
    return {
        "name": "Jan",
        "email": "jan@example.com",
        "chiro_name": "Chiro Nieuw",
        **extra,
    }


def test_join_request_is_public_and_stored() -> None:
    client = Client()
    url = reverse("join_request")
    assert client.get(url).status_code == 200
    assert client.post(url, _join_data()).status_code == 200
    assert JoinRequest.objects.get().email == "jan@example.com"


def test_filled_hidden_field_is_ignored() -> None:
    response = Client().post(reverse("join_request"), _join_data(website="spam"))
    assert "Thank you" in response.content.decode()
    assert not JoinRequest.objects.exists()


def test_join_requests_are_limited_per_address() -> None:
    for _ in range(7):
        Client().post(reverse("join_request"), _join_data())
    assert JoinRequest.objects.count() == 5


def _staff() -> Client:
    client = Client()
    client.force_login(User.objects.create_superuser("baas"))
    return client


def _run_action(client: Client, action: str, join: JoinRequest) -> None:
    response = client.post(
        "/admin/accounts/joinrequest/",
        {"action": action, "_selected_action": [join.pk]},
    )
    assert response.status_code == 302


def test_approving_a_new_chiro_creates_it_and_invites_an_admin() -> None:
    join = JoinRequest.objects.create(
        name="Jan", email="jan@example.com", chiro_name="Chiro Nieuw"
    )
    _run_action(_staff(), "approve", join)

    invitation = Invitation.objects.get()
    assert invitation.chiro.name == "Chiro Nieuw"
    assert invitation.role == Role.ADMIN
    assert invitation.token in mail.outbox[0].body
    join.refresh_from_db()
    assert join.status == JoinRequest.Status.APPROVED


def test_approving_for_an_existing_chiro_invites_a_member() -> None:
    chiro = Chiro.objects.create(name="Chiro Oud")
    Membership.objects.create(
        user=User.objects.create_user("oud"), chiro=chiro, role=Role.ADMIN
    )
    join = JoinRequest.objects.create(
        name="Jan", email="jan@example.com", chiro_name="chiro oud"
    )
    _run_action(_staff(), "approve", join)
    invitation = Invitation.objects.get()
    assert invitation.chiro == chiro
    assert invitation.role == Role.MEMBER
    assert Chiro.objects.count() == 1


def test_rejecting_sends_nothing_and_approving_twice_invites_once() -> None:
    client = _staff()
    join = JoinRequest.objects.create(
        name="Jan", email="jan@example.com", chiro_name="Chiro Nieuw"
    )
    _run_action(client, "reject", join)
    _run_action(client, "approve", join)
    assert mail.outbox == []
    assert not Invitation.objects.exists()


def test_diet_rows_can_swap_and_a_removed_value_can_come_back(camp) -> None:
    client = member_client(camp)
    url = reverse("camp_diets", args=[camp.pk])
    vegan = DietaryNeed.objects.create(camp=camp, diet=Diet.VEGAN, count=1)
    pork = DietaryNeed.objects.create(camp=camp, diet=Diet.NO_PORK, count=2)

    swap = _rows(
        [
            {"id": vegan.pk, "diet": Diet.NO_PORK, "count": "1"},
            {"id": pork.pk, "diet": Diet.VEGAN, "count": "2"},
        ],
        initial=2,
    )
    assert client.post(url, swap).status_code == 302
    vegan.refresh_from_db()
    assert vegan.diet == Diet.NO_PORK

    again = _rows(
        [
            {"id": vegan.pk, "diet": Diet.NO_PORK, "count": "1", "DELETE": "on"},
            {"id": pork.pk, "diet": Diet.VEGAN, "count": "2"},
            {"diet": Diet.NO_PORK, "count": "7"},
        ],
        initial=2,
    )
    assert client.post(url, again).status_code == 302
    assert DietaryNeed.objects.get(diet=Diet.NO_PORK).count == 7


def test_removed_row_is_no_duplicate_while_another_row_is_invalid(camp) -> None:
    need = DietaryNeed.objects.create(camp=camp, diet=Diet.VEGAN, count=1)
    data = _rows(
        [
            {"id": need.pk, "diet": Diet.VEGAN, "count": "1", "DELETE": "on"},
            {"diet": Diet.VEGAN, "count": "2"},
            {"diet": Diet.NO_PORK, "count": "x"},
        ],
        initial=1,
    )
    response = member_client(camp).post(reverse("camp_diets", args=[camp.pk]), data)
    assert response.status_code == 200
    assert "twice" not in response.content.decode()


def test_days_before_the_first_trip_use_up_the_pantry_first() -> None:
    camp = make_camp(children=0, teens=10, staff=0)
    recipe = make_recipe("Stew", teens=10, ingredients=[("Potatoes", "8", KG, PRODUCE)])
    assign(camp, AUG(1), MealType.DINNER, recipe)  # before any trip's coverage
    assign(camp, AUG(3), MealType.DINNER, recipe)
    ShoppingTrip.objects.create(camp=camp, date=AUG(2))
    _add_pantry(camp, "10")
    assert _quantities(camp) == [[Decimal("6.0")]]


def test_invitation_to_a_chiro_without_admin_makes_an_admin(camp) -> None:
    invitation = Invitation.objects.create(chiro=camp.chiro, email="jan@example.com")
    password = "soep-en-brood-42"
    Client().post(
        reverse("invitation_accept", args=[invitation.token]),
        {"username": "jan", "password1": password, "password2": password},
    )
    assert Membership.objects.get(user__username="jan").role == Role.ADMIN


def test_admin_invitation_upgrades_an_existing_member(camp) -> None:
    member_client(camp, "baas", role=Role.ADMIN)
    client = member_client(camp, "lid")
    User.objects.filter(username="lid").update(email="lid@example.com")
    invitation = Invitation.objects.create(
        chiro=camp.chiro, email="lid@example.com", role=Role.ADMIN
    )
    client.post(reverse("invitation_accept", args=[invitation.token]))
    assert Membership.objects.get(user__username="lid").role == Role.ADMIN


def test_removing_yourself_ends_on_your_account_page(camp) -> None:
    member_client(camp, "ander", role=Role.ADMIN)
    client = member_client(camp, "baas", role=Role.ADMIN)
    membership = Membership.objects.get(user__username="baas")
    response = client.post(
        reverse("chiro_member", args=[camp.chiro.pk, membership.pk]),
        {"remove": "1"},
    )
    assert response["Location"] == reverse("account")


def test_chiro_page_shows_a_full_invitation_link(camp) -> None:
    admin = member_client(camp, "baas", role=Role.ADMIN)
    invitation = Invitation.objects.create(chiro=camp.chiro, email="jan@example.com")
    page = admin.get(reverse("chiro_detail", args=[camp.chiro.pk])).content.decode()
    assert f"http://testserver/invitations/{invitation.token}/" in page


def test_duplicate_join_requests_invite_once_and_members_not_at_all(camp) -> None:
    client = _staff()
    first, second = (
        JoinRequest.objects.create(
            name="Jan", email="jan@example.com", chiro_name=camp.chiro.name
        )
        for _ in range(2)
    )
    _run_action(client, "approve", first)
    _run_action(client, "approve", second)
    assert Invitation.objects.count() == 1

    member_client(camp, "lid")
    User.objects.filter(username="lid").update(email="lid@example.com")
    join = JoinRequest.objects.create(
        name="Lid", email="lid@example.com", chiro_name=camp.chiro.name
    )
    _run_action(client, "approve", join)
    assert Invitation.objects.count() == 1
    join.refresh_from_db()
    assert join.status == JoinRequest.Status.APPROVED


def test_unknown_ingredient_gives_no_false_alarm_about_vegetables(camp) -> None:
    _dinner_with(camp, FoodTag.MEAT)
    other = make_recipe(
        "Soep", dish_type=DishType.SOUP, ingredients=[("Prei", "1", KG, PRODUCE)]
    )
    assign(camp, AUG(2), MealType.LUNCH, other, course="soup")
    warnings = menu_checks(camp).balance[AUG(2)]
    assert "Stoofpot has no vegetables" in warnings  # its one ingredient is known
    assert "No vegetables this day" not in warnings  # Prei could be one
    Ingredient.objects.filter(name="Prei").update(tags_checked=True)
    assert "No vegetables this day" in menu_checks(camp).balance[AUG(2)]
