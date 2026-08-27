import datetime

from django.test import TestCase
from django.utils import timezone

from riders.models import Rider
from rides import services
from rides.models import Ride, RideRegistration


def make_ride():
    return Ride.objects.create(
        name="Pondicherry Weekend Ride",
        start_date=datetime.date(2026, 8, 30),
        start_time=datetime.time(5, 30),
        end_date=datetime.date(2026, 8, 30),
        end_time=datetime.time(20, 0),
        start_location="OMR Toll Gate",
        destination="Pondicherry Beach",
        status=Ride.Status.ONGOING,
    )


def make_rider(i):
    return Rider.objects.create(name=f"Rider {i}", email=f"rider{i}@example.com", mobile=f"90000000{i:02d}")


class RideSummaryTests(TestCase):
    def setUp(self):
        self.ride = make_ride()
        self.riders = [make_rider(i) for i in range(4)]
        # 0: fully completed, 1: destination reached, 2: starting point only, 3: not started
        for i, rider in enumerate(self.riders):
            reg = RideRegistration.objects.create(ride=self.ride, rider=rider, status=RideRegistration.Status.APPROVED)
            if i <= 2:
                reg.starting_point_reached_at = timezone.now()
            if i <= 1:
                reg.destination_reached_at = timezone.now()
            if i == 0:
                reg.home_reached_at = timezone.now()
            reg.save()
        # A pending (not approved) registration should not count toward "approved".
        RideRegistration.objects.create(ride=self.ride, rider=make_rider(4), status=RideRegistration.Status.PENDING)

    def test_summary_counts(self):
        summary = services.ride_summary(self.ride)
        self.assertEqual(summary["total_riders"], 5)
        self.assertEqual(summary["approved"], 4)
        self.assertEqual(summary["starting_point_reached"], 3)
        self.assertEqual(summary["destination_reached"], 2)
        self.assertEqual(summary["home_confirmed"], 1)
        self.assertEqual(summary["starting_point_pending"], 1)
        self.assertEqual(summary["destination_pending"], 1)
        self.assertEqual(summary["home_confirmation_pending"], 1)

    def test_rider_report_rows_excludes_unapproved(self):
        rows = services.rider_report_rows(self.ride)
        self.assertEqual(len(rows), 4)

    def test_rider_report_rows_status_filter(self):
        rows = services.rider_report_rows(self.ride, status_filter="Home Pending")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rider"].name, "Rider 1")

    def test_rider_report_rows_not_started_filter(self):
        rows = services.rider_report_rows(self.ride, status_filter="Not Started")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rider"].name, "Rider 3")
