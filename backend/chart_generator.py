"""
chart_generator.py
==================
Generates charts as PNG byte streams for embedding in the PDF report.
All charts match the Geojit report visual style.
"""

import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).parent / ".mplconfig"))

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand colors (Geojit teal / dark theme)
# ---------------------------------------------------------------------------
TEAL       = "#006D77"
TEAL_LIGHT = "#83C5BE"
ORANGE     = "#E29578"
DARK_BG    = "#F8FAFB"
GRID_COLOR = "#DDE3E9"
TEXT_COLOR = "#1A2340"
BAR_COLOR  = "#006D77"
LINE_COLOR = "#E29578"


def _fig_to_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Chart 1: Revenue & PAT Bar + Line Combo
# ---------------------------------------------------------------------------

def revenue_pat_chart(annual_financials: List[Dict]) -> Optional[bytes]:
    """
    Dual-axis bar (Revenue) + line (PAT) chart across fiscal years.
    """
    if not annual_financials:
        return None

    years, sales, pat = [], [], []
    for row in annual_financials:
        years.append(row.get("year", ""))
        try:
            s = str(row.get("sales", "0")).replace(",", "").replace("N/A", "0")
            sales.append(float(s) if s else 0)
        except (ValueError, TypeError):
            sales.append(0)
        try:
            p = str(row.get("pat", "0")).replace(",", "").replace("N/A", "0")
            pat.append(float(p) if p else 0)
        except (ValueError, TypeError):
            pat.append(0)

    if not any(sales):
        return None

    x = np.arange(len(years))
    width = 0.5

    fig, ax1 = plt.subplots(figsize=(7, 3.5))
    fig.patch.set_facecolor(DARK_BG)
    ax1.set_facecolor(DARK_BG)

    bars = ax1.bar(x, sales, width, color=TEAL, alpha=0.85, zorder=3, label="Revenue (Rs. cr)")
    ax1.set_ylabel("Revenue (Rs. cr)", fontsize=8, color=TEXT_COLOR, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=TEXT_COLOR, labelsize=7)
    ax1.set_xticks(x)
    ax1.set_xticklabels(years, fontsize=8, color=TEXT_COLOR)
    ax1.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5, zorder=0)
    ax1.set_axisbelow(True)
    for spine in ax1.spines.values():
        spine.set_visible(False)

    # PAT line on secondary axis
    ax2 = ax1.twinx()
    ax2.plot(x, pat, color=LINE_COLOR, marker="o", linewidth=2,
             markersize=5, zorder=4, label="PAT (Rs. cr)")
    ax2.set_ylabel("PAT (Rs. cr)", fontsize=8, color=LINE_COLOR, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=LINE_COLOR, labelsize=7)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    # Legend
    h1 = mpatches.Patch(color=TEAL, label="Revenue")
    h2 = mpatches.Patch(color=LINE_COLOR, label="PAT")
    ax1.legend(handles=[h1, h2], loc="upper left", fontsize=7,
               framealpha=0.8, edgecolor=GRID_COLOR)

    ax1.set_title("Revenue & PAT Trend", fontsize=9, fontweight="bold",
                  color=TEXT_COLOR, pad=8)
    plt.tight_layout(pad=0.5)
    return _fig_to_bytes(fig)


# ---------------------------------------------------------------------------
# Chart 2: EBITDA Margin Trend (Line)
# ---------------------------------------------------------------------------

def ebitda_margin_chart(annual_financials: List[Dict]) -> Optional[bytes]:
    """Line chart of EBITDA margin % across fiscal years."""
    if not annual_financials:
        return None

    years, margins = [], []
    for row in annual_financials:
        years.append(row.get("year", ""))
        try:
            m = str(row.get("ebitda_margin", "0")).replace("%", "").replace(",", "").replace("N/A", "0")
            margins.append(float(m) if m else 0)
        except (ValueError, TypeError):
            margins.append(0)

    if not any(margins):
        return None

    x = np.arange(len(years))
    fig, ax = plt.subplots(figsize=(7, 3.2))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    ax.fill_between(x, margins, alpha=0.15, color=TEAL, zorder=2)
    ax.plot(x, margins, color=TEAL, marker="o", linewidth=2.5,
            markersize=6, zorder=3)

    for i, (xi, m) in enumerate(zip(x, margins)):
        ax.annotate(f"{m:.1f}%", (xi, m), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=7, color=TEAL, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=8, color=TEXT_COLOR)
    ax.set_ylabel("EBITDA Margin (%)", fontsize=8, color=TEXT_COLOR, fontweight="bold")
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", labelsize=7, colors=TEXT_COLOR)
    ax.set_title("EBITDA Margin Trend (%)", fontsize=9, fontweight="bold",
                 color=TEXT_COLOR, pad=8)
    plt.tight_layout(pad=0.5)
    return _fig_to_bytes(fig)


# ---------------------------------------------------------------------------
# Chart 3: Revenue & GOV / Quarterly Revenue Bar
# ---------------------------------------------------------------------------

def quarterly_revenue_chart(quarterly_financials: List[Dict],
                             q_labels: List[str]) -> Optional[bytes]:
    """Bar chart comparing revenue across the three quarterly periods."""
    if not quarterly_financials:
        return None

    sales_row = next((r for r in quarterly_financials
                      if "sales" in r.get("metric", "").lower()), None)
    if not sales_row:
        return None

    def _v(val):
        try:
            return float(str(val).replace(",", "").replace("N/A", "0"))
        except (ValueError, TypeError):
            return 0.0

    values = [
        _v(sales_row.get("q_curr", 0)),
        _v(sales_row.get("q_prev_yr", 0)),
        _v(sales_row.get("q_prev_seq", 0)),
    ]
    labels = q_labels if len(q_labels) == 3 else ["Q-Curr", "Q-PrevYr", "Q-Seq"]

    fig, ax = plt.subplots(figsize=(5, 3.2))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    colors = [TEAL, TEAL_LIGHT, ORANGE]
    bars = ax.bar(labels, values, color=colors, width=0.5, zorder=3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.01,
                f"{val:,.0f}", ha="center", va="bottom", fontsize=7, color=TEXT_COLOR,
                fontweight="bold")

    ax.set_ylabel("Rs. cr", fontsize=8, color=TEXT_COLOR, fontweight="bold")
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", labelsize=8, colors=TEXT_COLOR)
    ax.set_title("Quarterly Revenue Comparison", fontsize=9, fontweight="bold",
                 color=TEXT_COLOR, pad=8)
    plt.tight_layout(pad=0.5)
    return _fig_to_bytes(fig)


# ---------------------------------------------------------------------------
# Chart 4: Shareholding Pie
# ---------------------------------------------------------------------------

def shareholding_pie_chart(shareholding: List[Dict],
                            quarter_idx: int = 2) -> Optional[bytes]:
    """Pie chart of the most recent quarter's shareholding pattern."""
    if not shareholding:
        return None

    key = ["q1", "q2", "q3"][min(quarter_idx, 2)]
    labels, sizes = [], []
    for row in shareholding:
        cat = row.get("category", "")
        try:
            val = float(str(row.get(key, "0")).replace("%", "").replace("N/A", "0"))
        except (ValueError, TypeError):
            val = 0.0
        if val > 0:
            labels.append(cat)
            sizes.append(val)

    if not sizes:
        return None

    pie_colors = [TEAL, TEAL_LIGHT, ORANGE, "#8ECAE6", "#219EBC"]
    fig, ax = plt.subplots(figsize=(4, 3.2))
    fig.patch.set_facecolor(DARK_BG)

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=pie_colors[:len(sizes)],
        autopct="%1.1f%%", startangle=90,
        textprops={"fontsize": 7, "color": TEXT_COLOR},
        pctdistance=0.75, wedgeprops={"linewidth": 0.5, "edgecolor": "white"}
    )
    for at in autotexts:
        at.set_fontsize(6.5)
        at.set_color("white")
        at.set_fontweight("bold")

    ax.set_title("Shareholding Pattern", fontsize=9, fontweight="bold",
                 color=TEXT_COLOR, pad=5)
    plt.tight_layout(pad=0.3)
    return _fig_to_bytes(fig)


# ---------------------------------------------------------------------------
# Generate all charts — returns dict of chart_name → bytes
# ---------------------------------------------------------------------------

def generate_all_charts(data: Dict) -> Dict[str, bytes]:
    """Generate all charts for the report. Returns {name: png_bytes}."""
    charts = {}

    af = data.get("annual_financials", [])
    qf = data.get("quarterly_financials", [])
    sh = data.get("shareholding", [])
    q_labels = [
        data.get("q_curr_label", "Q-Curr"),
        data.get("q_prev_yr_label", "Q-PrevYr"),
        data.get("q_prev_seq_label", "Q-Seq"),
    ]

    try:
        c = revenue_pat_chart(af)
        if c:
            charts["revenue_pat"] = c
    except Exception as e:
        logger.warning(f"revenue_pat_chart failed: {e}")

    try:
        c = ebitda_margin_chart(af)
        if c:
            charts["ebitda_margin"] = c
    except Exception as e:
        logger.warning(f"ebitda_margin_chart failed: {e}")

    try:
        c = quarterly_revenue_chart(qf, q_labels)
        if c:
            charts["quarterly_revenue"] = c
    except Exception as e:
        logger.warning(f"quarterly_revenue_chart failed: {e}")

    try:
        c = shareholding_pie_chart(sh)
        if c:
            charts["shareholding_pie"] = c
    except Exception as e:
        logger.warning(f"shareholding_pie_chart failed: {e}")

    logger.info(f"Generated {len(charts)} charts: {list(charts.keys())}")
    return charts
