"""
Ride access control and journey-state transitions. All rider-facing actions
must go through these functions - never trust a frontend button state.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import AuditLog, Ride, RideRegistration


class RideActionError(Exception):
    user_message = "This action could not be completed."


class RideAccessDeniedError(RideActionError):
    user_message = "You are not approved for this ride. Please contact the ride administrator."


class InvalidTransitionError(RideActionError):
    def __init__(self, message):
        self.user_message = message


class AlreadyCompletedError(RideActionError):
    user_message = "This step has already been completed."


def get_approved_registration(rider, ride_id):
    """
    Full authorization chain for a rider acting on a ride:
    authenticated (checked by the caller/decorator) -> rider active
    -> ride exists -> registration exists -> registration approved.
    Raises RideAccessDeniedError otherwise. Never leaks whether the ride
    exists to an unauthorized rider - same error either way.
    """
    ride = get_object_or_404(Ride, pk=ride_id)
    registration = RideRegistration.objects.select_related("ride", "rider").filter(ride=ride, rider=rider).first()
    if registration is None or registration.status != RideRegistration.Status.APPROVED:
        raise RideAccessDeniedError()
    return registration


def _assert_ride_is_open(ride):
    if ride.status == Ride.Status.DRAFT:
        raise InvalidTransitionError("This ride has not been published yet.")
    if ride.is_locked():
        raise InvalidTransitionError("This ride is no longer active.")


@transaction.atomic
def mark_starting_point(registration):
    registration = RideRegistration.objects.select_for_update().get(pk=registration.pk)
    if registration.status != RideRegistration.Status.APPROVED:
        raise RideAccessDeniedError()
    if registration.starting_point_reached_at is not None:
        raise AlreadyCompletedError()
    ride = registration.ride
    _assert_ride_is_open(ride)

    registration.starting_point_reached_at = timezone.now()
    registration.save(update_fields=["starting_point_reached_at"])

    if ride.status == Ride.Status.UPCOMING:
        # The first rider checking in is what actually starts the ride.
        ride.status = Ride.Status.ONGOING
        ride.save(update_fields=["status"])

    return registration


@transaction.atomic
def mark_destination(registration):
    registration = RideRegistration.objects.select_for_update().get(pk=registration.pk)
    if registration.status != RideRegistration.Status.APPROVED:
        raise RideAccessDeniedError()
    if registration.destination_reached_at is not None:
        raise AlreadyCompletedError()
    _assert_ride_is_open(registration.ride)
    if registration.starting_point_reached_at is None:
        raise InvalidTransitionError("Please complete Starting Point before marking Destination.")

    registration.destination_reached_at = timezone.now()
    registration.save(update_fields=["destination_reached_at"])
    return registration


@transaction.atomic
def mark_home_confirmation(registration):
    registration = RideRegistration.objects.select_for_update().get(pk=registration.pk)
    if registration.status != RideRegistration.Status.APPROVED:
        raise RideAccessDeniedError()
    if registration.home_reached_at is not None:
        raise AlreadyCompletedError()
    ride = registration.ride
    _assert_ride_is_open(ride)
    if registration.destination_reached_at is None:
        raise InvalidTransitionError("Please complete Destination before marking Home Confirmation.")

    registration.home_reached_at = timezone.now()
    registration.save(update_fields=["home_reached_at"])

    total_approved = ride.registrations.filter(status=RideRegistration.Status.APPROVED).count()
    total_home = ride.registrations.filter(home_reached_at__isnull=False).count()
    if total_approved and total_approved == total_home and ride.status == Ride.Status.ONGOING:
        ride.status = Ride.Status.COMPLETED
        ride.save(update_fields=["status"])

    return registration


@transaction.atomic
def admin_override_journey(registration, field, reason, changed_by):
    """
    Admin manual override of a single journey timestamp field. Every change
    is written to AuditLog with the old/new value and the reason given.
    `field` must be one of starting_point_reached_at / destination_reached_at
    / home_reached_at.
    """
    if field not in ("starting_point_reached_at", "destination_reached_at", "home_reached_at"):
        raise ValueError(f"Unsupported journey field: {field}")

    registration = RideRegistration.objects.select_for_update().get(pk=registration.pk)
    old_value = getattr(registration, field)
    new_value = timezone.now()
    setattr(registration, field, new_value)
    registration.save(update_fields=[field])

    AuditLog.objects.create(
        ride=registration.ride,
        rider=registration.rider,
        action=f"manual_override:{field}",
        old_value=str(old_value) if old_value else "",
        new_value=str(new_value),
        reason=reason,
        changed_by=changed_by,
    )
    return registration


@transaction.atomic
def approve_registration(registration, changed_by, reason=""):
    old_status = registration.status
    registration.status = RideRegistration.Status.APPROVED
    registration.approved_at = timezone.now()
    registration.save(update_fields=["status", "approved_at"])
    AuditLog.objects.create(
        ride=registration.ride,
        rider=registration.rider,
        action="registration_approved",
        old_value=old_status,
        new_value=registration.status,
        reason=reason,
        changed_by=changed_by,
    )
    return registration


def ride_summary(ride):
    """Aggregate checkpoint counts for a ride - the basis of every dashboard card and report."""
    regs = list(ride.registrations.all())
    total = len(regs)
    approved = sum(1 for r in regs if r.status == RideRegistration.Status.APPROVED)
    starting = sum(1 for r in regs if r.starting_point_reached_at)
    destination = sum(1 for r in regs if r.destination_reached_at)
    home = sum(1 for r in regs if r.home_reached_at)
    return {
        "ride": ride,
        "total_riders": total,
        "approved": approved,
        "starting_point_reached": starting,
        "destination_reached": destination,
        "home_confirmed": home,
        "starting_point_pending": max(approved - starting, 0),
        "destination_pending": max(starting - destination, 0),
        "home_confirmation_pending": max(destination - home, 0),
    }


def rider_report_rows(ride, status_filter=None):
    """
    Rider-wise report rows for a ride: name, email, mobile, checkpoint times,
    final status. `status_filter` (if given) matches RideRegistration.journey_status
    (e.g. "Home Pending") so admins can filter to exactly who is still pending.
    """
    registrations = (
        ride.registrations.select_related("rider")
        .filter(status=RideRegistration.Status.APPROVED)
        .order_by("rider__name")
    )
    rows = []
    for reg in registrations:
        if status_filter and reg.journey_status != status_filter:
            continue
        rows.append(
            {
                "rider": reg.rider,
                "starting_point_reached_at": reg.starting_point_reached_at,
                "destination_reached_at": reg.destination_reached_at,
                "home_reached_at": reg.home_reached_at,
                "final_status": reg.journey_status,
            }
        )
    return rows


@transaction.atomic
def reject_registration(registration, changed_by, reason=""):
    old_status = registration.status
    registration.status = RideRegistration.Status.REJECTED
    registration.rejected_at = timezone.now()
    registration.save(update_fields=["status", "rejected_at"])
    AuditLog.objects.create(
        ride=registration.ride,
        rider=registration.rider,
        action="registration_rejected",
        old_value=old_status,
        new_value=registration.status,
        reason=reason,
        changed_by=changed_by,
    )
    return registration


@transaction.atomic
def cancel_registration(registration, changed_by, reason=""):
    old_status = registration.status
    registration.status = RideRegistration.Status.CANCELLED
    registration.cancelled_at = timezone.now()
    registration.save(update_fields=["status", "cancelled_at"])
    AuditLog.objects.create(
        ride=registration.ride,
        rider=registration.rider,
        action="registration_cancelled",
        old_value=old_status,
        new_value=registration.status,
        reason=reason,
        changed_by=changed_by,
    )
    return registration
