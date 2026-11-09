from django.urls import path

from kitchen import views

urlpatterns = [
    path("chiros/<int:chiro_id>/stock/", views.chiro_stock, name="chiro_stock"),
    path("camps/<int:camp_id>/utensils/", views.camp_utensils, name="camp_utensils"),
]
