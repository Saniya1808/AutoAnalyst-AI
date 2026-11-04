import React from 'react'
import { motion } from 'framer-motion'
import { BarChart3, BrainCircuit, Database } from 'lucide-react'

const features = [
  {
    icon: Database,
    title: 'Understands your data',
    text: 'Profiles columns, data types, missing values and distribution patterns.',
  },
  {
    icon: BarChart3,
    title: 'Builds your dashboard',
    text: 'Chooses useful KPIs and visualizations customized to your dataset.',
  },
  {
    icon: BrainCircuit,
    title: 'Finds the story',
    text: 'Turns verified analysis into clear, actionable natural language insights.',
  },
]

export const FeaturesSection: React.FC = () => {
  return (
    <section className="features-section section-wrap" id="features">
      <div className="section-heading">
        <div className="eyebrow">LESS MANUAL WORK. MORE DISCOVERY.</div>
        <h2>
          Analytics that moves
          <br />
          <span className="gradient-text">at the speed of thought.</span>
        </h2>
        <p>
          From your first upload to your final insight, one intelligent workspace brings the
          workflow together.
        </p>
      </div>

      <div className="feature-grid">
        {features.map((feature, index) => (
          <motion.article
            className="feature-card"
            key={feature.title}
            whileHover={{ y: -5 }}
            transition={{ duration: 0.2 }}
          >
            <div className="feature-icon">
              <feature.icon size={21} />
            </div>
            <span className="feature-number">0{index + 1}</span>
            <h3>{feature.title}</h3>
            <p>{feature.text}</p>
          </motion.article>
        ))}
      </div>
    </section>
  )
}
