"""Chiros and who belongs to them (SPEC §6, §9.8)."""

from django.conf import settings
from django.db import models


class Chiro(models.Model):
    """A Chiro group. Created in the admin only: access is by invitation."""

    name = models.CharField(max_length=200, unique=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Membership", related_name="chiros"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chiro = models.ForeignKey(Chiro, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "chiro"], name="unique_chiro_membership"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.chiro}"
