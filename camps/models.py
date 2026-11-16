"""Camp models (docs/spec/planning.md)."""

import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Chiro
from core.constants import Diet
from core.portions import portions


class CampQuerySet(models.QuerySet):
    def for_user(self, user) -> "CampQuerySet":
        """The camps of the user's Chiros
        (docs/spec/accounts.md), and the example camps that
        everyone may look at (docs/spec/accounts.md)."""
        return self.filter(
            models.Q(chiro__in=user.chiros.all()) | models.Q(chiro__is_example=True)
        )

    def active(self) -> "CampQuerySet":
        return self.filter(is_archived=False)


class Camp(models.Model):
    chiro = models.ForeignKey(
        Chiro, on_delete=models.PROTECT, related_name="camps", verbose_name="Chiro"
    )
    name = models.CharField(max_length=200, verbose_name=_("name"))
    start_date = models.DateField(verbose_name=_("start date"))
    end_date = models.DateField(verbose_name=_("end date"))
    num_children = models.PositiveIntegerField(
        default=0, verbose_name=_("children (<12)")
    )
    num_teens = models.PositiveIntegerField(default=0, verbose_name=_("teens (12+)"))
    num_staff = models.PositiveIntegerField(default=0, verbose_name=_("staff"))
    breakfast_time = models.TimeField(
        default=datetime.time(8, 0), verbose_name=_("breakfast")
    )
    lunch_time = models.TimeField(
        default=datetime.time(12, 30), verbose_name=_("lunch")
    )
    teatime_time = models.TimeField(
        default=datetime.time(16, 0), verbose_name=_("tea time")
    )
    dinner_time = models.TimeField(
        default=datetime.time(18, 30), verbose_name=_("dinner")
    )

    # Runbook front-page info (mirrors the draaiboek kookploeg documents)
    cook_team = models.TextField(
        blank=True,
        verbose_name=_("cook team"),
        help_text=_("One member per line: name + phone number"),
    )
    location = models.TextField(
        blank=True,
        verbose_name=_("location"),
        help_text=_("Camp site name + address"),
    )
    contact_leader = models.TextField(
        blank=True,
        verbose_name=_("contact for the leaders"),
        help_text=_("Name + phone number"),
    )
    contact_rental = models.TextField(
        blank=True,
        verbose_name=_("contact for the rental"),
        help_text=_("Name + phone/mail"),
    )
    bakery = models.TextField(
        blank=True,
        verbose_name=_("bakery"),
        help_text=_("Bakery name, phone, address"),
    )
    general_notes = models.TextField(
        blank=True,
        verbose_name=_("general notes"),
        help_text=_("Shown on the runbook front page"),
    )
    # Out of the way on the camp list, but kept as history; unlike deleting.
    is_archived = models.BooleanField(default=False, verbose_name=_("archived"))

    objects = CampQuerySet.as_manager()

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(_("End date must be on or after start date."))

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

    def update_headcount(self) -> None:
        """Set the three totals from the camp's groups
        (docs/spec/planning.md). Everything that
        scales reads the totals, so the groups only change how they're entered."""
        totals = {kind: 0 for kind in CampGroup.Kind.values}
        for kind, count in self.groups.values_list("kind", "count"):
            totals[kind] += count
        self.num_children = totals[CampGroup.Kind.CHILDREN]
        self.num_teens = totals[CampGroup.Kind.TEENS]
        self.num_staff = totals[CampGroup.Kind.STAFF]
        self.save(update_fields=["num_children", "num_teens", "num_staff"])

    def can_delete(self, user) -> bool:
        return user.is_staff or self.chiro.is_admin(user)

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


class DietaryNeed(models.Model):
    """How many people in a camp have a diet or allergy (docs/spec/planning.md)."""

    camp = models.ForeignKey(
        Camp, on_delete=models.CASCADE, related_name="dietary_needs"
    )
    diet = models.CharField(
        max_length=20, choices=Diet.CHOICES, verbose_name=_("diet or allergy")
    )
    count = models.PositiveIntegerField(default=1, verbose_name=_("people"))
    note = models.CharField(max_length=200, blank=True, verbose_name=_("note"))

    class Meta:
        ordering = ["diet"]
        constraints = [
            models.UniqueConstraint(fields=["camp", "diet"], name="unique_camp_diet"),
        ]

    def __str__(self) -> str:
        return f"{self.camp}: {self.count} {self.get_diet_display()}"


class CampGroup(models.Model):
    """An afdeling or team at the camp and how many come
    (docs/spec/planning.md). The camp's
    three totals are the sums per kind."""

    class Kind(models.TextChoices):
        CHILDREN = "children", _("under 12")
        TEENS = "teens", _("12+")
        STAFF = "staff", _("staff")

    camp = models.ForeignKey(Camp, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField(max_length=100, verbose_name=_("group"))
    kind = models.CharField(
        max_length=10,
        choices=Kind.choices,
        default=Kind.CHILDREN,
        verbose_name=_("counts as"),
    )
    count = models.PositiveIntegerField(default=0, verbose_name=_("number"))

    class Meta:
        # Rows keep their ids when saved again (core.rows), so this is the order
        # they were added in: youngest afdeling first, as entered.
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["camp", "name"], name="unique_camp_group_name"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.camp}: {self.count} {self.name}"
