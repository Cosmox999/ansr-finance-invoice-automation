"""
config.py - Single place for all tunable settings.

Keeping configuration in one file (instead of scattering magic numbers and paths
across modules) is a small habit that makes the prototype easy to demo, explain,
and later harden for production.
"""

import os
from pathlib import Path

# Load GROQ_API_KEY (and anything else) from a local .env file if present, so the
# user doesn't have to export it every time. A real environment variable still
# takes precedence. This is a no-op if python-dotenv isn't installed.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- Paths ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PDF_INBOX_DIR = DATA_DIR / "invoices_pdf"      # PDFs downloaded from Gmail land here
SAMPLE_PDF_DIR = DATA_DIR / "sample_pdfs"      # generated PDF invoices (also the offline source)
PO_MASTER_PATH = DATA_DIR / "po_master.xlsx"
TRACKER_PATH = DATA_DIR / "invoice_tracker.xlsx"

OUTPUT_DIR = ROOT / "output"
EMAIL_DIR = OUTPUT_DIR / "discrepancy_emails"
RUN_LOG_PATH = OUTPUT_DIR / "run_log.jsonl"   # Audit trail: one JSON line per invoice per run

# --- Invoice source ------------------------------------------------------
# Invoices are always PDFs. The source decides where those PDFs come from:
# "gmail" = read PDF attachments from a Gmail inbox (the real workflow).
# "local" = read PDF files already saved in data/sample_pdfs/ (offline demo / no inbox).
# Override without editing code via the INVOICE_SOURCE env var.
INVOICE_SOURCE = os.environ.get("INVOICE_SOURCE", "gmail")

# --- Gmail (IMAP) --------------------------------------------------------
# We use IMAP + an App Password rather than full OAuth: far less setup for a
# prototype, and uses only the Python standard library to connect.
# Credentials are read from the environment (GMAIL_ADDRESS / GMAIL_APP_PASSWORD),
# never hardcoded.
IMAP_HOST = "imap.gmail.com"
GMAIL_MAILBOX = "INBOX"
# Which messages to scan, written in Gmail's own search syntax and run server-side
# via X-GM-RAW. Gmail does the filtering and returns ONLY unread emails that actually
# carry a PDF attachment - so it stays fast even with thousands of unread emails, and
# we never download mail we don't need. The is_invoice guard then skips any PDF that
# isn't really an invoice.
GMAIL_SEARCH = "is:unread has:attachment filename:pdf"

# After an email is processed, mark it as read so it is NOT picked up again on the
# next run - this is what stops already-processed invoices from being reprocessed
# when new mail arrives. Set False to keep emails unread (handy for re-running the
# exact same demo).
MARK_AS_READ = True

# --- LLM (Groq) ----------------------------------------------------------
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# --- Validation tolerance ------------------------------------------------
# Tolerance exists ONLY to absorb tiny rounding noise (a few paise of tax
# rounding, etc.) - which is always small in ABSOLUTE terms, no matter how large
# the invoice. So we use a small flat amount and flag everything beyond it.
#
# (We deliberately do NOT use a percentage tolerance: 1% of a large PO is real
# money, not rounding - e.g. 1% of Rs.10,00,000 is Rs.10,000, which should never
# be auto-approved. A flat threshold catches that; a percentage would hide it.)
ABS_AMOUNT_TOLERANCE = 1.0     # Rs. - ignore differences up to this; flag the rest

# Currency label used purely for display in emails / console.
# ("Rs." instead of the rupee glyph keeps the console safe on all terminals.)
CURRENCY = "Rs."

# --- Human-in-the-loop ---------------------------------------------------
# Extractions below this confidence are flagged for human review even if they
# otherwise "Match" - the kind of guardrail a real Finance deployment needs.
LOW_CONFIDENCE_THRESHOLD = 0.80
