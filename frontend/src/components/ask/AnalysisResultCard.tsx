import React, { useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  BarChart2,
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  FileCheck2,
  Info,
  Table,
} from 'lucide-react'
import { InteractiveChart } from '../dashboard/InteractiveChart'
import type { ChatMessage, QueryResultFact } from '../../types/ask'

interface AnalysisResultCardProps {
  message: ChatMessage
  onSelectPrompt?: (prompt: string) => void
  onSelectFact?: (fact: QueryResultFact) => void
}

export const AnalysisResultCard: React.FC<AnalysisResultCardProps> = ({
  message,
  onSelectPrompt,
  onSelectFact,
}) => {
  const hasChart = Boolean(message.chart && message.chart.chart_type)
  const hasTable = Boolean(message.tabular_data && message.tabular_data.length > 0)
  const columns = hasTable ? Object.keys(message.tabular_data[0]) : []

  const [viewMode, setViewMode] = useState<'chart' | 'table'>(hasChart ? 'chart' : 'table')
  const [showMethodology, setShowMethodology] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    const textToCopy = message.direct_answer || message.content
    navigator.clipboard.writeText(textToCopy)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const renderCellContent = (value: unknown) => {
    if (typeof value === 'number') {
      return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })
    }
    const strVal = String(value ?? '—')
    if (strVal.startsWith('http://') || strVal.startsWith('https://')) {
      return (
        <a
          href={strVal}
          target="_blank"
          rel="noopener noreferrer"
          className="table-cell-link text-indigo-400 hover:text-indigo-300 underline truncate max-w-xs inline-block"
          title={strVal}
        >
          {strVal.length > 35 ? `${strVal.slice(0, 32)}...` : strVal}
        </a>
      )
    }
    return strVal
  }

  return (
    <div className="analysis-result-card">
      {/* Direct Answer Paragraph */}
      <div className="result-answer-row">
        <p className="direct-answer-text">{message.direct_answer || message.content}</p>
        <button
          type="button"
          className={`copy-answer-btn ${copied ? 'copied' : ''}`}
          onClick={handleCopy}
          title="Copy answer to clipboard"
        >
          {copied ? (
            <>
              <Check size={13} /> Copied
            </>
          ) : (
            <>
              <Copy size={13} /> Copy
            </>
          )}
        </button>
      </div>

      {/* Primary Metric Badge Card if available */}
      {message.primary_metric && (
        <div className="primary-metric-badge-box">
          <span className="metric-badge-label">{message.primary_metric.label}</span>
          <span className="metric-badge-value">{message.primary_metric.formatted}</span>
        </div>
      )}

      {/* Chart & Table Dual View Section */}
      {(hasChart || hasTable) && (
        <div className="dual-view-container">
          <div className="dual-view-header">
            <span className="dual-view-title">
              {hasChart && hasTable ? 'Calculated Visualization & Data' : (hasChart ? 'Visualization' : 'Computed Data')}
            </span>
            {hasChart && hasTable && (
              <div className="view-toggle-buttons">
                <button
                  type="button"
                  className={`toggle-btn ${viewMode === 'chart' ? 'active' : ''}`}
                  onClick={() => setViewMode('chart')}
                >
                  <BarChart2 size={13} /> Chart
                </button>
                <button
                  type="button"
                  className={`toggle-btn ${viewMode === 'table' ? 'active' : ''}`}
                  onClick={() => setViewMode('table')}
                >
                  <Table size={13} /> Table ({message.tabular_data.length})
                </button>
              </div>
            )}
          </div>

          <div className="dual-view-body">
            {viewMode === 'chart' && message.chart && (
              <div className="chart-render-wrapper">
                <InteractiveChart chart={message.chart} height={320} />
              </div>
            )}

            {(viewMode === 'table' || !hasChart) && hasTable && (
              <div className="table-render-wrapper">
                <table className="analysis-data-table">
                  <thead>
                    <tr>
                      {columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {message.tabular_data.map((row, idx) => (
                      <tr key={idx}>
                        {columns.map((col) => (
                          <td key={col}>
                            {renderCellContent(row[col])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Limitations / Caveats Box */}
      {message.limitations_and_warnings && message.limitations_and_warnings.length > 0 && (
        <div className="limitations-alert-box">
          <AlertTriangle size={14} className="text-amber-500 shrink-0" />
          <div className="limitations-content">
            <b>Calculation Caveats:</b>
            <ul>
              {message.limitations_and_warnings.map((lim, idx) => (
                <li key={idx}>{lim}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Grounded Fact Tags */}
      {message.grounded_facts && message.grounded_facts.length > 0 && (
        <div className="grounded-facts-chips-row">
          <span className="facts-prefix">
            <FileCheck2 size={13} className="text-emerald-500" /> Verified Facts:
          </span>
          {message.grounded_facts.map((fact) => (
            <button
              key={fact.fact_id}
              type="button"
              className="fact-chip-btn"
              title={fact.formatted_statement}
              onClick={() => onSelectFact?.(fact)}
            >
              #{fact.fact_id} ({fact.metric_name})
            </button>
          ))}
        </div>
      )}

      {/* Calculation Methodology Accordion */}
      {message.calculation_method && (
        <div className="methodology-accordion">
          <button
            type="button"
            className="methodology-toggle-btn"
            onClick={() => setShowMethodology(!showMethodology)}
          >
            <Info size={13} />
            <span>Calculation Methodology & Columns</span>
            {showMethodology ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showMethodology && (
            <div className="methodology-details">
              <p><b>Method:</b> {message.calculation_method}</p>
              {message.columns_used && message.columns_used.length > 0 && (
                <p><b>Columns Used:</b> {message.columns_used.map((c) => <code key={c}>{c}</code>)}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Suggested Follow-up Prompt Chips */}
      {message.suggested_follow_ups && message.suggested_follow_ups.length > 0 && (
        <div className="follow-ups-container">
          <span className="follow-ups-label">Suggested follow-ups:</span>
          <div className="follow-ups-list">
            {message.suggested_follow_ups.map((q, idx) => (
              <button
                key={idx}
                type="button"
                className="follow-up-chip"
                onClick={() => onSelectPrompt?.(q)}
              >
                <span>{q}</span>
                <ArrowRight size={12} />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
