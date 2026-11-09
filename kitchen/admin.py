from django.contrib import admin

from kitchen.models import CampUtensil, Utensil


@admin.register(Utensil)
class UtensilAdmin(admin.ModelAdmin):
    list_display = ["name", "chiro", "in_stock", "note"]
    list_filter = ["chiro"]
    search_fields = ["name"]


@admin.register(CampUtensil)
class CampUtensilAdmin(admin.ModelAdmin):
    list_display = ["camp", "utensil", "needed"]
    list_filter = ["camp"]
    autocomplete_fields = ["utensil"]
