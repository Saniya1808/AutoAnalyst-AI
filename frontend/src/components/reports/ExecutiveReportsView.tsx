/**
 * AutoAnalyst AI — Executive Reports & Business Intelligence View
 *
 * Brand: Powered by Saniya
 * Tagline: Your Autonomous Data Analyst
 *
 * Provides an interactive report configuration customizer, live document preview,
 * verified fact-grounding badges, one-click PDF streaming export, 8-worksheet Excel export,
 * and browser print preview.
 */

import React, { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Award,
  CheckCircle2,
  CheckSquare,
  Clock,
  Download,
  FileSpreadsheet,
  FileText,
  Filter,
  Info,
  Lock,
  Printer,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import {
  exportReportExcel,
  exportReportPdf,
  generateExecutiveReport,
  triggerFileDownload,
} from '../../services/api'
import type {
  ExecutiveReportData,
  ReportConfigRequest,
  ReportSectionId,
} from '../../types/reports'
import { ALL_REPORT_SECTIONS, REPORT_SECTION_META } from '../../types/reports'
import { InteractiveChart } from '../dashboard/InteractiveChart'

interface ExecutiveReportsViewProps {
  datasetId: string
  datasetFilename: string
}

export const ExecutiveReportsView: React.FC<ExecutiveReportsViewProps> = ({
  datasetId,
  datasetFilename,
}) => {
  // Configuration state
  const [reportTitle, setReportTitle] = useState('Executive Intelligence Report')
  const [reportSubtitle, setReportSubtitle] = useState(
    `Comprehensive Business Intelligence Audit • ${datasetFilename}`
  )
  const [confidentialityNotice, setConfidentialityNotice] = useState(
    'CONFIDENTIAL & PROPRIETARY — FOR INTERNAL USE ONLY'
  )
  const [selectedSections, setSelectedSections] = useState<ReportSectionId[]>(ALL_REPORT_SECTIONS)
  const [includeCharts, setIncludeCharts] = useState(true)
  const [dateRangeStart, setDateRangeStart] = useState('')
  const [dateRangeEnd, setDateRangeEnd] = useState('')
  const [isConfigExpanded, setIsConfigExpanded] = useState(false)

  // Data & loading state
  const [reportData, setReportData] = useState<ExecutiveReportData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isExportingPdf, setIsExportingPdf] = useState(false)
  const [isExportingExcel, setIsExportingExcel] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successToast, setSuccessToast] = useState<string | null>(null)

  // Build request payload
  const buildConfigRequest = useCallback((): ReportConfigRequest => {
    return {
      title: reportTitle.trim() || 'Executive Intelligence Report',
      subtitle: reportSubtitle.trim() || undefined,
      selected_sections: selectedSections,
      include_charts: includeCharts,
      date_range_start: dateRangeStart.trim() || undefined,
      date_range_end: dateRangeEnd.trim() || undefined,
      confidentiality_notice: confidentialityNotice.trim() || undefined,
    }
  }, [
    reportTitle,
    reportSubtitle,
    selectedSections,
    includeCharts,
    dateRangeStart,
    dateRangeEnd,
    confidentialityNotice,
  ])

  // Fetch / Generate report
  const handleGenerateReport = useCallback(async () => {
    setIsLoading(true)
    setErrorMessage(null)
    try {
      const config = buildConfigRequest()
      const data = await generateExecutiveReport(datasetId, config)
      setReportData(data)
      setSuccessToast('Executive report preview generated successfully.')
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to generate executive report preview.'
      )
    } finally {
      setIsLoading(false)
    }
  }, [datasetId, buildConfigRequest])

  // Auto-generate preview on first load or when datasetId changes
  useEffect(() => {
    setReportSubtitle(`Comprehensive Business Intelligence Audit • ${datasetFilename}`)
    handleGenerateReport()
  }, [datasetId, datasetFilename])

  // Toggle individual section inclusion
  const handleToggleSection = (sectionId: ReportSectionId) => {
    setSelectedSections((prev) => {
      if (prev.includes(sectionId)) {
        if (prev.length === 1) {
          return prev // Keep at least one section
        }
        return prev.filter((s) => s !== sectionId)
      } else {
        return [...prev, sectionId]
      }
    })
  }

  // Select all or reset sections
  const handleSelectAllSections = () => {
    setSelectedSections([...ALL_REPORT_SECTIONS])
  }

  // Export PDF Handler
  const handleExportPdf = async () => {
    if (isExportingPdf) return
    setIsExportingPdf(true)
    setErrorMessage(null)
    try {
      const config = buildConfigRequest()
      const { blob, filename } = await exportReportPdf(datasetId, config)
      triggerFileDownload(blob, filename)
      setSuccessToast(`Executive PDF downloaded: ${filename}`)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'PDF export failed.')
    } finally {
      setIsExportingPdf(false)
    }
  }

  // Export Excel Handler
  const handleExportExcel = async () => {
    if (isExportingExcel) return
    setIsExportingExcel(true)
    setErrorMessage(null)
    try {
      const config = buildConfigRequest()
      const { blob, filename } = await exportReportExcel(datasetId, config)
      triggerFileDownload(blob, filename)
      setSuccessToast(`Executive Excel workbook downloaded: ${filename}`)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Excel export failed.')
    } finally {
      setIsExportingExcel(false)
    }
  }

  // Print Preview Handler
  const handlePrint = () => {
    window.print()
  }

  return (
    <div className="reports-view-wrapper">
      {/* Notifications */}
      {successToast && (
        <div className="success-toast-banner print-hide">
          <CheckCircle2 size={16} />
          <span>{successToast}</span>
          <button
            type="button"
            className="toast-close-btn"
            onClick={() => setSuccessToast(null)}
          >
            ×
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="error-toast-banner print-hide">
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
          <button
            type="button"
            className="toast-close-btn"
            onClick={() => setErrorMessage(null)}
          >
            ×
          </button>
        </div>
      )}

      {/* Control Header & Actions Bar */}
      <div className="reports-action-bar print-hide">
        <div className="reports-action-bar-left">
          <div className="reports-header-icon-badge">
            <FileText size={22} />
          </div>
          <div>
            <h2 className="reports-main-heading">Executive Intelligence Reports</h2>
            <p className="reports-subheading">
              Powered by Saniya • <i>Your Autonomous Data Analyst</i>
            </p>
          </div>
        </div>

        <div className="reports-action-buttons-group">
          <button
            type="button"
            className="button button-secondary text-sm-btn"
            onClick={() => setIsConfigExpanded(!isConfigExpanded)}
            title="Configure report title, sections, and date ranges"
          >
            <Filter size={15} />
            {isConfigExpanded ? 'Hide Options' : 'Customize Report'}
          </button>

          <button
            type="button"
            className="button button-secondary text-sm-btn"
            onClick={handleGenerateReport}
            disabled={isLoading || isExportingPdf || isExportingExcel}
            title="Refresh preview with updated settings"
          >
            <RefreshCw size={15} className={isLoading ? 'animate-spin' : ''} />
            {isLoading ? 'Assembling...' : 'Update Preview'}
          </button>

          <button
            type="button"
            className="button button-secondary text-sm-btn"
            onClick={handlePrint}
            disabled={!reportData}
            title="Print or save as PDF via browser print"
          >
            <Printer size={15} />
            Print View
          </button>

          <button
            type="button"
            className="button button-secondary text-sm-btn export-excel-btn"
            onClick={handleExportExcel}
            disabled={isExportingExcel || !reportData}
            title="Download formatted 8-worksheet Excel workbook"
          >
            <FileSpreadsheet size={15} />
            {isExportingExcel ? 'Building XLSX...' : 'Download Excel'}
          </button>

          <button
            type="button"
            className="button button-primary text-sm-btn export-pdf-btn"
            onClick={handleExportPdf}
            disabled={isExportingPdf || !reportData}
            title="Download publication-grade executive PDF"
          >
            <Download size={15} />
            {isExportingPdf ? 'Rendering PDF...' : 'Download PDF'}
          </button>
        </div>
      </div>

      {/* Expandable Configuration Drawer */}
      {isConfigExpanded && (
        <div className="reports-config-card print-hide">
          <div className="reports-config-header">
            <h4>Report Configuration & Section Filters</h4>
            <button
              type="button"
              className="text-xs-btn link-style-btn"
              onClick={handleSelectAllSections}
            >
              Select All 8 Sections
            </button>
          </div>

          <div className="reports-config-grid">
            <div className="config-field-group">
              <label htmlFor="report-title-input">Report Title</label>
              <input
                id="report-title-input"
                type="text"
                className="input-field"
                value={reportTitle}
                maxLength={150}
                onChange={(e) => setReportTitle(e.target.value)}
                placeholder="Executive Intelligence Report"
              />
            </div>

            <div className="config-field-group">
              <label htmlFor="report-subtitle-input">Custom Subtitle / Context</label>
              <input
                id="report-subtitle-input"
                type="text"
                className="input-field"
                value={reportSubtitle}
                maxLength={250}
                onChange={(e) => setReportSubtitle(e.target.value)}
                placeholder="e.g. Q4 Business Performance & Quality Audit"
              />
            </div>

            <div className="config-field-group">
              <label htmlFor="report-confidentiality-input">Confidentiality Notice</label>
              <input
                id="report-confidentiality-input"
                type="text"
                className="input-field"
                value={confidentialityNotice}
                maxLength={200}
                onChange={(e) => setConfidentialityNotice(e.target.value)}
                placeholder="CONFIDENTIAL & PROPRIETARY"
              />
            </div>

            <div className="config-field-group">
              <label>Visualization Options</label>
              <div className="checkbox-toggle-row">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={includeCharts}
                    onChange={(e) => setIncludeCharts(e.target.checked)}
                  />
                  <span>Include Visual Interactive Charts</span>
                </label>
              </div>
            </div>

            <div className="config-field-group">
              <label htmlFor="report-date-start">Date Range Start (Optional)</label>
              <input
                id="report-date-start"
                type="date"
                className="input-field"
                value={dateRangeStart}
                onChange={(e) => setDateRangeStart(e.target.value)}
              />
            </div>

            <div className="config-field-group">
              <label htmlFor="report-date-end">Date Range End (Optional)</label>
              <input
                id="report-date-end"
                type="date"
                className="input-field"
                value={dateRangeEnd}
                onChange={(e) => setDateRangeEnd(e.target.value)}
              />
            </div>
          </div>

          <div className="date-scope-disclaimer">
            <Info size={14} />
            <span>
              <strong>Date-Scoping Notice:</strong> Start and end date filters focus longitudinal
              trend and time-series analyses. Aggregate KPIs and dataset-wide quality audits reflect
              the active snapshot.
            </span>
          </div>

          {/* Section Selection Toggles */}
          <div className="sections-toggle-container">
            <span className="sections-toggle-label">Include Sections in Document:</span>
            <div className="sections-toggle-grid">
              {ALL_REPORT_SECTIONS.map((secId) => {
                const meta = REPORT_SECTION_META[secId]
                const isSelected = selectedSections.includes(secId)
                return (
                  <button
                    key={secId}
                    type="button"
                    className={`section-toggle-pill ${isSelected ? 'active' : ''}`}
                    onClick={() => handleToggleSection(secId)}
                  >
                    <CheckSquare size={14} className={isSelected ? 'text-accent' : 'opacity-40'} />
                    <span>{meta.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Main Report Container */}
      {isLoading && !reportData ? (
        <div className="report-loading-state">
          <div className="spinner-large" />
          <p className="loading-title">Assembling Executive Report...</p>
          <p className="loading-subtitle">
            Aggregating multi-engine intelligence across KPIs, automated insights, trends, and data
            quality.
          </p>
        </div>
      ) : reportData ? (
        <div className="reports-preview-paper" id="executive-report-document">
          {/* Executive Cover & Header Banner */}
          <div className="report-cover-banner">
            <div className="report-cover-top">
              <div className="report-brand-badge">
                <Sparkles size={16} />
                <span>AutoAnalyst AI</span>
                <span className="brand-dot">•</span>
                <span className="brand-author">Powered by Saniya</span>
              </div>
              <div className="report-confidentiality-tag">
                <Lock size={12} />
                <span>{reportData.confidentiality_notice || 'CONFIDENTIAL'}</span>
              </div>
            </div>

            <h1 className="report-doc-title">{reportData.config.title || reportTitle}</h1>
            {reportData.config.subtitle && (
              <p className="report-doc-subtitle">{reportData.config.subtitle}</p>
            )}

            <div className="report-metadata-bar">
              <div className="metadata-item">
                <span className="meta-label">Dataset:</span>
                <span className="meta-value">{reportData.dataset_name}</span>
              </div>
              <div className="metadata-item">
                <span className="meta-label">Snapshot State:</span>
                <span
                  className={`meta-badge ${reportData.is_cleaned ? 'badge-cleaned' : 'badge-raw'}`}
                >
                  {reportData.is_cleaned
                    ? `Cleaned Snapshot (v${reportData.cleaning_version})`
                    : 'Original Raw'}
                </span>
              </div>
              <div className="metadata-item">
                <span className="meta-label">Snapshot SHA-256:</span>
                <span
                  className="meta-hash"
                  title={`Full SHA-256: ${reportData.snapshot_hash}`}
                >
                  {reportData.snapshot_hash.slice(0, 16)}...
                </span>
              </div>
              <div className="metadata-item">
                <span className="meta-label">Generated:</span>
                <span className="meta-value">
                  <Clock size={12} />
                  {new Date(reportData.generated_at).toLocaleString()}
                </span>
              </div>
              <div className="metadata-item">
                <span className="meta-label">Health Score:</span>
                <span
                  className={`health-badge ${
                    reportData.health_score >= 80
                      ? 'health-excellent'
                      : reportData.health_score >= 60
                        ? 'health-good'
                        : 'health-poor'
                  }`}
                >
                  {Math.round(reportData.health_score)}/100
                </span>
              </div>
            </div>
          </div>

          {/* SECTION 1: Executive Summary */}
          {reportData.executive_summary && (
            <div className="report-section-card">
              <div className="section-card-header">
                <div className="section-header-left">
                  <div className="section-icon-box">
                    <FileText size={18} />
                  </div>
                  <div>
                    <h3>1. Executive Summary & Strategic Narrative</h3>
                    <p>High-level strategic briefing derived from statistical synthesis</p>
                  </div>
                </div>
                <div className="section-header-right">
                  <span
                    className={`mode-badge ${
                      reportData.executive_summary.mode === 'ai_generated'
                        ? 'mode-ai'
                        : 'mode-fallback'
                    }`}
                  >
                    {reportData.executive_summary.mode === 'ai_generated'
                      ? 'AI-Generated Narrative'
                      : 'Statistical Synthesis Engine'}
                  </span>
                </div>
              </div>

              <div className="narrative-box">
                <p>{reportData.executive_summary.narrative}</p>
              </div>

              {reportData.executive_summary.key_takeaways.length > 0 && (
                <div className="takeaways-box">
                  <h4>Top Strategic Takeaways</h4>
                  <ul>
                    {reportData.executive_summary.key_takeaways.map((takeaway, idx) => (
                      <li key={idx}>
                        <CheckCircle2 size={15} className="takeaway-icon" />
                        <span>{takeaway}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* SECTION 2: Key KPIs & Vital Signs */}
          {reportData.key_kpis && (
            <div className="report-section-card">
              <div className="section-card-header">
                <div className="section-header-left">
                  <div className="section-icon-box">
                    <Activity size={18} />
                  </div>
                  <div>
                    <h3>2. Key KPIs & Vital Signs</h3>
                    <p>Core volume counts, data integrity, and dataset completeness</p>
                  </div>
                </div>
              </div>

              <div className="kpi-cards-grid">
                <div className="report-kpi-card">
                  <span className="kpi-label">Total Records (Rows)</span>
                  <span className="kpi-val">
                    {reportData.key_kpis.kpis.total_rows.toLocaleString()}
                  </span>
                  <span className="kpi-foot">Verified Active Snapshot</span>
                </div>

                <div className="report-kpi-card">
                  <span className="kpi-label">Total Attributes (Cols)</span>
                  <span className="kpi-val">{reportData.key_kpis.kpis.total_columns}</span>
                  <span className="kpi-foot">Dimensional schema width</span>
                </div>

                <div className="report-kpi-card">
                  <span className="kpi-label">Data Completeness</span>
                  <span className="kpi-val">
                    {reportData.key_kpis.kpis.data_completeness.toFixed(1)}%
                  </span>
                  <span className="kpi-foot">
                    {reportData.key_kpis.kpis.missing_cells.toLocaleString()} missing cells
                  </span>
                </div>

                <div className="report-kpi-card">
                  <span className="kpi-label">Duplicate Rows</span>
                  <span className="kpi-val">
                    {reportData.key_kpis.kpis.duplicate_rows.toLocaleString()}
                  </span>
                  <span className="kpi-foot">
                    {reportData.key_kpis.kpis.duplicate_percentage.toFixed(1)}% of total
                  </span>
                </div>

                {reportData.key_kpis.kpis.selected_column_stats && (
                  <>
                    <div className="report-kpi-card highlight-kpi">
                      <span className="kpi-label">
                        Avg {reportData.key_kpis.kpis.selected_column}
                      </span>
                      <span className="kpi-val">
                        {reportData.key_kpis.kpis.selected_column_stats.average !== null
                          ? reportData.key_kpis.kpis.selected_column_stats.average.toLocaleString(
                              undefined,
                              { maximumFractionDigits: 2 }
                            )
                          : 'N/A'}
                      </span>
                      <span className="kpi-foot">Numerical mean baseline</span>
                    </div>

                    <div className="report-kpi-card highlight-kpi">
                      <span className="kpi-label">
                        Total {reportData.key_kpis.kpis.selected_column}
                      </span>
                      <span className="kpi-val">
                        {reportData.key_kpis.kpis.selected_column_stats.sum.toLocaleString(
                          undefined,
                          { maximumFractionDigits: 0 }
                        )}
                      </span>
                      <span className="kpi-foot">Aggregate sum total</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* SECTION 3: Key Findings */}
          {reportData.key_findings && (
            <div className="report-section-card">
              <div className="section-card-header">
                <div className="section-header-left">
                  <div className="section-icon-box">
                    <Sparkles size={18} />
                  </div>
                  <div>
                    <h3>3. Key Automated Findings</h3>
                    <p>Statistically validated insights ranked by business significance</p>
                  </div>
                </div>
                <span className="badge-count">
                  {reportData.key_findings.findings.length} Findings
                </span>
              </div>

              {reportData.key_findings.findings.length === 0 ? (
                <p className="empty-section-note">
                  No automated statistical findings were identified above significance thresholds.
                </p>
              ) : (
                <div className="findings-list">
                  {reportData.key_findings.findings.map((f) => (
                    <div key={f.finding_id} className="finding-item-card">
                      <div className="finding-top-row">
                        <div className="finding-title-group">
                          <span
                            className={`importance-tag tag-${f.importance || 'medium'}`}
                          >
                            {(f.importance || 'notable').toUpperCase()}
                          </span>
                          <span className="finding-category-tag">{f.category}</span>
                          <h4 className="finding-title">{f.title}</h4>
                        </div>
                        {f.referenced_fact_ids && f.referenced_fact_ids.length > 0 && (
                          <span
                            className="fact-grounded-pill"
                            title={`Referenced empirical facts: ${f.referenced_fact_ids.join(', ')}`}
                          >
                            <ShieldCheck size={12} />
                            Verified Fact Grounded
                          </span>
                        )}
                      </div>
                      <p className="finding-desc">{f.description}</p>
                      {f.columns_involved && f.columns_involved.length > 0 && (
                        <div className="columns-involved-row">
                          <span className="meta-sub">Columns:</span>
                          {f.columns_involved.map((c) => (
                            <code key={c} className="column-chip">
                              {c}
                            </code>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* SECTION 4: Category Benchmarks */}
          {reportData.category_benchmarks && (
            <div className="report-section-card">
              <div className="section-card-header">
                <div className="section-header-left">
                  <div className="section-icon-box">
                    <Award size={18} />
                  </div>
                  <div>
                    <h3>4. Category Benchmarks & Performance Deltas</h3>
                    <p>Best and worst category performers across key categorical dimensions</p>
                  </div>
                </div>
                <span className="badge-count">
                  {reportData.category_benchmarks.benchmarks.length} Dimensions
                </span>
              </div>

              {reportData.category_benchmarks.benchmarks.length === 0 ? (
                <p className="empty-section-note">
                  No categorical benchmark relationships were discovered with sufficient sample
                  size.
                </p>
              ) : (
                <div className="benchmarks-list">
                  {reportData.category_benchmarks.benchmarks.map((bm, idx) => (
                    <div key={idx} className="benchmark-card">
                      <div className="benchmark-card-header">
                        <div>
                          <h4>
                            Dimension: <code>{bm.dimension_column}</code>
                            {bm.metric_column && (
                              <span>
                                {' '}
                                • Metric: <code>{bm.metric_column}</code>
                              </span>
                            )}
                          </h4>
                          <p className="benchmark-explanation">{bm.explanation}</p>
                        </div>
                        <div className="benchmark-avg-pill">
                          <span className="avg-label">Dataset Avg:</span>
                          <span className="avg-val">{bm.formatted_average}</span>
                        </div>
                      </div>

                      <div className="performer-comparison-row">
                        <div className="performer-box best-box">
                          <div className="performer-title">
                            <TrendingUp size={15} /> Top Performer
                          </div>
                          <div className="performer-name">{bm.best_performer.category_name}</div>
                          <div className="performer-stats">
                            <span className="performer-val">
                              {bm.best_performer.formatted_value}
                            </span>
                            <span className="delta-pill delta-positive">
                              +{bm.best_performer.delta_vs_average_pct.toFixed(1)}% vs avg
                            </span>
                          </div>
                          <div className="performer-sample">
                            N = {bm.best_performer.sample_size.toLocaleString()} samples
                          </div>
                        </div>

                        <div className="performer-box worst-box">
                          <div className="performer-title">
                            <TrendingDown size={15} /> Lowest Performer
                          </div>
                          <div className="performer-name">{bm.worst_performer.category_name}</div>
                          <div className="performer-stats">
                            <span className="performer-val">
                              {bm.worst_performer.formatted_value}
                            </span>
                            <span className="delta-pill delta-negative">
                              {bm.worst_performer.delta_vs_average_pct.toFixed(1)}% vs avg
                            </span>
                          </div>
                          <div className="performer-sample">
                            N = {bm.worst_performer.sample_size.toLocaleString()} samples
                          </div>
                        </div>
                      </div>

                      {/* Embedded Chart if available */}
                      {reportData.config.include_charts && bm.chart && (
                        <div className="report-embedded-chart">
                          <InteractiveChart chart={bm.chart} height={280} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* SECTION 5: Trends & Seasonality */}
          {reportData.trends_and_seasonality && (
            <div className="report-section-card">
              <div className="section-card-header">
                <div className="section-header-left">
                  <div className="section-icon-box">
                    <TrendingUp size={18} />
                  </div>
                  <div>
                    <h3>5. Longitudinal Trends & Seasonality</h3>
                    <p>Time-series trajectory, statistical significance, and cyclical patterns</p>
                  </div>
                </div>
                {reportData.trends_and_seasonality.has_temporal_data && (
                  <span className="badge-count">
                    {reportData.trends_and_seasonality.trends.length} Series
                  </span>
                )}
              </div>

              {!reportData.trends_and_seasonality.has_temporal_data ? (
                <div className="non-temporal-card">
                  <Info size={28} className="text-muted-icon" />
                  <h4>No Datetime Columns Detected</h4>
                  <p>
                    This dataset does not contain recognizable date or timestamp columns.
                    Longitudinal trend regressions and seasonality decompositions were skipped
                    gracefully.
                  </p>
                </div>
              ) : (
                <div className="trends-container">
                  {reportData.trends_and_seasonality.trends.map((tr) => (
                    <div key={tr.trend_id} className="trend-report-card">
                      <div className="trend-report-header">
                        <div>
                          <h4>
                            Trend: <code>{tr.metric_column}</code> over <code>{tr.date_column}</code>
                          </h4>
                          <div className="trend-badges-row">
                            <span className={`direction-pill dir-${tr.direction}`}>
                              {tr.direction.toUpperCase()}
                            </span>
                            <span
                              className={`stat-pill evidence-${tr.statistical_evidence}`}
                            >
                              {tr.statistical_evidence.replace(/_/g, ' ')}
                            </span>
                            <span className="mag-pill">
                              Magnitude: {tr.business_magnitude}
                            </span>
                          </div>
                        </div>
                        <div className="trend-shift-box">
                          <span className="shift-label">Net Endpoint Change</span>
                          <span
                            className={`shift-val ${
                              tr.absolute_change >= 0 ? 'text-emerald' : 'text-rose'
                            }`}
                          >
                            {tr.formatted_absolute_change}
                          </span>
                          {tr.conventional_growth_pct !== null &&
                            tr.conventional_growth_pct !== undefined && (
                              <span className="growth-sub">
                                ({tr.conventional_growth_pct >= 0 ? '+' : ''}
                                {tr.conventional_growth_pct.toFixed(1)}% growth)
                              </span>
                            )}
                        </div>
                      </div>

                      <p className="trend-desc">{tr.explanation}</p>

                      <div className="trend-stats-grid">
                        <div className="trend-stat">
                          <span className="stat-lbl">Baseline Start</span>
                          <span className="stat-num">{tr.starting_baseline.toFixed(2)}</span>
                        </div>
                        <div className="trend-stat">
                          <span className="stat-lbl">Baseline End</span>
                          <span className="stat-num">{tr.ending_baseline.toFixed(2)}</span>
                        </div>
                        <div className="trend-stat">
                          <span className="stat-lbl">Peak Period</span>
                          <span className="stat-num">
                            {tr.peak_period} ({tr.peak_value.toFixed(1)})
                          </span>
                        </div>
                        <div className="trend-stat">
                          <span className="stat-lbl">Trough Period</span>
                          <span className="stat-num">
                            {tr.trough_period} ({tr.trough_value.toFixed(1)})
                          </span>
                        </div>
                        <div className="trend-stat">
                          <span className="stat-lbl">R² Goodness-of-Fit</span>
                          <span className="stat-num">{tr.trend_strength_r2.toFixed(3)}</span>
                        </div>
                        <div className="trend-stat">
                          <span className="stat-lbl">
                            {tr.p_value_fdr_adjusted !== null &&
                            tr.p_value_fdr_adjusted !== undefined
                              ? 'FDR-Adjusted p'
                              : 'OLS p-value'}
                          </span>
                          <span className="stat-num">
                            {tr.p_value_fdr_adjusted !== null &&
                            tr.p_value_fdr_adjusted !== undefined
                              ? tr.p_value_fdr_adjusted.toFixed(4)
                              : tr.p_value !== null && tr.p_value !== undefined
                                ? tr.p_value.toFixed(4)
                                : 'N/A'}
                          </span>
                        </div>
                      </div>

                      {/* Embedded Trend Chart */}
                      {reportData.config.include_charts && tr.chart && (
                        <div className="report-embedded-chart">
                          <InteractiveChart chart={tr.chart} height={280} />
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Seasonality Card */}
                  {reportData.trends_and_seasonality.seasonality && (
                    <div className="seasonality-report-card">
                      <h4>
                        Seasonality Pattern:{' '}
                        <code>
                          {reportData.trends_and_seasonality.seasonality.cycle_type
                            ? reportData.trends_and_seasonality.seasonality.cycle_type.replace(/_/g, ' ')
                            : 'Periodic'}{' '}
                          Cycle
                        </code>
                      </h4>
                      <p>{reportData.trends_and_seasonality.seasonality.explanation}</p>
                      <div className="seasonality-chips-row">
                        {reportData.trends_and_seasonality.seasonality.peak_season && (
                          <span className="season-badge peak-badge">
                            Peak Season: {reportData.trends_and_seasonality.seasonality.peak_season}
                          </span>
                        )}
                        {reportData.trends_and_seasonality.seasonality.trough_season && (
                          <span className="season-badge trough-badge">
                            Trough Season:{' '}
                            {reportData.trends_and_seasonality.seasonality.trough_season}
                          </span>
                        )}
                        <span className="season-badge ratio-badge">
                          Status:{' '}
                          {reportData.trends_and_seasonality.seasonality.status.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* SECTION 6: Anomalies & Risk Signals */}
          {reportData.anomalies_and_risks && (
            <div className="report-section-card">
              <div className="section-card-header">
                <div className="section-header-left">
                  <div className="section-icon-box">
                    <AlertTriangle size={18} />
                  </div>
                  <div>
                    <h3>6. Anomalies & Operational Risks</h3>
                    <p>Categorical distributions, statistical outliers, and temporal spikes/drops</p>
                  </div>
                </div>
                <span className="badge-count">
                  {reportData.anomalies_and_risks.total_anomaly_count} Signals
                </span>
              </div>

              {reportData.anomalies_and_risks.total_anomaly_count === 0 ? (
                <p className="empty-section-note">
                  Zero critical anomalies or statistical disruptions were detected in the dataset.
                </p>
              ) : (
                <div className="anomalies-list">
                  {reportData.anomalies_and_risks.anomalies.map((an) => (
                    <div key={an.anomaly_id} className="anomaly-item-card">
                      <div className="anomaly-header-row">
                        <div className="anomaly-type-group">
                          <span
                            className={`severity-badge sev-${an.severity || 'warning'}`}
                          >
                            {(an.severity || 'warning').toUpperCase()}
                          </span>
                          <span className="anomaly-name">{an.anomaly_type.replace(/_/g, ' ')}</span>
                          <code className="column-chip">{an.column_name}</code>
                        </div>
                      </div>
                      <p className="anomaly-desc">{an.description}</p>
                    </div>
                  ))}

                  {reportData.anomalies_and_risks.temporal_anomalies.map((tan) => (
                    <div key={tan.anomaly_id} className="anomaly-item-card temporal-anomaly-card">
                      <div className="anomaly-header-row">
                        <div className="anomaly-type-group">
                          <span
                            className={`severity-badge sev-${tan.severity || 'warning'}`}
                          >
                            {(tan.severity || 'warning').toUpperCase()}
                          </span>
                          <span className="anomaly-name">
                            {tan.anomaly_type.replace(/_/g, ' ')}
                          </span>
                          <span className="period-chip">{tan.period_label}</span>
                        </div>
                      </div>
                      <p className="anomaly-desc">
                        Temporal disturbance observed during period {tan.period_label}.
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* SECTION 7: Actionable Recommendations */}
          {reportData.recommendations && (
            <div className="report-section-card">
              <div className="section-card-header">
                <div className="section-header-left">
                  <div className="section-icon-box">
                    <CheckSquare size={18} />
                  </div>
                  <div>
                    <h3>7. Actionable Business Recommendations</h3>
                    <p>Strategic actions classified by priority and verified fact grounding</p>
                  </div>
                </div>
                <span className="badge-count">
                  {reportData.recommendations.recommendations.length} Items
                </span>
              </div>

              {reportData.recommendations.recommendations.length === 0 ? (
                <p className="empty-section-note">
                  No automated business recommendations generated for this snapshot.
                </p>
              ) : (
                <div className="recommendations-list">
                  {reportData.recommendations.recommendations.map((rec) => (
                    <div key={rec.recommendation_id} className="recommendation-card">
                      <div className="rec-top-row">
                        <div className="rec-badge-group">
                          <span className={`priority-tag pri-${rec.priority}`}>
                            {rec.priority.toUpperCase()} PRIORITY
                          </span>
                          <span className="rec-cat-pill">{rec.category}</span>
                        </div>

                        {/* Distinction between Empirical Fact vs Analytical Hypothesis */}
                        {rec.is_hypothesis ? (
                          <span className="rec-nature-tag nature-hypothesis">
                            <Sparkles size={12} />
                            Analytical Hypothesis
                          </span>
                        ) : (
                          <span className="rec-nature-tag nature-fact">
                            <ShieldCheck size={12} />
                            Verified Fact Grounded
                          </span>
                        )}
                      </div>

                      <h4 className="rec-title">{rec.title}</h4>
                      <p className="rec-action">
                        <strong>Action:</strong> {rec.action_statement}
                      </p>
                      <p className="rec-impact">
                        <strong>Expected Impact:</strong> {rec.expected_impact}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* SECTION 8: Data Quality Audit */}
          {reportData.data_quality_audit && (
            <div className="report-section-card">
              <div className="section-card-header">
                <div className="section-header-left">
                  <div className="section-icon-box">
                    <ShieldCheck size={18} />
                  </div>
                  <div>
                    <h3>8. Data Quality & Integrity Audit</h3>
                    <p>Profile metrics, completeness, uniqueness, and column health scores</p>
                  </div>
                </div>
                <span className="grade-badge">
                  Grade: {reportData.data_quality_audit.quality_grade}
                </span>
              </div>

              <div className="quality-scores-grid">
                <div className="quality-score-tile">
                  <span className="tile-title">Overall Quality</span>
                  <span className="tile-val">
                    {reportData.data_quality_audit.overall_quality_score.toFixed(1)}%
                  </span>
                  <div className="progress-bar-bg">
                    <div
                      className="progress-bar-fill fill-quality"
                      style={{
                        width: `${Math.min(
                          100,
                          reportData.data_quality_audit.overall_quality_score
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="quality-score-tile">
                  <span className="tile-title">Completeness</span>
                  <span className="tile-val">
                    {reportData.data_quality_audit.completeness_score.toFixed(1)}%
                  </span>
                  <div className="progress-bar-bg">
                    <div
                      className="progress-bar-fill fill-complete"
                      style={{
                        width: `${Math.min(
                          100,
                          reportData.data_quality_audit.completeness_score
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="quality-score-tile">
                  <span className="tile-title">Uniqueness</span>
                  <span className="tile-val">
                    {reportData.data_quality_audit.uniqueness_score.toFixed(1)}%
                  </span>
                  <div className="progress-bar-bg">
                    <div
                      className="progress-bar-fill fill-unique"
                      style={{
                        width: `${Math.min(
                          100,
                          reportData.data_quality_audit.uniqueness_score
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="quality-score-tile">
                  <span className="tile-title">Validity</span>
                  <span className="tile-val">
                    {reportData.data_quality_audit.validity_score.toFixed(1)}%
                  </span>
                  <div className="progress-bar-bg">
                    <div
                      className="progress-bar-fill fill-valid"
                      style={{
                        width: `${Math.min(
                          100,
                          reportData.data_quality_audit.validity_score
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Column Health Summary Table */}
              {reportData.columns && reportData.columns.length > 0 && (
                <div className="column-health-table-wrapper">
                  <h4>Column Health & Profile Summary</h4>
                  <table className="column-health-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Column Name</th>
                        <th>Data Type</th>
                        <th>Non-Null</th>
                        <th>Missing %</th>
                        <th>Unique Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reportData.columns.map((c) => (
                        <tr key={c.name}>
                          <td>{c.position}</td>
                          <td className="col-name-cell">
                            <code>{c.name}</code>
                          </td>
                          <td>
                            <span className="dtype-pill">{c.data_type}</span>
                          </td>
                          <td>{c.non_null_count.toLocaleString()}</td>
                          <td>
                            <span
                              className={c.null_percentage > 0 ? 'text-rose' : 'text-muted'}
                            >
                              {c.null_percentage.toFixed(1)}%
                            </span>
                          </td>
                          <td>{c.unique_count.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Analytical Limitations & Scope Disclaimers */}
          <div className="report-limitations-footer">
            <h4>Analytical Limitations & Scope Notes</h4>
            <ul>
              {reportData.limitations.map((lim, idx) => (
                <li key={idx}>• {lim}</li>
              ))}
              {reportData.date_scoping_limitations.map((dlim, idx) => (
                <li key={`date-${idx}`}>• {dlim}</li>
              ))}
            </ul>
            <div className="report-final-disclaimer">
              {reportData.brand_name} • {reportData.brand_attribution} • {reportData.brand_tagline}
            </div>
          </div>
        </div>
      ) : (
        <div className="report-empty-prompt-state">
          <FileText size={48} className="text-muted-icon" />
          <h3>No Report Preview Generated</h3>
          <p>Click "Update Preview" to assemble executive findings from the active dataset.</p>
          <button
            type="button"
            className="button button-primary"
            onClick={handleGenerateReport}
            disabled={isLoading}
          >
            Generate Executive Report Preview
          </button>
        </div>
      )}
    </div>
  )
}
