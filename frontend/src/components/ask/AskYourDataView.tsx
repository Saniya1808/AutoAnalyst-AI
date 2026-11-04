import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  FileCheck2,
  Info,
  MessageSquare,
  RefreshCw,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react'
import {
  askDatasetQuestion,
  clearConversation,
  getConversationHistory,
  getSuggestedQuestions,
} from '../../services/api'
import type { ChatMessage, QueryResultFact } from '../../types/ask'
import { ChatInputBox } from './ChatInputBox'
import { ChatMessageItem } from './ChatMessageItem'
import { SuggestedPromptsBar } from './SuggestedPromptsBar'
import { ThinkingIndicator } from './ThinkingIndicator'

interface AskYourDataViewProps {
  datasetId: string
  datasetFilename: string
  isCleaned?: boolean
  version?: number
}

export const AskYourDataView: React.FC<AskYourDataViewProps> = ({
  datasetId,
  datasetFilename,
  isCleaned = false,
  version = 0,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [prompts, setPrompts] = useState<string[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  const [isAsking, setIsAsking] = useState(false)
  const [isClearing, setIsClearing] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [snapshotNotice, setSnapshotNotice] = useState<string | null>(null)
  const [selectedFact, setSelectedFact] = useState<QueryResultFact | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback((smooth = true) => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' })
    }
  }, [])

  // Load history & suggested prompts
  const loadData = useCallback(async () => {
    setIsLoadingHistory(true)
    setErrorMessage(null)

    try {
      const [histRes, promptsRes] = await Promise.all([
        getConversationHistory(datasetId),
        getSuggestedQuestions(datasetId),
      ])

      setMessages(histRes.messages || [])
      setSnapshotNotice(histRes.notice || null)
      setPrompts(promptsRes.prompts || [])
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to load conversation history'
      )
    } finally {
      setIsLoadingHistory(false)
    }
  }, [datasetId])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    scrollToBottom(false)
  }, [messages, scrollToBottom])

  const handleSendMessage = async (question: string, includeChart: boolean) => {
    if (!question.trim() || isAsking) return

    setErrorMessage(null)
    setIsAsking(true)

    // Temporary optimistic user message
    const tempUserMsg: ChatMessage = {
      message_id: `temp_${Date.now()}`,
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
      dataset_id: datasetId,
      snapshot_hash: '',
      columns_used: [],
      filters_applied: [],
      tabular_data: [],
      grounded_facts: [],
      limitations_and_warnings: [],
      suggested_follow_ups: [],
      mode: 'ai_generated',
      provider: 'gemini',
      model: 'gemini-3.8-flash',
    }

    setMessages((prev) => [...prev, tempUserMsg])
    setTimeout(() => scrollToBottom(true), 50)

    try {
      const res = await askDatasetQuestion(datasetId, {
        question,
        include_chart: includeChart,
      })

      const assistantMsg: ChatMessage = {
        message_id: res.message_id,
        role: 'assistant',
        content: res.direct_answer,
        created_at: res.created_at,
        dataset_id: res.dataset_id,
        snapshot_hash: res.snapshot_hash,
        direct_answer: res.direct_answer,
        primary_metric: res.primary_metric,
        calculation_method: res.calculation_method,
        columns_used: res.columns_used,
        filters_applied: res.filters_applied,
        tabular_data: res.tabular_data,
        chart: res.chart,
        grounded_facts: res.grounded_facts,
        limitations_and_warnings: res.limitations_and_warnings,
        is_ambiguous: res.is_ambiguous,
        clarification_prompt: res.clarification_prompt,
        suggested_follow_ups: res.suggested_follow_ups,
        mode: res.mode,
        provider: res.provider,
        model: res.model,
      }

      setMessages((prev) => [...prev, assistantMsg])
      setTimeout(() => scrollToBottom(true), 100)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to get answer from data analyst'
      )
    } finally {
      setIsAsking(false)
    }
  }

  const handleClearHistory = async () => {
    if (!window.confirm(`Clear conversation history for "${datasetFilename}"?`)) return

    setIsClearing(true)
    try {
      await clearConversation(datasetId)
      setMessages([])
      setSnapshotNotice(null)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to clear conversation history'
      )
    } finally {
      setIsClearing(false)
    }
  }

  return (
    <div className="ask-workspace-container">
      {/* Top Header Bar */}
      <div className="ask-header-bar">
        <div className="ask-header-left">
          <div className="ask-icon-badge">
            <MessageSquare size={18} />
          </div>
          <div>
            <div className="ask-title-row">
              <h3>Ask Your Data</h3>
              <span className="brand-pill">Powered by Saniya</span>
            </div>
            <div className="ask-subtitle">
              <span>{datasetFilename}</span>
              {isCleaned ? (
                <span className="dataset-tag tag-cleaned">Cleaned (v{version})</span>
              ) : (
                <span className="dataset-tag tag-original">Original Source</span>
              )}
              <span className="dataset-tag tag-grounded">
                <FileCheck2 size={11} /> 100% Pandas Grounded
              </span>
            </div>
          </div>
        </div>

        <div className="ask-header-right">
          {messages.length > 0 && (
            <button
              type="button"
              className="button button-secondary text-sm-btn"
              onClick={handleClearHistory}
              disabled={isClearing || isAsking}
              title="Clear conversation history"
            >
              <Trash2 size={13} />
              <span>{isClearing ? 'Clearing...' : 'Clear Chat'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Snapshot change notice banner */}
      {snapshotNotice && (
        <div className="snapshot-notice-banner">
          <Info size={16} className="text-amber-500 shrink-0" />
          <span>{snapshotNotice}</span>
        </div>
      )}

      {/* Error Banner */}
      {errorMessage && (
        <div className="ask-error-banner">
          <AlertCircle size={16} className="text-red-500 shrink-0" />
          <span>{errorMessage}</span>
          <button type="button" className="close-banner-btn" onClick={() => setErrorMessage(null)}>
            ×
          </button>
        </div>
      )}

      {/* Chat Messages Stream */}
      <div className="chat-messages-stream">
        {isLoadingHistory ? (
          <div className="chat-loading-history">
            <RefreshCw size={24} className="animate-spin text-muted" />
            <p>Loading conversation history...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="empty-state-icon">
              <Sparkles size={32} />
            </div>
            <h4>Ask anything about {datasetFilename}</h4>
            <p>
              AutoAnalyst AI interprets your questions, calculates exact figures using Pandas,
              and returns clear explanations with interactive visualizations.
            </p>

            <SuggestedPromptsBar
              prompts={prompts}
              onSelectPrompt={(p) => handleSendMessage(p, true)}
              disabled={isAsking}
            />
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessageItem
                key={msg.message_id}
                message={msg}
                onSelectPrompt={(p) => handleSendMessage(p, true)}
                onSelectFact={(f) => setSelectedFact(f)}
              />
            ))}

            {isAsking && <ThinkingIndicator />}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Bottom Suggested Chips when conversation is active */}
      {messages.length > 0 && !isAsking && prompts.length > 0 && (
        <div className="chat-bottom-prompts">
          <SuggestedPromptsBar
            prompts={prompts.slice(0, 4)}
            onSelectPrompt={(p) => handleSendMessage(p, true)}
            disabled={isAsking}
          />
        </div>
      )}

      {/* Chat Input Bar */}
      <ChatInputBox
        onSendMessage={handleSendMessage}
        isLoading={isAsking}
        disabled={isLoadingHistory}
      />

      {/* Fact Detail Modal */}
      {selectedFact && (
        <div className="fact-modal-backdrop" onClick={() => setSelectedFact(null)}>
          <div className="fact-modal" onClick={(e) => e.stopPropagation()}>
            <div className="fact-modal-header">
              <div className="fact-modal-title">
                <FileCheck2 size={18} className="text-emerald-500" />
                <span>Verified Fact Details</span>
                <span className="fact-modal-id">#{selectedFact.fact_id}</span>
              </div>
              <button
                type="button"
                className="fact-modal-close"
                onClick={() => setSelectedFact(null)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="fact-modal-body">
              <div className="fact-detail-row">
                <span className="detail-label">Category:</span>
                <span className="detail-value">{selectedFact.category}</span>
              </div>
              {selectedFact.column_name && (
                <div className="fact-detail-row">
                  <span className="detail-label">Target Column:</span>
                  <code className="detail-value">{selectedFact.column_name}</code>
                </div>
              )}
              <div className="fact-detail-row">
                <span className="detail-label">Metric Name:</span>
                <span className="detail-value">{selectedFact.metric_name}</span>
              </div>
              <div className="fact-detail-statement">
                <span className="detail-label">Empirical Statement:</span>
                <p>{selectedFact.formatted_statement}</p>
              </div>
              <div className="fact-detail-raw">
                <span className="detail-label">Computed Value:</span>
                <pre>{JSON.stringify(selectedFact.value, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
