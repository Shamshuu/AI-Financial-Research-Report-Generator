"""Build the editable, Geojit-style research-report template.

The application uses the same field names as ``template_fields.py``.  The
template is useful for analyst review/manual completion, while generated
reports are rendered as paginated, print-ready PDFs.
"""

from __future__ import annotations

import io
from typing import Iterable

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4
TEAL, ORANGE, INK, PALE = HexColor("#006D77"), HexColor("#E29578"), HexColor("#1A2340"), HexColor("#F3F7F8")


def _header(c: canvas.Canvas, title: str, page: int) -> None:
    c.setFillColor(TEAL)
    c.rect(0, PAGE_H - 1.1 * cm, PAGE_W, 1.1 * cm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(1.35 * cm, PAGE_H - .7 * cm, "EQUITY RESEARCH | EDITABLE TEMPLATE")
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1.35 * cm, PAGE_H - 2.0 * cm, title)
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.2)
    c.line(1.35 * cm, 1.1 * cm, PAGE_W - 1.35 * cm, 1.1 * cm)
    c.setFillColor(INK)
    c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_W - 1.35 * cm, .65 * cm, f"Page {page}")


def _field(c: canvas.Canvas, name: str, label: str, x: float, y: float, width: float, height: float = .55 * cm, multiline: bool = False) -> None:
    c.setFillColor(INK)
    c.setFont("Helvetica", 7)
    c.drawString(x, y + height + 3, label)
    flags = 4096 if multiline else 0
    c.acroForm.textfield(name=name, tooltip=label, x=x, y=y, width=width, height=height,
                         borderStyle="solid", borderWidth=.5, borderColor=HexColor("#9CB8BC"),
                         fillColor=white, textColor=INK, forceBorder=True, fieldFlags=flags,
                         fontName="Helvetica", fontSize=8)


def _table(c: canvas.Canvas, title: str, columns: Iterable[str], rows: int, y: float, prefix: str) -> float:
    x, width, row_h = 1.35 * cm, PAGE_W - 2.7 * cm, .62 * cm
    columns = list(columns)
    c.setFillColor(TEAL)
    c.rect(x, y, width, .55 * cm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 5, y + 5, title)
    y -= .65 * cm
    cell_w = width / len(columns)
    c.setFillColor(PALE)
    c.rect(x, y, width, .45 * cm, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 6.5)
    for index, column in enumerate(columns):
        c.drawCentredString(x + cell_w * (index + .5), y + 4, column)
    y -= row_h
    for row in range(rows):
        for col in range(len(columns)):
            _field(c, f"{prefix}_{row}_{col}", "", x + col * cell_w + 1, y + 2, cell_w - 2, row_h - 4)
        y -= row_h
    return y


def build_fillable_template() -> bytes:
    """Return a multi-page interactive PDF template with named AcroForm fields."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, title="Editable Equity Research Report Template", author="AI Financial Research Report Generator")

    _header(c, "Company Research Report", 1)
    fields = [("company_name", "Company Name"), ("ticker", "Ticker"), ("exchange", "Exchange"), ("sector", "Sector"),
              ("cmp", "CMP (Rs.)"), ("target_price", "Target Price (Rs.)"), ("upside_pct", "Upside (%)"), ("rating", "Rating"),
              ("report_date", "Report Date"), ("analyst_name", "Analyst")]
    for i, (name, label) in enumerate(fields):
        col, row = i % 2, i // 2
        _field(c, name, label, 1.35 * cm + col * 9.1 * cm, PAGE_H - 3.25 * cm - row * 1.15 * cm, 7.8 * cm)
    y = PAGE_H - 9.3 * cm
    y = _table(c, "Company Data", ["Metric", "Value", "Metric", "Value"], 5, y, "company_data")
    _field(c, "company_description", "Company Overview", 1.35 * cm, y - 3.1 * cm, PAGE_W - 2.7 * cm, 2.7 * cm, multiline=True)
    c.showPage()

    _header(c, "Financial Summary", 2)
    y = PAGE_H - 3.0 * cm
    y = _table(c, "Annual Financial Summary (Rs. cr)", ["Metric", "FY-2", "FY-1", "FY", "FY+1", "FY+2"], 13, y, "annual")
    c.showPage()

    _header(c, "Quarterly Performance & Analysis", 3)
    y = PAGE_H - 3.0 * cm
    y = _table(c, "Quarterly Financials (Rs. cr)", ["Metric", "Current", "Prior Year", "YoY", "Prior Qtr", "QoQ"], 7, y, "quarterly")
    y -= .2 * cm
    y = _table(c, "Change in Estimates", ["Metric", "Old FY1", "Old FY2", "New FY1", "New FY2", "Change"], 4, y, "estimates")
    _field(c, "investment_rationale", "Key Highlights", 1.35 * cm, 2.2 * cm, PAGE_W - 2.7 * cm, 2.2 * cm, multiline=True)
    c.showPage()

    _header(c, "Valuation, Risks & Recommendation", 4)
    _field(c, "valuation_outlook", "Outlook & Valuation", 1.35 * cm, PAGE_H - 6.1 * cm, PAGE_W - 2.7 * cm, 2.6 * cm, multiline=True)
    _field(c, "risks", "Key Risks", 1.35 * cm, PAGE_H - 10.1 * cm, PAGE_W - 2.7 * cm, 2.1 * cm, multiline=True)
    _table(c, "Recommendation History", ["Date", "Rating", "Target Price"], 6, PAGE_H - 11.8 * cm, "recommendation")
    c.save()
    buf.seek(0)
    return buf.read()
