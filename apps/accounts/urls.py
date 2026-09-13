from django.urls import path

from . import views

urlpatterns = [
    path("", views.profile, name="profile"),
    path("invitations/", views.invitations, name="invitations"),
    path("invitations/<int:pk>/", views.invitation_action, name="invitation_action"),
    path("invite/<str:token>/", views.accept_invitation, name="accept_invitation"),
]
