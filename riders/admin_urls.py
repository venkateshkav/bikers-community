from django.urls import path

from . import admin_views

app_name = "riders_admin"

urlpatterns = [
    path("", admin_views.rider_list_view, name="list"),
    path("create/", admin_views.rider_create_view, name="create"),
    path("import/", admin_views.rider_import_view, name="import"),
    path("import/sample/", admin_views.rider_import_sample_view, name="import-sample"),
    path("<int:rider_id>/edit/", admin_views.rider_edit_view, name="edit"),
    path("<int:rider_id>/toggle-active/", admin_views.rider_toggle_active_view, name="toggle-active"),
]
