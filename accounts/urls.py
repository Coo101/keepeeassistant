from django.urls import path

from accounts import views

urlpatterns = [
    path("account/", views.account, name="account"),
    path(
        "invitations/<str:token>/",
        views.invitation_accept,
        name="invitation_accept",
    ),
]
