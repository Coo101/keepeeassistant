"""Shopping trip models (SPEC §6, §8)."""

from django.db import models

from camps.models import Camp


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
