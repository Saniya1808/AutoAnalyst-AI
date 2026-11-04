import React, { useEffect, useRef, useState } from 'react'
import { BarChart3, CornerDownLeft, Sparkles } from 'lucide-react'

interface ChatInputBoxProps {
  onSendMessage: (question: string, includeChart: boolean) => void
  isLoading: boolean
  disabled?: boolean
}

export const ChatInputBox: React.FC<ChatInputBoxProps> = ({
  onSendMessage,
  isLoading,
  disabled = false,
}) => {
  const [text, setText] = useState('')
  const [includeChart, setIncludeChart] = useState(true)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [isLoading])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading || disabled) return
    onSendMessage(trimmed, includeChart)
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    // Auto resize
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }

  return (
    <div className="chat-input-container">
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your data (e.g., 'What is the average fare by class?')..."
          rows={1}
          maxLength={1000}
          disabled={isLoading || disabled}
          className="chat-textarea"
        />

        <div className="chat-input-actions">
          <label className="chart-toggle-label" title="Toggle automatic visual chart generation">
            <input
              type="checkbox"
              checked={includeChart}
              onChange={(e) => setIncludeChart(e.target.checked)}
              disabled={isLoading || disabled}
            />
            <BarChart3 size={13} />
            <span>Generate Chart</span>
          </label>

          <span className="char-count">{text.length}/1000</span>

          <button
            type="button"
            className="send-message-btn"
            onClick={handleSubmit}
            disabled={!text.trim() || isLoading || disabled}
            title="Send question (Enter)"
          >
            {isLoading ? (
              <Sparkles size={16} className="animate-spin" />
            ) : (
              <>
                <span>Send</span>
                <CornerDownLeft size={14} />
              </>
            )}
          </button>
        </div>
      </div>
      <div className="chat-input-footer-hint">
        <span>Press <b>Enter</b> to send, <b>Shift + Enter</b> for new line. Grounded in Pandas calculations.</span>
      </div>
    </div>
  )
}
