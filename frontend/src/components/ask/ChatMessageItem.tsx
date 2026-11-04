import React from 'react'
import { Bot, Clock, Database, Sparkles, User } from 'lucide-react'
import type { ChatMessage, QueryResultFact } from '../../types/ask'
import { AnalysisResultCard } from './AnalysisResultCard'

interface ChatMessageItemProps {
  message: ChatMessage
  onSelectPrompt?: (prompt: string) => void
  onSelectFact?: (fact: QueryResultFact) => void
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  onSelectPrompt,
  onSelectFact,
}) => {
  const isUser = message.role === 'user'
  const isFallback = message.mode === 'statistical_fallback'

  const formattedTime = (() => {
    try {
      const d = new Date(message.created_at)
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  })()

  if (isUser) {
    return (
      <div className="chat-message-row user-row">
        <div className="message-bubble user-bubble">
          <p className="user-text">{message.content}</p>
          <div className="message-meta user-meta">
            <User size={12} />
            <span>You</span>
            {formattedTime && (
              <>
                <span>•</span>
                <span>{formattedTime}</span>
              </>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-message-row assistant-row">
      <div className="message-bubble assistant-bubble">
        {/* Model & Source Badge Header */}
        <div className="assistant-bubble-header">
          <div className="assistant-badge">
            <Sparkles size={13} className="text-accent" />
            <span className="assistant-name">AutoAnalyst AI</span>
          </div>
          <div className="assistant-model-pill" title={isFallback ? 'Generated using deterministic Pandas heuristics' : `Synthesized via ${message.model}`}>
            {isFallback ? (
              <>
                <Database size={11} className="text-amber-500" />
                <span>Deterministic Heuristics Engine</span>
              </>
            ) : (
              <>
                <Bot size={11} className="text-indigo-400" />
                <span>{message.model}</span>
              </>
            )}
          </div>
          {formattedTime && (
            <span className="assistant-time">
              <Clock size={11} /> {formattedTime}
            </span>
          )}
        </div>

        {/* Structured Result Body */}
        <AnalysisResultCard
          message={message}
          onSelectPrompt={onSelectPrompt}
          onSelectFact={onSelectFact}
        />
      </div>
    </div>
  )
}

