"""Sending invitations."""

import smtplib

from django.core.mail import send_mail
from django.http import HttpRequest
from django.urls import reverse
from django.utils.translation import gettext as _

from accounts.models import Invitation

MAIL_ERRORS = (OSError, ValueError, smtplib.SMTPException)


def invitation_link(request: HttpRequest, invitation: Invitation) -> str:
    return request.build_absolute_uri(
        reverse("invitation_accept", args=[invitation.token])
    )


def send_invitation(request: HttpRequest, invitation: Invitation) -> None:
    send_mail(
        _("Join %(chiro)s on Camp Meal Planner") % {"chiro": invitation.chiro},
        _(
            "You're invited to plan camp meals with %(chiro)s.\n\n"
            "Accept here within two weeks:\n%(link)s\n"
        )
        % {"chiro": invitation.chiro, "link": invitation_link(request, invitation)},
        None,
        [invitation.email],
    )
