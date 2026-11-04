import React from 'react'
import { Database, FileSpreadsheet, Trash2 } from 'lucide-react'
import type { DatasetOverview } from '../../types/dataset'

interface DatasetSelectorProps {
  datasets: DatasetOverview[]
  activeDatasetId: string | null
  onSelectDataset: (id: string) => void
  onDeleteDataset: (id: string) => void
  isDeleting?: boolean
}

export const DatasetSelector: React.FC<DatasetSelectorProps> = ({
  datasets,
  activeDatasetId,
  onSelectDataset,
  onDeleteDataset,
  isDeleting = false,
}) => {
  if (datasets.length === 0) {
    return null
  }

  return (
    <div className="dataset-selector-bar">
      <div className="dataset-selector-label">
        <Database size={15} />
        <span>ACTIVE DATASET</span>
      </div>

      <div className="dataset-pills-list">
        {datasets.map((dataset) => {
          const isActive = dataset.id === activeDatasetId
          return (
            <div
              key={dataset.id}
              className={`dataset-pill ${isActive ? 'active' : ''}`}
            >
              <button
                type="button"
                className="dataset-pill-btn"
                onClick={() => onSelectDataset(dataset.id)}
                title={`${dataset.filename} (${dataset.row_count.toLocaleString()} rows, ${dataset.column_count} cols)`}
              >
                <FileSpreadsheet size={15} />
                <span className="dataset-pill-name">{dataset.filename}</span>
                {dataset.is_cleaned && (
                  <span className="badge-cleaned">v{dataset.version} Cleaned</span>
                )}
                {dataset.is_sample && (
                  <span className="badge-cleaned" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
                    Sample
                  </span>
                )}
                <span className="dataset-pill-badge">
                  {dataset.row_count.toLocaleString()} rows
                </span>
              </button>

              {!dataset.is_sample && (
                <button
                  type="button"
                  className="dataset-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation()
                    if (
                      window.confirm(
                        `Are you sure you want to delete dataset "${dataset.filename}"? This cannot be undone.`
                      )
                    ) {
                      onDeleteDataset(dataset.id)
                    }
                  }}
                  disabled={isDeleting}
                  title="Delete dataset"
                  aria-label={`Delete ${dataset.filename}`}
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

