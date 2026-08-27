import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from riders.models import Rider

from . import services
from .models import AuditLog, Ride, RideRegistration


def make_rider(name="Arun Kumar", email="arun@example.com", mobile="9876543210"):
    return Rider.objects.create(name=name, email=email, mobile=mobile, is_active=True)


def make_ride(**kwargs):
    defaults = dict(
        name="Pondicherry Weekend Ride",
        start_date=datetime.date(2026, 8, 30),
        start_time=datetime.time(5, 30),
        end_date=datetime.date(2026, 8, 30),
        end_time=datetime.time(20, 0),
        start_location="OMR Toll Gate",
        destination="Pondicherry Beach",
        status=Ride.Status.ONGOING,
    )
    defaults.update(kwargs)
    return Ride.objects.create(**defaults)


def register(ride, rider, status=RideRegistration.Status.APPROVED):
    return RideRegistration.objects.create(ride=ride, rider=rider, status=status)


class RideAccessTests(TestCase):
    def setUp(self):
        self.ride = make_ride()
        self.rider = make_rider()

    def test_approved_rider_gets_registration(self):
        reg = register(self.ride, self.rider, RideRegistration.Status.APPROVED)
        result = services.get_approved_registration(self.rider, self.ride.id)
        self.assertEqual(result.pk, reg.pk)

    def test_pending_rider_denied(self):
        register(self.ride, self.rider, RideRegistration.Status.PENDING)
        with self.assertRaises(services.RideAccessDeniedError):
            services.get_approved_registration(self.rider, self.ride.id)

    def test_rejected_rider_denied(self):
        register(self.ride, self.rider, RideRegistration.Status.REJECTED)
        with self.assertRaises(services.RideAccessDeniedError):
            services.get_approved_registration(self.rider, self.ride.id)

    def test_cancelled_rider_denied(self):
        register(self.ride, self.rider, RideRegistration.Status.CANCELLED)
        with self.assertRaises(services.RideAccessDeniedError):
            services.get_approved_registration(self.rider, self.ride.id)

    def test_unregistered_rider_denied(self):
        with self.assertRaises(services.RideAccessDeniedError):
            services.get_approved_registration(self.rider, self.ride.id)


class JourneyTransitionTests(TestCase):
    def setUp(self):
        self.ride = make_ride()
        self.rider = make_rider()
        self.registration = register(self.ride, self.rider)

    def test_mark_starting_point_success(self):
        reg = services.mark_starting_point(self.registration)
        self.assertIsNotNone(reg.starting_point_reached_at)

    def test_duplicate_starting_point_blocked(self):
        services.mark_starting_point(self.registration)
        with self.assertRaises(services.AlreadyCompletedError):
            services.mark_starting_point(self.registration)

    def test_destination_before_starting_point_blocked(self):
        with self.assertRaises(services.InvalidTransitionError):
            services.mark_destination(self.registration)

    def test_destination_after_starting_point_succeeds(self):
        services.mark_starting_point(self.registration)
        reg = services.mark_destination(self.registration)
        self.assertIsNotNone(reg.destination_reached_at)

    def test_duplicate_destination_blocked(self):
        services.mark_starting_point(self.registration)
        services.mark_destination(self.registration)
        with self.assertRaises(services.AlreadyCompletedError):
            services.mark_destination(self.registration)

    def test_home_before_destination_blocked(self):
        services.mark_starting_point(self.registration)
        with self.assertRaises(services.InvalidTransitionError):
            services.mark_home_confirmation(self.registration)

    def test_home_after_destination_succeeds_and_completes_ride(self):
        services.mark_starting_point(self.registration)
        services.mark_destination(self.registration)
        reg = services.mark_home_confirmation(self.registration)
        self.assertIsNotNone(reg.home_reached_at)
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, Ride.Status.COMPLETED)

    def test_duplicate_home_confirmation_blocked(self):
        services.mark_starting_point(self.registration)
        services.mark_destination(self.registration)
        services.mark_home_confirmation(self.registration)
        with self.assertRaises(services.AlreadyCompletedError):
            services.mark_home_confirmation(self.registration)


class RideStatusGatingTests(TestCase):
    """A ride's status must gate rider actions, not just approval + step order."""

    def setUp(self):
        self.rider = make_rider()

    def test_draft_ride_blocks_starting_point(self):
        ride = make_ride(status=Ride.Status.DRAFT)
        registration = register(ride, self.rider)
        with self.assertRaises(services.InvalidTransitionError):
            services.mark_starting_point(registration)

    def test_upcoming_ride_allows_starting_point_and_promotes_to_ongoing(self):
        ride = make_ride(status=Ride.Status.UPCOMING)
        registration = register(ride, self.rider)
        services.mark_starting_point(registration)
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.ONGOING)

    def test_cancelled_ride_blocks_starting_point(self):
        ride = make_ride(status=Ride.Status.CANCELLED)
        registration = register(ride, self.rider)
        with self.assertRaises(services.InvalidTransitionError):
            services.mark_starting_point(registration)

    def test_cancelled_ride_blocks_home_confirmation_even_after_destination(self):
        ride = make_ride(status=Ride.Status.ONGOING)
        registration = register(ride, self.rider)
        services.mark_starting_point(registration)
        services.mark_destination(registration)
        ride.status = Ride.Status.CANCELLED
        ride.save(update_fields=["status"])
        with self.assertRaises(services.InvalidTransitionError):
            services.mark_home_confirmation(registration)


class RiderActionViewTests(TestCase):
    def setUp(self):
        self.ride = make_ride()
        self.rider = make_rider()
        self.other_rider = make_rider(name="Bala", email="bala@example.com", mobile="9876500000")
        self.registration = register(self.ride, self.rider)
        register(self.ride, self.other_rider)

    def _login(self, rider):
        session = self.client.session
        session["rider_id"] = rider.id
        session.save()

    def test_unauthenticated_request_redirects_to_login(self):
        response = self.client.post(reverse("rides:starting-point", args=[self.ride.id]))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_unapproved_rider_cannot_act(self):
        pending_rider = make_rider(name="Kumar", email="kumar@example.com", mobile="9111111111")
        register(self.ride, pending_rider, RideRegistration.Status.PENDING)
        self._login(pending_rider)
        response = self.client.post(reverse("rides:starting-point", args=[self.ride.id]), follow=True)
        self.assertContains(response, "not approved")

    def test_wrong_rider_cannot_modify_others_registration(self):
        """A rider changing the URL's ride id must never touch another rider's own registration state."""
        self._login(self.other_rider)
        self.client.post(reverse("rides:starting-point", args=[self.ride.id]))

        self.registration.refresh_from_db()
        self.assertIsNone(self.registration.starting_point_reached_at)

    def test_valid_starting_point_action(self):
        self._login(self.rider)
        self.client.post(reverse("rides:starting-point", args=[self.ride.id]))
        self.registration.refresh_from_db()
        self.assertIsNotNone(self.registration.starting_point_reached_at)

    def test_duplicate_action_shows_message(self):
        self._login(self.rider)
        self.client.post(reverse("rides:starting-point", args=[self.ride.id]))
        response = self.client.post(reverse("rides:starting-point", args=[self.ride.id]), follow=True)
        self.assertContains(response, "already been completed")


class RideAdminCrudViewTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="admin", password="pw", is_staff=True)
        self.client.force_login(self.staff)

    def test_non_staff_cannot_access_ride_list(self):
        self.client.logout()
        response = self.client.get(reverse("admin_panel:ride-list"))
        self.assertNotEqual(response.status_code, 200)

    def test_create_ride_sets_created_by(self):
        response = self.client.post(
            reverse("admin_panel:ride-create"),
            {
                "name": "Yercaud Ride",
                "start_date": "2026-09-15",
                "start_time": "06:00",
                "end_date": "2026-09-15",
                "end_time": "20:00",
                "start_location": "Salem",
                "destination": "Yercaud",
                "status": Ride.Status.UPCOMING,
            },
        )
        ride = Ride.objects.get(name="Yercaud Ride")
        self.assertRedirects(response, reverse("admin_panel:ride-status", args=[ride.id]))
        self.assertEqual(ride.created_by, self.staff)

    def test_edit_ride(self):
        ride = make_ride()
        response = self.client.post(
            reverse("admin_panel:ride-edit", args=[ride.id]),
            {
                "name": "Pondicherry Weekend Ride (Updated)",
                "start_date": ride.start_date,
                "start_time": "05:30",
                "end_date": ride.end_date,
                "end_time": ride.end_time,
                "start_location": ride.start_location,
                "destination": ride.destination,
                "status": ride.status,
            },
        )
        self.assertRedirects(response, reverse("admin_panel:ride-status", args=[ride.id]))
        ride.refresh_from_db()
        self.assertEqual(ride.name, "Pondicherry Weekend Ride (Updated)")

    def test_cancel_ride(self):
        ride = make_ride()
        self.client.post(reverse("admin_panel:ride-cancel", args=[ride.id]))
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.CANCELLED)


class RegistrationManagementViewTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="admin", password="pw", is_staff=True)
        self.client.force_login(self.staff)
        self.ride = make_ride()
        self.rider = make_rider()

    def test_add_rider_with_auto_approve(self):
        response = self.client.post(
            reverse("admin_panel:registration-add", args=[self.ride.id]),
            {"riders": [self.rider.id], "auto_approve": "on"},
        )
        self.assertRedirects(response, reverse("admin_panel:ride-status", args=[self.ride.id]))
        reg = RideRegistration.objects.get(ride=self.ride, rider=self.rider)
        self.assertEqual(reg.status, RideRegistration.Status.APPROVED)

    def test_add_rider_without_auto_approve_stays_pending(self):
        self.client.post(reverse("admin_panel:registration-add", args=[self.ride.id]), {"riders": [self.rider.id]})
        reg = RideRegistration.objects.get(ride=self.ride, rider=self.rider)
        self.assertEqual(reg.status, RideRegistration.Status.PENDING)

    def test_add_multiple_riders_at_once(self):
        other_rider = make_rider(name="Bala", email="bala2@example.com", mobile="9876511111")
        self.client.post(
            reverse("admin_panel:registration-add", args=[self.ride.id]),
            {"riders": [self.rider.id, other_rider.id], "auto_approve": "on"},
        )
        self.assertEqual(
            RideRegistration.objects.filter(
                ride=self.ride, rider__in=[self.rider, other_rider], status=RideRegistration.Status.APPROVED
            ).count(),
            2,
        )

    def test_approve_pending_registration(self):
        reg = register(self.ride, self.rider, RideRegistration.Status.PENDING)
        self.client.post(reverse("admin_panel:registration-approve", args=[self.ride.id, reg.id]))
        reg.refresh_from_db()
        self.assertEqual(reg.status, RideRegistration.Status.APPROVED)
        self.assertTrue(AuditLog.objects.filter(action="registration_approved").exists())

    def test_reject_pending_registration(self):
        reg = register(self.ride, self.rider, RideRegistration.Status.PENDING)
        self.client.post(reverse("admin_panel:registration-reject", args=[self.ride.id, reg.id]))
        reg.refresh_from_db()
        self.assertEqual(reg.status, RideRegistration.Status.REJECTED)

    def test_cancel_approved_registration(self):
        reg = register(self.ride, self.rider, RideRegistration.Status.APPROVED)
        self.client.post(reverse("admin_panel:registration-cancel", args=[self.ride.id, reg.id]))
        reg.refresh_from_db()
        self.assertEqual(reg.status, RideRegistration.Status.CANCELLED)

    def test_can_re_add_a_previously_rejected_rider(self):
        reg = register(self.ride, self.rider, RideRegistration.Status.REJECTED)
        self.client.post(
            reverse("admin_panel:registration-add", args=[self.ride.id]),
            {"riders": [self.rider.id], "auto_approve": "on"},
        )
        reg.refresh_from_db()
        self.assertEqual(reg.status, RideRegistration.Status.APPROVED)
        self.assertEqual(RideRegistration.objects.filter(ride=self.ride, rider=self.rider).count(), 1)
