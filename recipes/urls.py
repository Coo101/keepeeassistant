from django.urls import path

from recipes import views

urlpatterns = [
    path("recipes/", views.recipe_list, name="recipe_list"),
    path("recipes/new/", views.recipe_create, name="recipe_create"),
    path("recipes/<int:recipe_id>/", views.recipe_detail, name="recipe_detail"),
    path("recipes/<int:recipe_id>/edit/", views.recipe_edit, name="recipe_edit"),
    path("recipes/<int:recipe_id>/copy/", views.recipe_copy, name="recipe_copy"),
    path("recipes/<int:recipe_id>/delete/", views.recipe_delete, name="recipe_delete"),
    path("recipes/<int:recipe_id>.pdf", views.recipe_pdf, name="recipe_pdf"),
    path("ingredients/", views.ingredient_list, name="ingredient_list"),
    path("ingredients/new/", views.ingredient_create, name="ingredient_create"),
    path(
        "ingredients/quick-add/",
        views.ingredient_quick_add,
        name="ingredient_quick_add",
    ),
    path(
        "ingredients/<int:ingredient_id>/delete/",
        views.ingredient_delete,
        name="ingredient_delete",
    ),
    path(
        "ingredients/<int:ingredient_id>/edit/",
        views.ingredient_edit,
        name="ingredient_edit",
    ),
]
