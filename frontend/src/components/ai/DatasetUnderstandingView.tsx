import React, { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  Bot,
  Clock,
  Columns,
  Database,
  FileCheck2,
  HelpCircle,
  Info,
  Lightbulb,
  RefreshCw,
  Sparkles,
  X,
} from 'lucide-react'
import { getDatasetUnderstanding, refreshDatasetUnderstanding } from '../../services/api'
import type { ComputedFact, DatasetUnderstandingResponse } from '../../types/ai'
import { ColumnUnderstandingTable } from './ColumnUnderstandingTable'
import { ExecutiveSummaryCard } from './ExecutiveSummaryCard'
import { InsightsAndObservations } from './InsightsAndObservations'
import { SuggestedQuestionsPanel } from './SuggestedQuestionsPanel'
import { UnderstandingLoadingSkeleton } from './UnderstandingLoadingSkeleton'

interface DatasetUnderstandingViewProps {
  datasetId: string
  datasetFilename: string
}

type AISubTab = 'overview' | 'insights' | 'columns' | 'analysis' | 'facts'

export const DatasetUnderstandingView: React.FC<DatasetUnderstandingViewProps> = ({
  datasetId,
  datasetFilename,
}) => {
  const [data, setData] = useState<DatasetUnderstandingResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [activeSubTab, setActiveSubTab] = useState<AISubTab>('overview')
  const [selectedFactId, setSelectedFactId] = useState<string | null>(null)

  const fetchUnderstanding = useCallback(
    async (refresh = false) => {
      if (refresh) {
        setIsRefreshing(true)
      } else {
        setIsLoading(true)
      }
      setErrorMessage(null)

      try {
        const response = refresh
          ? await refreshDatasetUnderstanding(datasetId)
          : await getDatasetUnderstanding(datasetId)
        setData(response)
      } catch (err) {
        setErrorMessage(
          err instanceof Error
            ? err.message
            : 'Failed to generate AI dataset understanding'
        )
      } finally {
        setIsLoading(false)
        setIsRefreshing(false)
      }
    },
    [datasetId]
  )

  useEffect(() => {
    fetchUnderstanding(false)
  }, [fetchUnderstanding])

  const handleSelectFact = (factId: string) => {
    setSelectedFactId(factId)
  }

  const selectedFact: ComputedFact | null =
    selectedFactId && data?.computed_facts
      ? data.computed_facts[selectedFactId] || null
      : null

  if (isLoading) {
    return <UnderstandingLoadingSkeleton />
  }

  if (errorMessage || !data) {
    return (
      <div className="ai-error-container">
        <div className="ai-error-card">
          <AlertCircle size={36} className="text-red-500" />
          <h3>AI Understanding Unavailable</h3>
          <p>{errorMessage || 'No understanding data received from backend.'}</p>
          <button
            type="button"
            className="button button-primary"
            onClick={() => fetchUnderstanding(false)}
          >
            <RefreshCw size={14} /> Retry Analysis
          </button>
        </div>
      </div>
    )
  }

  const isFallback = data.mode === 'statistical_fallback'
  const computedFactsList = Object.values(data.computed_facts || {})

  return (
    <div className="ai-workspace-container">
      {/* Top Banner / Mode & Metadata Bar */}
      <div className="ai-top-header">
        <div className="ai-header-left">
          <div className="ai-brand-badge">
            <Sparkles size={16} />
            <span>AI Dataset Understanding</span>
          </div>
          <h2 className="ai-dataset-heading">{data.filename || datasetFilename}</h2>
          <div className="ai-metadata-tags">
            {data.is_cleaned ? (
              <span className="tag-pill tag-cleaned">Cleaned (v{data.version})</span>
            ) : (
              <span className="tag-pill tag-original">Original Source</span>
            )}
            <span
              className={`tag-pill ${isFallback ? 'tag-fallback' : 'tag-ai'}`}
              title={
                isFallback
                  ? 'Using offline deterministic statistical inference engine'
                  : `Model: ${data.model} via ${data.provider}`
              }
            >
              {isFallback ? (
                <>
                  <Database size={13} /> Statistical Heuristic Engine (Offline)
                </>
              ) : (
                <>
                  <Bot size={13} /> {data.model}
                </>
              )}
            </span>
            {data.is_cached && (
              <span className="tag-pill tag-cached" title="Retrieved from cache snapshot">
                <Clock size={13} /> Cached
              </span>
            )}
            <span className="tag-pill tag-facts-count" title="Number of computed facts grounded in Pandas">
              <FileCheck2 size={13} /> {computedFactsList.length} Grounded Facts
            </span>
          </div>
        </div>

        <div className="ai-header-right">
          <button
            type="button"
            className="button button-secondary text-sm-btn"
            onClick={() => fetchUnderstanding(true)}
            disabled={isRefreshing}
            title="Force refresh understanding bypassing cache"
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            {isRefreshing ? 'Re-analyzing...' : 'Refresh AI Analysis'}
          </button>
        </div>
      </div>

      {/* Fallback Notice Banner if offline */}
      {isFallback && (
        <div className="ai-fallback-banner">
          <Info size={18} className="text-indigo-400" />
          <div className="banner-content">
            <b>Operating in Statistical Grounding Mode</b>
            <p>
              Dataset understanding is currently generated using deterministic Pandas heuristics. To
              activate full generative multi-perspective synthesis with Google Gemini, set your{' '}
              <code>GEMINI_API_KEY</code> in <code>backend/.env</code>.
            </p>
          </div>
        </div>
      )}

      {/* Subtabs Navigation */}
      <div className="ai-subtabs-bar">
        <button
          type="button"
          className={`ai-subtab-btn ${activeSubTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('overview')}
        >
          <Sparkles size={15} /> Executive Overview
        </button>
        <button
          type="button"
          className={`ai-subtab-btn ${activeSubTab === 'insights' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('insights')}
        >
          <Lightbulb size={15} /> Observations & Hypotheses (
          {data.analytical_insights.key_observations.length})
        </button>
        <button
          type="button"
          className={`ai-subtab-btn ${activeSubTab === 'columns' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('columns')}
        >
          <Columns size={15} /> Column Catalog ({data.columns.length})
        </button>
        <button
          type="button"
          className={`ai-subtab-btn ${activeSubTab === 'analysis' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('analysis')}
        >
          <HelpCircle size={15} /> KPIs & Questions (
          {data.suggested_analysis.suggested_questions.length})
        </button>
        <button
          type="button"
          className={`ai-subtab-btn ${activeSubTab === 'facts' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('facts')}
        >
          <FileCheck2 size={15} /> Grounded Facts Inspector ({computedFactsList.length})
        </button>
      </div>

      {/* Tab Content */}
      <div className="ai-tab-body">
        {activeSubTab === 'overview' && (
          <ExecutiveSummaryCard
            overview={data.overview}
            computedFacts={data.computed_facts}
            onSelectFact={handleSelectFact}
          />
        )}

        {activeSubTab === 'insights' && (
          <InsightsAndObservations
            insights={data.analytical_insights}
            computedFacts={data.computed_facts}
            onSelectFact={handleSelectFact}
          />
        )}

        {activeSubTab === 'columns' && (
          <ColumnUnderstandingTable
            columns={data.columns}
            computedFacts={data.computed_facts}
            onSelectFact={handleSelectFact}
          />
        )}

        {activeSubTab === 'analysis' && (
          <SuggestedQuestionsPanel analysis={data.suggested_analysis} />
        )}

        {activeSubTab === 'facts' && (
          <div className="ai-section-card">
            <h3 className="ai-subheading">
              <FileCheck2 size={18} className="text-emerald-500" /> Grounded Empirical Facts Catalog
            </h3>
            <p className="ai-subheading-desc">
              Every numerical claim and distribution statement is computed by Pandas and assigned a
              permanent fact identifier to prevent AI hallucination.
            </p>

            <div className="facts-inspector-grid">
              {computedFactsList.map((fact) => (
                <div
                  key={fact.fact_id}
                  className={`fact-card ${selectedFactId === fact.fact_id ? 'fact-card-active' : ''}`}
                  onClick={() => setSelectedFactId(fact.fact_id)}
                >
                  <div className="fact-card-header">
                    <span className="fact-id-badge">#{fact.fact_id}</span>
                    <span className="fact-cat-badge">{fact.category}</span>
                    {fact.column_name && (
                      <code className="fact-col-badge">{fact.column_name}</code>
                    )}
                  </div>
                  <p className="fact-statement">{fact.formatted_statement}</p>
                  <div className="fact-metric-row">
                    <span className="metric-label">{fact.metric_name}:</span>
                    <span className="metric-value">
                      {typeof fact.value === 'object'
                        ? JSON.stringify(fact.value)
                        : String(fact.value)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Grounded Fact Modal / Drawer */}
      {selectedFact && (
        <div className="fact-modal-backdrop" onClick={() => setSelectedFactId(null)}>
          <div className="fact-modal" onClick={(e) => e.stopPropagation()}>
            <div className="fact-modal-header">
              <div className="fact-modal-title">
                <FileCheck2 size={18} className="text-emerald-500" />
                <span>Grounded Fact Details</span>
                <span className="fact-modal-id">#{selectedFact.fact_id}</span>
              </div>
              <button
                type="button"
                className="fact-modal-close"
                onClick={() => setSelectedFactId(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="fact-modal-body">
              <div className="fact-detail-row">
                <span className="detail-label">Category:</span>
                <span className="detail-value">{selectedFact.category}</span>
              </div>
              {selectedFact.column_name && (
                <div className="fact-detail-row">
                  <span className="detail-label">Target Column:</span>
                  <code className="detail-value">{selectedFact.column_name}</code>
                </div>
              )}
              <div className="fact-detail-row">
                <span className="detail-label">Metric Name:</span>
                <span className="detail-value">{selectedFact.metric_name}</span>
              </div>
              <div className="fact-detail-statement">
                <span className="detail-label">Empirical Statement:</span>
                <p>{selectedFact.formatted_statement}</p>
              </div>
              <div className="fact-detail-raw">
                <span className="detail-label">Pandas Computed Value:</span>
                <pre>{JSON.stringify(selectedFact.value, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
