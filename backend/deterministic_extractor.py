"""Deterministic extraction for structured CSVs and common research-note text.

The LLM remains the preferred extractor, but this module makes the product
useful (and testable) without an API key.  It deliberately only derives values
that are explicitly present in the uploaded document.
"""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List


def _clean(value: str) -> str:
    return value.strip().replace("\u2014", "-").replace("â€”", "-")


def _number(value: str) -> Any:
    value = _clean(value).replace("Rs.", "").replace("Rs", "").replace(",", "")
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return _clean(value)


def extract_deterministically(company_name: str, document_text: str) -> Dict[str, Any]:
    """Return explicitly recoverable report fields, or an empty dict."""
    if re.search(r"(?im)^section\s*,\s*field\s*,\s*value\s*$", document_text):
        return _from_key_value_csv(company_name, document_text)
    return _from_research_text(company_name, document_text)


def _from_key_value_csv(company_name: str, text: str) -> Dict[str, Any]:
    rows = list(csv.DictReader(io.StringIO(text)))
    data: Dict[str, Any] = {"company_name": company_name}
    annual: Dict[str, Dict[str, Any]] = defaultdict(dict)
    shareholding: Dict[str, Dict[str, Any]] = defaultdict(dict)
    highlights, risks = [], []

    for row in rows:
        section, field, value = (_clean(row.get(k, "")) for k in ("section", "field", "value"))
        if not field:
            continue
        if section in {"identification", "metrics"}:
            data[field] = _number(value) if field in {"cmp", "target_price", "upside_pct"} else value
        elif section == "annual":
            match = re.match(r"(FY\d{2}[AE])_(.+)", field)
            if match:
                annual[match.group(1)][match.group(2)] = value
        elif section == "quarterly":
            # handled after all rows are read
            data.setdefault("_quarterly_source", {})[field] = value
        elif section == "shareholding":
            match = re.match(r"(.+)_(Q[1-4]FY\d{2})$", field)
            if match:
                shareholding[match.group(1)][match.group(2)] = value
        elif section == "price_perf":
            key_map = {"stock_3m": "price_perf_3m", "stock_6m": "price_perf_6m", "stock_1y": "price_perf_1y",
                       "sensex_3m": "sensex_3m", "sensex_6m": "sensex_6m", "sensex_1y": "sensex_1y"}
            data[key_map.get(field, field)] = value
        elif section == "narrative":
            (highlights if field.startswith("highlight_") else risks if field.startswith("risk_") else []).append(value)

    data["annual_financials"] = [{"year": year, **values} for year, values in sorted(annual.items())]
    quarters = sorted({quarter for values in shareholding.values() for quarter in values})
    if quarters:
        data["sh_quarter_labels"] = quarters[-3:]
        data["shareholding"] = [{"category": category, **{f"q{i + 1}": values.get(q, "N/A") for i, q in enumerate(quarters[-3:])}}
                                for category, values in shareholding.items()]
    if highlights:
        data["investment_rationale"] = highlights
    if risks:
        data["risks"] = risks
    _build_quarterly_from_flat(data)
    _add_safe_narratives(data)
    return data


def _build_quarterly_from_flat(data: Dict[str, Any]) -> None:
    source = data.pop("_quarterly_source", {})
    if not source:
        return
    quarters = sorted({match.group(1) for key in source for match in [re.match(r"(Q[1-4]FY\d{2})_", key)] if match}, key=_quarter_key)
    if not quarters:
        return
    current = quarters[-1]
    prior_year = f"{current[:2]}FY{int(current[-2:]) - 1:02d}"
    prior_seq = sorted((q for q in quarters if q != current), key=_quarter_key)[-1] if len(quarters) > 1 else ""
    metrics = [("Sales", "sales"), ("EBITDA", "ebitda"), ("Reported PAT", "pat"), ("Adj. EPS (Rs.)", "eps")]
    rows = []
    for label, key in metrics:
        curr = source.get(f"{current}_{key}")
        if curr is None:
            continue
        prev = source.get(f"{prior_year}_{key}", "N/A")
        seq = source.get(f"{prior_seq}_{key}", "N/A")
        rows.append({"metric": label, "q_curr": curr, "q_prev_yr": prev, "q_prev_seq": seq,
                     "yoy_growth": _growth(curr, prev), "qoq_growth": _growth(curr, seq)})
    data.update({"quarterly_financials": rows, "q_curr_label": current,
                 "q_prev_yr_label": prior_year, "q_prev_seq_label": prior_seq})


def _growth(current: Any, prior: Any) -> str:
    try:
        prior_float, current_float = float(str(prior).replace(",", "")), float(str(current).replace(",", ""))
        return "N/A" if prior_float == 0 else f"{(current_float / prior_float - 1) * 100:.1f}%"
    except (ValueError, TypeError):
        return "N/A"


def _quarter_key(quarter: str) -> tuple[int, int]:
    match = re.fullmatch(r"Q([1-4])FY(\d{2})", quarter)
    return (int(match.group(2)), int(match.group(1))) if match else (0, 0)


def _from_research_text(company_name: str, text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"company_name": company_name}
    header = text.splitlines()[:5]
    first = next((line.strip() for line in header if line.strip()), "")
    if first:
        data["company_name"] = re.sub(r"\s*\(.*?\)", "", first).title()
    labels = {"Ticker": "ticker", "Exchange": "exchange", "Sector": "sector", "Cap Type": "cap_type",
              "Market Cap": "market_cap", "Enterprise Value": "enterprise_value", "Outstanding Shares": "outstanding_shares",
              "Free Float": "free_float", "Beta": "beta", "Face Value": "face_value", "Dividend Yield": "dividend_yield",
              "6M Avg Volume": "avg_volume_6m"}
    for label, key in labels.items():
        match = re.search(rf"(?im)^\s*-?\s*{re.escape(label)}\s*:\s*(.+)$", text)
        if match:
            data[key] = _clean(match.group(1))
    for label, key in {"CMP": "cmp", "Target Price": "target_price", "Upside": "upside_pct"}.items():
        match = re.search(rf"(?im)^\s*-?\s*{label}\s*:\s*Rs\.\s*([\d,.]+)|^\s*-?\s*{label}\s*:\s*([\d.]+)%", text)
        if match:
            data[key] = _number(next(v for v in match.groups() if v is not None))
    rating = re.search(r"\b(BUY|HOLD|SELL|ACCUMULATE)\s+rating\b", text, re.I)
    if rating:
        data["rating"] = rating.group(1).upper()
    high_low = re.search(r"52\s*Week\s*High/Low:\s*Rs\.\s*([\d,.]+)\s*/\s*Rs\.\s*([\d,.]+)", text, re.I)
    if high_low:
        data["week_52_high"], data["week_52_low"] = high_low.groups()
    data["annual_financials"] = _parse_annual_table(text)
    data["quarterly_financials"], labels = _parse_quarterly(text)
    data.update(labels)
    data["shareholding"], data["sh_quarter_labels"] = _parse_shareholding(text)
    data.update(_parse_price_performance(text))
    data["investment_rationale"] = _section_bullets(text, "Key Highlights", "Key Risks")
    data["risks"] = _section_bullets(text, "Key Risks", "Recommendation History")
    analyst = re.search(r"Analyst:\s*(.+?)\s*\|\s*Report Date:\s*(.+)", text)
    if analyst:
        data["analyst_name"], data["report_date"] = analyst.groups()
    _add_safe_narratives(data)
    return {key: value for key, value in data.items() if value not in (None, [], "")}


def _parse_annual_table(text: str) -> List[Dict[str, str]]:
    rows = []
    for line in text.splitlines():
        parts = re.split(r"\s{2,}", line.strip())
        if not re.fullmatch(r"FY\d{2}[AE]", parts[0] if parts else "") or len(parts) < 10:
            continue
        keys = ["year", "sales", "sales_growth", "ebitda", "ebitda_margin", "pat", "pat_growth", "eps", "pe", "roe", "de"]
        rows.append(dict(zip(keys, parts)))
    return rows


def _parse_quarterly(text: str):
    header = re.search(r"Quarterly Financials\s+(Q\dFY\d{2})\s+vs\s+(Q\dFY\d{2})\s+vs\s+(Q\dFY\d{2})", text, re.I)
    labels = {"q_curr_label": header.group(1), "q_prev_yr_label": header.group(2), "q_prev_seq_label": header.group(3)} if header else {}
    rows = []
    for line in text.splitlines():
        match = re.match(r"([\w. ]+):\s*([^|]+)\|\s*([^|]+)\|\s*YoY\s*([^|]+)\|\s*Q4FY\d{2}:\s*([^|]+)\|\s*QoQ\s*(.+)", line.strip(), re.I)
        if match:
            metric, curr, prior, yoy, seq, qoq = (v.strip() for v in match.groups())
            rows.append({"metric": metric, "q_curr": curr, "q_prev_yr": prior, "yoy_growth": yoy, "q_prev_seq": seq, "qoq_growth": qoq})
    return rows, labels


def _parse_shareholding(text: str):
    section = re.search(r"Shareholding Pattern \(%\):\s*\n(?:.*\n){0,8}", text, re.I)
    if not section:
        return [], []
    lines = [line.strip() for line in section.group(0).splitlines() if line.strip()]
    if len(lines) < 2:
        return [], []
    quarters = re.findall(r"Q[1-4]FY\d{2}", lines[1])
    rows = []
    for line in lines[2:]:
        match = re.match(r"(.+?)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)$", line)
        if match:
            category, q1, q2, q3 = match.groups()
            rows.append({"category": category, "q1": q1, "q2": q2, "q3": q3})
    return rows, quarters


def _section_bullets(text: str, title: str, next_title: str) -> List[str]:
    match = re.search(rf"{re.escape(title)}:\s*(.*?)(?=\n\s*{re.escape(next_title)}:|\Z)", text, re.S | re.I)
    return [line.strip()[1:].strip() for line in match.group(1).splitlines() if line.strip().startswith("-")] if match else []


def _parse_price_performance(text: str) -> Dict[str, str]:
    match = re.search(r"Price Performance vs Sensex:\s*\n.*?\n\s*Stock Return\s+([^\n]+)\n\s*Sensex\s+([^\n]+)", text, re.I)
    if not match:
        return {}
    stock, sensex = (re.findall(r"[-+]?\d+(?:\.\d+)?%", value) for value in match.groups())
    fields = {}
    for key, value in zip(("price_perf_3m", "price_perf_6m", "price_perf_1y"), stock):
        fields[key] = value
    for key, value in zip(("sensex_3m", "sensex_6m", "sensex_1y"), sensex):
        fields[key] = value
    return fields


def _add_safe_narratives(data: Dict[str, Any]) -> None:
    name = data.get("company_name", "The company")
    sector = data.get("sector", "its operating sector")
    data.setdefault("company_description", f"{name} operates in {sector}. This report summarises only the financial information supplied in the source document.")
    data.setdefault("valuation_outlook", "The valuation outlook should be read alongside the reported financial trend, operating metrics, and risks disclosed in this report. Fields not present in the source are marked N/A.")
