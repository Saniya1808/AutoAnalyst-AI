import React from 'react'
import { Activity, RefreshCw } from 'lucide-react'
import { useBackendHealth } from '../../hooks/useBackendHealth'

interface BackendStatusIndicatorProps {
  compact?: boolean
}

export const BackendStatusIndicator: React.FC<BackendStatusIndicatorProps> = ({
  compact = false,
}) => {
  const { status, data, error, refetch } = useBackendHealth(20000)

  const getStatusConfig = () => {
    switch (status) {
      case 'online':
        return {
          colorClass: 'status-online',
          dotColor: '#35c99b',
          label: compact ? 'Online' : `FastAPI Online ${data?.version ? `v${data.version}` : ''}`,
          title: `Backend Healthy (${data?.service || 'AutoAnalyst AI API'}) - Click to refresh`,
        }
      case 'offline':
        return {
          colorClass: 'status-offline',
          dotColor: '#ff5c5c',
          label: compact ? 'Offline' : 'FastAPI Offline',
          title: error ? `Error: ${error} - Click to retry` : 'Backend unreachable - Click to retry',
        }
      case 'checking':
      default:
        return {
          colorClass: 'status-checking',
          dotColor: '#eab308',
          label: compact ? 'Checking' : 'Checking API...',
          title: 'Verifying backend health...',
        }
    }
  }

  const config = getStatusConfig()

  return (
    <button
      type="button"
      className={`backend-status-pill ${config.colorClass}`}
      onClick={refetch}
      title={config.title}
      aria-label={config.title}
    >
      <span
        className="backend-status-dot"
        style={{ backgroundColor: config.dotColor }}
      />
      <span className="backend-status-text">{config.label}</span>
      {status === 'checking' ? (
        <RefreshCw size={11} className="backend-spin-icon" />
      ) : (
        <Activity size={12} className="backend-activity-icon" />
      )}
    </button>
  )
}
