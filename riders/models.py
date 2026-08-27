from django.core.validators import RegexValidator
from django.db import models

mobile_validator = RegexValidator(
    regex=r"^\+?[0-9]{10,15}$",
    message="Enter a valid mobile number (10-15 digits, optional leading +).",
)


class Rider(models.Model):
    """
    Rider master record. Created and managed only by the admin - riders
    never self-register. Keep this model minimal (see project spec):
    no bike model/number, no emergency contact, no profile photo.
    """

    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True, db_index=True)
    mobile = models.CharField(max_length=16, validators=[mobile_validator])
    is_active = models.BooleanField(default=True, help_text="Inactive riders cannot log in.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def save(self, *args, **kwargs):
        # Normalize email so uniqueness/lookups are always case-insensitive,
        # regardless of the database collation in use.
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def masked_email(self):
        """e.g. arun@gmail.com -> a***@gmail.com, used on the OTP screen."""
        try:
            local, domain = self.email.split("@", 1)
        except ValueError:
            return self.email
        visible = local[0] if local else ""
        return f"{visible}***@{domain}"
