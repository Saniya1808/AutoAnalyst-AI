import React from 'react'
import { Database, Layers3, Sparkles } from 'lucide-react'

export const MetricsSummary: React.FC = () => {
  return (
    <div className="workspace-cards">
      <article>
        <div className="small-card-icon">
          <Database size={18} />
        </div>
        <small>DATASETS</small>
        <strong>—</strong>
        <span>No datasets uploaded yet</span>
      </article>

      <article>
        <div className="small-card-icon">
          <Layers3 size={18} />
        </div>
        <small>PROJECTS</small>
        <strong>—</strong>
        <span>Analyses will appear here</span>
      </article>

      <article>
        <div className="small-card-icon">
          <Sparkles size={18} />
        </div>
        <small>INSIGHTS FOUND</small>
        <strong>—</strong>
        <span>Ready when data is imported</span>
      </article>
    </div>
  )
}
