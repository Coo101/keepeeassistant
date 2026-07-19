from django.urls import path

from recipes import views

urlpatterns = [
    path("recipes/", views.recipe_list, name="recipe_list"),
    path("recipes/<int:recipe_id>/", views.recipe_detail, name="recipe_detail"),
    path("recipes/<int:recipe_id>.pdf", views.recipe_pdf, name="recipe_pdf"),
]
