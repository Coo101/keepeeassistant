"""Camp models (SPEC §6)."""

import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from core.portions import portions


class Camp(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    num_children = models.PositiveIntegerField(default=0, verbose_name="children (<12)")
    num_teens = models.PositiveIntegerField(default=0, verbose_name="teens (12+)")
    num_staff = models.PositiveIntegerField(default=0)
    breakfast_time = models.TimeField(default=datetime.time(8, 0))
    lunch_time = models.TimeField(default=datetime.time(12, 30))
    teatime_time = models.TimeField(default=datetime.time(16, 0))
    dinner_time = models.TimeField(default=datetime.time(18, 30))

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("End date must be on or after start date.")

    @property
    def demand_portions(self) -> Decimal:
        return portions(
            children=self.num_children, teens=self.num_teens, staff=self.num_staff
        )

    @property
    def days(self) -> list[datetime.date]:
        """Every date of the camp, start to end inclusive."""
        n = (self.end_date - self.start_date).days + 1
        return [self.start_date + datetime.timedelta(days=i) for i in range(n)]
