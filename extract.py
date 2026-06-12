"""
extract.py - Turn raw invoice text into structured fields using an LLM.

WHY AN LLM HERE (and not regex/templates)?
Every vendor formats invoices differently - tables, email bodies, abbreviations,
varied date formats and field labels. Writing a regex/template per vendor does not
scale and breaks the moment a vendor tweaks their layout. An instruction-following
LLM reads all of these styles with one prompt, which is exactly the kind of
"varies a lot, rules are brittle" problem LLMs are good at.

We call Groq's OpenAI-compatible chat completions endpoint with the Groq SDK and
ask for a strict JSON object. We also request JSON mode and, as a belt-and-braces
fallback, strip any markdown code fences before json.loads().
"""

import json
import os
import re

from groq import Groq

import config

# The single prompt that handles every vendor format. We ask for a confidence
# score too - a cheap, honest signal for routing low-confidence extractions to a
# human (human-in-the-loop), which a real Finance deployment needs.
SYSTEM_PROMPT = """You are a precise invoice data-extraction engine for a Finance team.
You will be given the raw text of a single vendor invoice. Vendors use many
different layouts, labels, abbreviations and date formats.

Extract these fields and return ONLY a JSON object (no prose, no markdown) with
exactly these keys:
  - "vendor":          the vendor / supplier company name (string)
  - "invoice_number":  the invoice number / reference (string)
  - "invoice_date":    the invoice date, normalised to YYYY-MM-DD (string)
  - "amount":          the FINAL total payable as a number, no currency symbol,
                       no thousands separators (e.g. 103250.00)
  - "po_number":       the purchase order number exactly as written, e.g. "PO-1004"
  - "confidence":      your confidence from 0.0 to 1.0 that the above fields are
                       correct for this invoice (number)

Rules:
- "amount" is the grand total / total payable (incl. taxes if shown), not a line item.
- Indian-format numbers like 1,03,250.00 must become 103250.00.
- If a field is genuinely absent, use null and lower your confidence.
"""


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences if the model adds them."""
    text = text.strip()
    if text.startswith("```"):
        # Drop the opening fence (optionally ```json) and the trailing fence.
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _extract_one(client: Groq, filename: str, raw_text: str) -> dict:
    """Send one invoice's text to Groq and parse the JSON response."""
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Invoice text:\n\n{raw_text}"},
        ],
        temperature=0,                       # deterministic extraction
        response_format={"type": "json_object"},  # ask Groq for strict JSON
    )
    content = resp.choices[0].message.content
    data = json.loads(_strip_code_fences(content))

    # Normalise amount to a float (the LLM is told to send a clean number, but we
    # defend lightly so the rest of the pipeline can assume numeric amounts).
    if data.get("amount") is not None:
        data["amount"] = float(str(data["amount"]).replace(",", "").strip())

    data["source_file"] = filename
    return data


def extract_invoices() -> list[dict]:
    """Extract structured fields for every invoice in data/invoices/.

    Returns a list of dicts, one per invoice, each including 'source_file'.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
            "and set it, e.g. (PowerShell):  $env:GROQ_API_KEY = 'your_key_here'"
        )

    client = Groq(api_key=api_key)

    files = sorted(config.INVOICE_DIR.glob("*.txt"))
    results = []
    for path in files:
        raw_text = path.read_text(encoding="utf-8")
        print(f"  - Extracting {path.name} ...")
        record = _extract_one(client, path.name, raw_text)
        results.append(record)
    return results


if __name__ == "__main__":
    # Allow running this module standalone for quick inspection.
    for rec in extract_invoices():
        print(json.dumps(rec, ensure_ascii=False))
