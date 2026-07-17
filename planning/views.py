"""Menu planner views (SPEC §9.3, §9.5)."""

import datetime
import logging

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from camps.models import Camp
from core.constants import MEAL_SLOTS, MealType
from core.pdf import render_pdf
from planning.forms import SlotForm
from planning.models import MenuEntry
from planning.services import scale_entry

logger = logging.getLogger(__name__)

MEAL_LABELS = dict(MealType.CHOICES)


def _parse_date(value: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise Http404(f"Invalid date: {value}") from exc


def _build_grid(camp: Camp) -> list[dict]:
    """Rows = camp days; each row has the four meals with their slots."""
    entries = {
        (e.date, e.meal_type, e.course): e
        for e in camp.menu_entries.select_related("recipe")
    }
    grid = []
    for day in camp.days:
        meals = []
        for meal_type in MealType.ORDER:
            cells = [
                {
                    "slot": slot,
                    "entry": entries.get((day, meal_type, slot.course)),
                }
                for slot in MEAL_SLOTS
                if slot.meal_type == meal_type
            ]
            meals.append(
                {
                    "meal_type": meal_type,
                    "label": MEAL_LABELS[meal_type],
                    "cells": cells,
                }
            )
        grid.append({"day": day, "meals": meals})
    return grid


def planner(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp, pk=camp_id)
    return render(
        request,
        "planning/planner.html",
        {"camp": camp, "grid": _build_grid(camp)},
    )


def edit_slot(
    request: HttpRequest, camp_id: int, date: str, meal_type: str
) -> HttpResponse:
    camp = get_object_or_404(Camp, pk=camp_id)
    day = _parse_date(date)
    course = request.GET.get("course", "")
    if meal_type not in MealType.ORDER:
        raise Http404(f"Unknown meal type: {meal_type}")

    entry = MenuEntry.objects.filter(
        camp=camp, date=day, meal_type=meal_type, course=course
    ).first()

    if request.method == "POST":
        form = SlotForm(request.POST, meal_type=meal_type, course=course)
        if form.is_valid():
            recipe = form.cleaned_data["recipe"]
            if recipe is None:
                if entry:
                    entry.delete()
                    logger.info("Cleared slot %s %s/%s", day, meal_type, course)
            else:
                if entry is None:
                    entry = MenuEntry(
                        camp=camp, date=day, meal_type=meal_type, course=course
                    )
                entry.recipe = recipe
                entry.full_clean()
                entry.save()
            return redirect("planner", camp_id=camp.pk)
    else:
        form = SlotForm(
            initial={"recipe": entry.recipe if entry else None},
            meal_type=meal_type,
            course=course,
        )

    scaled = scale_entry(entry, camp) if entry else None
    return render(
        request,
        "planning/edit_slot.html",
        {
            "camp": camp,
            "day": day,
            "meal_type": meal_type,
            "meal_label": MEAL_LABELS[meal_type],
            "course": course,
            "form": form,
            "entry": entry,
            "scaled": scaled,
        },
    )


def overview_pdf(request: HttpRequest, camp_id: int) -> HttpResponse:
    """Camp/day overview with scaled quantities per meal (SPEC §9.5)."""
    camp = get_object_or_404(Camp, pk=camp_id)
    grid = _build_grid(camp)
    for row in grid:
        for meal in row["meals"]:
            for cell in meal["cells"]:
                if cell["entry"]:
                    cell["scaled"] = scale_entry(cell["entry"], camp)
    return render_pdf(
        request,
        "planning/overview_print.html",
        {"camp": camp, "grid": grid},
        filename=f"{camp.name}-overview.pdf",
    )
