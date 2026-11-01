import smtplib

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.invitations import send_invitation
from accounts.models import Chiro, Invitation, Membership, RateLimitHit
from accounts.ratelimit import LimitedAdminLoginForm


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(Chiro)
class ChiroAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    inlines = [MembershipInline]


class UserChiroInline(admin.TabularInline):
    model = Membership
    extra = 1
    autocomplete_fields = ["chiro"]
    verbose_name_plural = "Chiros"


admin.site.login_form = LimitedAdminLoginForm
admin.site.unregister(User)


@admin.register(User)
class ChiroUserAdmin(UserAdmin):
    """The usual user admin, plus which Chiros the user belongs to."""

    inlines = [UserChiroInline]


@admin.register(RateLimitHit)
class RateLimitHitAdmin(admin.ModelAdmin):
    """Delete these to unlock logins; the keys themselves are hashed."""

    list_display = ["at"]

    def has_add_permission(self, request) -> bool:
        return False


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    """Saving a new invitation mails the link; it also shows here to pass on."""

    list_display = ["email", "chiro", "created_at", "accepted_at"]
    list_filter = ["chiro"]
    search_fields = ["email"]
    autocomplete_fields = ["chiro"]
    fields = ["chiro", "email", "link", "invited_by", "created_at", "accepted_at"]
    readonly_fields = ["link", "invited_by", "created_at", "accepted_at"]
    actions = ["send_again"]

    @admin.display(description="Link (after this site's address)")
    def link(self, obj: Invitation) -> str:
        return reverse("invitation_accept", args=[obj.token]) if obj.pk else "-"

    def save_model(self, request, obj, form, change) -> None:
        obj.invited_by = obj.invited_by or request.user
        super().save_model(request, obj, form, change)
        if not change:
            self._send(request, obj)

    def _send(self, request, invitation: Invitation) -> None:
        try:
            send_invitation(request, invitation)
            messages.success(request, f"Mail sent to {invitation.email}.")
        except (OSError, ValueError, smtplib.SMTPException) as exc:
            messages.error(
                request,
                f"The mail to {invitation.email} failed ({exc}). "
                "Pass on the link on the invitation's page instead.",
            )

    @admin.action(description="Send the invitation mail again")
    def send_again(self, request, queryset) -> None:
        for invitation in queryset:
            if invitation.is_open:
                self._send(request, invitation)
            else:
                messages.warning(
                    request,
                    f"{invitation.email}: used or expired. Create a new invitation.",
                )
