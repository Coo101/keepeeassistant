"""Slow down password guessing and reset-mail flooding.

Counted in the database, because gunicorn's workers share no memory. Keys are
hashed, so the table holds no usernames or addresses. Parallel requests can go
slightly over a limit, which is fine for its purpose.

Failures also lock the account for its real owner, for at most 15 minutes. A
password reset lifts that, and staff can clear all counters in the admin.
"""

import datetime
import hashlib
import unicodedata

from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpRequest
from django.utils import timezone

from accounts.models import RateLimitHit

WINDOW = datetime.timedelta(minutes=15)
MAX_FAILS_PER_ACCOUNT = 10
MAX_FAILS_PER_ADDRESS = 50
MAX_RESETS_PER_EMAIL = 3
MAX_RESETS_PER_ADDRESS = 10


def client_address(request: HttpRequest) -> str:
    """Behind a proxy REMOTE_ADDR is the proxy, so a header can be configured. The
    last value is the one the nearest proxy added; earlier ones can be made up."""
    header = settings.CLIENT_IP_HEADER
    if header:
        forwarded = request.META.get(header, "").split(",")[-1].strip()
        if forwarded:
            return forwarded
    return request.META.get("REMOTE_ADDR", "")


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def is_limited(key: str, limit: int) -> bool:
    recent = RateLimitHit.objects.filter(
        key=_hash(key), at__gte=timezone.now() - WINDOW
    )
    return recent.count() >= limit


def record(key: str) -> None:
    RateLimitHit.objects.filter(at__lt=timezone.now() - WINDOW).delete()
    RateLimitHit.objects.create(key=_hash(key))


def clear(key: str) -> None:
    RateLimitHit.objects.filter(key=_hash(key)).delete()


def _user_key(pk: int) -> str:
    return f"login-user:{pk}"


def _account_key(identifier: str) -> str:
    """One counter per account, whichever spelling or address is used to log in."""
    identifier = unicodedata.normalize("NFKC", identifier).strip()
    user = (
        get_user_model()
        .objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier))
        .order_by("pk")
        .first()
    )
    return _user_key(user.pk) if user else f"login-name:{identifier.casefold()}"


class _LoginLimitMixin:
    def clean(self) -> dict:
        account_key = _account_key(self.data.get(self.add_prefix("username")) or "")
        address_key = f"login-ip:{client_address(self.request)}"
        if is_limited(account_key, MAX_FAILS_PER_ACCOUNT) or is_limited(
            address_key, MAX_FAILS_PER_ADDRESS
        ):
            raise ValidationError(
                "Too many failed attempts. Wait 15 minutes, or reset your password."
            )
        try:
            cleaned = super().clean()
        except ValidationError:
            record(account_key)
            record(address_key)
            raise
        # A blank password returns here too, without any check of the password.
        if self.get_user():
            clear(account_key)
        return cleaned


class LimitedLoginForm(_LoginLimitMixin, AuthenticationForm):
    pass


class LimitedAdminLoginForm(_LoginLimitMixin, AdminAuthenticationForm):
    pass


class LimitedPasswordResetForm(PasswordResetForm):
    def save(self, *args, request=None, **kwargs) -> None:
        # Silently, like an unknown address: the page says the same either way.
        email_key = f"reset:{self.cleaned_data['email'].casefold()}"
        address_key = f"reset-ip:{client_address(request)}"
        if is_limited(email_key, MAX_RESETS_PER_EMAIL) or is_limited(
            address_key, MAX_RESETS_PER_ADDRESS
        ):
            return
        record(email_key)
        record(address_key)
        super().save(*args, request=request, **kwargs)


class UnlockingSetPasswordForm(SetPasswordForm):
    """The lockout message points to a reset, so a reset must lift the lock."""

    def save(self, commit: bool = True):
        user = super().save(commit)
        clear(_user_key(user.pk))
        return user
