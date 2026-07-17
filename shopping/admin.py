from django.contrib import admin

from shopping.models import ShoppingTrip


@admin.register(ShoppingTrip)
class ShoppingTripAdmin(admin.ModelAdmin):
    list_display = ["camp", "date"]
    list_filter = ["camp"]
