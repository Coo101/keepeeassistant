"""Shopping trip models (SPEC §6, §8)."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

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
    """What a camp already has, in the ingredient's unit (SPEC §9.12)."""

    camp = models.ForeignKey(
        Camp, on_delete=models.CASCADE, related_name="pantry_items"
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    class Meta:
        ordering = ["ingredient__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["camp", "ingredient"], name="unique_pantry_item"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.camp}: {self.quantity} {self.ingredient}"
