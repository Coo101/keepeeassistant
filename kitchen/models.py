"""Kitchen utilities: what a Chiro owns, and what a camp needs (SPEC §9.15)."""

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.models import Chiro
from camps.models import Camp


class Utensil(models.Model):
    """Pots, fire pits and the like in a Chiro's stock, shared by its camps."""

    chiro = models.ForeignKey(Chiro, on_delete=models.CASCADE, related_name="utensils")
    name = models.CharField(max_length=200, verbose_name=_("name"))
    in_stock = models.PositiveIntegerField(default=0, verbose_name=_("in stock"))
    note = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("note"),
        help_text=_("Size, condition or where it's kept"),
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["chiro", "name"], name="unique_utensil"),
        ]

    def __str__(self) -> str:
        return self.name


class CampUtensil(models.Model):
    """How many of one utility a camp needs; whatever the stock lacks is bought."""

    camp = models.ForeignKey(
        Camp, on_delete=models.CASCADE, related_name="utensil_needs"
    )
    # Protected: the stock page refuses to remove what a camp still needs.
    utensil = models.ForeignKey(
        Utensil, on_delete=models.PROTECT, related_name="camp_needs"
    )
    needed = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)], verbose_name=_("needed")
    )

    class Meta:
        ordering = ["utensil__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["camp", "utensil"], name="unique_camp_utensil"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.camp}: {self.needed} {self.utensil}"

    @property
    def to_buy(self) -> int:
        return max(0, self.needed - self.utensil.in_stock)
