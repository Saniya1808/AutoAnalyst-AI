import React, { useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  Sparkles,
  X,
} from 'lucide-react'
import type { CleaningPreviewResponse } from '../../types/cleaning'

interface CleaningPreviewModalProps {
  preview: CleaningPreviewResponse | null
  onClose: () => void
  onConfirmApply: () => void
  isApplying?: boolean
}

export const CleaningPreviewModal: React.FC<CleaningPreviewModalProps> = ({
  preview,
  onClose,
  onConfirmApply,
  isApplying = false,
}) => {
  const [activeDiffTab, setActiveDiffTab] = useState<'after' | 'before'>('after')

  if (!preview) return null

  const sampleCols =
    preview.cleaned_sample.length > 0
      ? Object.keys(preview.cleaned_sample[0])
      : preview.original_sample.length > 0
      ? Object.keys(preview.original_sample[0])
      : []

  return (
    <div className="drilldown-modal-backdrop">
      <div className="cleaning-preview-modal-box">
        {/* Modal Header */}
        <div className="preview-modal-header">
          <div className="flex items-center gap-2">
            <div className="preview-badge-pill">
              <Sparkles size={16} className="text-purple-400" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-neutral-100">
                Transformation Impact Preview
              </h3>
              <p className="text-xs text-neutral-400">
                Simulated in-memory without altering original source files.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="toast-close-btn"
            onClick={onClose}
            disabled={isApplying}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="preview-modal-body">
          {/* Summary Box */}
          <div className="preview-summary-card">
            <div className="text-sm font-medium text-neutral-200">{preview.summary}</div>
            <div className="preview-stats-row mt-2 flex flex-wrap gap-4 text-xs">
              <span className="badge-stat">
                Affected Rows: <b>{preview.affected_rows.toLocaleString()}</b>
              </span>
              <span className="badge-stat">
                Affected Cells: <b>{preview.affected_cells.toLocaleString()}</b>
              </span>
              <span className="badge-stat">
                Operation: <b>{preview.operation_type}</b>
              </span>
              {preview.column_name && (
                <span className="badge-stat">
                  Column: <b>{preview.column_name}</b>
                </span>
              )}
            </div>
          </div>

          {/* Validation Warnings if any */}
          {preview.validation_warnings.length > 0 && (
            <div className="preview-warnings-card mt-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-amber-300">
                <AlertTriangle size={14} /> Attention Needed:
              </div>
              <ul className="list-disc list-inside mt-1 space-y-1 text-xs text-amber-200/90">
                {preview.validation_warnings.map((warn, i) => (
                  <li key={i}>{warn}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Diff Preview Sample Table */}
          <div className="preview-diff-section mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-neutral-400">
                Sample Record Comparison (First 5 Rows)
              </span>
              <div className="tab-buttons-group scale-90 origin-right">
                <button
                  type="button"
                  className={`tab-btn ${activeDiffTab === 'after' ? 'active' : ''}`}
                  onClick={() => setActiveDiffTab('after')}
                >
                  <FileCheck2 size={13} /> Cleaned Result
                </button>
                <button
                  type="button"
                  className={`tab-btn ${activeDiffTab === 'before' ? 'active' : ''}`}
                  onClick={() => setActiveDiffTab('before')}
                >
                  Original Data
                </button>
              </div>
            </div>

            <div className="table-responsive-container max-h-60 overflow-y-auto">
              <table className="quality-table">
                <thead>
                  <tr>
                    {sampleCols.map((col) => (
                      <th
                        key={col}
                        className={col === preview.column_name ? 'text-purple-300 bg-purple-900/20' : ''}
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(activeDiffTab === 'after' ? preview.cleaned_sample : preview.original_sample).map(
                    (row, rowIdx) => (
                      <tr key={rowIdx} className="hover:bg-neutral-800/30">
                        {sampleCols.map((col) => {
                          const val = row[col]
                          const isTargetCol = col === preview.column_name
                          return (
                            <td
                              key={col}
                              className={`text-xs ${
                                isTargetCol ? 'bg-purple-900/10 font-medium text-purple-200' : ''
                              }`}
                            >
                              {val === null || val === undefined ? (
                                <span className="preview-null-tag">null</span>
                              ) : (
                                String(val)
                              )}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="preview-modal-footer">
          <button
            type="button"
            className="button button-outline"
            onClick={onClose}
            disabled={isApplying}
          >
            Cancel
          </button>
          <button
            type="button"
            className="button button-primary flex items-center gap-2"
            onClick={onConfirmApply}
            disabled={isApplying}
          >
            {isApplying ? (
              <>
                <div className="spinner-small" /> Applying...
              </>
            ) : (
              <>
                <CheckCircle2 size={16} /> Confirm & Apply to Cleaned Version
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
