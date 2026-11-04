import asyncio
import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from playwright.async_api import async_playwright

from app.models.dashboard import ChartConfig
from app.models.reports import (
    ExecutiveReportData,
    ReportSectionId,
)


# =============================================================================
# Standalone SVG Chart Generator (Self-Contained Vector Graphics)
# =============================================================================

class SvgChartRenderer:
    """
    Renders standalone vector SVG charts directly from Plotly ChartConfig structures.
    Does not require external JS bundles, CDN access, or headless canvas rendering.
    Provides graceful tabular fallback if data points cannot be plotted.
    """

    @classmethod
    def render_chart(cls, chart: ChartConfig, max_width: int = 680, height: int = 260) -> str:
        """Renders ChartConfig as an embedded SVG string or fallback tabular HTML."""
        try:
            if not chart.plotly_data:
                return cls._render_fallback_table(chart)

            trace = chart.plotly_data[0]
            chart_type = chart.chart_type.lower()

            if chart_type in ("bar", "column"):
                x_vals = trace.get("x") or []
                y_vals = trace.get("y") or []
                if x_vals and y_vals:
                    return cls._render_bar_svg(chart.title, x_vals, y_vals, max_width, height)

            elif chart_type in ("line", "scatter"):
                x_vals = trace.get("x") or []
                y_vals = trace.get("y") or []
                if x_vals and y_vals:
                    return cls._render_line_svg(chart.title, x_vals, y_vals, max_width, height)

            elif chart_type == "pie":
                labels = trace.get("labels") or []
                values = trace.get("values") or []
                if labels and values:
                    return cls._render_pie_svg(chart.title, labels, values, max_width, height)

            return cls._render_fallback_table(chart)
        except Exception:
            return cls._render_fallback_table(chart)

    @classmethod
    def _render_bar_svg(cls, title: str, x_vals: list, y_vals: list, width: int, height: int) -> str:
        n = min(len(x_vals), 12)
        x_sub = x_vals[:n]
        y_sub = [float(v) if v is not None else 0.0 for v in y_vals[:n]]

        margin_l, margin_r, margin_t, margin_b = 65, 25, 35, 45
        plot_w = width - margin_l - margin_r
        plot_h = height - margin_t - margin_b

        max_y = max(y_sub) if y_sub and max(y_sub) > 0 else 1.0
        min_y = min(0.0, min(y_sub))
        y_range = max(max_y - min_y, 0.0001)

        slot_w = plot_w / max(n, 1)
        bar_w = min(slot_w * 0.65, 45.0)

        svg = [
            f'<div class="chart-wrapper avoid-break">',
            f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" '
            f'style="background:#F8FAFC; border-radius:8px; border:1px solid #E2E8F0; font-family: \'Segoe UI\', sans-serif;">',
        ]

        # Chart Title
        clean_title = html.escape(title, quote=True)
        svg.append(f'<text x="{margin_l}" y="22" font-size="11" font-weight="bold" fill="#1E1B4B">{clean_title}</text>')

        # Y-Grid lines and Ticks (4 levels)
        for i in range(5):
            val = min_y + (y_range * (i / 4))
            y_pos = margin_t + plot_h - (plot_h * (i / 4))
            svg.append(f'<line x1="{margin_l}" y1="{y_pos:.1f}" x2="{width - margin_r}" y2="{y_pos:.1f}" stroke="#E2E8F0" stroke-width="1" />')
            svg.append(f'<text x="{margin_l - 8}" y="{y_pos + 3:.1f}" font-size="8.5" text-anchor="end" fill="#64748B">{val:,.1f}</text>')

        # Zero Baseline
        base_y = margin_t + plot_h - (plot_h * ((0 - min_y) / y_range)) if min_y < 0 else margin_t + plot_h
        svg.append(f'<line x1="{margin_l}" y1="{base_y:.1f}" x2="{width - margin_r}" y2="{base_y:.1f}" stroke="#94A3B8" stroke-width="1.5" />')

        # Bars & Labels
        colors = ["#7C3AED", "#36C9F4", "#34D399", "#FBBF24", "#F472B6", "#A78BFA", "#60A5FA", "#FB923C"]
        for i, (x_name, y_val) in enumerate(zip(x_sub, y_sub)):
            x_center = margin_l + (i + 0.5) * slot_w
            x_bar = x_center - (bar_w / 2)
            h = abs(y_val) / y_range * plot_h
            y_bar = base_y - h if y_val >= 0 else base_y

            c = colors[i % len(colors)]
            clean_name = html.escape(str(x_name)[:12], quote=True)

            svg.append(f'<rect x="{x_bar:.1f}" y="{y_bar:.1f}" width="{bar_w:.1f}" height="{max(h, 2):.1f}" fill="{c}" rx="3" />')
            svg.append(f'<text x="{x_center:.1f}" y="{margin_t + plot_h + 16}" font-size="8.5" text-anchor="middle" fill="#475569">{clean_name}</text>')
            val_y = y_bar - 4 if y_val >= 0 else y_bar + h + 10
            svg.append(f'<text x="{x_center:.1f}" y="{val_y:.1f}" font-size="8" font-weight="bold" text-anchor="middle" fill="#1E1B4B">{y_val:,.1f}</text>')

        svg.append('</svg></div>')
        return "".join(svg)

    @classmethod
    def _render_line_svg(cls, title: str, x_vals: list, y_vals: list, width: int, height: int) -> str:
        n = min(len(x_vals), 24)
        x_sub = x_vals[:n]
        y_sub = [float(v) if v is not None else 0.0 for v in y_vals[:n]]

        margin_l, margin_r, margin_t, margin_b = 65, 25, 35, 45
        plot_w = width - margin_l - margin_r
        plot_h = height - margin_t - margin_b

        max_y = max(y_sub) if y_sub else 1.0
        min_y = min(y_sub) if y_sub else 0.0
        if max_y == min_y:
            max_y += 1.0
            min_y -= 1.0
        y_range = max(max_y - min_y, 0.0001)

        points = []
        for i, (x_name, y_val) in enumerate(zip(x_sub, y_sub)):
            x_pos = margin_l + (i / max(n - 1, 1)) * plot_w
            y_pos = margin_t + plot_h - ((y_val - min_y) / y_range * plot_h)
            points.append((x_pos, y_pos, x_name, y_val))

        svg = [
            f'<div class="chart-wrapper avoid-break">',
            f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" '
            f'style="background:#F8FAFC; border-radius:8px; border:1px solid #E2E8F0; font-family: \'Segoe UI\', sans-serif;">',
        ]

        # Title
        clean_title = html.escape(title, quote=True)
        svg.append(f'<text x="{margin_l}" y="22" font-size="11" font-weight="bold" fill="#1E1B4B">{clean_title}</text>')

        # Y-Grid lines and Ticks
        for i in range(5):
            val = min_y + (y_range * (i / 4))
            y_pos = margin_t + plot_h - (plot_h * (i / 4))
            svg.append(f'<line x1="{margin_l}" y1="{y_pos:.1f}" x2="{width - margin_r}" y2="{y_pos:.1f}" stroke="#E2E8F0" stroke-width="1" />')
            svg.append(f'<text x="{margin_l - 8}" y="{y_pos + 3:.1f}" font-size="8.5" text-anchor="end" fill="#64748B">{val:,.1f}</text>')

        # Area under curve
        if points:
            area_d = [f"M {points[0][0]:.1f} {margin_t + plot_h}"]
            for pt in points:
                area_d.append(f"L {pt[0]:.1f} {pt[1]:.1f}")
            area_d.append(f"L {points[-1][0]:.1f} {margin_t + plot_h} Z")
            svg.append(f'<path d="{" ".join(area_d)}" fill="rgba(124, 58, 237, 0.08)" />')

            # Line path
            line_d = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
            for pt in points[1:]:
                line_d.append(f"L {pt[0]:.1f} {pt[1]:.1f}")
            svg.append(f'<path d="{" ".join(line_d)}" fill="none" stroke="#7C3AED" stroke-width="2.5" />')

            # Points and Ticks
            step = max(1, n // 8)
            for i, (x_pos, y_pos, x_name, y_val) in enumerate(points):
                svg.append(f'<circle cx="{x_pos:.1f}" cy="{y_pos:.1f}" r="3.5" fill="#1E1B4B" stroke="#7C3AED" stroke-width="2" />')
                if i % step == 0 or i == n - 1:
                    clean_name = html.escape(str(x_name)[:10], quote=True)
                    svg.append(f'<text x="{x_pos:.1f}" y="{margin_t + plot_h + 16}" font-size="8" text-anchor="middle" fill="#475569">{clean_name}</text>')

        svg.append('</svg></div>')
        return "".join(svg)

    @classmethod
    def _render_pie_svg(cls, title: str, labels: list, values: list, width: int, height: int) -> str:
        # Fallback to tabular representation for multi-slice donut / pie
        return cls._render_fallback_table(
            ChartConfig(
                chart_id="pie_fallback",
                title=title,
                chart_type="pie",
                plotly_data=[{"x": labels, "y": values}],
            )
        )

    @staticmethod
    def _render_fallback_table(chart: ChartConfig) -> str:
        """Renders tabular data fallback if chart rendering is unavailable or fails."""
        clean_title = html.escape(chart.title, quote=True)
        rows_html = []
        if chart.plotly_data:
            tr = chart.plotly_data[0]
            x_vals = tr.get("x") or tr.get("labels") or []
            y_vals = tr.get("y") or tr.get("values") or []
            for x, y in list(zip(x_vals, y_vals))[:10]:
                rows_html.append(
                    f"<tr><td>{html.escape(str(x), quote=True)}</td>"
                    f"<td style='text-align:right;'>{html.escape(f'{y:,.2f}' if isinstance(y, (int, float)) else str(y), quote=True)}</td></tr>"
                )

        table_body = "".join(rows_html) if rows_html else "<tr><td colspan='2' style='color:#64748B;'>No visual chart data points available.</td></tr>"

        return f"""
        <div class="chart-fallback avoid-break" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px; margin-bottom:14px;">
          <div style="font-weight:bold; font-size:10pt; color:#1E1B4B; margin-bottom:6px;">{clean_title} (Analytical Data Table)</div>
          <table class="data-table" style="width:100%; font-size:8.5pt;">
            <thead><tr><th>Category / Period</th><th style="text-align:right;">Metric Value</th></tr></thead>
            <tbody>{table_body}</tbody>
          </table>
        </div>
        """


# =============================================================================
# Playwright PDF Report Builder
# =============================================================================

class PdfReportBuilder:
    """
    Renders pixel-perfect, print-optimized A4 executive intelligence PDF reports
    from ExecutiveReportData using Playwright Chromium with corporate branding,
    strict HTML escaping, and standalone vector SVG charts.
    """

    @classmethod
    async def generate_pdf_bytes(cls, report_data: ExecutiveReportData) -> bytes:
        """
        Asynchronously compiles the report HTML and uses Playwright headless Chromium
        to render a high-fidelity A4 PDF with running headers and footers.
        """
        async with async_playwright() as p:
            browser = None
            try:
                browser = await cls._launch_browser(p)
                page = await browser.new_page()

                # 1. Render complete self-contained HTML
                html_content = cls.render_html_report(report_data)

                # 2. Set content in Chromium page
                await page.set_content(html_content, wait_until="load")

                # 3. Running Header & Footer HTML Templates
                clean_confidentiality = html.escape(
                    report_data.confidentiality_notice or "CONFIDENTIAL & PROPRIETARY — FOR INTERNAL USE ONLY",
                    quote=True,
                )
                header_html = (
                    '<div style="font-family: \'Segoe UI\', sans-serif; font-size: 8px; color: #64748B; width: 100%; display: flex; justify-content: space-between; padding: 0 15mm; border-bottom: 1px solid #E2E8F0; padding-bottom: 3px;">'
                    '<span><strong>AutoAnalyst AI</strong> — Powered by Saniya</span>'
                    '<span>Your Autonomous Data Analyst</span>'
                    '</div>'
                )
                footer_html = (
                    '<div style="font-family: \'Segoe UI\', sans-serif; font-size: 8px; color: #64748B; width: 100%; display: flex; justify-content: space-between; padding: 0 15mm; border-top: 1px solid #E2E8F0; padding-top: 3px;">'
                    f'<span>{clean_confidentiality}</span>'
                    '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>'
                    '</div>'
                )

                # 4. Generate A4 PDF
                pdf_bytes = await page.pdf(
                    format="A4",
                    print_background=True,
                    display_header_footer=True,
                    header_template=header_html,
                    footer_template=footer_html,
                    margin={
                        "top": "20mm",
                        "bottom": "20mm",
                        "left": "15mm",
                        "right": "15mm",
                    },
                )
                return pdf_bytes
            finally:
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass

    @classmethod
    async def _launch_browser(cls, playwright_instance):
        """
        Launches Chromium headless browser safely across Windows and Linux cloud hosts.
        Supports standard Linux container flags (--no-sandbox, --disable-dev-shm-usage).
        Tries host Chrome, host Edge, standard Playwright Chromium, and known binary paths.
        """
        launch_errors = []
        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ]

        # 1. Try host installed Google Chrome (standard on Windows/Linux)
        try:
            return await playwright_instance.chromium.launch(
                headless=True,
                channel="chrome",
                args=launch_args,
            )
        except Exception as e:
            launch_errors.append(f"chrome_channel: {e}")

        # 2. Try host installed Microsoft Edge
        try:
            return await playwright_instance.chromium.launch(
                headless=True,
                channel="msedge",
                args=launch_args,
            )
        except Exception as e:
            launch_errors.append(f"msedge_channel: {e}")

        # 3. Try standard Playwright Chromium (Render & cloud container default)
        try:
            return await playwright_instance.chromium.launch(
                headless=True,
                args=launch_args,
            )
        except Exception as e:
            launch_errors.append(f"playwright_chromium: {e}")

        # 4. Try standard Windows and Linux executable paths
        known_paths = [
            # Windows
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            # Linux (Render, Ubuntu, Debian)
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]
        for kp in known_paths:
            if Path(kp).exists():
                try:
                    return await playwright_instance.chromium.launch(
                        headless=True,
                        executable_path=kp,
                        args=launch_args,
                    )
                except Exception as e:
                    launch_errors.append(f"{kp}: {e}")

        raise RuntimeError(
            "Failed to launch Chromium/Chrome browser for PDF report generation. "
            f"Errors encountered: {'; '.join(launch_errors)}"
        )

    # =========================================================================
    # HTML Report Assembly
    # =========================================================================

    @classmethod
    def render_html_report(cls, report_data: ExecutiveReportData) -> str:
        """
        Renders complete, self-contained HTML document for the executive report.
        Strictly escapes all user-controlled text and embeds standalone vector SVG charts.
        """
        sections_html = []

        # 1. Cover Page
        sections_html.append(cls._render_cover_page(report_data))

        # 2. Executive Summary & Health Score
        if report_data.executive_summary:
            sections_html.append(cls._render_executive_summary_section(report_data))

        # 3. Key KPIs
        if report_data.key_kpis:
            sections_html.append(cls._render_kpis_section(report_data))

        # 4. Key Findings
        if report_data.key_findings:
            sections_html.append(cls._render_key_findings_section(report_data))

        # 5. Category Benchmarks
        if report_data.category_benchmarks:
            sections_html.append(cls._render_category_benchmarks_section(report_data))

        # 6. Trends & Seasonality
        if report_data.trends_and_seasonality:
            sections_html.append(cls._render_trends_seasonality_section(report_data))

        # 7. Anomalies & Outliers
        if report_data.anomalies_and_risks:
            sections_html.append(cls._render_anomalies_section(report_data))

        # 8. Actionable Recommendations
        if report_data.recommendations:
            sections_html.append(cls._render_recommendations_section(report_data))

        # 9. Data Quality Audit
        if report_data.data_quality_audit:
            sections_html.append(cls._render_data_quality_section(report_data))

        # 10. Disclaimers & Grounded Fact Provenance
        sections_html.append(cls._render_disclaimers_section(report_data))

        body_content = "".join(sections_html)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(report_data.config.title, quote=True)}</title>
  <style>
    {cls._get_embedded_css()}
  </style>
</head>
<body>
  {body_content}
</body>
</html>"""

    # =========================================================================
    # CSS Stylesheet
    # =========================================================================

    @staticmethod
    def _get_embedded_css() -> str:
        """Returns self-contained CSS styles for print-optimized A4 executive reports."""
        return """
        @page {
          size: A4;
          margin: 20mm 15mm 20mm 15mm;
        }
        * {
          box-sizing: border-box;
        }
        body {
          font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
          margin: 0;
          padding: 0;
          color: #0F172A;
          background-color: #FFFFFF;
          font-size: 9pt;
          line-height: 1.45;
          -webkit-print-color-adjust: exact;
          print-color-adjust: exact;
        }
        .page-break {
          page-break-after: always;
          break-after: page;
        }
        .avoid-break {
          page-break-inside: avoid;
          break-inside: avoid;
        }
        
        /* Cover Page Styling */
        .cover-container {
          min-height: 82vh;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          padding: 30px 20px 20px 20px;
        }
        .brand-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          border-bottom: 2px solid #7C3AED;
          padding-bottom: 12px;
          margin-bottom: 40px;
        }
        .brand-logo-text {
          font-size: 20pt;
          font-weight: 800;
          color: #1E1B4B;
          letter-spacing: -0.5px;
        }
        .brand-tagline {
          font-size: 9.5pt;
          color: #7C3AED;
          font-weight: 600;
          margin-top: 3px;
        }
        .brand-attribution {
          font-size: 8.5pt;
          color: #64748B;
          font-weight: bold;
          text-align: right;
        }
        .cover-hero {
          margin: 30px 0;
        }
        .cover-title {
          font-size: 24pt;
          font-weight: 800;
          color: #1E1B4B;
          line-height: 1.2;
          margin-bottom: 10px;
        }
        .cover-subtitle {
          font-size: 13pt;
          color: #475569;
          font-weight: 500;
          margin-bottom: 25px;
        }
        .health-badge-large {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          background: #EDE9FE;
          border: 1px solid #C4B5FD;
          border-radius: 20px;
          padding: 6px 16px;
          color: #6D28D9;
          font-weight: bold;
          font-size: 11pt;
        }
        .metadata-card {
          background: #F8FAFC;
          border: 1px solid #E2E8F0;
          border-radius: 8px;
          padding: 16px 20px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px 24px;
          font-size: 8.5pt;
        }
        .meta-item {
          display: flex;
          flex-direction: column;
        }
        .meta-label {
          font-size: 7.5pt;
          font-weight: bold;
          text-transform: uppercase;
          color: #64748B;
          letter-spacing: 0.5px;
        }
        .meta-val {
          font-size: 9.5pt;
          font-weight: 600;
          color: #0F172A;
          word-break: break-all;
        }
        .cover-confidentiality {
          background: #1E1B4B;
          color: #FFFFFF;
          text-align: center;
          padding: 8px 14px;
          border-radius: 6px;
          font-size: 8pt;
          font-weight: bold;
          letter-spacing: 0.5px;
        }

        /* Section Headings */
        .section-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1.5px solid #1E1B4B;
          padding-bottom: 6px;
          margin: 22px 0 14px 0;
        }
        .section-title {
          font-size: 13pt;
          font-weight: 700;
          color: #1E1B4B;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .section-badge {
          font-size: 8pt;
          font-weight: 600;
          padding: 2px 8px;
          border-radius: 12px;
          background: #EDE9FE;
          color: #7C3AED;
        }

        /* KPI Cards Grid */
        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 10px;
          margin-bottom: 14px;
        }
        .kpi-card {
          background: #F8FAFC;
          border: 1px solid #E2E8F0;
          border-radius: 6px;
          padding: 10px 12px;
          text-align: center;
        }
        .kpi-val {
          font-size: 15pt;
          font-weight: 800;
          color: #1E1B4B;
          line-height: 1.2;
        }
        .kpi-lbl {
          font-size: 7.5pt;
          text-transform: uppercase;
          font-weight: bold;
          color: #64748B;
          margin-top: 3px;
          letter-spacing: 0.4px;
        }

        /* Executive Briefing Callout */
        .briefing-box {
          background: #F8FAFC;
          border-left: 4px solid #7C3AED;
          border-top: 1px solid #E2E8F0;
          border-right: 1px solid #E2E8F0;
          border-bottom: 1px solid #E2E8F0;
          border-radius: 0 8px 8px 0;
          padding: 14px 16px;
          margin-bottom: 14px;
          font-size: 9pt;
          line-height: 1.5;
        }
        .takeaway-list {
          margin: 8px 0 0 0;
          padding-left: 20px;
        }
        .takeaway-list li {
          margin-bottom: 4px;
          color: #334155;
        }

        /* Data Tables */
        table.data-table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 14px;
          font-size: 8.5pt;
        }
        table.data-table th {
          background-color: #1E1B4B;
          color: #FFFFFF;
          font-weight: bold;
          text-align: left;
          padding: 6px 8px;
          border: 1px solid #1E1B4B;
          font-size: 8pt;
        }
        table.data-table td {
          padding: 5px 8px;
          border: 1px solid #E2E8F0;
          color: #0F172A;
          vertical-align: middle;
        }
        table.data-table tr:nth-child(even) td {
          background-color: #F8FAFC;
        }

        /* Badges */
        .badge {
          display: inline-block;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 7.5pt;
          font-weight: bold;
          text-transform: uppercase;
        }
        .badge-high { background: #FEE2E2; color: #991B1B; }
        .badge-medium { background: #FEF3C7; color: #92400E; }
        .badge-notable { background: #DBEAFE; color: #1E40AF; }
        .badge-critical { background: #FEE2E2; color: #991B1B; }
        .badge-warning { background: #FEF3C7; color: #92400E; }
        .badge-info { background: #E0E7FF; color: #3730A3; }
        .badge-empirical { background: #D1FAE5; color: #065F46; }
        .badge-hypothesis { background: #FFEDD5; color: #9A3412; }
        .badge-trend-inc { background: #D1FAE5; color: #065F46; }
        .badge-trend-dec { background: #FEE2E2; color: #991B1B; }
        .badge-trend-stab { background: #DBEAFE; color: #1E40AF; }
        .badge-trend-fluc { background: #EDE9FE; color: #6D28D9; }

        /* Chart Container */
        .chart-wrapper {
          margin: 12px 0 16px 0;
          text-align: center;
        }
        
        .info-notice {
          background: #F8FAFC;
          border: 1px solid #CBD5E1;
          border-radius: 6px;
          padding: 10px 14px;
          font-size: 8.5pt;
          color: #475569;
          font-style: italic;
          margin-bottom: 12px;
        }
        """

    # =========================================================================
    # Section Renderers
    # =========================================================================

    @classmethod
    def _render_cover_page(cls, report_data: ExecutiveReportData) -> str:
        clean_title = html.escape(report_data.config.title, quote=True)
        clean_subtitle = html.escape(report_data.config.subtitle or "Executive Business Intelligence & Risk Audit", quote=True)
        clean_dataset = html.escape(report_data.dataset_name, quote=True)
        clean_dataset_id = html.escape(report_data.dataset_id, quote=True)
        clean_active_id = html.escape(report_data.active_dataset_id, quote=True)
        clean_hash = html.escape(report_data.snapshot_hash, quote=True)
        clean_date = html.escape(report_data.generated_at, quote=True)
        clean_notice = html.escape(report_data.confidentiality_notice or "CONFIDENTIAL & PROPRIETARY", quote=True)

        snapshot_type = f"Cleaned Version {report_data.cleaning_version}" if report_data.is_cleaned else "Original Dataset Snapshot"

        return f"""
        <div class="cover-container page-break">
          <div>
            <div class="brand-header">
              <div>
                <div class="brand-logo-text">AutoAnalyst AI</div>
                <div class="brand-tagline">Your Autonomous Data Analyst</div>
              </div>
              <div class="brand-attribution">Powered by Saniya</div>
            </div>

            <div class="cover-hero">
              <div class="cover-title">{clean_title}</div>
              <div class="cover-subtitle">{clean_subtitle}</div>
              <div class="health-badge-large">
                Overall Dataset Health: {report_data.health_score:,.1f} / 100
              </div>
            </div>
          </div>

          <div>
            <div class="metadata-card" style="margin-bottom: 20px;">
              <div class="meta-item">
                <span class="meta-label">Dataset Filename</span>
                <span class="meta-val">{clean_dataset}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Snapshot Version</span>
                <span class="meta-val">{snapshot_type}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Dataset ID</span>
                <span class="meta-val">{clean_dataset_id}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Active Snapshot ID</span>
                <span class="meta-val">{clean_active_id}</span>
              </div>
              <div class="meta-item" style="grid-column: span 2;">
                <span class="meta-label">SHA-256 Snapshot Checksum</span>
                <span class="meta-val" style="font-family: monospace; font-size: 8pt;">{clean_hash}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Analysis Timestamp</span>
                <span class="meta-val">{clean_date}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">Verification Integrity</span>
                <span class="meta-val" style="color: #059669;">Verified Empirical Facts</span>
              </div>
            </div>

            <div class="cover-confidentiality">{clean_notice}</div>
          </div>
        </div>
        """

    @classmethod
    def _render_executive_summary_section(cls, report_data: ExecutiveReportData) -> str:
        es = report_data.executive_summary
        if not es:
            return ""

        clean_narrative = html.escape(es.narrative, quote=True)
        mode_label = "AI Generated Narrative (Gemini)" if es.mode == "ai_generated" else "Deterministic Analytical Engine"

        takeaways_html = []
        if es.key_takeaways:
            for t in es.key_takeaways:
                takeaways_html.append(f"<li>{html.escape(t, quote=True)}</li>")
        takeaways_block = f"<ul class='takeaway-list'>{''.join(takeaways_html)}</ul>" if takeaways_html else ""

        return f"""
        <div class="section-container avoid-break">
          <div class="section-header">
            <div class="section-title">1. Executive Summary</div>
            <div class="section-badge">{mode_label}</div>
          </div>

          <div class="briefing-box">
            <div style="font-weight:bold; color:#1E1B4B; margin-bottom:6px;">Strategic Intelligence Briefing</div>
            <div>{clean_narrative}</div>
            {f'<div style="font-weight:bold; color:#1E1B4B; margin-top:10px;">Key Strategic Takeaways:</div>' + takeaways_block if takeaways_html else ''}
          </div>
        </div>
        """

    @classmethod
    def _render_kpis_section(cls, report_data: ExecutiveReportData) -> str:
        rk = report_data.key_kpis
        if not rk:
            return ""

        k = rk.kpis

        # Focus column stats if present
        focus_block = ""
        if k.selected_column_stats:
            st = k.selected_column_stats
            col_name = html.escape(str(st.get("column", "")), quote=True)
            focus_block = f"""
            <div class="avoid-break" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:10px 14px; margin-bottom:14px;">
              <div style="font-weight:bold; font-size:9.5pt; color:#1E1B4B; margin-bottom:6px;">Selected Focus Metric: {col_name}</div>
              <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; font-size:8.5pt;">
                <div><span class="meta-label">Sum Total</span><br><strong>{st.get('sum', 0.0):,.2f}</strong></div>
                <div><span class="meta-label">Mean Average</span><br><strong>{st.get('average', 0.0):,.2f}</strong></div>
                <div><span class="meta-label">Min / Max</span><br><strong>{st.get('minimum', 0.0):,.2f} / {st.get('maximum', 0.0):,.2f}</strong></div>
                <div><span class="meta-label">Zero Count</span><br><strong>{st.get('zeros_count', 0):,}</strong></div>
              </div>
            </div>
            """

        return f"""
        <div class="section-container avoid-break">
          <div class="section-header">
            <div class="section-title">2. Key Performance Indicators</div>
            <div class="section-badge">Dataset Health: {rk.health_score:,.1f}%</div>
          </div>

          <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-val">{k.total_rows:,}</div><div class="kpi-lbl">Total Records</div></div>
            <div class="kpi-card"><div class="kpi-val">{k.total_columns:,}</div><div class="kpi-lbl">Attributes</div></div>
            <div class="kpi-card"><div class="kpi-val">{k.data_completeness:,.1f}%</div><div class="kpi-lbl">Completeness</div></div>
            <div class="kpi-card"><div class="kpi-val">{k.missing_percentage:,.1f}%</div><div class="kpi-lbl">Missing Cells</div></div>
            <div class="kpi-card"><div class="kpi-val">{k.total_cells:,}</div><div class="kpi-lbl">Total Cells</div></div>
            <div class="kpi-card"><div class="kpi-val">{k.missing_cells:,}</div><div class="kpi-lbl">Empty Cells</div></div>
            <div class="kpi-card"><div class="kpi-val">{k.duplicate_rows:,}</div><div class="kpi-lbl">Duplicate Rows</div></div>
            <div class="kpi-card"><div class="kpi-val">{k.duplicate_percentage:,.1f}%</div><div class="kpi-lbl">Duplicate %</div></div>
          </div>

          {focus_block}
        </div>
        """

    @classmethod
    def _render_key_findings_section(cls, report_data: ExecutiveReportData) -> str:
        kf = report_data.key_findings
        if not kf or not kf.findings:
            return ""

        rows_html = []
        for f in kf.findings:
            imp_badge = f'<span class="badge badge-{f.importance}">{f.importance.upper()}</span>'
            clean_title = html.escape(f.title, quote=True)
            clean_desc = html.escape(f.description, quote=True)
            cols_clean = html.escape(", ".join(f.columns_involved), quote=True) if f.columns_involved else "Dataset"
            facts_clean = html.escape(", ".join(f.referenced_fact_ids), quote=True) if f.referenced_fact_ids else "N/A"

            rows_html.append(f"""
            <tr>
              <td style="font-family:monospace; font-size:7.5pt;">{html.escape(f.finding_id, quote=True)}</td>
              <td>{imp_badge}</td>
              <td><span class="badge badge-info">{html.escape(f.category.title(), quote=True)}</span></td>
              <td style="text-align:right; font-weight:bold;">{f.significance_score * 100:,.1f}%</td>
              <td><strong>{clean_title}</strong><br><span style="color:#475569; font-size:8pt;">{clean_desc}</span></td>
              <td style="font-size:7.5pt; color:#64748B;">{cols_clean}</td>
              <td style="font-family:monospace; font-size:7pt; color:#7C3AED;">{facts_clean}</td>
            </tr>
            """)

        return f"""
        <div class="section-container avoid-break">
          <div class="section-header">
            <div class="section-title">3. Automated Key Findings</div>
            <div class="section-badge">{kf.total_count} Discoveries ({kf.high_importance_count} High)</div>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th style="width:70px;">ID</th>
                <th style="width:65px;">Priority</th>
                <th style="width:75px;">Category</th>
                <th style="width:60px; text-align:right;">Score</th>
                <th>Analytical Finding & Detail</th>
                <th style="width:90px;">Columns</th>
                <th style="width:70px;">Fact IDs</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows_html)}
            </tbody>
          </table>
        </div>
        """

    @classmethod
    def _render_category_benchmarks_section(cls, report_data: ExecutiveReportData) -> str:
        cb = report_data.category_benchmarks
        if not cb or not cb.benchmarks:
            return ""

        benchmarks_html = []
        for b in cb.benchmarks:
            dim_clean = html.escape(b.dimension_column, quote=True)
            met_clean = html.escape(b.metric_column or "Count", quote=True)
            clean_exp = html.escape(b.explanation, quote=True)
            facts_clean = html.escape(", ".join(b.referenced_fact_ids), quote=True)

            best_delta = f"{b.best_performer.delta_vs_average_pct:+,.1f}%"
            worst_delta = f"{b.worst_performer.delta_vs_average_pct:+,.1f}%"

            # Render embedded SVG chart if present and requested
            chart_html = ""
            if report_data.config.include_charts and b.chart:
                chart_html = SvgChartRenderer.render_chart(b.chart)

            # Ranked performers table
            ranked_rows = []
            for p in b.ranked_performers[:8]:
                rel_badge = (
                    '<span class="badge badge-empirical">Reliable (n>=5)</span>'
                    if p.is_statistically_reliable
                    else '<span class="badge badge-warning">Small (n<5)</span>'
                )
                delta_str = f"{p.delta_vs_average_pct:+,.1f}%"
                delta_color = "#059669" if p.delta_vs_average_pct >= 0 else "#DC2626"

                ranked_rows.append(f"""
                <tr>
                  <td><strong>{html.escape(p.category_name, quote=True)}</strong></td>
                  <td style="text-align:right;">{p.metric_value:,.2f}</td>
                  <td style="text-align:right; font-weight:bold; color:{delta_color};">{delta_str}</td>
                  <td style="text-align:right;">{p.sample_size:,}</td>
                  <td style="text-align:center;">{rel_badge}</td>
                </tr>
                """)

            benchmarks_html.append(f"""
            <div class="avoid-break" style="margin-bottom:16px;">
              <div style="font-weight:bold; font-size:10pt; color:#1E1B4B; margin-bottom:6px;">
                Dimension: {dim_clean} &bull; Metric: {met_clean} ({b.aggregation.upper()}) &bull; Avg: {b.dataset_average:,.2f}
              </div>

              <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:10px;">
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px; padding:8px 12px;">
                  <span class="meta-label" style="color:#166534;">Top Performer</span><br>
                  <strong style="font-size:11pt; color:#14532D;">{html.escape(b.best_performer.category_name, quote=True)}</strong>
                  <span style="color:#059669; font-weight:bold; margin-left:8px;">{best_delta} vs avg</span><br>
                  <span style="font-size:8pt; color:#475569;">Value: {b.best_performer.formatted_value} (n={b.best_performer.sample_size})</span>
                </div>

                <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:6px; padding:8px 12px;">
                  <span class="meta-label" style="color:#991B1B;">Lowest Performer</span><br>
                  <strong style="font-size:11pt; color:#7F1D1D;">{html.escape(b.worst_performer.category_name, quote=True)}</strong>
                  <span style="color:#DC2626; font-weight:bold; margin-left:8px;">{worst_delta} vs avg</span><br>
                  <span style="font-size:8pt; color:#475569;">Value: {b.worst_performer.formatted_value} (n={b.worst_performer.sample_size})</span>
                </div>
              </div>

              {chart_html}

              <table class="data-table" style="font-size:8pt; margin-top:8px;">
                <thead>
                  <tr>
                    <th>Category Name</th>
                    <th style="text-align:right;">Metric Value</th>
                    <th style="text-align:right;">Delta vs Avg</th>
                    <th style="text-align:right;">Sample Size</th>
                    <th style="text-align:center;">Reliability</th>
                  </tr>
                </thead>
                <tbody>
                  {''.join(ranked_rows)}
                </tbody>
              </table>

              <div style="font-size:8pt; color:#475569; font-style:italic; margin-top:4px;">
                {clean_exp} <span style="font-family:monospace; color:#7C3AED;">[Facts: {facts_clean}]</span>
              </div>
            </div>
            """)

        return f"""
        <div class="section-container avoid-break">
          <div class="section-header">
            <div class="section-title">4. Category Benchmarks</div>
            <div class="section-badge">{cb.dimension_count} Dimensions Evaluated</div>
          </div>
          {''.join(benchmarks_html)}
        </div>
        """

    @classmethod
    def _render_trends_seasonality_section(cls, report_data: ExecutiveReportData) -> str:
        ts = report_data.trends_and_seasonality
        if not ts:
            return ""

        if not ts.has_temporal_data:
            return f"""
            <div class="section-container avoid-break">
              <div class="section-header">
                <div class="section-title">5. Temporal Trends & Seasonality</div>
                <div class="section-badge">No Temporal Data</div>
              </div>
              <div class="info-notice">
                Dataset contains no valid datetime columns for chronological trend or seasonality analysis.
              </div>
            </div>
            """

        trends_html = []
        for t in ts.trends:
            dir_map = {
                "increasing": "badge-trend-inc",
                "decreasing": "badge-trend-dec",
                "stable": "badge-trend-stab",
                "fluctuating": "badge-trend-fluc",
            }
            dir_badge = f'<span class="badge {dir_map.get(t.direction, "badge-info")}">{t.direction.upper()}</span>'
            growth_val = f"{t.conventional_growth_pct:+,.1f}%" if t.conventional_growth_pct is not None else (f"{t.range_normalized_shift_pct:+,.1f}% (shift)" if t.range_normalized_shift_pct is not None else "N/A")

            chart_html = ""
            if report_data.config.include_charts and t.chart:
                chart_html = SvgChartRenderer.render_chart(t.chart)

            trends_html.append(f"""
            <div class="avoid-break" style="margin-bottom:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-weight:bold; font-size:10pt; color:#1E1B4B;">
                  {html.escape(t.metric_column, quote=True)} across {html.escape(t.date_column, quote=True)} ({t.granularity.title()})
                </span>
                <span>{dir_badge}</span>
              </div>

              <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:8px 12px; margin-bottom:8px; font-size:8.5pt;">
                <div><span class="meta-label">Statistical Evidence</span><br><strong>{t.statistical_evidence.replace('_', ' ').title()}</strong></div>
                <div><span class="meta-label">Business Magnitude</span><br><strong>{t.business_magnitude.title()}</strong></div>
                <div><span class="meta-label">R² Strength</span><br><strong>{t.trend_strength_r2:.3f}</strong></div>
                <div><span class="meta-label">Net Change</span><br><strong>{t.absolute_change:+,.2f} ({growth_val})</strong></div>
              </div>

              {chart_html}

              <div style="font-size:8pt; color:#475569; margin-top:4px;">
                {html.escape(t.explanation, quote=True)}
                <span style="font-family:monospace; color:#7C3AED;">[Facts: {html.escape(', '.join(t.referenced_fact_ids), quote=True)}]</span>
              </div>
            </div>
            """)

        # Seasonality subsection if analyzed
        seas_html = ""
        if ts.seasonality:
            s = ts.seasonality
            seas_html = f"""
            <div class="avoid-break" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:10px 14px; margin-top:10px;">
              <div style="font-weight:bold; font-size:9.5pt; color:#1E1B4B; margin-bottom:4px;">
                Seasonality Audit: {s.status.replace('_', ' ').title()} ({html.escape(s.cycle_type or 'None', quote=True)})
              </div>
              <div style="font-size:8pt; color:#475569; margin-bottom:6px;">{html.escape(s.explanation, quote=True)}</div>
              <div style="display:flex; gap:16px; font-size:8pt;">
                <span><strong>Peak:</strong> {html.escape(s.peak_season or 'N/A', quote=True)}</span>
                <span><strong>Trough:</strong> {html.escape(s.trough_season or 'N/A', quote=True)}</span>
                <span><strong>ANOVA p-val:</strong> {s.anova_p_value if s.anova_p_value is not None else 'N/A'}</span>
              </div>
            </div>
            """

        return f"""
        <div class="section-container avoid-break">
          <div class="section-header">
            <div class="section-title">5. Temporal Trends & Seasonality</div>
            <div class="section-badge">{len(ts.trends)} Trends Analyzed</div>
          </div>
          {''.join(trends_html)}
          {seas_html}
        </div>
        """

    @classmethod
    def _render_anomalies_section(cls, report_data: ExecutiveReportData) -> str:
        ar = report_data.anomalies_and_risks
        if not ar:
            return ""

        if not ar.anomalies and not ar.temporal_anomalies:
            return f"""
            <div class="section-container avoid-break">
              <div class="section-header">
                <div class="section-title">6. Anomalies & Outliers</div>
                <div class="section-badge">Clean (0 Anomalies)</div>
              </div>
              <div class="info-notice">No severe statistical anomalies or unusual outliers detected across the dataset.</div>
            </div>
            """

        rows_html = []
        for a in ar.anomalies:
            sev_badge = f'<span class="badge badge-{a.severity}">{a.severity.upper()}</span>'
            clean_type = html.escape(a.anomaly_type.replace('_', ' ').title(), quote=True)
            clean_col = html.escape(a.column_name, quote=True)
            clean_desc = html.escape(a.description, quote=True)

            rows_html.append(f"""
            <tr>
              <td style="font-family:monospace; font-size:7.5pt;">{html.escape(a.anomaly_id, quote=True)}</td>
              <td>{sev_badge}</td>
              <td><span class="badge badge-info">{clean_type}</span></td>
              <td><strong>{clean_col}</strong></td>
              <td>{clean_desc}</td>
            </tr>
            """)

        for ta in ar.temporal_anomalies:
            sev_badge = f'<span class="badge badge-{ta.severity}">{ta.severity.upper()}</span>'
            clean_type = html.escape(ta.anomaly_type.replace('_', ' ').title(), quote=True)
            clean_col = html.escape(f"{ta.metric_column} ({ta.date_column})", quote=True)
            delta_str = f"{ta.delta_pct:+,.1f}%" if ta.delta_pct is not None else f"{ta.delta_abs:+,.2f}"
            clean_desc = html.escape(f"Period {ta.period_label}: Shift from {ta.previous_value:,.2f} to {ta.current_value:,.2f} ({delta_str}). {ta.detection_reason}", quote=True)

            rows_html.append(f"""
            <tr>
              <td style="font-family:monospace; font-size:7.5pt;">{html.escape(ta.anomaly_id, quote=True)}</td>
              <td>{sev_badge}</td>
              <td><span class="badge badge-warning">{clean_type}</span></td>
              <td><strong>{clean_col}</strong></td>
              <td>{clean_desc}</td>
            </tr>
            """)

        return f"""
        <div class="section-container avoid-break">
          <div class="section-header">
            <div class="section-title">6. Anomalies & Outliers</div>
            <div class="section-badge">{ar.total_anomaly_count} Anomalies Detected</div>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th style="width:75px;">ID</th>
                <th style="width:65px;">Severity</th>
                <th style="width:95px;">Anomaly Type</th>
                <th style="width:110px;">Target Column</th>
                <th>Observation & Evidence Detail</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows_html)}
            </tbody>
          </table>
        </div>
        """

    @classmethod
    def _render_recommendations_section(cls, report_data: ExecutiveReportData) -> str:
        rec = report_data.recommendations
        if not rec or not rec.recommendations:
            return ""

        rows_html = []
        for r in rec.recommendations:
            prio_badge = f'<span class="badge badge-{r.priority}">{r.priority.upper()}</span>'
            prov_badge = (
                '<span class="badge badge-hypothesis">Analytical Hypothesis</span>'
                if r.is_hypothesis
                else '<span class="badge badge-empirical">Verified Empirical Fact</span>'
            )

            clean_title = html.escape(r.title, quote=True)
            clean_action = html.escape(r.action_statement, quote=True)
            clean_impact = html.escape(r.expected_impact, quote=True)
            facts_clean = html.escape(", ".join(r.referenced_fact_ids), quote=True) if r.referenced_fact_ids else "N/A"

            rows_html.append(f"""
            <tr>
              <td style="font-family:monospace; font-size:7.5pt;">{html.escape(r.recommendation_id, quote=True)}</td>
              <td>{prio_badge}</td>
              <td>{prov_badge}</td>
              <td>
                <strong style="color:#1E1B4B;">{clean_title}</strong><br>
                <span style="color:#334155; font-size:8pt;"><strong>Action:</strong> {clean_action}</span><br>
                <span style="color:#059669; font-size:8pt;"><strong>Impact:</strong> {clean_impact}</span>
              </td>
              <td style="font-family:monospace; font-size:7pt; color:#7C3AED;">{facts_clean}</td>
            </tr>
            """)

        return f"""
        <div class="section-container avoid-break">
          <div class="section-header">
            <div class="section-title">7. Actionable Recommendations</div>
            <div class="section-badge">{rec.total_count} Actions ({rec.empirical_facts_count} Empirical, {rec.analytical_hypotheses_count} Hypotheses)</div>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th style="width:70px;">ID</th>
                <th style="width:65px;">Priority</th>
                <th style="width:130px;">Evidence Type</th>
                <th>Strategic Action & Expected Business Impact</th>
                <th style="width:75px;">Fact IDs</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows_html)}
            </tbody>
          </table>
        </div>
        """

    @classmethod
    def _render_data_quality_section(cls, report_data: ExecutiveReportData) -> str:
        dqa = report_data.data_quality_audit
        if not dqa:
            return ""

        rows_html = []
        if dqa.quality_profile and dqa.quality_profile.columns:
            for c in dqa.quality_profile.columns[:10]:
                clean_name = html.escape(c.column_name, quote=True)
                clean_type = html.escape(c.data_type, quote=True)
                iqr_str = f"{c.outliers_iqr_count:,}" if c.outliers_iqr_count is not None else "N/A"
                zscore_str = f"{c.outliers_zscore_count:,}" if c.outliers_zscore_count is not None else "N/A"

                rows_html.append(f"""
                <tr>
                  <td><strong>{clean_name}</strong></td>
                  <td>{clean_type}</td>
                  <td style="text-align:right;">{c.total_count:,}</td>
                  <td style="text-align:right;">{c.missing_count:,}</td>
                  <td style="text-align:right;">{c.missing_percentage:,.1f}%</td>
                  <td style="text-align:right;">{c.unique_count:,}</td>
                  <td style="text-align:center;">{iqr_str}</td>
                  <td style="text-align:center;">{zscore_str}</td>
                </tr>
                """)

        cols_table = f"""
        <table class="data-table" style="margin-top:10px;">
          <thead>
            <tr>
              <th>Column Name</th>
              <th>Data Type</th>
              <th style="text-align:right;">Total</th>
              <th style="text-align:right;">Missing</th>
              <th style="text-align:right;">Null %</th>
              <th style="text-align:right;">Unique</th>
              <th style="text-align:center;">IQR Outliers</th>
              <th style="text-align:center;">Z-Score Outliers</th>
            </tr>
          </thead>
          <tbody>{''.join(rows_html)}</tbody>
        </table>
        """ if rows_html else ""

        return f"""
        <div class="section-container avoid-break">
          <div class="section-header">
            <div class="section-title">8. Data Quality & Health Audit</div>
            <div class="section-badge">Grade: {html.escape(dqa.quality_grade, quote=True)} ({dqa.overall_quality_score:,.1f} / 100)</div>
          </div>

          <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-val">{dqa.overall_quality_score:,.1f}</div><div class="kpi-lbl">Quality Score</div></div>
            <div class="kpi-card"><div class="kpi-val">{dqa.completeness_score:,.1f}%</div><div class="kpi-lbl">Completeness</div></div>
            <div class="kpi-card"><div class="kpi-val">{dqa.uniqueness_score:,.1f}%</div><div class="kpi-lbl">Uniqueness</div></div>
            <div class="kpi-card"><div class="kpi-val">{dqa.validity_score:,.1f}%</div><div class="kpi-lbl">Validity</div></div>
          </div>

          {cols_table}
        </div>
        """

    @classmethod
    def _render_disclaimers_section(cls, report_data: ExecutiveReportData) -> str:
        # Verified fact provenance table
        fact_rows = []
        if report_data.grounded_facts:
            for f in report_data.grounded_facts[:12]:
                fact_rows.append(f"""
                <tr>
                  <td style="font-family:monospace; font-size:7.5pt; color:#7C3AED;">{html.escape(f.fact_id, quote=True)}</td>
                  <td>{html.escape(f.category.title(), quote=True)}</td>
                  <td>{html.escape(f.metric_name, quote=True)}</td>
                  <td>{html.escape(f.formatted_statement, quote=True)}</td>
                </tr>
                """)

        facts_table = f"""
        <table class="data-table" style="font-size:8pt; margin-top:8px;">
          <thead>
            <tr>
              <th style="width:75px;">Fact ID</th>
              <th style="width:80px;">Category</th>
              <th style="width:110px;">Metric</th>
              <th>Verified Empirical Statement</th>
            </tr>
          </thead>
          <tbody>{''.join(fact_rows)}</tbody>
        </table>
        """ if fact_rows else "<div class='info-notice'>No grounded empirical facts registered.</div>"

        # Disclaimers
        disclaimers = list(report_data.date_scoping_limitations) + list(report_data.limitations)
        disc_items = []
        for d in disclaimers:
            disc_items.append(f"<li>{html.escape(d, quote=True)}</li>")
        disc_list = f"<ul class='takeaway-list'>{''.join(disc_items)}</ul>" if disc_items else "<p style='color:#64748B;'>No scope constraints or date limitations reported.</p>"

        return f"""
        <div class="section-container avoid-break" style="margin-top:20px;">
          <div class="section-header">
            <div class="section-title">9. Evidence Provenance & Disclaimers</div>
            <div class="section-badge">{len(report_data.grounded_facts)} Facts Verified</div>
          </div>

          <div style="font-weight:bold; font-size:9.5pt; color:#1E1B4B; margin-bottom:4px;">Verified Empirical Facts Registry</div>
          {facts_table}

          <div style="font-weight:bold; font-size:9.5pt; color:#1E1B4B; margin-top:14px; margin-bottom:4px;">Reporting Scope & Analytical Limitations</div>
          <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:10px 14px; font-size:8pt;">
            {disc_list}
          </div>
        </div>
        """

