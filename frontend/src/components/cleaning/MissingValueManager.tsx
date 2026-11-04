import React, { useState } from 'react'
import { CheckCircle2, Eye } from 'lucide-react'
import type { CleaningPreviewRequest, DataQualityProfile } from '../../types/cleaning'

interface MissingValueManagerProps {
  profile: DataQualityProfile
  selectedColumn?: string
  onPreview: (request: CleaningPreviewRequest) => void
  isLoading?: boolean
}

export const MissingValueManager: React.FC<MissingValueManagerProps> = ({
  profile,
  selectedColumn: initialCol,
  onPreview,
  isLoading = false,
}) => {
  const [columnName, setColumnName] = useState<string>(
    initialCol || profile.columns.find((c) => c.missing_count > 0)?.column_name || profile.columns[0]?.column_name || ''
  )
  const [strategy, setStrategy] = useState<string>('mean_replacement')
  const [constantValue, setConstantValue] = useState<string>('0')

  const activeCol = profile.columns.find((c) => c.column_name === columnName)
  const isNumeric = activeCol?.is_numeric ?? false
  const missingCount = activeCol?.missing_count ?? 0
  const missingPct = activeCol?.missing_percentage ?? 0

  // Auto-adjust strategy when column changes
  const handleColumnChange = (newColName: string) => {
    setColumnName(newColName)
    const targetCol = profile.columns.find((c) => c.column_name === newColName)
    if (targetCol?.is_numeric) {
      setStrategy('mean_replacement')
      setConstantValue('0')
    } else {
      setStrategy('mode_replacement')
      setConstantValue('Unknown')
    }
  }

  const handleTriggerPreview = () => {
    if (!columnName && strategy !== 'remove_rows') return

    const params: Record<string, any> = {}
    if (strategy === 'constant_replacement') {
      params.value = isNumeric ? Number(constantValue) : constantValue
    }

    const req: CleaningPreviewRequest = {
      operation_type: 'missing_values',
      column_name: columnName,
      strategy: strategy,
      parameters: params,
    }
    onPreview(req)
  }

  return (
    <div className="cleaning-card">
      <div className="cleaning-card-header">
        <div>
          <h3 className="cleaning-card-title">Missing Value Imputation & Treatment</h3>
          <p className="cleaning-card-subtitle">
            Impute or remove missing values safely using statistical methods or constant fills.
          </p>
        </div>
      </div>

      <div className="cleaning-controls-grid">
        {/* Column Picker */}
        <div className="control-group">
          <label className="control-label">Target Column</label>
          <select
            className="control-select"
            value={columnName}
            onChange={(e) => handleColumnChange(e.target.value)}
          >
            {profile.columns.map((col) => (
              <option key={col.column_name} value={col.column_name}>
                {col.column_name} ({col.data_type}) — {col.missing_count} missing ({col.missing_percentage}%)
              </option>
            ))}
          </select>
          {activeCol && (
            <div className="control-hint flex items-center gap-1.5 mt-1 text-xs">
              {missingCount > 0 ? (
                <span className="text-amber-400 font-medium">
                  {missingCount.toLocaleString()} cells missing ({missingPct}%)
                </span>
              ) : (
                <span className="text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 size={12} /> Complete (0 missing)
                </span>
              )}
            </div>
          )}
        </div>

        {/* Strategy Selector */}
        <div className="control-group">
          <label className="control-label">Treatment Strategy</label>
          <select
            className="control-select"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
          >
            {isNumeric ? (
              <>
                <option value="mean_replacement">Mean Imputation (Arithmetic Average)</option>
                <option value="median_replacement">Median Imputation (50th Percentile / Robust)</option>
                <option value="constant_replacement">Constant Value Replacement</option>
                <option value="remove_rows">Remove Rows with Missing Values in this Column</option>
                <option value="remove_column">Remove Column Entirely</option>
              </>
            ) : (
              <>
                <option value="mode_replacement">Mode Imputation (Most Frequent Category)</option>
                <option value="constant_replacement">Constant String Replacement (e.g. 'Unknown')</option>
                <option value="remove_rows">Remove Rows with Missing Values in this Column</option>
                <option value="remove_column">Remove Column Entirely</option>
              </>
            )}
          </select>
          <div className="control-hint mt-1 text-xs text-neutral-400">
            {strategy === 'mean_replacement' && 'Replaces missing values with column mean. Sensitive to extreme outliers.'}
            {strategy === 'median_replacement' && 'Replaces missing values with median. Resistant to outliers.'}
            {strategy === 'mode_replacement' && 'Fills missing values with the most frequently occurring category.'}
            {strategy === 'constant_replacement' && 'Replaces missing values with a designated fixed constant.'}
            {strategy === 'remove_rows' && 'Drops records where this column is empty. Decreases row count.'}
            {strategy === 'remove_column' && 'Deletes this column from the cleaned dataset entirely.'}
          </div>
        </div>

        {/* Constant Value Input */}
        {strategy === 'constant_replacement' && (
          <div className="control-group">
            <label className="control-label">Replacement Value</label>
            <input
              type={isNumeric ? 'number' : 'text'}
              className="control-input"
              value={constantValue}
              onChange={(e) => setConstantValue(e.target.value)}
              placeholder={isNumeric ? '0' : 'Unknown'}
            />
          </div>
        )}
      </div>

      <div className="cleaning-action-footer">
        <button
          type="button"
          className="button button-primary flex items-center gap-2"
          onClick={handleTriggerPreview}
          disabled={isLoading || (missingCount === 0 && strategy !== 'remove_column')}
        >
          <Eye size={15} />
          {isLoading ? 'Simulating...' : 'Preview Transformation'}
        </button>
        {missingCount === 0 && strategy !== 'remove_column' && (
          <span className="text-xs text-neutral-400 self-center">
            Column '{columnName}' has no missing values.
          </span>
        )}
      </div>
    </div>
  )
}
