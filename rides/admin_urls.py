from django.urls import path

from . import admin_views

app_name = "admin_panel"

urlpatterns = [
    path("", admin_views.dashboard_view, name="dashboard"),
    path("audit-logs/", admin_views.audit_log_view, name="audit-logs"),
    path("rides/manage/", admin_views.ride_list_view, name="ride-list"),
    path("rides/manage/create/", admin_views.ride_create_view, name="ride-create"),
    path("rides/manage/<int:ride_id>/edit/", admin_views.ride_edit_view, name="ride-edit"),
    path("rides/manage/<int:ride_id>/cancel/", admin_views.ride_cancel_view, name="ride-cancel"),
    path("rides/<int:ride_id>/", admin_views.ride_status_view, name="ride-status"),
    path(
        "rides/<int:ride_id>/registrations/<int:registration_id>/override/",
        admin_views.manual_override_view,
        name="manual-override",
    ),
    path("rides/<int:ride_id>/registrations/add/", admin_views.add_registration_view, name="registration-add"),
    path(
        "rides/<int:ride_id>/registrations/<int:registration_id>/approve/",
        admin_views.approve_registration_view,
        name="registration-approve",
    ),
    path(
        "rides/<int:ride_id>/registrations/<int:registration_id>/reject/",
        admin_views.reject_registration_view,
        name="registration-reject",
    ),
    path(
        "rides/<int:ride_id>/registrations/<int:registration_id>/cancel/",
        admin_views.cancel_registration_view,
        name="registration-cancel",
    ),
]
