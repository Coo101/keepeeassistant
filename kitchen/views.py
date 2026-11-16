"""The Chiro's stock (kitchen utilities and food) and a camp's needs
(docs/spec/kitchen.md, docs/spec/shopping.md)."""

import logging

from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from camps.access import get_camp, get_chiro
from kitchen.forms import NAMES_LIST_ID, NeedFormSet, StockFormSet
from kitchen.services import camp_needs, save_needs
from recipes.models import Ingredient
from shopping.forms import PantryFormSet

logger = logging.getLogger(__name__)


def chiro_stock(request: HttpRequest, chiro_id: int) -> HttpResponse:
    """Two tables, each its own form: the utilities and the food (pantry)."""
    chiro = get_chiro(request, chiro_id)
    section = (
        request.POST.get("section", "utensils") if request.method == "POST" else ""
    )
    utensils = StockFormSet(
        request.POST if section == "utensils" else None,
        queryset=chiro.utensils.prefetch_related("camp_needs__camp"),
    )
    pantry = PantryFormSet(
        request.POST if section == "pantry" else None,
        queryset=chiro.pantry_items.select_related("ingredient"),
        prefix="pantry",
    )
    # One query for the dropdown, instead of one per row.
    choices = [("", "---------")] + [
        (ingredient.pk, str(ingredient)) for ingredient in Ingredient.objects.all()
    ]
    for form in [*pantry.forms, pantry.empty_form]:
        form.fields["ingredient"].choices = choices

    if section == "pantry" and pantry.is_valid():
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


def camp_utensils(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_camp(request, camp_id)
    needs = camp_needs(camp)
    data = request.POST if request.method == "POST" else None
    formset = NeedFormSet(
        data,
        initial=[{"name": need.utensil.name, "needed": need.needed} for need in needs],
    )
    if data is not None and formset.is_valid():
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
