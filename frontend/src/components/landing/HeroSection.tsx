import React from 'react'
import { ArrowRight, ShieldCheck } from 'lucide-react'
import { AnalysisPreviewCard } from './AnalysisPreviewCard'

interface HeroSectionProps {
  onStart: () => void
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onStart }) => {
  return (
    <section className="hero section-wrap">
      <div className="hero-copy">
        <div className="eyebrow">
          <span className="status-dot" /> THE FUTURE OF DATA ANALYTICS
        </div>
        <h1>
          Meet your data.
          <br />
          <span className="gradient-text">Meet your analyst.</span>
        </h1>
        <p className="hero-description">
          Upload your data. Let intelligence do the heavy lifting. AutoAnalyst AI turns
          raw datasets into interactive dashboards and clear business insights.
        </p>
        <div className="hero-buttons">
          <button
            type="button"
            className="button button-primary button-large"
            onClick={onStart}
          >
            Start analysing <ArrowRight size={17} />
          </button>
          <a className="button button-outline button-large" href="#how-it-works">
            <span className="play-icon">▶</span> See how it works
          </a>
        </div>
        <div className="trust-line">
          <ShieldCheck size={15} /> Built for clarity, control and responsible AI analysis
        </div>
      </div>

      <AnalysisPreviewCard />
    </section>
  )
}
