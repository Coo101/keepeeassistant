"""URL configuration (SPEC §9)."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("camps.urls")),
    path("", include("planning.urls")),
    path("", include("shopping.urls")),
]
