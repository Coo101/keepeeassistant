"""Bills per camp: upload, review and what was paid (docs/spec/finance.md)."""

import logging

from django.db import transaction
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.models import Chiro
from bills.forms import BillLineForm, BillLineFormSet, BillUploadForm
from bills.models import Bill
from bills.reading import read_text_pdf
from bills.report import build_report
from bills.services import apply_review, camp_spending
from camps.access import get_camp
from camps.models import Camp
from core.delete import confirm_delete
from core.pdf import render_pdf
from kitchen.services import NEW_ITEM, add_to_stock
from recipes.forms import IngredientForm
from recipes.models import Ingredient
from recipes.views import NEW_INGREDIENT_PREFIX

logger = logging.getLogger(__name__)


def _camp(request: HttpRequest, camp_id: int) -> Camp:
    return get_camp(request, camp_id)


def _bill(request: HttpRequest, camp_id: int, bill_id: int) -> Bill:
    return get_object_or_404(_camp(request, camp_id).bills, pk=bill_id)


def bill_list(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = _camp(request, camp_id)
    form = BillUploadForm(
        request.POST or None,
        request.FILES or None,
        initial={"shop": None},
    )
    if request.method == "POST" and form.is_valid():
        bill = form.save(commit=False)
        bill.camp = camp
        bill.uploaded_by = request.user
        bill.original_name = form.cleaned_data["file"].name[:255]
        bill.save()
        logger.info("%s uploaded bill %s", request.user, bill.pk)
        read_text_pdf(bill, text=form.pdf_text)
        return redirect("bill_detail", camp_id=camp.pk, bill_id=bill.pk)
    return render(
        request,
        "bills/bill_list.html",
        {
            "camp": camp,
            "form": form,
            "bills": camp.bills.prefetch_related("lines"),
            "spending": camp_spending(camp),
        },
    )


def bill_detail(request: HttpRequest, camp_id: int, bill_id: int) -> HttpResponse:
    """The review: nothing changes a price before someone saves this page."""
    bill = _bill(request, camp_id, bill_id)
    data = request.POST if request.method == "POST" else None
    formset = BillLineFormSet(
        data, queryset=bill.lines.select_related("ingredient", "utensil")
    )
    chiro = bill.camp.chiro
    # One query per dropdown, instead of one per line.
    choices = [("", "---------")] + [
        (ingredient.pk, str(ingredient)) for ingredient in Ingredient.objects.all()
    ]
    stock_choices = [("", "—"), (NEW_ITEM, _("New item"))] + [
        (str(utensil.pk), utensil.name) for utensil in chiro.utensils.all()
    ]
    for form in [*formset.forms, formset.empty_form]:
        form.fields["ingredient"].choices = choices
        form.fields["stock"].choices = stock_choices

    if data is not None and formset.is_valid():
        with transaction.atomic():
            lines = formset.save(commit=False)
            for line in lines:
                line.bill = bill
                line.save()
            for line in formset.deleted_objects:
                line.delete()
            for form in formset.forms:
                _add_to_stock(form, chiro)
            apply_review(bill)
        logger.info("%s reviewed bill %s", request.user, bill.pk)
        return redirect("bill_list", camp_id=camp_id)
    total = bill.lines_total()
    return render(
        request,
        "bills/bill_detail.html",
        {
            "camp": bill.camp,
            "bill": bill,
            "formset": formset,
            "total": total,
            "total_differs": (
                bill.printed_total is not None and bill.printed_total != total
            ),
            "new_ingredient_form": IngredientForm(
                prefix=NEW_INGREDIENT_PREFIX, user=request.user
            ),
        },
    )


def _add_to_stock(form: BillLineForm, chiro: Chiro) -> None:
    """Each line goes into the stock once, however often the review is saved."""
    line = form.instance
    choice = form.cleaned_data.get("stock")
    if not choice or not line.pk or line.utensil_id or line.skipped:
        return
    if form.cleaned_data.get("DELETE"):
        return
    line.utensil = add_to_stock(chiro, choice, line.description, line.quantity)
    line.save(update_fields=["utensil"])


def bill_file(request: HttpRequest, camp_id: int, bill_id: int) -> FileResponse:
    bill = _bill(request, camp_id, bill_id)
    if not bill.file:
        raise Http404("The file was removed")
    # Always a download: an uploaded file must never run in this site's pages.
    return FileResponse(
        bill.file.open("rb"),
        as_attachment=True,
        filename=bill.original_name or "bill",
    )


@require_POST
def bill_remove_file(request: HttpRequest, camp_id: int, bill_id: int) -> HttpResponse:
    """Keep the amounts, drop the document with the personal data."""
    bill = _bill(request, camp_id, bill_id)
    bill.file.delete(save=False)
    bill.file = ""
    if bill.status == Bill.Status.FAILED:
        bill.status = Bill.Status.REVIEW
    bill.save(update_fields=["file", "status"])
    logger.info("%s removed the file of bill %s", request.user, bill.pk)
    return redirect("bill_detail", camp_id=camp_id, bill_id=bill.pk)


def bill_delete(request: HttpRequest, camp_id: int, bill_id: int) -> HttpResponse:
    bill = _bill(request, camp_id, bill_id)
    return confirm_delete(
        request,
        bill,
        cancel_url=reverse("bill_detail", args=[camp_id, bill.pk]),
        success_url=reverse("bill_list", args=[camp_id]),
        consequences=[
            _("The file, if it's still there"),
            _("Its lines, and the camp prices they set"),
        ],
    )


def report(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = _camp(request, camp_id)
    return render(
        request, "bills/report.html", {"camp": camp, "report": build_report(camp)}
    )


def report_pdf(request: HttpRequest, camp_id: int) -> HttpResponse:
    camp = _camp(request, camp_id)
    return render_pdf(
        request,
        "bills/report_print.html",
        {"camp": camp, "report": build_report(camp)},
        filename=_("%(camp)s-financial-report.pdf") % {"camp": camp.name},
    )
