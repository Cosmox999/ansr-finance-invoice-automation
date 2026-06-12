"""
config.py - Single place for all tunable settings.

Keeping configuration in one file (instead of scattering magic numbers and paths
across modules) is a small habit that makes the prototype easy to demo, explain,
and later harden for production.
"""

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
INVOICE_DIR = DATA_DIR / "invoices"
PO_MASTER_PATH = DATA_DIR / "po_master.xlsx"
TRACKER_PATH = DATA_DIR / "invoice_tracker.xlsx"

OUTPUT_DIR = ROOT / "output"
EMAIL_DIR = OUTPUT_DIR / "discrepancy_emails"
RUN_LOG_PATH = OUTPUT_DIR / "run_log.jsonl"   # Audit trail: one JSON line per invoice per run

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
