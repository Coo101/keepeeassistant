from django.urls import path

from camps import views

urlpatterns = [
    path("camps/", views.camp_list, name="camp_list"),
    path("camps/new/", views.camp_create, name="camp_create"),
    path("camps/<int:camp_id>/edit/", views.camp_edit, name="camp_edit"),
    path("camps/<int:camp_id>/delete/", views.camp_delete, name="camp_delete"),
]
