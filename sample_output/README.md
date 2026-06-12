# Sample output (a captured real run)

These files are the actual result of running `python main.py` on the mock data, so
a reviewer can see the system's output **without needing a Groq API key**.

| File | What it is |
|------|------------|
| `console_output.txt` | The full console run, including the summary table (7 invoices: 4 matched, 3 discrepancies). |
| `invoice_tracker.xlsx` | The Excel tracker the pipeline produced — one row per invoice with its status. |
| `run_log.jsonl` | The audit trail — one JSON line per invoice (what was extracted and decided). |
| `discrepancy_emails/` | The three draft alert emails, one per flagged invoice. |

The three seeded discrepancies it catches:

- **DLI-2026-3390** — *PO Not Found* (references PO-9999, which isn't in the master).
- **ORION-AMC-2026-12** — *Amount Mismatch* (invoice Rs. 1,58,000 vs PO Rs. 1,45,000).
- **TTH-2026-0521** — *Vendor Mismatch* (amount + PO are valid, but PO-1007 belongs
  to Vertex Industrial Supplies, not Titan Tools — caught by the vendor cross-check
  that pure amount-matching would miss).
