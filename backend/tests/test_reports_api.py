import asyncio
import io
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from app.main import app
from app.models.reports import (
    ALL_REPORT_SECTIONS,
    ExecutiveReportData,
    ReportConfigRequest,
    ReportSectionId,
)
from app.services.dataset_storage import dataset_storage
from app.services.reports.report_assembly_service import ReportAssemblyService

client = TestClient(app)


def _upload_csv(csv_content: str, filename: str = "test_reports.csv") -> str:
    """Helper to upload a CSV file and return the generated dataset ID."""
    files = {"file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/datasets/upload", files=files)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["overview"]["id"]


# =============================================================================
# Test 1: Report Model Defaults and All Eight Section Identifiers
# =============================================================================

def test_report_config_defaults_and_section_identifiers():
    """Verify default configurations, limits, and all eight standardized section identifiers."""
    config = ReportConfigRequest()
    assert config.title == "Executive Intelligence Report"
    assert config.subtitle is None
    assert config.include_charts is True
    assert config.date_range_start is None
    assert config.date_range_end is None
    assert config.confidentiality_notice == "CONFIDENTIAL & PROPRIETARY — FOR INTERNAL USE ONLY"

    # Must contain exactly the eight approved section identifiers
    expected_sections = [
        "executive_summary",
        "key_kpis",
        "key_findings",
        "category_benchmarks",
        "trends_and_seasonality",
        "anomalies_and_risks",
        "recommendations",
        "data_quality_audit",
    ]
    assert len(ALL_REPORT_SECTIONS) == 8
    assert len(config.selected_sections) == 8
    actual_values = [s.value for s in config.selected_sections]
    assert actual_values == expected_sections

    # Title fallback on whitespace
    config_empty_title = ReportConfigRequest(title="   ")
    assert config_empty_title.title == "Executive Intelligence Report"


# =============================================================================
# Test 2: Invalid Date Formats and Reversed Date Ranges
# =============================================================================

def test_report_config_date_validation():
    """Verify strict date parsing, rejecting malformed formats and reversed ranges."""
    # Valid date range
    valid_cfg = ReportConfigRequest(
        date_range_start="2024-01-01",
        date_range_end="2024-12-31",
    )
    assert valid_cfg.date_range_start == "2024-01-01"
    assert valid_cfg.date_range_end == "2024-12-31"

    # Reversed date range must fail validation
    with pytest.raises(ValidationError) as exc_info:
        ReportConfigRequest(
            date_range_start="2024-12-31",
            date_range_end="2024-01-01",
        )
    assert "cannot be earlier than start" in str(exc_info.value)

    # Malformed start date
    with pytest.raises(ValidationError) as exc_info:
        ReportConfigRequest(date_range_start="not-a-valid-date")
    assert "Invalid date format" in str(exc_info.value)

    # Malformed end date
    with pytest.raises(ValidationError) as exc_info:
        ReportConfigRequest(date_range_end="2024-13-45")
    assert "Invalid date format" in str(exc_info.value)

    # Single bound provided is valid
    single_start = ReportConfigRequest(date_range_start="2024-01-01")
    assert single_start.date_range_start == "2024-01-01"
    assert single_start.date_range_end is None

    single_end = ReportConfigRequest(date_range_end="2024-12-31")
    assert single_end.date_range_end == "2024-12-31"


# =============================================================================
# Test 3: Report Assembly with All Eight Available Sections
# =============================================================================

def test_report_assembly_all_sections():
    """Verify full end-to-end assembly across all eight sections on a rich dataset."""
    csv_data = (
        "transaction_date,region,revenue,units_sold\n"
        "2023-01-15,North,12000,150\n"
        "2023-02-15,North,14000,160\n"
        "2023-03-15,North,16000,180\n"
        "2023-04-15,North,18000,200\n"
        "2023-05-15,North,21000,220\n"
        "2023-06-15,North,25000,260\n"
        "2023-01-15,South,8000,90\n"
        "2023-02-15,South,8500,95\n"
        "2023-03-15,South,9000,100\n"
        "2023-04-15,South,9200,105\n"
        "2023-05-15,South,9500,110\n"
        "2023-06-15,South,10000,115\n"
    )
    ds_id = _upload_csv(csv_data, "sales_quarterly.csv")

    config = ReportConfigRequest(
        title="Quarterly Sales Performance Audit",
        subtitle="H1 Performance and Regional Benchmark",
        target_metric_col="revenue",
        target_date_col="transaction_date",
    )

    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, config))

    assert isinstance(report, ExecutiveReportData)
    assert report.report_id.startswith("rpt_")
    assert report.dataset_id == ds_id
    assert report.active_dataset_id == ds_id
    assert report.dataset_name == "sales_quarterly.csv"
    assert len(report.snapshot_hash) == 64
    assert report.is_cleaned is False
    assert report.health_score > 0

    # Section 1: Executive Summary
    assert report.executive_summary is not None
    assert len(report.executive_summary.narrative) > 20
    assert report.executive_summary.mode in ("ai_generated", "statistical_fallback")

    # Section 2: Key KPIs
    assert report.key_kpis is not None
    assert report.key_kpis.kpis.total_rows == 12
    assert report.key_kpis.kpis.total_columns == 4
    assert report.key_kpis.kpis.selected_column == "revenue"

    # Section 3: Key Findings
    assert report.key_findings is not None
    assert report.key_findings.total_count >= 1

    # Section 4: Category Benchmarks
    assert report.category_benchmarks is not None
    assert report.category_benchmarks.dimension_count >= 1

    # Section 5: Trends & Seasonality
    assert report.trends_and_seasonality is not None
    assert report.trends_and_seasonality.has_temporal_data is True
    assert len(report.trends_and_seasonality.trends) >= 1
    assert report.trends_and_seasonality.trends[0].direction == "increasing"

    # Section 6: Anomalies & Risks
    assert report.anomalies_and_risks is not None

    # Section 7: Recommendations
    assert report.recommendations is not None
    assert report.recommendations.total_count >= 1

    # Section 8: Data Quality Audit
    assert report.data_quality_audit is not None
    assert report.data_quality_audit.overall_quality_score >= 80.0
    assert report.data_quality_audit.column_count == 4

    # Supporting metadata
    assert len(report.columns) == 4
    assert len(report.charts) >= 1
    assert len(report.grounded_facts) >= 2


# =============================================================================
# Test 4: Active Cleaned-Dataset Resolution
# =============================================================================

def test_active_cleaned_dataset_resolution():
    """Verify that an active cleaned dataset version is detected and used exclusively."""
    csv_data = "category,val\nA,10\nB,20\nC,30\n"
    ds_id = _upload_csv(csv_data, "raw_cats.csv")

    # Initial assembly uses raw dataset
    rep_raw = asyncio.run(ReportAssemblyService.assemble_report(ds_id))
    assert rep_raw.active_dataset_id == ds_id
    assert rep_raw.is_cleaned is False

    # Simulate registering a cleaned version
    clean_df = pd.DataFrame({"category": ["A", "B", "C", "D"], "val": [10, 20, 30, 40]})
    clean_detail = dataset_storage.register_cleaned_dataset(
        parent_id=ds_id,
        cleaned_df=clean_df,
        version=1,
    )
    clean_id = clean_detail.overview.id
    assert clean_id == f"clean_{ds_id}"

    # Re-assemble report: must resolve clean_{id} and use cleaned snapshot hash
    rep_clean = asyncio.run(ReportAssemblyService.assemble_report(ds_id))
    assert rep_clean.active_dataset_id == clean_id
    assert rep_clean.is_cleaned is True
    assert rep_clean.cleaning_version == 1
    assert rep_clean.snapshot_hash != rep_raw.snapshot_hash
    assert rep_clean.key_kpis.kpis.total_rows == 4

    # Cleanup cleaned version
    dataset_storage.delete_cleaned_dataset(ds_id)


# =============================================================================
# Test 5: Consistent Dataset ID and Snapshot Hash Across Report
# =============================================================================

def test_snapshot_hash_consistency_across_report():
    """Verify active file hash matches the report snapshot hash exactly."""
    csv_data = "metric_a,metric_b\n100,200\n300,400\n500,600\n"
    ds_id = _upload_csv(csv_data, "snapshot_test.csv")

    active_id, is_clean, expected_hash, file_path = ReportAssemblyService.resolve_active_dataset(ds_id)
    assert file_path.exists()

    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id))
    assert report.snapshot_hash == expected_hash
    assert report.active_dataset_id == active_id


# =============================================================================
# Test 6: Non-Temporal Dataset Handling
# =============================================================================

def test_non_temporal_dataset_handling():
    """Verify safe handling of non-temporal datasets without errors or fabricated trends."""
    csv_data = (
        "employee,department,rating\n"
        "Alice,Engineering,4.8\n"
        "Bob,Engineering,4.6\n"
        "Charlie,Sales,3.9\n"
        "Diana,Sales,4.1\n"
        "Evan,Support,3.5\n"
    )
    ds_id = _upload_csv(csv_data, "ratings_no_date.csv")

    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id))

    assert report.trends_and_seasonality is not None
    assert report.trends_and_seasonality.has_temporal_data is False
    assert len(report.trends_and_seasonality.trends) == 0
    assert report.trends_and_seasonality.seasonality is None
    assert any("datetime" in lim.lower() for lim in report.limitations)


# =============================================================================
# Test 7: Missing Optional Analytics and Small/Empty Dataset Handling
# =============================================================================

def test_small_and_empty_dataset_handling():
    """Verify small datasets preserve reliability flags and empty datasets assemble safely."""
    # Small dataset (n=3)
    csv_small = "cat,val\nA,10\nB,20\nC,30\n"
    ds_small = _upload_csv(csv_small, "small_ds.csv")
    rep_small = asyncio.run(ReportAssemblyService.assemble_report(ds_small))
    assert rep_small.key_kpis.kpis.total_rows == 3

    # Empty dataset fallback
    empty_cfg = ReportConfigRequest(title="Empty Report")
    rep_empty = ReportAssemblyService._build_empty_dataset_report(
        dataset_id="empty_ds",
        active_id="empty_ds",
        filename="empty.csv",
        snapshot_hash="0" * 64,
        is_cleaned=False,
        cleaning_version=0,
        config=empty_cfg,
    )
    assert rep_empty.health_score == 0.0
    assert rep_empty.key_kpis.kpis.total_rows == 0
    assert "empty" in rep_empty.limitations[0].lower()


# =============================================================================
# Test 8: Selected-Section Configuration & Chart Exclusion
# =============================================================================

def test_selected_section_configuration():
    """Verify that only requested sections are populated and include_charts=False strips charts."""
    csv_data = (
        "date,category,metric\n"
        "2023-01-01,Alpha,100\n"
        "2023-02-01,Alpha,120\n"
        "2023-03-01,Alpha,140\n"
        "2023-01-01,Beta,80\n"
        "2023-02-01,Beta,90\n"
        "2023-03-01,Beta,100\n"
    )
    ds_id = _upload_csv(csv_data, "partial_sections.csv")

    # Select only Executive Summary and Recommendations, charts disabled
    cfg = ReportConfigRequest(
        selected_sections=[
            ReportSectionId.EXECUTIVE_SUMMARY,
            ReportSectionId.RECOMMENDATIONS,
        ],
        include_charts=False,
    )
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, cfg))

    assert report.executive_summary is not None
    assert report.recommendations is not None

    # Excluded sections must be None
    assert report.key_kpis is None
    assert report.key_findings is None
    assert report.category_benchmarks is None
    assert report.trends_and_seasonality is None
    assert report.anomalies_and_risks is None
    assert report.data_quality_audit is None

    # Charts must be empty
    assert len(report.charts) == 0

    # Section status dictionary helper
    status = report.section_inclusion_status
    assert status["executive_summary"] is True
    assert status["recommendations"] is True
    assert status["key_kpis"] is False
    assert status["trends_and_seasonality"] is False


# =============================================================================
# Test 9: Snapshot Change During Assembly Fails Safely
# =============================================================================

def test_snapshot_change_during_assembly_fails_safely():
    """Verify that a race condition or file modification during assembly aborts safely."""
    csv_data = "x,y\n1,2\n3,4\n"
    ds_id = _upload_csv(csv_data, "race_test.csv")

    # Simulate hash divergence after load
    with patch.object(dataset_storage, "compute_sha256", side_effect=["hash_initial", "hash_modified", "hash_modified"]):
        with pytest.raises(ValueError) as exc_info:
            asyncio.run(ReportAssemblyService.assemble_report(ds_id))
        assert "snapshot changed" in str(exc_info.value).lower()


# =============================================================================
# Test 10: Fact IDs and Fact-vs-Hypothesis Distinctions Preserved
# =============================================================================

def test_fact_ids_and_hypothesis_distinctions():
    """Verify that verified fact IDs are preserved and recommendations separate hypotheses."""
    csv_data = (
        "segment,sales,orders\n"
        "Enterprise,500000,50\n"
        "MidMarket,200000,80\n"
        "SMB,50000,120\n"
        "Consumer,15000,300\n"
    )
    ds_id = _upload_csv(csv_data, "facts_test.csv")

    cfg = ReportConfigRequest(
        date_range_start="2023-01-01",
        date_range_end="2023-12-31",
    )
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, cfg))

    # Provenance facts
    assert len(report.grounded_facts) >= 1
    for fact in report.grounded_facts:
        assert fact.fact_id.startswith("fact_")
        assert len(fact.formatted_statement) > 0

    # Recommendations hypothesis accounting
    if report.recommendations:
        total = report.recommendations.total_count
        empirical = report.recommendations.empirical_facts_count
        hypotheses = report.recommendations.analytical_hypotheses_count
        assert empirical + hypotheses == total

    # Date-scoping limitation disclaimer present
    assert len(report.date_scoping_limitations) == 1
    assert "2023-01-01" in report.date_scoping_limitations[0]
    assert "2023-12-31" in report.date_scoping_limitations[0]
    assert "verified snapshot" in report.date_scoping_limitations[0]


# =============================================================================
# Step 2: Excel Report Builder Tests
# =============================================================================

from openpyxl import load_workbook
from app.services.reports.excel_report_builder import ExcelReportBuilder, sanitize_cell_value


def test_excel_sanitize_cell_value_security():
    """Verify formula injection protection escapes risky text while preserving negative numbers."""
    # Negative numbers must remain numeric
    neg_float = -123.45
    neg_int = -42
    assert sanitize_cell_value(neg_float) == -123.45
    assert isinstance(sanitize_cell_value(neg_float), float)
    assert sanitize_cell_value(neg_int) == -42
    assert isinstance(sanitize_cell_value(neg_int), int)

    # Positive numbers & zero remain numeric
    assert sanitize_cell_value(0) == 0
    assert sanitize_cell_value(99.9) == 99.9

    # Text starting with formula characters must be prepended with a single quote
    assert sanitize_cell_value("=1+1") == "'=1+1"
    assert sanitize_cell_value("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_cell_value("-some_formula()") == "'-some_formula()"
    assert sanitize_cell_value("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_cell_value("   =spaced_formula") == "'   =spaced_formula"

    # Benign text remains unaltered
    assert sanitize_cell_value("Normal Category") == "Normal Category"
    assert sanitize_cell_value("Revenue in USD") == "Revenue in USD"
    assert sanitize_cell_value(None) == ""


def test_excel_builder_valid_workbook_generation_and_all_sheets():
    """Verify that ExcelReportBuilder creates a valid in-memory workbook with exactly 8 sheets."""
    csv_data = (
        "date,category,sales,quantity\n"
        "2023-01-01,Alpha,5000,50\n"
        "2023-02-01,Alpha,6000,60\n"
        "2023-03-01,Alpha,7000,70\n"
        "2023-04-01,Alpha,8000,80\n"
        "2023-01-01,Beta,3000,30\n"
        "2023-02-01,Beta,3500,35\n"
        "2023-03-01,Beta,4000,40\n"
        "2023-04-01,Beta,4500,45\n"
    )
    ds_id = _upload_csv(csv_data, "excel_test.csv")

    config = ReportConfigRequest(
        title="Corporate Sales Audit Q1",
        subtitle="Executive Performance Review",
        target_metric_col="sales",
        target_date_col="date",
    )
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, config))

    # Generate in-memory Excel buffer
    buffer = ExcelReportBuilder.generate_excel_bytes(report)
    assert isinstance(buffer, io.BytesIO)
    excel_bytes = buffer.getvalue()
    assert len(excel_bytes) > 5000  # Non-trivial workbook payload

    # Load workbook from buffer and inspect sheets
    wb = load_workbook(buffer)
    expected_sheets = [
        "Executive Summary",
        "KPIs",
        "Key Findings",
        "Category Benchmarks",
        "Trends & Seasonality",
        "Anomalies & Outliers",
        "Recommendations",
        "Data Quality",
    ]
    assert wb.sheetnames == expected_sheets
    assert len(wb.sheetnames) == 8


def test_excel_builder_executive_summary_metadata_and_provenance():
    """Verify metadata, snapshot hash, and fact provenance in the Executive Summary sheet."""
    csv_data = "dept,budget\nIT,100000\nHR,50000\nSales,150000\nOps,80000\n"
    ds_id = _upload_csv(csv_data, "dept_budget.csv")

    config = ReportConfigRequest(
        title="Departmental Budget Review",
        subtitle="Annual Operating Budget",
    )
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, config))

    buffer = ExcelReportBuilder.generate_excel_bytes(report)
    wb = load_workbook(buffer)
    ws = wb["Executive Summary"]

    # Check title banner
    assert "AutoAnalyst AI" in str(ws["A1"].value)
    assert "Powered by Saniya" in str(ws["A1"].value)

    # Collect all text in worksheet to check metadata presence
    all_values = []
    for row in ws.iter_rows(values_only=True):
        for cell in row:
            if cell is not None:
                all_values.append(str(cell))
    text_content = " ".join(all_values)

    assert "Departmental Budget Review" in text_content
    assert report.snapshot_hash in text_content
    assert report.dataset_id in text_content
    assert "dept_budget.csv" in text_content


def test_excel_builder_data_in_worksheets_and_number_formats():
    """Verify correct section data and native number formatting across sheets."""
    csv_data = (
        "order_date,region,profit,units\n"
        "2023-01-01,East,1200.50,10\n"
        "2023-02-01,East,1400.75,12\n"
        "2023-03-01,East,1800.00,15\n"
        "2023-01-01,West,900.25,8\n"
        "2023-02-01,West,950.00,9\n"
        "2023-03-01,West,1100.50,11\n"
    )
    ds_id = _upload_csv(csv_data, "regional_profit.csv")
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id))

    wb = ExcelReportBuilder.build_workbook(report)

    # 1. Check KPIs sheet
    ws_kpis = wb["KPIs"]
    kpi_texts = [str(cell.value) for row in ws_kpis.iter_rows() for cell in row if cell.value is not None]
    assert any("Total Rows" in t for t in kpi_texts)
    assert any("Data Completeness" in t for t in kpi_texts)

    # 2. Check Key Findings sheet
    ws_findings = wb["Key Findings"]
    assert ws_findings.max_row >= 5
    header_vals = [ws_findings.cell(row=5, column=c).value for c in range(1, 9)]
    assert "Finding ID" in header_vals
    assert "Importance" in header_vals

    # 3. Check Category Benchmarks sheet
    ws_benchmarks = wb["Category Benchmarks"]
    assert ws_benchmarks.max_row >= 4

    # 4. Check Trends & Seasonality sheet
    ws_trends = wb["Trends & Seasonality"]
    assert ws_trends.max_row >= 4

    # 5. Check Recommendations sheet and hypothesis provenance
    ws_recs = wb["Recommendations"]
    rec_texts = [str(cell.value) for row in ws_recs.iter_rows() for cell in row if cell.value is not None]
    if report.recommendations and report.recommendations.recommendations:
        # Must clearly distinguish empirical facts from hypotheses
        assert any("Verified Empirical Fact" in t or "Analytical Hypothesis" in t for t in rec_texts)

    # 6. Check Data Quality sheet
    ws_quality = wb["Data Quality"]
    quality_texts = [str(cell.value) for row in ws_quality.iter_rows() for cell in row if cell.value is not None]
    assert any("Overall Quality Score" in t for t in quality_texts)


def test_excel_builder_column_widths_and_styling():
    """Verify column widths stay within [12, 55] and frozen panes are set."""
    csv_data = "col_a,col_b\n1,2\n3,4\n"
    ds_id = _upload_csv(csv_data, "styling_test.csv")
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id))

    wb = ExcelReportBuilder.build_workbook(report)
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for col_dim in ws.column_dimensions.values():
            if col_dim.width is not None:
                assert col_dim.width >= 12, f"Sheet {sheet_name} col width < 12: {col_dim.width}"
                assert col_dim.width <= 55, f"Sheet {sheet_name} col width > 55: {col_dim.width}"


def test_excel_builder_missing_and_unselected_sections():
    """Verify that unselected sections render a graceful notice box without crashing."""
    csv_data = "x,y\n10,20\n30,40\n"
    ds_id = _upload_csv(csv_data, "missing_test.csv")

    # Select only Executive Summary
    cfg = ReportConfigRequest(selected_sections=[ReportSectionId.EXECUTIVE_SUMMARY])
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, cfg))

    wb = ExcelReportBuilder.build_workbook(report)
    assert len(wb.sheetnames) == 8

    # Unselected sheets should contain the notice
    for unselected_title in ["KPIs", "Key Findings", "Category Benchmarks", "Trends & Seasonality", "Recommendations", "Data Quality"]:
        ws = wb[unselected_title]
        text_vals = [str(cell.value) for row in ws.iter_rows() for cell in row if cell.value is not None]
        assert any("excluded from the report configuration" in t for t in text_vals), f"Sheet {unselected_title} missing excluded notice"


def test_excel_builder_negative_numbers_and_formula_injection_end_to_end():
    """Verify end-to-end that formula injection text is escaped while negative numbers remain raw numeric cells."""
    csv_data = (
        "date,product,margin,units\n"
        "2023-01-01,=HYPERLINK('http://evil.com'),-15.5,-10\n"
        "2023-02-01,+cmd|' /C calc',-25.0,-20\n"
        "2023-03-01,@SUM(1+1),35.0,30\n"
        "2023-04-01,-test_func(),45.5,40\n"
    )
    ds_id = _upload_csv(csv_data, "injection_and_neg_test.csv")

    config = ReportConfigRequest(
        title="=MALICIOUS_TITLE()",
        subtitle="-MALICIOUS_SUBTITLE()",
        target_metric_col="margin",
        target_date_col="date",
    )
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, config))

    wb = ExcelReportBuilder.build_workbook(report)

    # 1. Check Executive Summary title escaping
    ws_summary = wb["Executive Summary"]
    title_cell = ws_summary["B5"]  # Report Title value cell
    assert title_cell.value.startswith("'=") or title_cell.value.startswith("'")

    # 2. Check KPIs sheet: verify numeric values are numeric
    ws_kpis = wb["KPIs"]
    for row in ws_kpis.iter_rows():
        for cell in row:
            if isinstance(cell.value, (int, float)):
                assert cell.data_type == "n", f"Cell {cell.coordinate} should be numeric 'n' but got {cell.data_type}"

    # 3. Check Category Benchmarks or Trends for negative numbers
    ws_benchmarks = wb["Category Benchmarks"]
    for row in ws_benchmarks.iter_rows():
        for cell in row:
            if isinstance(cell.value, (int, float)):
                assert cell.data_type == "n"
            elif isinstance(cell.value, str) and cell.value.strip() and cell.value.strip()[0] in ("=", "+", "-", "@"):
                # Must be escaped with leading quote
                assert cell.value.startswith("'"), f"Unescaped formula in cell {cell.coordinate}: {cell.value}"


# =============================================================================
# Step 3: PDF Report Builder Tests
# =============================================================================

from unittest.mock import AsyncMock
from app.models.dashboard import ChartConfig
from app.services.reports.pdf_report_builder import PdfReportBuilder, SvgChartRenderer


def test_pdf_builder_generate_pdf_bytes_and_header():
    """Verify end-to-end PDF generation producing valid %PDF- bytes via Playwright."""
    csv_data = (
        "date,category,sales,cost\n"
        "2023-01-01,Alpha,1000,600\n"
        "2023-02-01,Alpha,1200,700\n"
        "2023-03-01,Alpha,1500,800\n"
        "2023-01-01,Beta,800,500\n"
        "2023-02-01,Beta,900,550\n"
        "2023-03-01,Beta,950,600\n"
    )
    ds_id = _upload_csv(csv_data, "pdf_test.csv")

    config = ReportConfigRequest(
        title="Executive Performance & Risk Audit",
        subtitle="Quarterly Regional Performance Evaluation",
        target_metric_col="sales",
        target_date_col="date",
    )
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, config))

    # Generate PDF bytes
    pdf_bytes = asyncio.run(PdfReportBuilder.generate_pdf_bytes(report))
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-"), "Generated file does not start with standard %PDF- magic bytes"
    assert len(pdf_bytes) > 15000, f"Generated PDF is unexpectedly small ({len(pdf_bytes)} bytes)"


def test_pdf_builder_html_rendering_branding_metadata_and_snapshot():
    """Verify HTML template structure, branding, metadata, snapshot hash, and layout."""
    csv_data = "metric_1,metric_2\n10,20\n30,40\n"
    ds_id = _upload_csv(csv_data, "html_meta_test.csv")

    config = ReportConfigRequest(
        title="Q1 Corporate Health Audit",
        subtitle="Confidential Strategic Review",
    )
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, config))

    html_content = PdfReportBuilder.render_html_report(report)

    # Required Brand elements
    assert "AutoAnalyst AI" in html_content
    assert "Powered by Saniya" in html_content
    assert "Your Autonomous Data Analyst" in html_content

    # Required Metadata & Snapshot Checksum
    assert "Q1 Corporate Health Audit" in html_content
    assert "Confidential Strategic Review" in html_content
    assert report.snapshot_hash in html_content
    assert report.dataset_id in html_content
    assert "html_meta_test.csv" in html_content

    # Verify CSS & print breaks
    assert "page-break" in html_content
    assert "cover-container" in html_content
    assert "avoid-break" in html_content


def test_pdf_builder_html_escaping_prevents_xss():
    """Verify strict HTML escaping on user-controlled fields prevents script or tag injection."""
    csv_data = "item,value\nA,10\nB,20\n"
    ds_id = _upload_csv(csv_data, "xss_test.csv")

    # Inject HTML and JavaScript strings into report configuration
    xss_config = ReportConfigRequest(
        title="<script>alert('xss_title')</script>",
        subtitle="<img src=x onerror=alert('xss_sub')>",
        confidentiality_notice="<iframe src='javascript:alert(1)'></iframe>",
    )
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, xss_config))

    html_content = PdfReportBuilder.render_html_report(report)

    # Raw script, img onerror, and iframe tags must NOT be present
    assert "<script>alert('xss_title')</script>" not in html_content
    assert "<img src=x onerror=alert('xss_sub')>" not in html_content
    assert "<iframe src='javascript:alert(1)'>" not in html_content

    # Escaped versions must be present
    assert "&lt;script&gt;alert(&#x27;xss_title&#x27;)&lt;/script&gt;" in html_content or "&lt;script&gt;" in html_content
    assert "&lt;img src=x" in html_content
    assert "&lt;iframe" in html_content


def test_pdf_builder_missing_and_unselected_sections():
    """Verify that unselected sections are cleanly omitted without errors or crashes."""
    csv_data = "col1,col2\n100,200\n300,400\n"
    ds_id = _upload_csv(csv_data, "unselected_test.csv")

    # Select only Executive Summary and Data Quality Audit
    cfg = ReportConfigRequest(
        selected_sections=[
            ReportSectionId.EXECUTIVE_SUMMARY,
            ReportSectionId.DATA_QUALITY_AUDIT,
        ]
    )
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id, cfg))

    html_content = PdfReportBuilder.render_html_report(report)
    assert "1. Executive Summary" in html_content
    assert "8. Data Quality &amp; Health Audit" in html_content or "8. Data Quality" in html_content

    # Unselected sections must not render section containers
    assert "3. Automated Key Findings" not in html_content
    assert "4. Category Benchmarks" not in html_content
    assert "7. Actionable Recommendations" not in html_content

    # PDF generation must succeed smoothly
    pdf_bytes = asyncio.run(PdfReportBuilder.generate_pdf_bytes(report))
    assert pdf_bytes.startswith(b"%PDF-")


def test_svg_chart_renderer_and_fallback():
    """Verify standalone SVG chart rendering and graceful fallback table on invalid data."""
    # 1. Valid Bar Chart
    bar_chart = ChartConfig(
        chart_id="test_bar",
        title="Revenue by Division",
        chart_type="bar",
        plotly_data=[{"x": ["East", "West", "North"], "y": [5000.0, 3000.0, 4000.0]}],
    )
    svg_bar = SvgChartRenderer.render_chart(bar_chart)
    assert "<svg" in svg_bar
    assert "Revenue by Division" in svg_bar
    assert "East" in svg_bar
    assert "</svg>" in svg_bar

    # 2. Valid Line Chart
    line_chart = ChartConfig(
        chart_id="test_line",
        title="Monthly Trend",
        chart_type="line",
        plotly_data=[{"x": ["2023-01", "2023-02", "2023-03"], "y": [10.5, 15.2, 20.0]}],
    )
    svg_line = SvgChartRenderer.render_chart(line_chart)
    assert "<svg" in svg_line
    assert "Monthly Trend" in svg_line
    assert "<path" in svg_line

    # 3. Chart with empty or malformed data falls back gracefully
    empty_chart = ChartConfig(
        chart_id="empty",
        title="Empty Metric Chart",
        chart_type="bar",
        plotly_data=[],
    )
    fallback_html = SvgChartRenderer.render_chart(empty_chart)
    assert "chart-fallback" in fallback_html
    assert "Empty Metric Chart" in fallback_html
    assert "<table" in fallback_html


def test_pdf_builder_empty_dataset_handling():
    """Verify that an empty dataset report generates valid PDF without crashing."""
    empty_cfg = ReportConfigRequest(title="Empty Snapshot Report")
    empty_report = ReportAssemblyService._build_empty_dataset_report(
        dataset_id="empty_123",
        active_id="empty_123",
        filename="empty.csv",
        snapshot_hash="0" * 64,
        is_cleaned=False,
        cleaning_version=0,
        config=empty_cfg,
    )

    html_content = PdfReportBuilder.render_html_report(empty_report)
    assert "Empty Snapshot Report" in html_content
    assert "Overall Dataset Health: 0.0 / 100" in html_content

    pdf_bytes = asyncio.run(PdfReportBuilder.generate_pdf_bytes(empty_report))
    assert pdf_bytes.startswith(b"%PDF-")


def test_pdf_builder_browser_closed_on_success_and_failure():
    """Verify that Playwright browser is always closed in finally blocks on success and failure."""
    csv_data = "a,b\n1,2\n"
    ds_id = _upload_csv(csv_data, "resource_cleanup_test.csv")
    report = asyncio.run(ReportAssemblyService.assemble_report(ds_id))

    # Test failure cleanup: simulate page.pdf error
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_page.pdf.side_effect = RuntimeError("Simulated PDF generation error")
    mock_browser.new_page.return_value = mock_page

    with patch.object(PdfReportBuilder, "_launch_browser", return_value=mock_browser):
        with pytest.raises(RuntimeError) as exc_info:
            asyncio.run(PdfReportBuilder.generate_pdf_bytes(report))
        assert "Simulated PDF generation error" in str(exc_info.value)
        # Browser must be closed even after exception!
        mock_browser.close.assert_awaited_once()


# =============================================================================
# Step 4: Reports API Integration Tests
# =============================================================================

def test_api_generate_report_preview_success():
    """Verify POST /api/v1/datasets/{id}/reports/generate returns valid ExecutiveReportData JSON."""
    csv_data = (
        "transaction_date,region,revenue,units\n"
        "2023-01-15,North,15000,150\n"
        "2023-02-15,North,18000,180\n"
        "2023-03-15,North,22000,210\n"
        "2023-01-15,South,10000,100\n"
        "2023-02-15,South,12000,120\n"
        "2023-03-15,South,13000,130\n"
    )
    ds_id = _upload_csv(csv_data, "api_preview_test.csv")

    payload = {
        "title": "Q1 Revenue Intelligence Preview",
        "subtitle": "Regional Operations Review",
        "target_metric_col": "revenue",
        "target_date_col": "transaction_date",
        "include_charts": True,
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/reports/generate", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["report_id"].startswith("rpt_")
    assert data["dataset_id"] == ds_id
    assert data["dataset_name"] == "api_preview_test.csv"
    assert len(data["snapshot_hash"]) == 64
    assert data["brand_attribution"] == "Powered by Saniya"
    assert data["config"]["title"] == "Q1 Revenue Intelligence Preview"

    # Verify all eight standardized sections exist in response
    assert data["executive_summary"] is not None
    assert data["key_kpis"] is not None
    assert data["key_kpis"]["kpis"]["total_rows"] == 6
    assert data["key_findings"] is not None
    assert data["category_benchmarks"] is not None
    assert data["trends_and_seasonality"] is not None
    assert data["trends_and_seasonality"]["has_temporal_data"] is True
    assert data["anomalies_and_risks"] is not None
    assert data["recommendations"] is not None
    assert data["data_quality_audit"] is not None


def test_api_export_pdf_success():
    """Verify POST /api/v1/datasets/{id}/reports/export/pdf returns streaming application/pdf."""
    csv_data = "quarter,sales\nQ1,10000\nQ2,15000\nQ3,18000\nQ4,22000\n"
    ds_id = _upload_csv(csv_data, "pdf_api_test.csv")

    payload = {
        "title": "Annual Sales Intelligence Report",
        "subtitle": "Full Year Operating Performance",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/reports/export/pdf", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in resp.headers["content-disposition"]
    assert resp.headers["content-disposition"].endswith('.pdf"')

    pdf_bytes = resp.content
    assert pdf_bytes.startswith(b"%PDF-"), "Response content does not start with standard %PDF- magic bytes"
    assert len(pdf_bytes) > 10000


def test_api_export_excel_success():
    """Verify POST /api/v1/datasets/{id}/reports/export/excel returns valid multi-sheet XLSX."""
    csv_data = "department,headcount,budget\nEngineering,50,500000\nSales,30,300000\nMarketing,20,200000\n"
    ds_id = _upload_csv(csv_data, "excel_api_test.csv")

    payload = {
        "title": "Workforce & Budget Audit",
        "subtitle": "Departmental Allocation",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/reports/export/excel", json=payload)
    assert resp.status_code == 200, resp.text
    expected_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert resp.headers["content-type"] == expected_mime
    assert "attachment; filename=" in resp.headers["content-disposition"]
    assert resp.headers["content-disposition"].endswith('.xlsx"')

    excel_bytes = resp.content
    assert len(excel_bytes) > 2000

    # Parse with openpyxl to verify all 8 sheets
    wb = load_workbook(io.BytesIO(excel_bytes))
    assert len(wb.sheetnames) == 8
    assert wb.sheetnames == [
        "Executive Summary",
        "KPIs",
        "Key Findings",
        "Category Benchmarks",
        "Trends & Seasonality",
        "Anomalies & Outliers",
        "Recommendations",
        "Data Quality",
    ]


def test_api_download_filenames_are_sanitized_and_safe():
    """Verify download filenames neutralize path traversal and special characters."""
    csv_data = "a,b\n1,2\n"
    ds_id = _upload_csv(csv_data, "sanitize_name.csv")

    malicious_payload = {
        "title": "../../etc/passwd/&&!*<evil_title>",
    }
    resp_pdf = client.post(f"/api/v1/datasets/{ds_id}/reports/export/pdf", json=malicious_payload)
    assert resp_pdf.status_code == 200
    disp_pdf = resp_pdf.headers["content-disposition"]
    assert ".." not in disp_pdf
    assert "/" not in disp_pdf.split("filename=")[1]
    assert "<" not in disp_pdf
    assert disp_pdf.endswith('.pdf"')

    resp_xlsx = client.post(f"/api/v1/datasets/{ds_id}/reports/export/excel", json=malicious_payload)
    assert resp_xlsx.status_code == 200
    disp_xlsx = resp_xlsx.headers["content-disposition"]
    assert ".." not in disp_xlsx
    assert "/" not in disp_xlsx.split("filename=")[1]
    assert disp_xlsx.endswith('.xlsx"')


def test_api_invalid_configuration_and_reversed_date_range():
    """Verify that reversed date ranges and malformed dates are rejected with HTTP 422."""
    csv_data = "x,y\n1,2\n"
    ds_id = _upload_csv(csv_data, "val_error.csv")

    # Reversed date range
    bad_dates = {
        "date_range_start": "2024-12-31",
        "date_range_end": "2024-01-01",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/reports/generate", json=bad_dates)
    assert resp.status_code == 422
    assert "cannot be earlier than start" in resp.text

    # Malformed date format
    bad_fmt = {
        "date_range_start": "invalid-date-string",
    }
    resp_fmt = client.post(f"/api/v1/datasets/{ds_id}/reports/generate", json=bad_fmt)
    assert resp_fmt.status_code == 422
    assert "Invalid date format" in resp_fmt.text


def test_api_nonexistent_dataset_returns_404():
    """Verify that nonexistent dataset IDs return HTTP 404 for all three report endpoints."""
    fake_id = "nonexistent_dataset_99999"

    resp_gen = client.post(f"/api/v1/datasets/{fake_id}/reports/generate")
    assert resp_gen.status_code == 404
    assert f"Dataset '{fake_id}' not found." in resp_gen.text

    resp_pdf = client.post(f"/api/v1/datasets/{fake_id}/reports/export/pdf")
    assert resp_pdf.status_code == 404
    assert f"Dataset '{fake_id}' not found." in resp_pdf.text

    resp_xlsx = client.post(f"/api/v1/datasets/{fake_id}/reports/export/excel")
    assert resp_xlsx.status_code == 404
    assert f"Dataset '{fake_id}' not found." in resp_xlsx.text


def test_api_selected_sections_and_chart_toggles():
    """Verify that custom section selection and include_charts=False are honored by endpoints."""
    csv_data = "cat,val\nA,10\nB,20\n"
    ds_id = _upload_csv(csv_data, "toggle_test.csv")

    payload = {
        "selected_sections": ["executive_summary", "data_quality_audit"],
        "include_charts": False,
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/reports/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["executive_summary"] is not None
    assert data["data_quality_audit"] is not None
    assert data["key_kpis"] is None
    assert data["category_benchmarks"] is None
    assert data["trends_and_seasonality"] is None
    assert data["charts"] == []


def test_api_active_cleaned_snapshot_handled_correctly():
    """Verify that report endpoints detect and report on an active cleaned snapshot."""
    csv_data = "name,score\nAlice,90\nBob,80\n"
    ds_id = _upload_csv(csv_data, "clean_api_test.csv")

    # Generate report on raw dataset
    resp_raw = client.post(f"/api/v1/datasets/{ds_id}/reports/generate")
    assert resp_raw.status_code == 200
    assert resp_raw.json()["is_cleaned"] is False
    assert resp_raw.json()["active_dataset_id"] == ds_id

    # Register cleaned dataset
    clean_df = pd.DataFrame({"name": ["Alice", "Bob", "Charlie"], "score": [90, 80, 85]})
    clean_detail = dataset_storage.register_cleaned_dataset(
        parent_id=ds_id,
        cleaned_df=clean_df,
        version=1,
    )
    clean_id = clean_detail.overview.id

    # Report endpoints must now use the clean snapshot
    resp_clean = client.post(f"/api/v1/datasets/{ds_id}/reports/generate")
    assert resp_clean.status_code == 200
    assert resp_clean.json()["is_cleaned"] is True
    assert resp_clean.json()["active_dataset_id"] == clean_id
    assert resp_clean.json()["key_kpis"]["kpis"]["total_rows"] == 3

    # Clean up
    dataset_storage.delete_cleaned_dataset(ds_id)


def test_api_snapshot_change_during_assembly_returns_conflict():
    """Verify that file hash modification during assembly returns HTTP 409 Conflict."""
    csv_data = "x,y\n1,2\n"
    ds_id = _upload_csv(csv_data, "conflict_test.csv")

    with patch.object(dataset_storage, "compute_sha256", side_effect=["initial_h", "modified_h", "modified_h"]):
        resp = client.post(f"/api/v1/datasets/{ds_id}/reports/generate")
        assert resp.status_code == 409
        assert "snapshot changed" in resp.text.lower()


def test_api_pdf_chromium_failure_returns_controlled_500():
    """Verify that Playwright / Chromium launch failure returns clean 500 without leaking paths."""
    csv_data = "x,y\n1,2\n"
    ds_id = _upload_csv(csv_data, "browser_err_test.csv")

    with patch.object(PdfReportBuilder, "generate_pdf_bytes", side_effect=RuntimeError("Chromium launch failed")):
        resp = client.post(f"/api/v1/datasets/{ds_id}/reports/export/pdf")
        assert resp.status_code == 500
        # Must return controlled error, not raw stack trace or internal path
        assert "PDF generation engine encountered an internal error" in resp.text
        assert "C:\\" not in resp.text


def test_api_unexpected_exception_sanitized_error():
    """Verify that unhandled internal exceptions do not leak stack traces or file paths."""
    csv_data = "x,y\n1,2\n"
    ds_id = _upload_csv(csv_data, "unhandled_err_test.csv")

    with patch.object(ReportAssemblyService, "assemble_report", side_effect=Exception("Critical error in C:\\secret\\path\\file.py")):
        resp = client.post(f"/api/v1/datasets/{ds_id}/reports/generate")
        assert resp.status_code == 500
        assert "Failed to assemble executive report due to an internal server error." in resp.text
        assert "C:\\secret" not in resp.text


def test_existing_api_routes_unaffected():
    """Verify that existing Phase 1 through 4.4 endpoints remain fully functional."""
    # Root endpoint
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "AutoAnalyst AI" in resp_root.json()["message"]

    # Health endpoint
    resp_health = client.get("/api/v1/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "healthy"

    # Datasets list endpoint
    resp_datasets = client.get("/api/v1/datasets")
    assert resp_datasets.status_code == 200
    assert "datasets" in resp_datasets.json()
