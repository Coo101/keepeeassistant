"""Forms for the account page and for accepting an invitation."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from accounts.models import Invitation

User = get_user_model()


def email_is_taken(email: str, user_pk: int | None = None) -> bool:
    return User.objects.filter(email__iexact=email).exclude(pk=user_pk).exists()


def _has_open_invitation(email: str) -> bool:
    invitations = Invitation.objects.filter(email__iexact=email)
    return any(invitation.is_open for invitation in invitations)


class ProfileForm(forms.ModelForm):
    current_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        help_text="Needed to change your email address.",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def clean_email(self) -> str:
        email = self.cleaned_data["email"]
        # The address logs in and resets the password, so it must point to one user
        # and can't be claimed before the invited person gets there.
        if email and email_is_taken(email, self.instance.pk):
            raise ValidationError("Another account uses this address.")
        if email and "email" in self.changed_data and _has_open_invitation(email):
            raise ValidationError(
                "This address has an open invitation. Use the link in that mail."
            )
        return email

    def clean(self) -> dict:
        cleaned = super().clean()
        # A borrowed session must not be able to redirect password resets.
        password = cleaned.get("current_password") or ""
        if "email" in self.changed_data and not self.instance.check_password(password):
            self.add_error("current_password", "That isn't your current password.")
        return cleaned


class AcceptInvitationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username"]
