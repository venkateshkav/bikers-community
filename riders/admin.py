from django.contrib import admin

from .models import Rider

admin.site.site_header = "Bikers Community Admin"
admin.site.site_title = "Bikers Community"
admin.site.index_title = "Ride Management"


@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "mobile", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "email", "mobile")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50
    fieldsets = (
        (None, {"fields": ("name", "email", "mobile", "is_active")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
