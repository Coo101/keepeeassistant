from django.urls import path

from camps import views

urlpatterns = [
    path("", views.camp_list, name="camp_list"),
]
