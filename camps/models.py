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

    # Runbook front-page info (mirrors the draaiboek kookploeg documents)
    cook_team = models.TextField(
        blank=True,
        verbose_name="kookploeg",
        help_text="One member per line: name + phone number",
    )
    location = models.TextField(blank=True, help_text="Camp site name + address")
    contact_leader = models.TextField(
        blank=True,
        verbose_name="aanspreekpunt leiding",
        help_text="Name + phone number",
    )
    contact_rental = models.TextField(
        blank=True,
        verbose_name="aanspreekpunt verhuur",
        help_text="Name + phone/mail",
    )
    bakery = models.TextField(
        blank=True, verbose_name="bakker", help_text="Bakery name, phone, address"
    )
    general_notes = models.TextField(
        blank=True, help_text="Shown on the runbook front page"
    )

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

    def entries_outside_dates(self) -> models.QuerySet:
        """Menu entries stranded by a change of camp dates: not shown in the
        planner and not bought, so pages warn about them."""
        return self.menu_entries.exclude(
            date__range=(self.start_date, self.end_date)
        ).select_related("recipe")


class DayNote(models.Model):
    """Free-form runbook notes for one camp day (the draaiboek 'no-tities')."""

    camp = models.ForeignKey(Camp, on_delete=models.CASCADE, related_name="day_notes")
    date = models.DateField()
    text = models.TextField(blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["camp", "date"], name="unique_day_note"),
        ]

    def __str__(self) -> str:
        return f"{self.camp} notes {self.date}"
