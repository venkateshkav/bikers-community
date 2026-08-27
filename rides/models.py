from django.conf import settings
from django.db import models


class Ride(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        UPCOMING = "UPCOMING", "Upcoming"
        ONGOING = "ONGOING", "Ongoing"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    name = models.CharField(max_length=200)
    ride_date = models.DateField()
    start_location = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    start_time = models.TimeField()
    expected_arrival_time = models.TimeField(null=True, blank=True)
    expected_return_time = models.TimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="rides_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ride_date", "-start_time"]
        indexes = [models.Index(fields=["ride_date", "status"])]

    def __str__(self):
        return f"{self.name} ({self.ride_date:%d-%m-%Y})"

    def is_locked(self):
        """Cancelled/completed rides can no longer accept new journey actions."""
        return self.status in (self.Status.CANCELLED, self.Status.COMPLETED)


class RideRegistration(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="registrations")
    rider = models.ForeignKey("riders.Rider", on_delete=models.CASCADE, related_name="registrations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    registered_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    starting_point_reached_at = models.DateTimeField(null=True, blank=True)
    destination_reached_at = models.DateTimeField(null=True, blank=True)
    home_reached_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["ride", "rider__name"]
        constraints = [
            models.UniqueConstraint(fields=["ride", "rider"], name="unique_ride_rider"),
        ]
        indexes = [
            models.Index(fields=["ride", "status"]),
        ]

    def __str__(self):
        return f"{self.rider} - {self.ride} ({self.status})"

    @property
    def journey_status(self):
        """Human-friendly progress label derived purely from timestamps."""
        if self.status != self.Status.APPROVED and self.home_reached_at is None:
            return self.get_status_display()
        if self.home_reached_at:
            return "Completed"
        if self.destination_reached_at:
            return "Home Pending"
        if self.starting_point_reached_at:
            return "Destination Pending"
        return "Not Started"

    @property
    def is_completed(self):
        return self.home_reached_at is not None


class AuditLog(models.Model):
    """Immutable trail of every manual admin override to journey/status data."""

    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True)
    rider = models.ForeignKey(
        "riders.Rider", on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True
    )
    action = models.CharField(max_length=100)
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on {self.rider} / {self.ride} at {self.created_at:%Y-%m-%d %H:%M}"
