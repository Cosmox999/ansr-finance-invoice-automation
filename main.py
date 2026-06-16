"""
main.py - Run the whole invoice-automation pipeline end to end.

    Email/PDF (mock text)  ->  Extract (Groq LLM)  ->  Validate (PO master)
                           ->  Update tracker (Excel)  ->  Flag discrepancies (drafts)
                           ->  Console summary + audit log

Run:  python main.py
"""

import json
import sys
from datetime import datetime

from tabulate import tabulate

import config
from extract import extract_invoices, load_local_sources
from gmail_ingest import ingest_from_gmail
from validate import validate_invoices
from update_tracker import update_tracker
from flag_discrepancies import flag_discrepancies

# Render the box-drawing summary table correctly on Windows terminals, whose
# default code page (cp1252) can't encode Unicode line glyphs.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def _money(value) -> str:
    """Format a number as 'Rs. 1,234.00', or 'N/A' if it is None."""
    if value is None:
        return "N/A"
    return f"{config.CURRENCY} {value:,.2f}"


def _write_audit_log(records: list[dict]) -> None:
    """Append one JSON line per invoice per run - a simple, greppable audit trail.

    Production Finance systems must be able to answer 'what did the bot decide, and
    why, on this invoice, on this date?'. A JSONL log is the cheapest honest version
    of that, and it never overwrites history.
    """
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with config.RUN_LOG_PATH.open("a", encoding="utf-8") as f:
        for r in records:
            entry = {"run_id": run_id, **r}
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _print_summary(records: list[dict]) -> None:
    rows = []
    for r in records:
        rows.append([
            r.get("invoice_number") or "N/A",
            (r.get("vendor") or "N/A")[:28],
            _money(r.get("amount")),
            r.get("po_number") or "N/A",
            r.get("status"),
        ])

    print("\n" + "=" * 78)
    print("INVOICE PROCESSING SUMMARY")
    print("=" * 78)
    print(tabulate(
        rows,
        headers=["Invoice #", "Vendor", "Amount", "PO #", "Status"],
        tablefmt="rounded_outline",
    ))

    # Counts by outcome - the line a Finance lead actually cares about.
    matched = sum(1 for r in records if r["status"] == "Matched")
    review = sum(1 for r in records if r["status"].startswith("Review"))
    discrepancies = sum(1 for r in records if r["status"].startswith("Discrepancy"))
    skipped = sum(1 for r in records if r["status"].startswith("Skipped"))
    summary = (
        f"\nProcessed {len(records)} document(s)  |  "
        f"{matched} matched  |  {discrepancies} discrepancies  |  "
        f"{review} need review"
    )
    if skipped:
        summary += f"  |  {skipped} skipped (not an invoice)"
    print(summary)


def _load_sources() -> list[dict]:
    """Get invoice text from the configured source: Gmail PDFs or local .txt."""
    if config.INVOICE_SOURCE == "gmail":
        print("Step 1/5  Fetching invoice PDFs from Gmail ...")
        sources = ingest_from_gmail()
        print(f"          -> {len(sources)} PDF invoice(s) downloaded from the inbox")
    else:
        print("Step 1/5  Loading local .txt invoices ...")
        sources = load_local_sources()
        print(f"          -> {len(sources)} invoice file(s) found")
    return sources


def run_pipeline() -> list[dict]:
    """Run ingest -> extract -> validate -> track -> flag, then print a summary."""
    sources = _load_sources()
    if not sources:
        print("\nNo invoices found to process. Nothing to do.")
        return []

    print("Step 2/5  Extracting invoice fields with Groq LLM ...")
    extracted = extract_invoices(sources)

    print("Step 3/5  Validating against PO master ...")
    validated = validate_invoices(extracted)

    print("Step 4/5  Updating Excel tracker ...")
    tracker_path = update_tracker(validated)
    print(f"          -> {tracker_path}")

    print("Step 5/5  Drafting discrepancy alert emails ...")
    drafts = flag_discrepancies(validated)
    if drafts:
        print(f"          -> {len(drafts)} draft(s) in {config.EMAIL_DIR}")
        for p in drafts:
            print(f"             - {p}")
    else:
        print("          -> No discrepancies to flag.")

    _write_audit_log(validated)
    _print_summary(validated)
    return validated


if __name__ == "__main__":
    run_pipeline()
