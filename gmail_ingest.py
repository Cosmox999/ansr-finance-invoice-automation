"""
gmail_ingest.py - Pull invoice PDFs from a Gmail inbox and read their text.

This is the real front door of the workflow: instead of reading bundled text
files, we connect to Gmail, find emails that have PDF attachments, download those
PDFs, and extract their text - which then flows into the same extraction +
validation pipeline as before.

Design choices (kept deliberately simple for a prototype):
  - IMAP + an App Password, not full OAuth. IMAP is built into Python's standard
    library (imaplib/email), so there's no Google Cloud project or consent screen
    to set up - just an App Password in the .env file.
  - We read messages with BODY.PEEK[] so they are NOT marked as read, which means
    you can re-run the demo as many times as you like.
  - pypdf extracts text from digitally-generated PDFs. Scanned/image PDFs would
    need an OCR step (e.g. Tesseract) - noted as a production next step.

Credentials come from the environment (never hardcoded):
  GMAIL_ADDRESS        e.g. you@gmail.com
  GMAIL_APP_PASSWORD   a 16-char Google App Password (NOT your normal password)
"""

import email
import imaplib
import os
from email.header import decode_header

from pypdf import PdfReader

import config


def read_pdf_text(pdf_path) -> str:
    """Extract all text from a PDF file as a single string."""
    reader = PdfReader(str(pdf_path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages).strip()


def _decode_filename(raw_name: str) -> str:
    """Decode an email attachment filename that may be MIME-encoded."""
    parts = decode_header(raw_name)
    out = ""
    for text, enc in parts:
        out += text.decode(enc or "utf-8", errors="replace") if isinstance(text, bytes) else text
    return out


def fetch_invoice_pdfs() -> list:
    """Connect to Gmail, save every PDF attachment from matching emails, and
    return the list of saved file paths."""
    address = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    # Google displays App Passwords in 4 groups of 4 (e.g. "abcd efgh ijkl mnop");
    # strip spaces so a direct copy-paste works.
    app_password = app_password.replace(" ", "").strip()
    if not address or not app_password:
        raise RuntimeError(
            "GMAIL_ADDRESS / GMAIL_APP_PASSWORD are not set. Put them in your .env "
            "file. The app password is a 16-char Google App Password (Google "
            "Account -> Security -> 2-Step Verification -> App passwords), not your "
            "normal Gmail password."
        )

    config.PDF_INBOX_DIR.mkdir(parents=True, exist_ok=True)

    imap = imaplib.IMAP4_SSL(config.IMAP_HOST)
    imap.login(address, app_password)
    try:
        imap.select(config.GMAIL_MAILBOX)
        _status, message_sets = imap.search(None, config.GMAIL_SEARCH)
        message_ids = message_sets[0].split()

        saved = []
        for msg_id in message_ids:
            # BODY.PEEK[] downloads the message WITHOUT marking it as read.
            _status, data = imap.fetch(msg_id, "(BODY.PEEK[])")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)

            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                filename = part.get_filename()
                if not filename:
                    continue
                filename = _decode_filename(filename)
                if not filename.lower().endswith(".pdf"):
                    continue
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                dest = config.PDF_INBOX_DIR / filename
                dest.write_bytes(payload)
                saved.append(dest)
        return saved
    finally:
        imap.logout()


def ingest_from_gmail() -> list[dict]:
    """Fetch PDF attachments from Gmail and return one record per invoice as
    {"source_file": <pdf name>, "raw_text": <extracted text>}.

    This is the same shape the extractor consumes for local .txt invoices, so the
    rest of the pipeline is unchanged.
    """
    pdf_paths = fetch_invoice_pdfs()
    sources = []
    for path in sorted(pdf_paths):
        text = read_pdf_text(path)
        sources.append({"source_file": path.name, "raw_text": text})
    return sources


if __name__ == "__main__":
    found = ingest_from_gmail()
    print(f"Fetched {len(found)} invoice PDF(s) from Gmail:")
    for item in found:
        preview = item["raw_text"].replace("\n", " ")[:80]
        print(f"  - {item['source_file']}: {preview}...")
