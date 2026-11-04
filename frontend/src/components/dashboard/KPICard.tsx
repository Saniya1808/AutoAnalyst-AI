import React from 'react'
import {
  AlertTriangle,
  Calculator,
  CheckCircle2,
  Copy,
  Database,
  Layers,
} from 'lucide-react'
import type { ColumnInfo, DashboardKPI } from '../../types/dashboard'

interface KPICardProps {
  kpis: DashboardKPI
  availableColumns: ColumnInfo[]
  onSelectNumericColumn: (column: string) => void
}

export const KPICard: React.FC<KPICardProps> = ({
  kpis,
  availableColumns,
  onSelectNumericColumn,
}) => {
  const numericColumns = availableColumns.filter(
    (c) => c.data_type === 'integer' || c.data_type === 'float'
  )

  const stats = kpis.selected_column_stats

  return (
    <div className="dashboard-kpis-section">
      <div className="kpi-grid-primary">
        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-purple">
            <Layers size={18} />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">TOTAL ROWS</span>
            <strong className="kpi-value">{kpis.total_rows.toLocaleString()}</strong>
            <span className="kpi-sub">{kpis.total_cells.toLocaleString()} data cells</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-blue">
            <Database size={18} />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">TOTAL COLUMNS</span>
            <strong className="kpi-value">{kpis.total_columns}</strong>
            <span className="kpi-sub">
              {numericColumns.length} numeric, {kpis.total_columns - numericColumns.length} other
            </span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-amber">
            <AlertTriangle size={18} />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">MISSING VALUES</span>
            <strong className="kpi-value">
              {kpis.missing_cells.toLocaleString()}
            </strong>
            <span className="kpi-sub">
              {kpis.missing_percentage}% of total cells
            </span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-pink">
            <Copy size={18} />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">DUPLICATE ROWS</span>
            <strong className="kpi-value">
              {kpis.duplicate_rows.toLocaleString()}
            </strong>
            <span className="kpi-sub">
              {kpis.duplicate_percentage}% duplicate rate
            </span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-green">
            <CheckCircle2 size={18} />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">DATA COMPLETENESS</span>
            <strong className="kpi-value">{kpis.data_completeness}%</strong>
            <span className="kpi-sub">Overall quality score</span>
          </div>
        </div>
      </div>

      {/* Numeric Column Deep-Dive Metric Card */}
      {numericColumns.length > 0 && (
        <div className="numeric-kpi-banner">
          <div className="numeric-kpi-header">
            <div className="numeric-kpi-title">
              <Calculator size={18} />
              <h4>Column Metric Calculations</h4>
            </div>

            <div className="numeric-selector-wrap">
              <label htmlFor="numeric-col-select">Select Numeric Column:</label>
              <select
                id="numeric-col-select"
                className="metric-select-dropdown"
                value={kpis.selected_column || numericColumns[0].name}
                onChange={(e) => onSelectNumericColumn(e.target.value)}
              >
                {numericColumns.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name} ({c.data_type})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {stats && (
            <div className="numeric-stats-row">
              <div className="num-stat-box">
                <span className="num-stat-label">SUM</span>
                <strong className="num-stat-val">
                  {stats.sum !== null ? stats.sum.toLocaleString() : '—'}
                </strong>
              </div>

              <div className="num-stat-box">
                <span className="num-stat-label">AVERAGE (MEAN)</span>
                <strong className="num-stat-val">
                  {stats.average !== null ? stats.average.toLocaleString() : '—'}
                </strong>
              </div>

              <div className="num-stat-box">
                <span className="num-stat-label">MINIMUM</span>
                <strong className="num-stat-val">
                  {stats.minimum !== null ? stats.minimum.toLocaleString() : '—'}
                </strong>
              </div>

              <div className="num-stat-box">
                <span className="num-stat-label">MAXIMUM</span>
                <strong className="num-stat-val">
                  {stats.maximum !== null ? stats.maximum.toLocaleString() : '—'}
                </strong>
              </div>

              {stats.std !== null && (
                <div className="num-stat-box">
                  <span className="num-stat-label">STD DEV</span>
                  <strong className="num-stat-val">{stats.std.toLocaleString()}</strong>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
