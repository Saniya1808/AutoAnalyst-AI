import React from 'react'
import { Database, FileSpreadsheet, Layers3, ShieldCheck } from 'lucide-react'
import type { DatasetDetail } from '../../types/dataset'

interface MetricsSummaryProps {
  totalDatasets: number
  totalRowsAll: number
  activeDataset: DatasetDetail | null
}

export const MetricsSummary: React.FC<MetricsSummaryProps> = ({
  totalDatasets,
  totalRowsAll,
  activeDataset,
}) => {
  const hasData = totalDatasets > 0 && activeDataset !== null

  return (
    <div className="workspace-cards">
      <article>
        <div className="small-card-icon">
          <Database size={18} />
        </div>
        <small>DATASETS</small>
        <strong>{totalDatasets > 0 ? totalDatasets : '—'}</strong>
        <span>
          {totalDatasets === 0
            ? 'No datasets uploaded yet'
            : totalDatasets === 1
            ? '1 dataset available'
            : `${totalDatasets} datasets available`}
        </span>
      </article>

      <article>
        <div className="small-card-icon">
          <Layers3 size={18} />
        </div>
        <small>ACTIVE ROWS</small>
        <strong>
          {hasData
            ? activeDataset.overview.row_count.toLocaleString()
            : totalRowsAll > 0
            ? totalRowsAll.toLocaleString()
            : '—'}
        </strong>
        <span>
          {hasData
            ? `In ${activeDataset.overview.filename}`
            : 'Row count on import'}
        </span>
      </article>

      <article>
        <div className="small-card-icon">
          <FileSpreadsheet size={18} />
        </div>
        <small>ACTIVE COLUMNS</small>
        <strong>{hasData ? activeDataset.overview.column_count : '—'}</strong>
        <span>
          {hasData
            ? `${
                activeDataset.columns.filter(
                  (c) => c.data_type === 'integer' || c.data_type === 'float'
                ).length
              } numeric, ${
                activeDataset.columns.filter((c) => c.data_type === 'string').length
              } text`
            : 'Columns distribution'}
        </span>
      </article>

      <article>
        <div className="small-card-icon">
          <ShieldCheck size={18} />
        </div>
        <small>DATA COMPLETENESS</small>
        <strong>
          {hasData
            ? `${(100 - activeDataset.overview.missing_percentage).toFixed(1)}%`
            : '—'}
        </strong>
        <span>
          {hasData
            ? `${activeDataset.overview.missing_cells.toLocaleString()} missing cells (${activeDataset.overview.missing_percentage}%)`
            : 'Quality check on upload'}
        </span>
      </article>
    </div>
  )
}
