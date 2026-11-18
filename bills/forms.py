"""Forms for uploading and reviewing bills (docs/spec/finance.md)."""

from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory
from django.utils.translation import gettext_lazy as _

from bills.models import Bill, BillLine
from bills.reading import pdf_text

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_UNIT_PRICE = 9999


class BillUploadForm(forms.ModelForm):
    file = forms.FileField(
        label=_("PDF with text"),
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf"}),
    )

    class Meta:
        model = Bill
        fields = ["file", "shop", "date"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def clean_file(self):
        """Only PDFs with real text: the app reads them in Python (D21)."""
        upload = self.cleaned_data["file"]
        if Path(upload.name).suffix.lower() != ".pdf":
            raise ValidationError(
                _("Upload a PDF. Turn a photo into a PDF with text first.")
            )
        if upload.size > MAX_UPLOAD_BYTES:
            raise ValidationError(_("The file can be 15 MB at most."))
        # Kept for reading the lines, so the PDF is only parsed once.
        self.pdf_text = ""
        if upload.read(5) == b"%PDF-":
            upload.seek(0)
            self.pdf_text = pdf_text(upload)
        upload.seek(0)
        if not self.pdf_text.strip():
            raise ValidationError(
                _(
                    "This PDF has no text the app can read. Make a PDF with text "
                    "(with text recognition), or ask for the shop's digital invoice."
                )
            )
        return upload


class BillLineForm(forms.ModelForm):
    # Choices are the Chiro's stock, set by the view; once a line is in the stock
    # the page shows where it went instead.
    stock = forms.ChoiceField(required=False, label=_("Add to stock"))

    class Meta:
        model = BillLine
        fields = [
            "description",
            "ingredient",
            "category",
            "quantity",
            "pack_amount",
            "line_total",
            "skipped",
        ]

    def clean(self) -> dict:
        cleaned = super().clean()
        category = cleaned.get("category")
        if cleaned.get("stock") and category != BillLine.Category.UTENSILS:
            self.add_error("stock", _("Only kitchen utilities go into the stock."))
        if cleaned.get("skipped") or category != BillLine.Category.FOOD:
            return cleaned
        if cleaned.get("ingredient") and not cleaned.get("pack_amount"):
            self.add_error("pack_amount", _("How much is one item, in this unit?"))
        quantity = cleaned.get("quantity")
        amount = cleaned.get("pack_amount")
        total = cleaned.get("line_total")
        if (
            quantity
            and amount
            and total
            and cleaned.get("ingredient")
            and total / (quantity * amount) > MAX_UNIT_PRICE
        ):
            self.add_error("pack_amount", _("That makes the price per unit too high."))
        return cleaned


BillLineFormSet = modelformset_factory(
    BillLine, form=BillLineForm, extra=1, can_delete=True
)
