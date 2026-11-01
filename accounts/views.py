"""The account page and accepting invitations."""

import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.forms import (
    AcceptInvitationForm,
    InvitationForm,
    JoinRequestForm,
    ProfileForm,
    email_is_taken,
)
from accounts.invitations import MAIL_ERRORS, invitation_link, send_invitation
from accounts.models import Chiro, Invitation, Membership, Role
from accounts.ratelimit import client_address, is_limited, record

logger = logging.getLogger(__name__)

MAX_JOIN_REQUESTS_PER_ADDRESS = 5


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
    chiro = invitation.chiro
    # A Chiro without an admin gets one, so it can manage itself from then on.
    role = Role.ADMIN if not chiro.has_admin() else invitation.role
    membership, created = Membership.objects.get_or_create(
        user=user, chiro=chiro, defaults={"role": role}
    )
    if not created and role == Role.ADMIN and membership.role != Role.ADMIN:
        membership.role = Role.ADMIN
        membership.save(update_fields=["role"])
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


def _member_chiro(request: HttpRequest, chiro_id: int) -> Chiro:
    return get_object_or_404(request.user.chiros, pk=chiro_id)


def _admin_chiro(request: HttpRequest, chiro_id: int) -> Chiro:
    chiro = _member_chiro(request, chiro_id)
    if not chiro.is_admin(request.user):
        raise PermissionDenied("Only an admin of this Chiro can do this.")
    return chiro


def chiro_detail(request: HttpRequest, chiro_id: int) -> HttpResponse:
    chiro = _member_chiro(request, chiro_id)
    is_admin = chiro.is_admin(request.user)
    form = None
    if is_admin:
        form = InvitationForm(request.POST or None, chiro=chiro)
        if request.method == "POST" and form.is_valid():
            invitation = form.save(commit=False)
            invitation.chiro = chiro
            invitation.invited_by = request.user
            invitation.save()
            try:
                send_invitation(request, invitation)
                messages.success(request, f"Invitation sent to {invitation.email}.")
            except MAIL_ERRORS as exc:
                logger.warning("Invitation %s not sent: %s", invitation.pk, exc)
                messages.error(
                    request,
                    "The mail couldn't be sent. Pass on the link below yourself.",
                )
            return redirect("chiro_detail", chiro_id=chiro.pk)
    elif request.method == "POST":
        raise PermissionDenied("Only an admin of this Chiro can do this.")
    invitations = [
        (invitation, invitation_link(request, invitation))
        for invitation in chiro.invitation_set.all()
        if invitation.is_open
    ]
    return render(
        request,
        "accounts/chiro_detail.html",
        {
            "chiro": chiro,
            "is_admin": is_admin,
            "form": form,
            "memberships": chiro.membership_set.select_related("user").order_by(
                "user__username"
            ),
            "invitations": invitations if is_admin else [],
            "roles": Role.choices,
        },
    )


@require_POST
@transaction.atomic
def chiro_member(
    request: HttpRequest, chiro_id: int, membership_id: int
) -> HttpResponse:
    """Change a member's role, or remove them from the Chiro."""
    chiro = _admin_chiro(request, chiro_id)
    membership = get_object_or_404(chiro.membership_set, pk=membership_id)
    remove = "remove" in request.POST
    role = request.POST.get("role")
    # Locked, so two admins demoting each other can't leave the Chiro without one.
    admins = chiro.membership_set.select_for_update().filter(role=Role.ADMIN)
    other_admins = [admin for admin in admins if admin.pk != membership.pk]
    if (remove or role != Role.ADMIN) and not other_admins:
        messages.error(request, "A Chiro needs at least one admin.")
    elif remove:
        membership.delete()
        logger.info("%s removed %s from %s", request.user, membership.user, chiro)
        if membership.user == request.user:
            return redirect("account")
    elif role in Role.values:
        membership.role = role
        membership.save(update_fields=["role"])
    return redirect("chiro_detail", chiro_id=chiro.pk)


@require_POST
def invitation_cancel(
    request: HttpRequest, chiro_id: int, invitation_id: int
) -> HttpResponse:
    chiro = _admin_chiro(request, chiro_id)
    get_object_or_404(chiro.invitation_set, pk=invitation_id).delete()
    return redirect("chiro_detail", chiro_id=chiro.pk)


@login_not_required
def join_request(request: HttpRequest) -> HttpResponse:
    form = JoinRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        key = f"join-ip:{client_address(request)}"
        # Bots and floods get the same thank-you, and nothing is stored.
        if not form.cleaned_data["website"] and not is_limited(
            key, MAX_JOIN_REQUESTS_PER_ADDRESS
        ):
            record(key)
            form.save()
        return render(request, "accounts/join_thanks.html")
    return render(request, "accounts/join_request.html", {"form": form})
