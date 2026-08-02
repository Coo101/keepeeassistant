"""URL configuration (SPEC §9)."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Only login/logout: password reset would need a mail backend.
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("camps.urls")),
    path("", include("recipes.urls")),
    path("", include("planning.urls")),
    path("", include("shopping.urls")),
]
