"""
validate.py - Check each extracted invoice against the PO master.

This is the deterministic, rules-based half of the system. The LLM handles the
messy "read any format" part; plain Python handles the part that must be exact and
auditable - matching POs and comparing amounts. Using AI only where it adds value,
and rules where they belong, is the core judgment this kind of role is about.
"""

import re

import pandas as pd

import config


def _normalise_vendor(name) -> str:
    """Lowercase and keep only letters/digits, so 'Apex Steel & Co.' and
    'APEX STEEL CO' compare equal (ignores case, spaces and punctuation)."""
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def _vendor_matches(invoice_vendor, po_vendor) -> bool:
    """Tolerant vendor check: treat names as the same if, after normalising, they
    are equal or one is contained in the other (handles minor wording like a
    missing 'Pvt Ltd'/'Co.'). If either side is blank we don't raise a false flag.
    """
    a = _normalise_vendor(invoice_vendor)
    b = _normalise_vendor(po_vendor)
    if not a or not b:
        return True
    return a == b or a in b or b in a


def _amount_within_tolerance(invoice_amount: float, po_amount: float) -> bool:
    """True if the invoice amount matches the PO amount within tolerance.

    Tolerance is a small FLAT amount (config.ABS_AMOUNT_TOLERANCE) - just enough
    to absorb rounding noise. Anything bigger is treated as a real mismatch, so a
    genuine overcharge (even on a large invoice) is always flagged for a human.
    """
    return abs(invoice_amount - po_amount) <= config.ABS_AMOUNT_TOLERANCE


def validate_invoices(invoices: list[dict]) -> list[dict]:
    """Enrich each invoice record with a validation status and PO details.

    Status values:
      - "Matched"
      - "Discrepancy: PO Not Found"
      - "Discrepancy: Amount Mismatch"
      - "Discrepancy: Vendor Mismatch"   (PO + amount fine, but wrong vendor)
      - "Review: Low Confidence"         (matched, but extraction confidence is low)
      - "Skipped: Not an Invoice"        (the PDF wasn't a vendor invoice at all)
    """
    po_df = pd.read_excel(config.PO_MASTER_PATH)
    # Index the PO master by PO Number for O(1) lookups.
    po_by_number = {str(row["PO Number"]).strip(): row for _, row in po_df.iterrows()}

    enriched = []
    for inv in invoices:
        rec = dict(inv)  # copy so we don't mutate the extractor's output

        # Guard: real inboxes contain non-invoice PDFs (statements, receipts, etc.).
        # The LLM flags those; we skip them instead of raising a false discrepancy.
        if not inv.get("is_invoice", True):
            rec["po_amount"] = None
            rec["po_vendor"] = None
            rec["status"] = "Skipped: Not an Invoice"
            enriched.append(rec)
            continue

        po_number = str(inv.get("po_number") or "").strip()
        po_row = po_by_number.get(po_number)

        if po_row is None:
            rec["po_amount"] = None
            rec["po_vendor"] = None
            rec["status"] = "Discrepancy: PO Not Found"
        else:
            po_amount = float(po_row["PO Amount"])
            rec["po_amount"] = po_amount
            rec["po_vendor"] = po_row["Vendor Name"]
            invoice_amount = inv.get("amount")

            if invoice_amount is None or not _amount_within_tolerance(invoice_amount, po_amount):
                rec["status"] = "Discrepancy: Amount Mismatch"
            elif not _vendor_matches(inv.get("vendor"), po_row["Vendor Name"]):
                # PO exists and the amount is right, but the invoice is from a
                # different vendor than the PO - a control pure amount-matching
                # would miss (wrong PO quoted, or a duplicate/fraudulent invoice).
                rec["status"] = "Discrepancy: Vendor Mismatch"
            else:
                rec["status"] = "Matched"

        # Human-in-the-loop overlay: even a clean match gets routed to a human if
        # the LLM wasn't confident about what it read.
        confidence = inv.get("confidence")
        if rec["status"] == "Matched" and confidence is not None \
                and confidence < config.LOW_CONFIDENCE_THRESHOLD:
            rec["status"] = "Review: Low Confidence"

        enriched.append(rec)

    return enriched


if __name__ == "__main__":
    import json
    from extract import extract_invoices, load_local_sources

    for record in validate_invoices(extract_invoices(load_local_sources())):
        print(json.dumps(record, ensure_ascii=False))
