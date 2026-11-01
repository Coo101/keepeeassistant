"""Camp pages: overview, create, edit and delete (SPEC §9.2)."""

import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from camps.forms import CampForm
from camps.models import Camp
from core.delete import confirm_delete

logger = logging.getLogger(__name__)


def camp_list(request: HttpRequest) -> HttpResponse:
    camps = Camp.objects.for_user(request.user)
    return render(
        request,
        "camps/camp_list.html",
        {"camps": camps, "has_chiro": request.user.chiros.exists()},
    )


def _camp_form_page(request: HttpRequest, camp: Camp) -> HttpResponse:
    data = request.POST if request.method == "POST" else None
    form = CampForm(data, instance=camp, user=request.user)
    if data is not None and form.is_valid():
        saved = form.save()
        logger.info("%s saved camp %s", request.user, saved.pk)
        return redirect("planner", camp_id=saved.pk)
    return render(request, "camps/camp_form.html", {"camp": camp, "form": form})


def camp_create(request: HttpRequest) -> HttpResponse:
    if not request.user.chiros.exists():
        raise PermissionDenied("A camp belongs to a Chiro; you aren't linked to one.")
    return _camp_form_page(request, Camp())


def camp_edit(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    return _camp_form_page(request, camp)


def camp_delete(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_object_or_404(Camp.objects.for_user(request.user), pk=camp_id)
    return confirm_delete(
        request,
        camp,
        cancel_url=reverse("camp_edit", args=[camp.pk]),
        success_url=reverse("camp_list"),
        consequences=[
            f"{camp.menu_entries.count()} planned meals",
            f"{camp.shopping_trips.count()} shopping days",
            f"{camp.day_notes.count()} day notes",
            "The contact details and other runbook info",
        ],
    )
