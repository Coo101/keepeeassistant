"""Menu planning models (SPEC §6, §9.3)."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from camps.models import Camp
from core.constants import Course, MealType, allowed_dish_types
from recipes.models import Recipe


class MenuEntry(models.Model):
    camp = models.ForeignKey(
        Camp, on_delete=models.CASCADE, related_name="menu_entries"
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MealType.CHOICES)
    # "" for single-slot meals; lunch uses soup/main/dessert.
    course = models.CharField(max_length=10, choices=Course.CHOICES, blank=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = _("menu entries")
        ordering = ["date", "meal_type", "course"]
        constraints = [
            models.UniqueConstraint(
                fields=["camp", "date", "meal_type", "course"],
                name="unique_menu_slot",
            ),
        ]

    def __str__(self) -> str:
        slot = f"{self.meal_type}/{self.course}" if self.course else self.meal_type
        return f"{self.camp} {self.date} {slot}: {self.recipe}"

    def clean(self) -> None:
        allowed = allowed_dish_types(self.meal_type, self.course)
        if not allowed:
            raise ValidationError(
                f"Invalid slot: meal {self.meal_type!r} with course {self.course!r}."
            )
        if self.recipe_id and self.recipe.dish_type not in allowed:
            raise ValidationError(
                f"Recipe dish type {self.recipe.dish_type!r} does not fit the "
                f"{self.meal_type}{f'/{self.course}' if self.course else ''} slot "
                f"(allowed: {', '.join(allowed)})."
            )
        if self.camp_id and self.date and self.date not in self.camp.days:
            raise ValidationError(
                f"{self.date} is outside camp dates "
                f"({self.camp.start_date} – {self.camp.end_date})."
            )
