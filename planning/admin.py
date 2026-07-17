from django.contrib import admin

from planning.models import MenuEntry


@admin.register(MenuEntry)
class MenuEntryAdmin(admin.ModelAdmin):
    list_display = ["camp", "date", "meal_type", "course", "recipe"]
    list_filter = ["camp", "meal_type"]
    date_hierarchy = "date"
    autocomplete_fields = ["recipe"]
