# AutoAnalyst AI — Phase 4.3: Automated Insights & Business Intelligence

Brand: **Powered by Saniya**  
Tagline: **Your Autonomous Data Analyst**

## Overview
Phase 4.3 elevates AutoAnalyst AI from a reactive question-answering tool to an autonomous, proactive Business Intelligence analyst. It autonomously discovers critical findings, benchmarks best and worst-performing categories, detects statistical anomalies (IQR outliers, rare categories, missing concentrations), and generates actionable, fact-grounded recommendations without requiring manual user configuration.

---

## Key Capabilities

### 1. Semantic Column Classification
- Analyzes column names, cardinality, and data types using regex and heuristics.
- Assigns semantic roles: `identifier`, `numerical_measure`, `categorical_dimension`, `entity_name`, `date_time`, `url_media`, `free_text`.
- **Mandatory Safeguard:** Automatically excludes technical identifiers (`PassengerId`, `*_id`, sequential indices) and media URLs from business metrics, averages, correlations, or category groupings.

### 2. Autonomous Statistical Findings
- **Data Quality Audit:** Detects missing value concentrations and health score (0–100 scale).
- **Distribution & Skewness:** Identifies asymmetric distributions where mean deviates significantly from median.
- **Pairwise Correlation:** Scans Pearson correlations ($|r| \ge 0.45$) strictly between true numerical measures.
- **Category Imbalance:** Detects dominance ratios exceeding 60% in categorical dimensions.

### 3. Best and Worst Category Benchmarking
- Intelligently pairs categorical dimensions with business measures or frequency counts.
- Computes top and bottom performers, delta percentages vs dataset average (`+X% vs avg`).
- Produces interactive comparative Plotly bar charts highlighting top (emerald) and lowest (rose) performers.
- **Sample Size Safeguard:** Flags categories with $n < 5$ as `exploratory` to prevent false conclusions.

### 4. Anomaly & Unusual Pattern Detection
- **Numerical Outliers:** Evaluates Tukey's Interquartile Range fences ($[Q_1 - 1.5 \times IQR, Q_3 + 1.5 \times IQR]$).
- **Rare Categories:** Identifies categories representing $< 1\%$ of total dataset records.
- **Missing Concentrations:** Highlights columns with $> 40\%$ missing cells.

### 5. Actionable Business Recommendations
- Generates strategic actions categorized by `operational`, `commercial`, `risk`, and `data_quality`.
- **Fact Grounding:** Strictly separates verified empirical facts (`is_hypothesis=False`) from analytical assumptions (`is_hypothesis=True`).
- Assigns stable fact IDs (`#fact_1`, `#fact_2`) referencing Pandas-computed observations.

### 6. Natural Language Query Resolution in "Ask Your Data"
Directly interprets and resolves broad analytical queries without requiring column names:
1. *"What are the most important findings?"*
2. *"Which categories perform best and worst?"*
3. *"Are there unusual patterns?"*
4. *"What actions would you recommend based on the data?"*
5. *"What are the most important data-quality issues?"*

### 7. Snapshot-Aware Caching
- Generates cache keys incorporating `dataset_id`, the SHA-256 snapshot hash (`snapshot_hash[:12]`), model name, and schema version.
- Any cleaning operation, undo, or reset automatically generates a new snapshot hash, ensuring stale insights are never served.

---

## API Endpoints

### 1. GET `/api/v1/datasets/{dataset_id}/insights`
Retrieves automated insights, best/worst analysis, anomalies, and recommendations. Returns cached data if the dataset snapshot hash matches.

### 2. POST `/api/v1/datasets/{dataset_id}/insights/refresh`
Bypasses the snapshot cache and re-computes insights fresh using Pandas and Gemini (with heuristic fallback).

### 3. POST `/api/v1/datasets/{dataset_id}/ask`
Accepts natural language queries (both metric-specific and broad analytical intents) and returns grounded answers, charts, and tabular breakdowns.

---

## Test Verification
- **Total Backend Tests:** 100 passed out of 100 (0 failures).
- **Frontend Production Build:** `tsc -b && vite build` built in 1m 11s with 0 errors.

