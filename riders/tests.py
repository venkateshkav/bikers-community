from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Rider


class RiderModelTests(TestCase):
    def test_email_is_normalized_to_lowercase(self):
        rider = Rider.objects.create(name="Arun", email="Arun@Example.com", mobile="9876543210")
        self.assertEqual(rider.email, "arun@example.com")

    def test_email_uniqueness_is_case_insensitive(self):
        Rider.objects.create(name="Arun", email="arun@example.com", mobile="9876543210")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Rider.objects.create(name="Someone Else", email="ARUN@EXAMPLE.COM", mobile="9876500000")

    def test_deactivated_rider_cannot_log_in(self):
        rider = Rider.objects.create(name="Arun", email="arun@example.com", mobile="9876543210", is_active=False)
        from accounts.services import get_active_rider_by_email

        self.assertIsNone(get_active_rider_by_email(rider.email))


class RiderAdminCrudViewTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="admin", password="pw", is_staff=True)
        self.client.force_login(self.staff)

    def test_non_staff_cannot_access_rider_list(self):
        self.client.logout()
        response = self.client.get(reverse("riders_admin:list"))
        self.assertNotEqual(response.status_code, 200)

    def test_create_rider(self):
        response = self.client.post(
            reverse("riders_admin:create"),
            {"name": "Kumar", "email": "kumar@example.com", "mobile": "9111111111", "is_active": "on"},
        )
        self.assertRedirects(response, reverse("riders_admin:list"))
        self.assertTrue(Rider.objects.filter(email="kumar@example.com").exists())

    def test_edit_rider(self):
        rider = Rider.objects.create(name="Kumar", email="kumar@example.com", mobile="9111111111")
        response = self.client.post(
            reverse("riders_admin:edit", args=[rider.id]),
            {"name": "Kumar S", "email": rider.email, "mobile": rider.mobile, "is_active": "on"},
        )
        self.assertRedirects(response, reverse("riders_admin:list"))
        rider.refresh_from_db()
        self.assertEqual(rider.name, "Kumar S")

    def test_toggle_active(self):
        rider = Rider.objects.create(name="Kumar", email="kumar@example.com", mobile="9111111111", is_active=True)
        self.client.post(reverse("riders_admin:toggle-active", args=[rider.id]))
        rider.refresh_from_db()
        self.assertFalse(rider.is_active)
