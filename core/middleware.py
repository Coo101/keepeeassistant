"""Access control: reading is open, changing anything needs a login.

Applied by HTTP method rather than per view, so a new POST endpoint is
protected by default instead of relying on someone adding a decorator.
"""

import logging

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.urls import reverse

logger = logging.getLogger(__name__)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class LoginRequiredForWritesMiddleware:
    """Anonymous users may read every page but not submit anything.

    The admin is skipped: it has its own login flow and staff checks, and
    its login form is itself a POST.
    """

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._needs_login(request):
            logger.info(
                "Anonymous %s to %s redirected to login",
                request.method,
                request.path,
            )
            return redirect_to_login(request.get_full_path())
        return self.get_response(request)

    def _needs_login(self, request: HttpRequest) -> bool:
        if request.method in SAFE_METHODS:
            return False
        if getattr(request, "user", None) and request.user.is_authenticated:
            return False
        return not self._is_exempt(request.path)

    def _is_exempt(self, path: str) -> bool:
        # The login form and the admin's own auth must stay reachable.
        return path.startswith("/admin/") or path == reverse("login")
