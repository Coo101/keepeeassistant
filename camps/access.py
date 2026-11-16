"""Who may open and change a camp or a Chiro's stock (docs/spec/accounts.md)."""

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from accounts.models import Chiro
from camps.models import Camp

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _refuse_changes(request: HttpRequest, chiro: Chiro) -> None:
    if request.method not in SAFE_METHODS and chiro.is_read_only_for(request.user):
        raise PermissionDenied(
            _("This is an example: you can look around, but not change it.")
        )


def get_camp(request: HttpRequest, camp_id: int) -> Camp:
    """A camp the user may open; any change to an example camp is refused."""
    camp = get_object_or_404(
        Camp.objects.for_user(request.user).select_related("chiro"), pk=camp_id
    )
    _refuse_changes(request, camp.chiro)
    return camp


def get_chiro(request: HttpRequest, chiro_id: int) -> Chiro:
    """One of the user's Chiros, or an example Chiro to look at."""
    chiros = Chiro.objects.filter(
        Q(pk__in=request.user.chiros.all()) | Q(is_example=True)
    )
    chiro = get_object_or_404(chiros, pk=chiro_id)
    _refuse_changes(request, chiro)
    return chiro
