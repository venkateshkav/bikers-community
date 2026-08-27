"""
Bulk rider import from CSV. Reuses RiderForm for validation so an imported
row is held to exactly the same rules (email format, mobile format,
uniqueness) as a rider created one at a time through the UI.
"""

import csv
import io

from .forms import RiderForm

REQUIRED_COLUMNS = {"name", "email", "mobile"}


def import_riders_from_csv(csv_file):
    """
    Returns {"created": [...], "skipped": [(row_number, reason), ...]}.
    `created` holds the created Rider names; `skipped` explains every row
    that was not imported, including the header row's 1-based line number
    (line 1 is the header, so data rows start at line 2).
    """
    decoded = csv_file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    created, skipped = [], []

    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset({f.strip().lower() for f in reader.fieldnames}):
        skipped.append((1, f"CSV must have these columns: {', '.join(sorted(REQUIRED_COLUMNS))}"))
        return {"created": created, "skipped": skipped}

    for line_number, row in enumerate(reader, start=2):
        normalized = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        form = RiderForm(
            data={
                "name": normalized.get("name", ""),
                "email": normalized.get("email", ""),
                "mobile": normalized.get("mobile", ""),
                "is_active": "on",
            }
        )
        if form.is_valid():
            rider = form.save()
            created.append(rider.name)
        else:
            reasons = "; ".join(f"{field}: {err}" for field, errs in form.errors.items() for err in errs)
            skipped.append((line_number, reasons or "Invalid row"))

    return {"created": created, "skipped": skipped}
