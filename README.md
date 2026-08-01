# AI Financial Research Report Generator

Minimal web application that turns a company context document into a downloadable equity-research PDF. The layout is a Geojit-style research-report structure, with financial tables, narrative sections, risk disclosures and charts.

## What is included

- React upload UI: company name + PDF, CSV, TXT, XLSX or Markdown document.
- FastAPI report pipeline: parse, extract, validate, chart and PDF generation.
- Gemini 2.5 Flash extraction when `GEMINI_API_KEY` is configured. Set `GEMINI_MODEL` to use another model enabled for your key.
- Deterministic fallback for structured key/value CSVs and common research-note TXT files. It only extracts values present in the supplied file.
- A multi-page editable AcroForm template at `GET /api/template`, generated from the same report schema.
- Two generated example reports and two source inputs in `examples/` and `sample_inputs/`.

## Run locally

Prerequisites: Python 3.10+ and Node.js 18+.

```powershell
cd backend
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Optional: set GEMINI_API_KEY in .env
python main.py
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Enter a company name, upload a context document, generate the report, and use the Download PDF button.

## Submission artifacts

Regenerate the submitted examples and editable template with:

```powershell
cd backend
python generate_examples.py
```

The command writes these files:

- `examples/Eternal_Limited_report.pdf` (TXT input)
- `examples/ICICI_Bank_report.pdf` (CSV input)
- `examples/Editable_Research_Report_Template.pdf` (interactive AcroForm template)

The editable template can also be downloaded at `http://localhost:8000/api/template`.

## Template fields and extension points

`backend/template_fields.py` is the single source of truth for the report field schema and defaults. The same names are used by:

- `backend/ai_extractor.py` for LLM extraction
- `backend/deterministic_extractor.py` for no-key CSV/TXT extraction
- `backend/pdf_generator.py` for the final print-ready report
- `backend/fillable_template.py` for the editable AcroForm template

To add a field: add it to `TEMPLATE_FIELDS`, teach the relevant extractor how to obtain it, and render it in `pdf_generator.py` and/or `fillable_template.py`.

Missing source values are retained as `N/A`; the generator does not fabricate financial figures.

## API

- `POST /api/generate-report` - multipart request with `company_name` and `file`; returns a task id.
- `GET /api/report/{task_id}/status` - processing status.
- `GET /api/report/{task_id}` - downloads the completed report.
- `GET /api/template` - downloads the editable report template.
- `GET /api/health` - health check.

## Verification

```powershell
cd backend
python test_e2e.py
cd ../frontend
npm run build
```

The backend checks CSV/TXT parsing, deterministic field population, the interactive template, and full PDF/chart generation for both supplied examples.

## Technology

React + Vite, FastAPI, Google Gemini, pdfplumber, pandas, ReportLab, and Matplotlib.
