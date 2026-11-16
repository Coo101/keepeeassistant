from django.urls import path

from pages import views

urlpatterns = [
    path("", views.home, name="home"),
    path("news/", views.post_list, name="post_list"),
    path("news/<slug:slug>/", views.post_detail, name="post_detail"),
    path("docs/<slug:slug>/", views.doc, name="doc"),
]
