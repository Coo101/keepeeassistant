"""Shopping list views (SPEC §9.4, §9.5)."""

import datetime
import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from camps.models import Camp
from core.pdf import render_pdf
from shopping.budget import build_budget
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
    trip_dates = {t.date for t in plan.camp.shopping_trips.all()}
    return render(
        request,
        "shopping/shopping.html",
        {
            "camp": camp,
            "plan": plan,
            "outside_entries": camp.entries_outside_dates(),
            "outside_trips": sorted(trip_dates - set(candidates)),
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
