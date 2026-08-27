"""
Export helpers. Every export re-reads from the database via
rides.services.rider_report_rows - never from values passed in from the
frontend - so exported files always match what's actually stored.
"""

import csv

from django.http import HttpResponse
from django.utils import timezone

HEADERS = ["Rider", "Email", "Mobile", "Starting Point", "Destination", "Home", "Final Status"]


def _row_values(row):
    def fmt(dt):
        return timezone.localtime(dt).strftime("%d-%m-%Y %I:%M %p") if dt else "Pending"

    return [
        row["rider"].name,
        row["rider"].email,
        row["rider"].mobile,
        fmt(row["starting_point_reached_at"]),
        fmt(row["destination_reached_at"]),
        fmt(row["home_reached_at"]),
        row["final_status"],
    ]


def export_csv(ride, rows):
    response = HttpResponse(content_type="text/csv")
    filename = f"{ride.name}-report.csv".replace(" ", "_")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([f"Ride Report: {ride.name}"])
    writer.writerow([f"Start: {ride.start_date:%d-%m-%Y}  End: {ride.end_date:%d-%m-%Y}"])
    writer.writerow([])
    writer.writerow(HEADERS)
    for row in rows:
        writer.writerow(_row_values(row))
    return response


def export_excel(ride, rows):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Ride Report"

    ws.append([f"Ride Report: {ride.name}"])
    ws.append([f"Start: {ride.start_date:%d-%m-%Y}  End: {ride.end_date:%d-%m-%Y}"])
    ws.append([])
    ws.append(HEADERS)
    for cell in ws[4]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(_row_values(row))

    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = max(length + 2, 12)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    filename = f"{ride.name}-report.xlsx".replace(" ", "_")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def export_pdf(ride, rows, summary):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet

    response = HttpResponse(content_type="application/pdf")
    filename = f"{ride.name}-report.pdf".replace(" ", "_")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response, pagesize=landscape(A4), topMargin=20 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Ride Report: {ride.name}", styles["Title"]),
        Paragraph(
            f"Start: {ride.start_date:%d-%m-%Y} | End: {ride.end_date:%d-%m-%Y} | "
            f"Route: {ride.start_location} -> {ride.destination}",
            styles["Normal"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            f"Total Riders: {summary['total_riders']} | Approved: {summary['approved']} | "
            f"Starting Point: {summary['starting_point_reached']} | Destination: {summary['destination_reached']} | "
            f"Home Confirmed: {summary['home_confirmed']}",
            styles["Normal"],
        ),
        Spacer(1, 8 * mm),
    ]

    table_data = [HEADERS] + [_row_values(row) for row in rows]
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1c1c1c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f0")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return response
