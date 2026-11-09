"""URL configuration (SPEC §9)."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path
from django.views.i18n import set_language

from accounts.ratelimit import (
    LimitedLoginForm,
    LimitedPasswordResetForm,
    UnlockingSetPasswordForm,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(authentication_form=LimitedLoginForm),
        name="login",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=UnlockingSetPasswordForm
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/password_reset/",
        auth_views.PasswordResetView.as_view(form_class=LimitedPasswordResetForm),
        name="password_reset",
    ),
    # Open to anonymous users: logging out after the session expired must not
    # bounce through the login form back to this POST-only view.
    path(
        "accounts/logout/",
        login_not_required(auth_views.LogoutView.as_view()),
        name="logout",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("language/", login_not_required(set_language), name="set_language"),
    path("", include("accounts.urls")),
    path("", include("pages.urls")),
    path("", include("camps.urls")),
    path("", include("recipes.urls")),
    path("", include("planning.urls")),
    path("", include("shopping.urls")),
    path("", include("bills.urls")),
    path("", include("kitchen.urls")),
]
