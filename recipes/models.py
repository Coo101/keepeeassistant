"""Recipe library models (SPEC §6)."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from core.constants import DishType, IngredientCategory, PriceSource, Shop, Unit
from core.portions import format_quantity, portions


class IngredientQuerySet(models.QuerySet):
    def with_latest_price(self) -> "IngredientQuerySet":
        """Adds `latest_price` and `latest_price_date`, None without a price."""
        latest = IngredientPrice.objects.filter(
            ingredient=models.OuterRef("pk"), unit=models.OuterRef("unit")
        )
        return self.annotate(
            latest_price=models.Subquery(latest.values("price")[:1]),
            latest_price_date=models.Subquery(latest.values("date")[:1]),
        )


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=10, choices=Unit.CHOICES)
    category = models.CharField(
        max_length=20,
        choices=IngredientCategory.CHOICES,
        default=IngredientCategory.OTHER,
    )

    # Budgeting (SPEC §9.6): EUR per canonical unit, set by hand.
    shop = models.CharField(
        max_length=12,
        choices=Shop.CHOICES,
        default=Shop.COLRUYT,
        help_text="Where this ingredient is bought",
    )
    product_details = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="product details",
        help_text="Name, [brand] ([LOS] = loose/unpackaged) and container "
        "volume or other details",
    )

    objects = IngredientQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.unit})"


class IngredientPrice(models.Model):
    """One price at one moment. Without a camp it's a general price, entered on
    the ingredients page; with a camp it's what that camp paid (SPEC §9.6)."""

    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name="prices"
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="EUR per kg/liter/piece",
    )
    # A price stays per the unit it was entered in; after the ingredient's unit
    # changes it's history only, never used to calculate a cost.
    unit = models.CharField(max_length=10, choices=Unit.CHOICES, editable=False)
    source = models.CharField(
        max_length=10, choices=PriceSource.CHOICES, default=PriceSource.MANUAL
    )
    date = models.DateField(default=timezone.localdate)
    # Kept when a camp is deleted: the price is still useful for estimates.
    camp = models.ForeignKey(
        "camps.Camp",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ingredient_prices",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-date", "-pk"]

    def __str__(self) -> str:
        return f"{self.ingredient.name}: {self.price} on {self.date}"

    def save(self, *args, **kwargs) -> None:
        if not self.unit:
            self.unit = self.ingredient.unit
        super().save(*args, **kwargs)


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

    # Sharing (SPEC §9.1): everyone with an account can read and copy a recipe.
    # No author (imported recipes, deleted accounts) means staff manage it.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recipes",
    )
    others_can_edit = models.BooleanField(
        default=False,
        verbose_name="others can edit",
        help_text="Let everyone with an account change this recipe",
    )

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

    def can_manage_access(self, user) -> bool:
        return user.is_staff or self.author_id == user.pk

    def planned_by_other_chiros(self, user) -> bool:
        """Finished camps don't count: nobody shops for them anymore."""
        return (
            self.menuentry_set.exclude(camp__chiro__in=user.chiros.all())
            .filter(camp__end_date__gte=timezone.localdate())
            .exists()
        )

    def can_edit(self, user) -> bool:
        """Once another Chiro plans a recipe it stays as it is, so their lists and
        budgets don't change under them; a copy can still be changed. Staff can fix
        mistakes, with a warning on the edit page."""
        if user.is_staff:
            return True
        allowed = self.others_can_edit or self.author_id == user.pk
        return allowed and not self.planned_by_other_chiros(user)


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

    def clean(self) -> None:
        # The ingredient's price is per its own unit, so a different unit here
        # could not be costed (SPEC §3: no conversions).
        if self.ingredient_id and self.unit != self.ingredient.unit:
            raise ValidationError(
                {
                    "unit": f"{self.ingredient.name} is measured in "
                    f"{self.ingredient.unit}; use that unit or change the "
                    "ingredient."
                }
            )

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
