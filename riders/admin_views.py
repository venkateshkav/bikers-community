"""
Custom, premium-styled CRUD for the Rider master (separate from
django.contrib.admin, which remains available as a fallback).
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import RiderForm
from .models import Rider


@staff_member_required
def rider_list_view(request):
    riders = Rider.objects.all()

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    if q:
        riders = riders.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(mobile__icontains=q))
    if status == "active":
        riders = riders.filter(is_active=True)
    elif status == "inactive":
        riders = riders.filter(is_active=False)

    return render(
        request,
        "admin_panel/rider_list.html",
        {"riders": riders, "filters": {"q": q, "status": status}, "active_nav": "riders"},
    )


@staff_member_required
def rider_create_view(request):
    form = RiderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        rider = form.save()
        messages.success(request, f"{rider.name} added.")
        return redirect("riders_admin:list")

    return render(request, "admin_panel/rider_form.html", {"form": form, "title": "Add Rider", "active_nav": "riders"})


@staff_member_required
def rider_edit_view(request, rider_id):
    rider = get_object_or_404(Rider, pk=rider_id)
    form = RiderForm(request.POST or None, instance=rider)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{rider.name} updated.")
        return redirect("riders_admin:list")

    return render(
        request,
        "admin_panel/rider_form.html",
        {"form": form, "title": "Edit Rider", "rider": rider, "active_nav": "riders"},
    )


@staff_member_required
@require_http_methods(["POST"])
def rider_toggle_active_view(request, rider_id):
    rider = get_object_or_404(Rider, pk=rider_id)
    rider.is_active = not rider.is_active
    rider.save(update_fields=["is_active"])
    messages.success(request, f"{rider.name} is now {'active' if rider.is_active else 'inactive'}.")
    return redirect("riders_admin:list")
