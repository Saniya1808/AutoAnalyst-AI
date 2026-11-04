import React from 'react'
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Copy,
  Cpu,
  FileText,
  HardDrive,
  Layers,
} from 'lucide-react'
import type { DatasetOverview } from '../../types/dataset'

interface DatasetOverviewCardProps {
  overview: DatasetOverview
}

export const DatasetOverviewCard: React.FC<DatasetOverviewCardProps> = ({ overview }) => {
  const formattedDate = new Date(overview.uploaded_at).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  const completenessPercentage = (100 - overview.missing_percentage).toFixed(1)

  return (
    <div className="dataset-overview-panel">
      <div className="overview-header">
        <div className="overview-title-group">
          <div className="overview-icon-badge">
            <FileText size={20} />
          </div>
          <div>
            <h3>{overview.filename}</h3>
            <p className="overview-meta">
              <span>{overview.file_type.toUpperCase()}</span>
              <span>•</span>
              <span className="meta-item">
                <Calendar size={13} /> {formattedDate}
              </span>
              <span>•</span>
              <span className="meta-item">
                <HardDrive size={13} /> {overview.memory_usage_human} in RAM
              </span>
            </p>
          </div>
        </div>

        <div className="quality-score-pill">
          {overview.missing_percentage === 0 ? (
            <div className="quality-good">
              <CheckCircle2 size={16} />
              <span>100% Complete</span>
            </div>
          ) : (
            <div className="quality-warning">
              <AlertTriangle size={16} />
              <span>{completenessPercentage}% Complete</span>
            </div>
          )}
        </div>
      </div>

      <div className="overview-stats-grid">
        <div className="stat-card">
          <div className="stat-card-label">
            <Layers size={14} /> ROWS & COLUMNS
          </div>
          <div className="stat-card-value">
            {overview.row_count.toLocaleString()}{' '}
            <span className="stat-card-unit">× {overview.column_count} cols</span>
          </div>
          <div className="stat-card-hint">
            {overview.total_cells.toLocaleString()} total data cells
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-label">
            <AlertTriangle size={14} /> MISSING DATA
          </div>
          <div className="stat-card-value">
            {overview.missing_percentage}%
          </div>
          <div className="stat-card-hint">
            {overview.missing_cells.toLocaleString()} empty or null cells
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-label">
            <Copy size={14} /> DUPLICATE ROWS
          </div>
          <div className="stat-card-value">
            {overview.duplicate_rows.toLocaleString()}{' '}
            <span className="stat-card-unit">({overview.duplicate_percentage}%)</span>
          </div>
          <div className="stat-card-hint">
            {overview.duplicate_rows === 0
              ? 'Zero duplicate rows detected'
              : 'Exact duplicate record matches'}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-label">
            <Cpu size={14} /> MEMORY FOOTPRINT
          </div>
          <div className="stat-card-value">
            {overview.memory_usage_human}
          </div>
          <div className="stat-card-hint">
            {(overview.file_size_bytes / 1024).toFixed(1)} KB file size on disk
          </div>
        </div>
      </div>
    </div>
  )
}

