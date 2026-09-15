from django.urls import path

from . import views, views_reports

urlpatterns = [
    path("agreements/", views.agreements, name="agreements"),
    path("agreements/<int:template_id>/sign/", views.sign, name="sign_agreement"),
    path("approvals/", views.approvals, name="approvals"),
    path("approvals/<int:pk>/decide/", views.decide, name="decide_agreement"),
    path("computer-password/", views.computer_password, name="computer_password"),
    path("computer-password/manage/", views_reports.password_manage, name="password_manage"),
    path("access-rosters/", views_reports.access_rosters, name="access_rosters"),
    path("agreements/<int:pk>/pdf/", views_reports.agreement_pdf, name="agreement_pdf"),
    path("agreements/<int:pk>/revoke/", views_reports.agreement_revoke, name="agreement_revoke"),
]
