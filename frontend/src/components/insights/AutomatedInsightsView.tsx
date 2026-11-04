import React, { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  Award,
  Calendar,
  CheckCircle2,
  Clock,
  Database,
  Flame,
  Info,
  Layers,
  Lightbulb,
  Percent,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
} from 'lucide-react'
import { getAutomatedInsights, refreshAutomatedInsights } from '../../services/api'
import type {
  AutomatedInsightsResponse,
  DateGranularity,
  GroundedFact,
  StatisticalEvidence,
  TrendDirection,
} from '../../types/insights'
import { InteractiveChart } from '../dashboard/InteractiveChart'

interface AutomatedInsightsViewProps {
  datasetId: string
  datasetFilename: string
}

type FilterSection = 'all' | 'trends' | 'findings' | 'benchmarks' | 'anomalies' | 'recommendations'

export const AutomatedInsightsView: React.FC<AutomatedInsightsViewProps> = ({
  datasetId,
  datasetFilename,
}) => {
  const [insights, setInsights] = useState<AutomatedInsightsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<FilterSection>('all')
  const [selectedFact, setSelectedFact] = useState<GroundedFact | null>(null)
  const [selectedCombinationId, setSelectedCombinationId] = useState<string>('')
  const [selectedGranularity, setSelectedGranularity] = useState<DateGranularity>('month')

  const fetchInsights = useCallback(
    async (forceRefresh = false, dateCol?: string, metricCol?: string, gran?: string) => {
      if (forceRefresh) {
        setIsRefreshing(true)
      } else if (!dateCol && !metricCol) {
        setIsLoading(true)
      }
      setError(null)

      try {
        const params =
          dateCol && metricCol
            ? { date_col: dateCol, metric_col: metricCol, granularity: gran }
            : undefined
        const data = forceRefresh
          ? await refreshAutomatedInsights(datasetId, params)
          : await getAutomatedInsights(datasetId, params)
        setInsights(data)
        if (data.available_combinations && data.available_combinations.length > 0) {
          const defaultComb =
            data.available_combinations.find((c) => c.is_default) ||
            data.available_combinations[0]
          if (!dateCol) {
            setSelectedCombinationId(defaultComb.combination_id)
            setSelectedGranularity(defaultComb.granularity)
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load automated insights')
      } finally {
        setIsLoading(false)
        setIsRefreshing(false)
      }
    },
    [datasetId]
  )

  useEffect(() => {
    fetchInsights(false)
  }, [fetchInsights])

  const handleSelectCombination = (combId: string) => {
    setSelectedCombinationId(combId)
    const comb = insights?.available_combinations.find((c) => c.combination_id === combId)
    if (comb) {
      fetchInsights(false, comb.date_column, comb.metric_column, selectedGranularity)
    }
  }

  const handleSelectGranularity = (gran: DateGranularity) => {
    setSelectedGranularity(gran)
    const comb = insights?.available_combinations.find(
      (c) => c.combination_id === selectedCombinationId
    )
    if (comb) {
      fetchInsights(false, comb.date_column, comb.metric_column, gran)
    }
  }

  const findFactById = (factId: string): GroundedFact | undefined => {
    return insights?.grounded_facts.find((f) => f.fact_id === factId)
  }

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10'
    if (score >= 60) return 'text-amber-400 border-amber-500/40 bg-amber-500/10'
    return 'text-rose-400 border-rose-500/40 bg-rose-500/10'
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return <span className="badge badge-critical">Critical</span>
      case 'warning':
        return <span className="badge badge-warning">Warning</span>
      default:
        return <span className="badge badge-info">Info</span>
    }
  }

  const getPriorityBadge = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return <span className="badge badge-critical">High Priority</span>
      case 'medium':
        return <span className="badge badge-warning">Medium Priority</span>
      default:
        return <span className="badge badge-info">Low Priority</span>
    }
  }

  const getTrendDirectionBadge = (direction: TrendDirection) => {
    switch (direction) {
      case 'increasing':
        return (
          <span className="direction-badge increasing">
            <TrendingUp size={15} /> Upward Trend
          </span>
        )
      case 'decreasing':
        return (
          <span className="direction-badge decreasing">
            <TrendingDown size={15} /> Downward Trend
          </span>
        )
      case 'stable':
        return (
          <span className="direction-badge stable">
            <Activity size={15} /> Stable Series
          </span>
        )
      default:
        return (
          <span className="direction-badge fluctuating">
            <Activity size={15} /> Fluctuating Series
          </span>
        )
    }
  }

  const getStatisticalEvidenceBadge = (evidence: StatisticalEvidence) => {
    switch (evidence) {
      case 'statistically_supported':
        return (
          <span className="evidence-badge statistically_supported">
            <CheckCircle2 size={13} /> Statistically Supported (p ≤ 0.05)
          </span>
        )
      case 'exploratory_pattern':
        return (
          <span className="evidence-badge exploratory_pattern">
            <AlertCircle size={13} /> Exploratory Pattern
          </span>
        )
      default:
        return (
          <span className="evidence-badge insufficient_sample">
            <Info size={13} /> Insufficient Sample (T &lt; 6)
          </span>
        )
    }
  }

  if (isLoading) {
    return (
      <div className="insights-loading-container">
        <div className="spinner-large" />
        <h3 className="loading-heading">Discovering Automated Insights...</h3>
        <p className="loading-subtext">
          Scanning distributions, analyzing temporal trends, computing benchmarks, and detecting statistical anomalies.
        </p>
      </div>
    )
  }

  if (error || !insights) {
    return (
      <div className="insights-error-card">
        <AlertCircle size={32} className="text-rose-400" />
        <h3>Unable to Generate Automated Insights</h3>
        <p>{error || 'An unexpected error occurred.'}</p>
        <button
          type="button"
          className="button button-primary"
          onClick={() => fetchInsights(false)}
        >
          <RefreshCw size={14} /> Try Again
        </button>
      </div>
    )
  }

  const primaryTrend = insights.trends && insights.trends.length > 0 ? insights.trends[0] : null

  return (
    <div className="automated-insights-wrapper">
      {/* HEADER SECTION */}
      <div className="insights-header-card">
        <div className="insights-header-left">
          <div className="brand-pill">
            <Sparkles size={14} className="text-purple-400" />
            <span>Powered by Saniya</span>
            <span className="dot-divider">•</span>
            <span>Your Autonomous Data Analyst</span>
          </div>
          <h2 className="insights-title">Automated Insights & Business Intelligence</h2>
          <p className="insights-subtitle">
            Autonomous discovery across <strong className="text-white">{datasetFilename}</strong>. Every
            finding is statistically validated and fact-grounded in Pandas.
          </p>

          <div className="insights-meta-badges">
            <span className="meta-chip">
              <Database size={12} /> Snapshot: {insights.snapshot_hash.slice(0, 8)}
            </span>
            <span className="meta-chip">
              {insights.is_cached ? (
                <>
                  <CheckCircle2 size={12} className="text-emerald-400" /> Instant Snapshot Cache
                </>
              ) : (
                <>
                  <Activity size={12} className="text-purple-400" /> Live Analysis
                </>
              )}
            </span>
            <span className="meta-chip">
              {insights.mode === 'ai_generated' ? 'Gemini 3.8 Flash' : 'Deterministic Fallback'}
            </span>
          </div>
        </div>

        <div className="insights-header-right">
          {/* HEALTH SCORE GAUGE */}
          <div className={`health-score-gauge ${getHealthScoreColor(insights.health_score)}`}>
            <div className="score-val">{insights.health_score.toFixed(0)}</div>
            <div className="score-label">DATA HEALTH</div>
          </div>

          <button
            type="button"
            className="button button-secondary refresh-btn"
            disabled={isRefreshing}
            onClick={() => fetchInsights(true)}
            title="Recalculate insights and bypass cache"
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Insights'}</span>
          </button>
        </div>
      </div>

      {/* EXECUTIVE SUMMARY BRIEFING */}
      {insights.executive_summary && (
        <div className="executive-summary-card">
          <div className="executive-summary-header">
            <Sparkles size={18} className="text-purple-400" />
            <h3>Executive Briefing</h3>
          </div>
          <p className="executive-summary-text">{insights.executive_summary}</p>
        </div>
      )}

      {/* CAVEATS & LIMITATIONS BANNER */}
      {insights.limitations && insights.limitations.length > 0 && (
        <div className="limitations-banner">
          <Info size={16} className="text-cyan-400 flex-shrink-0" />
          <div className="limitations-list">
            {insights.limitations.map((lim, idx) => (
              <span key={idx} className="limitation-item">
                {lim}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* FILTER PILLS */}
      <div className="insights-filter-bar">
        <button
          type="button"
          className={`filter-pill ${activeFilter === 'all' ? 'active' : ''}`}
          onClick={() => setActiveFilter('all')}
        >
          All Insights
        </button>
        <button
          type="button"
          className={`filter-pill ${activeFilter === 'trends' ? 'active' : ''}`}
          onClick={() => setActiveFilter('trends')}
        >
          Trends & Seasonality ({insights.trends.length})
        </button>
        <button
          type="button"
          className={`filter-pill ${activeFilter === 'findings' ? 'active' : ''}`}
          onClick={() => setActiveFilter('findings')}
        >
          Key Findings ({insights.key_findings.length})
        </button>
        <button
          type="button"
          className={`filter-pill ${activeFilter === 'benchmarks' ? 'active' : ''}`}
          onClick={() => setActiveFilter('benchmarks')}
        >
          Category Benchmarks ({insights.best_worst_analyses.length})
        </button>
        <button
          type="button"
          className={`filter-pill ${activeFilter === 'anomalies' ? 'active' : ''}`}
          onClick={() => setActiveFilter('anomalies')}
        >
          Anomalies & Patterns ({insights.anomalies_and_patterns.length})
        </button>
        <button
          type="button"
          className={`filter-pill ${activeFilter === 'recommendations' ? 'active' : ''}`}
          onClick={() => setActiveFilter('recommendations')}
        >
          Recommendations ({insights.recommendations.length})
        </button>
      </div>

      {/* ===================================================================== */}
      {/* SECTION 1: TEMPORAL TRENDS, ANOMALIES & SEASONALITY (PHASE 4.4)        */}
      {/* ===================================================================== */}
      {(activeFilter === 'all' || activeFilter === 'trends') && (
        <div className="insights-section">
          <div className="section-title-row">
            <Clock size={18} className="text-purple-400" />
            <h3>Temporal Trends & Anomaly Intelligence</h3>
            <span className="section-count">
              {insights.has_temporal_data ? `${insights.trends.length} active time series` : 'No dates'}
            </span>
          </div>

          {!insights.has_temporal_data ? (
            <div className="non-temporal-card">
              <Calendar size={32} className="text-muted" />
              <h4>No Temporal Columns Detected</h4>
              <p>
                This dataset does not contain calendar timestamps or date fields (e.g., date, timestamp, year).
                Temporal trend regression, sudden change detection, and recurring seasonality require time-series dimensions.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-5">
              {/* COMBINATION SELECTOR TOOLBAR */}
              {insights.available_combinations && insights.available_combinations.length > 0 && (
                <div className="combination-selector-bar">
                  <div className="selector-group">
                    <span className="selector-label">
                      <Layers size={14} className="text-purple-400" /> Time Series Pair:
                    </span>
                    <select
                      className="selector-dropdown"
                      value={selectedCombinationId}
                      onChange={(e) => handleSelectCombination(e.target.value)}
                    >
                      {insights.available_combinations.map((comb) => (
                        <option key={comb.combination_id} value={comb.combination_id}>
                          {comb.display_label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="selector-group">
                    <span className="selector-label">Granularity:</span>
                    <div className="granularity-pills-group">
                      {(['year', 'quarter', 'month', 'week', 'day'] as DateGranularity[]).map((gran) => (
                        <button
                          key={gran}
                          type="button"
                          className={`gran-pill ${selectedGranularity === gran ? 'active' : ''}`}
                          onClick={() => handleSelectGranularity(gran)}
                        >
                          {gran.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* PRIMARY TREND HERO CARD */}
              {primaryTrend && (
                <div className="trend-hero-card">
                  <div className="trend-hero-top">
                    <div className="trend-hero-title-group">
                      <h4>
                        Temporal Trend: <strong className="text-white">{primaryTrend.metric_column}</strong> over{' '}
                        <span className="text-purple-400">{primaryTrend.date_column}</span>
                      </h4>
                      <span className="trend-hero-sub">
                        <Clock size={13} /> {primaryTrend.granularity.toUpperCase()} resolution (
                        {primaryTrend.data_points.length} periods evaluated)
                      </span>
                    </div>

                    <div className="trend-badges-row">
                      {getTrendDirectionBadge(primaryTrend.direction)}
                      {getStatisticalEvidenceBadge(primaryTrend.statistical_evidence)}
                      <span className="magnitude-badge">{primaryTrend.business_magnitude} magnitude</span>
                      {typeof primaryTrend.p_value_fdr_adjusted === 'number' && (
                        <span className="meta-chip" title="Benjamini-Hochberg False Discovery Rate Adjusted p-value">
                          FDR p={primaryTrend.p_value_fdr_adjusted.toFixed(4)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 4-COLUMN METRICS GRID */}
                  <div className="trend-metrics-grid">
                    <div className="trend-metric-box">
                      <span className="metric-box-label">
                        {typeof primaryTrend.conventional_growth_pct === 'number'
                          ? 'Net Growth'
                          : 'Range Shift'}
                      </span>
                      <div
                        className={`metric-box-val ${
                          (primaryTrend.conventional_growth_pct ?? primaryTrend.range_normalized_shift_pct ?? 0) >= 0
                            ? 'text-emerald-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {typeof primaryTrend.conventional_growth_pct === 'number' ? (
                          <>
                            {primaryTrend.conventional_growth_pct >= 0 ? '+' : ''}
                            {primaryTrend.conventional_growth_pct.toFixed(1)}%
                          </>
                        ) : typeof primaryTrend.range_normalized_shift_pct === 'number' ? (
                          <>
                            {primaryTrend.range_normalized_shift_pct >= 0 ? '+' : ''}
                            {primaryTrend.range_normalized_shift_pct.toFixed(1)}%
                          </>
                        ) : (
                          '0.0%'
                        )}
                      </div>
                      <span className="metric-box-sub">
                        {typeof primaryTrend.conventional_growth_pct === 'number'
                          ? 'Conventional growth'
                          : 'Range-normalized shift (baseline ≤ 0)'}
                      </span>
                    </div>

                    <div className="trend-metric-box">
                      <span className="metric-box-label">Absolute Change</span>
                      <div className="metric-box-val">{primaryTrend.formatted_absolute_change}</div>
                      <span className="metric-box-sub">
                        Start: {primaryTrend.starting_baseline.toLocaleString()} → End:{' '}
                        {primaryTrend.ending_baseline.toLocaleString()}
                      </span>
                    </div>

                    <div className="trend-metric-box">
                      <span className="metric-box-label">Historical Peak</span>
                      <div className="metric-box-val text-emerald-400">
                        {primaryTrend.peak_value.toLocaleString()}
                      </div>
                      <span className="metric-box-sub">Recorded in {primaryTrend.peak_period}</span>
                    </div>

                    <div className="trend-metric-box">
                      <span className="metric-box-label">Historical Trough</span>
                      <div className="metric-box-val text-rose-400">
                        {primaryTrend.trough_value.toLocaleString()}
                      </div>
                      <span className="metric-box-sub">Recorded in {primaryTrend.trough_period}</span>
                    </div>
                  </div>

                  <p className="trend-explanation-text">{primaryTrend.explanation}</p>

                  {/* TREND CHART */}
                  {primaryTrend.chart && (
                    <div className="benchmark-chart-container">
                      <InteractiveChart chart={primaryTrend.chart} height={340} />
                    </div>
                  )}

                  {primaryTrend.referenced_fact_ids.length > 0 && (
                    <div className="fact-chips-group">
                      <span className="text-xs text-muted">Supporting Facts:</span>
                      {primaryTrend.referenced_fact_ids.map((fid) => (
                        <button
                          key={fid}
                          type="button"
                          className="fact-chip-btn"
                          onClick={() => {
                            const fact = findFactById(fid)
                            if (fact) setSelectedFact(fact)
                          }}
                        >
                          #{fid}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TEMPORAL ANOMALIES TABLE */}
              {insights.temporal_anomalies && insights.temporal_anomalies.length > 0 && (
                <div className="temporal-anomalies-card">
                  <div className="section-title-row">
                    <ShieldAlert size={16} className="text-rose-400" />
                    <h4>Abrupt Chronological Changes & Drops ({insights.temporal_anomalies.length})</h4>
                  </div>

                  <div className="temporal-table-wrapper">
                    <table className="temporal-table">
                      <thead>
                        <tr>
                          <th>Period</th>
                          <th>Anomaly Type</th>
                          <th>Severity</th>
                          <th>Observed Value</th>
                          <th>Baseline Reference</th>
                          <th>Absolute Diff</th>
                          <th>Robust Z-Score</th>
                          <th>Detection Method</th>
                        </tr>
                      </thead>
                      <tbody>
                        {insights.temporal_anomalies.map((a, idx) => (
                          <tr key={idx}>
                            <td className="font-semibold text-white">{a.period_label}</td>
                            <td>
                              <span className="flex items-center gap-1">
                                {a.anomaly_type === 'sudden_drop' ? (
                                  <ArrowDownRight size={14} className="text-rose-400" />
                                ) : (
                                  <ArrowUpRight size={14} className="text-amber-400" />
                                )}
                                {a.anomaly_type.replace(/_/g, ' ').toUpperCase()}
                              </span>
                            </td>
                            <td>{getSeverityBadge(a.severity)}</td>
                            <td>{a.formatted_observed_value}</td>
                            <td>{a.formatted_baseline_reference}</td>
                            <td className="font-mono text-rose-400">{a.absolute_diff.toFixed(2)}</td>
                            <td className="font-mono font-semibold">{a.robust_z_score.toFixed(2)}</td>
                            <td className="text-xs text-muted">{a.detection_method}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* RECURRING SEASONALITY & CYCLICAL PATTERNS */}
              {insights.seasonality && (
                <div className="seasonality-card">
                  <div className="seasonality-header-row">
                    <div className="seasonality-title-group">
                      <h4>
                        Recurring Seasonality Analysis:{' '}
                        <span className="text-purple-400">
                          {insights.seasonality.cycle_type === 'day_of_week'
                            ? 'Day-of-Week Cycle'
                            : 'Monthly Cycle'}
                        </span>
                      </h4>
                      <div className="season-chips-row mt-2">
                        {insights.seasonality.peak_season && (
                          <span className="season-chip peak">
                            <TrendingUp size={13} /> Peak: {insights.seasonality.peak_season}
                          </span>
                        )}
                        {insights.seasonality.trough_season && (
                          <span className="season-chip trough">
                            <TrendingDown size={13} /> Trough: {insights.seasonality.trough_season}
                          </span>
                        )}
                        {typeof insights.seasonality.anova_f_stat === 'number' && (
                          <span className="meta-chip">
                            ANOVA F={insights.seasonality.anova_f_stat.toFixed(2)} (p=
                            {insights.seasonality.anova_p_value?.toFixed(4)})
                          </span>
                        )}
                      </div>
                    </div>

                    <span
                      className={`status-pill ${
                        insights.seasonality.status === 'statistically_supported'
                          ? 'pill-green'
                          : 'pill-amber'
                      }`}
                    >
                      {insights.seasonality.status.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  </div>

                  <p className="trend-explanation-text">{insights.seasonality.explanation}</p>

                  {insights.seasonality.chart && (
                    <div className="benchmark-chart-container">
                      <InteractiveChart chart={insights.seasonality.chart} height={300} />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* SECTION 2: KEY FINDINGS */}
      {(activeFilter === 'all' || activeFilter === 'findings') && (
        <div className="insights-section">
          <div className="section-title-row">
            <Flame size={18} className="text-amber-400" />
            <h3>Key Statistical Findings</h3>
            <span className="section-count">{insights.key_findings.length} discovered</span>
          </div>

          <div className="findings-grid">
            {insights.key_findings.map((f) => (
              <div key={f.finding_id} className="finding-card">
                <div className="finding-card-top">
                  <span className="finding-category">{f.category.replace('_', ' ').toUpperCase()}</span>
                  <span className={`importance-tag importance-${f.importance}`}>
                    {f.importance.toUpperCase()}
                  </span>
                </div>

                <h4 className="finding-title">{f.title}</h4>
                <p className="finding-desc">{f.description}</p>

                {f.metric_formatted && (
                  <div className="finding-metric-badge">
                    <Percent size={13} />
                    <span>{f.metric_formatted}</span>
                  </div>
                )}

                <div className="finding-card-footer">
                  <div className="involved-cols">
                    {f.columns_involved.map((col) => (
                      <span key={col} className="col-chip">
                        {col}
                      </span>
                    ))}
                  </div>

                  {f.referenced_fact_ids.length > 0 && (
                    <div className="fact-chips-group">
                      {f.referenced_fact_ids.map((fid) => (
                        <button
                          key={fid}
                          type="button"
                          className="fact-chip-btn"
                          onClick={() => {
                            const fact = findFactById(fid)
                            if (fact) setSelectedFact(fact)
                          }}
                          title="Inspect supporting empirical fact"
                        >
                          #{fid}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 3: BEST & WORST CATEGORY BENCHMARKS */}
      {(activeFilter === 'all' || activeFilter === 'benchmarks') &&
        insights.best_worst_analyses.length > 0 && (
          <div className="insights-section">
            <div className="section-title-row">
              <Award size={18} className="text-emerald-400" />
              <h3>Best & Worst Category Analysis</h3>
              <span className="section-count">
                {insights.best_worst_analyses.length} benchmark comparison
              </span>
            </div>

            {insights.best_worst_analyses.map((bw, idx) => (
              <div key={idx} className="benchmark-card">
                <div className="benchmark-card-header">
                  <div>
                    <h4 className="benchmark-title">
                      Category Comparison: {bw.dimension_column}{' '}
                      <span className="benchmark-sub">
                        ({bw.aggregation} of {bw.metric_column || 'frequency'})
                      </span>
                    </h4>
                    <p className="benchmark-avg">
                      Dataset Benchmark Average: <strong>{bw.formatted_average}</strong>
                    </p>
                  </div>
                </div>

                {/* BEST / WORST SPLIT CARDS */}
                <div className="split-performers-grid">
                  {/* TOP PERFORMER */}
                  <div className="performer-box best-performer-box">
                    <div className="performer-header">
                      <div className="performer-badge best-badge">
                        <TrendingUp size={14} /> TOP PERFORMER
                      </div>
                      <span
                        className={`reliability-tag ${
                          bw.best_performer.is_statistically_reliable
                            ? 'reliable'
                            : 'exploratory'
                        }`}
                      >
                        {bw.best_performer.is_statistically_reliable
                          ? 'Reliable (n ≥ 5)'
                          : 'Exploratory (n < 5)'}
                      </span>
                    </div>

                    <div className="performer-name">{bw.best_performer.category_name}</div>
                    <div className="performer-value">{bw.best_performer.formatted_value}</div>
                    <div className="performer-delta text-emerald-400">
                      {bw.best_performer.delta_vs_average_pct >= 0 ? '+' : ''}
                      {bw.best_performer.delta_vs_average_pct.toFixed(1)}% vs dataset average
                    </div>
                    <div className="performer-sample">Sample size: {bw.best_performer.sample_size} records</div>
                  </div>

                  {/* WORST PERFORMER */}
                  <div className="performer-box worst-performer-box">
                    <div className="performer-header">
                      <div className="performer-badge worst-badge">
                        <TrendingDown size={14} /> LOWEST PERFORMER
                      </div>
                      <span
                        className={`reliability-tag ${
                          bw.worst_performer.is_statistically_reliable
                            ? 'reliable'
                            : 'exploratory'
                        }`}
                      >
                        {bw.worst_performer.is_statistically_reliable
                          ? 'Reliable (n ≥ 5)'
                          : 'Exploratory (n < 5)'}
                      </span>
                    </div>

                    <div className="performer-name">{bw.worst_performer.category_name}</div>
                    <div className="performer-value">{bw.worst_performer.formatted_value}</div>
                    <div className="performer-delta text-rose-400">
                      {bw.worst_performer.delta_vs_average_pct >= 0 ? '+' : ''}
                      {bw.worst_performer.delta_vs_average_pct.toFixed(1)}% vs dataset average
                    </div>
                    <div className="performer-sample">Sample size: {bw.worst_performer.sample_size} records</div>
                  </div>
                </div>

                {/* BENCHMARK CHART */}
                {bw.chart && (
                  <div className="benchmark-chart-container">
                    <InteractiveChart chart={bw.chart} height={320} />
                  </div>
                )}

                {/* RANKED PERFORMERS TABLE */}
                {bw.ranked_performers && bw.ranked_performers.length > 0 && (
                  <div className="ranked-performers-table-wrapper">
                    <table className="ranked-table">
                      <thead>
                        <tr>
                          <th>Rank</th>
                          <th>{bw.dimension_column}</th>
                          <th>Value</th>
                          <th>Delta vs Avg</th>
                          <th>Sample Size</th>
                          <th>Reliability</th>
                        </tr>
                      </thead>
                      <tbody>
                        {bw.ranked_performers.map((p, pIdx) => (
                          <tr
                            key={pIdx}
                            className={
                              pIdx === 0
                                ? 'top-row'
                                : pIdx === bw.ranked_performers.length - 1
                                ? 'bottom-row'
                                : ''
                            }
                          >
                            <td>#{pIdx + 1}</td>
                            <td className="font-semibold text-white">{p.category_name}</td>
                            <td>{p.formatted_value}</td>
                            <td
                              className={
                                p.delta_vs_average_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                              }
                            >
                              {p.delta_vs_average_pct >= 0 ? '+' : ''}
                              {p.delta_vs_average_pct.toFixed(1)}%
                            </td>
                            <td>{p.sample_size}</td>
                            <td>
                              <span
                                className={`status-pill ${
                                  p.is_statistically_reliable ? 'pill-green' : 'pill-amber'
                                }`}
                              >
                                {p.is_statistically_reliable ? 'Reliable' : 'Exploratory'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <div className="benchmark-explanation">
                  <p>{bw.explanation}</p>
                </div>
              </div>
            ))}
          </div>
        )}

      {/* SECTION 4: ANOMALIES & UNUSUAL PATTERNS */}
      {(activeFilter === 'all' || activeFilter === 'anomalies') && (
        <div className="insights-section">
          <div className="section-title-row">
            <ShieldAlert size={18} className="text-rose-400" />
            <h3>Anomalies & Unusual Patterns</h3>
            <span className="section-count">
              {insights.anomalies_and_patterns.length} conditions detected
            </span>
          </div>

          {insights.anomalies_and_patterns.length === 0 ? (
            <div className="empty-insights-box">
              <CheckCircle2 size={24} className="text-emerald-400" />
              <p>No statistically significant anomalies, severe outliers, or invariant columns detected.</p>
            </div>
          ) : (
            <div className="anomalies-grid">
              {insights.anomalies_and_patterns.map((a) => (
                <div key={a.anomaly_id} className="anomaly-card">
                  <div className="anomaly-header">
                    <span className="anomaly-type">
                      {a.anomaly_type.replace('_', ' ').toUpperCase()}
                    </span>
                    {getSeverityBadge(a.severity)}
                  </div>

                  <div className="anomaly-target">
                    Column: <strong className="text-white">{a.column_name}</strong>
                  </div>

                  <p className="anomaly-desc">{a.description}</p>

                  {/* METRIC EVIDENCE */}
                  {a.metric_evidence && Object.keys(a.metric_evidence).length > 0 && (
                    <div className="evidence-box">
                      <div className="evidence-title">Empirical Evidence:</div>
                      <div className="evidence-chips">
                        {a.metric_evidence.iqr_lower_fence !== undefined && (
                          <span className="evidence-chip">
                            Fence: [{String(a.metric_evidence.iqr_lower_fence)},{' '}
                            {String(a.metric_evidence.iqr_upper_fence)}]
                          </span>
                        )}
                        {a.metric_evidence.outlier_count !== undefined && (
                          <span className="evidence-chip">
                            Outliers: {String(a.metric_evidence.outlier_count)} (
                            {String(a.metric_evidence.outlier_percentage)}%)
                          </span>
                        )}
                        {a.metric_evidence.missing_cells !== undefined && (
                          <span className="evidence-chip">
                            Missing: {String(a.metric_evidence.missing_cells)} cells (
                            {String(a.metric_evidence.missing_percentage)}%)
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {a.referenced_fact_ids.length > 0 && (
                    <div className="fact-chips-group mt-2">
                      {a.referenced_fact_ids.map((fid) => (
                        <button
                          key={fid}
                          type="button"
                          className="fact-chip-btn"
                          onClick={() => {
                            const fact = findFactById(fid)
                            if (fact) setSelectedFact(fact)
                          }}
                        >
                          #{fid}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SECTION 5: ACTIONABLE RECOMMENDATIONS */}
      {(activeFilter === 'all' || activeFilter === 'recommendations') && (
        <div className="insights-section">
          <div className="section-title-row">
            <Lightbulb size={18} className="text-yellow-400" />
            <h3>Actionable Business Recommendations</h3>
            <span className="section-count">{insights.recommendations.length} recommendations</span>
          </div>

          <div className="recommendations-grid">
            {insights.recommendations.map((r) => (
              <div key={r.recommendation_id} className="recommendation-card">
                <div className="recommendation-header">
                  <div className="flex items-center gap-2">
                    {getPriorityBadge(r.priority)}
                    <span className="rec-category">{r.category.toUpperCase()}</span>
                  </div>
                  <span
                    className={`classification-badge ${
                      r.is_hypothesis ? 'badge-hypothesis' : 'badge-grounded'
                    }`}
                  >
                    {r.is_hypothesis ? 'Analytical Hypothesis' : 'Verified Fact Grounded'}
                  </span>
                </div>

                <h4 className="rec-title">{r.title}</h4>
                <p className="rec-action">{r.action_statement}</p>

                <div className="impact-box">
                  <div className="impact-label">EXPECTED IMPACT:</div>
                  <div className="impact-val">{r.expected_impact}</div>
                </div>

                {r.referenced_fact_ids.length > 0 && (
                  <div className="fact-chips-group mt-3">
                    <span className="text-xs text-muted">Supporting Facts:</span>
                    {r.referenced_fact_ids.map((fid) => (
                      <button
                        key={fid}
                        type="button"
                        className="fact-chip-btn"
                        onClick={() => {
                          const fact = findFactById(fid)
                          if (fact) setSelectedFact(fact)
                        }}
                      >
                        #{fid}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* FACT INSPECTION MODAL */}
      {selectedFact && (
        <div className="fact-modal-overlay" onClick={() => setSelectedFact(null)}>
          <div className="fact-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="fact-modal-header">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={18} className="text-emerald-400" />
                <h4>Grounded Fact Verification: {selectedFact.fact_id}</h4>
              </div>
              <button
                type="button"
                className="close-btn"
                onClick={() => setSelectedFact(null)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="fact-modal-body">
              <p className="fact-statement">{selectedFact.formatted_statement}</p>

              <div className="fact-details-grid">
                <div className="fact-detail-item">
                  <span className="label">Category:</span>
                  <span className="val">{selectedFact.category}</span>
                </div>
                {selectedFact.column_name && (
                  <div className="fact-detail-item">
                    <span className="label">Column:</span>
                    <span className="val">{selectedFact.column_name}</span>
                  </div>
                )}
                <div className="fact-detail-item">
                  <span className="label">Metric:</span>
                  <span className="val">{selectedFact.metric_name}</span>
                </div>
                <div className="fact-detail-item">
                  <span className="label">Exact Value:</span>
                  <span className="val font-mono">{String(selectedFact.value)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
