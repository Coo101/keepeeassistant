"""Checks for the pages moved to Bootstrap (roadmap step 3, the UI move).

Each area adds its converted templates to CONVERTED_TEMPLATES and its pages to
CONVERTED_PAGES (docs/superpowers/specs/2026-11-16-ui-move-design.md).
"""

import re
from collections.abc import Callable
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Chiro, Membership
from camps.models import Camp
from recipes.models import Recipe
from tests.factories import (
    KG,
    PRODUCE,
    account_client,
    make_camp,
    make_recipe,
    member_client,
)

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

# Paths under templates/ that no longer use the old hand-written classes.
CONVERTED_TEMPLATES: list[str] = [
    "components/page_header.html",
    "components/empty_state.html",
    "components/back_link.html",
    "components/form_errors.html",
    "components/camp_nav.html",
    "components/checkbox_chips.html",
    "partials/_formset_row.html",
    "recipes/_formset.html",
    "camps/camp_list.html",
    "camps/camp_form.html",
    "camps/_groups.html",
    "camps/_example_note.html",
    "camps/rows_page.html",
    "planning/planner.html",
    "planning/_outside_entries.html",
    "planning/_headcount.html",
    "planning/edit_slot.html",
    "planning/runbook.html",
    "recipes/recipe_list.html",
    "recipes/_recipe_results.html",
    "recipes/recipe_detail.html",
    "recipes/_recipe_ingredients.html",
    "recipes/_recipe_pdf_link.html",
    "recipes/recipe_form.html",
    "recipes/_new_ingredient_dialog.html",
    "recipes/ingredient_list.html",
    "recipes/_ingredient_results.html",
    "recipes/ingredient_form.html",
    "shopping/shopping.html",
    "shopping/budget.html",
    "kitchen/stock.html",
    "kitchen/camp_utensils.html",
    "bills/bill_detail.html",
    "bills/_bill_line_row.html",
    "bills/bill_list.html",
    "bills/report.html",
    "bills/_report_body.html",
]

# (URL name, the URL's args for a camp): full pages with one h1 and the red rule.
CONVERTED_PAGES: list[tuple[str, Callable[[Camp], list]]] = [
    ("camp_list", lambda camp: []),
    ("camp_create", lambda camp: []),
    ("camp_edit", lambda camp: [camp.pk]),
    ("camp_diets", lambda camp: [camp.pk]),
    ("planner", lambda camp: [camp.pk]),
    ("edit_slot", lambda camp: [camp.pk, camp.start_date.isoformat(), "dinner"]),
    ("runbook", lambda camp: [camp.pk]),
    ("shopping", lambda camp: [camp.pk]),
    ("budget", lambda camp: [camp.pk]),
    ("camp_utensils", lambda camp: [camp.pk]),
    ("bill_list", lambda camp: [camp.pk]),
    ("financial_report", lambda camp: [camp.pk]),
]

# (URL name, the URL's args for a recipe): recipe pages with one h1 and the red rule.
RECIPE_PAGES: list[tuple[str, Callable[[Recipe], list]]] = [
    ("recipe_list", lambda recipe: []),
    ("recipe_detail", lambda recipe: [recipe.pk]),
    ("recipe_create", lambda recipe: []),
    ("recipe_edit", lambda recipe: [recipe.pk]),
    ("ingredient_list", lambda recipe: []),
    ("ingredient_create", lambda recipe: []),
    ("ingredient_edit", lambda recipe: [recipe.ingredients.first().ingredient_id]),
]

OLD = {
    "back-link",
    "stacked-form",
    "form-row",
    "actions",
    "warning",
    "page-meta",
    "muted",
    "table-scroll",
    "compact",
    "btn-outline",
    "btn-small",
    "btn-danger-outline",
    "empty-slot",
    "missing",
    "toc",
    "outside-list",
    "note-form",
    "runbook-info-grid",
    "runbook-menu",
    "planner-table",
    "slot",
    "slot-course",
    "step-block",
    "qty",
}

CLASS_ATTRIBUTE = re.compile(r'class="([^"]*)"')


def old_classes(template_text: str) -> set[str]:
    """The old app.css classes a template still uses, plus "btn" for a bare `.btn`
    and "badge" for a badge without a Bootstrap colour. A colour from a template
    variable (`badge {{ ... }}`) can't be checked here and counts as one."""
    found: set[str] = set()
    for attribute in CLASS_ATTRIBUTE.findall(template_text):
        tokens = [t for t in attribute.split() if "{" not in t and "%" not in t]
        found |= OLD.intersection(tokens)
        if "btn" in tokens and not any(t.startswith("btn-") for t in tokens):
            found.add("btn")
        if (
            "badge" in tokens
            and "{{" not in attribute
            and not any(t.startswith(("text-bg-", "bg-")) for t in tokens)
        ):
            found.add("badge")
    return found


def test_old_classes_finds_the_old_ones() -> None:
    assert old_classes('<a class="btn">x</a>') == {"btn"}
    assert old_classes('<a class="btn btn-outline-primary">') == set()
    assert old_classes('<p class="muted page-meta">') == {"muted", "page-meta"}
    assert old_classes('<span class="badge">') == {"badge"}
    assert old_classes('<span class="badge text-bg-warning">') == set()
    assert old_classes('<span class="badge {{ colour }}">') == set()
    assert (
        old_classes('<a class="slot-chip{% if x %} slot-chip-empty{% endif %}">')
        == set()
    )


@pytest.mark.parametrize("path", CONVERTED_TEMPLATES)
def test_converted_template_has_no_old_classes(path: str) -> None:
    text = (TEMPLATES / path).read_text(encoding="utf-8")
    assert old_classes(text) == set()


@pytest.mark.django_db
@pytest.mark.parametrize("url_name,args", CONVERTED_PAGES)
def test_converted_page_has_one_h1_and_the_red_rule(
    url_name: str, args: Callable[[Camp], list]
) -> None:
    camp = make_camp()
    response = member_client(camp).get(reverse(url_name, args=args(camp)))
    assert response.status_code == 200
    html = response.content.decode()
    assert html.count("<h1") == 1
    assert not re.search(r"<h1[^>]*>\s*</h1>", html), "the h1 is empty"
    assert "page-rule" in html


@pytest.mark.django_db
@pytest.mark.parametrize("url_name,args", RECIPE_PAGES)
def test_recipe_page_has_one_h1_and_the_red_rule(
    url_name: str, args: Callable[[Recipe], list]
) -> None:
    client = account_client()
    recipe = make_recipe("Stoofpot", ingredients=[("Prei", "1", KG, PRODUCE)])
    recipe.author = User.objects.get(username="kok")
    recipe.save()
    response = client.get(reverse(url_name, args=args(recipe)))
    assert response.status_code == 200
    html = response.content.decode()
    assert html.count("<h1") == 1
    assert not re.search(r"<h1[^>]*>\s*</h1>", html), "the h1 is empty"
    assert "page-rule" in html


@pytest.mark.django_db
def test_camp_list_dates_are_short() -> None:
    camp = make_camp()
    client = member_client(camp)
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "nl"
    html = client.get(reverse("camp_list")).content.decode()
    assert "za 1 aug – wo 5 aug 2026" in html


@pytest.mark.django_db
def test_camp_list_empty_states() -> None:
    client = account_client()
    html = client.get(reverse("camp_list")).content.decode()
    assert "bi-people" in html
    assert "isn&#x27;t linked to a Chiro" in html or "isn't linked to a Chiro" in html
    chiro = Chiro.objects.create(name="Lege Chiro")
    Membership.objects.create(user=User.objects.get(username="kok"), chiro=chiro)
    html = client.get(reverse("camp_list")).content.decode()
    assert "bi-calendar-event" in html
    assert reverse("camp_create") in html


@pytest.mark.django_db
def test_edit_slot_select_has_a_label() -> None:
    camp = make_camp()
    url = reverse("edit_slot", args=[camp.pk, camp.start_date.isoformat(), "dinner"])
    html = member_client(camp).get(url).content.decode()
    assert 'for="id_recipe" class="form-label"' in html


@pytest.mark.django_db
def test_runbook_note_has_a_label() -> None:
    camp = make_camp()
    html = member_client(camp).get(reverse("runbook", args=[camp.pk])).content.decode()
    textarea = re.search(r"<textarea[^>]*>", html)
    assert textarea is not None
    textarea_id = re.search(r'id="([^"]+)"', textarea.group(0))
    assert textarea_id is not None
    assert re.search(rf'<label[^>]*for="{textarea_id.group(1)}"', html)


@pytest.mark.django_db
def test_camp_form_errors_show_a_summary_and_keep_input() -> None:
    camp = make_camp()
    data = {
        "name": "Foutkamp",
        "start_date": "2027-07-10",
        "end_date": "2027-07-01",
        "breakfast_time": "08:00",
        "lunch_time": "late",
        "teatime_time": "16:00",
        "dinner_time": "18:30",
        "groups-TOTAL_FORMS": "0",
        "groups-INITIAL_FORMS": "0",
    }
    response = member_client(camp).post(reverse("camp_edit", args=[camp.pk]), data)
    assert response.status_code == 200
    html = response.content.decode()
    assert "alert-danger" in html
    assert "is-invalid" in html
    assert "Foutkamp" in html


@pytest.mark.django_db
def test_example_camp_pages_render_for_a_member() -> None:
    example = Chiro.objects.create(name="Voorbeeld", is_example=True)
    camp = make_camp(chiro=example)
    client = account_client()
    for url_name in ("planner", "camp_edit", "runbook"):
        response = client.get(reverse(url_name, args=[camp.pk]))
        assert response.status_code == 200
        assert "alert-info" in response.content.decode()


@pytest.mark.django_db
def test_ingredient_form_errors_show_a_summary() -> None:
    client = account_client()
    make_recipe("Stoofpot", ingredients=[("Prei", "1", KG, PRODUCE)])
    response = client.post(
        reverse("ingredient_create"),
        {"name": "Prei", "unit": KG, "category": PRODUCE, "shop": "colruyt"},
    )
    assert response.status_code == 200
    html = response.content.decode()
    assert "alert-danger" in html
    assert "is-invalid" in html
