from django.contrib import admin

from bills.models import Bill, LineMatch


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    # No file field: bills are only opened through the access-checked view.
    list_display = ["__str__", "camp", "status", "uploaded_at"]
    list_filter = ["status", "shop"]
    fields = ["camp", "shop", "date", "status", "error", "printed_total"]
    readonly_fields = ["camp"]

    def has_add_permission(self, request) -> bool:
        return False


@admin.register(LineMatch)
class LineMatchAdmin(admin.ModelAdmin):
    list_display = ["key", "shop", "ingredient", "pack_amount", "unit"]
    list_filter = ["shop"]
    search_fields = ["key"]
