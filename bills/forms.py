"""Forms for uploading and reviewing bills (SPEC §9.10)."""

from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory
from PIL import Image

from bills.models import Bill, BillLine

ALLOWED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_UNIT_PRICE = 9999


class BillUploadForm(forms.ModelForm):
    file = forms.FileField(
        label="PDF or photo",
        widget=forms.ClearableFileInput(
            attrs={"accept": ",".join(sorted(ALLOWED_SUFFIXES))}
        ),
    )

    class Meta:
        model = Bill
        fields = ["file", "shop", "date"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def clean_file(self):
        upload = self.cleaned_data["file"]
        suffix = Path(upload.name).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise ValidationError("Upload a PDF, JPG, PNG or WebP file.")
        if upload.size > MAX_UPLOAD_BYTES:
            raise ValidationError("The file can be 15 MB at most.")
        if suffix == ".pdf":
            valid = upload.read(5) == b"%PDF-"
        else:
            try:
                Image.open(upload).verify()
                valid = True
            # Pillow raises several types on files that aren't images.
            except Exception:
                valid = False
        upload.seek(0)
        if not valid:
            raise ValidationError("This file doesn't look like a real PDF or image.")
        return upload


class BillLineForm(forms.ModelForm):
    class Meta:
        model = BillLine
        fields = [
            "description",
            "quantity",
            "pack_amount",
            "line_total",
            "category",
            "ingredient",
            "skipped",
        ]

    def clean(self) -> dict:
        cleaned = super().clean()
        if cleaned.get("skipped") or cleaned.get("category") != BillLine.Category.FOOD:
            return cleaned
        if cleaned.get("ingredient") and not cleaned.get("pack_amount"):
            self.add_error("pack_amount", "How much is one item, in this unit?")
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
            self.add_error("pack_amount", "That makes the price per unit too high.")
        return cleaned


BillLineFormSet = modelformset_factory(
    BillLine, form=BillLineForm, extra=1, can_delete=True
)
