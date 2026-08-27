"""
Business logic for rider login. Kept out of views so the rules are
unit-testable in isolation.

Note: OTP verification was intentionally removed at the project owner's
request - logging in only requires the email to match an active Rider
record. There is no proof the caller actually owns that email address.
"""

from django.conf import settings

from riders.models import Rider


class LoginError(Exception):
    user_message = "Something went wrong. Please try again."


class RiderNotFoundError(LoginError):
    user_message = "This email is not registered. Please contact the ride administrator."


def normalize_email(email):
    return (email or "").strip().lower()


def get_active_rider_by_email(email):
    """Returns the active Rider for this email, or None. Never raises."""
    email = normalize_email(email)
    if not email:
        return None
    return Rider.objects.filter(email__iexact=email, is_active=True).first()


def login_rider(request, rider):
    """Establishes a server-side Django session for the logged-in rider."""
    request.session.flush()  # prevent session fixation
    request.session["rider_id"] = rider.id
    request.session["rider_email"] = rider.email
    request.session.set_expiry(settings.SESSION_COOKIE_AGE)


def logout_rider(request):
    request.session.flush()
