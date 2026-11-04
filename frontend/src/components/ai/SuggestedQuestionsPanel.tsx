import React, { useState } from 'react'
import {
  BarChart,
  Calculator,
  Check,
  Copy,
  HelpCircle,
} from 'lucide-react'
import type { SuggestedAnalysisAI } from '../../types/ai'

interface SuggestedQuestionsPanelProps {
  analysis: SuggestedAnalysisAI
}

export const SuggestedQuestionsPanel: React.FC<SuggestedQuestionsPanelProps> = ({
  analysis,
}) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

  const handleCopyQuestion = (question: string, index: number) => {
    navigator.clipboard.writeText(question)
    setCopiedIndex(index)
    setTimeout(() => {
      setCopiedIndex(null)
    }, 2000)
  }

  const kpis = analysis.suggested_kpis || []
  const charts = analysis.recommended_charts || []
  const questions = analysis.suggested_questions || []

  return (
    <div className="ai-suggested-analysis-container">
      {/* Suggested KPIs */}
      {kpis.length > 0 && (
        <div className="ai-section-card">
          <h3 className="ai-subheading">
            <Calculator size={18} className="text-emerald-500" /> Recommended Analytical KPIs
          </h3>
          <p className="ai-subheading-desc">
            Standard domain metrics and aggregated indicators tailored to this dataset.
          </p>

          <div className="kpi-cards-grid">
            {kpis.map((kpi, idx) => (
              <div key={idx} className="kpi-card">
                <div className="kpi-header">
                  <span className="kpi-name">{kpi.name}</span>
                  {kpi.target_column && (
                    <code className="kpi-target-col">{kpi.target_column}</code>
                  )}
                </div>
                <div className="kpi-calc">
                  <span className="calc-label">Formula:</span>
                  <code>{kpi.calculation}</code>
                </div>
                <p className="kpi-purpose">{kpi.purpose}</p>
                <div className="kpi-business-val">
                  <span className="value-label">Business Value:</span> {kpi.business_value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Visualizations */}
      {charts.length > 0 && (
        <div className="ai-section-card">
          <h3 className="ai-subheading">
            <BarChart size={18} className="text-violet-500" /> Recommended Visualizations
          </h3>
          <p className="ai-subheading-desc">
            Charts designed to reveal distributions, correlations, and comparative segments.
          </p>

          <div className="charts-recommendations-grid">
            {charts.map((ch, idx) => (
              <div key={idx} className="chart-rec-card">
                <div className="chart-rec-header">
                  <span className={`chart-type-pill chart-${ch.chart_type.toLowerCase()}`}>
                    {ch.chart_type.toUpperCase()}
                  </span>
                  <span className="chart-rec-title">{ch.title}</span>
                </div>
                <div className="chart-axes">
                  {ch.x_column && (
                    <span className="axis-item">
                      <b>X:</b> <code>{ch.x_column}</code>
                    </span>
                  )}
                  {ch.y_column && (
                    <span className="axis-item">
                      <b>Y:</b> <code>{ch.y_column}</code>
                    </span>
                  )}
                  {ch.aggregation && (
                    <span className="axis-item">
                      <b>Agg:</b> <code>{ch.aggregation}</code>
                    </span>
                  )}
                </div>
                <p className="chart-rec-reason">{ch.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Exploratory Questions */}
      <div className="ai-section-card">
        <h3 className="ai-subheading">
          <HelpCircle size={18} className="text-amber-500" /> Exploratory Business Questions ({questions.length})
        </h3>
        <p className="ai-subheading-desc">
          Strategic inquiries to investigate in visual dashboards and analytical drill-downs. Click to copy.
        </p>

        <div className="questions-list">
          {questions.length === 0 ? (
            <div className="empty-substate">No questions generated.</div>
          ) : (
            questions.map((q, idx) => {
              const isCopied = copiedIndex === idx
              return (
                <div key={idx} className="question-item">
                  <div className="question-number">{idx + 1}</div>
                  <div className="question-text">{q}</div>
                  <button
                    type="button"
                    className={`copy-question-btn ${isCopied ? 'copied' : ''}`}
                    onClick={() => handleCopyQuestion(q, idx)}
                    title="Copy question text"
                  >
                    {isCopied ? (
                      <>
                        <Check size={14} /> Copied
                      </>
                    ) : (
                      <>
                        <Copy size={14} /> Copy
                      </>
                    )}
                  </button>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
