"""
pdf_generator.py
================
Generates a Geojit-style research report PDF using ReportLab.
Layout closely mirrors the Eternal/Geojit sample PDF.
"""

import io
import logging
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepInFrame,
    HRFlowable,
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------
TEAL        = colors.HexColor("#006D77")
TEAL_LIGHT  = colors.HexColor("#83C5BE")
TEAL_DARK   = colors.HexColor("#004C54")
ORANGE      = colors.HexColor("#E29578")
ORANGE_LIGHT= colors.HexColor("#F4A985")
BG_HEADER   = colors.HexColor("#006D77")
BG_SUBHDR   = colors.HexColor("#E8F4F5")
TEXT_DARK   = colors.HexColor("#1A2340")
TEXT_MED    = colors.HexColor("#4A5568")
TEXT_LIGHT  = colors.HexColor("#718096")
WHITE       = colors.white
LIGHT_GRAY  = colors.HexColor("#F7F8FA")
MID_GRAY    = colors.HexColor("#DDE3E9")
RATING_BUY  = colors.HexColor("#16A085")
RATING_HOLD = colors.HexColor("#E67E22")
RATING_SELL = colors.HexColor("#E74C3C")

PAGE_W, PAGE_H = A4
MARGIN_L = 1.5 * cm
MARGIN_R = 1.5 * cm
MARGIN_T = 0.8 * cm
MARGIN_B = 1.2 * cm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _build_styles():
    base = getSampleStyleSheet()
    s = {}

    s["title"] = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=14,
        textColor=WHITE, leading=18, spaceAfter=2
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle", fontName="Helvetica", fontSize=8,
        textColor=colors.HexColor("#B2DFDB"), leading=11
    )
    s["rating_tag"] = ParagraphStyle(
        "rating_tag", fontName="Helvetica-Bold", fontSize=10,
        textColor=WHITE, alignment=TA_CENTER
    )
    s["section_header"] = ParagraphStyle(
        "section_header", fontName="Helvetica-Bold", fontSize=9,
        textColor=WHITE, leading=13, spaceAfter=4, spaceBefore=6,
        leftIndent=4
    )
    s["body"] = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=7.5,
        textColor=TEXT_DARK, leading=12, alignment=TA_JUSTIFY,
        spaceAfter=4
    )
    s["bullet"] = ParagraphStyle(
        "bullet", fontName="Helvetica", fontSize=7.5,
        textColor=TEXT_DARK, leading=11, leftIndent=12,
        firstLineIndent=-8, spaceAfter=4
    )
    s["table_header"] = ParagraphStyle(
        "table_header", fontName="Helvetica-Bold", fontSize=7,
        textColor=WHITE, alignment=TA_CENTER
    )
    s["table_cell"] = ParagraphStyle(
        "table_cell", fontName="Helvetica", fontSize=7,
        textColor=TEXT_DARK, alignment=TA_RIGHT
    )
    s["table_label"] = ParagraphStyle(
        "table_label", fontName="Helvetica", fontSize=7,
        textColor=TEXT_DARK, alignment=TA_LEFT
    )
    s["table_label_bold"] = ParagraphStyle(
        "table_label_bold", fontName="Helvetica-Bold", fontSize=7,
        textColor=TEXT_DARK, alignment=TA_LEFT
    )
    s["metric_label"] = ParagraphStyle(
        "metric_label", fontName="Helvetica", fontSize=6.5,
        textColor=TEXT_MED, leading=9
    )
    s["metric_value"] = ParagraphStyle(
        "metric_value", fontName="Helvetica-Bold", fontSize=8,
        textColor=TEXT_DARK, leading=10
    )
    s["disclaimer"] = ParagraphStyle(
        "disclaimer", fontName="Helvetica", fontSize=5.5,
        textColor=TEXT_LIGHT, leading=8, alignment=TA_JUSTIFY
    )
    s["small_bold"] = ParagraphStyle(
        "small_bold", fontName="Helvetica-Bold", fontSize=7,
        textColor=TEXT_DARK, leading=10
    )
    s["url"] = ParagraphStyle(
        "url", fontName="Helvetica", fontSize=7,
        textColor=TEAL, leading=9, alignment=TA_RIGHT
    )
    return s


STYLES = _build_styles()

# ---------------------------------------------------------------------------
# Helper Flowables
# ---------------------------------------------------------------------------

class ColorRect(Flowable):
    """A filled rectangle flowable (for section backgrounds)."""
    def __init__(self, width, height, fill_color, stroke_color=None, radius=0):
        super().__init__()
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        if self.stroke_color:
            self.canv.setStrokeColor(self.stroke_color)
        if self.radius:
            self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1,
                                stroke=1 if self.stroke_color else 0)
        else:
            self.canv.rect(0, 0, self.width, self.height, fill=1,
                           stroke=1 if self.stroke_color else 0)


def _section_header(title: str, width: float = CONTENT_W) -> Table:
    """Teal section header bar with white text."""
    p = Paragraph(f"<b>{title.upper()}</b>", STYLES["section_header"])
    t = Table([[p]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    return t


def _na(val) -> str:
    if val is None or val == "" or val == 0 or val == 0.0:
        return "N/A"
    return str(val)


def _rating_color(rating: str):
    r = (rating or "").upper()
    if r in ("BUY", "ACCUMULATE"):
        return RATING_BUY
    elif r in ("HOLD", "NEUTRAL"):
        return RATING_HOLD
    elif r in ("SELL", "REDUCE"):
        return RATING_SELL
    return TEAL


# ---------------------------------------------------------------------------
# Page layout / header+footer callbacks
# ---------------------------------------------------------------------------

def _add_page_header_footer(canvas, doc, data: Dict):
    """Draw persistent header bar on every page."""
    canvas.saveState()

    # Top teal bar
    canvas.setFillColor(BG_HEADER)
    canvas.rect(0, PAGE_H - 1.0 * cm, PAGE_W, 1.0 * cm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(MARGIN_L, PAGE_H - 0.65 * cm,
                      f"{data.get('company_name','Company')} | Initiating Coverage")
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(PAGE_W - MARGIN_R, PAGE_H - 0.65 * cm,
                           f"www.geojit.com | Page {canvas.getPageNumber()}")

    # Bottom orange rule + disclaimer line
    canvas.setStrokeColor(ORANGE)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN_L, MARGIN_B - 2 * mm, PAGE_W - MARGIN_R, MARGIN_B - 2 * mm)
    canvas.setFillColor(TEXT_LIGHT)
    canvas.setFont("Helvetica", 5)
    canvas.drawString(MARGIN_L, MARGIN_B - 5 * mm,
                      "Geojit Financial Services Ltd. | SEBI Reg. No: INH200000345 | "
                      "This report is for informational purposes only.")

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_cover_header(data: Dict, story: List) -> None:
    """
    Full-width cover header: company name, rating box, CMP / Target.
    Mirrors the Geojit report cover strip layout.
    """
    company   = data.get("company_name", "N/A")
    ticker    = data.get("ticker", "")
    exchange  = data.get("exchange", "NSE")
    cap_type  = data.get("cap_type", "Large Cap")
    rating    = data.get("rating", "N/A")
    cmp       = data.get("cmp", 0)
    target    = data.get("target_price", 0)
    upside    = data.get("upside_pct", 0)
    period    = data.get("investment_period", "12 Months")
    report_dt = data.get("report_date", "")
    analyst   = data.get("analyst_name", "Research Team")
    sector    = data.get("sector", "")

    rating_color = _rating_color(rating)

    # --- Header table: left=company info, right=price box ---
    cmp_str    = f"Rs. {cmp:,.0f}" if cmp else "N/A"
    target_str = f"Rs. {target:,.0f}" if target else "N/A"
    upside_str = f"+{upside:.1f}%" if upside and upside > 0 else (f"{upside:.1f}%" if upside else "N/A")

    left_content = [
        Paragraph(f"<b>{company}</b>", STYLES["title"]),
        Spacer(1, 2),
        Paragraph(f"{ticker}  |  {exchange}  |  {cap_type}  |  {sector}", STYLES["subtitle"]),
        Spacer(1, 2),
        Paragraph(f"Report Date: {report_dt}  |  Analyst: {analyst}", STYLES["subtitle"]),
    ]

    price_box = [
        [Paragraph(f"<b>CMP</b>", ParagraphStyle("ph", fontName="Helvetica-Bold",
                   fontSize=6.5, textColor=colors.HexColor("#B2DFDB")),)],
        [Paragraph(f"<b>{cmp_str}</b>", ParagraphStyle("pv", fontName="Helvetica-Bold",
                   fontSize=11, textColor=WHITE))],
        [Spacer(1, 3)],
        [Paragraph(f"Target: <b>{target_str}</b>", ParagraphStyle("pt", fontName="Helvetica",
                   fontSize=7, textColor=colors.HexColor("#B2DFDB")))],
        [Paragraph(f"Upside: <b>{upside_str}</b>", ParagraphStyle("pu", fontName="Helvetica",
                   fontSize=7, textColor=TEAL_LIGHT))],
        [Spacer(1, 3)],
        [Paragraph(f"<b>{period}</b>", ParagraphStyle("pp", fontName="Helvetica",
                   fontSize=6, textColor=colors.HexColor("#B2DFDB")))],
    ]

    rating_cell = Table(
        [[Paragraph(f"<b>{rating}</b>", ParagraphStyle("rp", fontName="Helvetica-Bold",
                    fontSize=14, textColor=WHITE, alignment=TA_CENTER))]],
        colWidths=[2.5 * cm],
    )
    rating_cell.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), rating_color),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), [3, 3, 3, 3]),
    ]))

    price_tbl = Table(price_box, colWidths=[3.2 * cm])
    price_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
    ]))

    right_col = Table([[rating_cell, price_tbl]], colWidths=[2.8 * cm, 3.6 * cm])
    right_col.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))

    left_tbl = Table([[c] for c in left_content], colWidths=[CONTENT_W - 7 * cm])
    left_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    header_data = [[left_tbl, right_col]]
    header_tbl = Table(header_data, colWidths=[CONTENT_W - 7 * cm, 7 * cm])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BG_HEADER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4))


def _build_company_data_panel(data: Dict, story: List) -> None:
    """Two-column panel: Company Data (left) + Shareholding/Price Performance (right)."""

    # --- Company Data ---
    cd_rows = [
        ["Market Cap (Rs. cr)", _na(data.get("market_cap"))],
        ["52 Week High – Low (Rs.)", f"{_na(data.get('week_52_high'))} – {_na(data.get('week_52_low'))}"],
        ["Enterprise Value (Rs. cr)", _na(data.get("enterprise_value"))],
        ["Outstanding Shares (cr)", _na(data.get("outstanding_shares"))],
        ["Free Float (%)", _na(data.get("free_float"))],
        ["Dividend Yield (%)", _na(data.get("dividend_yield"))],
        ["6M Avg Volume (cr)", _na(data.get("avg_volume_6m"))],
        ["Beta", _na(data.get("beta"))],
        ["Face Value (Rs.)", _na(data.get("face_value"))],
    ]
    cd_table_data = [["Company Data", ""]] + cd_rows
    cd_col_w = [3.8 * cm, 2.8 * cm]
    cd_tbl = Table(cd_table_data, colWidths=cd_col_w, repeatRows=1)
    cd_tbl.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7),
        ("SPAN",          (0, 0), (-1, 0)),
        ("ALIGN",         (0, 0), (-1, 0), "LEFT"),
        # Data rows
        ("FONTSIZE",      (0, 1), (-1, -1), 6.5),
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica"),
        ("FONTNAME",      (1, 1), (1, -1), "Helvetica-Bold"),
        ("ALIGN",         (1, 1), (1, -1), "RIGHT"),
        ("TEXTCOLOR",     (0, 1), (-1, -1), TEXT_DARK),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
    ]))

    # --- Shareholding pattern ---
    sh_data = data.get("shareholding", [])
    q_labels = data.get("sh_quarter_labels", ["Q3FY25", "Q4FY25", "Q1FY26"])
    sh_header = [["Category"] + q_labels]
    sh_rows = []
    for row in sh_data:
        sh_rows.append([
            row.get("category", ""),
            row.get("q1", "N/A"),
            row.get("q2", "N/A"),
            row.get("q3", "N/A"),
        ])
    if not sh_rows:
        sh_rows = [["N/A", "N/A", "N/A", "N/A"]]

    sh_header_row = [["Shareholding (%)"] + [""] * 3]
    sh_table_data = sh_header_row + sh_header + sh_rows
    sh_col_w = [2.5 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm]
    sh_tbl = Table(sh_table_data, colWidths=sh_col_w, repeatRows=2)
    sh_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7),
        ("SPAN",          (0, 0), (-1, 0)),
        ("BACKGROUND",    (0, 1), (-1, 1), TEAL_DARK),
        ("TEXTCOLOR",     (0, 1), (-1, 1), WHITE),
        ("FONTNAME",      (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 1), (-1, 1), 6),
        ("FONTSIZE",      (0, 2), (-1, -1), 6.5),
        ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS",(0, 2), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))

    # --- Price Performance ---
    pp_data = [
        ["Price Performance", "3 Month", "6 Month", "1 Year"],
        ["Absolute Return", data.get("price_perf_3m","N/A"), data.get("price_perf_6m","N/A"), data.get("price_perf_1y","N/A")],
        ["Absolute Sensex", data.get("sensex_3m","N/A"), data.get("sensex_6m","N/A"), data.get("sensex_1y","N/A")],
    ]
    pp_tbl = Table(pp_data, colWidths=sh_col_w, repeatRows=1)
    pp_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 6.5),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))

    right_col_data = [[sh_tbl], [Spacer(1, 4)], [pp_tbl]]
    right_col = Table(right_col_data, colWidths=[6.2 * cm])

    # Combine
    gap = 0.4 * cm
    left_w  = 6.8 * cm
    right_w = 6.2 * cm
    spacer_w = CONTENT_W - left_w - right_w

    combined = Table(
        [[cd_tbl, Spacer(spacer_w, 1), right_col]],
        colWidths=[left_w, spacer_w, right_w]
    )
    combined.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    story.append(combined)
    story.append(Spacer(1, 6))


def _build_annual_financials_table(data: Dict, story: List) -> None:
    """Annual financial summary table matching Geojit layout."""
    story.append(_section_header("Financial Summary (Annual)"))
    story.append(Spacer(1, 3))

    af = data.get("annual_financials", [])
    if not af:
        story.append(Paragraph("Financial data not available.", STYLES["body"]))
        story.append(Spacer(1, 4))
        return

    year_headers = [row.get("year", "") for row in af]
    metrics = [
        ("Sales (Rs. cr)",       "sales"),
        ("Growth (%)",           "sales_growth"),
        ("EBITDA",               "ebitda"),
        ("EBITDA Margin (%)",    "ebitda_margin"),
        ("PAT Adjusted",         "pat"),
        ("PAT Growth (%)",       "pat_growth"),
        ("Adj. EPS (Rs.)",       "eps"),
        ("EPS Growth (%)",       "eps_growth"),
        ("P/E (x)",              "pe"),
        ("P/B (x)",              "pb"),
        ("EV/EBITDA (x)",        "ev_ebitda"),
        ("ROE (%)",              "roe"),
        ("D/E (x)",              "de"),
    ]

    header_row = [Paragraph("<b>Y.E. March (Rs. cr)</b>", STYLES["table_label_bold"])]
    for yr in year_headers:
        header_row.append(Paragraph(f"<b>{yr}</b>", STYLES["table_header"]))

    rows = [header_row]
    for label, key in metrics:
        row = [Paragraph(label, STYLES["table_label"])]
        for yr_data in af:
            val = _na(yr_data.get(key))
            row.append(Paragraph(val, STYLES["table_cell"]))
        rows.append(row)

    n_cols = 1 + len(af)
    label_w = 3.6 * cm
    data_w  = (CONTENT_W - label_w) / max(len(af), 1)
    col_ws  = [label_w] + [data_w] * len(af)

    tbl = Table(rows, colWidths=col_ws, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        # Highlight key rows
        ("FONTNAME",      (0, 1), (0, 1),   "Helvetica-Bold"),
        ("FONTNAME",      (0, 5), (0, 5),   "Helvetica-Bold"),
        ("FONTNAME",      (0, 7), (0, 7),   "Helvetica-Bold"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))


def _build_quarterly_table(data: Dict, story: List) -> None:
    """Quarterly financials comparison table."""
    story.append(_section_header("Quarterly Financials (Consolidated)"))
    story.append(Spacer(1, 3))

    qf = data.get("quarterly_financials", [])
    if not qf:
        story.append(Paragraph("Quarterly data not available.", STYLES["body"]))
        story.append(Spacer(1, 4))
        return

    q_curr  = data.get("q_curr_label", "Q-Curr")
    q_prev  = data.get("q_prev_yr_label", "Q-PrevYr")
    q_seq   = data.get("q_prev_seq_label", "Q-Seq")

    col_headers = [
        Paragraph("<b>Rs. cr</b>", STYLES["table_label_bold"]),
        Paragraph(f"<b>{q_curr}</b>", STYLES["table_header"]),
        Paragraph(f"<b>{q_prev}</b>", STYLES["table_header"]),
        Paragraph("<b>YoY Growth (%)</b>", STYLES["table_header"]),
        Paragraph(f"<b>{q_seq}</b>", STYLES["table_header"]),
        Paragraph("<b>QoQ Growth (%)</b>", STYLES["table_header"]),
    ]

    rows = [col_headers]
    for row in qf:
        rows.append([
            Paragraph(row.get("metric", ""), STYLES["table_label"]),
            Paragraph(_na(row.get("q_curr")),      STYLES["table_cell"]),
            Paragraph(_na(row.get("q_prev_yr")),   STYLES["table_cell"]),
            Paragraph(_na(row.get("yoy_growth")),  STYLES["table_cell"]),
            Paragraph(_na(row.get("q_prev_seq")),  STYLES["table_cell"]),
            Paragraph(_na(row.get("qoq_growth")),  STYLES["table_cell"]),
        ])

    col_ws = [3.2 * cm, 1.7 * cm, 1.7 * cm, 2.0 * cm, 1.7 * cm, 2.0 * cm]
    tbl = Table(rows, colWidths=col_ws, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))


def _build_narrative_section(title: str, text: str, story: List) -> None:
    story.append(_section_header(title))
    story.append(Spacer(1, 3))
    if not text or text.strip() == "":
        story.append(Paragraph("Information not available.", STYLES["body"]))
    else:
        for para in text.split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), STYLES["body"]))
    story.append(Spacer(1, 5))


def _build_bullet_section(title: str, bullets: List[str], story: List) -> None:
    story.append(_section_header(title))
    story.append(Spacer(1, 3))
    if not bullets:
        story.append(Paragraph("No items available.", STYLES["body"]))
    else:
        for bullet in bullets:
            if bullet.strip():
                story.append(Paragraph(
                    f"<bullet>\u25cf</bullet> {bullet.strip()}", STYLES["bullet"]
                ))
    story.append(Spacer(1, 5))


def _build_charts_section(charts: Dict[str, bytes], story: List) -> None:
    if not charts:
        return

    story.append(_section_header("Charts & Trends"))
    story.append(Spacer(1, 4))

    chart_items = list(charts.items())
    # Place two charts per row
    i = 0
    while i < len(chart_items):
        row = []
        for j in range(2):
            if i + j < len(chart_items):
                name, img_bytes = chart_items[i + j]
                try:
                    img_reader = ImageReader(io.BytesIO(img_bytes))
                    img = Image(io.BytesIO(img_bytes),
                                width=(CONTENT_W / 2) - 0.3 * cm,
                                height=4.5 * cm)
                    row.append(img)
                except Exception as e:
                    logger.warning(f"Chart {name} failed to embed: {e}")
                    row.append(Paragraph("Chart unavailable", STYLES["body"]))
            else:
                row.append(Spacer(1, 1))
        tbl = Table([row], colWidths=[(CONTENT_W / 2) - 0.1 * cm] * 2)
        tbl.setStyle(TableStyle([
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING",(0, 0), (-1, -1), 3),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 4))
        i += 2


def _build_estimate_changes_table(data: Dict, story: List) -> None:
    ec = data.get("estimate_changes", [])
    if not ec:
        return

    annual_data = data.get("annual_financials", [])
    fy_years = [r.get("year", "") for r in annual_data if "E" in str(r.get("year", ""))]
    fy1 = fy_years[0] if len(fy_years) > 0 else "FY26E"
    fy2 = fy_years[1] if len(fy_years) > 1 else "FY27E"

    story.append(_section_header("Change in Estimates"))
    story.append(Spacer(1, 3))

    headers = [
        Paragraph("<b>Year / Rs. cr</b>", STYLES["table_label_bold"]),
        Paragraph(f"<b>Old {fy1}</b>", STYLES["table_header"]),
        Paragraph(f"<b>Old {fy2}</b>", STYLES["table_header"]),
        Paragraph(f"<b>New {fy1}</b>", STYLES["table_header"]),
        Paragraph(f"<b>New {fy2}</b>", STYLES["table_header"]),
        Paragraph(f"<b>Chg. {fy1}</b>", STYLES["table_header"]),
        Paragraph(f"<b>Chg. {fy2}</b>", STYLES["table_header"]),
    ]
    rows = [headers]
    for row in ec:
        rows.append([
            Paragraph(row.get("metric", ""), STYLES["table_label"]),
            Paragraph(_na(row.get("old_fy1")), STYLES["table_cell"]),
            Paragraph(_na(row.get("old_fy2")), STYLES["table_cell"]),
            Paragraph(_na(row.get("new_fy1")), STYLES["table_cell"]),
            Paragraph(_na(row.get("new_fy2")), STYLES["table_cell"]),
            Paragraph(_na(row.get("chg_fy1")), STYLES["table_cell"]),
            Paragraph(_na(row.get("chg_fy2")), STYLES["table_cell"]),
        ])

    col_ws = [3.0*cm, 1.7*cm, 1.7*cm, 1.7*cm, 1.7*cm, 1.6*cm, 1.6*cm]
    tbl = Table(rows, colWidths=col_ws, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))


def _build_recommendation_history(data: Dict, story: List) -> None:
    rh = data.get("recommendation_history", [])
    if not rh:
        return

    story.append(_section_header("Recommendation Summary (Last 3 Years)"))
    story.append(Spacer(1, 3))

    headers = [
        Paragraph("<b>Date</b>", STYLES["table_label_bold"]),
        Paragraph("<b>Rating</b>", STYLES["table_header"]),
        Paragraph("<b>Target (Rs.)</b>", STYLES["table_header"]),
    ]
    rows = [headers]
    for rec in rh:
        rating = rec.get("rating", "N/A")
        rc = _rating_color(rating)
        rows.append([
            Paragraph(rec.get("date", "N/A"), STYLES["table_cell"]),
            Paragraph(f"<b>{rating}</b>", ParagraphStyle(
                "rrt", fontName="Helvetica-Bold", fontSize=7,
                textColor=rc, alignment=TA_CENTER)),
            Paragraph(_na(rec.get("target")), STYLES["table_cell"]),
        ])

    col_ws = [4 * cm, 3 * cm, 4 * cm]
    tbl = Table(rows, colWidths=col_ws, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTSIZE",      (0, 0), (-1, -1), 7),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))


def _build_disclaimer(story: List) -> None:
    story.append(HRFlowable(width=CONTENT_W, thickness=1, color=ORANGE))
    story.append(Spacer(1, 4))
    story.append(_section_header("Investment Rating Criteria"))
    story.append(Spacer(1, 3))

    rating_rows = [
        ["Rating", "Large Caps", "Mid Caps", "Small Caps"],
        ["Buy", "Upside above 10%", "Upside above 15%", "Upside above 20%"],
        ["Accumulate", "–", "Upside 10%–15%", "Upside 10%–20%"],
        ["Hold", "Upside 0%–10%", "Upside 0%–10%", "Upside 0%–10%"],
        ["Reduce/Sell", "Downside > 0%", "Downside > 0%", "Downside > 0%"],
    ]
    tbl = Table(rating_rows, colWidths=[2.5*cm, 3.5*cm, 3.5*cm, 3.5*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), TEAL_DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 6.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 6))

    disclaimer_text = (
        "<b>DISCLAIMER &amp; DISCLOSURES:</b> This report has been prepared by the Research Team. "
        "Certification: The views expressed in this research report reflect our personal views about "
        "the subject issuer or securities. This report is for informational purposes only and does not "
        "constitute investment advice. Investors should conduct their own research before making investment "
        "decisions. Past performance is not indicative of future results. The information contained herein "
        "has been obtained from sources believed to be reliable, but we do not guarantee its accuracy or completeness. "
        "SEBI Reg. No: INH200000345. For general disclosures: www.geojit.com"
    )
    story.append(Paragraph(disclaimer_text, STYLES["disclaimer"]))


# ---------------------------------------------------------------------------
# Main PDF generation function
# ---------------------------------------------------------------------------

def generate_pdf(data: Dict, charts: Dict[str, bytes]) -> bytes:
    """
    Generate the complete research report PDF.

    Args:
        data:   Validated template fields dict
        charts: Dict of {chart_name: png_bytes}

    Returns:
        PDF as bytes
    """
    buf = io.BytesIO()
    company = data.get("company_name", "Company")

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T + 1.0 * cm,   # room for header bar
        bottomMargin=MARGIN_B + 0.6 * cm,
        title=f"{company} Research Report",
        author="Geojit Research",
        subject="Equity Research Report",
    )

    frame = Frame(
        MARGIN_L, MARGIN_B + 0.6 * cm,
        PAGE_W - MARGIN_L - MARGIN_R,
        PAGE_H - MARGIN_T - MARGIN_B - 1.6 * cm,
        id="main"
    )

    def _header_footer(canvas, doc):
        _add_page_header_footer(canvas, doc, data)

    template = PageTemplate(id="main", frames=[frame],
                            onPage=_header_footer)
    doc.addPageTemplates([template])

    # Build story
    story = []

    # 1. Cover header
    _build_cover_header(data, story)

    # 2. Company data panel
    _build_company_data_panel(data, story)

    # 3. Company description
    _build_narrative_section(
        "Company Overview",
        data.get("company_description", ""),
        story
    )

    # 4. Key highlights / investment rationale
    _build_bullet_section(
        "Key Highlights",
        data.get("investment_rationale", []),
        story
    )

    # 5. Annual financials table
    _build_annual_financials_table(data, story)

    # 6. Charts
    _build_charts_section(charts, story)

    # 7. Quarterly financials
    _build_quarterly_table(data, story)

    # 8. Estimate changes
    _build_estimate_changes_table(data, story)

    # 9. Valuation & Outlook
    _build_narrative_section(
        "Outlook & Valuation",
        data.get("valuation_outlook", ""),
        story
    )

    # 10. Risks
    _build_bullet_section(
        "Key Risks",
        data.get("risks", []),
        story
    )

    # 11. Recommendation history
    _build_recommendation_history(data, story)

    # 12. Disclaimer
    _build_disclaimer(story)

    doc.build(story)
    buf.seek(0)
    return buf.read()
