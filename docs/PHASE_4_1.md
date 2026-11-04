# Phase 4.1 — AI-Powered Dataset Understanding

**Status:** Completed and Verified  
**Brand:** Powered by Saniya  
**Tagline:** Your Autonomous Data Analyst  

---

## Overview

Phase 4.1 introduces **AI-Powered Dataset Understanding** to **AutoAnalyst AI**. When a user selects an uploaded or cleaned dataset, the system synthesizes an intelligent, structured, natural-language explanation of what the data represents, its likely domain and purpose, potential target variables, column semantics, grounded empirical observations, suggested KPIs, recommended charts, and 5–10 exploratory business questions.

The implementation strictly enforces **privacy-preserving data minimization**, **empirical statistical grounding** (zero hallucinated figures), and **seamless offline resilience** via deterministic statistical fallbacks.

---

## 1. Core Architecture & Design Principles

### A. Modular LLM Provider Abstraction
- Defined an abstract base class `BaseLLMProvider` (`app/services/ai/base_provider.py`).
- Implemented `GeminiProvider` (`app/services/ai/gemini_provider.py`) using `httpx.AsyncClient` with the official Google Generative Language REST API (`/v1beta/models/{model}:generateContent`).
- **Default Model:** `gemini-3.8-flash` (replacing the deprecated `gemini-2.0-flash`).
- **Configurability:** Fully configurable via backend environment variables:
  - `AI_MODEL_NAME="gemini-3.8-flash"`
  - `AI_TIMEOUT_SECONDS=30`
  - `AI_CACHE_ENABLED=True`
  - `PROMPT_SCHEMA_VERSION="v1"`
  - `GEMINI_API_KEY` / `GOOGLE_API_KEY`
- Architecture is extensible to other providers (Anthropic Claude, OpenAI, Local Ollama) without modifying business logic.

### B. Strict Data Privacy & Minimization
- **Zero Raw Data Rows:** Raw tabular records are **never** transmitted to Gemini.
- The `PromptContextBuilder` compiles a privacy-preserving summary containing only:
  - Dataset dimensions (row count, column count, missing count, duplicate count)
  - Column names and semantic types (`integer`, `float`, `string`, `boolean`, `datetime`)
  - 5-number numerical summaries (`min`, `mean`, `median`, `max`)
  - Top 3 categorical frequency distributions with percentages
  - Top bivariate Pearson correlations
- The context payload is compact ($\sim 2-4\text{ KB}$), protecting data sovereignty and optimizing LLM token latency.
- Wide datasets with up to 200+ columns are safely bounded: the top 35 most informative columns are profiled in depth while providing the full schema summary.

### C. Statistical Grounding & Anti-Hallucination
- Every numerical metric is calculated strictly by **Pandas** on the server.
- Each calculated observation is assigned a permanent, stable fact identifier (`fact_1`, `fact_2`, `fact_3`, ...).
- The LLM prompt enforces referencing these `referenced_fact_ids`.
- The backend validates every cited fact ID before delivering the response.
- **Empirical vs. Hypothesis Separation:**
  - `observed_fact`: Verified empirically against calculated facts.
  - `interpretation`: Analytical deduction with supporting evidence.
  - `hypothesis`: Domain hypothesis subject to testing. If an LLM claims an observation without a valid fact citation, it is automatically downgraded to `hypothesis`.

### D. Deterministic Offline Fallback Engine
- When `GEMINI_API_KEY` is not provided or if network calls timeout, the `HeuristicFallbackEngine` takes over seamlessly.
- Infers business domain and purpose via domain vocabulary heuristics (Maritime Logistics, E-Commerce, Financial, Healthcare, General).
- Detects classification or regression target variables using name heuristics, cardinality rules, and variance filters.
- Formulates grounded empirical observations from Pandas five-number summaries and categorical modes.
- Generates tailored KPIs, recommended chart types, and copyable exploratory questions.
- Result: **Zero 500 errors, zero downtime, and complete offline autonomy**.

### E. Cache Safety & Snapshot Invalidation
- Cache keys incorporate:
  $$\text{Cache Key} = \text{dataset\_id} + \text{snapshot\_hash}[:12] + \text{model} + \text{schema\_version}$$
- When a dataset is cleaned, transformed, undone, or reset, its SHA-256 snapshot hash changes, automatically guaranteeing a fresh cache entry.
- Cache writes use atomic temporary file replacement (`.tmp` to `.json`) to prevent corrupted reads during concurrent access.
- Force refresh bypasses cache on demand: `POST /api/v1/datasets/{dataset_id}/understanding/refresh`.

---

## 2. API Endpoints

### 1. `GET /api/v1/datasets/{dataset_id}/understanding`
Generates or retrieves cached dataset understanding.

**Query Parameters:**
- `force_refresh` (bool, default `false`): Bypass cache and recalculate.

**Response Structure (`DatasetUnderstandingResponse`):**
```json
{
  "dataset_id": "d6a8528cfad14fdea235f2a0de041322",
  "filename": "titanic.csv",
  "is_cleaned": false,
  "version": 0,
  "snapshot_hash": "a1b2c3d4e5f6...",
  "mode": "ai_generated", // or "statistical_fallback"
  "provider": "gemini",
  "model": "gemini-3.8-flash",
  "generated_at": "2026-11-01T21:08:29Z",
  "is_cached": true,
  "computed_facts": {
    "fact_1": {
      "fact_id": "fact_1",
      "category": "dimension",
      "column_name": null,
      "metric_name": "row_count",
      "value": 891,
      "formatted_statement": "Dataset contains 891 total rows."
    }
  },
  "overview": {
    "domain": "Maritime Transport & Passenger Demographics",
    "likely_purpose": "Analyzing passenger survival determinants and evacuation equity across travel classes.",
    "executive_summary": "Comprehensive historical manifest detailing passenger demographics, travel accommodations, and survival outcomes.",
    "detected_target_variable": {
      "column_name": "Survived",
      "confidence": "high",
      "reasoning": "Binary outcome indicating passenger survival status during the voyage.",
      "referenced_fact_ids": ["fact_7", "fact_8"]
    },
    "referenced_fact_ids": ["fact_1", "fact_2", "fact_3"]
  },
  "columns": [
    {
      "name": "Survived",
      "semantic_type": "integer",
      "business_meaning": "Indicator of passenger survival (1 = Survived, 0 = Deceased).",
      "is_key_feature": true,
      "is_identifier": false,
      "data_quality_note": null,
      "referenced_fact_ids": ["fact_7"]
    }
  ],
  "analytical_insights": {
    "key_observations": [
      {
        "observation_type": "observed_fact",
        "statement": "Column 'Age' exhibits missing values in 177 records (19.9%).",
        "business_implication": "Demographic analyses involving age require imputation or filtering.",
        "referenced_fact_ids": ["fact_12"],
        "is_verified_fact": true
      }
    ],
    "potential_relationships": [
      {
        "primary_column": "Pclass",
        "secondary_column": "Survived",
        "relationship_description": "Passenger ticket class strongly influences survival rates, with First Class passengers exhibiting higher survival probabilities.",
        "analytical_type": "segmentation",
        "referenced_fact_ids": ["fact_9"]
      }
    ],
    "business_relevance": "Provides critical historical evidence on passenger safety equity and crisis triage operations."
  },
  "suggested_analysis": {
    "suggested_kpis": [
      {
        "name": "Overall Survival Rate",
        "calculation": "sum(Survived) / count(Survived) * 100",
        "purpose": "Track percentage of passengers who survived.",
        "business_value": "Primary benchmark for evacuation efficacy.",
        "target_column": "Survived"
      }
    ],
    "recommended_charts": [
      {
        "chart_type": "bar",
        "title": "Survival Rate by Passenger Class",
        "x_column": "Pclass",
        "y_column": "Survived",
        "aggregation": "mean",
        "reason": "Compares survival equity across socioeconomic travel tiers."
      }
    ],
    "suggested_questions": [
      "What is the survival disparity between male and female passengers across ticket classes?",
      "Did port of embarkation correlate with cabin assignment or survival probability?",
      "How did fare prices vary among family units traveling with siblings or parents?"
    ]
  },
  "validation_warnings": []
}
```

### 2. `POST /api/v1/datasets/{dataset_id}/understanding/refresh`
Forces an immediate recalculation and cache update for the specified dataset.

---

## 3. Frontend Workspace UI Components

Located in `frontend/src/components/ai/`:

1. **`DatasetUnderstandingView.tsx`**:
   - Master workspace orchestrating loading, error handling, cache pills, and refresh actions.
   - Mode tags: `gemini-3.8-flash` (generative AI) or `Statistical Heuristic Engine (Offline)` with contextual guidance.
   - Five subtab views: `Executive Overview`, `Observations & Hypotheses`, `Column Catalog`, `KPIs & Questions`, and `Grounded Facts Inspector`.

2. **`ExecutiveSummaryCard.tsx`**:
   - Inferred domain header with badge and verified Pandas checkmark.
   - Likely Purpose and Executive Summary narrative blocks.
   - Detected Target Variable box with confidence badge (High / Medium / Low), reasoning, and evidence fact IDs.

3. **`InsightsAndObservations.tsx`**:
   - Filter pill controls: `All`, `Verified Facts`, `Hypotheses`.
   - Clear visual differentiation between empirical facts (green border, checkmark) and hypotheses (purple border, help icon).
   - Potential relationships card grid showcasing cross-column dynamics and analytical types.
   - Strategic and analytical business relevance card.

4. **`ColumnUnderstandingTable.tsx`**:
   - Searchable and filterable column catalog.
   - Semantic data types and role badges (`Key Feature`, `ID`, `Feature`).
   - Business meanings and data quality alerts.

5. **`SuggestedQuestionsPanel.tsx`**:
   - Suggested KPIs with formula, purpose, and business value.
   - Recommended visualizations with chart type pills and axis mapping.
   - 5–10 exploratory business questions with interactive 1-click clipboard copy buttons.

6. **`UnderstandingLoadingSkeleton.tsx`**:
   - Multi-step animated progress indicators explaining numerical grounding, privacy minimization, and LLM synthesis.

7. **`Grounded Facts Inspector Drawer`**:
   - Modal and grid viewing exact Pandas-computed values, categories, metric names, and empirical statements for every fact ID.

---

## 4. Verification & Testing

### Automated Pytest Suite
Ran 70 tests across the backend with **100% pass rate**:
```
tests/test_ai_understanding_api.py::test_missing_api_key_activates_fallback PASSED
tests/test_ai_understanding_api.py::test_valid_ai_response_with_mocked_gemini[asyncio] PASSED
tests/test_ai_understanding_api.py::test_provider_timeout_graceful_fallback[asyncio] PASSED
tests/test_ai_understanding_api.py::test_dataset_not_found PASSED
tests/test_ai_understanding_api.py::test_cache_hit_returns_cached_data PASSED
tests/test_ai_understanding_api.py::test_force_refresh_bypasses_cache PASSED
tests/test_ai_understanding_api.py::test_cleaned_dataset_distinct_understanding PASSED
tests/test_ai_understanding_api.py::test_fact_grounding_and_downgrade PASSED
tests/test_ai_understanding_api.py::test_wide_dataset_handling PASSED
... (61 previous tests for Phase 1, 2.1, 2.2, 3 all passed)
70 passed, 4 warnings in 6.48s
```

### Production Build
- `npm run build` executed with zero TypeScript and bundling errors:
```
✓ 1982 modules transformed.
dist/index.html                     0.87 kB │ gzip:     0.45 kB
dist/assets/index-CdZdxTwb.css     80.84 kB │ gzip:    14.62 kB
dist/assets/index-DuZcFe3f.js   5,240.92 kB │ gzip: 1,610.10 kB
✓ built in 51.58s
```

### Live Server Verification
- Backend running on `http://127.0.0.1:8000`
- Frontend running on `http://127.0.0.1:5173`
- Verified live responses for original datasets (`titanic.csv`, `customers.csv`) and cleaned datasets (`Cleaned_test_clean.csv`).
- Verified cache hits (`is_cached: True`) and force refresh (`is_cached: False`).

