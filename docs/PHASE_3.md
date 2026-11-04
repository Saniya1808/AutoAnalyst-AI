# Phase 3 — Intelligent Data Cleaning & Transformation

**Status:** Completed and Verified  
**Brand:** Powered by Saniya  
**Tagline:** Your Autonomous Data Analyst  

---

## Overview

Phase 3 introduces an enterprise-grade, non-destructive data cleaning and transformation engine into **AutoAnalyst AI**. It enables data analysts to assess quality index scores, impute missing values, eliminate duplicate records, cast schemas, and treat numerical distribution outliers with full reversibility (Undo and Reset) and guaranteed original source immutability verified via SHA-256 cryptographic hashes.

---

## 1. Non-Destructive Architecture & Immutability

### A. Original Dataset Protection
- The original uploaded dataset file (`{dataset_id}.csv`/`.xlsx`/`.xls`) and its metadata (`{dataset_id}_meta.json`) are **strictly read-only**.
- A **SHA-256 cryptographic checksum** is computed and verified before and after every single operation (Preview, Apply, Undo, and Reset) to guarantee zero byte alteration to the source file.

### B. Cleaned Versioning & Undo Pipeline
- Working cleaned versions are persisted separately: `uploads/{clean_id}.csv` (where `clean_id = clean_{parent_id}`).
- Intermediate version snapshots are archived in: `uploads/snapshots_{dataset_id}/v{version}.csv`.
- An audit log of all transformations is maintained in: `uploads/{dataset_id}_history.json`.
- **Undo**: Pops the most recent transformation step and rolls back to version $N-1$. If rolling back to version 0, it cleanly reverts to the pristine original dataset.
- **Reset**: Discards all transformation snapshots, clears the audit trail, and restores the original uploaded dataset without touching the source file.

---

## 2. Standardized Data Quality Index Formula

AutoAnalyst AI uses an objective, mathematically defined Data Quality Index ($Q$) composed of three weighted pillars:

$$Q = 0.50 \times S_{\text{comp}} + 0.30 \times S_{\text{valid}} + 0.20 \times S_{\text{uniq}}$$

Where:
1. **Completeness Score ($S_{\text{comp}}$)**:
   Measures the proportion of non-null cells across the total dataset grid:
   $$S_{\text{comp}} = \left( 1 - \frac{\text{Missing Cells}}{\text{Total Rows} \times \text{Total Columns}} \right) \times 100$$
2. **Validity Score ($S_{\text{valid}}$)**:
   Measures the proportion of cells that conform strictly to their inferred semantic data types without coercion failures, invalid parses, or mathematical infinities ($\pm\infty$):
   $$S_{\text{valid}} = \left( 1 - \frac{\text{Type-Inconsistent Cells} + \text{Infinite Cells}}{\text{Total Cells}} \right) \times 100$$
3. **Uniqueness Score ($S_{\text{uniq}}$)**:
   Measures row-level distinctness and penalizes redundancy:
   $$S_{\text{uniq}} = \left( 1 - \frac{\text{Duplicate Rows}}{\text{Total Rows}} \right) \times 100$$

### Quality Grades
- **Excellent**: $Q \ge 90\%$
- **Good**: $75\% \le Q < 90\%$
- **Fair**: $50\% \le Q < 75\%$
- **Needs Attention**: $Q < 50\%$

---

## 3. Cleaning & Transformation Capabilities

### A. Missing Value Imputation & Treatment
- **Numeric Columns**:
  - `mean_replacement`: Imputes nulls with the arithmetic mean.
  - `median_replacement`: Imputes nulls with the median (robust against skewed distributions).
  - `constant_replacement`: Imputes nulls with a user-specified numerical constant.
  - `remove_rows`: Drops rows with nulls in the selected column.
  - `remove_column`: Drops the column from the cleaned dataset.
- **Categorical Columns**:
  - `mode_replacement`: Imputes nulls with the most frequent category.
  - `constant_replacement`: Imputes nulls with a user-specified string (e.g., `"Unknown"`).
  - `remove_rows`: Drops rows with nulls in the selected column.
  - `remove_column`: Drops the column.
- **Edge-Case Resilience**: Safely handles 100% missing columns, columns without numeric entries, and multi-modal categorical distributions.

### B. Duplicate Record Removal
- Identifies identical row tuples across all features.
- Supports retention policies: `keep="first"` (chronologically earliest) or `keep="last"` (chronologically latest).
- Recalculates dataset dimensions and quality scores dynamically.

### C. Data Type Conversion & Schema Casting
- Target semantic types: `integer` (nullable Int64), `float` (Float64), `string` (text), `boolean` (truthy/falsy parsing), and `datetime` (ISO parsing).
- Non-convertible value detection with safe coercion mode (`force_coercion=True` sets invalid entries to null rather than failing the pipeline).

### D. Outlier Detection & Treatment
- **IQR Rule**: Calculates Q1, Q3, $\text{IQR} = Q3 - Q1$, Lower Bound ($Q1 - 1.5 \times \text{IQR}$), Upper Bound ($Q3 + 1.5 \times \text{IQR}$).
- **Z-Score Rule**: Calculates mean ($\mu$), standard deviation ($\sigma$), with configurable threshold ($Z > 2.0, 2.5, 3.0, 3.5$).
- **Advisory Notice**: Educational communication explaining that statistical outliers are not necessarily errors and may represent authentic high-value business events.
- **Treatment Actions**:
  - `keep`: Retains outliers (informational inspection).
  - `cap_values`: Winsorizes extreme values to the calculated upper and lower boundaries.
  - `remove_rows`: Removes rows outside the statistical boundary.
- **Explicit Confirmation**: Requires user confirmation before executing destructive outlier modifications.

---

## 4. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/datasets/{id}/cleaning/profile` | Computes quality score, missing metrics, and outlier boundaries |
| `POST` | `/api/v1/datasets/{id}/cleaning/preview` | In-memory simulation returning affected counts, warnings, and diffs |
| `POST` | `/api/v1/datasets/{id}/cleaning/apply` | Applies transformation, creates undo snapshot, and verifies SHA-256 |
| `GET` | `/api/v1/datasets/{id}/cleaning/history` | Returns chronological audit trail of applied transformation steps |
| `POST` | `/api/v1/datasets/{id}/cleaning/undo` | Rolls back the latest transformation to snapshot $N-1$ |
| `POST` | `/api/v1/datasets/{id}/cleaning/reset` | Resets all transformations and restores original uploaded dataset |

---

## 5. Acceptance Checklist

- [x] All Phase 1, Phase 2.1, and Phase 2.2 functionality and tests preserved.
- [x] Original uploaded dataset immutability verified with SHA-256 checksums before and after operations.
- [x] Non-destructive architecture with separate cleaned dataset versions (`clean_{id}`).
- [x] Reversible transformation pipeline supporting sequential Undo and complete Reset.
- [x] Standardized, mathematically sound Data Quality Index ($Q = 0.50 \times \text{Comp} + 0.30 \times \text{Valid} + 0.20 \times \text{Uniq}$).
- [x] Missing value handling (mean, median, mode, constant, drop rows, drop column).
- [x] Duplicate row detection and removal (keep first vs. keep last).
- [x] Data type conversion (integer, float, string, boolean, datetime) with safe coercion.
- [x] Outlier detection via IQR and Z-score with educational notice and capping/removal treatments.
- [x] Cleaned dataset seamless integration into existing profiling, preview, KPI cards, and visual dashboards.
- [x] 24 dedicated automated backend tests passing in `backend/tests/test_cleaning_api.py` (61 total passing backend tests).
- [x] Frontend TypeScript compilation and production build passing with 0 errors.

