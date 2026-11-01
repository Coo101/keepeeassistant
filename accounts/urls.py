from django.urls import path

from accounts import views

urlpatterns = [
    path("account/", views.account, name="account"),
    path("join/", views.join_request, name="join_request"),
    path("chiros/<int:chiro_id>/", views.chiro_detail, name="chiro_detail"),
    path(
        "chiros/<int:chiro_id>/members/<int:membership_id>/",
        views.chiro_member,
        name="chiro_member",
    ),
    path(
        "chiros/<int:chiro_id>/invitations/<int:invitation_id>/cancel/",
        views.invitation_cancel,
        name="invitation_cancel",
    ),
    path(
        "invitations/<str:token>/",
        views.invitation_accept,
        name="invitation_accept",
    ),
]
