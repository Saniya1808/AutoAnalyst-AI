import React from 'react'
import {
  CheckCircle2,
  Copy,
  FileCheck2,
  Percent,
  ShieldCheck,
} from 'lucide-react'
import type { DataQualityProfile } from '../../types/cleaning'

interface DataQualityOverviewProps {
  profile: DataQualityProfile
  onSelectColumn?: (colName: string) => void
}

export const DataQualityOverview: React.FC<DataQualityOverviewProps> = ({
  profile,
  onSelectColumn,
}) => {
  const { quality_metrics } = profile

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10'
    if (score >= 75) return 'text-blue-400 border-blue-500/40 bg-blue-500/10'
    if (score >= 50) return 'text-amber-400 border-amber-500/40 bg-amber-500/10'
    return 'text-rose-400 border-rose-500/40 bg-rose-500/10'
  }

  return (
    <div className="cleaning-quality-overview">
      {/* Top Banner: Composite Score & Integrity Badge */}
      <div className="quality-header-card">
        <div className="quality-header-left">
          <div className={`quality-score-circle ${getScoreColor(quality_metrics.overall_quality_score)}`}>
            <span className="score-value">{Math.round(quality_metrics.overall_quality_score)}</span>
            <span className="score-label">/ 100</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="quality-title">Data Quality Index: {quality_metrics.quality_grade}</h3>
              {profile.is_cleaned && (
                <span className="badge-cleaned">Version {profile.version} Cleaned</span>
              )}
            </div>
            <p className="quality-subtitle">
              Calculated via standardized formula:{' '}
              <code>Q = 0.50×Completeness + 0.30×Validity + 0.20×Uniqueness</code>
            </p>
          </div>
        </div>

        {profile.original_file_hash && (
          <div className="integrity-badge">
            <ShieldCheck size={18} className="text-emerald-400" />
            <div>
              <div className="integrity-title">Original Source Integrity Verified</div>
              <div className="integrity-hash font-mono">
                SHA-256: {profile.original_file_hash.substring(0, 16)}...
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3 Pillars Breakdown */}
      <div className="quality-pillars-grid">
        <div className="pillar-card">
          <div className="pillar-header">
            <Percent size={18} className="text-purple-400" />
            <span className="pillar-title">Completeness</span>
            <span className="pillar-weight">50% weight</span>
          </div>
          <div className="pillar-score">{quality_metrics.completeness_score}%</div>
          <div className="pillar-bar-bg">
            <div
              className="pillar-bar-fill bg-purple-500"
              style={{ width: `${quality_metrics.completeness_score}%` }}
            />
          </div>
          <p className="pillar-desc">
            {profile.total_missing_cells} missing cells ({profile.missing_percentage}% of dataset)
          </p>
        </div>

        <div className="pillar-card">
          <div className="pillar-header">
            <FileCheck2 size={18} className="text-cyan-400" />
            <span className="pillar-title">Validity</span>
            <span className="pillar-weight">30% weight</span>
          </div>
          <div className="pillar-score">{quality_metrics.validity_score}%</div>
          <div className="pillar-bar-bg">
            <div
              className="pillar-bar-fill bg-cyan-500"
              style={{ width: `${quality_metrics.validity_score}%` }}
            />
          </div>
          <p className="pillar-desc">
            Values conforming to inferred semantic data types without coercion errors or infinities
          </p>
        </div>

        <div className="pillar-card">
          <div className="pillar-header">
            <Copy size={18} className="text-emerald-400" />
            <span className="pillar-title">Uniqueness</span>
            <span className="pillar-weight">20% weight</span>
          </div>
          <div className="pillar-score">{quality_metrics.uniqueness_score}%</div>
          <div className="pillar-bar-bg">
            <div
              className="pillar-bar-fill bg-emerald-500"
              style={{ width: `${quality_metrics.uniqueness_score}%` }}
            />
          </div>
          <p className="pillar-desc">
            {profile.duplicate_rows} duplicate rows ({profile.duplicate_percentage}% redundancy)
          </p>
        </div>
      </div>

      {/* Column Quality Table */}
      <div className="quality-columns-section">
        <div className="section-title-row">
          <h4 className="text-sm font-semibold tracking-wide text-neutral-300">
            Column-by-Column Quality Metrics ({profile.columns.length} columns)
          </h4>
          <span className="text-xs text-neutral-400">Click a column to quickly inspect</span>
        </div>

        <div className="table-responsive-container">
          <table className="quality-table">
            <thead>
              <tr>
                <th>Column</th>
                <th>Type</th>
                <th>Missing Values</th>
                <th>Unique Values</th>
                <th>IQR Outliers</th>
                <th>Z-Score Outliers</th>
              </tr>
            </thead>
            <tbody>
              {profile.columns.map((col) => (
                <tr
                  key={col.column_name}
                  className="quality-tr cursor-pointer hover:bg-neutral-800/40"
                  onClick={() => onSelectColumn?.(col.column_name)}
                >
                  <td className="font-medium text-neutral-200">
                    <div className="flex items-center gap-1.5">
                      <span>{col.column_name}</span>
                      {col.missing_count > 0 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300">
                          {col.missing_percentage}% null
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className="badge-type">{col.data_type}</span>
                  </td>
                  <td>
                    {col.missing_count === 0 ? (
                      <span className="text-emerald-400 flex items-center gap-1 text-xs">
                        <CheckCircle2 size={13} /> Complete
                      </span>
                    ) : (
                      <span className="text-amber-400 text-xs">
                        {col.missing_count.toLocaleString()} cells ({col.missing_percentage}%)
                      </span>
                    )}
                  </td>
                  <td className="text-xs text-neutral-300">
                    {col.unique_count.toLocaleString()} unique
                  </td>
                  <td>
                    {col.is_numeric && col.outliers_iqr_count != null ? (
                      col.outliers_iqr_count > 0 ? (
                        <span className="text-rose-400 text-xs font-mono">
                          {col.outliers_iqr_count} outliers
                        </span>
                      ) : (
                        <span className="text-neutral-500 text-xs font-mono">0</span>
                      )
                    ) : (
                      <span className="text-neutral-600 text-xs">—</span>
                    )}
                  </td>
                  <td>
                    {col.is_numeric && col.outliers_zscore_count != null ? (
                      col.outliers_zscore_count > 0 ? (
                        <span className="text-amber-400 text-xs font-mono">
                          {col.outliers_zscore_count} outliers
                        </span>
                      ) : (
                        <span className="text-neutral-500 text-xs font-mono">0</span>
                      )
                    ) : (
                      <span className="text-neutral-600 text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
