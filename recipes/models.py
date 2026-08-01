"""Recipe library models (SPEC §6)."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.functional import cached_property

from core.constants import DishType, IngredientCategory, Shop, Unit
from core.portions import format_quantity, portions


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=10, choices=Unit.CHOICES)
    category = models.CharField(
        max_length=20,
        choices=IngredientCategory.CHOICES,
        default=IngredientCategory.OTHER,
    )

    # Budgeting (SPEC §13): EUR per canonical unit (kg / liter / piece).
    shop = models.CharField(
        max_length=12,
        choices=Shop.CHOICES,
        default=Shop.COLRUYT,
        help_text="Where this ingredient is bought; only Colruyt items get "
        "automatic price updates",
    )
    price_per_unit = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="EUR per kg/liter/piece",
    )
    product_details = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="product details",
        help_text="Name, [brand] ([LOS] = loose/unpackaged) and container "
        "volume or other details",
    )
    colruyt_product_id = models.CharField(
        max_length=20,
        blank=True,
        help_text="Pin a Colruyt productId; price updates follow this product",
    )
    price_updated = models.DateTimeField(null=True, blank=True)

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

    @cached_property
    def total_duration_minutes(self) -> int:
        # Cached: templates read this twice (test + display) per recipe, and
        # it walks the prefetched steps rather than re-querying.
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

    @property
    def quantity_display(self) -> str:
        """Quantity without trailing zeros (2.500 -> 2.5, 130.000 -> 130)."""
        return format_quantity(self.quantity)


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
