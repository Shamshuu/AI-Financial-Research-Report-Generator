"""
test_e2e.py
===========
End-to-end smoke tests: document parsing + full report pipeline.
Run: cd backend && python test_e2e.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from chart_generator import generate_all_charts
from deterministic_extractor import extract_deterministically
from document_parser import parse_document
from pdf_generator import generate_pdf
from template_fields import validate_and_fill
from deterministic_extractor import extract_deterministically
from fillable_template import build_fillable_template

ROOT = Path(__file__).parent.parent
SAMPLES = ROOT / "sample_inputs"


def test_parse_formats():
    txt = (SAMPLES / "eternal_limited_context.txt").read_bytes()
    csv = (SAMPLES / "icici_bank_financials.csv").read_bytes()

    t1, f1 = parse_document(txt, "eternal_limited_context.txt")
    t2, f2 = parse_document(csv, "icici_bank_financials.csv")

    assert f1 == "txt" and len(t1) > 500, f"TXT parse failed: {len(t1)} chars"
    assert f2 == "csv" and len(t2) > 100, f"CSV parse failed: {len(t2)} chars"
    print(f"PASS  parse formats  txt={len(t1)} chars  csv={len(t2)} chars")


def test_deterministic_extraction():
    csv_text, _ = parse_document((SAMPLES / "icici_bank_financials.csv").read_bytes(), "icici_bank_financials.csv")
    csv_data = validate_and_fill(extract_deterministically("ICICI Bank Limited", csv_text))
    assert csv_data["ticker"] == "ICICIBANK"
    assert len(csv_data["annual_financials"]) == 5
    assert len(csv_data["shareholding"]) == 4
    assert len(csv_data["quarterly_financials"]) >= 3

    text, _ = parse_document((SAMPLES / "eternal_limited_context.txt").read_bytes(), "eternal_limited_context.txt")
    text_data = validate_and_fill(extract_deterministically("Eternal Limited", text))
    assert len(text_data["annual_financials"]) == 5
    assert len(text_data["investment_rationale"]) == 5
    assert len(text_data["risks"]) >= 3
    print("PASS  deterministic extraction  CSV and TXT fields populated")


def test_fillable_template():
    template = build_fillable_template()
    assert len(template) > 5_000
    assert b"/AcroForm" in template and b"company_name" in template
    print(f"PASS  fillable template  pdf={len(template)//1024}KB")


def test_full_pipeline(format_name: str, filename: str, company: str):
    path = SAMPLES / filename
    raw, fmt = parse_document(path.read_bytes(), filename)
    # Keep CI deterministic: LLM connectivity is integration-tested through
    # the API, while fixture outputs must not depend on network/API quotas.
    data = validate_and_fill(extract_deterministically(company, raw))
    charts = generate_all_charts(data)
    pdf = generate_pdf(data, charts)

    assert len(pdf) > 10_000, f"PDF too small for {company}"
    assert len(charts) >= 1, f"No charts for {company}"
    assert data.get("company_name"), f"Missing company name for {company}"
    print(f"PASS  pipeline ({format_name})  {company}  pdf={len(pdf)//1024}KB  charts={len(charts)}")


def main():
    test_parse_formats()
    test_deterministic_extraction()
    test_fillable_template()
    test_full_pipeline("TXT", "eternal_limited_context.txt", "Eternal Limited")
    test_full_pipeline("CSV", "icici_bank_financials.csv", "ICICI Bank Limited")
    print("\nAll E2E tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
