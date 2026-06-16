"""
update_tracker.py - Write processed invoices into the Excel tracker.

Finance already lives in Excel, so the system's output is a normal .xlsx the team
can open, filter and sort. If the tracker doesn't exist we create it with headers;
otherwise we append the new run's rows so history accumulates.
"""

from datetime import datetime

import pandas as pd

import config

TRACKER_COLUMNS = [
    "Date Processed",
    "Vendor",
    "Invoice Number",
    "Invoice Date",
    "Invoice Amount",
    "PO Number",
    "PO Amount",
    "Status",
]


def update_tracker(records: list[dict]) -> str:
    """Append validated records to data/invoice_tracker.xlsx. Returns the path."""
    processed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_rows = [
        {
            "Date Processed": processed_at,
            "Vendor": r.get("vendor"),
            "Invoice Number": r.get("invoice_number"),
            "Invoice Date": r.get("invoice_date"),
            "Invoice Amount": r.get("amount"),
            "PO Number": r.get("po_number"),
            "PO Amount": r.get("po_amount"),
            "Status": r.get("status"),
        }
        for r in records
    ]
    new_df = pd.DataFrame(new_rows, columns=TRACKER_COLUMNS)

    if config.TRACKER_PATH.exists():
        existing = pd.read_excel(config.TRACKER_PATH)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df

    config.TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_excel(config.TRACKER_PATH, index=False)
    return str(config.TRACKER_PATH)


if __name__ == "__main__":
    from extract import extract_invoices, load_local_sources
    from validate import validate_invoices

    print(f"Tracker updated: "
          f"{update_tracker(validate_invoices(extract_invoices(load_local_sources())))}")
