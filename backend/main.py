"""
main.py
=======
FastAPI backend for the AI Financial Research Report Generator.
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from ai_extractor import extract_fields
from chart_generator import generate_all_charts
from document_parser import parse_document
from pdf_generator import generate_pdf
from fillable_template import build_fillable_template
from template_fields import validate_and_fill

# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Financial Research Report Generator",
    description="Generates Geojit-style equity research reports from uploaded financial documents.",
    version="1.0.0",
)

# CORS – allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory for generated PDFs
OUTPUT_DIR = Path(__file__).parent / "generated_reports"
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory job store  {task_id: {"status", "file_path", "error"}}
_jobs: dict = {}

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/api/template")
def get_template():
    """Download the editable AcroForm template used by the report schema."""
    from fastapi.responses import Response
    return Response(build_fillable_template(), media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=equity_research_template.pdf"})


# ---------------------------------------------------------------------------
# Generate report endpoint
# ---------------------------------------------------------------------------

@app.post("/api/generate-report")
async def generate_report(
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Accept a company name + uploaded financial document.
    Returns a task_id. Poll GET /api/report/{task_id} for status.
    """
    if not file.filename:
        raise HTTPException(400, "No file uploaded")
    if not company_name or not company_name.strip():
        raise HTTPException(400, "Company name is required")

    allowed_ext = {".pdf", ".csv", ".txt", ".xlsx", ".xls", ".md"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_ext:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {allowed_ext}")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "Uploaded file is empty")
    task_id = str(uuid.uuid4())
    _jobs[task_id] = {"status": "processing", "file_path": None, "error": None}

    background_tasks.add_task(
        _run_pipeline, task_id, company_name, file_bytes, file.filename
    )

    return JSONResponse({"task_id": task_id, "status": "processing"})


def _run_pipeline(task_id: str, company_name: str,
                  file_bytes: bytes, filename: str) -> None:
    """Background task: parse → extract → chart → PDF."""
    try:
        logger.info(f"[{task_id}] Starting pipeline for {company_name}")

        # 1. Parse document
        logger.info(f"[{task_id}] Parsing document: {filename}")
        raw_text, fmt = parse_document(file_bytes, filename)
        logger.info(f"[{task_id}] Parsed {len(raw_text)} chars from {fmt}")

        # 2. AI extraction
        logger.info(f"[{task_id}] Running AI extraction...")
        extracted = extract_fields(company_name, raw_text)

        # 3. Merge with defaults
        data = validate_and_fill(extracted)

        # 4. Generate charts
        logger.info(f"[{task_id}] Generating charts...")
        charts = generate_all_charts(data)

        # 5. Generate PDF
        logger.info(f"[{task_id}] Generating PDF...")
        pdf_bytes = generate_pdf(data, charts)

        # 6. Save to disk
        safe_name = "".join(c if c.isalnum() else "_" for c in company_name)
        filename_out = f"{safe_name}_{task_id[:8]}_report.pdf"
        out_path = OUTPUT_DIR / filename_out
        out_path.write_bytes(pdf_bytes)

        _jobs[task_id] = {
            "status": "done",
            "file_path": str(out_path),
            "filename": filename_out,
            "error": None,
        }
        logger.info(f"[{task_id}] Done → {out_path}")

    except Exception as e:
        logger.exception(f"[{task_id}] Pipeline failed")
        _jobs[task_id] = {"status": "error", "file_path": None, "error": str(e)}


# ---------------------------------------------------------------------------
# Status & Download endpoint
# ---------------------------------------------------------------------------

@app.get("/api/report/{task_id}")
def get_report(task_id: str):
    """
    Returns the generated PDF if ready, or JSON status if still processing.
    """
    job = _jobs.get(task_id)
    if not job:
        raise HTTPException(404, f"Task {task_id} not found")

    if job["status"] == "processing":
        return JSONResponse({"status": "processing"})

    if job["status"] == "error":
        raise HTTPException(500, f"Report generation failed: {job['error']}")

    file_path = job.get("file_path")
    if not file_path or not Path(file_path).exists():
        raise HTTPException(500, "Report file not found on disk")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=job.get("filename", "report.pdf"),
        headers={"Content-Disposition": f"attachment; filename={job.get('filename', 'report.pdf')}"},
    )


@app.get("/api/report/{task_id}/status")
def get_status(task_id: str):
    """JSON status endpoint."""
    job = _jobs.get(task_id)
    if not job:
        raise HTTPException(404, f"Task {task_id} not found")
    return JSONResponse({"status": job["status"], "error": job.get("error")})


# ---------------------------------------------------------------------------
# Serve frontend (production)
# ---------------------------------------------------------------------------
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
