import React, { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  Binary,
  CheckCircle2,
  Copy,
  Gauge,
  History,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  Undo2,
  Wand2,
} from 'lucide-react'
import {
  applyCleaningOperation,
  getCleaningHistory,
  getCleaningProfile,
  previewCleaningOperation,
  resetCleaningDataset,
  undoCleaningOperation,
} from '../../services/api'
import type {
  CleaningApplyRequest,
  CleaningPreviewRequest,
  CleaningPreviewResponse,
  DataQualityProfile,
  TransformationStep,
} from '../../types/cleaning'
import { CleaningPreviewModal } from './CleaningPreviewModal'
import { DataQualityOverview } from './DataQualityOverview'
import { DataTypeConverter } from './DataTypeConverter'
import { DuplicateManager } from './DuplicateManager'
import { MissingValueManager } from './MissingValueManager'
import { OutlierDetector } from './OutlierDetector'
import { TransformationHistory } from './TransformationHistory'

interface CleaningWorkspaceProps {
  datasetId: string
  datasetFilename: string
  onDatasetUpdated?: () => void
}

type CleaningSubTab = 'quality' | 'missing' | 'duplicates' | 'types' | 'outliers' | 'history'

export const CleaningWorkspace: React.FC<CleaningWorkspaceProps> = ({
  datasetId,
  datasetFilename,
  onDatasetUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<CleaningSubTab>('quality')
  const [profile, setProfile] = useState<DataQualityProfile | null>(null)
  const [history, setHistory] = useState<TransformationStep[]>([])
  const [currentVersion, setCurrentVersion] = useState<number>(0)
  const [selectedColumn, setSelectedColumn] = useState<string | undefined>(undefined)

  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isApplying, setIsApplying] = useState<boolean>(false)
  const [isUndoing, setIsUndoing] = useState<boolean>(false)
  const [isResetting, setIsResetting] = useState<boolean>(false)

  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successToast, setSuccessToast] = useState<string | null>(null)

  // Preview modal state
  const [activePreview, setActivePreview] = useState<CleaningPreviewResponse | null>(null)
  const [pendingApplyReq, setPendingApplyReq] = useState<CleaningApplyRequest | null>(null)

  // Load profile and history
  const loadData = useCallback(async () => {
    setIsLoading(true)
    setErrorMessage(null)
    try {
      const [profData, histData] = await Promise.all([
        getCleaningProfile(datasetId),
        getCleaningHistory(datasetId),
      ])
      setProfile(profData)
      setHistory(histData.history)
      setCurrentVersion(histData.current_version)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to load data cleaning profile'
      )
    } finally {
      setIsLoading(false)
    }
  }, [datasetId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Handle preview request from tool subcomponents
  const handlePreview = async (req: CleaningPreviewRequest) => {
    setIsApplying(true)
    setErrorMessage(null)
    try {
      const previewRes = await previewCleaningOperation(datasetId, req)
      setActivePreview(previewRes)
      setPendingApplyReq({
        operation_type: req.operation_type,
        column_name: req.column_name,
        strategy: req.strategy,
        parameters: req.parameters,
      })
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Simulation of cleaning operation failed'
      )
    } finally {
      setIsApplying(false)
    }
  }

  // Handle confirm apply
  const handleConfirmApply = async () => {
    if (!pendingApplyReq) return
    setIsApplying(true)
    setErrorMessage(null)
    try {
      const applyRes = await applyCleaningOperation(datasetId, pendingApplyReq)
      setActivePreview(null)
      setPendingApplyReq(null)
      setSuccessToast(applyRes.message || 'Transformation applied successfully!')
      setProfile(applyRes.updated_quality)
      setCurrentVersion(applyRes.version)

      // Refresh history & notify parent
      const histData = await getCleaningHistory(datasetId)
      setHistory(histData.history)
      onDatasetUpdated?.()
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to apply transformation'
      )
    } finally {
      setIsApplying(false)
    }
  }

  // Handle undo
  const handleUndo = async () => {
    setIsUndoing(true)
    setErrorMessage(null)
    try {
      const undoRes = await undoCleaningOperation(datasetId)
      setSuccessToast(undoRes.message)
      setProfile(undoRes.updated_quality)
      setCurrentVersion(undoRes.current_version)

      const histData = await getCleaningHistory(datasetId)
      setHistory(histData.history)
      onDatasetUpdated?.()
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to undo transformation')
    } finally {
      setIsUndoing(false)
    }
  }

  // Handle reset
  const handleReset = async () => {
    setIsResetting(true)
    setErrorMessage(null)
    try {
      const resetRes = await resetCleaningDataset(datasetId)
      setSuccessToast(resetRes.message)
      setProfile(resetRes.updated_quality)
      setCurrentVersion(0)
      setHistory([])
      onDatasetUpdated?.()
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to reset dataset')
    } finally {
      setIsResetting(false)
    }
  }

  const handleSelectColumnFromQuality = (colName: string) => {
    setSelectedColumn(colName)
    setActiveTab('missing')
  }

  if (isLoading && !profile) {
    return (
      <div className="tab-loading-state">
        <div className="spinner-large" />
        <p>Analyzing dataset quality and computing integrity hashes...</p>
      </div>
    )
  }

  return (
    <div className="cleaning-workspace-wrapper">
      {/* Workspace Header */}
      <div className="cleaning-workspace-header">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-neutral-100 flex items-center gap-2">
              <Wand2 size={20} className="text-purple-400" /> Data Cleaning & Transformation
            </h2>
            {profile?.is_cleaned && (
              <span className="badge-cleaned">Cleaned v{currentVersion}</span>
            )}
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Dataset: <span className="text-neutral-200 font-medium">{datasetFilename}</span>
            {currentVersion > 0 && ` • ${history.length} transformation step(s) applied`}
          </p>
        </div>

        {/* Action Pills */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="button button-outline text-xs flex items-center gap-1.5"
            onClick={handleUndo}
            disabled={isUndoing || isResetting || history.length === 0}
            title="Undo most recent transformation"
          >
            <Undo2 size={13} />
            {isUndoing ? 'Reverting...' : `Undo (${history.length})`}
          </button>
          <button
            type="button"
            className="button button-danger text-xs flex items-center gap-1.5"
            onClick={handleReset}
            disabled={isUndoing || isResetting || history.length === 0}
            title="Reset to pristine original uploaded file"
          >
            <RotateCcw size={13} />
            {isResetting ? 'Resetting...' : 'Reset to Original'}
          </button>
        </div>
      </div>

      {/* Error & Success Toasts */}
      {errorMessage && (
        <div className="error-banner flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertCircle size={16} className="text-rose-400 shrink-0" />
            <span className="text-xs text-rose-200">{errorMessage}</span>
          </div>
          <button
            type="button"
            className="toast-close-btn"
            onClick={() => setErrorMessage(null)}
          >
            ×
          </button>
        </div>
      )}

      {successToast && (
        <div className="success-toast flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
            <span className="text-xs text-emerald-200">{successToast}</span>
          </div>
          <button
            type="button"
            className="toast-close-btn"
            onClick={() => setSuccessToast(null)}
          >
            ×
          </button>
        </div>
      )}

      {/* Subtabs Navigation */}
      <div className="cleaning-subtabs-bar">
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'quality' ? 'active' : ''}`}
          onClick={() => setActiveTab('quality')}
        >
          <Gauge size={14} /> Quality Analysis
        </button>
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'missing' ? 'active' : ''}`}
          onClick={() => setActiveTab('missing')}
        >
          <Sparkles size={14} /> Missing Values ({profile?.total_missing_cells || 0})
        </button>
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'duplicates' ? 'active' : ''}`}
          onClick={() => setActiveTab('duplicates')}
        >
          <Copy size={14} /> Duplicate Rows ({profile?.duplicate_rows || 0})
        </button>
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'types' ? 'active' : ''}`}
          onClick={() => setActiveTab('types')}
        >
          <Binary size={14} /> Type Conversion
        </button>
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'outliers' ? 'active' : ''}`}
          onClick={() => setActiveTab('outliers')}
        >
          <ShieldAlert size={14} /> Outlier Treatment
        </button>
        <button
          type="button"
          className={`subtab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          <History size={14} /> Audit History ({history.length})
        </button>
      </div>

      {/* Subtab Content Area */}
      <div className="cleaning-subtab-content mt-4">
        {profile && (
          <>
            {activeTab === 'quality' && (
              <DataQualityOverview
                profile={profile}
                onSelectColumn={handleSelectColumnFromQuality}
              />
            )}

            {activeTab === 'missing' && (
              <MissingValueManager
                profile={profile}
                selectedColumn={selectedColumn}
                onPreview={handlePreview}
                isLoading={isApplying}
              />
            )}

            {activeTab === 'duplicates' && (
              <DuplicateManager
                profile={profile}
                onPreview={handlePreview}
                isLoading={isApplying}
              />
            )}

            {activeTab === 'types' && (
              <DataTypeConverter
                profile={profile}
                selectedColumn={selectedColumn}
                onPreview={handlePreview}
                isLoading={isApplying}
              />
            )}

            {activeTab === 'outliers' && (
              <OutlierDetector
                profile={profile}
                selectedColumn={selectedColumn}
                onPreview={handlePreview}
                isLoading={isApplying}
              />
            )}

            {activeTab === 'history' && (
              <TransformationHistory
                history={history}
                currentVersion={currentVersion}
                onUndo={handleUndo}
                onReset={handleReset}
                isUndoing={isUndoing}
                isResetting={isResetting}
              />
            )}
          </>
        )}
      </div>

      {/* Preview Modal */}
      <CleaningPreviewModal
        preview={activePreview}
        onClose={() => {
          setActivePreview(null)
          setPendingApplyReq(null)
        }}
        onConfirmApply={handleConfirmApply}
        isApplying={isApplying}
      />
    </div>
  )
}
