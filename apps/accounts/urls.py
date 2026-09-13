from django.urls import path

from . import views

urlpatterns = [
    path("", views.profile, name="profile"),
    path("invitations/", views.invitations, name="invitations"),
    path("invite/<str:token>/", views.accept_invitation, name="accept_invitation"),
]
