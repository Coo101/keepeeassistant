from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from accounts.models import Chiro, Membership


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


admin.site.unregister(User)


@admin.register(User)
class ChiroUserAdmin(UserAdmin):
    """The usual user admin, plus which Chiros the user belongs to."""

    inlines = [UserChiroInline]
