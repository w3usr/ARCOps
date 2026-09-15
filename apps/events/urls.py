from django.urls import path

from . import views, views_manage, views_member, views_rules, views_slots

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path("mine/", views.my_schedule, name="my_schedule"),
    path("<int:pk>/", views.event_detail, name="event_detail"),
    path("<int:pk>/publish/", views.publish, name="event_publish"),
    path("new/", views_manage.event_create, name="event_create"),
    path("<int:pk>/manage/", views_manage.event_manage, name="event_manage"),
    path("<int:pk>/periods/add/", views_manage.period_add, name="period_add"),
    path(
        "<int:pk>/periods/<int:period_id>/delete/", views_manage.period_delete, name="period_delete"
    ),
    path("<int:pk>/locations/add/", views_manage.location_add, name="location_add"),
    path(
        "<int:pk>/locations/<int:location_id>/positions/add/",
        views_manage.position_add,
        name="position_add",
    ),
    path(
        "<int:pk>/positions/<int:position_id>/delete/",
        views_manage.position_delete,
        name="position_delete",
    ),
    path("<int:pk>/captains/add/", views_manage.captain_add, name="captain_add"),
    path(
        "<int:pk>/captains/<int:user_id>/remove/",
        views_manage.captain_remove,
        name="captain_remove",
    ),
    path("<int:pk>/slots/generate/", views_manage.slots_generate, name="slots_generate"),
    path("<int:pk>/duplicate/", views_manage.event_duplicate, name="event_duplicate"),
    path("<int:pk>/cancel/", views_manage.event_cancel, name="event_cancel"),
    path("slot/<int:slot_id>/toggle/", views_manage.slot_toggle, name="slot_toggle"),
    path("<int:pk>/tz/", views_slots.roster_tz, name="roster_tz"),
    path("<int:pk>/slot/<int:slot_id>/", views_slots.slot_detail, name="slot_detail"),
    path("<int:pk>/slot/<int:slot_id>/seats/", views_slots.slot_capacities, name="slot_capacities"),
    path(
        "<int:pk>/slot/<int:slot_id>/control-operator/",
        views_slots.slot_control_operator,
        name="slot_control_operator",
    ),
    path("<int:pk>/slot/<int:slot_id>/assign/", views_slots.slot_assign, name="slot_assign"),
    path("<int:pk>/bulk/", views_slots.event_bulk, name="event_bulk"),
    path("signup/<int:signup_id>/no-show/", views_slots.signup_no_show, name="signup_no_show"),
    path("slot/<int:slot_id>/signup/", views.sign_up, name="sign_up"),
    path("signup/<int:signup_id>/cancel/", views.cancel_signup, name="cancel_signup"),
    path("signup/<int:signup_id>/checkin/", views.check_in, name="check_in"),
    path("signup/<int:signup_id>/confirm/", views.confirm_signup, name="confirm_signup"),
    path("confirm/<str:token>/", views.confirm_by_token, name="confirm_by_token"),
    path("<int:pk>/state/", views_rules.event_state, name="event_state"),
    path("<int:pk>/limits/", views_rules.limits_save, name="limits_save"),
    path("<int:pk>/eligibility/", views_rules.eligibility_save, name="eligibility_save"),
    path(
        "<int:pk>/slot/<int:slot_id>/eligibility/",
        views_rules.slot_eligibility,
        name="slot_eligibility",
    ),
    path("<int:pk>/openings/add/", views_rules.opening_add, name="opening_add"),
    path(
        "<int:pk>/openings/<int:opening_id>/delete/",
        views_rules.opening_delete,
        name="opening_delete",
    ),
    path("<int:pk>/roster.csv", views_member.roster_csv, name="roster_csv"),
    path(
        "signup/<int:signup_id>/role/", views_member.signup_change_role, name="signup_change_role"
    ),
    path("slot/<int:slot_id>/waitlist/", views_member.waitlist_join, name="waitlist_join"),
    path("waitlist/<int:pk>/withdraw/", views_member.waitlist_withdraw, name="waitlist_withdraw"),
    path("waitlist/<int:pk>/accept/", views_member.waitlist_accept, name="waitlist_accept"),
    path("feed/<str:token>.ics", views_member.ical_feed, name="ical_feed"),
    path("health/", views_member.health_overview, name="health_overview"),
    path("cannot/<str:token>/", views.cannot_by_token, name="cannot_by_token"),
]
