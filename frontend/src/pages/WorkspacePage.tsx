import React, { Suspense, useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart3,
  CheckCircle2,
  Columns,
  Eye,
  FileSpreadsheet,
  FileText,
  Info,
  MessageSquare,
  Sparkles,
  Wand2,
} from 'lucide-react'
import { CleaningWorkspace } from '../components/cleaning/CleaningWorkspace'
import { DashboardOverview } from '../components/dashboard/DashboardOverview'
import { DatasetUnderstandingView } from '../components/ai/DatasetUnderstandingView'
import { AskYourDataView } from '../components/ask/AskYourDataView'
import { AutomatedInsightsView } from '../components/insights/AutomatedInsightsView'
const ExecutiveReportsView = React.lazy(() =>
  import('../components/reports/ExecutiveReportsView').then((m) => ({
    default: m.ExecutiveReportsView,
  }))
)
import { ColumnProfileView } from '../components/workspace/ColumnProfileView'
import { DatasetOverviewCard } from '../components/workspace/DatasetOverviewCard'
import { DatasetPreviewTable } from '../components/workspace/DatasetPreviewTable'
import { DatasetSelector } from '../components/workspace/DatasetSelector'
import { MetricsSummary } from '../components/workspace/MetricsSummary'
import { RecentActivityPanel } from '../components/workspace/RecentActivityPanel'
import { WelcomeBanner } from '../components/workspace/WelcomeBanner'
import { WorkspaceSidebar } from '../components/workspace/WorkspaceSidebar'
import { WorkspaceTopBar } from '../components/workspace/WorkspaceTopBar'
import {
  deleteDataset,
  getDataset,
  getDatasetPreview,
  listDatasets,
  uploadDataset,
} from '../services/api'
import type { DatasetDetail, DatasetOverview } from '../types/dataset'

interface WorkspacePageProps {
  onNavigateHome: () => void
}

type DatasetTab = 'overview' | 'columns' | 'preview' | 'dashboard' | 'cleaning' | 'insights' | 'understanding' | 'ask' | 'reports'

export const WorkspacePage: React.FC<WorkspacePageProps> = ({ onNavigateHome }) => {
  const [activeSection, setActiveSection] = useState('overview')
  const [datasets, setDatasets] = useState<DatasetOverview[]>([])
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(null)
  const [activeDataset, setActiveDataset] = useState<DatasetDetail | null>(null)
  const [activeTab, setActiveTab] = useState<DatasetTab>('overview')

  const [isUploading, setIsUploading] = useState(false)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [isLoadingPreviewPage, setIsLoadingPreviewPage] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successToast, setSuccessToast] = useState<string | null>(null)

  // Load existing datasets on mount
  const loadDatasets = useCallback(async () => {
    try {
      const response = await listDatasets()
      setDatasets(response.datasets)

      if (response.datasets.length > 0 && !activeDatasetId) {
        const firstId = response.datasets[0].id
        setActiveDatasetId(firstId)
        loadDatasetDetail(firstId)
      }
    } catch {
      // Backend may be offline or starting up
    }
  }, [activeDatasetId])

  useEffect(() => {
    loadDatasets()
  }, [])

  // Load full detail for active dataset
  const loadDatasetDetail = async (id: string) => {
    setIsLoadingDetail(true)
    try {
      const detail = await getDataset(id)
      setActiveDataset(detail)
      setActiveDatasetId(id)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to load dataset details'
      )
    } finally {
      setIsLoadingDetail(false)
    }
  }

  // Handle dataset selection
  const handleSelectDataset = (id: string) => {
    if (id !== activeDatasetId) {
      loadDatasetDetail(id)
    }
  }

  // Handle file upload
  const handleUploadFile = async (file: File) => {
    setIsUploading(true)
    setErrorMessage(null)
    setSuccessToast(null)

    try {
      const detail = await uploadDataset(file)
      // Prepend to dataset list
      setDatasets((prev) => [
        detail.overview,
        ...prev.filter((d) => d.id !== detail.overview.id),
      ])
      setActiveDatasetId(detail.overview.id)
      setActiveDataset(detail)
      setActiveTab('overview')

      setSuccessToast(
        `Successfully uploaded and profiled "${detail.overview.filename}" (${detail.overview.row_count.toLocaleString()} rows, ${detail.overview.column_count} columns)`
      )

      // Clear success toast after 6 seconds
      setTimeout(() => {
        setSuccessToast(null)
      }, 6000)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'An error occurred during file upload'
      )
    } finally {
      setIsUploading(false)
    }
  }

  // Handle dataset deletion
  const handleDeleteDataset = async (id: string) => {
    setIsDeleting(true)
    try {
      await deleteDataset(id)
      const remaining = datasets.filter((d) => d.id !== id)
      setDatasets(remaining)

      if (activeDatasetId === id) {
        if (remaining.length > 0) {
          const nextId = remaining[0].id
          setActiveDatasetId(nextId)
          loadDatasetDetail(nextId)
        } else {
          setActiveDatasetId(null)
          setActiveDataset(null)
        }
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to delete dataset'
      )
    } finally {
      setIsDeleting(false)
    }
  }

  // Handle preview pagination
  const handlePreviewPageChange = async (newOffset: number) => {
    if (!activeDatasetId || !activeDataset) return
    setIsLoadingPreviewPage(true)
    try {
      const newPreview = await getDatasetPreview(activeDatasetId, newOffset, 50)
      setActiveDataset({
        ...activeDataset,
        preview: newPreview,
      })
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to fetch preview rows'
      )
    } finally {
      setIsLoadingPreviewPage(false)
    }
  }

  const totalRowsAll = datasets.reduce((sum, d) => sum + d.row_count, 0)

  return (
    <motion.main
      key="workspace"
      className="workspace section-wrap"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35 }}
    >
      <WorkspaceSidebar
        activeSection={activeSection}
        onSelectSection={setActiveSection}
        onNavigateHome={onNavigateHome}
      />

      <section className="workspace-main">
        <WorkspaceTopBar />

        {/* Global Success Notification Toast */}
        {successToast && (
          <div className="success-toast-banner">
            <CheckCircle2 size={16} />
            <span>{successToast}</span>
            <button
              type="button"
              className="toast-close-btn"
              onClick={() => setSuccessToast(null)}
            >
              ×
            </button>
          </div>
        )}

        {/* SECTION: Overview (Default) */}
        {activeSection === 'overview' && (
          <>
            <WelcomeBanner
              isUploading={isUploading}
              errorMessage={errorMessage}
              onClearError={() => setErrorMessage(null)}
              onUploadFile={handleUploadFile}
            />

            <MetricsSummary
              totalDatasets={datasets.length}
              totalRowsAll={totalRowsAll}
              activeDataset={activeDataset}
            />

            {datasets.length > 0 && (
              <DatasetSelector
                datasets={datasets}
                activeDatasetId={activeDatasetId}
                onSelectDataset={handleSelectDataset}
                onDeleteDataset={handleDeleteDataset}
                isDeleting={isDeleting}
              />
            )}

            {/* Active Dataset Inspection Area */}
            {activeDataset && (
              <div className="dataset-tabs-container">
                <div className="dataset-tabs-header">
                  <div className="tab-buttons-group">
                    <button
                      type="button"
                      className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
                      onClick={() => setActiveTab('overview')}
                    >
                      <Info size={15} /> Dataset Overview
                    </button>
                    <button
                      type="button"
                      className={`tab-btn ${activeTab === 'columns' ? 'active' : ''}`}
                      onClick={() => setActiveTab('columns')}
                    >
                      <Columns size={15} /> Schema & Columns ({activeDataset.columns.length})
                    </button>
                    <button
                      type="button"
                      className={`tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
                      onClick={() => setActiveTab('preview')}
                    >
                      <Eye size={15} /> Data Preview ({activeDataset.overview.row_count.toLocaleString()})
                    </button>
                    <button
                      type="button"
                      className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
                      onClick={() => setActiveTab('dashboard')}
                    >
                      <BarChart3 size={15} /> Visual Dashboard
                    </button>
                    <button
                      type="button"
                      className={`tab-btn ${activeTab === 'cleaning' ? 'active' : ''}`}
                      onClick={() => setActiveTab('cleaning')}
                    >
                      <Wand2 size={15} /> Data Cleaning
                    </button>
                    <button
                      type="button"
                      className={`tab-btn ${activeTab === 'insights' ? 'active' : ''}`}
                      onClick={() => setActiveTab('insights')}
                    >
                      <Sparkles size={15} /> Automated Insights
                    </button>
                    <button
                      type="button"
                      className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
                      onClick={() => setActiveTab('reports')}
                    >
                      <FileText size={15} /> Executive Reports
                    </button>
                    <button
                      type="button"
                      className={`tab-btn ${activeTab === 'understanding' ? 'active' : ''}`}
                      onClick={() => setActiveTab('understanding')}
                    >
                      <Sparkles size={15} /> AI Understanding
                    </button>
                    <button
                      type="button"
                      className={`tab-btn ${activeTab === 'ask' ? 'active' : ''}`}
                      onClick={() => setActiveTab('ask')}
                    >
                      <MessageSquare size={15} /> Ask Your Data
                    </button>
                  </div>
                </div>

                <div className="tab-content-area">
                  {isLoadingDetail ? (
                    <div className="tab-loading-state">
                      <div className="spinner-large" />
                      <p>Loading dataset profile...</p>
                    </div>
                  ) : (
                    <>
                      {activeTab === 'overview' && (
                        <DatasetOverviewCard overview={activeDataset.overview} />
                      )}

                      {activeTab === 'columns' && (
                        <ColumnProfileView columns={activeDataset.columns} />
                      )}

                      {activeTab === 'preview' && (
                        <DatasetPreviewTable
                          preview={activeDataset.preview}
                          isLoadingPage={isLoadingPreviewPage}
                          onPageChange={handlePreviewPageChange}
                        />
                      )}

                      {activeTab === 'dashboard' && (
                        <DashboardOverview
                          datasetId={activeDataset.overview.id}
                          datasetFilename={activeDataset.overview.filename}
                        />
                      )}

                      {activeTab === 'cleaning' && (
                        <CleaningWorkspace
                          datasetId={activeDataset.overview.parent_id || activeDataset.overview.id}
                          datasetFilename={activeDataset.overview.filename}
                          onDatasetUpdated={loadDatasets}
                        />
                      )}

                      {activeTab === 'insights' && (
                        <AutomatedInsightsView
                          datasetId={activeDataset.overview.id}
                          datasetFilename={activeDataset.overview.filename}
                        />
                      )}

                      {activeTab === 'reports' && (
                        <Suspense
                          fallback={
                            <div className="tab-loading-state">
                              <div className="spinner-large" />
                              <p>Loading Executive Reports...</p>
                            </div>
                          }
                        >
                          <ExecutiveReportsView
                            datasetId={activeDataset.overview.id}
                            datasetFilename={activeDataset.overview.filename}
                          />
                        </Suspense>
                      )}

                      {activeTab === 'understanding' && (
                        <DatasetUnderstandingView
                          datasetId={activeDataset.overview.id}
                          datasetFilename={activeDataset.overview.filename}
                        />
                      )}

                      {activeTab === 'ask' && (
                        <AskYourDataView
                          datasetId={activeDataset.overview.id}
                          datasetFilename={activeDataset.overview.filename}
                          isCleaned={activeDataset.overview.is_cleaned}
                          version={activeDataset.overview.version}
                        />
                      )}
                    </>
                  )}
                </div>
              </div>
            )}

            <RecentActivityPanel
              datasets={datasets}
              activeDatasetId={activeDatasetId}
              onSelectDataset={handleSelectDataset}
              onTriggerUpload={() => document.getElementById('file-upload')?.click()}
            />
          </>
        )}

        {/* SECTION: My Datasets */}
        {activeSection === 'datasets' && (
          <div className="section-panel">
            <div className="section-panel-header">
              <div>
                <h2>My Datasets</h2>
                <p>Manage all uploaded datasets, inspect metadata, or remove old records.</p>
              </div>
              <button
                type="button"
                className="button button-primary"
                onClick={() => document.getElementById('file-upload')?.click()}
              >
                Upload new dataset
              </button>
            </div>

            {datasets.length === 0 ? (
              <div className="empty-state">
                <FileSpreadsheet size={28} />
                <b>No datasets uploaded</b>
                <span>Upload a CSV or Excel file to get started.</span>
              </div>
            ) : (
              <div className="datasets-management-list">
                {datasets.map((d) => (
                  <div key={d.id} className="dataset-manage-card">
                    <div className="manage-card-left">
                      <div className="manage-icon">
                        <FileSpreadsheet size={20} />
                      </div>
                      <div>
                        <h4>{d.filename}</h4>
                        <p>
                          <span>{d.file_type.toUpperCase()}</span> •{' '}
                          <span>{d.row_count.toLocaleString()} rows</span> •{' '}
                          <span>{d.column_count} columns</span> •{' '}
                          <span>{d.memory_usage_human}</span>
                        </p>
                      </div>
                    </div>

                    <div className="manage-card-actions">
                      <button
                        type="button"
                        className="button button-secondary text-sm-btn"
                        onClick={() => {
                          handleSelectDataset(d.id)
                          setActiveSection('overview')
                        }}
                      >
                        Inspect & Profile
                      </button>
                      <button
                        type="button"
                        className="button button-secondary text-sm-btn"
                        onClick={() => {
                          handleSelectDataset(d.id)
                          setActiveSection('dashboards')
                        }}
                      >
                        Open Dashboard
                      </button>
                      <button
                        type="button"
                        className="button button-secondary text-sm-btn"
                        onClick={() => {
                          handleSelectDataset(d.id)
                          setActiveSection('analysis')
                        }}
                      >
                        AI Insights
                      </button>
                      <button
                        type="button"
                        className="button button-secondary text-sm-btn"
                        onClick={() => {
                          handleSelectDataset(d.id)
                          setActiveSection('ask')
                        }}
                      >
                        Ask Data
                      </button>
                      <button
                        type="button"
                        className="button button-secondary text-sm-btn"
                        onClick={() => {
                          handleSelectDataset(d.id)
                          setActiveSection('reports')
                        }}
                      >
                        Executive Report
                      </button>
                      <button
                        type="button"
                        className="button button-danger text-sm-btn"
                        onClick={() => {
                          if (
                            window.confirm(
                              `Delete dataset "${d.filename}"? This cannot be undone.`
                            )
                          ) {
                            handleDeleteDataset(d.id)
                          }
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION: Data Cleaning (Phase 3 Live!) */}
        {activeSection === 'cleaning' && (
          <div className="cleaning-section-wrapper">
            {activeDataset ? (
              <CleaningWorkspace
                datasetId={activeDataset.overview.parent_id || activeDataset.overview.id}
                datasetFilename={activeDataset.overview.filename}
                onDatasetUpdated={loadDatasets}
              />
            ) : datasets.length > 0 ? (
              <CleaningWorkspace
                datasetId={datasets[0].parent_id || datasets[0].id}
                datasetFilename={datasets[0].filename}
                onDatasetUpdated={loadDatasets}
              />
            ) : (
              <div className="section-panel text-center-panel">
                <Wand2 size={40} className="text-muted-icon" />
                <h3>No Dataset Selected for Cleaning</h3>
                <p>
                  Please upload or select a CSV or Excel dataset to begin intelligent data cleaning.
                </p>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    setActiveSection('overview')
                    document.getElementById('file-upload')?.click()
                  }}
                >
                  Upload Dataset
                </button>
              </div>
            )}
          </div>
        )}

        {/* SECTION: Visual Dashboards (Phase 2.2 Live!) */}
        {activeSection === 'dashboards' && (
          <div className="dashboard-section-wrapper">
            {activeDataset ? (
              <DashboardOverview
                datasetId={activeDataset.overview.id}
                datasetFilename={activeDataset.overview.filename}
              />
            ) : datasets.length > 0 ? (
              <DashboardOverview
                datasetId={datasets[0].id}
                datasetFilename={datasets[0].filename}
              />
            ) : (
              <div className="section-panel text-center-panel">
                <BarChart3 size={40} className="text-muted-icon" />
                <h3>No Dataset Selected for Dashboard</h3>
                <p>
                  Please upload or select a CSV or Excel dataset to automatically
                  generate interactive visual dashboards.
                </p>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    setActiveSection('overview')
                    document.getElementById('file-upload')?.click()
                  }}
                >
                  Upload Dataset
                </button>
              </div>
            )}
          </div>
        )}

        {/* SECTION: Automated Insights & Business Intelligence (Phase 4.3 Live!) */}
        {activeSection === 'insights' && (
          <div className="insights-section-wrapper">
            {activeDataset ? (
              <AutomatedInsightsView
                datasetId={activeDataset.overview.id}
                datasetFilename={activeDataset.overview.filename}
              />
            ) : datasets.length > 0 ? (
              <AutomatedInsightsView
                datasetId={datasets[0].id}
                datasetFilename={datasets[0].filename}
              />
            ) : (
              <div className="section-panel text-center-panel">
                <Sparkles size={40} className="text-muted-icon" />
                <h3>No Dataset Selected for Automated Insights</h3>
                <p>
                  Please upload or select a CSV or Excel dataset to discover automated statistical findings,
                  category benchmarks, and actionable recommendations.
                </p>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    setActiveSection('overview')
                    document.getElementById('file-upload')?.click()
                  }}
                >
                  Upload Dataset
                </button>
              </div>
            )}
          </div>
        )}

        {/* SECTION: Ask Your Data (Phase 4.2 Live!) */}
        {activeSection === 'ask' && (
          <div className="ask-section-wrapper">
            {activeDataset ? (
              <AskYourDataView
                datasetId={activeDataset.overview.id}
                datasetFilename={activeDataset.overview.filename}
                isCleaned={activeDataset.overview.is_cleaned}
                version={activeDataset.overview.version}
              />
            ) : datasets.length > 0 ? (
              <AskYourDataView
                datasetId={datasets[0].id}
                datasetFilename={datasets[0].filename}
                isCleaned={datasets[0].is_cleaned}
                version={datasets[0].version}
              />
            ) : (
              <div className="section-panel text-center-panel">
                <MessageSquare size={40} className="text-muted-icon" />
                <h3>No Dataset Selected</h3>
                <p>
                  Please upload or select a CSV or Excel dataset to ask natural language questions.
                </p>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    setActiveSection('overview')
                    document.getElementById('file-upload')?.click()
                  }}
                >
                  Upload Dataset
                </button>
              </div>
            )}
          </div>
        )}

        {/* SECTION: AI Analysis (Phase 4.1 Live!) */}
        {activeSection === 'analysis' && (
          <div className="ai-section-wrapper">
            {activeDataset ? (
              <DatasetUnderstandingView
                datasetId={activeDataset.overview.id}
                datasetFilename={activeDataset.overview.filename}
              />
            ) : datasets.length > 0 ? (
              <DatasetUnderstandingView
                datasetId={datasets[0].id}
                datasetFilename={datasets[0].filename}
              />
            ) : (
              <div className="section-panel text-center-panel">
                <Sparkles size={40} className="text-muted-icon" />
                <h3>No Dataset Selected for AI Understanding</h3>
                <p>
                  Please upload or select a CSV or Excel dataset to generate autonomous AI-powered
                  dataset explanations, domain synthesis, and exploratory questions.
                </p>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    setActiveSection('overview')
                    document.getElementById('file-upload')?.click()
                  }}
                >
                  Upload Dataset
                </button>
              </div>
            )}
          </div>
        )}

        {/* SECTION: Executive Reports (Phase 4.5 Live!) */}
        {activeSection === 'reports' && (
          <div className="reports-section-wrapper">
            <Suspense
              fallback={
                <div className="tab-loading-state">
                  <div className="spinner-large" />
                  <p>Loading Executive Reports...</p>
                </div>
              }
            >
              {activeDataset ? (
                <ExecutiveReportsView
                  datasetId={activeDataset.overview.id}
                  datasetFilename={activeDataset.overview.filename}
                />
              ) : datasets.length > 0 ? (
                <ExecutiveReportsView
                  datasetId={datasets[0].id}
                  datasetFilename={datasets[0].filename}
                />
              ) : (
                <div className="section-panel text-center-panel">
                  <FileText size={40} className="text-muted-icon" />
                  <h3>No Dataset Selected for Executive Reports</h3>
                  <p>
                    Please upload or select a CSV or Excel dataset to generate publication-grade executive reports, PDF downloads, and multi-sheet Excel workbooks.
                  </p>
                  <button
                    type="button"
                    className="button button-primary"
                    onClick={() => {
                      setActiveSection('overview')
                      document.getElementById('file-upload')?.click()
                    }}
                  >
                    Upload Dataset
                  </button>
                </div>
              )}
            </Suspense>
          </div>
        )}
      </section>
    </motion.main>
  )
}
