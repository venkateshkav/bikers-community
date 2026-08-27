from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render

from rides import services
from rides.models import Ride

from . import exports

STATUS_CHOICES = ["Not Started", "Destination Pending", "Home Pending", "Completed"]


@staff_member_required
def report_list_view(request):
    rides = Ride.objects.exclude(status=Ride.Status.DRAFT).order_by("-ride_date")

    ride_date = request.GET.get("date", "").strip()
    status = request.GET.get("status", "").strip()
    name = request.GET.get("name", "").strip()

    if ride_date:
        rides = rides.filter(ride_date=ride_date)
    if status:
        rides = rides.filter(status=status)
    if name:
        rides = rides.filter(name__icontains=name)

    return render(
        request,
        "admin_panel/report_list.html",
        {
            "rides": rides,
            "ride_status_choices": Ride.Status.choices,
            "filters": {"date": ride_date, "status": status, "name": name},
            "active_nav": "reports",
        },
    )


def _filtered_rows(ride, request):
    status_filter = request.GET.get("status", "").strip() or None
    rider_query = request.GET.get("rider", "").strip()
    rows = services.rider_report_rows(ride, status_filter=status_filter)
    if rider_query:
        q = rider_query.lower()
        rows = [r for r in rows if q in r["rider"].name.lower() or q in r["rider"].email.lower()]
    return rows


@staff_member_required
def ride_report_view(request, ride_id):
    ride = get_object_or_404(Ride, pk=ride_id)
    summary = services.ride_summary(ride)
    rows = _filtered_rows(ride, request)

    return render(
        request,
        "admin_panel/ride_report.html",
        {
            "ride": ride,
            "summary": summary,
            "rows": rows,
            "status_choices": STATUS_CHOICES,
            "filters": {
                "status": request.GET.get("status", ""),
                "rider": request.GET.get("rider", ""),
            },
            "active_nav": "reports",
        },
    )


@staff_member_required
def export_csv_view(request, ride_id):
    ride = get_object_or_404(Ride, pk=ride_id)
    rows = _filtered_rows(ride, request)
    return exports.export_csv(ride, rows)


@staff_member_required
def export_excel_view(request, ride_id):
    ride = get_object_or_404(Ride, pk=ride_id)
    rows = _filtered_rows(ride, request)
    return exports.export_excel(ride, rows)


@staff_member_required
def export_pdf_view(request, ride_id):
    ride = get_object_or_404(Ride, pk=ride_id)
    rows = _filtered_rows(ride, request)
    summary = services.ride_summary(ride)
    return exports.export_pdf(ride, rows, summary)
