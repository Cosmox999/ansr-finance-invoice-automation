# Invoice Processing & Validation — Prototype

Automates the Finance team's manual invoice workflow: **pull invoice PDFs from
Gmail → validate against the PO master → update the Excel tracker → flag
discrepancies for review.** An LLM (via Groq) handles the messy "every vendor
formats invoices differently" part; plain Python handles the exact, auditable matching.

> Built for the ANSR Global — AI Builder Intern assignment. Happy-path prototype:
> simple, practical, and runnable with one command. See
> [SOLUTION_DESIGN.md](SOLUTION_DESIGN.md) for the stakeholder-facing write-up.

---

## What it does (at a glance)

```
Gmail inbox (PDF attachments)  ──►  gmail_ingest.py (IMAP + pypdf)  ──►  extract.py (Groq LLM)
                               ──►  validate.py (PO master)  ──►  update_tracker.py (Excel)
                               ──►  flag_discrepancies.py (draft emails)
                               ──►  main.py prints a summary table + writes an audit log
```

## Setup

**1. Python** — requires Python 3.10+ (tested on 3.12).

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Get a free Groq API key**

- Go to **https://console.groq.com** → sign in → *API Keys* → *Create API Key*.
- Copy the key (starts with `gsk_...`).

**4. Set the key as an environment variable** (the code reads
`os.environ["GROQ_API_KEY"]` — it is never hardcoded):

```powershell
# Windows PowerShell
$env:GROQ_API_KEY = "gsk_your_key_here"
```

```bash
# macOS / Linux
export GROQ_API_KEY="gsk_your_key_here"
```

> Alternatively, create a `.env` file with `GROQ_API_KEY=gsk_your_key_here` — it is
> loaded automatically.

**5. Connect your Gmail (to read invoice PDFs)**

The pipeline reads invoice **PDF attachments straight from a Gmail inbox** over IMAP.
Gmail no longer allows your normal password for this, so you create a one-time
**App Password** (requires 2-Step Verification on the account):

1. Turn on **2-Step Verification**: https://myaccount.google.com/security
2. Create an App Password: https://myaccount.google.com/apppasswords
   → pick "Mail" / "Other", name it e.g. *Invoice Bot*, and copy the 16-character code.
3. Add both to your `.env` file:

```
GROQ_API_KEY=gsk_your_key_here
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your16charapppassword
```

> `.env` is gitignored — these secrets never get committed.

## Run

```bash
# (first time only) generate the PO master + the sample invoice PDFs
python generate_mock_data.py
python generate_sample_pdfs.py     # writes PDFs to data/sample_pdfs/

# email those PDFs to your Gmail address (as attachments), leave them unread, then:
python main.py
```

`python main.py` pulls the PDF invoices from your inbox → extracts fields with the
LLM → validates against the PO master → updates the Excel tracker → drafts
discrepancy emails → prints the summary.

> It uses Gmail's own search (server-side) to fetch only **unread emails that have a
> PDF attachment**, so it downloads just those — not every unread message in the
> inbox — and lets the LLM decide what's actually an invoice (non-invoice PDFs are
> skipped). Each processed email is then **marked read**, so re-runs only pick up new
> invoices and nothing is processed twice. (Set `MARK_AS_READ = False` in `config.py`
> to keep them unread for repeated demos.)

> **No inbox / offline demo:** set `INVOICE_SOURCE=local` to read the PDF invoices
> already in `data/sample_pdfs/` instead of Gmail — handy for a quick test without
> email setup. Still PDFs, just from disk. PowerShell:
> `$env:INVOICE_SOURCE="local"; python main.py`

## Folder structure

```
Finance assignment/
├── config.py                  # All paths, model, tolerances, Gmail/source settings
├── generate_mock_data.py      # Defines the mock invoice content + writes the PO master
├── generate_sample_pdfs.py    # Renders the mock invoices into PDFs to email
├── gmail_ingest.py            # Pull PDF attachments from Gmail (IMAP) + read PDF text
├── extract.py                 # LLM extraction (Groq) → structured fields + confidence
├── validate.py                # PO lookup + amount tolerance + vendor cross-check
├── update_tracker.py          # Append results to the Excel tracker
├── flag_discrepancies.py      # Draft (don't send) alert emails for mismatches
├── main.py                    # Orchestrator: runs the whole pipeline
├── requirements.txt
├── SOLUTION_DESIGN.md         # 1-2 page solution design (for Finance stakeholders)
├── README.md
├── data/
│   ├── sample_pdfs/           # 7 mock invoice PDFs (email these; also the offline source)
│   ├── invoices_pdf/          # ← PDFs downloaded from Gmail at runtime
│   ├── po_master.xlsx         # Purchase Order master (source of truth)
│   └── invoice_tracker.xlsx   # ← created/updated by the pipeline
└── output/
    ├── discrepancy_emails/    # ← draft alert emails (one per flagged invoice)
    └── run_log.jsonl          # ← audit trail: one JSON line per invoice per run
```

## The mock data (and the 3 seeded discrepancies)

Seven invoices are written in deliberately different styles (formal table, casual
email body, abbreviation-heavy slip, letter format, different date formats) to
prove the LLM copes with format variation. Three are seeded to fail validation:

| Invoice | Vendor | Expected outcome |
|---|---|---|
| ORION-AMC-2026-12 | Orion Software Solutions | **Amount Mismatch** (invoice Rs. 1,58,000 vs PO Rs. 1,45,000) |
| DLI-2026-3390 | Delta Logistics | **PO Not Found** (references PO-9999, not in master) |
| TTH-2026-0521 | Titan Tools & Hardware | **Vendor Mismatch** (right amount + valid PO-1007, but that PO belongs to Vertex Industrial Supplies) |

The other four match cleanly. The vendor mismatch is the interesting one: the
amount *and* the PO are both valid, so a system that only checked amounts would
pay it. The vendor cross-check catches a wrong-PO / duplicate / fraudulent invoice
that amount-matching alone would miss.

## Sample expected output

```
Step 1/5  Fetching invoice PDFs from Gmail ...
          -> 7 PDF invoice(s) downloaded from the inbox
Step 2/5  Extracting invoice fields with Groq LLM ...
  - Extracting invoice_apex_steel.pdf ...
  - Extracting invoice_brightspark_email.pdf ...
  - Extracting invoice_delta_logistics.pdf ...
  - Extracting invoice_orion_software.pdf ...
  - Extracting invoice_summit_office.pdf ...
  - Extracting invoice_titan_tools.pdf ...
  - Extracting invoice_zenith_pack.pdf ...
Step 3/5  Validating against PO master ...
Step 4/5  Updating Excel tracker ...
          -> .../data/invoice_tracker.xlsx
Step 5/5  Drafting discrepancy alert emails ...
          -> 3 draft(s) in .../output/discrepancy_emails

==============================================================================
INVOICE PROCESSING SUMMARY
==============================================================================
╭───────────────────┬─────────────────────────────┬────────────────┬─────────┬──────────────────────────────╮
│ Invoice #         │ Vendor                      │ Amount         │ PO #    │ Status                       │
├───────────────────┼─────────────────────────────┼────────────────┼─────────┼──────────────────────────────┤
│ APX-2026-0455     │ APEX STEEL & ALLOYS PVT LTD │ Rs. 103,250.00 │ PO-1001 │ Matched                      │
│ BSE/INV/8821      │ BrightSpark Electricals     │ Rs. 64,800.00  │ PO-1002 │ Matched                      │
│ DLI-2026-3390     │ DELTA LOGISTICS (INDIA)     │ Rs. 31,000.00  │ PO-9999 │ Discrepancy: PO Not Found    │
│ ORION-AMC-2026-12 │ Orion Software Solutions    │ Rs. 158,000.00 │ PO-1004 │ Discrepancy: Amount Mismatch │
│ SOS-2026-1190     │ SUMMIT OFFICE SUPPLIES      │ Rs. 97,500.00  │ PO-1006 │ Matched                      │
│ TTH-2026-0521     │ TITAN TOOLS & HARDWARE      │ Rs. 55,000.00  │ PO-1007 │ Discrepancy: Vendor Mismatch │
│ ZP-7741           │ Zenith Packaging Co.        │ Rs. 42,000.00  │ PO-1003 │ Matched                      │
╰───────────────────┴─────────────────────────────┴────────────────┴─────────┴──────────────────────────────╯

Processed 7 document(s)  |  4 matched  |  3 discrepancies  |  0 need review
```

A full captured run (tracker, draft emails, audit log, console output) is committed
under [sample_output/](sample_output/) so you can see the results without running it.

*(Exact numbers depend on the LLM's reading; the three seeded discrepancies will
always be flagged.)*
