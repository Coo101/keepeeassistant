"""Camp pages: overview, create, edit and delete (docs/spec/planning.md)."""

import logging

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from camps.access import get_camp
from camps.forms import (
    CampForm,
    DietaryNeedFormSet,
    camp_group_formset,
    initial_groups,
)
from camps.models import Camp, CampGroup
from core.constants import CHILD_PORTION_FACTOR
from core.delete import confirm_delete
from core.portions import format_quantity, portions
from core.rows import row_index

logger = logging.getLogger(__name__)


def camp_list(request: HttpRequest) -> HttpResponse:
    visible = Camp.objects.for_user(request.user)
    camps = visible.filter(chiro__is_example=False)
    return render(
        request,
        "camps/camp_list.html",
        {
            "camps": camps.active(),
            "archived": camps.filter(is_archived=True),
            "examples": visible.filter(chiro__is_example=True),
            "has_chiro": request.user.chiros.exists(),
        },
    )


def _camp_form_page(request: HttpRequest, camp: Camp) -> HttpResponse:
    data = request.POST if request.method == "POST" else None
    # Without JavaScript, "add group" posts the form: show it again with one more
    # empty row, keeping what was typed, and save nothing.
    adding_row = data is not None and data.get("add_row") == "groups"
    if adding_row:
        data = data.copy()
        data["groups-TOTAL_FORMS"] = str(row_index(data.get("groups-TOTAL_FORMS")) + 1)
    form = CampForm(data, instance=camp, user=request.user)
    groups = camp_group_formset(
        data,
        camp=camp,
        initial=None if camp.pk else initial_groups(request.user),
    )
    # A list, not a generator: show the errors of both at once.
    if (
        data is not None
        and not adding_row
        and all([form.is_valid(), groups.is_valid()])
    ):
        with transaction.atomic():
            saved = form.save()
            groups.save_rows(camp=saved)
            saved.update_headcount()
        logger.info("%s saved camp %s", request.user, saved.pk)
        return redirect("planner", camp_id=saved.pk)
    return render(
        request,
        "camps/camp_form.html",
        {
            "camp": camp,
            "form": form,
            "groups": groups,
            "totals": _group_totals(groups),
            "can_delete": camp.pk and camp.can_delete(request.user),
        },
    )


def _group_totals(groups) -> dict:
    """The totals the rows on the page add up to, typed or saved, so the form
    shows them without JavaScript too."""
    totals = {kind: 0 for kind in CampGroup.Kind.values}
    for row in groups:
        if row["DELETE"].value() or row["kind"].value() not in totals:
            continue
        try:
            totals[row["kind"].value()] += max(0, int(row["count"].value() or 0))
        except (TypeError, ValueError):
            continue
    children = totals[CampGroup.Kind.CHILDREN]
    teens = totals[CampGroup.Kind.TEENS]
    staff = totals[CampGroup.Kind.STAFF]
    return {
        "children": children,
        "teens": teens,
        "staff": staff,
        "portions": format_quantity(portions(children, teens, staff)),
        "child_factor": str(CHILD_PORTION_FACTOR),
    }


def camp_group_row(request: HttpRequest) -> HttpResponse:
    """One empty group row for the camp form (HTMX), numbered by the page's
    TOTAL_FORMS, which the response bumps out of band."""
    index = row_index(request.GET.get("groups-TOTAL_FORMS"))
    formset = camp_group_formset(camp=Camp())
    row = formset.empty_form
    row.prefix = formset.add_prefix(index)
    return render(
        request,
        "partials/_formset_row.html",
        {"row": row, "formset": formset, "total_forms": index + 1},
    )


def camp_create(request: HttpRequest) -> HttpResponse:
    if not request.user.chiros.exists():
        raise PermissionDenied(
            _("A camp belongs to a Chiro; you aren't linked to one.")
        )
    return _camp_form_page(request, Camp())


def camp_edit(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_camp(request, camp_id)
    return _camp_form_page(request, camp)


@require_POST
def camp_archive(request: HttpRequest, camp_id: int) -> HttpResponse:
    """Archive or bring back; the button says which."""
    camp = get_camp(request, camp_id)
    camp.is_archived = not camp.is_archived
    camp.save(update_fields=["is_archived"])
    logger.info("%s set %s archived=%s", request.user, camp, camp.is_archived)
    return redirect("camp_list")


def camp_diets(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_camp(request, camp_id)
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
            "title": _("Diets and allergies"),
            "intro": _(
                "The planner warns when a planned recipe contains something "
                "these people can't eat. That relies on what ingredients are marked "
                "as containing, so always check labels yourself for allergies."
            ),
        },
    )


def camp_delete(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = get_camp(request, camp_id)
    if not camp.can_delete(request.user):
        raise PermissionDenied(_("Only an admin of this Chiro can delete a camp."))
    return confirm_delete(
        request,
        camp,
        cancel_url=reverse("camp_edit", args=[camp.pk]),
        success_url=reverse("camp_list"),
        consequences=[
            _("%(count)d planned meals") % {"count": camp.menu_entries.count()},
            _("%(count)d shopping days") % {"count": camp.shopping_trips.count()},
            _("%(count)d day notes") % {"count": camp.day_notes.count()},
            _("%(count)d bills and their files") % {"count": camp.bills.count()},
            _("%(count)d kitchen utilities it needs")
            % {"count": camp.utensil_needs.count()},
            _("The contact details and other runbook info"),
        ],
    )
