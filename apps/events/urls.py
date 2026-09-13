from django.urls import path

from . import views, views_manage

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path("mine/", views.my_schedule, name="my_schedule"),
    path("<int:pk>/", views.event_detail, name="event_detail"),
    path("<int:pk>/publish/", views.publish, name="event_publish"),
    path("new/", views_manage.event_create, name="event_create"),
    path("<int:pk>/manage/", views_manage.event_manage, name="event_manage"),
    path("<int:pk>/periods/add/", views_manage.period_add, name="period_add"),
    path("<int:pk>/periods/<int:period_id>/delete/", views_manage.period_delete, name="period_delete"),
    path("<int:pk>/locations/add/", views_manage.location_add, name="location_add"),
    path("<int:pk>/locations/<int:location_id>/positions/add/", views_manage.position_add, name="position_add"),
    path("<int:pk>/positions/<int:position_id>/delete/", views_manage.position_delete, name="position_delete"),
    path("<int:pk>/captains/add/", views_manage.captain_add, name="captain_add"),
    path("<int:pk>/captains/<int:user_id>/remove/", views_manage.captain_remove, name="captain_remove"),
    path("<int:pk>/slots/generate/", views_manage.slots_generate, name="slots_generate"),
    path("<int:pk>/duplicate/", views_manage.event_duplicate, name="event_duplicate"),
    path("<int:pk>/cancel/", views_manage.event_cancel, name="event_cancel"),
    path("slot/<int:slot_id>/toggle/", views_manage.slot_toggle, name="slot_toggle"),
    path("slot/<int:slot_id>/signup/", views.sign_up, name="sign_up"),
    path("signup/<int:signup_id>/cancel/", views.cancel_signup, name="cancel_signup"),
    path("signup/<int:signup_id>/checkin/", views.check_in, name="check_in"),
    path("signup/<int:signup_id>/confirm/", views.confirm_signup, name="confirm_signup"),
]
