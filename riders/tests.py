from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from . import services
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


def make_csv(content):
    return SimpleUploadedFile("riders.csv", content.encode("utf-8"), content_type="text/csv")


class RiderCsvImportServiceTests(TestCase):
    def test_valid_rows_are_created(self):
        csv_content = "name,email,mobile\nArun Kumar,arun@example.com,9876543210\nBala,bala@example.com,9876500000\n"
        result = services.import_riders_from_csv(make_csv(csv_content))
        self.assertEqual(len(result["created"]), 2)
        self.assertEqual(len(result["skipped"]), 0)
        self.assertTrue(Rider.objects.filter(email="arun@example.com").exists())

    def test_duplicate_email_is_skipped(self):
        Rider.objects.create(name="Arun", email="arun@example.com", mobile="9876543210")
        csv_content = "name,email,mobile\nArun Again,arun@example.com,9876543211\n"
        result = services.import_riders_from_csv(make_csv(csv_content))
        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(result["skipped"][0][0], 2)

    def test_invalid_mobile_is_skipped(self):
        csv_content = "name,email,mobile\nArun,arun@example.com,abc\n"
        result = services.import_riders_from_csv(make_csv(csv_content))
        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(len(result["skipped"]), 1)

    def test_missing_required_column_reports_error(self):
        csv_content = "name,mobile\nArun,9876543210\n"
        result = services.import_riders_from_csv(make_csv(csv_content))
        self.assertEqual(len(result["created"]), 0)
        self.assertEqual(len(result["skipped"]), 1)

    def test_two_rows_with_same_new_email_only_first_created(self):
        csv_content = "name,email,mobile\nArun,arun@example.com,9876543210\nArun Dup,arun@example.com,9876543211\n"
        result = services.import_riders_from_csv(make_csv(csv_content))
        self.assertEqual(len(result["created"]), 1)
        self.assertEqual(len(result["skipped"]), 1)


class RiderImportViewTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username="admin", password="pw", is_staff=True)
        self.client.force_login(self.staff)

    def test_non_staff_cannot_access_import(self):
        self.client.logout()
        response = self.client.get(reverse("riders_admin:import"))
        self.assertNotEqual(response.status_code, 200)

    def test_import_creates_riders(self):
        csv_content = "name,email,mobile\nArun Kumar,arun@example.com,9876543210\n"
        response = self.client.post(
            reverse("riders_admin:import"), {"csv_file": make_csv(csv_content)}, format="multipart"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Rider.objects.filter(email="arun@example.com").exists())

    def test_non_csv_file_rejected(self):
        bad_file = SimpleUploadedFile("riders.txt", b"name,email,mobile", content_type="text/plain")
        response = self.client.post(reverse("riders_admin:import"), {"csv_file": bad_file}, format="multipart")
        self.assertContains(response, "Please upload a .csv file")

    def test_sample_csv_download(self):
        response = self.client.get(reverse("riders_admin:import-sample"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
