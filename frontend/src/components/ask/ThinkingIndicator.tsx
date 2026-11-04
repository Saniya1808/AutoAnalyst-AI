import React, { useEffect, useState } from 'react'
import { Bot, Database, Sparkles } from 'lucide-react'

export const ThinkingIndicator: React.FC = () => {
  const [stage, setStage] = useState(0)

  const stages = [
    { icon: Bot, label: 'Interpreting question & columns...' },
    { icon: Database, label: 'Executing Pandas calculations...' },
    { icon: Sparkles, label: 'Grounding facts & synthesizing answer...' },
  ]

  useEffect(() => {
    const timer = setInterval(() => {
      setStage((prev) => (prev < stages.length - 1 ? prev + 1 : prev))
    }, 1400)
    return () => clearInterval(timer)
  }, [stages.length])

  const CurrentIcon = stages[stage].icon

  return (
    <div className="ask-thinking-bubble">
      <div className="thinking-icon-spin">
        <CurrentIcon size={16} className="animate-spin" />
      </div>
      <div className="thinking-stage-text">
        <span>{stages[stage].label}</span>
      </div>
      <div className="thinking-dots">
        <span className="dot dot-1" />
        <span className="dot dot-2" />
        <span className="dot dot-3" />
      </div>
    </div>
  )
}
