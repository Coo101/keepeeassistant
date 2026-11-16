"""Shopping trip models (docs/spec/shopping.md)."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Chiro
from camps.models import Camp
from recipes.models import Ingredient


class ShoppingTrip(models.Model):
    camp = models.ForeignKey(
        Camp, on_delete=models.CASCADE, related_name="shopping_trips"
    )
    date = models.DateField()

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["camp", "date"], name="unique_trip_per_day"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.camp} shop on {self.date}"


class PantryItem(models.Model):
    """Food a Chiro already has, in the ingredient's unit; every camp of the Chiro
    takes it off its shopping lists (docs/spec/shopping.md)."""

    chiro = models.ForeignKey(
        Chiro, on_delete=models.CASCADE, related_name="pantry_items"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, verbose_name=_("ingredient")
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name=_("quantity"),
    )

    class Meta:
        ordering = ["ingredient__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["chiro", "ingredient"], name="unique_pantry_item"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.chiro}: {self.quantity} {self.ingredient}"
