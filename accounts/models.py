"""Chiros and who belongs to them (SPEC §6, §9.8)."""

import datetime
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

INVITATION_DAYS = 14


def _new_token() -> str:
    return secrets.token_urlsafe(32)


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


class Invitation(models.Model):
    """A one-time link that adds someone to a Chiro. Access is by invitation."""

    chiro = models.ForeignKey(Chiro, on_delete=models.CASCADE)
    email = models.EmailField()
    token = models.CharField(
        max_length=64, unique=True, default=_new_token, editable=False
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        editable=False,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.email} to {self.chiro}"

    @property
    def is_open(self) -> bool:
        expires = self.created_at + datetime.timedelta(days=INVITATION_DAYS)
        return self.accepted_at is None and timezone.now() < expires
