import React from 'react'
import { ArrowRight, CheckCircle2, Clock, FileSpreadsheet } from 'lucide-react'
import type { DatasetOverview } from '../../types/dataset'

interface RecentActivityPanelProps {
  datasets: DatasetOverview[]
  activeDatasetId: string | null
  onSelectDataset: (id: string) => void
  onTriggerUpload: () => void
}

export const RecentActivityPanel: React.FC<RecentActivityPanelProps> = ({
  datasets,
  activeDatasetId,
  onSelectDataset,
  onTriggerUpload,
}) => {
  if (datasets.length === 0) {
    return (
      <div className="recent-panel">
        <div>
          <h3>Recent activity</h3>
          <p>
            Your latest datasets, automated profiling, and visual charts will show up here.
          </p>
        </div>

        <div className="empty-state">
          <div>
            <FileSpreadsheet size={23} />
          </div>
          <b>Your workspace is ready</b>
          <span>Upload your first CSV or Excel file to get started.</span>
          <button
            type="button"
            className="text-button"
            onClick={onTriggerUpload}
          >
            Choose a file <ArrowRight size={14} />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="recent-panel">
      <div className="recent-header-flex">
        <div>
          <h3>Dataset History</h3>
          <p>Recently uploaded and profiled datasets in this session.</p>
        </div>
        <button
          type="button"
          className="button button-secondary text-sm-btn"
          onClick={onTriggerUpload}
        >
          Upload another file
        </button>
      </div>

      <div className="recent-datasets-grid">
        {datasets.map((d) => {
          const isActive = d.id === activeDatasetId
          const uploadDate = new Date(d.uploaded_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })

          return (
            <div
              key={d.id}
              className={`recent-dataset-item ${isActive ? 'active-item' : ''}`}
              onClick={() => onSelectDataset(d.id)}
            >
              <div className="recent-item-icon">
                <FileSpreadsheet size={18} />
              </div>

              <div className="recent-item-details">
                <div className="recent-item-title-row">
                  <h4 title={d.filename}>{d.filename}</h4>
                  {isActive && (
                    <span className="active-tag">
                      <CheckCircle2 size={12} /> Active
                    </span>
                  )}
                </div>

                <div className="recent-item-sub">
                  <span>{d.row_count.toLocaleString()} rows</span>
                  <span>•</span>
                  <span>{d.column_count} columns</span>
                  <span>•</span>
                  <span>{d.memory_usage_human}</span>
                </div>
              </div>

              <div className="recent-item-time">
                <Clock size={12} /> {uploadDate}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
