"""
generate_examples.py
====================
Generate example research PDFs from bundled sample inputs.
Used to produce submission-ready example outputs without the web UI.

Usage:
    cd backend
    python generate_examples.py
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from chart_generator import generate_all_charts
from deterministic_extractor import extract_deterministically
from document_parser import parse_document
from pdf_generator import generate_pdf
from fillable_template import build_fillable_template
from template_fields import validate_and_fill

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
SAMPLE_INPUTS = ROOT / "sample_inputs"
EXAMPLES_OUT = ROOT / "examples"

EXAMPLES = [
    {
        "company_name": "Eternal Limited",
        "input_file": SAMPLE_INPUTS / "eternal_limited_context.txt",
        "output_file": EXAMPLES_OUT / "Eternal_Limited_report.pdf",
    },
    {
        "company_name": "ICICI Bank Limited",
        "input_file": SAMPLE_INPUTS / "icici_bank_financials.csv",
        "output_file": EXAMPLES_OUT / "ICICI_Bank_report.pdf",
    },
]


def generate_one(company_name: str, input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Sample input not found: {input_path}")

    logger.info("Processing %s from %s", company_name, input_path.name)
    file_bytes = input_path.read_bytes()
    raw_text, fmt = parse_document(file_bytes, input_path.name)
    logger.info("  Parsed %d chars (%s)", len(raw_text), fmt)

    # Examples must be reproducible without an API key or network access.
    extracted = extract_deterministically(company_name, raw_text)
    data = validate_and_fill(extracted)
    charts = generate_all_charts(data)
    pdf_bytes = generate_pdf(data, charts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)
    logger.info("  Saved %s (%d KB, %d charts)", output_path.name, len(pdf_bytes) // 1024, len(charts))


def main() -> int:
    logger.info("Generating %d example reports → %s", len(EXAMPLES), EXAMPLES_OUT)
    errors = []
    for ex in EXAMPLES:
        try:
            generate_one(ex["company_name"], ex["input_file"], ex["output_file"])
        except Exception as e:
            logger.exception("Failed: %s", ex["company_name"])
            errors.append((ex["company_name"], str(e)))

    template_path = EXAMPLES_OUT / "Editable_Research_Report_Template.pdf"
    template_path.write_bytes(build_fillable_template())
    logger.info("  Saved %s", template_path.name)

    if errors:
        for name, err in errors:
            logger.error("  %s: %s", name, err)
        return 1

    logger.info("Done. Example PDFs ready in examples/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
