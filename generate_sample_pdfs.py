"""
generate_sample_pdfs.py - Turn the mock invoice texts into real PDF files.

The Gmail workflow reads PDF attachments, so for testing we need actual PDFs to
email to ourselves. This script renders each mock invoice (the same ones used in
the offline demo) into a PDF in data/sample_pdfs/, preserving the layout with a
monospace font so the different vendor formats still look distinct.

Workflow:
  1. python generate_sample_pdfs.py        # creates the PDFs
  2. Email those PDFs (as attachments) to your Gmail
  3. python main.py                         # pulls them from Gmail and processes

Run:  python generate_sample_pdfs.py
"""

from fpdf import FPDF

import config
from generate_mock_data import INVOICES


MAX_CHARS_PER_LINE = 90  # Courier 9pt fits ~90 chars across an A4 page with margins


def _text_to_pdf(text: str, out_path) -> None:
    """Render plain invoice text to a single PDF, monospace to keep alignment.

    We hard-wrap long lines by character in Python and draw each line with a simple
    cell. This avoids fpdf's auto-wrapping entirely (which can loop/raise on long
    unbroken runs like rows of dashes), so rendering is fully deterministic.
    """
    pdf = FPDF(format="A4")
    pdf.set_margins(left=10, top=12, right=10)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Courier", size=9)
    # Replace any characters the built-in font can't encode (latin-1) so we never
    # crash on an odd glyph; our mock invoices are plain ASCII so this is a no-op.
    safe = text.encode("latin-1", "replace").decode("latin-1")
    for raw_line in safe.split("\n"):
        # Break each source line into chunks that fit the page width.
        chunks = [raw_line[i:i + MAX_CHARS_PER_LINE]
                  for i in range(0, len(raw_line), MAX_CHARS_PER_LINE)] or [""]
        for chunk in chunks:
            pdf.cell(0, 5, text=chunk, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(out_path))


def main():
    """Render every mock invoice text into a PDF in data/sample_pdfs/."""
    config.SAMPLE_PDF_DIR.mkdir(parents=True, exist_ok=True)
    for filename, text in INVOICES:
        _text_to_pdf(text, config.SAMPLE_PDF_DIR / filename)
    print(f"Wrote {len(INVOICES)} invoice PDFs to {config.SAMPLE_PDF_DIR}")
    print("Next: email these PDFs to your Gmail, then run  python main.py")


if __name__ == "__main__":
    main()
