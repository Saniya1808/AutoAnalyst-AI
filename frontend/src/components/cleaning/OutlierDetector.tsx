import React, { useState } from 'react'
import { AlertTriangle, Eye, Info } from 'lucide-react'
import type { CleaningPreviewRequest, DataQualityProfile } from '../../types/cleaning'

interface OutlierDetectorProps {
  profile: DataQualityProfile
  selectedColumn?: string
  onPreview: (request: CleaningPreviewRequest) => void
  isLoading?: boolean
}

export const OutlierDetector: React.FC<OutlierDetectorProps> = ({
  profile,
  selectedColumn: initialCol,
  onPreview,
  isLoading = false,
}) => {
  const numericCols = profile.columns.filter((c) => c.is_numeric)

  const [columnName, setColumnName] = useState<string>(
    initialCol && numericCols.some((c) => c.column_name === initialCol)
      ? initialCol
      : numericCols[0]?.column_name || ''
  )
  const [method, setMethod] = useState<'iqr' | 'zscore'>('iqr')
  const [zThreshold, setZThreshold] = useState<number>(3.0)
  const [strategy, setStrategy] = useState<'cap_values' | 'remove_rows' | 'keep'>('cap_values')
  const [isConfirmed, setIsConfirmed] = useState<boolean>(false)

  const colDetails = profile.outlier_details[columnName]
  const iqrInfo = colDetails?.iqr
  const zInfo = colDetails?.zscore

  const activeStats = method === 'iqr' ? iqrInfo : zInfo
  const outlierCount = activeStats?.outlier_count ?? 0
  const outlierPct = activeStats?.outlier_percentage ?? 0

  const handleTriggerPreview = () => {
    if (!columnName) return

    onPreview({
      operation_type: 'outliers',
      column_name: columnName,
      strategy: strategy,
      parameters: {
        method: method,
        threshold: zThreshold,
      },
    })
  }

  return (
    <div className="cleaning-card">
      <div className="cleaning-card-header">
        <div>
          <h3 className="cleaning-card-title">Outlier Detection & Boundary Treatment</h3>
          <p className="cleaning-card-subtitle">
            Detect distribution extremes via IQR or Z-score and safely winsorize (cap) or filter records.
          </p>
        </div>
      </div>

      {/* Educational Notice on Outlier Safety */}
      <div className="outlier-alert-banner">
        <Info size={18} className="text-blue-400 shrink-0 mt-0.5" />
        <div className="text-xs text-neutral-300 leading-relaxed">
          <b className="text-neutral-100">Statistical Outlier Advisory:</b> Extreme values detected outside statistical boundaries are not necessarily erroneous. In business data, they often represent legitimate high-value orders, enterprise accounts, or peak seasonal spikes. Always verify domain context before applying destructive removals.
        </div>
      </div>

      <div className="cleaning-controls-grid mt-4">
        {/* Column Picker */}
        <div className="control-group">
          <label className="control-label">Numeric Column</label>
          <select
            className="control-select"
            value={columnName}
            onChange={(e) => {
              setColumnName(e.target.value)
              setIsConfirmed(false)
            }}
          >
            {numericCols.map((col) => (
              <option key={col.column_name} value={col.column_name}>
                {col.column_name} ({col.data_type})
              </option>
            ))}
          </select>
        </div>

        {/* Method Picker */}
        <div className="control-group">
          <label className="control-label">Detection Method</label>
          <select
            className="control-select"
            value={method}
            onChange={(e) => setMethod(e.target.value as 'iqr' | 'zscore')}
          >
            <option value="iqr">Interquartile Range (IQR = Q3 - Q1, 1.5× Rule)</option>
            <option value="zscore">Z-Score Standard Deviation (Z &gt; Threshold)</option>
          </select>
        </div>

        {/* Z-Score Threshold if Z-Score selected */}
        {method === 'zscore' && (
          <div className="control-group">
            <label className="control-label">Z-Score Threshold (σ)</label>
            <select
              className="control-select"
              value={zThreshold}
              onChange={(e) => setZThreshold(Number(e.target.value))}
            >
              <option value={2.0}>2.0 σ (Conservative ~95.4% of normal data)</option>
              <option value={2.5}>2.5 σ (Standard ~98.8% of normal data)</option>
              <option value={3.0}>3.0 σ (Standard 3-Sigma ~99.7% of normal data)</option>
              <option value={3.5}>3.5 σ (Strict extreme detection)</option>
            </select>
          </div>
        )}

        {/* Strategy */}
        <div className="control-group">
          <label className="control-label">Treatment Action</label>
          <select
            className="control-select"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value as 'cap_values' | 'remove_rows' | 'keep')}
          >
            <option value="cap_values">Cap Extreme Values (Winsorize to Lower/Upper Bound)</option>
            <option value="remove_rows">Remove Rows Containing Outliers</option>
            <option value="keep">Keep Outliers (Informational inspection only)</option>
          </select>
        </div>
      </div>

      {/* Outlier Statistics Display Box */}
      {activeStats && (
        <div className="outlier-metrics-display mt-4">
          <div className="metric-box">
            <span className="metric-box-label">Outlier Count</span>
            <span className="metric-box-val text-amber-400">
              {outlierCount.toLocaleString()} ({outlierPct}%)
            </span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Lower Boundary</span>
            <span className="metric-box-val text-neutral-300 font-mono">
              {activeStats.lower_bound}
            </span>
          </div>
          <div className="metric-box">
            <span className="metric-box-label">Upper Boundary</span>
            <span className="metric-box-val text-neutral-300 font-mono">
              {activeStats.upper_bound}
            </span>
          </div>
          {method === 'iqr' && iqrInfo && (
            <div className="metric-box">
              <span className="metric-box-label">IQR (Q3 - Q1)</span>
              <span className="metric-box-val text-neutral-300 font-mono">
                {iqrInfo.iqr} (Q1: {iqrInfo.q1}, Q3: {iqrInfo.q3})
              </span>
            </div>
          )}
          {method === 'zscore' && zInfo && (
            <div className="metric-box">
              <span className="metric-box-label">Mean & Std Dev</span>
              <span className="metric-box-val text-neutral-300 font-mono">
                μ={zInfo.mean}, σ={zInfo.std}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Explicit Confirmation Checkbox for Destructive Actions */}
      {strategy !== 'keep' && (
        <div className="mt-4 flex items-center gap-2">
          <input
            type="checkbox"
            id="outlier-confirm"
            className="rounded border-neutral-700 text-purple-600 focus:ring-purple-500"
            checked={isConfirmed}
            onChange={(e) => setIsConfirmed(e.target.checked)}
          />
          <label htmlFor="outlier-confirm" className="text-xs text-neutral-300 cursor-pointer">
            I confirm that I have reviewed the outlier boundaries and want to apply this treatment.
          </label>
        </div>
      )}

      <div className="cleaning-action-footer">
        <button
          type="button"
          className="button button-primary flex items-center gap-2"
          onClick={handleTriggerPreview}
          disabled={isLoading || !columnName || (strategy !== 'keep' && !isConfirmed)}
        >
          <Eye size={15} />
          {isLoading ? 'Simulating...' : 'Preview Outlier Treatment'}
        </button>
        {strategy !== 'keep' && !isConfirmed && (
          <span className="text-xs text-amber-400 self-center flex items-center gap-1">
            <AlertTriangle size={12} /> Please confirm review before previewing treatment.
          </span>
        )}
      </div>
    </div>
  )
}
