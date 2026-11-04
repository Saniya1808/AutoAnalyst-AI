import React from 'react'
import { BarChart3, Sparkles } from 'lucide-react'
import type { ChartConfig } from '../../types/dashboard'
import { InteractiveChart } from './InteractiveChart'

interface ChartRecommendationsProps {
  charts: ChartConfig[]
  onCategoryClick?: (column: string, value: string) => void
}

export const ChartRecommendations: React.FC<ChartRecommendationsProps> = ({
  charts,
  onCategoryClick,
}) => {
  if (charts.length === 0) {
    return (
      <div className="recommendations-empty-panel">
        <BarChart3 size={32} />
        <h4>No chart recommendations available</h4>
        <p>Ensure your dataset contains valid numeric or categorical columns.</p>
      </div>
    )
  }

  return (
    <div className="recommendations-section">
      <div className="section-heading-row">
        <div>
          <div className="eyebrow">
            <Sparkles size={13} /> AUTOMATIC RECOMMENDATIONS
          </div>
          <h3>Recommended Visualizations</h3>
          <p>
            Curated statistical distributions, compositional breakdowns, and trends
            inferred from your dataset. Click bars or slices to drill down.
          </p>
        </div>
      </div>

      <div className="recommendations-grid">
        {charts.map((chart) => (
          <div key={chart.chart_id} className="chart-card">
            <div className="chart-card-topbar">
              <span className={`chart-type-badge type-${chart.chart_type}`}>
                {chart.chart_type.toUpperCase()}
              </span>
              {chart.aggregation && (
                <span className="agg-badge">{chart.aggregation.toUpperCase()}</span>
              )}
            </div>

            <InteractiveChart
              chart={chart}
              onCategoryClick={onCategoryClick}
              height={340}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
