from django.urls import path

from . import views

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path("mine/", views.my_schedule, name="my_schedule"),
    path("<int:pk>/", views.event_detail, name="event_detail"),
    path("<int:pk>/publish/", views.publish, name="event_publish"),
    path("slot/<int:slot_id>/signup/", views.sign_up, name="sign_up"),
    path("signup/<int:signup_id>/cancel/", views.cancel_signup, name="cancel_signup"),
    path("signup/<int:signup_id>/checkin/", views.check_in, name="check_in"),
    path("signup/<int:signup_id>/confirm/", views.confirm_signup, name="confirm_signup"),
]
