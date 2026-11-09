from django.urls import path

from bills import views

urlpatterns = [
    path("camps/<int:camp_id>/bills/", views.bill_list, name="bill_list"),
    path("camps/<int:camp_id>/report/", views.report, name="financial_report"),
    path("camps/<int:camp_id>/report.pdf", views.report_pdf, name="report_pdf"),
    path(
        "camps/<int:camp_id>/bills/<int:bill_id>/",
        views.bill_detail,
        name="bill_detail",
    ),
    path(
        "camps/<int:camp_id>/bills/<int:bill_id>/file/",
        views.bill_file,
        name="bill_file",
    ),
    path(
        "camps/<int:camp_id>/bills/<int:bill_id>/retry/",
        views.bill_retry,
        name="bill_retry",
    ),
    path(
        "camps/<int:camp_id>/bills/<int:bill_id>/remove-file/",
        views.bill_remove_file,
        name="bill_remove_file",
    ),
    path(
        "camps/<int:camp_id>/bills/<int:bill_id>/delete/",
        views.bill_delete,
        name="bill_delete",
    ),
]
