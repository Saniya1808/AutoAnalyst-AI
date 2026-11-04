import React, { useState } from 'react'
import { Eye } from 'lucide-react'
import type { CleaningPreviewRequest, DataQualityProfile } from '../../types/cleaning'

interface DataTypeConverterProps {
  profile: DataQualityProfile
  selectedColumn?: string
  onPreview: (request: CleaningPreviewRequest) => void
  isLoading?: boolean
}

export const DataTypeConverter: React.FC<DataTypeConverterProps> = ({
  profile,
  selectedColumn: initialCol,
  onPreview,
  isLoading = false,
}) => {
  const [columnName, setColumnName] = useState<string>(
    initialCol || profile.columns[0]?.column_name || ''
  )
  const [targetType, setTargetType] = useState<string>('integer')
  const [forceCoerce, setForceCoerce] = useState<boolean>(true)

  const activeCol = profile.columns.find((c) => c.column_name === columnName)

  const handleTriggerPreview = () => {
    if (!columnName) return

    onPreview({
      operation_type: 'type_conversion',
      column_name: columnName,
      strategy: targetType,
      parameters: { force_coercion: forceCoerce },
    })
  }

  return (
    <div className="cleaning-card">
      <div className="cleaning-card-header">
        <div>
          <h3 className="cleaning-card-title">Data Type Coercion & Schema Casting</h3>
          <p className="cleaning-card-subtitle">
            Convert column types to Integer, Float, String, Boolean, or Datetime with safe error coercion.
          </p>
        </div>
      </div>

      <div className="cleaning-controls-grid">
        <div className="control-group">
          <label className="control-label">Column to Convert</label>
          <select
            className="control-select"
            value={columnName}
            onChange={(e) => setColumnName(e.target.value)}
          >
            {profile.columns.map((col) => (
              <option key={col.column_name} value={col.column_name}>
                {col.column_name} (Current: {col.data_type})
              </option>
            ))}
          </select>
          {activeCol && (
            <div className="control-hint mt-1 text-xs text-neutral-400">
              Current semantic data type:{' '}
              <span className="text-purple-300 font-medium">{activeCol.data_type}</span>
            </div>
          )}
        </div>

        <div className="control-group">
          <label className="control-label">Target Data Type</label>
          <select
            className="control-select"
            value={targetType}
            onChange={(e) => setTargetType(e.target.value)}
          >
            <option value="integer">Integer (Nullable Int64)</option>
            <option value="float">Float (Floating point numeric / Float64)</option>
            <option value="string">String (Text representation)</option>
            <option value="boolean">Boolean (True / False)</option>
            <option value="datetime">Datetime (Parsed ISO timestamp)</option>
          </select>
          <div className="control-hint mt-1 text-xs text-neutral-400">
            {targetType === 'integer' && 'Rounds decimals and casts to integer. Non-numeric values become null.'}
            {targetType === 'float' && 'Converts values to 64-bit float numbers.'}
            {targetType === 'string' && 'Converts every cell to standard string representation.'}
            {targetType === 'boolean' && 'Parses truthy values (true, 1, yes) and falsy values (false, 0, no).'}
            {targetType === 'datetime' && 'Parses date strings into chronologically sortable timestamps.'}
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <input
          type="checkbox"
          id="coerce-check"
          className="rounded border-neutral-700 text-purple-600 focus:ring-purple-500"
          checked={forceCoerce}
          onChange={(e) => setForceCoerce(e.target.checked)}
        />
        <label htmlFor="coerce-check" className="text-xs text-neutral-300 cursor-pointer">
          Safely coerce invalid non-convertible values to <code>null</code> without failing the transformation.
        </label>
      </div>

      <div className="cleaning-action-footer">
        <button
          type="button"
          className="button button-primary flex items-center gap-2"
          onClick={handleTriggerPreview}
          disabled={isLoading || !columnName}
        >
          <Eye size={15} />
          {isLoading ? 'Simulating...' : 'Preview Conversion'}
        </button>
      </div>
    </div>
  )
}
