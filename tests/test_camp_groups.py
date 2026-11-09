"""Headcount per afdeling on the camp form (SPEC §9.3)."""

import importlib
from decimal import Decimal

import pytest
from django.apps import apps
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Chiro, Membership
from camps.forms import DEFAULT_GROUPS
from camps.models import Camp, CampGroup
from tests.factories import account_client, make_camp, member_client

pytestmark = pytest.mark.django_db

CHILDREN = CampGroup.Kind.CHILDREN
TEENS = CampGroup.Kind.TEENS
STAFF = CampGroup.Kind.STAFF


def _camp_data(rows: list[tuple], initial: int = 0, **extra) -> dict:
    """The camp form with group rows (id, name, kind, count[, delete])."""
    data = {
        "name": "Zomerkamp",
        "start_date": "2027-07-01",
        "end_date": "2027-07-10",
        "breakfast_time": "08:00",
        "lunch_time": "12:30",
        "teatime_time": "16:00",
        "dinner_time": "18:30",
        "groups-TOTAL_FORMS": str(len(rows)),
        "groups-INITIAL_FORMS": str(initial),
    }
    for i, (pk, name, kind, count, *delete) in enumerate(rows):
        data[f"groups-{i}-id"] = pk or ""
        data[f"groups-{i}-name"] = name
        data[f"groups-{i}-kind"] = kind
        data[f"groups-{i}-count"] = str(count)
        if delete:
            data[f"groups-{i}-DELETE"] = "on"
    return {**data, **extra}


def _client_in(chiro: Chiro) -> Client:
    client = account_client()
    Membership.objects.create(user=User.objects.get(username="kok"), chiro=chiro)
    return client


@pytest.fixture
def chiro() -> Chiro:
    return Chiro.objects.create(name="Chiro Opoeteren")


def test_a_new_camp_starts_with_the_usual_afdelingen(chiro: Chiro) -> None:
    page = _client_in(chiro).get(reverse("camp_create")).content.decode()

    for name, _kind in DEFAULT_GROUPS:
        assert f'value="{escape(name)}"' in page


def test_the_totals_come_from_the_groups(chiro: Chiro) -> None:
    client = _client_in(chiro)
    rows = [
        (None, "Ribbels", CHILDREN, 12),
        (None, "Speelclub", CHILDREN, 0),  # left at 0: not saved
        (None, "Tito's", TEENS, 9),
        (None, "Keti's", TEENS, 7),
        (None, "Leiding", STAFF, 6),
    ]

    response = client.post(reverse("camp_create"), _camp_data(rows, chiro=chiro.pk))

    camp = Camp.objects.get()
    assert response["Location"] == reverse("planner", args=[camp.pk])
    assert (camp.num_children, camp.num_teens, camp.num_staff) == (12, 16, 6)
    assert camp.demand_portions == Decimal("30.4")
    assert list(camp.groups.values_list("name", flat=True)) == [
        "Ribbels",
        "Tito's",
        "Keti's",
        "Leiding",
    ]


def test_a_new_camp_copies_the_groups_of_the_chiros_last_camp(chiro: Chiro) -> None:
    earlier = make_camp(chiro=chiro)
    CampGroup.objects.create(camp=earlier, name="Sloebers", kind=CHILDREN, count=8)
    CampGroup.objects.create(camp=earlier, name="Kwiks", kind=CHILDREN, count=11)

    page = _client_in(chiro).get(reverse("camp_create")).content.decode()

    assert 'value="Sloebers"' in page and 'value="Kwiks"' in page
    assert 'value="Ribbels"' not in page
    assert 'value="8"' not in page  # the numbers are this camp's own


def test_editing_a_group_updates_the_totals() -> None:
    camp = make_camp(children=0, teens=0, staff=0)
    ribbels = CampGroup.objects.create(
        camp=camp, name="Ribbels", kind=CHILDREN, count=5
    )
    aspis = CampGroup.objects.create(camp=camp, name="Aspi's", kind=TEENS, count=4)
    camp.update_headcount()
    client = member_client(camp)
    rows = [
        (ribbels.pk, "Ribbels", CHILDREN, 10),
        (aspis.pk, "Aspi's", TEENS, 4, "delete"),
        (None, "Leiding", STAFF, 3),
    ]

    response = client.post(
        reverse("camp_edit", args=[camp.pk]), _camp_data(rows, initial=2)
    )

    assert response.status_code == 302
    camp.refresh_from_db()
    assert (camp.num_children, camp.num_teens, camp.num_staff) == (10, 0, 3)
    assert set(camp.groups.values_list("name", flat=True)) == {"Ribbels", "Leiding"}


def test_a_group_name_is_used_once(chiro: Chiro) -> None:
    client = _client_in(chiro)
    rows = [(None, "Ribbels", CHILDREN, 5), (None, "Ribbels", CHILDREN, 6)]

    response = client.post(reverse("camp_create"), _camp_data(rows, chiro=chiro.pk))

    assert response.status_code == 200
    assert "Ribbels is in the list twice." in response.content.decode()
    assert not Camp.objects.exists()


def test_adding_a_row_without_javascript_keeps_what_was_typed(chiro: Chiro) -> None:
    client = _client_in(chiro)
    rows = [(None, "Ribbels", CHILDREN, 10), (None, "Tito's", TEENS, 5)]

    response = client.post(
        reverse("camp_create"), _camp_data(rows, chiro=chiro.pk, add_row="groups")
    )

    page = response.content.decode()
    assert response.status_code == 200
    assert not Camp.objects.exists()
    assert 'name="groups-2-name"' in page
    assert 'name="groups-TOTAL_FORMS" value="3"' in page
    # The totals shown add up the typed rows: 10 x 0.7 + 5.
    assert '<strong data-total="portions">12</strong>' in page


def test_the_row_endpoint_numbers_the_new_row(chiro: Chiro) -> None:
    client = _client_in(chiro)

    response = client.get(reverse("camp_group_row"), {"groups-TOTAL_FORMS": "4"})

    page = response.content.decode()
    assert 'name="groups-4-name"' in page
    assert 'name="groups-TOTAL_FORMS" value="5"' in page


def test_the_row_endpoint_needs_a_login() -> None:
    response = Client().get(reverse("camp_group_row"))

    assert response.status_code == 302


def test_the_runbook_lists_the_groups() -> None:
    camp = make_camp()
    CampGroup.objects.create(camp=camp, name="Speelclub", kind=CHILDREN, count=14)

    page = member_client(camp).get(reverse("runbook", args=[camp.pk])).content
    pdf = member_client(camp).get(reverse("runbook_pdf", args=[camp.pk]))

    assert "Speelclub" in page.decode()
    assert pdf.status_code == 200


def test_existing_camps_get_groups_that_keep_their_totals() -> None:
    camp = make_camp(children=20, teens=30, staff=0)
    migration = importlib.import_module("camps.migrations.0007_groups_from_totals")

    migration.groups_from_totals(apps, None)

    assert camp.groups.count() == 2  # no row for the 0 staff
    camp.update_headcount()
    camp.refresh_from_db()
    assert (camp.num_children, camp.num_teens, camp.num_staff) == (20, 30, 0)
