import React, { useState } from 'react'
import { Copy, Eye } from 'lucide-react'
import type { CleaningPreviewRequest, DataQualityProfile } from '../../types/cleaning'

interface DuplicateManagerProps {
  profile: DataQualityProfile
  onPreview: (request: CleaningPreviewRequest) => void
  isLoading?: boolean
}

export const DuplicateManager: React.FC<DuplicateManagerProps> = ({
  profile,
  onPreview,
  isLoading = false,
}) => {
  const [keepStrategy, setKeepStrategy] = useState<'first' | 'last'>('first')
  const { duplicate_rows, duplicate_percentage, total_rows } = profile

  const handleTriggerPreview = () => {
    onPreview({
      operation_type: 'duplicates',
      strategy: 'remove_duplicates',
      parameters: { keep: keepStrategy },
    })
  }

  return (
    <div className="cleaning-card">
      <div className="cleaning-card-header">
        <div>
          <h3 className="cleaning-card-title">Duplicate Row Detection & Removal</h3>
          <p className="cleaning-card-subtitle">
            Identify redundant rows across all dataset attributes and safely deduplicate records.
          </p>
        </div>
      </div>

      <div className="duplicate-status-box">
        <div className="flex items-center gap-3">
          <div className="status-icon-pill">
            <Copy size={20} className={duplicate_rows > 0 ? 'text-amber-400' : 'text-emerald-400'} />
          </div>
          <div>
            <div className="text-sm font-semibold text-neutral-200">
              {duplicate_rows > 0
                ? `${duplicate_rows.toLocaleString()} Duplicate Rows Detected (${duplicate_percentage}%)`
                : 'Zero Duplicate Records Found'}
            </div>
            <div className="text-xs text-neutral-400">
              {duplicate_rows > 0
                ? `Removing duplicates will reduce the dataset size from ${total_rows.toLocaleString()} to ${(total_rows - duplicate_rows).toLocaleString()} rows.`
                : 'The active dataset contains 100% unique row records.'}
            </div>
          </div>
        </div>
      </div>

      <div className="cleaning-controls-grid mt-4">
        <div className="control-group">
          <label className="control-label">Deduplication Rule</label>
          <select
            className="control-select"
            value={keepStrategy}
            onChange={(e) => setKeepStrategy(e.target.value as 'first' | 'last')}
          >
            <option value="first">Keep First Occurrence (Preserve chronologically earliest row)</option>
            <option value="last">Keep Last Occurrence (Preserve chronologically latest row)</option>
          </select>
          <div className="control-hint mt-1 text-xs text-neutral-400">
            Select which row instance is retained when identical copies are encountered.
          </div>
        </div>
      </div>

      <div className="cleaning-action-footer">
        <button
          type="button"
          className="button button-primary flex items-center gap-2"
          onClick={handleTriggerPreview}
          disabled={isLoading || duplicate_rows === 0}
        >
          <Eye size={15} />
          {isLoading ? 'Simulating...' : 'Preview Deduplication'}
        </button>
        {duplicate_rows === 0 && (
          <span className="text-xs text-neutral-400 self-center">
            No duplicate rows exist to remove.
          </span>
        )}
      </div>
    </div>
  )
}
