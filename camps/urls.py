from django.urls import path

from camps import views

urlpatterns = [
    path("camps/", views.camp_list, name="camp_list"),
    path("camps/new/", views.camp_create, name="camp_create"),
    path("camps/group-row/", views.camp_group_row, name="camp_group_row"),
    path("camps/<int:camp_id>/edit/", views.camp_edit, name="camp_edit"),
    path("camps/<int:camp_id>/delete/", views.camp_delete, name="camp_delete"),
    path("camps/<int:camp_id>/archive/", views.camp_archive, name="camp_archive"),
    path("camps/<int:camp_id>/diets/", views.camp_diets, name="camp_diets"),
]
