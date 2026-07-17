"""Recipe library models (SPEC §6)."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from core.constants import DishType, IngredientCategory, Unit
from core.portions import portions


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=10, choices=Unit.CHOICES)
    category = models.CharField(
        max_length=20,
        choices=IngredientCategory.CHOICES,
        default=IngredientCategory.OTHER,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.unit})"


class Recipe(models.Model):
    name = models.CharField(max_length=200)
    dish_type = models.CharField(max_length=20, choices=DishType.CHOICES)
    base_children = models.PositiveIntegerField(
        default=0, help_text="Under-12 count the entered quantities feed"
    )
    base_teens = models.PositiveIntegerField(
        default=0, help_text="12+ count the entered quantities feed"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(base_children__gt=0) | models.Q(base_teens__gt=0),
                name="recipe_base_headcount_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def base_portions(self) -> Decimal:
        return portions(children=self.base_children, teens=self.base_teens)

    @property
    def total_duration_minutes(self) -> int:
        return sum(step.duration_minutes or 0 for step in self.steps.all())


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="ingredients"
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    unit = models.CharField(max_length=10, choices=Unit.CHOICES)

    class Meta:
        ordering = ["ingredient__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"], name="unique_recipe_ingredient"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} {self.unit} {self.ingredient.name}"


class RecipeStep(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField()
    instruction = models.TextField()
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "order"], name="unique_recipe_step_order"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.order}. {self.instruction[:50]}"
