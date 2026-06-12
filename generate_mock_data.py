"""
generate_mock_data.py - Create the sample dataset for the prototype.

HOW THIS MAPS TO THE REAL SCENARIO
----------------------------------
In production, Finance receives invoices as PDF attachments over email, in many
different vendor layouts. A real pipeline would (1) pull the attachment from the
inbox and (2) run PDF text extraction / OCR to get the raw text.

For this prototype we stand in for those two steps with plain-text files in
data/invoices/ - one file = one "already-extracted" invoice. Each file is written
in a DELIBERATELY different style (formal table, casual email body, abbreviations,
different date formats and field labels) so we can prove the LLM extractor copes
with format variation the way a real vendor mix would demand.

The data/po_master.xlsx file is the Purchase Order master the Finance team checks
invoices against. We seed it so that 4 invoices match cleanly and 3 are
discrepancies (one amount mismatch, one PO that does not exist, and one where the
amount is right but the invoice comes from the wrong vendor).

Run:  python generate_mock_data.py
"""

import pandas as pd

import config

# --------------------------------------------------------------------------
# 1. Mock invoices - each a different vendor "voice" and layout on purpose.
# --------------------------------------------------------------------------
# Tuple = (filename, raw_text). Comments note what makes each one tricky.

INVOICES = [

    # (A) Classic formal invoice with a header block + table. CLEAN MATCH.
    ("invoice_apex_steel.txt", """\
APEX STEEL & ALLOYS PVT LTD
GST: 27AAACA1234F1Z5 | Mumbai, Maharashtra
------------------------------------------------------------
                         TAX INVOICE
------------------------------------------------------------
Invoice No.   : APX-2026-0455
Invoice Date  : 03-06-2026
Purchase Order No. : PO-1001

Bill To: Northwind Manufacturing Ltd

  Description              Qty      Rate        Amount
  TMT Steel Bars (12mm)    50 MT    1,750.00    87,500.00
  ------------------------------------------------------
                          Sub Total        Rs. 87,500.00
                          GST @ 18%         Rs. 15,750.00
                          ------------------------------
                          GRAND TOTAL       Rs. 1,03,250.00

Payment due within 30 days. Thank you for your business.
"""),

    # (B) Casual EMAIL BODY style - no table, details inline in a sentence.
    #     Uses "PO#" abbreviation. CLEAN MATCH.
    ("invoice_brightspark_email.txt", """\
From: accounts@brightspark-electricals.com
To: payables@northwind.com
Subject: Invoice for May electrical works

Hi team,

Please find our billing details for the electrical fit-out completed last week.
This is against PO# PO-1002. Our invoice number is BSE/INV/8821 dated
11 June 2026, and the total payable comes to Rs. 64,800 (all inclusive).

Kindly process at the earliest and confirm once done.

Thanks,
Ravi Menon
BrightSpark Electricals
"""),

    # (C) Minimal / abbreviation-heavy slip. "Amt", "Dt", "PO No". CLEAN MATCH.
    ("invoice_zenith_pack.txt", """\
ZENITH PACKAGING
Inv No: ZP-7741
Dt: 2026/06/07
Vendor: Zenith Packaging Co.
PO No: PO-1003
Amt: 42,000.00 INR
Corrugated boxes - bulk order. Net 15.
"""),

    # (D) Letter-style invoice, spelled-out wording. AMOUNT MISMATCH (seeded).
    #     Invoice says 1,58,000 but PO-1004 is for 1,45,000.
    ("invoice_orion_software.txt", """\
ORION SOFTWARE SOLUTIONS
Annual Maintenance Contract - Billing Statement

Dear Northwind Accounts Team,

This statement is issued under Purchase Order Number PO-1004.
Invoice reference: ORION-AMC-2026-12
Date of issue: June 5, 2026
Total amount payable for the annual maintenance renewal is
Rupees One Lakh Fifty-Eight Thousand only (Rs. 1,58,000.00).

Regards,
Finance Desk, Orion Software Solutions
"""),

    # (E) Different date format (mm/dd/yyyy) + "P.O." with dots.
    #     PO DOES NOT EXIST in master (seeded). PO-9999.
    ("invoice_delta_logistics.txt", """\
DELTA LOGISTICS (INDIA)
Freight & Transport Services

Invoice Number: DLI-2026-3390
Invoice Date: 06/09/2026
Reference P.O.: PO-9999
Bill To: Northwind Manufacturing Ltd

Outbound freight - 4 consignments .......... Rs. 28,500.00
Fuel surcharge ............................. Rs.  2,500.00
                                  TOTAL .... Rs. 31,000.00
"""),

    # (F) Compact tabular vendor with thousands separators. CLEAN MATCH.
    ("invoice_summit_office.txt", """\
SUMMIT OFFICE SUPPLIES  ::  Invoice
=====================================
Invoice #     SOS-2026-1190
Issued        08-Jun-2026
Against PO    PO-1006
Customer      Northwind Manufacturing Ltd
-------------------------------------
Office chairs x20 ............ 90,000.00
Desk organizers x40 .........  7,500.00
-------------------------------------
TOTAL (INR) ................. 97,500.00
"""),

    # (G) VENDOR MISMATCH (seeded). The amount (55,000) and PO (PO-1007) are both
    #     valid, but PO-1007 belongs to "Vertex Industrial Supplies" - this invoice
    #     is from "Titan Tools & Hardware". Pure amount-matching would wave it
    #     through; the vendor cross-check catches it.
    ("invoice_titan_tools.txt", """\
TITAN TOOLS & HARDWARE
Invoice: TTH-2026-0521
Date: 10-Jun-2026
PO Reference: PO-1007
Billed to: Northwind Manufacturing Ltd

Industrial tool kits (x15) ......... Rs. 50,000.00
Safety equipment ................... Rs.  5,000.00
                          Total ..... Rs. 55,000.00
"""),
]


# --------------------------------------------------------------------------
# 2. PO master - the source of truth Finance validates against.
# --------------------------------------------------------------------------
# Note the three intentional discrepancies:
#   - PO-1004: PO amount 1,45,000 vs invoice 1,58,000      -> Amount Mismatch
#   - PO-9999: referenced by Delta invoice but NOT listed  -> PO Not Found
#   - PO-1007: belongs to Vertex, but Titan Tools invoices  -> Vendor Mismatch
PO_MASTER = [
    {"PO Number": "PO-1001", "Vendor Name": "Apex Steel & Alloys Pvt Ltd",
     "PO Amount": 103250.00, "Status": "Open"},
    {"PO Number": "PO-1002", "Vendor Name": "BrightSpark Electricals",
     "PO Amount": 64800.00, "Status": "Open"},
    {"PO Number": "PO-1003", "Vendor Name": "Zenith Packaging Co.",
     "PO Amount": 42000.00, "Status": "Open"},
    # PO-1004 amount (1,45,000) deliberately differs from the invoice (1,58,000).
    {"PO Number": "PO-1004", "Vendor Name": "Orion Software Solutions",
     "PO Amount": 145000.00, "Status": "Open"},
    {"PO Number": "PO-1006", "Vendor Name": "Summit Office Supplies",
     "PO Amount": 97500.00, "Status": "Open"},
    # PO-1007 belongs to Vertex; the Titan Tools invoice quotes it (right amount,
    # wrong vendor) -> Vendor Mismatch.
    {"PO Number": "PO-1007", "Vendor Name": "Vertex Industrial Supplies",
     "PO Amount": 55000.00, "Status": "Open"},
    # (No PO-9999 on purpose -> Delta Logistics invoice will be flagged.)
]


def main():
    """Write the mock invoice text files and the PO master Excel file."""
    # Create folders
    config.INVOICE_DIR.mkdir(parents=True, exist_ok=True)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Write invoice text files
    for filename, text in INVOICES:
        (config.INVOICE_DIR / filename).write_text(text, encoding="utf-8")
    print(f"Wrote {len(INVOICES)} mock invoices to {config.INVOICE_DIR}")

    # Write PO master
    df = pd.DataFrame(PO_MASTER)
    df.to_excel(config.PO_MASTER_PATH, index=False)
    print(f"Wrote PO master ({len(PO_MASTER)} POs) to {config.PO_MASTER_PATH}")
    print("Seeded discrepancies: PO-1004 (amount mismatch), PO-9999 (PO not "
          "found), PO-1007 (vendor mismatch).")


if __name__ == "__main__":
    main()
