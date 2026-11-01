"""Camp pages: overview, create, edit and delete (SPEC §9.2)."""

import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from camps.forms import CampForm, DietaryNeedFormSet
from camps.models import Camp
from core.delete import confirm_delete

logger = logging.getLogger(__name__)


def camp_list(request: HttpRequest) -> HttpResponse:
    camps = Camp.objects.for_user(request.user)
    return render(
        request,
        "camps/camp_list.html",
        {
            "camps": camps.active(),
            "archived": camps.filter(is_archived=True),
            "has_chiro": request.user.chiros.exists(),
        },
    )


def _camp_form_page(request: HttpRequest, camp: Camp) -> HttpResponse:
    data = request.POST if request.method == "POST" else None
    form = CampForm(data, instance=camp, user=request.user)
    if data is not None and form.is_valid():
        saved = form.save()
        logger.info("%s saved camp %s", request.user, saved.pk)
        return redirect("planner", camp_id=saved.pk)
    return render(
        request,
        "camps/camp_form.html",
        {
            "camp": camp,
            "form": form,
            "can_delete": camp.pk and camp.can_delete(request.user),
        },
    )


def camp_create(request: HttpRequest) -> HttpResponse:
    if not request.user.chiros.exists():
        raise PermissionDenied("A camp belongs to a Chiro; you aren't linked to one.")
    return _camp_form_page(request, Camp())


def camp_edit(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    return _camp_form_page(request, camp)


@require_POST
def camp_archive(request: HttpRequest, camp_id: int) -> HttpResponse:
    """Archive or bring back; the button says which."""
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    camp.is_archived = not camp.is_archived
    camp.save(update_fields=["is_archived"])
    logger.info("%s set %s archived=%s", request.user, camp, camp.is_archived)
    return redirect("camp_list")


def camp_diets(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    data = request.POST if request.method == "POST" else None
    formset = DietaryNeedFormSet(data, queryset=camp.dietary_needs.all())
    if data is not None and formset.is_valid():
        formset.save_rows(camp=camp)
        return redirect("planner", camp_id=camp.pk)
    return render(
        request,
        "camps/rows_page.html",
        {
            "camp": camp,
            "formset": formset,
            "title": "Diets and allergies",
            "intro": "The planner warns when a planned recipe contains something "
            "these people can't eat. That relies on what ingredients are marked as "
            "containing, so always check labels yourself for allergies.",
        },
    )


def camp_delete(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    if not camp.can_delete(request.user):
        raise PermissionDenied("Only an admin of this Chiro can delete a camp.")
    return confirm_delete(
        request,
        camp,
        cancel_url=reverse("camp_edit", args=[camp.pk]),
        success_url=reverse("camp_list"),
        consequences=[
            f"{camp.menu_entries.count()} planned meals",
            f"{camp.shopping_trips.count()} shopping days",
            f"{camp.day_notes.count()} day notes",
            f"{camp.bills.count()} bills and their files",
            "The contact details and other runbook info",
        ],
    )
