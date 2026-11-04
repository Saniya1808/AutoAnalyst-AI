import io
import json
from typing import Any, Dict, List, Optional, Tuple, Union
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.models.reports import (
    ExecutiveReportData,
    ReportSectionId,
)


# =============================================================================
# Color Palette & Styling Tokens (AutoAnalyst AI Theme)
# =============================================================================

COLOR_NAVY = "1E1B4B"        # Deep navy banner & primary headers (#1E1B4B)
COLOR_PURPLE = "7C3AED"      # Electric purple subtitle banner (#7C3AED)
COLOR_PURPLE_LIGHT = "EDE9FE"# Light purple accent fill (#EDE9FE)
COLOR_ZEBRA_ODD = "F8FAFC"   # Alternating row background (#F8FAFC)
COLOR_WHITE = "FFFFFF"       # White background
COLOR_BORDER = "CBD5E1"      # Slate 300 subtle cell borders (#CBD5E1)
COLOR_BORDER_DARK = "94A3B8" # Slate 400 section separator border (#94A3B8)
COLOR_TEXT_MAIN = "0F172A"   # Slate 900 main text
COLOR_TEXT_MUTED = "64748B"  # Slate 500 secondary text
COLOR_SUCCESS = "059669"     # Emerald 600
COLOR_WARNING = "D97706"     # Amber 600
COLOR_DANGER = "DC2626"      # Rose/Red 600

FONT_FAMILY = "Segoe UI"

HEADER_FILL_NAVY = PatternFill(fill_type="solid", start_color=COLOR_NAVY, end_color=COLOR_NAVY)
BANNER_FILL_PURPLE = PatternFill(fill_type="solid", start_color=COLOR_PURPLE, end_color=COLOR_PURPLE)
SECTION_FILL = PatternFill(fill_type="solid", start_color=COLOR_PURPLE_LIGHT, end_color=COLOR_PURPLE_LIGHT)
ZEBRA_FILL = PatternFill(fill_type="solid", start_color=COLOR_ZEBRA_ODD, end_color=COLOR_ZEBRA_ODD)
WHITE_FILL = PatternFill(fill_type="solid", start_color=COLOR_WHITE, end_color=COLOR_WHITE)

THIN_BORDER = Border(
    left=Side(style="thin", color=COLOR_BORDER),
    right=Side(style="thin", color=COLOR_BORDER),
    top=Side(style="thin", color=COLOR_BORDER),
    bottom=Side(style="thin", color=COLOR_BORDER),
)

SECTION_BORDER = Border(
    left=Side(style="thin", color=COLOR_BORDER_DARK),
    right=Side(style="thin", color=COLOR_BORDER_DARK),
    top=Side(style="medium", color=COLOR_NAVY),
    bottom=Side(style="medium", color=COLOR_NAVY),
)

FONT_TITLE = Font(name=FONT_FAMILY, size=13, bold=True, color=COLOR_WHITE)
FONT_SUBTITLE = Font(name=FONT_FAMILY, size=9.5, bold=True, color=COLOR_WHITE)
FONT_SECTION_HDR = Font(name=FONT_FAMILY, size=10, bold=True, color=COLOR_NAVY)
FONT_TABLE_HDR = Font(name=FONT_FAMILY, size=9.5, bold=True, color=COLOR_WHITE)
FONT_BODY = Font(name=FONT_FAMILY, size=9.5, color=COLOR_TEXT_MAIN)
FONT_BODY_BOLD = Font(name=FONT_FAMILY, size=9.5, bold=True, color=COLOR_TEXT_MAIN)
FONT_MUTED = Font(name=FONT_FAMILY, size=9, italic=True, color=COLOR_TEXT_MUTED)


def sanitize_cell_value(val: Any) -> Any:
    """
    Prevents Excel CSV/formula injection for user-controlled text strings starting
    with '=', '+', '-', or '@'.
    Guarantees numeric types (integers, floats, negative values) remain uncorrupted raw numbers.
    """
    if val is None:
        return ""
    # CRITICAL: Numbers (int, float) and bools must NEVER be escaped or turned into strings!
    if isinstance(val, (int, float, bool)):
        return val
    val_str = str(val)
    trimmed = val_str.strip()
    if trimmed and trimmed[0] in ("=", "+", "-", "@"):
        return "'" + val_str
    return val_str


class ExcelReportBuilder:
    """
    Constructs multi-sheet executive Excel workbooks from ExecutiveReportData
    using openpyxl with corporate branding, strict formula injection protection,
    and native Excel number formatting.
    """

    WORKSHEET_TITLES = [
        "Executive Summary",
        "KPIs",
        "Key Findings",
        "Category Benchmarks",
        "Trends & Seasonality",
        "Anomalies & Outliers",
        "Recommendations",
        "Data Quality",
    ]

    @classmethod
    def generate_excel_bytes(cls, report_data: ExecutiveReportData) -> io.BytesIO:
        """Generates an in-memory BytesIO buffer containing the styled Excel workbook."""
        wb = cls.build_workbook(report_data)
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @classmethod
    def build_workbook(cls, report_data: ExecutiveReportData) -> openpyxl.Workbook:
        """
        Builds and returns an openpyxl Workbook containing exactly 8 worksheets
        formatted according to the AutoAnalyst AI executive reporting standard.
        """
        wb = openpyxl.Workbook()

        # Sheet 1: Executive Summary (replaces default active sheet)
        ws_summary = wb.active
        ws_summary.title = cls.WORKSHEET_TITLES[0]
        cls._build_executive_summary_sheet(ws_summary, report_data)

        # Sheet 2: KPIs
        ws_kpis = wb.create_sheet(title=cls.WORKSHEET_TITLES[1])
        cls._build_kpis_sheet(ws_kpis, report_data)

        # Sheet 3: Key Findings
        ws_findings = wb.create_sheet(title=cls.WORKSHEET_TITLES[2])
        cls._build_key_findings_sheet(ws_findings, report_data)

        # Sheet 4: Category Benchmarks
        ws_benchmarks = wb.create_sheet(title=cls.WORKSHEET_TITLES[3])
        cls._build_category_benchmarks_sheet(ws_benchmarks, report_data)

        # Sheet 5: Trends & Seasonality
        ws_trends = wb.create_sheet(title=cls.WORKSHEET_TITLES[4])
        cls._build_trends_seasonality_sheet(ws_trends, report_data)

        # Sheet 6: Anomalies & Outliers
        ws_anomalies = wb.create_sheet(title=cls.WORKSHEET_TITLES[5])
        cls._build_anomalies_outliers_sheet(ws_anomalies, report_data)

        # Sheet 7: Recommendations
        ws_recommendations = wb.create_sheet(title=cls.WORKSHEET_TITLES[6])
        cls._build_recommendations_sheet(ws_recommendations, report_data)

        # Sheet 8: Data Quality
        ws_quality = wb.create_sheet(title=cls.WORKSHEET_TITLES[7])
        cls._build_data_quality_sheet(ws_quality, report_data)

        return wb

    # =========================================================================
    # Shared Layout & Rendering Helpers
    # =========================================================================

    @staticmethod
    def _render_sheet_banner(ws, sheet_name: str, subtitle: str, max_col: int = 8) -> None:
        """Renders standard branded header banners at rows 1 and 2."""
        ws.views.sheetView[0].showGridLines = True
        ws.row_dimensions[1].height = 28
        ws.row_dimensions[2].height = 20
        ws.row_dimensions[3].height = 10  # blank spacer

        col_letter = get_column_letter(max(max_col, 6))
        ws.merge_cells(f"A1:{col_letter}1")
        ws.merge_cells(f"A2:{col_letter}2")

        c1 = ws["A1"]
        c1.value = "AutoAnalyst AI — Powered by Saniya"
        c1.font = FONT_TITLE
        c1.fill = HEADER_FILL_NAVY
        c1.alignment = Alignment(horizontal="left", vertical="center", indent=1)

        c2 = ws["A2"]
        c2.value = f"{sheet_name} | {subtitle}"
        c2.font = FONT_SUBTITLE
        c2.fill = BANNER_FILL_PURPLE
        c2.alignment = Alignment(horizontal="left", vertical="center", indent=1)

    @staticmethod
    def _render_section_header(ws, row_idx: int, title: str, max_col: int = 8) -> int:
        """Renders a prominent section divider header."""
        ws.row_dimensions[row_idx].height = 22
        col_letter = get_column_letter(max(max_col, 6))
        ws.merge_cells(f"A{row_idx}:{col_letter}{row_idx}")

        cell = ws[f"A{row_idx}"]
        cell.value = f"  {title.upper()}"
        cell.font = FONT_SECTION_HDR
        cell.fill = SECTION_FILL
        cell.border = SECTION_BORDER
        cell.alignment = Alignment(horizontal="left", vertical="center")
        return row_idx + 1

    @staticmethod
    def _render_info_box(ws, start_row: int, message: str, max_col: int = 8) -> int:
        """Renders an informational notice when a section is excluded or has no data."""
        ws.row_dimensions[start_row].height = 24
        col_letter = get_column_letter(max(max_col, 6))
        ws.merge_cells(f"A{start_row}:{col_letter}{start_row}")

        cell = ws[f"A{start_row}"]
        cell.value = f"Notice: {message}"
        cell.font = FONT_MUTED
        cell.fill = ZEBRA_FILL
        cell.border = THIN_BORDER
        cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        return start_row + 2

    @staticmethod
    def _render_table(
        ws,
        start_row: int,
        headers: List[str],
        rows: List[List[Any]],
        number_formats: Optional[List[Optional[str]]] = None,
        alignments: Optional[List[Optional[str]]] = None,
    ) -> int:
        """
        Renders a styled data table with navy headers, zebra rows, borders,
        and native number formatting.
        """
        num_cols = len(headers)
        ws.row_dimensions[start_row].height = 26

        # Write table headers
        for c_idx, h in enumerate(headers):
            cell = ws.cell(row=start_row, column=c_idx + 1, value=h)
            cell.fill = HEADER_FILL_NAVY
            cell.font = FONT_TABLE_HDR
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = THIN_BORDER

        # Write data rows
        curr_row = start_row + 1
        for r_idx, row_data in enumerate(rows):
            ws.row_dimensions[curr_row].height = 20
            row_fill = WHITE_FILL if r_idx % 2 == 0 else ZEBRA_FILL

            for c_idx in range(num_cols):
                raw_val = row_data[c_idx] if c_idx < len(row_data) else None
                clean_val = sanitize_cell_value(raw_val)

                cell = ws.cell(row=curr_row, column=c_idx + 1, value=clean_val)
                cell.fill = row_fill
                cell.font = FONT_BODY
                cell.border = THIN_BORDER

                # Apply number formatting if specified
                if number_formats and c_idx < len(number_formats) and number_formats[c_idx]:
                    if isinstance(clean_val, (int, float)):
                        cell.number_format = number_formats[c_idx]

                # Apply alignment
                if alignments and c_idx < len(alignments) and alignments[c_idx]:
                    cell.alignment = Alignment(horizontal=alignments[c_idx], vertical="center")
                elif isinstance(clean_val, (int, float)):
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

            curr_row += 1

        return curr_row

    @staticmethod
    def _auto_fit_columns(ws, min_width: int = 12, max_width: int = 55) -> None:
        """Auto-adjusts column widths between min_width and max_width, ignoring banner rows."""
        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)
            max_len = 0
            for cell in col:
                # Skip merged banner and section header rows
                if cell.row in (1, 2):
                    continue
                if cell.value is not None:
                    s_val = str(cell.value)
                    lines = s_val.split("\n")
                    line_len = max(len(l) for l in lines) if lines else 0
                    if line_len > max_len:
                        max_len = line_len
            calculated_width = max(min_width, min(max_len + 3, max_width))
            ws.column_dimensions[col_letter].width = calculated_width

    # =========================================================================
    # Sheet 1: Executive Summary
    # =========================================================================

    @classmethod
    def _build_executive_summary_sheet(cls, ws, report_data: ExecutiveReportData) -> None:
        cls._render_sheet_banner(
            ws,
            sheet_name="Executive Summary",
            subtitle="Strategic Intelligence Briefing & Verified Fact Evidence",
            max_col=6,
        )

        curr_row = 4
        curr_row = cls._render_section_header(ws, curr_row, "Report & Dataset Snapshot Metadata", max_col=6)

        metadata_rows = [
            ["Report Title", sanitize_cell_value(report_data.config.title)],
            ["Subtitle", sanitize_cell_value(report_data.config.subtitle or "N/A")],
            ["Dataset Name", sanitize_cell_value(report_data.dataset_name)],
            ["Dataset ID", sanitize_cell_value(report_data.dataset_id)],
            ["Active Snapshot ID", sanitize_cell_value(report_data.active_dataset_id)],
            [
                "Snapshot Type",
                f"Cleaned Snapshot (v{report_data.cleaning_version})"
                if report_data.is_cleaned
                else "Original Dataset Snapshot",
            ],
            ["SHA-256 Snapshot Hash", sanitize_cell_value(report_data.snapshot_hash)],
            ["Generation Timestamp", sanitize_cell_value(report_data.generated_at)],
            ["Dataset Health Score", report_data.health_score],
            [
                "Confidentiality Notice",
                sanitize_cell_value(report_data.confidentiality_notice or "CONFIDENTIAL"),
            ],
        ]

        for r_idx, (lbl, val) in enumerate(metadata_rows):
            ws.row_dimensions[curr_row].height = 20
            fill = WHITE_FILL if r_idx % 2 == 0 else ZEBRA_FILL

            c_lbl = ws.cell(row=curr_row, column=1, value=lbl)
            c_lbl.font = FONT_BODY_BOLD
            c_lbl.fill = fill
            c_lbl.border = THIN_BORDER
            c_lbl.alignment = Alignment(horizontal="left", vertical="center")

            ws.merge_cells(f"B{curr_row}:F{curr_row}")
            c_val = ws.cell(row=curr_row, column=2, value=val)
            c_val.font = FONT_BODY
            c_val.fill = fill
            c_val.border = THIN_BORDER
            c_val.alignment = Alignment(horizontal="left", vertical="center")
            if lbl == "Dataset Health Score":
                c_val.number_format = '0.0" / 100"'

            curr_row += 1

        curr_row += 1  # spacer

        # Strategic Briefing Section
        curr_row = cls._render_section_header(ws, curr_row, "Executive Strategic Briefing", max_col=6)
        if report_data.executive_summary:
            es = report_data.executive_summary
            mode_desc = "AI Generated Narrative (Gemini)" if es.mode == "ai_generated" else "Deterministic Heuristic Synthesis"
            provider_desc = f"{es.provider or 'offline'} / {es.model or 'heuristic'}"

            ws.row_dimensions[curr_row].height = 19
            ws.cell(row=curr_row, column=1, value="Synthesis Mode").font = FONT_BODY_BOLD
            ws.cell(row=curr_row, column=2, value=mode_desc).font = FONT_BODY
            ws.cell(row=curr_row, column=1).border = THIN_BORDER
            ws.cell(row=curr_row, column=2).border = THIN_BORDER
            curr_row += 1

            ws.row_dimensions[curr_row].height = 19
            ws.cell(row=curr_row, column=1, value="Engine / Provider").font = FONT_BODY_BOLD
            ws.cell(row=curr_row, column=2, value=provider_desc).font = FONT_BODY
            ws.cell(row=curr_row, column=1).border = THIN_BORDER
            ws.cell(row=curr_row, column=2).border = THIN_BORDER
            curr_row += 1

            # Narrative Text
            curr_row += 1
            ws.merge_cells(f"A{curr_row}:F{curr_row + 2}")
            c_narrative = ws.cell(row=curr_row, column=1, value=sanitize_cell_value(es.narrative))
            c_narrative.font = FONT_BODY
            c_narrative.fill = WHITE_FILL
            c_narrative.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            for r in range(curr_row, curr_row + 3):
                ws.row_dimensions[r].height = 20
                for c in range(1, 7):
                    ws.cell(row=r, column=c).border = THIN_BORDER
            curr_row += 4

            # Key Takeaways
            if es.key_takeaways:
                ws.cell(row=curr_row, column=1, value="Key Strategic Takeaways:").font = FONT_BODY_BOLD
                curr_row += 1
                for idx, t in enumerate(es.key_takeaways, 1):
                    ws.row_dimensions[curr_row].height = 19
                    ws.merge_cells(f"A{curr_row}:F{curr_row}")
                    c_tk = ws.cell(row=curr_row, column=1, value=f"•  {sanitize_cell_value(t)}")
                    c_tk.font = FONT_BODY
                    c_tk.alignment = Alignment(horizontal="left", vertical="center")
                    curr_row += 1
        else:
            curr_row = cls._render_info_box(ws, curr_row, "This section was excluded from the report configuration.", max_col=6)

        curr_row += 1  # spacer

        # Top Grounded Facts Registry
        curr_row = cls._render_section_header(ws, curr_row, "Verified Empirical Facts Registry", max_col=6)
        if report_data.grounded_facts:
            fact_headers = ["Fact ID", "Category", "Column", "Metric", "Value", "Verified Empirical Statement"]
            fact_rows = []
            for f in report_data.grounded_facts[:15]:
                fact_rows.append([
                    f.fact_id,
                    f.category.title(),
                    f.column_name or "Dataset Level",
                    f.metric_name,
                    f.value,
                    f.formatted_statement,
                ])
            curr_row = cls._render_table(
                ws,
                curr_row,
                fact_headers,
                fact_rows,
                alignments=["center", "center", "left", "left", "right", "left"],
            )
        else:
            curr_row = cls._render_info_box(ws, curr_row, "No grounded empirical facts registered.", max_col=6)

        curr_row += 1  # spacer

        # Disclaimers & Limitations
        curr_row = cls._render_section_header(ws, curr_row, "Analytical Disclaimers & Reporting Scope", max_col=6)
        disclaimers = list(report_data.date_scoping_limitations) + list(report_data.limitations)
        if disclaimers:
            for d in disclaimers:
                ws.row_dimensions[curr_row].height = 20
                ws.merge_cells(f"A{curr_row}:F{curr_row}")
                c_disc = ws.cell(row=curr_row, column=1, value=f"Notice: {sanitize_cell_value(d)}")
                c_disc.font = FONT_MUTED
                c_disc.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                curr_row += 1
        else:
            curr_row = cls._render_info_box(ws, curr_row, "No analytical limitations or date-scoping constraints reported.", max_col=6)

        cls._auto_fit_columns(ws, min_width=12, max_width=55)

    # =========================================================================
    # Sheet 2: KPIs
    # =========================================================================

    @classmethod
    def _build_kpis_sheet(cls, ws, report_data: ExecutiveReportData) -> None:
        cls._render_sheet_banner(
            ws,
            sheet_name="KPIs",
            subtitle="Executive Metrics, Dataset Volume & Schema Profile",
            max_col=8,
        )

        curr_row = 4
        if report_data.key_kpis:
            k = report_data.key_kpis.kpis
            curr_row = cls._render_section_header(ws, curr_row, "Core Dataset Health & Volume KPIs", max_col=8)

            kpi_headers = ["Metric Dimension", "Value", "Format / Type", "Status & Interpretation"]
            kpi_rows = [
                ["Total Rows", k.total_rows, "Integer Count", "Total records evaluated in verified snapshot"],
                ["Total Columns", k.total_columns, "Integer Count", "Analytical attributes across dataset"],
                ["Total Data Cells", k.total_cells, "Integer Count", "Total matrix volume (rows × columns)"],
                ["Data Completeness", k.data_completeness, "Percentage (%)", "Non-null populated cells ratio"],
                ["Total Missing Cells", k.missing_cells, "Integer Count", "Empty or unpopulated cells"],
                ["Missing Percentage", k.missing_percentage, "Percentage (%)", "Proportion of null data points"],
                ["Duplicate Rows", k.duplicate_rows, "Integer Count", "Identical redundant observations"],
                ["Duplicate Percentage", k.duplicate_percentage, "Percentage (%)", "Proportion of duplicate records"],
                ["Dataset Health Score", report_data.key_kpis.health_score, "Score (0-100)", "Overall hygiene and completeness grade"],
            ]

            num_formats = [None, "#,##0", None, None]
            curr_row = cls._render_table(
                ws,
                curr_row,
                kpi_headers,
                kpi_rows,
                number_formats=num_formats,
                alignments=["left", "right", "center", "left"],
            )

            # Format percentages specifically
            # Completeness is at row 8, missing % at row 10, duplicate % at row 12, health at 13
            # We can set number format on individual cells safely
            ws.cell(row=8, column=2).number_format = '0.0"%"'
            ws.cell(row=10, column=2).number_format = '0.0"%"'
            ws.cell(row=12, column=2).number_format = '0.0"%"'
            ws.cell(row=13, column=2).number_format = '0.0" / 100"'

            curr_row += 1  # spacer

            # Focus column statistics if available
            if k.selected_column_stats:
                st = k.selected_column_stats
                curr_row = cls._render_section_header(ws, curr_row, f"Selected Focus Metric Statistics ({k.selected_column})", max_col=8)
                stat_headers = ["Metric Property", "Numeric Value", "Description"]
                stat_rows = [
                    ["Target Column", sanitize_cell_value(st.get("column", "")), "Selected numerical measure"],
                    ["Record Count", st.get("count", 0), "Non-null numerical observations"],
                    ["Sum Total", st.get("sum", 0.0), "Aggregated sum across records"],
                    ["Mean Average", st.get("average", 0.0), "Arithmetic mean"],
                    ["Minimum Value", st.get("minimum", 0.0), "Lowest observed value"],
                    ["Maximum Value", st.get("maximum", 0.0), "Peak observed value"],
                    ["Standard Deviation", st.get("std", 0.0), "Statistical dispersion"],
                    ["Zero Values Count", st.get("zeros_count", 0), "Records with value == 0"],
                ]
                curr_row = cls._render_table(
                    ws,
                    curr_row,
                    stat_headers,
                    stat_rows,
                    number_formats=[None, "#,##0.00", None],
                    alignments=["left", "right", "left"],
                )
                curr_row += 1  # spacer

            # Column Schema Overview
            if report_data.columns:
                curr_row = cls._render_section_header(ws, curr_row, "Column Schema & Type Profiling", max_col=8)
                col_headers = ["Column Name", "Position", "Data Type", "Raw Dtype", "Non-Null", "Nulls", "Null %", "Unique Count", "Is Unique"]
                col_rows = []
                for c in report_data.columns:
                    col_rows.append([
                        c.name,
                        c.position,
                        c.data_type,
                        c.raw_dtype,
                        c.non_null_count,
                        c.null_count,
                        c.null_percentage,
                        c.unique_count,
                        "Yes" if c.is_unique else "No",
                    ])
                curr_row = cls._render_table(
                    ws,
                    curr_row,
                    col_headers,
                    col_rows,
                    number_formats=[None, "#,##0", None, None, "#,##0", "#,##0", '0.0"%"', "#,##0", None],
                    alignments=["left", "center", "center", "center", "right", "right", "right", "right", "center"],
                )
        else:
            curr_row = cls._render_info_box(ws, curr_row, "This section was excluded from the report configuration.", max_col=8)

        cls._auto_fit_columns(ws, min_width=12, max_width=50)

    # =========================================================================
    # Sheet 3: Key Findings
    # =========================================================================

    @classmethod
    def _build_key_findings_sheet(ws_cls, ws, report_data: ExecutiveReportData) -> None:
        ws_cls._render_sheet_banner(
            ws,
            sheet_name="Key Findings",
            subtitle="Automated Insights Ranked by Analytical Significance",
            max_col=8,
        )

        curr_row = 4
        if report_data.key_findings and report_data.key_findings.findings:
            curr_row = ws_cls._render_section_header(
                ws,
                curr_row,
                f"Significant Analytical Discoveries ({report_data.key_findings.total_count} Findings, {report_data.key_findings.high_importance_count} High Importance)",
                max_col=8,
            )

            headers = [
                "Finding ID",
                "Importance",
                "Category",
                "Significance Score",
                "Title",
                "Description",
                "Columns Involved",
                "Referenced Fact IDs",
            ]
            rows = []
            for f in report_data.key_findings.findings:
                rows.append([
                    f.finding_id,
                    f.importance.upper(),
                    f.category.title(),
                    f.significance_score,
                    f.title,
                    f.description,
                    ", ".join(f.columns_involved),
                    ", ".join(f.referenced_fact_ids),
                ])

            ws.freeze_panes = "A6"
            curr_row = ws_cls._render_table(
                ws,
                curr_row,
                headers,
                rows,
                number_formats=[None, None, None, '0.0"%"', None, None, None, None],
                alignments=["center", "center", "center", "right", "left", "left", "left", "left"],
            )
            # Add auto-filter
            ws.auto_filter.ref = f"A5:H{curr_row - 1}"
        elif report_data.key_findings:
            curr_row = ws_cls._render_info_box(ws, curr_row, "No automated findings met the significance threshold for this dataset.", max_col=8)
        else:
            curr_row = ws_cls._render_info_box(ws, curr_row, "This section was excluded from the report configuration.", max_col=8)

        ws_cls._auto_fit_columns(ws, min_width=12, max_width=55)

    # =========================================================================
    # Sheet 4: Category Benchmarks
    # =========================================================================

    @classmethod
    def _build_category_benchmarks_sheet(cls, ws, report_data: ExecutiveReportData) -> None:
        cls._render_sheet_banner(
            ws,
            sheet_name="Category Benchmarks",
            subtitle="Best and Worst Performer Benchmarks & Performance Disparities",
            max_col=10,
        )

        curr_row = 4
        if report_data.category_benchmarks and report_data.category_benchmarks.benchmarks:
            curr_row = cls._render_section_header(ws, curr_row, "Categorical Benchmark Overview", max_col=10)

            overview_headers = [
                "Dimension",
                "Metric",
                "Aggregation",
                "Dataset Average",
                "Best Performer",
                "Best Delta vs Avg (%)",
                "Worst Performer",
                "Worst Delta vs Avg (%)",
                "Strategic Explanation",
                "Referenced Fact IDs",
            ]
            overview_rows = []
            for b in report_data.category_benchmarks.benchmarks:
                overview_rows.append([
                    b.dimension_column,
                    b.metric_column or "Record Count",
                    b.aggregation.upper(),
                    b.dataset_average,
                    f"{b.best_performer.category_name} ({b.best_performer.formatted_value})",
                    b.best_performer.delta_vs_average_pct,
                    f"{b.worst_performer.category_name} ({b.worst_performer.formatted_value})",
                    b.worst_performer.delta_vs_average_pct,
                    b.explanation,
                    ", ".join(b.referenced_fact_ids),
                ])

            curr_row = cls._render_table(
                ws,
                curr_row,
                overview_headers,
                overview_rows,
                number_formats=[None, None, None, "#,##0.00", None, '0.0"%"', None, '0.0"%"', None, None],
                alignments=["left", "left", "center", "right", "left", "right", "left", "right", "left", "left"],
            )

            curr_row += 1  # spacer

            # Detailed Ranked Performers Breakdown
            curr_row = cls._render_section_header(ws, curr_row, "Detailed Ranked Category Performers Breakdown", max_col=10)
            ranked_headers = [
                "Dimension",
                "Category Name",
                "Metric Value",
                "Delta vs Average (%)",
                "Sample Size",
                "Statistical Reliability",
            ]
            ranked_rows = []
            for b in report_data.category_benchmarks.benchmarks:
                for p in b.ranked_performers:
                    ranked_rows.append([
                        b.dimension_column,
                        p.category_name,
                        p.metric_value,
                        p.delta_vs_average_pct,
                        p.sample_size,
                        "Statistically Reliable (n>=5)" if p.is_statistically_reliable else "Small Sample (n<5)",
                    ])

            curr_row = cls._render_table(
                ws,
                curr_row,
                ranked_headers,
                ranked_rows,
                number_formats=[None, None, "#,##0.00", '0.0"%"', "#,##0", None],
                alignments=["left", "left", "right", "right", "right", "center"],
            )
        elif report_data.category_benchmarks:
            curr_row = cls._render_info_box(ws, curr_row, "No categorical dimensions with sufficient grouping depth were identified for benchmarking.", max_col=10)
        else:
            curr_row = cls._render_info_box(ws, curr_row, "This section was excluded from the report configuration.", max_col=10)

        cls._auto_fit_columns(ws, min_width=12, max_width=55)

    # =========================================================================
    # Sheet 5: Trends & Seasonality
    # =========================================================================

    @classmethod
    def _build_trends_seasonality_sheet(cls, ws, report_data: ExecutiveReportData) -> None:
        cls._render_sheet_banner(
            ws,
            sheet_name="Trends & Seasonality",
            subtitle="Chronological Trajectories, Statistical Evidence & Cyclical Patterns",
            max_col=10,
        )

        curr_row = 4
        if report_data.trends_and_seasonality:
            ts = report_data.trends_and_seasonality
            if ts.has_temporal_data:
                # 1. Trends Summary Table
                if ts.trends:
                    curr_row = cls._render_section_header(ws, curr_row, "Temporal Trend Trajectories & Statistical Significance", max_col=10)
                    trend_headers = [
                        "Trend ID",
                        "Date Column",
                        "Metric Column",
                        "Granularity",
                        "Direction",
                        "Statistical Evidence",
                        "Business Magnitude",
                        "R² Strength",
                        "Absolute Net Change",
                        "Growth (%)",
                        "Peak Period (Value)",
                        "Trough Period (Value)",
                        "Referenced Fact IDs",
                    ]
                    trend_rows = []
                    for t in ts.trends:
                        growth_val = t.conventional_growth_pct if t.conventional_growth_pct is not None else t.range_normalized_shift_pct
                        trend_rows.append([
                            t.trend_id,
                            t.date_column,
                            t.metric_column,
                            t.granularity.title(),
                            t.direction.upper(),
                            t.statistical_evidence.replace("_", " ").title(),
                            t.business_magnitude.title(),
                            t.trend_strength_r2,
                            t.absolute_change,
                            growth_val,
                            f"{t.peak_period} ({t.peak_value:,.2f})",
                            f"{t.trough_period} ({t.trough_value:,.2f})",
                            ", ".join(t.referenced_fact_ids),
                        ])

                    curr_row = cls._render_table(
                        ws,
                        curr_row,
                        trend_headers,
                        trend_rows,
                        number_formats=[None, None, None, None, None, None, None, "0.000", "#,##0.00", '0.0"%"', None, None, None],
                        alignments=["center", "left", "left", "center", "center", "center", "center", "right", "right", "right", "left", "left", "left"],
                    )
                    curr_row += 1  # spacer

                # 2. Seasonality Section
                if ts.seasonality:
                    seas = ts.seasonality
                    curr_row = cls._render_section_header(ws, curr_row, "Seasonality & Recurring Periodic Patterns", max_col=10)
                    seas_headers = ["Audit Dimension", "Finding / Metric", "Interpretation"]
                    seas_rows = [
                        ["Seasonality Status", seas.status.replace("_", " ").title(), "Statistical test classification"],
                        ["Cycle Type", seas.cycle_type or "None Detected", "Evaluated periodic periodicity"],
                        ["Peak Season", seas.peak_season or "N/A", "Calendar period of maximum volume"],
                        ["Trough Season", seas.trough_season or "N/A", "Calendar period of lowest volume"],
                        ["ANOVA F-Statistic", seas.anova_f_stat if seas.anova_f_stat is not None else "N/A", "Between-period variance ratio"],
                        ["ANOVA p-value", seas.anova_p_value if seas.anova_p_value is not None else "N/A", "Significance test (p <= 0.05)"],
                        ["Kruskal p-value", seas.kruskal_p_value if seas.kruskal_p_value is not None else "N/A", "Non-parametric confirmation"],
                        ["Analytical Explanation", seas.explanation, "Business intelligence interpretation"],
                    ]
                    curr_row = cls._render_table(
                        ws,
                        curr_row,
                        seas_headers,
                        seas_rows,
                        number_formats=[None, None, None],
                        alignments=["left", "left", "left"],
                    )
                    curr_row += 1  # spacer

                    if seas.patterns:
                        curr_row = cls._render_section_header(ws, curr_row, "Detected Seasonal Cycle Residuals", max_col=10)
                        pat_headers = ["Cycle Type", "Period Name", "Average Residual", "Delta vs Overall Avg (%)", "Sample Occurrences"]
                        pat_rows = []
                        for p in seas.patterns:
                            pat_rows.append([
                                p.cycle_type,
                                p.period_name,
                                p.average_residual,
                                p.delta_vs_overall_avg_pct,
                                p.sample_occurrences,
                            ])
                        curr_row = cls._render_table(
                            ws,
                            curr_row,
                            pat_headers,
                            pat_rows,
                            number_formats=[None, None, "#,##0.00", '0.0"%"', "#,##0"],
                            alignments=["center", "left", "right", "right", "right"],
                        )
                        curr_row += 1  # spacer

                # 3. Time Series Data Points Table
                if ts.trends and ts.trends[0].data_points:
                    curr_row = cls._render_section_header(ws, curr_row, "Chronological Period Observations", max_col=10)
                    dp_headers = ["Period Label", "Timestamp", "Metric Value", "Period-over-Period (%)", "Completeness (%)", "Is Anomaly", "Severity"]
                    dp_rows = []
                    for pt in ts.trends[0].data_points:
                        dp_rows.append([
                            pt.period_label,
                            pt.timestamp or "N/A",
                            pt.value,
                            pt.period_over_period_pct,
                            pt.temporal_completeness_pct,
                            "Yes" if pt.is_anomaly else "No",
                            (pt.anomaly_severity or "normal").upper(),
                        ])
                    curr_row = cls._render_table(
                        ws,
                        curr_row,
                        dp_headers,
                        dp_rows,
                        number_formats=[None, None, "#,##0.00", '0.0"%"', '0.0"%"', None, None],
                        alignments=["center", "center", "right", "right", "right", "center", "center"],
                    )
            else:
                curr_row = cls._render_info_box(ws, curr_row, "Dataset contains no valid datetime columns for chronological trend or seasonality analysis.", max_col=10)
        else:
            curr_row = cls._render_info_box(ws, curr_row, "This section was excluded from the report configuration.", max_col=10)

        cls._auto_fit_columns(ws, min_width=12, max_width=55)

    # =========================================================================
    # Sheet 6: Anomalies & Outliers
    # =========================================================================

    @classmethod
    def _build_anomalies_outliers_sheet(cls, ws, report_data: ExecutiveReportData) -> None:
        cls._render_sheet_banner(
            ws,
            sheet_name="Anomalies & Outliers",
            subtitle="Statistical Outliers, Skewness & Temporal Shifts",
            max_col=8,
        )

        curr_row = 4
        if report_data.anomalies_and_risks:
            ar = report_data.anomalies_and_risks
            has_cross = bool(ar.anomalies)
            has_temp = bool(ar.temporal_anomalies)

            if has_cross:
                curr_row = cls._render_section_header(ws, curr_row, f"Distributional & Categorical Anomalies ({len(ar.anomalies)} Detected)", max_col=8)
                anom_headers = ["Anomaly ID", "Severity", "Anomaly Type", "Target Column", "Description", "Evidence Details", "Referenced Fact IDs"]
                anom_rows = []
                for a in ar.anomalies:
                    anom_rows.append([
                        a.anomaly_id,
                        a.severity.upper(),
                        a.anomaly_type.replace("_", " ").title(),
                        a.column_name,
                        a.description,
                        json.dumps(a.metric_evidence) if a.metric_evidence else "N/A",
                        ", ".join(a.referenced_fact_ids),
                    ])
                curr_row = cls._render_table(
                    ws,
                    curr_row,
                    anom_headers,
                    anom_rows,
                    alignments=["center", "center", "center", "left", "left", "left", "left"],
                )
                curr_row += 1  # spacer

            if has_temp:
                curr_row = cls._render_section_header(ws, curr_row, f"Temporal Anomalies & Sudden Fluctuations ({len(ar.temporal_anomalies)} Detected)", max_col=8)
                temp_headers = [
                    "Anomaly ID",
                    "Severity",
                    "Anomaly Type",
                    "Date Column",
                    "Metric Column",
                    "Period",
                    "Previous Value",
                    "Current Value",
                    "Absolute Delta",
                    "Delta (%)",
                    "Detection Reason",
                    "Referenced Fact IDs",
                ]
                temp_rows = []
                for ta in ar.temporal_anomalies:
                    temp_rows.append([
                        ta.anomaly_id,
                        ta.severity.upper(),
                        ta.anomaly_type.replace("_", " ").title(),
                        ta.date_column,
                        ta.metric_column,
                        ta.period_label,
                        ta.previous_value,
                        ta.current_value,
                        ta.delta_abs,
                        ta.delta_pct,
                        ta.detection_reason,
                        ", ".join(ta.referenced_fact_ids),
                    ])
                curr_row = cls._render_table(
                    ws,
                    curr_row,
                    temp_headers,
                    temp_rows,
                    number_formats=[None, None, None, None, None, None, "#,##0.00", "#,##0.00", "#,##0.00", '0.0"%"', None, None],
                    alignments=["center", "center", "center", "left", "left", "center", "right", "right", "right", "right", "left", "left"],
                )

            if not has_cross and not has_temp:
                curr_row = cls._render_info_box(ws, curr_row, "No statistical anomalies or unusual outliers detected across the dataset.", max_col=8)
        else:
            curr_row = cls._render_info_box(ws, curr_row, "This section was excluded from the report configuration.", max_col=8)

        cls._auto_fit_columns(ws, min_width=12, max_width=55)

    # =========================================================================
    # Sheet 7: Recommendations
    # =========================================================================

    @classmethod
    def _build_recommendations_sheet(cls, ws, report_data: ExecutiveReportData) -> None:
        cls._render_sheet_banner(
            ws,
            sheet_name="Recommendations",
            subtitle="Actionable Strategic Recommendations & Hypothesis Segregation",
            max_col=8,
        )

        curr_row = 4
        if report_data.recommendations and report_data.recommendations.recommendations:
            r_sec = report_data.recommendations
            curr_row = cls._render_section_header(
                ws,
                curr_row,
                f"Strategic Recommendations ({r_sec.total_count} Actions: {r_sec.empirical_facts_count} Verified Empirical, {r_sec.analytical_hypotheses_count} Analytical Hypotheses)",
                max_col=8,
            )

            rec_headers = [
                "Rec ID",
                "Priority",
                "Category",
                "Evidence Provenance",
                "Recommendation Title",
                "Action Statement",
                "Expected Business Impact",
                "Referenced Fact IDs",
            ]
            rec_rows = []
            for r in r_sec.recommendations:
                provenance_label = "Analytical Hypothesis (Requires Validation)" if r.is_hypothesis else "Verified Empirical Fact"
                rec_rows.append([
                    r.recommendation_id,
                    r.priority.upper(),
                    r.category.title(),
                    provenance_label,
                    r.title,
                    r.action_statement,
                    r.expected_impact,
                    ", ".join(r.referenced_fact_ids),
                ])

            ws.freeze_panes = "A6"
            curr_row = cls._render_table(
                ws,
                curr_row,
                rec_headers,
                rec_rows,
                alignments=["center", "center", "center", "center", "left", "left", "left", "left"],
            )
            ws.auto_filter.ref = f"A5:H{curr_row - 1}"
        elif report_data.recommendations:
            curr_row = cls._render_info_box(ws, curr_row, "No specific business recommendations generated for this snapshot.", max_col=8)
        else:
            curr_row = cls._render_info_box(ws, curr_row, "This section was excluded from the report configuration.", max_col=8)

        cls._auto_fit_columns(ws, min_width=12, max_width=55)

    # =========================================================================
    # Sheet 8: Data Quality
    # =========================================================================

    @classmethod
    def _build_data_quality_sheet(cls, ws, report_data: ExecutiveReportData) -> None:
        cls._render_sheet_banner(
            ws,
            sheet_name="Data Quality",
            subtitle="Dataset Health Audit, Integrity Metrics & Outlier Boundaries",
            max_col=8,
        )

        curr_row = 4
        if report_data.data_quality_audit:
            qa = report_data.data_quality_audit
            curr_row = cls._render_section_header(ws, curr_row, "Data Quality Scorecard & Overall Rating", max_col=8)

            scorecard_headers = ["Quality Dimension", "Score / Value", "Rating / Unit", "Analytical Interpretation"]
            scorecard_rows = [
                ["Overall Quality Score", qa.overall_quality_score, "Score (0-100)", f"Grade: {qa.quality_grade}"],
                ["Completeness Score", qa.completeness_score, "Percentage (%)", "Proportion of non-null populated data cells"],
                ["Uniqueness Score", qa.uniqueness_score, "Percentage (%)", "Proportion of non-duplicate record observations"],
                ["Validity Score", qa.validity_score, "Percentage (%)", "Adherence to expected semantic data formats"],
                ["Total Columns", qa.column_count, "Attribute Count", "Total attributes profiled across dataset"],
                ["Total Missing Cells", qa.missing_cells, "Cell Count", "Unpopulated or null values"],
                ["Duplicate Rows", qa.duplicate_rows, "Record Count", "Completely duplicate row entries"],
            ]
            curr_row = cls._render_table(
                ws,
                curr_row,
                scorecard_headers,
                scorecard_rows,
                number_formats=[None, "#,##0.00", None, None],
                alignments=["left", "right", "center", "left"],
            )
            # Format percentage cells specifically
            ws.cell(row=5, column=2).number_format = '0.0" / 100"'
            ws.cell(row=6, column=2).number_format = '0.0"%"'
            ws.cell(row=7, column=2).number_format = '0.0"%"'
            ws.cell(row=8, column=2).number_format = '0.0"%"'
            ws.cell(row=9, column=2).number_format = '#,##0'
            ws.cell(row=10, column=2).number_format = '#,##0'
            ws.cell(row=11, column=2).number_format = '#,##0'

            curr_row += 1  # spacer

            # Column Hygiene Details
            if qa.quality_profile and qa.quality_profile.columns:
                curr_row = cls._render_section_header(ws, curr_row, "Column-Level Hygiene & Outlier Breakdown", max_col=8)
                col_headers = [
                    "Column Name",
                    "Position",
                    "Data Type",
                    "Total Count",
                    "Missing Count",
                    "Missing %",
                    "Unique Count",
                    "IQR Outliers",
                    "Z-Score Outliers",
                ]
                col_rows = []
                for c in qa.quality_profile.columns:
                    col_rows.append([
                        c.column_name,
                        c.position,
                        c.data_type,
                        c.total_count,
                        c.missing_count,
                        c.missing_percentage,
                        c.unique_count,
                        c.outliers_iqr_count if c.outliers_iqr_count is not None else "N/A",
                        c.outliers_zscore_count if c.outliers_zscore_count is not None else "N/A",
                    ])
                curr_row = cls._render_table(
                    ws,
                    curr_row,
                    col_headers,
                    col_rows,
                    number_formats=[None, "#,##0", None, "#,##0", "#,##0", '0.0"%"', "#,##0", None, None],
                    alignments=["left", "center", "center", "right", "right", "right", "right", "center", "center"],
                )
        else:
            curr_row = cls._render_info_box(ws, curr_row, "This section was excluded from the report configuration.", max_col=8)

        cls._auto_fit_columns(ws, min_width=12, max_width=50)
