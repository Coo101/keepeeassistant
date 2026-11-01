from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db import transaction
from django.urls import reverse

from accounts.invitations import MAIL_ERRORS, send_invitation
from accounts.models import (
    Chiro,
    Invitation,
    JoinRequest,
    Membership,
    RateLimitHit,
    Role,
)
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
    fields = [
        "chiro",
        "email",
        "role",
        "link",
        "invited_by",
        "created_at",
        "accepted_at",
    ]
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
        except MAIL_ERRORS as exc:
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


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "chiro_name", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["name", "email", "chiro_name"]
    actions = ["approve", "reject"]

    def has_add_permission(self, request) -> bool:
        return False

    @admin.action(description="Approve: create the Chiro if needed, and invite")
    def approve(self, request, queryset) -> None:
        for join in queryset.filter(status=JoinRequest.Status.OPEN):
            invitation = self._invitation_for(join, request)
            if invitation is None:
                messages.info(
                    request,
                    f"{join.email} is already a member or has an open invitation.",
                )
                continue
            try:
                send_invitation(request, invitation)
                messages.success(
                    request, f"Invited {join.email} to {invitation.chiro}."
                )
            except MAIL_ERRORS as exc:
                messages.error(
                    request,
                    f"The mail to {join.email} failed ({exc}). Pass on the link on "
                    "the invitation's page instead.",
                )

    @transaction.atomic
    def _invitation_for(self, join: JoinRequest, request) -> Invitation | None:
        """Marks the request approved; None if nobody needs inviting."""
        join.status = JoinRequest.Status.APPROVED
        join.save(update_fields=["status"])
        chiro = Chiro.objects.filter(name__iexact=join.chiro_name).first()
        if chiro:
            members = chiro.membership_set.filter(user__email__iexact=join.email)
            invitations = chiro.invitation_set.filter(email__iexact=join.email)
            if members.exists() or any(i.is_open for i in invitations):
                return None
        else:
            chiro = Chiro.objects.create(name=join.chiro_name)
        # A Chiro without an admin gets its first one here; others join as members.
        role = Role.MEMBER if chiro.has_admin() else Role.ADMIN
        return Invitation.objects.create(
            chiro=chiro, email=join.email, role=role, invited_by=request.user
        )

    @admin.action(description="Reject (sends no mail)")
    def reject(self, request, queryset) -> None:
        queryset.filter(status=JoinRequest.Status.OPEN).update(
            status=JoinRequest.Status.REJECTED
        )
