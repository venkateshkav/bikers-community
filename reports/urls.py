from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.report_list_view, name="list"),
    path("rides/<int:ride_id>/", views.ride_report_view, name="ride-report"),
    path("rides/<int:ride_id>/export/csv/", views.export_csv_view, name="export-csv"),
    path("rides/<int:ride_id>/export/excel/", views.export_excel_view, name="export-excel"),
    path("rides/<int:ride_id>/export/pdf/", views.export_pdf_view, name="export-pdf"),
]
