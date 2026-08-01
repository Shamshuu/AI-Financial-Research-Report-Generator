"""
template_fields.py
==================
Single source of truth for all report template fields.
Add new fields here to extend the report for any company/section.
"""

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Field Registry – extend here to add new metrics / sections
# ---------------------------------------------------------------------------

TEMPLATE_FIELDS: Dict[str, Any] = {
    # ── Header / Identification ──────────────────────────────────────────
    "company_name":     {"type": str,   "label": "Company Name",        "default": "N/A"},
    "ticker":           {"type": str,   "label": "Ticker Symbol",       "default": "N/A"},
    "exchange":         {"type": str,   "label": "Exchange",            "default": "NSE/BSE"},
    "sector":           {"type": str,   "label": "Sector",              "default": "N/A"},
    "cap_type":         {"type": str,   "label": "Cap Type",            "default": "Large Cap"},
    "cmp":              {"type": float, "label": "CMP (Rs.)",           "default": 0.0},
    "target_price":     {"type": float, "label": "Target Price (Rs.)",  "default": 0.0},
    "upside_pct":       {"type": float, "label": "Upside (%)",          "default": 0.0},
    "rating":           {"type": str,   "label": "Rating",              "default": "N/A"},
    "report_date":      {"type": str,   "label": "Report Date",         "default": ""},
    "analyst_name":     {"type": str,   "label": "Analyst",             "default": "Research Team"},
    "investment_period":{"type": str,   "label": "Investment Period",   "default": "12 Months"},

    # ── Key Metrics Panel ────────────────────────────────────────────────
    "market_cap":       {"type": str,   "label": "Market Cap (Rs. cr)", "default": "N/A"},
    "week_52_high":     {"type": str,   "label": "52W High (Rs.)",      "default": "N/A"},
    "week_52_low":      {"type": str,   "label": "52W Low (Rs.)",       "default": "N/A"},
    "enterprise_value": {"type": str,   "label": "Enterprise Value (Rs. cr)", "default": "N/A"},
    "outstanding_shares":{"type": str,  "label": "Outstanding Shares (cr)", "default": "N/A"},
    "free_float":       {"type": str,   "label": "Free Float (%)",      "default": "N/A"},
    "dividend_yield":   {"type": str,   "label": "Dividend Yield (%)",  "default": "-"},
    "beta":             {"type": str,   "label": "Beta",                "default": "N/A"},
    "face_value":       {"type": str,   "label": "Face Value (Rs.)",    "default": "N/A"},
    "avg_volume_6m":    {"type": str,   "label": "6M Avg Volume (cr)",  "default": "N/A"},

    # ── Shareholding Table ───────────────────────────────────────────────
    # List of dicts: [{"category": "Promoters", "q1": "55.0", "q2": "55.0", "q3": "55.0"}]
    "shareholding":     {"type": list,  "label": "Shareholding (%)",    "default": []},
    "sh_quarter_labels":{"type": list,  "label": "Shareholding Quarters","default": ["Q3FY25","Q4FY25","Q1FY26"]},

    # ── Price Performance ────────────────────────────────────────────────
    "price_perf_3m":    {"type": str,   "label": "3M Return",           "default": "N/A"},
    "price_perf_6m":    {"type": str,   "label": "6M Return",           "default": "N/A"},
    "price_perf_1y":    {"type": str,   "label": "1Y Return",           "default": "N/A"},
    "sensex_3m":        {"type": str,   "label": "Sensex 3M",           "default": "N/A"},
    "sensex_6m":        {"type": str,   "label": "Sensex 6M",           "default": "N/A"},
    "sensex_1y":        {"type": str,   "label": "Sensex 1Y",           "default": "N/A"},

    # ── Narrative Sections ───────────────────────────────────────────────
    "company_description": {"type": str, "label": "Company Overview",   "default": ""},
    "investment_rationale": {"type": list,"label": "Key Highlights",    "default": []},
    "valuation_outlook":    {"type": str, "label": "Outlook & Valuation","default": ""},
    "risks":                {"type": list,"label": "Key Risks",          "default": []},

    # ── Financial Summary Table (Annual) ─────────────────────────────────
    # List of year-dicts with keys: year, sales, sales_growth, ebitda,
    # ebitda_margin, pat, pat_growth, eps, eps_growth, pe, pb, ev_ebitda, roe, de
    "annual_financials":{"type": list,  "label": "Annual Financials",   "default": []},

    # ── Quarterly Financials Table ───────────────────────────────────────
    # List of row-dicts: metric, q_curr, q_prev_yr, yoy_growth, q_prev_seq, qoq_growth
    "quarterly_financials":{"type": list,"label": "Quarterly Financials","default": []},
    "q_curr_label":     {"type": str,   "label": "Current Quarter",     "default": "Q1FY26"},
    "q_prev_yr_label":  {"type": str,   "label": "Prior Year Quarter",  "default": "Q1FY25"},
    "q_prev_seq_label": {"type": str,   "label": "Prior Sequential Q",  "default": "Q4FY25"},

    # ── Estimate Changes Table ───────────────────────────────────────────
    "estimate_changes": {"type": list,  "label": "Change in Estimates", "default": []},

    # ── Recommendation History ───────────────────────────────────────────
    "recommendation_history": {"type": list,"label": "Recommendation History","default": []},
}


def get_defaults() -> Dict[str, Any]:
    """Return a dict of field_name → default value."""
    return {k: v["default"] for k, v in TEMPLATE_FIELDS.items()}


def get_labels() -> Dict[str, str]:
    """Return a dict of field_name → human-readable label."""
    return {k: v["label"] for k, v in TEMPLATE_FIELDS.items()}


def validate_and_fill(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge extracted data with defaults.
    Missing fields are filled with their default values.
    """
    defaults = get_defaults()
    result = {}
    for field, default in defaults.items():
        val = data.get(field, None)
        if val is None or val == "" or val == [] or val == {}:
            result[field] = default
        else:
            result[field] = val
    return result
