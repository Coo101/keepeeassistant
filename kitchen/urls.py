from django.urls import path

from kitchen import views

urlpatterns = [
    path("chiros/<int:chiro_id>/stock/", views.chiro_stock, name="chiro_stock"),
    path(
        "chiros/<int:chiro_id>/stock/pantry-row/",
        views.pantry_row,
        name="pantry_row",
    ),
    path("camps/<int:camp_id>/utensils/", views.camp_utensils, name="camp_utensils"),
    path(
        "camps/<int:camp_id>/utensils/row/",
        views.camp_utensil_row,
        name="camp_utensil_row",
    ),
]
