from django.contrib import admin

from recipes.models import (
    Ingredient,
    IngredientPrice,
    Recipe,
    RecipeIngredient,
    RecipeStep,
)


class IngredientPriceInline(admin.TabularInline):
    model = IngredientPrice
    extra = 1
    autocomplete_fields = ["camp"]
    readonly_fields = ["unit", "created_by"]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "unit",
        "category",
        "shop",
        "latest_price",
        "latest_price_date",
        "product_details",
    ]
    list_filter = ["shop", "category", "unit"]
    search_fields = ["name", "product_details"]
    list_editable = ["shop"]
    inlines = [IngredientPriceInline]

    def save_formset(self, request, form, formset, change) -> None:
        for price in formset.save(commit=False):
            price.created_by = price.created_by or request.user
            price.save()
        for deleted in formset.deleted_objects:
            deleted.delete()

    def get_queryset(self, request):
        return super().get_queryset(request).with_latest_price()

    @admin.display(description="Latest price")
    def latest_price(self, obj: Ingredient):
        return obj.latest_price

    @admin.display(description="Price date")
    def latest_price_date(self, obj: Ingredient):
        return obj.latest_price_date


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 3
    autocomplete_fields = ["ingredient"]


class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 3


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "author",
        "others_can_edit",
        "dish_type",
        "base_children",
        "base_teens",
        "base_portions",
        "total_duration_minutes",
    ]
    list_filter = ["dish_type"]
    search_fields = ["name"]
    autocomplete_fields = ["author"]
    inlines = [RecipeIngredientInline, RecipeStepInline]

    @admin.display(description="Base portions")
    def base_portions(self, obj: Recipe) -> str:
        return str(obj.base_portions)

    @admin.display(description="Total time (min)")
    def total_duration_minutes(self, obj: Recipe) -> int:
        return obj.total_duration_minutes
