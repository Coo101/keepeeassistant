"""The shared delete flow: GET asks for confirmation, POST deletes."""

import logging
from collections.abc import Sequence

from django.db import models
from django.db.models import ProtectedError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def confirm_delete(
    request: HttpRequest,
    obj: models.Model,
    *,
    cancel_url: str,
    success_url: str,
    consequences: Sequence[str] = (),
    blocked_reason: str = "",
) -> HttpResponse:
    """`blocked_reason` explains why `obj` can't be deleted right now."""
    label = str(obj)
    if request.method == "POST" and not blocked_reason:
        try:
            obj.delete()
        except ProtectedError:
            # Something started using it after the page was opened.
            blocked_reason = _("It is in use, so it can't be deleted.")
        else:
            logger.info("%s deleted %r", request.user, label)
            return redirect(success_url)
    return render(
        request,
        "confirm_delete.html",
        {
            "label": label,
            "cancel_url": cancel_url,
            "consequences": consequences,
            "blocked_reason": blocked_reason,
        },
        status=409 if request.method == "POST" else 200,
    )
