"""Log in with a username or an email address."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(
            request, username=username, password=password, **kwargs
        )
        if user or not username or "@" not in username:
            return user
        User = get_user_model()
        # Two accounts can share an address in old data; then it says nothing.
        matches = list(User.objects.filter(email__iexact=username)[:2])
        if len(matches) != 1:
            # Same work as a real check, so timing doesn't reveal the address.
            User().set_password(password)
            return None
        candidate = matches[0]
        if candidate.check_password(password) and self.user_can_authenticate(candidate):
            return candidate
        return None
