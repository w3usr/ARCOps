from django.urls import path

from . import views, views_entry

urlpatterns = [
    path("", views.profile, name="profile"),
    path("invitations/", views.invitations, name="invitations"),
    path("invitations/<int:pk>/", views.invitation_action, name="invitation_action"),
    path("entry-links/", views_entry.entry_links, name="entry_links"),
    path("entry-links/<int:pk>/", views_entry.entry_link_action, name="entry_link_action"),
    path("invite/<str:token>/", views.accept_invitation, name="accept_invitation"),
]
