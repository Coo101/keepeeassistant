"""Menu planner views (SPEC §9.3, §9.5)."""

import datetime
import logging

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from camps.models import Camp, DayNote
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


def _build_grid(camp: Camp, with_recipe_details: bool = False) -> list[dict]:
    """Rows = camp days; each row has the four meals with their slots.

    `with_recipe_details` prefetches ingredients and steps for callers that
    render them (runbook, overview PDF); the plain grid only needs names.
    """
    queryset = camp.menu_entries.select_related("recipe")
    if with_recipe_details:
        queryset = queryset.prefetch_related(
            "recipe__ingredients__ingredient", "recipe__steps"
        )
    entries = {(e.date, e.meal_type, e.course): e for e in queryset}
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
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    return render(
        request,
        "planning/planner.html",
        {
            "camp": camp,
            "grid": _build_grid(camp),
            "outside_entries": camp.entries_outside_dates(),
        },
    )


def edit_slot(
    request: HttpRequest, camp_id: int, date: str, meal_type: str
) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
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


@require_POST
def remove_outside_entry(
    request: HttpRequest, camp_id: int, entry_id: int
) -> HttpResponse:
    """Meals outside the camp dates have no slot in the grid to clear."""
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    entry = get_object_or_404(camp.entries_outside_dates(), pk=entry_id)
    logger.info("%s removed %s", request.user, entry)
    entry.delete()
    back = "shopping" if request.POST.get("back") == "shopping" else "planner"
    return redirect(back, camp_id=camp.pk)


def _runbook_days(camp: Camp) -> list[dict]:
    """Day sections for the runbook: menu grid + scaled quantities, steps
    per planned recipe, and the day's note."""
    grid = _build_grid(camp, with_recipe_details=True)
    notes = {note.date: note for note in camp.day_notes.all()}
    days = []
    for number, row in enumerate(grid, start=1):
        step_blocks = []
        for meal in row["meals"]:
            for cell in meal["cells"]:
                entry = cell["entry"]
                if not entry:
                    continue
                cell["scaled"] = scale_entry(entry, camp)
                steps = list(entry.recipe.steps.all())
                if steps:
                    step_blocks.append(
                        {
                            "meal_label": meal["label"],
                            "recipe": entry.recipe,
                            "steps": steps,
                        }
                    )
        note = notes.get(row["day"])
        days.append(
            {
                "number": number,
                "date": row["day"],
                "meals": row["meals"],
                "step_blocks": step_blocks,
                "note_text": note.text if note else "",
            }
        )
    return days


def runbook(request: HttpRequest, camp_id: int) -> HttpResponse:
    """Digital draaiboek: front-page info, per-day menu/steps/notes."""
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)

    if request.method == "POST":
        day = _parse_date(request.POST.get("date", ""))
        if day not in camp.days:
            raise Http404(f"{day} is not a camp day")
        text = request.POST.get("text", "").strip()
        DayNote.objects.update_or_create(camp=camp, date=day, defaults={"text": text})
        logger.info("Saved runbook note for %s %s", camp, day)
        anchor = f"#day-{day.isoformat()}"
        return redirect(reverse("runbook", args=[camp.pk]) + anchor)

    return render(
        request,
        "planning/runbook.html",
        {"camp": camp, "days": _runbook_days(camp)},
    )


def runbook_pdf(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    return render_pdf(
        request,
        "planning/runbook_print.html",
        {"camp": camp, "days": _runbook_days(camp)},
        filename=f"{camp.name}-draaiboek.pdf",
    )


def overview_pdf(request: HttpRequest, camp_id: int) -> HttpResponse:
    """Camp/day overview with scaled quantities per meal (SPEC §9.5)."""
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    grid = _build_grid(camp, with_recipe_details=True)
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
