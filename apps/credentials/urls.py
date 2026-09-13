from django.urls import path

from . import views

urlpatterns = [
    path("agreements/", views.agreements, name="agreements"),
    path("agreements/<int:template_id>/sign/", views.sign, name="sign_agreement"),
    path("approvals/", views.approvals, name="approvals"),
    path("approvals/<int:pk>/decide/", views.decide, name="decide_agreement"),
    path("computer-password/", views.computer_password, name="computer_password"),
]
