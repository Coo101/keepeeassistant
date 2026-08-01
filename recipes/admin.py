from django.contrib import admin

from recipes.models import Ingredient, Recipe, RecipeIngredient, RecipeStep


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "unit",
        "category",
        "shop",
        "price_per_unit",
        "product_details",
        "price_updated",
    ]
    list_filter = ["shop", "category", "unit"]
    search_fields = ["name", "product_details"]
    list_editable = ["shop", "price_per_unit"]


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
        "dish_type",
        "base_children",
        "base_teens",
        "base_portions",
        "total_duration_minutes",
    ]
    list_filter = ["dish_type"]
    search_fields = ["name"]
    inlines = [RecipeIngredientInline, RecipeStepInline]

    @admin.display(description="Base portions")
    def base_portions(self, obj: Recipe) -> str:
        return str(obj.base_portions)

    @admin.display(description="Total time (min)")
    def total_duration_minutes(self, obj: Recipe) -> int:
        return obj.total_duration_minutes
