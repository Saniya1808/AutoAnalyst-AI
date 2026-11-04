import React from 'react'
import { HelpCircle, Sparkles } from 'lucide-react'

interface SuggestedPromptsBarProps {
  prompts: string[]
  onSelectPrompt: (prompt: string) => void
  disabled?: boolean
}

export const SuggestedPromptsBar: React.FC<SuggestedPromptsBarProps> = ({
  prompts,
  onSelectPrompt,
  disabled = false,
}) => {
  if (!prompts || prompts.length === 0) return null

  return (
    <div className="suggested-prompts-container">
      <div className="prompts-header">
        <Sparkles size={14} className="text-accent" />
        <span>Suggested Questions</span>
      </div>
      <div className="prompts-chips-list">
        {prompts.map((p, idx) => (
          <button
            key={idx}
            type="button"
            className="prompt-chip-btn"
            disabled={disabled}
            onClick={() => onSelectPrompt(p)}
          >
            <HelpCircle size={13} />
            <span>{p}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

