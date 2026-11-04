import React, { useEffect, useState } from 'react'
import { Brain, Cpu, Database, Sparkles } from 'lucide-react'

export const UnderstandingLoadingSkeleton: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0)

  const steps = [
    {
      icon: Database,
      title: 'Grounding Numerical Truth',
      desc: 'Pandas is calculating 5-number summaries, missing counts, and stable fact IDs...',
    },
    {
      icon: Cpu,
      title: 'Distilling Privacy-Preserving Metadata',
      desc: 'Minimizing column schemas and categorical distributions (no raw rows transmitted)...',
    },
    {
      icon: Brain,
      title: 'Synthesizing Semantic Understanding',
      desc: 'Inferring domain, likely purpose, target variables, and business hypotheses...',
    },
    {
      icon: Sparkles,
      title: 'Validating Empirical Citations',
      desc: 'Verifying every observation strictly references calculated fact IDs...',
    },
  ]

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev))
    }, 1800)
    return () => clearInterval(timer)
  }, [steps.length])

  return (
    <div className="ai-loading-container">
      <div className="ai-loading-card">
        <div className="ai-loading-icon-wrapper">
          <Sparkles className="ai-spinner-icon animate-spin" size={36} />
        </div>
        <h3 className="ai-loading-title">Generating AI Dataset Understanding</h3>
        <p className="ai-loading-subtitle">
          AutoAnalyst AI is performing autonomous semantic profiling and statistical verification.
        </p>

        <div className="ai-loading-steps">
          {steps.map((s, idx) => {
            const Icon = s.icon
            const isDone = idx < currentStep
            const isCurrent = idx === currentStep
            return (
              <div
                key={s.title}
                className={`ai-loading-step ${isCurrent ? 'active' : ''} ${isDone ? 'done' : ''}`}
              >
                <div className="step-indicator">
                  <Icon size={16} />
                </div>
                <div className="step-content">
                  <div className="step-title">{s.title}</div>
                  <div className="step-desc">{s.desc}</div>
                </div>
              </div>
            )
          })}
        </div>

        <div className="ai-loading-progress-bar">
          <div
            className="ai-loading-progress-fill"
            style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  )
}

