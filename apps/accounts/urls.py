from django.urls import path

from apps.comms import views as comms_views

from . import guardian, impersonate, views, views_entry, views_push

urlpatterns = [
    path("", views.profile, name="profile"),
    path("notifications/", views.notifications, name="notifications"),
    path("uls-name/", views.uls_name_decide, name="uls_name_decide"),
    path("messages/", comms_views.my_messages, name="my_messages"),
    path("push/subscribe/", views_push.push_subscribe, name="push_subscribe"),
    path("push/<int:pk>/revoke/", views_push.push_revoke, name="push_revoke"),
    path("push/toggle/", views_push.push_toggle, name="push_toggle"),
    path("view-as/stop/", impersonate.stop, name="impersonate_stop"),
    path("wards/<int:pk>/act/", guardian.act_start, name="act_start"),
    path("act/stop/", guardian.act_stop, name="act_stop"),
    path("wards/<int:pk>/password/", guardian.ward_password, name="ward_password"),
    path("close/", views.request_closure, name="request_closure"),
    path("invitations/", views.invitations, name="invitations"),
    path("invitations/<int:pk>/", views.invitation_action, name="invitation_action"),
    path("entry-links/", views_entry.entry_links, name="entry_links"),
    path("entry-links/<int:pk>/", views_entry.entry_link_action, name="entry_link_action"),
    path("invite/<str:token>/", views.accept_invitation, name="accept_invitation"),
]
