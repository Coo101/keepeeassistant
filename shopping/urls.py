from django.urls import path

from shopping import views

urlpatterns = [
    path("camps/<int:camp_id>/shopping/", views.shopping, name="shopping"),
    path("camps/<int:camp_id>/budget/", views.budget, name="budget"),
    path(
        "camps/<int:camp_id>/shopping.pdf",
        views.shopping_pdf,
        name="shopping_pdf",
    ),
]
