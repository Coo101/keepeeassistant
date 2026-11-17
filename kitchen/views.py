"""The Chiro's stock (kitchen utilities and food) and a camp's needs
(docs/spec/kitchen.md, docs/spec/shopping.md)."""

import logging

from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from camps.access import get_camp, get_chiro
from core.rows import row_index
from kitchen.forms import NAMES_LIST_ID, NeedFormSet, StockFormSet
from kitchen.services import camp_needs, save_needs
from recipes.models import Ingredient
from shopping.forms import PantryFormSet
from shopping.models import PantryItem

logger = logging.getLogger(__name__)

PANTRY_PREFIX = "pantry"
# NeedFormSet keeps Django's default prefix.
NEEDS_PREFIX = "form"


def _ingredient_choices() -> list[tuple]:
    """One query for the pantry's dropdowns, instead of one per row."""
    return [("", "---------")] + [
        (ingredient.pk, str(ingredient)) for ingredient in Ingredient.objects.all()
    ]


def _with_one_more_row(data: QueryDict, prefix: str) -> QueryDict:
    """Without JavaScript, "add a row" posts the form: show it again with one more
    empty row, keeping what was typed, and save nothing."""
    data = data.copy()
    total = f"{prefix}-TOTAL_FORMS"
    data[total] = str(row_index(data.get(total)) + 1)
    return data


def _empty_row(request: HttpRequest, formset, prefix: str) -> tuple:
    """One empty row (HTMX), numbered by the page's TOTAL_FORMS, which the response
    bumps out of band."""
    index = row_index(request.GET.get(f"{prefix}-TOTAL_FORMS"))
    row = formset.empty_form
    row.prefix = formset.add_prefix(index)
    return row, index


def chiro_stock(request: HttpRequest, chiro_id: int) -> HttpResponse:
    """Two tables, each its own form: the utilities and the food (pantry)."""
    chiro = get_chiro(request, chiro_id)
    section = (
        request.POST.get("section", "utensils") if request.method == "POST" else ""
    )
    pantry_data = request.POST if section == "pantry" else None
    adding_row = pantry_data is not None and pantry_data.get("add_row") == PANTRY_PREFIX
    if adding_row:
        pantry_data = _with_one_more_row(pantry_data, PANTRY_PREFIX)
    utensils = StockFormSet(
        request.POST if section == "utensils" else None,
        queryset=chiro.utensils.prefetch_related("camp_needs__camp"),
    )
    pantry = PantryFormSet(
        pantry_data,
        queryset=chiro.pantry_items.select_related("ingredient"),
        prefix=PANTRY_PREFIX,
    )
    choices = _ingredient_choices()
    for form in [*pantry.forms, pantry.empty_form]:
        form.fields["ingredient"].choices = choices

    if section == "pantry" and not adding_row and pantry.is_valid():
        pantry.save_rows(chiro=chiro)
        logger.info("%s updated the pantry of %s", request.user, chiro)
        return redirect(reverse("chiro_stock", args=[chiro.pk]) + "#pantry")
    if section == "utensils" and utensils.is_valid():
        try:
            with transaction.atomic():
                rows = utensils.save(commit=False)
                for row in utensils.deleted_objects:
                    row.delete()
                for row in rows:
                    row.chiro = chiro
                    row.save()
        except IntegrityError:
            # Two items swapping names in one save.
            utensils.non_form_errors().append(
                _("Two items can't swap names in one save. Rename one first.")
            )
        else:
            logger.info("%s updated the kitchen stock of %s", request.user, chiro)
            return redirect("chiro_stock", chiro_id=chiro.pk)
    return render(
        request,
        "kitchen/stock.html",
        {
            "chiro": chiro,
            "formset": utensils,
            "pantry": pantry,
            "is_member": request.user.chiros.filter(pk=chiro.pk).exists(),
        },
    )


def pantry_row(request: HttpRequest, chiro_id: int) -> HttpResponse:
    """One empty pantry row for the stock page (HTMX)."""
    get_chiro(request, chiro_id)
    formset = PantryFormSet(queryset=PantryItem.objects.none(), prefix=PANTRY_PREFIX)
    row, index = _empty_row(request, formset, PANTRY_PREFIX)
    row.fields["ingredient"].choices = _ingredient_choices()
    return render(
        request,
        "partials/_formset_row.html",
        {"row": row, "formset": formset, "total_forms": index + 1},
    )


def camp_utensils(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_camp(request, camp_id)
    needs = camp_needs(camp)
    data = request.POST if request.method == "POST" else None
    adding_row = data is not None and data.get("add_row") == NEEDS_PREFIX
    if adding_row:
        data = _with_one_more_row(data, NEEDS_PREFIX)
    formset = NeedFormSet(
        data,
        initial=[{"name": need.utensil.name, "needed": need.needed} for need in needs],
    )
    if data is not None and not adding_row and formset.is_valid():
        save_needs(
            camp,
            [
                (form.cleaned_data["name"], form.cleaned_data["needed"])
                for form in formset.kept_forms
            ],
        )
        logger.info("%s updated the kitchen utilities of %s", request.user, camp)
        return redirect("camp_utensils", camp_id=camp.pk)
    return render(
        request,
        "kitchen/camp_utensils.html",
        {
            "camp": camp,
            "formset": formset,
            "needs": needs,
            "to_buy": [need for need in needs if need.to_buy],
            "names": camp.chiro.utensils.values_list("name", flat=True),
            "names_list_id": NAMES_LIST_ID,
        },
    )


def camp_utensil_row(request: HttpRequest, camp_id: int) -> HttpResponse:
    """One empty row for a camp's kitchen utilities (HTMX)."""
    get_camp(request, camp_id)
    formset = NeedFormSet()
    row, index = _empty_row(request, formset, NEEDS_PREFIX)
    return render(
        request,
        "partials/_formset_row.html",
        {"row": row, "formset": formset, "total_forms": index + 1},
    )
