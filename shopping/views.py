"""Shopping list views (SPEC §9.4, §9.5)."""

import datetime
import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from camps.models import Camp
from core.pdf import render_pdf
from recipes.models import Ingredient
from shopping.budget import build_budget
from shopping.forms import PantryFormSet
from shopping.models import ShoppingTrip
from shopping.services import build_shopping_plan

logger = logging.getLogger(__name__)

# Offer trip dates from a few days before camp start (arrival-eve shop, SPEC §8)
PRE_CAMP_DAYS = 3


def _candidate_dates(camp: Camp) -> list[datetime.date]:
    first = camp.start_date - datetime.timedelta(days=PRE_CAMP_DAYS)
    n = (camp.end_date - first).days + 1
    return [first + datetime.timedelta(days=i) for i in range(n)]


def shopping(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    candidates = _candidate_dates(camp)

    if request.method == "POST":
        selected: set[datetime.date] = set()
        for value in request.POST.getlist("trip_dates"):
            try:
                selected.add(datetime.date.fromisoformat(value))
            except ValueError:
                logger.warning("Ignoring invalid trip date %r", value)
        selected &= set(candidates)
        # Trips outside the offered dates weren't on the form: keep them.
        camp.shopping_trips.filter(date__in=candidates).exclude(
            date__in=selected
        ).delete()
        existing = set(camp.shopping_trips.values_list("date", flat=True))
        ShoppingTrip.objects.bulk_create(
            ShoppingTrip(camp=camp, date=d) for d in selected - existing
        )
        return redirect("shopping", camp_id=camp.pk)

    plan = build_shopping_plan(camp)
    trips = list(plan.camp.shopping_trips.all())
    trip_dates = {t.date for t in trips}
    return render(
        request,
        "shopping/shopping.html",
        {
            "camp": camp,
            "plan": plan,
            "outside_entries": camp.entries_outside_dates(),
            "outside_trips": sorted(
                (t for t in trips if t.date not in candidates),
                key=lambda t: t.date,
            ),
            "candidates": [
                {
                    "date": d,
                    "selected": d in trip_dates,
                    "pre_camp": d < camp.start_date,
                }
                for d in candidates
            ],
        },
    )


@require_POST
def remove_outside_trip(
    request: HttpRequest, camp_id: int, trip_id: int
) -> HttpResponse:
    """Days on the form are simply unticked; this is for the ones that aren't."""
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    trips = camp.shopping_trips.exclude(date__in=_candidate_dates(camp))
    trip = get_object_or_404(trips, pk=trip_id)
    logger.info("%s removed shopping day %s of %s", request.user, trip.date, camp)
    trip.delete()
    return redirect("shopping", camp_id=camp.pk)


def pantry(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    data = request.POST if request.method == "POST" else None
    formset = PantryFormSet(
        data, queryset=camp.pantry_items.select_related("ingredient")
    )
    # One query for the dropdown, instead of one per row.
    choices = [("", "---------")] + [
        (ingredient.pk, str(ingredient)) for ingredient in Ingredient.objects.all()
    ]
    for form in [*formset.forms, formset.empty_form]:
        form.fields["ingredient"].choices = choices
    if data is not None and formset.is_valid():
        formset.save_rows(camp=camp)
        return redirect("shopping", camp_id=camp.pk)
    return render(
        request,
        "camps/rows_page.html",
        {
            "camp": camp,
            "formset": formset,
            "title": "Pantry",
            "intro": "What you already have, in the ingredient's unit. It's taken "
            "off the shopping lists and the budget, starting with the first trip.",
        },
    )


def budget(request: HttpRequest, camp_id: int) -> HttpResponse:
    """Estimated cost per shopping trip based on ingredient prices."""
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    return render(
        request,
        "shopping/budget.html",
        {"camp": camp, "budget": build_budget(camp)},
    )


def shopping_pdf(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    plan = build_shopping_plan(camp)
    return render_pdf(
        request,
        "shopping/shopping_print.html",
        {"camp": camp, "plan": plan},
        filename=f"{camp.name}-shopping-lists.pdf",
    )
