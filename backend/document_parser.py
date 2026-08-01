"""
document_parser.py
==================
Extracts raw text from uploaded documents.
Supports: PDF, CSV, TXT, XLSX
"""

import io
import logging
from pathlib import Path
from typing import Tuple

import pdfplumber

logger = logging.getLogger(__name__)


def parse_document(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Parse an uploaded document and return (raw_text, format_hint).

    Args:
        file_bytes: Raw bytes of the uploaded file
        filename:   Original filename (used for extension detection)

    Returns:
        (raw_text, format_hint) where format_hint is one of 'pdf','csv','txt','xlsx'
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_bytes), "pdf"
    elif ext in (".csv",):
        return _parse_csv(file_bytes), "csv"
    elif ext in (".xlsx", ".xls"):
        return _parse_excel(file_bytes), "xlsx"
    elif ext in (".txt", ".md"):
        return _parse_text(file_bytes), "txt"
    else:
        # Attempt PDF first, fallback to plain text
        try:
            return _parse_pdf(file_bytes), "pdf"
        except Exception:
            return _parse_text(file_bytes), "txt"


def _parse_pdf(file_bytes: bytes) -> str:
    """Extract text from all pages of a PDF."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            text_parts.append(f"--- Page {i+1} ---\n{page_text}")

            # Also extract tables
            tables = page.extract_tables()
            for j, table in enumerate(tables):
                if table:
                    text_parts.append(f"\n[TABLE {j+1}]")
                    for row in table:
                        if row:
                            clean_row = [str(c).strip() if c else "" for c in row]
                            text_parts.append(" | ".join(clean_row))

    return "\n".join(text_parts)


def _parse_csv(file_bytes: bytes) -> str:
    """Return canonical CSV text so structured key/value inputs remain lossless."""
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="replace")


def _parse_excel(file_bytes: bytes) -> str:
    """Parse Excel and return text from all sheets."""
    try:
        import pandas as pd
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        parts = []
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            parts.append(f"=== Sheet: {sheet} ===\n{df.to_string(index=False)}")
        return "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"Excel parse failed: {e}")
        return file_bytes.decode("utf-8", errors="replace")


def _parse_text(file_bytes: bytes) -> str:
    """Decode raw text file."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return file_bytes.decode(enc)
        except Exception:
            continue
    return file_bytes.decode("utf-8", errors="replace")
