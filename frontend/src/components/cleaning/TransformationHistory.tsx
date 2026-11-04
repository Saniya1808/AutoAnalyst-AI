import React, { useState } from 'react'
import { AlertTriangle, Clock, History, RotateCcw, Undo2 } from 'lucide-react'
import type { TransformationStep } from '../../types/cleaning'

interface TransformationHistoryProps {
  history: TransformationStep[]
  currentVersion: number
  onUndo: () => void
  onReset: () => void
  isUndoing?: boolean
  isResetting?: boolean
}

export const TransformationHistory: React.FC<TransformationHistoryProps> = ({
  history,
  currentVersion,
  onUndo,
  onReset,
  isUndoing = false,
  isResetting = false,
}) => {
  const [showResetConfirm, setShowResetConfirm] = useState(false)

  return (
    <div className="cleaning-card">
      <div className="cleaning-card-header flex items-center justify-between">
        <div>
          <h3 className="cleaning-card-title flex items-center gap-2">
            <History size={18} className="text-purple-400" /> Transformation Audit History (v{currentVersion})
          </h3>
          <p className="cleaning-card-subtitle">
            Sequential log of applied transformations. All operations are reversible.
          </p>
        </div>

        {/* Global Undo & Reset Actions */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="button button-outline text-xs flex items-center gap-1.5"
            onClick={onUndo}
            disabled={isUndoing || isResetting || history.length === 0}
            title="Roll back the most recent transformation step"
          >
            <Undo2 size={14} />
            {isUndoing ? 'Reverting...' : `Undo (${history.length})`}
          </button>
          <button
            type="button"
            className="button button-danger text-xs flex items-center gap-1.5"
            onClick={() => setShowResetConfirm(true)}
            disabled={isUndoing || isResetting || history.length === 0}
            title="Discard all changes and restore original dataset"
          >
            <RotateCcw size={14} />
            {isResetting ? 'Resetting...' : 'Reset to Original'}
          </button>
        </div>
      </div>

      {/* Reset Confirmation Dialog */}
      {showResetConfirm && (
        <div className="reset-confirm-box mt-3 p-3 rounded-lg border border-rose-500/40 bg-rose-500/10 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-rose-200">
            <AlertTriangle size={16} className="text-rose-400 shrink-0" />
            <span>
              Are you sure you want to discard all {history.length} transformation(s)? The pristine original uploaded file is permanently preserved.
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0 ml-3">
            <button
              type="button"
              className="px-2 py-1 text-xs rounded bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
              onClick={() => setShowResetConfirm(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="px-2 py-1 text-xs rounded bg-rose-600 text-white font-medium hover:bg-rose-500"
              onClick={() => {
                setShowResetConfirm(false)
                onReset()
              }}
            >
              Confirm Reset
            </button>
          </div>
        </div>
      )}

      {/* History Timeline */}
      <div className="history-timeline mt-4">
        {history.length === 0 ? (
          <div className="empty-history-state text-center py-6 text-neutral-500 text-xs">
            No transformations applied yet. Dataset is in its pristine uploaded state (Version 0).
          </div>
        ) : (
          <div className="timeline-list space-y-3">
            {history
              .slice()
              .reverse()
              .map((step, idx) => (
                <div key={step.step_id} className="timeline-item">
                  <div className="timeline-marker">
                    <span className="step-num">{history.length - idx}</span>
                  </div>
                  <div className="timeline-content">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="badge-step-op">{step.operation_type}</span>
                        {step.column_name && (
                          <span className="badge-step-col font-mono text-purple-300">
                            {step.column_name}
                          </span>
                        )}
                        <span className="text-xs text-neutral-400 font-mono">
                          v{step.version}
                        </span>
                      </div>
                      <span className="text-[11px] text-neutral-500 flex items-center gap-1 font-mono">
                        <Clock size={11} /> {new Date(step.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="timeline-desc text-xs text-neutral-200 mt-1">
                      {step.description}
                    </p>
                    <div className="timeline-meta flex items-center gap-3 text-[11px] text-neutral-400 mt-1">
                      <span>Affected Rows: <b>{step.affected_rows.toLocaleString()}</b></span>
                      <span>Affected Cells: <b>{step.affected_cells.toLocaleString()}</b></span>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  )
}
