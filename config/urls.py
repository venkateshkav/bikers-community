from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/rider/login/", permanent=False)),
    path("admin/", admin.site.urls),
    path("dashboard/", include("rides.admin_urls")),
    path("dashboard/riders/", include("riders.admin_urls")),
    path("reports/", include("reports.urls")),
    path("rider/", include("accounts.urls")),
    path("rider/", include("riders.urls")),
    path("rider/", include("rides.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
