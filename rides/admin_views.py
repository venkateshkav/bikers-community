"""
Custom, premium-styled admin dashboard views (separate from django.contrib.admin,
which is still used for raw CRUD on Rider/Ride/RideRegistration/AuditLog).
These pages answer, at a glance: who is participating, who has reached each
checkpoint, and who is still pending.
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from . import services
from .forms import AddRiderToRideForm, RideForm
from .models import AuditLog, Ride, RideRegistration

OVERRIDE_FIELDS = {
    "starting_point_reached_at": "Starting Point",
    "destination_reached_at": "Destination",
    "home_reached_at": "Home Confirmation",
}


@staff_member_required
def dashboard_view(request):
    rides = (
        Ride.objects.exclude(status=Ride.Status.DRAFT)
        .prefetch_related("registrations")
        .order_by("-ride_date", "-start_time")[:25]
    )
    ride_cards = [services.ride_summary(ride) for ride in rides]
    return render(request, "admin_panel/dashboard.html", {"ride_cards": ride_cards, "active_nav": "dashboard"})


@staff_member_required
def ride_list_view(request):
    rides = Ride.objects.all()

    name = request.GET.get("name", "").strip()
    status = request.GET.get("status", "").strip()
    ride_date = request.GET.get("date", "").strip()

    if name:
        rides = rides.filter(name__icontains=name)
    if status:
        rides = rides.filter(status=status)
    if ride_date:
        rides = rides.filter(ride_date=ride_date)

    return render(
        request,
        "admin_panel/ride_list.html",
        {
            "rides": rides,
            "status_choices": Ride.Status.choices,
            "filters": {"name": name, "status": status, "date": ride_date},
            "active_nav": "rides",
        },
    )


@staff_member_required
def ride_create_view(request):
    form = RideForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ride = form.save(commit=False)
        ride.created_by = request.user
        ride.save()
        messages.success(request, f"{ride.name} created.")
        return redirect("admin_panel:ride-status", ride_id=ride.id)

    return render(request, "admin_panel/ride_form.html", {"form": form, "title": "Create Ride", "active_nav": "rides"})


@staff_member_required
def ride_edit_view(request, ride_id):
    ride = get_object_or_404(Ride, pk=ride_id)
    form = RideForm(request.POST or None, instance=ride)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{ride.name} updated.")
        return redirect("admin_panel:ride-status", ride_id=ride.id)

    return render(
        request, "admin_panel/ride_form.html", {"form": form, "title": "Edit Ride", "ride": ride, "active_nav": "rides"}
    )


@staff_member_required
@require_http_methods(["POST"])
def ride_cancel_view(request, ride_id):
    ride = get_object_or_404(Ride, pk=ride_id)
    ride.status = Ride.Status.CANCELLED
    ride.save(update_fields=["status"])
    messages.success(request, f"{ride.name} has been cancelled.")
    return redirect("admin_panel:ride-list")


@staff_member_required
def ride_status_view(request, ride_id):
    ride = get_object_or_404(Ride, pk=ride_id)
    registrations = ride.registrations.select_related("rider").order_by("rider__name")
    summary = services.ride_summary(ride)
    add_rider_form = AddRiderToRideForm(ride)
    return render(
        request,
        "admin_panel/ride_status.html",
        {
            "ride": ride,
            "registrations": registrations,
            "summary": summary,
            "override_fields": OVERRIDE_FIELDS,
            "add_rider_form": add_rider_form,
            "active_nav": "rides",
        },
    )


@staff_member_required
@require_http_methods(["POST"])
def add_registration_view(request, ride_id):
    ride = get_object_or_404(Ride, pk=ride_id)
    form = AddRiderToRideForm(ride, request.POST)
    if form.is_valid():
        rider = form.cleaned_data["rider"]
        registration, created = RideRegistration.objects.get_or_create(
            ride=ride, rider=rider, defaults={"status": RideRegistration.Status.PENDING}
        )
        if not created:
            # Re-adding a previously rejected/cancelled rider - reset to pending.
            registration.status = RideRegistration.Status.PENDING
            registration.rejected_at = None
            registration.cancelled_at = None
            registration.save(update_fields=["status", "rejected_at", "cancelled_at"])
        if form.cleaned_data["auto_approve"]:
            services.approve_registration(registration, changed_by=request.user, reason="Added and approved by admin")
        messages.success(request, f"{rider.name} added to the ride.")
    else:
        messages.error(request, "Please select a rider to add.")
    return redirect("admin_panel:ride-status", ride_id=ride_id)


@staff_member_required
@require_http_methods(["POST"])
def approve_registration_view(request, ride_id, registration_id):
    registration = get_object_or_404(RideRegistration, pk=registration_id, ride_id=ride_id)
    services.approve_registration(registration, changed_by=request.user)
    messages.success(request, f"{registration.rider.name} approved for this ride.")
    return redirect("admin_panel:ride-status", ride_id=ride_id)


@staff_member_required
@require_http_methods(["POST"])
def reject_registration_view(request, ride_id, registration_id):
    registration = get_object_or_404(RideRegistration, pk=registration_id, ride_id=ride_id)
    services.reject_registration(registration, changed_by=request.user)
    messages.success(request, f"{registration.rider.name} rejected for this ride.")
    return redirect("admin_panel:ride-status", ride_id=ride_id)


@staff_member_required
@require_http_methods(["POST"])
def cancel_registration_view(request, ride_id, registration_id):
    registration = get_object_or_404(RideRegistration, pk=registration_id, ride_id=ride_id)
    services.cancel_registration(registration, changed_by=request.user, reason="Cancelled by admin")
    messages.success(request, f"{registration.rider.name} removed from this ride.")
    return redirect("admin_panel:ride-status", ride_id=ride_id)


@staff_member_required
def manual_override_view(request, ride_id, registration_id):
    registration = get_object_or_404(RideRegistration, pk=registration_id, ride_id=ride_id)

    if request.method == "POST":
        field = request.POST.get("field")
        reason = request.POST.get("reason", "").strip()
        if field not in OVERRIDE_FIELDS:
            messages.error(request, "Invalid field selected.")
        elif not reason:
            messages.error(request, "A reason is required for every manual override.")
        elif getattr(registration, field) is not None:
            messages.error(request, f"{OVERRIDE_FIELDS[field]} has already been recorded for this rider.")
        else:
            services.admin_override_journey(registration, field, reason, request.user)
            messages.success(request, f"{OVERRIDE_FIELDS[field]} marked manually and logged to the audit trail.")

    return redirect("admin_panel:ride-status", ride_id=ride_id)


@staff_member_required
def audit_log_view(request):
    logs = AuditLog.objects.select_related("ride", "rider", "changed_by")[:300]
    return render(request, "admin_panel/audit_log.html", {"logs": logs, "active_nav": "audit"})
