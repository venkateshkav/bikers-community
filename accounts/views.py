from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from . import services
from .forms import EmailLoginForm


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.rider is not None:
        return redirect("riders:dashboard")

    form = EmailLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        rider = services.get_active_rider_by_email(email)
        if rider is None:
            messages.error(request, services.RiderNotFoundError.user_message)
        else:
            services.login_rider(request, rider)
            messages.success(request, f"Welcome, {rider.name.split()[0]}!")
            return redirect("riders:dashboard")

    return render(request, "rider/login.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request):
    services.logout_rider(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")
