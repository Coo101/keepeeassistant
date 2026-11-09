from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from camps.models import Camp, CampGroup, DayNote


class CampGroupInline(admin.TabularInline):
    model = CampGroup
    extra = 1


@admin.register(Camp)
class CampAdmin(admin.ModelAdmin):
    inlines = [CampGroupInline]
    # Set from the groups (SPEC §9.3).
    readonly_fields = ["num_children", "num_teens", "num_staff"]
    list_display = [
        "name",
        "chiro",
        "start_date",
        "end_date",
        "num_children",
        "num_teens",
        "num_staff",
        "demand_portions",
    ]
    list_filter = ["chiro"]
    search_fields = ["name"]
    fieldsets = (
        (None, {"fields": ("chiro", "name", "start_date", "end_date")}),
        (_("Headcount"), {"fields": ("num_children", "num_teens", "num_staff")}),
        (
            _("Meal times"),
            {
                "fields": (
                    "breakfast_time",
                    "lunch_time",
                    "teatime_time",
                    "dinner_time",
                )
            },
        ),
        (
            _("Runbook info (front pages)"),
            {
                "fields": (
                    "cook_team",
                    "location",
                    "contact_leader",
                    "contact_rental",
                    "bakery",
                    "general_notes",
                )
            },
        ),
    )

    def save_related(self, request, form, formsets, change) -> None:
        super().save_related(request, form, formsets, change)
        form.instance.update_headcount()

    @admin.display(description=_("Demand portions"))
    def demand_portions(self, obj: Camp) -> str:
        return str(obj.demand_portions)


@admin.register(DayNote)
class DayNoteAdmin(admin.ModelAdmin):
    list_display = ["camp", "date"]
    list_filter = ["camp"]
