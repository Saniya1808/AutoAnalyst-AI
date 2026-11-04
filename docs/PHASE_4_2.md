# Phase 4.2 — Ask Your Data (Natural Language Data Analyst)

**Status:** Completed and Verified  
**Brand:** Powered by Saniya  
**Tagline:** Your Autonomous Data Analyst  

---

## Overview

**Phase 4.2: Ask Your Data** introduces an interactive, conversational natural-language data analyst to **AutoAnalyst AI**. Users can ask questions about any selected dataset (original or cleaned) in plain English — e.g., *"What is the average fare by passenger class?"*, *"Which product category generates the highest revenue?"*, *"Show monthly sales trends"*, or *"Which columns have the highest missing values?"*.

The architecture enforces:
1. **Zero Arbitrary Execution**: Absolute ban on arbitrary AI-generated Python (`eval`/`exec`) or raw SQL code.
2. **Strict QueryPlan Enforcement**: The LLM acts solely as a query interpreter outputting strict JSON conforming to a Pydantic `QueryPlan`.
3. **Hardened Analytical Execution Engine**: Predefined, audited Pandas aggregation pipelines execute all calculations, string matching (`starts_with`, `ends_with`, `contains`, `exact`), distinct value extraction, and generate grounded fact IDs (`fact_1`, `fact_2`, ...).
4. **Smart Entity & Column Disambiguation**: Differentiates human-readable entity columns (e.g. `Company Name`) from technical/media columns (e.g. `Company Logo (URL)`) and handles pluralization/possessives.
5. **General Dataset Overview Recognition**: Instantly explains dataset contents, rows, columns, and domain without demanding a numerical calculation.
6. **Automatic Plotly Visualizations & Clean Tabular Data**: Automatically generates Plotly bar, line, scatter, histogram, box, and pie charts with dual Chart/Table toggles and clean link rendering.
7. **Dataset-Isolated Multi-Turn Sessions**: Conversations are keyed per dataset ID and synchronized to the dataset file SHA-256 snapshot hash.
8. **Deterministic Offline Fallbacks**: Complete offline heuristics operate reliably when `GEMINI_API_KEY` is not configured or during provider timeouts.

---

## 1. System Architecture

```
User Natural Language Question
          │
          ▼
Context Builder (Distills schema, types, summaries — No raw rows)
          │
          ▼
Question Interpreter (Gemini 3.8-Flash / Heuristic Fallback)
          │
          ▼
Structured QueryPlan (Validated Pydantic Model)
          │
          ▼
Analytical Executor (Safe Pandas Execution Engine)
   ├── Column schema validation
   ├── Type compatibility checks
   ├── Vectorized filtering
   └── Group-by / Aggregations / Trends / Correlations
          │
          ├──> Computed Primary Metric & Grounded Fact IDs
          ├──> Tabular Result Data (Capped at 50 rows)
          └──> Interactive Plotly ChartConfig (Bar, Line, Scatter, etc.)
          │
          ▼
Answer Synthesizer (Gemini / Heuristic Grounded Generator)
   ├── Direct answer stating exact figures
   ├── Calculation method details
   ├── Exclusions & missing value caveats
   └── Intelligent follow-up prompts
          │
          ▼
Conversation Service (Per-dataset persistence, SHA-256 snapshot tracking)
          │
          ▼
Interactive Workspace UI (Chat bubbles, dual view, fact modals, copy answer)
```

---

## 2. Supported Analytical Operations

| Intent | Operation | Description | Generated Chart |
|---|---|---|---|
| `aggregate_metric` | `mean`, `sum`, `median`, `min`, `max`, `std`, `count` | Scalar aggregation on numeric column with non-null sample size | Histogram / Box Plot |
| `group_by_comparison` | `mean`, `sum`, `count`, `median`, `min`, `max` | Grouping across categorical segment and aggregating numerical metrics | Bar Chart / Pie Chart |
| `distribution_analysis` | `value_counts` / `distribution` | Categorical frequency counts and percentages or numeric distributions | Bar Chart / Pie / Histogram |
| `correlation_analysis` | `correlation` | Pearson correlation coefficient ($r$) between two numeric variables | Scatter Plot (sampled up to 500 points) |
| `trend_analysis` | `mean`, `sum`, `count` | Chronological grouping by year, month, or day | Line Chart |
| `ranking_top_bottom` | `max`, `min` | Top/bottom $N$ records sorted by numeric metric | Bar Chart |
| `missing_value_inspection`| `missing_summary` | Summary of missing values and percentages per column | Bar Chart |
| `dataset_summary` | `count` | Total rows, total columns, missing cells, and duplicate rows | None |
| `ambiguous_clarification` | `none` | Prompts user with 2–3 suggested specific questions when question is unclear | None |

---

## 3. Strict Safety & Grounding Controls

1. **No Code Execution**:
   - `eval()`, `exec()`, `subprocess`, and SQL statements are prohibited.
   - User inputs containing code injection patterns are parsed strictly as plain text strings and rejected or clarified.
2. **Schema & Type Validation**:
   - Columns must exist in `df.columns`.
   - Aggregations (`mean`, `sum`, `median`) are rejected on string columns.
   - Group-by columns are rejected if cardinality exceeds 1,000 unique values.
3. **Fact Grounding & Numerical Fidelity**:
   - Every number displayed in the response originates directly from Pandas calculations.
   - All observations carry stable fact IDs (`fact_1`, `fact_2`, ...) with metric names and formatted statements.
4. **Snapshot Hash Synchronization**:
   - Conversations are stored with the dataset's SHA-256 snapshot hash.
   - If a dataset is cleaned, transformed, undone, or reset, the snapshot hash changes, alerting the user and preventing stale calculations from bleeding into the new context.

---

## 4. API Endpoints

### 1. `POST /api/v1/datasets/{dataset_id}/ask`
Submits a natural-language question.

**Request Body:**
```json
{
  "question": "What is the average Fare by Pclass?",
  "include_chart": true
}
```

**Response (`AskDataResponse`):**
```json
{
  "message_id": "msg_f3a12b4e5d",
  "dataset_id": "d6a8528cfad14fdea235f2a0de041322",
  "snapshot_hash": "a9b8c7...",
  "question": "What is the average Fare by Pclass?",
  "direct_answer": "The highest mean of Fare occurs in 'Pclass' = 1.0 with 84.15.",
  "primary_metric": {
    "label": "Top Pclass",
    "value": 84.15,
    "formatted": "1.0: 84.15"
  },
  "calculation_method": "Grouped by 'Pclass', aggregated 'Fare' using mean(), and sorted.",
  "columns_used": ["Pclass", "Fare"],
  "filters_applied": [],
  "tabular_data": [
    { "Pclass": "1.0", "mean_Fare": 84.15 },
    { "Pclass": "2.0", "mean_Fare": 20.66 },
    { "Pclass": "3.0", "mean_Fare": 13.68 }
  ],
  "chart": {
    "chart_id": "chart_grp_bar_d6a8528c",
    "title": "Mean of Fare by Pclass",
    "chart_type": "bar",
    "x_column": "Pclass",
    "y_column": "mean_Fare",
    "plotly_data": [ ... ],
    "plotly_layout": { ... }
  },
  "grounded_facts": [
    {
      "fact_id": "fact_1",
      "category": "group_comparison",
      "column_name": "Pclass",
      "metric_name": "mean_1.0",
      "value": 84.15,
      "formatted_statement": "For 'Pclass' = 1.0, the mean of Fare is 84.15."
    }
  ],
  "limitations_and_warnings": [],
  "is_ambiguous": false,
  "clarification_prompt": null,
  "suggested_follow_ups": [
    "Are there any outliers in Pclass?",
    "How does this distribution change over time?"
  ],
  "mode": "statistical_fallback", // or "ai_generated" when GEMINI_API_KEY is configured
  "provider": "fallback",
  "model": "Deterministic Heuristics Engine",
  "created_at": "2026-11-01T21:50:09Z"
}
```

### 2. `GET /api/v1/datasets/{dataset_id}/conversation`
Retrieves chat history for the dataset.

### 3. `DELETE /api/v1/datasets/{dataset_id}/conversation`
Clears chat history for the dataset.

### 4. `GET /api/v1/datasets/{dataset_id}/suggested-questions`
Returns 5–8 schema-informed prompts based on columns, data types, and cardinality.

---

## 5. Automated Verification Results

### Backend Pytest Suite
Ran **83 passing tests** across all modules:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
======================= 83 passed, 4 warnings in 7.64s ========================
```
- 70 existing tests for Phase 1, Phase 2.1, Phase 2.2, Phase 3, and Phase 4.1.
- 13 new comprehensive tests in `test_ask_data_api.py`.

### Frontend Production Build
```powershell
npm run build
✓ 1988 modules transformed.
dist/index.html                     0.87 kB │ gzip:     0.45 kB
dist/assets/index-BIrzsZ1v.css     90.95 kB │ gzip:    16.17 kB
dist/assets/index-CEJ558Bg.js   5,260.30 kB │ gzip: 1,613.91 kB
✓ built in 39.45s
```
Zero TypeScript errors (`tsc -b`), clean production bundle.

### End-to-End Live Verification
- Backend running on `http://127.0.0.1:8000` (FastAPI with live reloader).
- Frontend running on `http://127.0.0.1:5173` (Vite dev server).
- Tested group-by queries on `titanic.csv` (891 rows):
  - Inferred `Pclass` as group column and `Fare` as numeric target.
  - Calculated exact means: Class 1 (\$84.15), Class 2 (\$20.66), Class 3 (\$13.68).
  - Returned Plotly Bar Chart and grounded fact IDs.
  - Verified conversation persistence and isolation across dataset switching.

