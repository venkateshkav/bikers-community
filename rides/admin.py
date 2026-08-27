from django.contrib import admin
from django.utils import timezone

from . import services
from .models import AuditLog, Ride, RideRegistration


class RideRegistrationInline(admin.TabularInline):
    model = RideRegistration
    extra = 0
    fields = (
        "rider",
        "status",
        "starting_point_reached_at",
        "destination_reached_at",
        "home_reached_at",
    )
    readonly_fields = ("starting_point_reached_at", "destination_reached_at", "home_reached_at")
    autocomplete_fields = ("rider",)


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("name", "ride_date", "start_location", "destination", "status", "approved_count", "total_count")
    list_filter = ("status", "ride_date")
    search_fields = ("name", "start_location", "destination")
    date_hierarchy = "ride_date"
    inlines = [RideRegistrationInline]
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not change or obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Approved")
    def approved_count(self, obj):
        return obj.registrations.filter(status=RideRegistration.Status.APPROVED).count()

    @admin.display(description="Total")
    def total_count(self, obj):
        return obj.registrations.count()


@admin.register(RideRegistration)
class RideRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "rider",
        "ride",
        "status",
        "starting_point_reached_at",
        "destination_reached_at",
        "home_reached_at",
    )
    list_filter = ("status", "ride")
    search_fields = ("rider__name", "rider__email", "ride__name")
    autocomplete_fields = ("ride", "rider")
    readonly_fields = (
        "registered_at",
        "approved_at",
        "rejected_at",
        "cancelled_at",
        "starting_point_reached_at",
        "destination_reached_at",
        "home_reached_at",
    )
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="Approve selected registrations")
    def approve_selected(self, request, queryset):
        for registration in queryset:
            services.approve_registration(registration, changed_by=request.user, reason="Bulk admin approval")

    @admin.action(description="Reject selected registrations")
    def reject_selected(self, request, queryset):
        for registration in queryset:
            services.reject_registration(registration, changed_by=request.user, reason="Bulk admin rejection")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "rider", "ride", "changed_by")
    list_filter = ("action",)
    search_fields = ("rider__name", "ride__name", "action", "reason")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
