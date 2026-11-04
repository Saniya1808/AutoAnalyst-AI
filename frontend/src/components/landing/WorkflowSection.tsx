import React from 'react'

const steps = [
  {
    step: '01',
    title: 'Bring your dataset',
    description: 'Start with supported CSV or Excel files in seconds.',
  },
  {
    step: '02',
    title: 'Let the engine analyse',
    description: 'Profile distributions, check correlations, and calculate high-value metrics.',
  },
  {
    step: '03',
    title: 'Explore and ask',
    description: 'Review charts, ask questions in natural language, and export insights.',
  },
]

export const WorkflowSection: React.FC = () => {
  return (
    <section className="workflow-section section-wrap" id="how-it-works">
      <div>
        <div className="eyebrow">A CLEARER WORKFLOW</div>
        <h2>
          From upload to
          <br />
          <span className="gradient-text">understanding.</span>
        </h2>
        <p>
          Keep control of your data while the platform handles repetitive analysis tasks.
        </p>
      </div>

      <div className="workflow-list">
        {steps.map((item) => (
          <div key={item.step}>
            <span>{item.step}</span>
            <b>{item.title}</b>
            <small>{item.description}</small>
          </div>
        ))}
      </div>
    </section>
  )
}
