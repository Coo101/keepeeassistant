from django.contrib import admin

from camps.models import Camp


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

    @admin.display(description="Demand portions")
    def demand_portions(self, obj: Camp) -> str:
        return str(obj.demand_portions)
