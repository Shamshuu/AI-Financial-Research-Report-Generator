"""
ai_extractor.py
===============
Uses Google Gemini to extract structured financial data from raw document text.
Maps extracted data to template_fields.py schema.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict

from google import genai
from google.genai import types

from template_fields import get_defaults
from deterministic_extractor import extract_deterministically

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini Setup
# ---------------------------------------------------------------------------

# Gemini 1.5 Flash was retired. Gemini 2.5 Flash is the current stable,
# text-capable replacement for document extraction. An environment override
# keeps deployments compatible with models enabled for their specific API key.
# Primary model default. An environment override keeps deployments compatible
# with models enabled for their specific API key.
_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def _get_client():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment.")
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Extraction Prompt
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """
You are a financial research analyst AI. Given the raw text extracted from a company's financial document (annual report, quarterly result, earnings PDF, CSV, etc.), extract structured data and return it as a single JSON object.

Company name (user-provided): {company_name}

Document text:
\"\"\"
{document_text}
\"\"\"

Return ONLY a JSON object with the following keys. Use null for any field you cannot find. DO NOT include markdown fences or extra text.

{{
  "company_name": "full legal company name",
  "ticker": "stock ticker",
  "exchange": "NSE or BSE or NSE/BSE",
  "sector": "industry sector",
  "cap_type": "Large Cap / Mid Cap / Small Cap",
  "cmp": current market price as number or null,
  "target_price": analyst target price as number or null,
  "upside_pct": upside percentage as number or null,
  "rating": "BUY / SELL / HOLD / ACCUMULATE or null",
  "report_date": "DD-Mon-YYYY or today's date",
  "analyst_name": "analyst or research team name",
  "investment_period": "12 Months",

  "market_cap": "market cap in cr as string e.g. 1,23,456",
  "week_52_high": "52W high as string",
  "week_52_low": "52W low as string",
  "enterprise_value": "EV in cr as string",
  "outstanding_shares": "shares outstanding in cr",
  "free_float": "free float percentage",
  "dividend_yield": "dividend yield or '-'",
  "beta": "beta value as string",
  "face_value": "face value",
  "avg_volume_6m": "6m average daily volume",

  "sh_quarter_labels": ["Q3FY25", "Q4FY25", "Q1FY26"],
  "shareholding": [
    {{"category": "Promoters", "q1": "XX.X", "q2": "XX.X", "q3": "XX.X"}},
    {{"category": "FIIs", "q1": "XX.X", "q2": "XX.X", "q3": "XX.X"}},
    {{"category": "MFs/Institutions", "q1": "XX.X", "q2": "XX.X", "q3": "XX.X"}},
    {{"category": "Public", "q1": "XX.X", "q2": "XX.X", "q3": "XX.X"}},
    {{"category": "Others", "q1": "XX.X", "q2": "XX.X", "q3": "XX.X"}}
  ],

  "price_perf_3m": "return % as string",
  "price_perf_6m": "return % as string",
  "price_perf_1y": "return % as string",
  "sensex_3m": "sensex 3m return as string",
  "sensex_6m": "sensex 6m return as string",
  "sensex_1y": "sensex 1y return as string",

  "company_description": "2-3 paragraph overview of the company's business, products, and market position",
  "investment_rationale": [
    "key highlight bullet 1 (full sentence)",
    "key highlight bullet 2",
    "key highlight bullet 3",
    "key highlight bullet 4",
    "key highlight bullet 5"
  ],
  "valuation_outlook": "2-3 paragraph valuation methodology, outlook, and price target rationale",
  "risks": [
    "risk factor 1",
    "risk factor 2",
    "risk factor 3"
  ],

  "annual_financials": [
    {{
      "year": "FY23A",
      "sales": "value in cr",
      "sales_growth": "% change",
      "ebitda": "value",
      "ebitda_margin": "% margin",
      "pat": "PAT value",
      "pat_growth": "% change",
      "eps": "EPS Rs.",
      "eps_growth": "% change",
      "pe": "P/E multiple",
      "pb": "P/B multiple",
      "ev_ebitda": "EV/EBITDA",
      "roe": "ROE %",
      "de": "D/E ratio"
    }}
  ],

  "quarterly_financials": [
    {{"metric": "Sales", "q_curr": "value", "q_prev_yr": "value", "yoy_growth": "%", "q_prev_seq": "value", "qoq_growth": "%"}},
    {{"metric": "EBITDA", "q_curr": "value", "q_prev_yr": "value", "yoy_growth": "%", "q_prev_seq": "value", "qoq_growth": "%"}},
    {{"metric": "EBITDA Margin (%)", "q_curr": "value", "q_prev_yr": "value", "yoy_growth": "bps", "q_prev_seq": "value", "qoq_growth": "bps"}},
    {{"metric": "EBIT", "q_curr": "value", "q_prev_yr": "value", "yoy_growth": "%", "q_prev_seq": "value", "qoq_growth": "%"}},
    {{"metric": "PBT", "q_curr": "value", "q_prev_yr": "value", "yoy_growth": "%", "q_prev_seq": "value", "qoq_growth": "%"}},
    {{"metric": "Reported PAT", "q_curr": "value", "q_prev_yr": "value", "yoy_growth": "%", "q_prev_seq": "value", "qoq_growth": "%"}},
    {{"metric": "Adj. EPS (Rs.)", "q_curr": "value", "q_prev_yr": "value", "yoy_growth": "%", "q_prev_seq": "value", "qoq_growth": "%"}}
  ],
  "q_curr_label": "Q1FY26",
  "q_prev_yr_label": "Q1FY25",
  "q_prev_seq_label": "Q4FY25",

  "estimate_changes": [
    {{"metric": "Revenue", "old_fy1": "value", "old_fy2": "value", "new_fy1": "value", "new_fy2": "value", "chg_fy1": "%", "chg_fy2": "%"}},
    {{"metric": "EBITDA", "old_fy1": "value", "old_fy2": "value", "new_fy1": "value", "new_fy2": "value", "chg_fy1": "%", "chg_fy2": "%"}},
    {{"metric": "Adj. PAT", "old_fy1": "value", "old_fy2": "value", "new_fy1": "value", "new_fy2": "value", "chg_fy1": "%", "chg_fy2": "%"}},
    {{"metric": "EPS", "old_fy1": "value", "old_fy2": "value", "new_fy1": "value", "new_fy2": "value", "chg_fy1": "%", "chg_fy2": "%"}}
  ],

  "recommendation_history": [
    {{"date": "DD-Mon-YY", "rating": "BUY/HOLD/SELL", "target": "price"}}
  ]
}}

Be thorough. Extract as many data points as possible from the document. For missing data, use null. Generate professional analyst-quality narrative for company_description, investment_rationale, valuation_outlook, and risks based on the data available.
"""


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extract_fields(company_name: str, document_text: str) -> Dict[str, Any]:
    """
    Call Gemini to extract all template fields from document text.

    Returns a dict ready to be merged with defaults via validate_and_fill().
    """
    # Truncate very long documents to fit context window
    max_chars = 50000
    if len(document_text) > max_chars:
        doc_text = document_text[:max_chars] + "\n\n[... document truncated for length ...]"
    else:
        doc_text = document_text

    prompt = _EXTRACTION_PROMPT.format(
        company_name=company_name,
        document_text=doc_text
    )

    models_to_try = [_MODEL_NAME, "gemini-3.6-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    # Deduplicate preserving order
    seen = set()
    models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

    client = _get_client()
    response = None
    last_err = None

    for model_name in models_to_try:
        try:
            logger.info(f"Attempting extraction with model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
            )
            if response and response.text:
                break
        except Exception as e:
            logger.warning(f"Model {model_name} extraction failed: {e}")
            last_err = e

    if not response or not response.text:
        logger.error(f"Gemini extraction failed across all candidate models: {last_err}")
        return _fallback_extraction(company_name, document_text)

    try:
        raw = response.text.strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        logger.info(f"Extracted {len(data)} fields for {company_name}")

        # Set report date if not found
        if not data.get("report_date"):
            data["report_date"] = datetime.now().strftime("%d-%b-%Y")

        # Ensure company name from UI overrides extracted
        if company_name and company_name.strip():
            data["company_name"] = company_name.strip()

        # Preserve deterministic fields if the model omitted them. This reduces
        # hallucination risk for source values that are straightforward to read.
        deterministic = extract_deterministically(company_name, document_text)
        return {**deterministic, **{k: v for k, v in data.items() if v not in (None, "", [], {})}}

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw response: {raw[:500] if 'raw' in locals() else 'N/A'}")
        return _fallback_extraction(company_name, document_text)
    except Exception as e:
        logger.error(f"Gemini extraction processing failed: {e}")
        return _fallback_extraction(company_name, document_text)


def _fallback_extraction(company_name: str, document_text: str) -> Dict[str, Any]:
    """
    Minimal fallback when AI extraction fails.
    Attempts basic regex extraction of key numbers.
    """
    logger.warning("Using deterministic extraction fallback")
    data = extract_deterministically(company_name, document_text)
    # The UI value is authoritative. In particular, parsed PDF text often
    # begins with a page marker such as "--- Page 1 ---", not a company name.
    if company_name and company_name.strip():
        data["company_name"] = company_name.strip()
    else:
        data.setdefault("company_name", "N/A")
    data.setdefault("report_date", datetime.now().strftime("%d-%b-%Y"))
    return data
