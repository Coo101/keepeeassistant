from django.urls import path

from planning import views

urlpatterns = [
    path("camps/<int:camp_id>/plan/", views.planner, name="planner"),
    path(
        "camps/<int:camp_id>/plan/<str:date>/<str:meal_type>/",
        views.edit_slot,
        name="edit_slot",
    ),
    path(
        "camps/<int:camp_id>/overview.pdf",
        views.overview_pdf,
        name="overview_pdf",
    ),
]
