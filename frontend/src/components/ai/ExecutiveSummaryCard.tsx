import React from 'react'
import {
  Briefcase,
  Compass,
  FileCheck2,
  Sparkles,
  Target,
} from 'lucide-react'
import type { ComputedFact, DatasetOverviewAI } from '../../types/ai'

interface ExecutiveSummaryCardProps {
  overview: DatasetOverviewAI
  computedFacts: Record<string, ComputedFact>
  onSelectFact?: (factId: string) => void
}

export const ExecutiveSummaryCard: React.FC<ExecutiveSummaryCardProps> = ({
  overview,
  computedFacts,
  onSelectFact,
}) => {
  const targetVar = overview.detected_target_variable

  return (
    <div className="ai-executive-card">
      <div className="ai-card-header">
        <div className="ai-domain-badge">
          <Briefcase size={16} />
          <span>{overview.domain}</span>
        </div>
        <div className="ai-grounded-indicator" title="All numbers verified against Pandas calculations">
          <FileCheck2 size={14} />
          <span>Pandas Verified Facts</span>
        </div>
      </div>

      <div className="ai-summary-body">
        <div className="ai-summary-section">
          <div className="ai-section-title">
            <Compass size={16} />
            <span>Likely Purpose</span>
          </div>
          <p className="ai-purpose-text">{overview.likely_purpose}</p>
        </div>

        <div className="ai-summary-section">
          <div className="ai-section-title">
            <Sparkles size={16} />
            <span>Executive Summary</span>
          </div>
          <p className="ai-executive-text">{overview.executive_summary}</p>
          {overview.referenced_fact_ids.length > 0 && (
            <div className="ai-facts-pills">
              <span className="facts-label">Grounded Facts:</span>
              {overview.referenced_fact_ids.map((fid) => {
                const fact = computedFacts[fid]
                return (
                  <button
                    key={fid}
                    type="button"
                    className="fact-pill"
                    title={fact?.formatted_statement || fid}
                    onClick={() => onSelectFact?.(fid)}
                  >
                    #{fid}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {targetVar && targetVar.column_name && targetVar.column_name.toLowerCase() !== 'none' && (
          <div className="ai-target-variable-box">
            <div className="target-var-header">
              <div className="target-var-title">
                <Target size={16} />
                <span>Detected Target Variable:</span>
                <code className="target-var-name">{targetVar.column_name}</code>
              </div>
              <span
                className={`confidence-badge confidence-${targetVar.confidence.toLowerCase()}`}
              >
                {targetVar.confidence.toUpperCase()} CONFIDENCE
              </span>
            </div>
            <p className="target-var-reasoning">{targetVar.reasoning}</p>
            {targetVar.referenced_fact_ids.length > 0 && (
              <div className="ai-facts-pills">
                <span className="facts-label">Evidence:</span>
                {targetVar.referenced_fact_ids.map((fid) => {
                  const fact = computedFacts[fid]
                  return (
                    <button
                      key={fid}
                      type="button"
                      className="fact-pill"
                      title={fact?.formatted_statement || fid}
                      onClick={() => onSelectFact?.(fid)}
                    >
                      #{fid}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
