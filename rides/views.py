from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.decorators import rider_login_required

from . import services
from .models import RideRegistration


@rider_login_required
def my_rides_view(request):
    registrations = (
        RideRegistration.objects.select_related("ride")
        .filter(rider=request.rider, status=RideRegistration.Status.APPROVED)
        .order_by("-ride__start_date")
    )
    return render(request, "rider/my_rides.html", {"registrations": registrations})


@rider_login_required
def ride_detail_view(request, ride_id):
    try:
        registration = services.get_approved_registration(request.rider, ride_id)
    except services.RideAccessDeniedError as exc:
        messages.error(request, exc.user_message)
        return redirect("riders:dashboard")

    return render(request, "rider/ride_detail.html", {"registration": registration, "ride": registration.ride})


def _do_action(request, ride_id, action_fn):
    try:
        registration = services.get_approved_registration(request.rider, ride_id)
        action_fn(registration)
    except services.RideActionError as exc:
        messages.error(request, exc.user_message)
    else:
        messages.success(request, "Updated successfully.")
    return redirect("rides:ride-detail", ride_id=ride_id)


@rider_login_required
@require_http_methods(["POST"])
def starting_point_action(request, ride_id):
    return _do_action(request, ride_id, services.mark_starting_point)


@rider_login_required
@require_http_methods(["POST"])
def destination_action(request, ride_id):
    return _do_action(request, ride_id, services.mark_destination)


@rider_login_required
@require_http_methods(["GET", "POST"])
def home_confirmation_action(request, ride_id):
    try:
        registration = services.get_approved_registration(request.rider, ride_id)
    except services.RideAccessDeniedError as exc:
        messages.error(request, exc.user_message)
        return redirect("riders:dashboard")

    if request.method == "POST":
        return _do_action(request, ride_id, services.mark_home_confirmation)

    return render(request, "rider/home_confirmation_confirm.html", {"registration": registration, "ride": registration.ride})
