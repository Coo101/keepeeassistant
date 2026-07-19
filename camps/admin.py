from django.contrib import admin

from camps.models import Camp, DayNote


@admin.register(Camp)
class CampAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "start_date",
        "end_date",
        "num_children",
        "num_teens",
        "num_staff",
        "demand_portions",
    ]
    search_fields = ["name"]
    fieldsets = (
        (None, {"fields": ("name", "start_date", "end_date")}),
        ("Headcount", {"fields": ("num_children", "num_teens", "num_staff")}),
        (
            "Meal times",
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
            "Runbook info (front pages)",
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

    @admin.display(description="Demand portions")
    def demand_portions(self, obj: Camp) -> str:
        return str(obj.demand_portions)


@admin.register(DayNote)
class DayNoteAdmin(admin.ModelAdmin):
    list_display = ["camp", "date"]
    list_filter = ["camp"]
