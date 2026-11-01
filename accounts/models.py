"""Chiros and who belongs to them (SPEC §6, §9.8)."""

import datetime
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

INVITATION_DAYS = 14


def _new_token() -> str:
    return secrets.token_urlsafe(32)


class Role(models.TextChoices):
    MEMBER = "member", "Member"
    ADMIN = "admin", "Admin (invites members, deletes camps)"


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

    def has_admin(self) -> bool:
        return self.membership_set.filter(role=Role.ADMIN).exists()

    def is_admin(self, user) -> bool:
        return self.membership_set.filter(user=user, role=Role.ADMIN).exists()


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chiro = models.ForeignKey(Chiro, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

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
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
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


class RateLimitHit(models.Model):
    """One failed login or reset mail; see accounts.ratelimit."""

    key = models.CharField(max_length=64, db_index=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)


class JoinRequest(models.Model):
    """Someone asking for access from the public site; staff decide."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(max_length=100)
    email = models.EmailField()
    chiro_name = models.CharField(max_length=200, verbose_name="your Chiro")
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name}, {self.chiro_name}"
