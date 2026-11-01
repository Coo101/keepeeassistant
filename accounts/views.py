"""The account page and accepting invitations."""

import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.forms import AcceptInvitationForm, ProfileForm, email_is_taken
from accounts.models import Invitation, Membership

logger = logging.getLogger(__name__)


def account(request: HttpRequest) -> HttpResponse:
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your details were saved.")
        return redirect("account")
    return render(
        request,
        "accounts/account.html",
        {"form": form, "chiros": request.user.chiros.all()},
    )


def _accept(invitation: Invitation, user) -> None:
    Membership.objects.get_or_create(user=user, chiro=invitation.chiro)
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    logger.info("%s accepted invitation %s", user, invitation.pk)


@login_not_required
@transaction.atomic
def invitation_accept(request: HttpRequest, token: str) -> HttpResponse:
    invitation = get_object_or_404(
        Invitation.objects.select_for_update().select_related("chiro"), token=token
    )
    context = {"invitation": invitation}
    if not invitation.is_open:
        return render(request, "accounts/invitation_closed.html", context, status=410)

    if request.user.is_authenticated:
        # The link is for one address: it may have been forwarded, or this may be
        # someone else's session on a shared kitchen device.
        if request.user.email.casefold() != invitation.email.casefold():
            return render(
                request, "accounts/invitation_wrong_account.html", context, status=403
            )
        if request.method == "POST":
            _accept(invitation, request.user)
            return redirect("camp_list")
        return render(request, "accounts/invitation_join.html", context)

    if email_is_taken(invitation.email):
        return render(request, "accounts/invitation_login.html", context)

    form = AcceptInvitationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.email = invitation.email
        user.save()
        _accept(invitation, user)
        login(request, user)
        return redirect("camp_list")
    return render(request, "accounts/invitation_signup.html", {**context, "form": form})
