"""URL configuration (SPEC §9)."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Only login/logout: password reset would need a mail backend.
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    # Open to anonymous users: logging out after the session expired must not
    # bounce through the login form back to this POST-only view.
    path(
        "accounts/logout/",
        login_not_required(auth_views.LogoutView.as_view()),
        name="logout",
    ),
    path("", include("camps.urls")),
    path("", include("recipes.urls")),
    path("", include("planning.urls")),
    path("", include("shopping.urls")),
]
