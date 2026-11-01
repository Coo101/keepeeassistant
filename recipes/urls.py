from django.urls import path

from recipes import views

urlpatterns = [
    path("recipes/", views.recipe_list, name="recipe_list"),
    path("recipes/new/", views.recipe_create, name="recipe_create"),
    path("recipes/<int:recipe_id>/", views.recipe_detail, name="recipe_detail"),
    path("recipes/<int:recipe_id>/edit/", views.recipe_edit, name="recipe_edit"),
    path("recipes/<int:recipe_id>/copy/", views.recipe_copy, name="recipe_copy"),
    path("recipes/<int:recipe_id>.pdf", views.recipe_pdf, name="recipe_pdf"),
]
