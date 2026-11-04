# AutoAnalyst AI
**Your Autonomous Data Analyst** — *Powered by Saniya.*

AutoAnalyst AI is a full-stack, enterprise-grade autonomous data analytics platform. It automatically ingests raw datasets, performs statistical profiling and cleaning, generates interactive dashboards, discovers automated insights, models longitudinal trends and anomalies with rigorous hypothesis testing, and compiles publication-grade executive reports in PDF and Excel.

---

## Key Capabilities & Features

### 1. Ingestion & Statistical Profiling (Phases 1 & 2.1)
- **Multi-Format Ingestion**: Ingests `.csv`, `.xlsx` (OpenPyXL), and `.xls` (XLRD) with encoding fallback (UTF-8, Latin-1).
- **Automated Profiling**: Real-time Pandas computation of schema cardinality, missingness, numeric distributions (mean, median, IQR, std), and duplicate analysis.
- **Safe JSON Sanitization**: Strict serialization pipeline converting `NaN`, `NaT`, `+inf`, and `-inf` to JSON `null`.
- **Non-Destructive Versioning**: Cryptographic SHA-256 snapshot hashing ensuring pristine raw datasets remain immutable.

### 2. Automated Visual Dashboards & KPI Explorers (Phase 2.2)
- **Automatic Recommendations**: Heuristic chart engine suggesting schema-driven Plotly charts (histograms, box plots, bar charts, line plots, and scatter plots).
- **Interactive Visual Explorer**: Custom visual builder supporting dynamic axes, groupings, aggregations (`sum`, `avg`, `count`, `min`, `max`), and drill-down record inspection.
- **Dynamic Multi-Faceted Filters**: Real-time categorical and numeric range filters with live dashboard recalculation.

### 3. Intelligent Data Cleaning & Transformation (Phase 3)
- **Composite Quality Index**: Weighted data health scoring ($Q = 0.50 \times \text{Comp} + 0.30 \times \text{Valid} + 0.20 \times \text{Uniq}$).
- **Transformation Pipeline**: Missing value imputation (mean, median, mode, constant, drop), deduplication, safe data type casting, and outlier treatment (IQR and Z-Score fences, winsorization, filtering).
- **Versioned Undo/Reset**: Snapshot-backed transformation history (`clean_{id}`) supporting sequential undo and one-click reset to original state.

### 4. AI Dataset Understanding & Grounding (Phase 4.1)
- **Autonomous Context Synthesis**: Domain detection, business purpose summary, target variable inference, and suggested exploratory questions.
- **Multi-Provider Architecture**: Defaulting to `gemini-3.8-flash` via Google Generative Language REST API, with complete offline statistical fallback.
- **Data Minimization & Fact Grounding**: Zero raw dataset rows transmitted to external APIs; context summarized strictly from Pandas statistical distributions (~3KB) with stable, verifiable fact IDs (`fact_1`, `fact_2`, ...).

### 5. Ask Your Data — Natural Language Data Analyst (Phase 4.2)
- **Deterministic Natural Language Understanding**: Parses analytical questions into validated Pydantic plans (`QueryPlan`) with zero arbitrary code execution (`eval`/`exec`) or raw SQL.
- **Verifiable Answers**: Directly links answers to deterministic Pandas execution results, methodology explanations, and automatic visualizations.
- **Isolated Conversation Threads**: Thread-isolated chat memory synchronized to the active dataset snapshot hash.

### 6. Automated Insights & Category Benchmarks (Phase 4.3)
- **Statistical Findings Ranking**: Automated extraction of distribution skews, cross-column correlations, and representation imbalances.
- **Category Benchmarks**: High-confidence detection of top and lowest category performers relative to dataset averages.
- **Actionable Strategic Recommendations**: Grounded recommendations categorized by priority and separated into empirical facts vs. analytical hypotheses.

### 7. Advanced Trend & Anomaly Intelligence (Phase 4.4)
- **Longitudinal Trend Modeling**: OLS regression with Durbin-Watson autocorrelation tests, Newey-West HAC standard error adjustment, and non-parametric Mann-Kendall trend tests.
- **Multiple Hypothesis Testing Correction**: Pure NumPy Benjamini–Hochberg False Discovery Rate (FDR) adjustment at $q = 0.05$.
- **Cyclical Seasonality Analysis**: ANOVA F-tests and Kruskal-Wallis non-parametric tests detecting day-of-week and month-of-year cyclical seasonality.
- **Multi-Type Anomaly Engine**: Robust Zero-MAD scale estimation, categorical frequency drops, extreme skewness warnings, and temporal spikes/drops.

### 8. Executive Reports & Business Intelligence (Phase 4.5)
- **Unified Document Assembly**: Single-pass aggregation of multi-engine intelligence into 8 standardized sections with SHA-256 snapshot integrity.
- **Corporate A4 PDF Export**: Multi-page PDF generation via Playwright Chromium featuring navy/purple branding (`#1E1B4B`, `#7C3AED`), standalone vector SVG charts, and running page numbers (`Page X of Y`).
- **Multi-Sheet Excel Workbooks**: Formatted 8-worksheet Excel workbook generated via `openpyxl` with styled header banners, auto-adjusted column widths, native Excel number formats, and formula injection protection.
- **Print Preview**: Clean, dedicated `@media print` stylesheet removing navigation, sidebars, and control buttons.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, Lucide React, Plotly.js |
| **Backend API** | Python 3.10+, FastAPI, Pydantic v2, Pydantic Settings, Uvicorn |
| **Data & Math** | Pandas, NumPy, SciPy (OLS, ANOVA, Kruskal-Wallis, Newey-West HAC, Mann-Kendall) |
| **Document Builders**| Playwright 1.64.1 (Chromium headless PDF), OpenPyXL 3.1.5 (Multi-sheet Excel) |
| **Generative AI** | Google Gemini API (`gemini-3.8-flash`) with deterministic statistical fallback |
| **Theme Engine** | System-synced dark/light themes with persistent state |

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        AutoAnalyst AI Platform                         │
│               Brand: Powered by Saniya • Your Autonomous Data Analyst  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌─────────────────────────────────────┐     ┌────────────────────────────────────┐
│      Frontend (React / Vite)        │     │       Backend API (FastAPI)        │
│  - Workspace & Navigation           │     │  - Pydantic Validation & Security  │
│  - Visual Dashboards (Plotly)       │◄───►│  - Pandas Profiling & Cleaning     │
│  - Ask Your Data Chat Interface     │     │  - Trend & Anomaly Intelligence    │
│  - Executive Reports Customizer     │     │  - Playwright Chromium PDF Engine  │
│  - Code-Split Bundles (React.lazy)  │     │  - OpenPyXL Multi-Sheet Builder    │
└─────────────────────────────────────┘     └─────────────────┬──────────────────┘
                                                              │
                                       ┌──────────────────────┴──────────────────┐
                                       ▼                                         ▼
                        ┌──────────────────────────────┐          ┌──────────────────────────────┐
                        │    Generative AI Service     │          │    Deterministic Fallback    │
                        │ - Google Gemini API (Flash)  │          │ - Empirical Heuristics       │
                        │ - Fact-Grounded Synthesis    │          │ - Pure Pandas/NumPy Rules    │
                        └──────────────────────────────┘          └──────────────────────────────┘
```

---

## Prerequisites

- **Node.js**: v20+ (tested with v22.21.0)
- **Python**: 3.10+ (tested with 3.10.11)
- **Git**
- **PowerShell** (Windows) or **Bash** (macOS/Linux)
- **Google Chrome** or **Microsoft Edge** (for Playwright PDF printing)

---

## Quickstart Guide

### 1. Clone & Set Up Environment

```powershell
git clone <repository-url>
cd AutoAnalyst-AI
```

### 2. Backend Setup (FastAPI)

```powershell
cd backend

# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt

# Copy environment template
Copy-Item .env.example .env

# Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive API Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

### 3. Frontend Setup (React + Vite)

Open a second terminal window:

```powershell
cd frontend

# Install frontend dependencies
npm install

# Copy environment template
Copy-Item .env.example .env

# Start Vite development server
npm run dev
```

- **Web Application URL**: [http://localhost:5173](http://localhost:5173)

---

## Environment Variables Reference

### Backend (`backend/.env`)

```ini
APP_NAME=AutoAnalyst AI
ENVIRONMENT=development
FRONTEND_ORIGIN=http://localhost:5173,http://127.0.0.1:5173
MAX_UPLOAD_SIZE_MB=25
MAX_DATASET_ROWS=100000
MAX_DATASET_COLUMNS=200

# Optional: Add Gemini API key for Generative AI summaries
# If omitted or offline, AutoAnalyst AI runs safely in deterministic fallback mode
GEMINI_API_KEY=your_gemini_api_key_here
AI_MODEL_NAME=gemini-3.8-flash
AI_TIMEOUT_SECONDS=30
AI_CACHE_ENABLED=true
```

### Frontend (`frontend/.env`)

```ini
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API root metadata and brand information |
| `GET` | `/api/v1/health` | Live backend service health check |
| `POST` | `/api/v1/datasets/upload` | Upload `.csv`, `.xlsx`, or `.xls` file and compute profile |
| `GET` | `/api/v1/datasets` | List all uploaded datasets and workspace totals |
| `GET` | `/api/v1/datasets/{id}` | Complete dataset profile, schema statistics, and preview |
| `GET` | `/api/v1/datasets/{id}/preview` | Paginated raw dataset records (`limit`, `offset`) |
| `DELETE` | `/api/v1/datasets/{id}` | Delete dataset and clean up persisted disk files |
| `GET` | `/api/v1/datasets/{id}/dashboard` | Retrieve automatic KPI cards, recommended charts, and filter bounds |
| `POST` | `/api/v1/datasets/{id}/charts/generate` | Generate custom interactive chart (Bar, Line, Scatter, Box, Pie) |
| `POST` | `/api/v1/datasets/{id}/dashboard/filter` | Apply multi-faceted filters and recalculate dashboard KPIs |
| `POST` | `/api/v1/datasets/{id}/dashboard/drilldown` | Inspect category segment metrics and view sample records |
| `GET` | `/api/v1/datasets/{id}/cleaning/profile` | Compute data quality index, missing counts, duplicate stats, and outliers |
| `POST` | `/api/v1/datasets/{id}/cleaning/apply` | Apply transformation, save undo snapshot, and update hash |
| `POST` | `/api/v1/datasets/{id}/cleaning/undo` | Roll back most recent transformation step |
| `POST` | `/api/v1/datasets/{id}/cleaning/reset` | Discard all transformations and restore original dataset |
| `GET` | `/api/v1/datasets/{id}/understanding` | Get AI dataset understanding, purpose summary, and suggested questions |
| `POST` | `/api/v1/datasets/{id}/ask` | Ask a natural language question with verified Pandas computation |
| `GET` | `/api/v1/datasets/{id}/insights` | Automated insights, ranked findings, category benchmarks, trends, and anomalies |
| `POST` | `/api/v1/datasets/{id}/reports/generate` | Assemble full executive intelligence report JSON preview |
| `POST` | `/api/v1/datasets/{id}/reports/export/pdf` | Stream publication-grade executive A4 PDF report |
| `POST` | `/api/v1/datasets/{id}/reports/export/excel` | Stream styled 8-worksheet Excel workbook (`.xlsx`) |

---

## Automated Test Suites

### Backend Test Suite (166 Passing Tests)

```powershell
Set-Location 'backend'
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest tests -v
```

Includes unit, regression, statistical, and API integration tests:
- `test_dataset_api.py`: Upload, schema validation, streaming, deletion.
- `test_dashboard_api.py`: KPIs, chart recommendations, custom charts, filters, drill-down.
- `test_cleaning_api.py`: Imputation, deduplication, type casting, outlier treatment, undo/reset snapshots.
- `test_ai_understanding_api.py`: Domain synthesis, question generation, statistical fallback.
- `test_ask_data_api.py`: QueryPlan execution, calculation safety, conversational history.
- `test_automated_insights_api.py`: Finding significance, category performers, recommendations.
- `test_trend_intelligence.py`: OLS, HAC, Mann-Kendall, Zero-MAD fallback, ANOVA/Kruskal, Benjamini-Hochberg FDR.
- `test_reports_api.py`: Report assembly, multi-sheet Excel generation, Playwright PDF export, snapshot conflict detection.

### Frontend Production Build & Type Checking

```powershell
Set-Location 'frontend'
npm run build
```

Compiles all TypeScript files with `0` type errors and produces optimized, code-split chunks with dynamic `React.lazy` loading.

---

## License & Attribution

**AutoAnalyst AI**  
*Brand: Powered by Saniya*  
*Tagline: Your Autonomous Data Analyst*  
Licensed under the MIT License.
