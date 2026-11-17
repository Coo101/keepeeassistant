"""The shared UI components and filters (docs/ui-guidelines.md)."""

import datetime

import pytest
from django import forms
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation

from core.constants import FoodTag
from pages.templatetags.ui import short_date, table_input
from recipes.forms import IngredientForm, StepFormSet
from recipes.models import Recipe
from tests.factories import make_camp


class _NameForm(forms.Form):
    name = forms.CharField(label="Name")
    end = forms.DateField(label="End")

    def clean(self):
        raise forms.ValidationError("End before start.")


class _ValidForm(forms.Form):
    note = forms.CharField(required=False)


def test_page_header_action() -> None:
    html = render_to_string(
        "components/page_header.html",
        {"title": "Camps", "action_url": "/x/", "action_label": "New"},
    )
    assert 'href="/x/"' in html
    assert "btn btn-primary" in html
    assert "<h1" in html and "page-rule" in html


def test_page_header_without_action_has_no_link() -> None:
    html = render_to_string("components/page_header.html", {"title": "Camps"})
    assert "<a" not in html


def test_page_header_outline_action() -> None:
    html = render_to_string(
        "components/page_header.html",
        {
            "title": "T",
            "action_url": "/x/",
            "action_label": "PDF",
            "action_style": "outline",
        },
    )
    assert "btn-outline-primary" in html


def test_back_link() -> None:
    html = render_to_string(
        "components/back_link.html", {"url": "/b/", "label": "Back"}
    )
    assert 'href="/b/"' in html and "bi-arrow-left" in html and "Back" in html


def test_form_errors_only_with_errors() -> None:
    invalid = _NameForm({"name": "", "end": "x"})
    html = render_to_string("components/form_errors.html", {"form": invalid})
    assert "alert-danger" in html
    assert "End before start." in html
    valid = forms.Form({})
    assert (
        render_to_string("components/form_errors.html", {"form": valid}).strip() == ""
    )


def test_empty_state_icon_is_navy() -> None:
    html = render_to_string(
        "components/empty_state.html", {"icon": "people", "text": "Nobody yet."}
    )
    assert "bi-people" in html and "text-primary" in html


def test_short_date_in_dutch() -> None:
    with translation.override("nl"):
        assert short_date(datetime.date(2026, 8, 1)) == "za 1 aug"
        assert short_date(datetime.date(2026, 8, 1), "year") == "za 1 aug 2026"


def test_short_date_in_english() -> None:
    with translation.override("en"):
        assert short_date(datetime.date(2026, 8, 1)) == "Sat 1 Aug"


class _RowForm(forms.Form):
    name = forms.CharField(label="Name")
    kind = forms.ChoiceField(label="Kind", choices=[("a", "A"), ("b", "B")])
    remove = forms.BooleanField(label="Delete", required=False)


def test_table_input_classes() -> None:
    form = _RowForm()
    name = str(table_input(form["name"]))
    assert 'class="form-control form-control-sm"' in name
    assert 'aria-label="Name"' in name
    assert "form-select form-select-sm" in str(table_input(form["kind"]))
    assert "form-check-input" in str(table_input(form["remove"]))


def test_table_input_marks_errors() -> None:
    form = _RowForm({"name": "", "kind": "a"})
    assert not form.is_valid()
    assert "is-invalid" in str(table_input(form["name"]))
    assert "is-invalid" not in str(table_input(form["kind"]))


@pytest.mark.django_db
def test_camp_nav_marks_the_active_page() -> None:
    camp = make_camp()
    html = render_to_string(
        "components/camp_nav.html", {"camp": camp, "active": "runbook"}
    )
    urls = [
        reverse(name, args=[camp.pk])
        for name in (
            "planner",
            "shopping",
            "runbook",
            "bill_list",
            "financial_report",
            "camp_diets",
            "camp_utensils",
            "camp_edit",
        )
    ]
    positions = [html.index(f'href="{url}"') for url in urls]
    assert positions == sorted(positions)
    assert html.count('aria-current="page"') == 1
    runbook_link = html[
        html.index(f'href="{urls[2]}"') - 200 : html.index(f'href="{urls[2]}"') + 200
    ]
    assert 'aria-current="page"' in runbook_link
    assert "nav-link active" in runbook_link


def test_page_header_badge() -> None:
    html = render_to_string(
        "components/page_header.html", {"title": "Soup", "badge": "read-only"}
    )
    h1 = html[html.index("<h1") : html.index("</h1>")]
    assert "text-bg-secondary" in h1 and "read-only" in h1
    plain = render_to_string("components/page_header.html", {"title": "Soup"})
    assert "badge" not in plain


@pytest.mark.django_db
def test_form_errors_sees_the_second_formset() -> None:
    steps = StepFormSet(
        {
            "steps-TOTAL_FORMS": "1",
            "steps-INITIAL_FORMS": "0",
            "steps-MIN_NUM_FORMS": "0",
            "steps-MAX_NUM_FORMS": "1000",
            "steps-0-order": "1",
            "steps-0-instruction": "",
            "steps-0-duration_minutes": "5",
        },
        prefix="steps",
        instance=Recipe(),
    )
    assert not steps.is_valid()
    html = render_to_string(
        "components/form_errors.html",
        {"form": _ValidForm({}), "formset": None, "formset2": steps},
    )
    assert "alert-danger" in html


@pytest.mark.django_db
def test_checkbox_chips() -> None:
    first = FoodTag.CHOICES[0][0]
    form = IngredientForm(user=None, initial={"tags": [first]})
    html = render_to_string("components/checkbox_chips.html", {"field": form["tags"]})
    assert html.count("<legend") == 1
    assert html.count("form-check-input") == len(FoodTag.CHOICES)
    assert html.count(" checked") == 1
