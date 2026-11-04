import React from 'react'
import {
  Table as TableIcon,
  X,
} from 'lucide-react'
import type { DrillDownResponse } from '../../types/dashboard'

interface DrillDownPanelProps {
  drillDownData: DrillDownResponse | null
  isLoading?: boolean
  onClose: () => void
}

export const DrillDownPanel: React.FC<DrillDownPanelProps> = ({
  drillDownData,
  isLoading = false,
  onClose,
}) => {
  if (!drillDownData && !isLoading) {
    return null
  }

  return (
    <div className="drilldown-modal-backdrop" onClick={onClose}>
      <div
        className="drilldown-modal-container"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="drilldown-header">
          <div>
            <span className="drilldown-eyebrow">CATEGORY DRILL-DOWN</span>
            <h3>
              {drillDownData?.category_column}:{' '}
              <span className="gradient-text">{drillDownData?.category_value}</span>
            </h3>
          </div>

          <button
            type="button"
            className="drilldown-close-btn"
            onClick={onClose}
            aria-label="Close drill-down panel"
          >
            <X size={18} />
          </button>
        </div>

        {isLoading ? (
          <div className="drilldown-loading">
            <div className="spinner-large" />
            <p>Filtering segment records...</p>
          </div>
        ) : drillDownData ? (
          <div className="drilldown-body">
            {/* Quick Segment Metrics */}
            <div className="drilldown-metrics-grid">
              <div className="drilldown-metric-card">
                <span className="drilldown-m-label">MATCHING ROWS</span>
                <strong className="drilldown-m-val">
                  {drillDownData.total_matching_rows.toLocaleString()}
                </strong>
                <span className="drilldown-m-sub">
                  {drillDownData.summary_stats.percentage_of_total}% of active dataset
                </span>
              </div>

              {drillDownData.summary_stats.numeric_metrics &&
                Object.entries(drillDownData.summary_stats.numeric_metrics)
                  .slice(0, 3)
                  .map(([col, stats]) => (
                    <div key={col} className="drilldown-metric-card">
                      <span className="drilldown-m-label">{col.toUpperCase()}</span>
                      <strong className="drilldown-m-val">
                        Sum: {stats.sum.toLocaleString()}
                      </strong>
                      <span className="drilldown-m-sub">
                        Avg: {stats.mean.toLocaleString()}
                      </span>
                    </div>
                  ))}
            </div>

            {/* Matching Sample Records Table */}
            <div className="drilldown-table-section">
              <div className="drilldown-table-header">
                <div className="table-header-title">
                  <TableIcon size={16} />
                  <h4>Sample Matching Records</h4>
                </div>
                <span className="records-count-tag">
                  Showing top {drillDownData.sample_records.length} of{' '}
                  {drillDownData.total_matching_rows.toLocaleString()} rows
                </span>
              </div>

              {drillDownData.sample_records.length > 0 ? (
                <div className="table-scroll-container">
                  <table className="data-preview-table">
                    <thead>
                      <tr>
                        {Object.keys(drillDownData.sample_records[0]).map((col) => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {drillDownData.sample_records.map((row, idx) => (
                        <tr key={idx}>
                          {Object.keys(drillDownData.sample_records[0]).map((col) => (
                            <td key={col}>
                              {row[col] === null ? (
                                <span className="null-cell-tag">null</span>
                              ) : (
                                String(row[col])
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="no-records-note">No matching records found.</p>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
