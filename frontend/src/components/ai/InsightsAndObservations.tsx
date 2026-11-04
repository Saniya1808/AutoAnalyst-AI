import React, { useState } from 'react'
import {
  ArrowRight,
  CheckCircle2,
  HelpCircle,
  Lightbulb,
  Link2,
  TrendingUp,
} from 'lucide-react'
import type { AnalyticalInsightsAI, ComputedFact } from '../../types/ai'

interface InsightsAndObservationsProps {
  insights: AnalyticalInsightsAI
  computedFacts: Record<string, ComputedFact>
  onSelectFact?: (factId: string) => void
}

export const InsightsAndObservations: React.FC<InsightsAndObservationsProps> = ({
  insights,
  computedFacts,
  onSelectFact,
}) => {
  const [filterType, setFilterType] = useState<'all' | 'verified' | 'hypothesis'>('all')

  const observations = insights.key_observations || []
  const relationships = insights.potential_relationships || []

  const filteredObservations = observations.filter((obs) => {
    if (filterType === 'verified') return obs.is_verified_fact || obs.observation_type === 'observed_fact'
    if (filterType === 'hypothesis') return obs.observation_type === 'hypothesis' || obs.observation_type === 'interpretation'
    return true
  })

  return (
    <div className="ai-insights-container">
      {/* Key Observations Section */}
      <div className="ai-section-card">
        <div className="ai-section-header-row">
          <div>
            <h3 className="ai-subheading">
              <Lightbulb size={18} className="text-amber-500" /> Key Observations & Hypotheses
            </h3>
            <p className="ai-subheading-desc">
              Empirical statements grounded in calculated statistics vs. domain hypotheses.
            </p>
          </div>
          <div className="filter-pill-group">
            <button
              type="button"
              className={`filter-pill ${filterType === 'all' ? 'active' : ''}`}
              onClick={() => setFilterType('all')}
            >
              All ({observations.length})
            </button>
            <button
              type="button"
              className={`filter-pill ${filterType === 'verified' ? 'active' : ''}`}
              onClick={() => setFilterType('verified')}
            >
              Verified Facts (
              {observations.filter((o) => o.is_verified_fact || o.observation_type === 'observed_fact').length}
              )
            </button>
            <button
              type="button"
              className={`filter-pill ${filterType === 'hypothesis' ? 'active' : ''}`}
              onClick={() => setFilterType('hypothesis')}
            >
              Hypotheses (
              {observations.filter((o) => o.observation_type === 'hypothesis' || o.observation_type === 'interpretation').length}
              )
            </button>
          </div>
        </div>

        <div className="ai-observations-grid">
          {filteredObservations.length === 0 ? (
            <div className="empty-substate">No observations match the selected filter.</div>
          ) : (
            filteredObservations.map((obs, idx) => {
              const isFact = obs.is_verified_fact || obs.observation_type === 'observed_fact'
              return (
                <div
                  key={idx}
                  className={`observation-card ${isFact ? 'card-verified' : 'card-hypothesis'}`}
                >
                  <div className="observation-header">
                    <span className={`obs-badge ${isFact ? 'badge-verified' : 'badge-hypothesis'}`}>
                      {isFact ? (
                        <>
                          <CheckCircle2 size={13} /> Verified Fact
                        </>
                      ) : (
                        <>
                          <HelpCircle size={13} /> Hypothesis / Interpretation
                        </>
                      )}
                    </span>
                    {obs.referenced_fact_ids.length > 0 && (
                      <div className="obs-fact-refs">
                        {obs.referenced_fact_ids.map((fid) => (
                          <button
                            key={fid}
                            type="button"
                            className="fact-pill-mini"
                            title={computedFacts[fid]?.formatted_statement || fid}
                            onClick={() => onSelectFact?.(fid)}
                          >
                            #{fid}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <p className="obs-statement">{obs.statement}</p>

                  {obs.business_implication && (
                    <div className="obs-implication">
                      <span className="implication-label">Business Implication:</span>{' '}
                      {obs.business_implication}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Potential Relationships Section */}
      {relationships.length > 0 && (
        <div className="ai-section-card">
          <h3 className="ai-subheading">
            <Link2 size={18} className="text-indigo-500" /> Detected Relationships & Patterns
          </h3>
          <p className="ai-subheading-desc">
            Interactions, correlations, and segmentations identified across variables.
          </p>

          <div className="relationships-grid">
            {relationships.map((rel, idx) => (
              <div key={idx} className="relationship-card">
                <div className="relationship-header">
                  <div className="rel-columns">
                    <code>{rel.primary_column}</code>
                    <ArrowRight size={14} className="rel-arrow" />
                    <code>{rel.secondary_column}</code>
                  </div>
                  <span className="rel-type-badge">{rel.analytical_type}</span>
                </div>
                <p className="relationship-desc">{rel.relationship_description}</p>
                {rel.referenced_fact_ids.length > 0 && (
                  <div className="rel-facts">
                    {rel.referenced_fact_ids.map((fid) => (
                      <button
                        key={fid}
                        type="button"
                        className="fact-pill-mini"
                        title={computedFacts[fid]?.formatted_statement || fid}
                        onClick={() => onSelectFact?.(fid)}
                      >
                        #{fid}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Business Relevance Summary */}
      {insights.business_relevance && (
        <div className="ai-section-card relevance-card">
          <div className="relevance-header">
            <TrendingUp size={18} />
            <h4>Analytical & Strategic Relevance</h4>
          </div>
          <p className="relevance-text">{insights.business_relevance}</p>
        </div>
      )}
    </div>
  )
}
