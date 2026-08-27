from django.shortcuts import render

from accounts.decorators import rider_login_required
from rides.models import Ride, RideRegistration


@rider_login_required
def dashboard_view(request):
    rider = request.rider

    active_registration = (
        RideRegistration.objects.select_related("ride")
        .filter(
            rider=rider,
            status=RideRegistration.Status.APPROVED,
            ride__status__in=[Ride.Status.UPCOMING, Ride.Status.ONGOING],
        )
        .order_by("ride__start_date", "ride__start_time")
        .first()
    )

    recent_registrations = (
        RideRegistration.objects.select_related("ride")
        .filter(rider=rider, status=RideRegistration.Status.APPROVED)
        .exclude(pk=active_registration.pk if active_registration else None)
        .order_by("-ride__start_date")[:5]
    )

    return render(
        request,
        "rider/dashboard.html",
        {
            "active_registration": active_registration,
            "recent_registrations": recent_registrations,
        },
    )
