"""Sending invitations."""

from django.core.mail import send_mail
from django.http import HttpRequest
from django.urls import reverse

from accounts.models import Invitation


def invitation_link(request: HttpRequest, invitation: Invitation) -> str:
    return request.build_absolute_uri(
        reverse("invitation_accept", args=[invitation.token])
    )


def send_invitation(request: HttpRequest, invitation: Invitation) -> None:
    send_mail(
        f"Join {invitation.chiro} on Camp Meal Planner",
        f"You're invited to plan camp meals with {invitation.chiro}.\n\n"
        f"Accept here within two weeks:\n{invitation_link(request, invitation)}\n",
        None,
        [invitation.email],
    )
