# Phase 2.1 — Dataset Ingestion, Quality Profiling & Safe Serialization

**Status:** Completed and Verified  
**Brand:** Powered by Saniya  
**Tagline:** Your Autonomous Data Analyst  

---

## Included in Phase 2.1

### 1. Backend Ingestion & Real Pandas Profiling
- **Multi-Format Ingestion**: Upload support for `.csv`, `.xlsx` (via `openpyxl`), and `.xls` (via `xlrd`) with automatic UTF-8 and Latin-1 decoding fallbacks.
- **Resource Limits & Guardrails**:
  - Configurable upload size limit (`MAX_UPLOAD_SIZE_MB = 25`, returns HTTP 413).
  - Maximum row limit (`MAX_DATASET_ROWS = 100,000`, returns HTTP 400).
  - Maximum column limit (`MAX_DATASET_COLUMNS = 200`, returns HTTP 400).
  - Empty file and header-only empty dataset validation (returns HTTP 400).
- **Atomic Upload & Cleanup**: Guaranteed cleanup of partial / temporary files if upload streaming, decoding, or validation fails.
- **Security & Privacy**:
  - Unpredictable 32-character hexadecimal dataset identifiers (`uuid.uuid4().hex`).
  - Strict prevention of internal server filesystem paths leaking into API responses.
- **Pandas Statistical Profiling**:
  - **Dataset Overview**: Row count, column count, total cells, missing cells count & percentage, duplicate rows count & percentage, memory footprint (bytes and human-readable).
  - **Column Profiling**: Semantic data type detection (`integer`, `float`, `string`, `boolean`, `datetime`), raw dtype, non-null/null counts, null percentage, cardinality (distinct count), uniqueness check.
  - **Numeric Distributions**: Min, max, mean, standard deviation, median, 25th percentile (Q25), 75th percentile (Q75), zeros count, negative count.
  - **Categorical Distributions**: Top frequent categories with occurrence counts.
  - **Datetime Bounds**: Minimum and maximum timestamps.
- **Safe JSON Serialization**:
  - Recursive sanitizer converting `NaN`, `NaT`, `+Infinity`, and `-Infinity` into standard JSON `null`.
  - Type-casting of NumPy scalars (`int64`, `float64`, `bool_`, `ndarray`) into standard Python primitives.

### 2. Frontend Workspace UI & Real-Time Analytics
- **Drag-and-Drop & File Picker**: Intuitive dropzone with accepted format specs, drag-over glow, and file constraints (`WelcomeBanner.tsx`).
- **Meaningful Lifecycle States**:
  - **Idle**: Clean upload trigger with format specifications.
  - **Processing**: Honest spinner with status message ("Profiling dataset...").
  - **Success**: Notification toast displaying parsed filename, rows, and columns.
  - **Error**: Dismissible error alert banner rendering actual backend error messages.
  - **Empty**: Helpful empty state when no datasets are loaded.
- **Real Backend Data Binding**:
  - **KPI Summary Cards**: Actual dataset counts, active row count, active columns distribution, and data completeness percentage (`MetricsSummary.tsx`).
  - **Active Dataset Selector**: Quick switcher pills for loaded datasets with deletion controls (`DatasetSelector.tsx`).
  - **Dataset Overview Card**: Detailed quality breakdown including completeness score, duplicate rows, missing cells, and memory footprint (`DatasetOverviewCard.tsx`).
  - **Schema & Columns Profiler**: Filterable column cards by name and data type, displaying statistical metrics, uniqueness tags, top categories, and sample values (`ColumnProfileView.tsx`).
  - **Interactive Data Preview**: Scrollable table rendering real backend rows with sticky headers, column types, styled null values (`null`), and paginated row navigation (`DatasetPreviewTable.tsx`).
  - **Dataset History**: Session activity feed displaying recently profiled datasets with quick inspection links (`RecentActivityPanel.tsx`).

---

## API Endpoints Added

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/datasets/upload` | Upload CSV, XLSX, or XLS file and generate profiling |
| `GET` | `/api/v1/datasets` | List all uploaded datasets and workspace totals |
| `GET` | `/api/v1/datasets/{id}` | Get full profile metadata, column stats, and preview |
| `GET` | `/api/v1/datasets/{id}/profile` | Dedicated column profiling and distributions endpoint |
| `GET` | `/api/v1/datasets/{id}/preview` | Paginated raw dataset records (`limit`, `offset`) |
| `DELETE` | `/api/v1/datasets/{id}` | Delete dataset and clean up disk storage |

---

## Phase 2.1 Acceptance Checklist

- [x] All Phase 1 functionality, branding, and theme toggling fully preserved.
- [x] Real CSV, XLSX, and XLS ingestion with Pandas profiling implemented.
- [x] Configurable upload size (25 MB), row (100k), and column (200) limits enforced.
- [x] Automatic cleanup of temporary files on failed or invalid uploads verified.
- [x] Safe JSON serialization eliminating NaN, NaT, and infinity values verified.
- [x] Secure, unpredictable 32-hex dataset IDs with zero file path exposure verified.
- [x] Frontend displays exclusively real backend statistics (no fabricated data).
- [x] Meaningful upload, loading, error, success, and empty states implemented.
- [x] Dataset persistence across backend reboots verified with atomic metadata sync.
- [x] Automated test suite with 23 passing unit/integration tests (`backend/tests/`).
- [x] TypeScript builds cleanly with zero errors (`tsc -b && vite build`).

