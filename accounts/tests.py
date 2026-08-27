from django.test import TestCase
from django.urls import reverse

from riders.models import Rider

from . import services


def make_rider(**kwargs):
    defaults = dict(name="Arun Kumar", email="arun@example.com", mobile="9876543210", is_active=True)
    defaults.update(kwargs)
    return Rider.objects.create(**defaults)


class GetActiveRiderTests(TestCase):
    def test_registered_active_rider_found(self):
        rider = make_rider()
        self.assertEqual(services.get_active_rider_by_email("ARUN@example.com"), rider)

    def test_unregistered_email_returns_none(self):
        self.assertIsNone(services.get_active_rider_by_email("nobody@example.com"))

    def test_inactive_rider_returns_none(self):
        make_rider(is_active=False)
        self.assertIsNone(services.get_active_rider_by_email("arun@example.com"))


class LoginFlowViewTests(TestCase):
    def test_unregistered_email_shows_error_and_does_not_log_in(self):
        response = self.client.post(reverse("accounts:login"), {"email": "nobody@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("rider_id", self.client.session)

    def test_inactive_rider_cannot_log_in(self):
        make_rider(is_active=False)
        response = self.client.post(reverse("accounts:login"), {"email": "arun@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("rider_id", self.client.session)

    def test_registered_email_logs_in_immediately(self):
        rider = make_rider()
        response = self.client.post(reverse("accounts:login"), {"email": rider.email})
        self.assertRedirects(response, reverse("riders:dashboard"))
        self.assertEqual(self.client.session["rider_id"], rider.id)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("riders:dashboard"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_logout_clears_session(self):
        rider = make_rider()
        self.client.post(reverse("accounts:login"), {"email": rider.email})
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("rider_id", self.client.session)
