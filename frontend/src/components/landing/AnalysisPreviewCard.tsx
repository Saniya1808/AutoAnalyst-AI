import React from 'react'
import { motion } from 'framer-motion'
import { BrainCircuit, Check, ChevronDown, Command, Sparkles } from 'lucide-react'

const chartData = [32, 48, 39, 64, 52, 78, 59, 88, 68, 96, 76, 85]

export const AnalysisPreviewCard: React.FC = () => {
  return (
    <div className="hero-visual">
      <div className="orbit orbit-a" />
      <div className="orbit orbit-b" />
      <motion.div
        className="visual-glow"
        animate={{ scale: [1, 1.08, 1], opacity: [0.55, 0.8, 0.55] }}
        transition={{ duration: 5, repeat: Infinity }}
      />
      
      <motion.div
        className="preview-card"
        initial={{ opacity: 0, scale: 0.94, rotateY: 8 }}
        animate={{ opacity: 1, scale: 1, rotateY: 0 }}
        transition={{ duration: 0.7, delay: 0.15 }}
      >
        <div className="preview-top">
          <div className="preview-dots">
            <i />
            <i />
            <i />
          </div>
          <span>
            ANALYSIS PREVIEW <span className="live-pill">LIVE UI</span>
          </span>
          <Command size={14} />
        </div>

        <div className="preview-heading">
          <div>
            <small>OVERVIEW / SALES DATA</small>
            <h3>Performance snapshot</h3>
          </div>
          <span className="period-pill">
            Last 30 days <ChevronDown size={12} />
          </span>
        </div>

        <div className="metric-grid">
          <div className="metric">
            <small>TOTAL REVENUE</small>
            <strong>$84,290</strong>
            <em>↗ 12.8%</em>
          </div>
          <div className="metric">
            <small>ORDERS</small>
            <strong>2,481</strong>
            <em>↗ 8.4%</em>
          </div>
          <div className="metric">
            <small>AVG. ORDER</small>
            <strong>$33.97</strong>
            <em>↗ 3.1%</em>
          </div>
        </div>

        <div className="chart-panel">
          <div className="chart-title">
            <span>Revenue trend</span>
            <small>Illustrative preview</small>
          </div>
          <div className="chart-bars">
            {chartData.map((height, i) => (
              <motion.div
                key={i}
                initial={{ height: 0 }}
                animate={{ height: `${height}%` }}
                transition={{ delay: 0.35 + i * 0.045, duration: 0.55 }}
              />
            ))}
          </div>
          <div className="chart-labels">
            <span>W1</span>
            <span>W2</span>
            <span>W3</span>
            <span>W4</span>
          </div>
        </div>

        <div className="insight-strip">
          <Sparkles size={15} />
          <span>
            <b>AI insight</b> · Revenue is trending upward in this illustrative preview.
          </span>
        </div>
      </motion.div>

      <div className="floating-chip chip-top">
        <span className="chip-icon">
          <BrainCircuit size={15} />
        </span>
        Autonomous profiling
      </div>

      <div className="floating-chip chip-bottom">
        <span className="chip-icon green">
          <Check size={15} />
        </span>
        Dashboard ready
      </div>
    </div>
  )
}
