"""Bills and what a camp actually paid (docs/spec/finance.md)."""

import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from camps.models import Camp
from core.constants import Shop, Unit
from recipes.models import Ingredient, IngredientPrice


def _bill_path(bill: "Bill", filename: str) -> str:
    # Never the uploaded name: it can hold personal data or odd characters.
    return f"bills/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Bill(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", _("Waiting to be read")
        FAILED = "failed", _("Couldn't be read")
        REVIEW = "review", _("To review")
        DONE = "done", _("Reviewed")

    camp = models.ForeignKey(Camp, on_delete=models.CASCADE, related_name="bills")
    # Empty once someone removes the file; the lines stay.
    file = models.FileField(upload_to=_bill_path, blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    shop = models.CharField(max_length=12, choices=Shop.CHOICES, verbose_name=_("shop"))
    date = models.DateField(default=timezone.localdate, verbose_name=_("date"))
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.WAITING,
        verbose_name=_("status"),
    )
    error = models.CharField(max_length=300, blank=True)
    printed_total = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("printed total"),
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
        return _("%(shop)s bill of %(date)s") % {
            "shop": self.get_shop_display(),
            "date": date_format(self.date),
        }

    def lines_total(self) -> Decimal:
        return sum(
            (line.line_total for line in self.lines.all() if not line.skipped),
            Decimal("0"),
        )


class BillLine(models.Model):
    class Category(models.TextChoices):
        FOOD = "food", _("Camp food")
        UTENSILS = "utensils", _("Kitchen utilities")
        ACTIVITY = "activity", _("Activity")
        PERSONAL = "personal", _("Personal")
        OTHER = "other", _("Other (deposit, discount, fee)")

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=200, verbose_name=_("description"))
    # The shop's own number, when the bill prints one: names change, this doesn't.
    article = models.CharField(max_length=20, blank=True, editable=False)
    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name=_("quantity"),
    )
    pack_amount = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name=_("amount per item"),
        help_text=_("In the ingredient's unit: kg, liter or pieces"),
    )
    line_total = models.DecimalField(
        max_digits=9, decimal_places=2, verbose_name=_("paid")
    )
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        default=Category.FOOD,
        verbose_name=_("category"),
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("ingredient"),
    )
    # Not a purchase at all, such as a misread total: left out of every sum.
    skipped = models.BooleanField(default=False, verbose_name=_("skipped"))
    # Set once the line was added to the Chiro's stock, so saving again can't
    # count it twice.
    utensil = models.ForeignKey(
        "kitchen.Utensil",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
    )
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
    key = models.CharField(max_length=200)  # article number, else the description
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


@receiver(pre_delete, sender=Camp)
def _delete_example_prices(sender, instance: Camp, **kwargs) -> None:
    """Other camps go on using a deleted camp's prices, but an example camp's
    prices are made up, so they go with it."""
    if instance.chiro.is_example:
        IngredientPrice.objects.filter(camp=instance).delete()
