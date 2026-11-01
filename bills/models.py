"""Bills and what a camp actually paid (SPEC §9.10)."""

import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from camps.models import Camp
from core.constants import Shop, Unit
from recipes.models import Ingredient, IngredientPrice


def _bill_path(bill: "Bill", filename: str) -> str:
    # Never the uploaded name: it can hold personal data or odd characters.
    return f"bills/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Bill(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting to be read"
        FAILED = "failed", "Couldn't be read"
        REVIEW = "review", "To review"
        DONE = "done", "Reviewed"

    camp = models.ForeignKey(Camp, on_delete=models.CASCADE, related_name="bills")
    # Empty once someone removes the file; the lines stay.
    file = models.FileField(upload_to=_bill_path, blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    shop = models.CharField(max_length=12, choices=Shop.CHOICES)
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.WAITING
    )
    error = models.CharField(max_length=300, blank=True)
    printed_total = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-pk"]

    def __str__(self) -> str:
        return f"{self.get_shop_display()} bill of {self.date}"

    def lines_total(self) -> Decimal:
        return sum(
            (line.line_total for line in self.lines.all() if not line.skipped),
            Decimal("0"),
        )


class BillLine(models.Model):
    class Category(models.TextChoices):
        FOOD = "food", "Camp food"
        ACTIVITY = "activity", "Activity"
        PERSONAL = "personal", "Personal"
        OTHER = "other", "Other (deposit, discount, fee)"

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    pack_amount = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="amount per item",
        help_text="In the ingredient's unit: kg, liter or pieces",
    )
    line_total = models.DecimalField(
        max_digits=9, decimal_places=2, verbose_name="paid"
    )
    category = models.CharField(
        max_length=10, choices=Category.choices, default=Category.FOOD
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.SET_NULL, null=True, blank=True
    )
    # Not a purchase at all, such as a misread total: left out of every sum.
    skipped = models.BooleanField(default=False)
    price = models.OneToOneField(
        IngredientPrice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="bill_line",
    )

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return self.description

    @property
    def unit_price(self) -> Decimal | None:
        """EUR per the ingredient's unit, when this line can set a price."""
        if self.skipped or self.category != self.Category.FOOD:
            return None
        if not self.ingredient_id or not self.pack_amount or self.line_total <= 0:
            return None
        amount = self.quantity * self.pack_amount
        return (self.line_total / amount).quantize(Decimal("0.0001"))

    @property
    def needs_review(self) -> bool:
        if self.skipped or self.category != self.Category.FOOD:
            return False
        return self.unit_price is None and self.line_total > 0


class LineMatch(models.Model):
    """A confirmed match per shop, so the next bill needs less checking."""

    shop = models.CharField(max_length=12, choices=Shop.CHOICES)
    key = models.CharField(max_length=200)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    pack_amount = models.DecimalField(max_digits=8, decimal_places=3)
    unit = models.CharField(max_length=10, choices=Unit.CHOICES)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["shop", "key"], name="unique_line_match"),
        ]

    def __str__(self) -> str:
        return f"{self.key} -> {self.ingredient.name}"


@receiver(pre_delete, sender=BillLine)
def _delete_line_price(sender, instance: BillLine, origin=None, **kwargs) -> None:
    # A removed line or bill takes its price along, however it's deleted. Deleting
    # a camp doesn't: its prices stay useful as history.
    if getattr(origin, "model", type(origin)) is not Camp and instance.price_id:
        IngredientPrice.objects.filter(pk=instance.price_id).delete()


@receiver(post_delete, sender=Bill)
def _delete_bill_file(sender, instance: Bill, **kwargs) -> None:
    # Also runs when deleting a camp: a bill's personal data must not stay behind.
    if instance.file:
        instance.file.delete(save=False)
