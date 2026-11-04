import React from 'react'
import { ChevronLeft, ChevronRight, Table } from 'lucide-react'
import type { DatasetPreview } from '../../types/dataset'

interface DatasetPreviewTableProps {
  preview: DatasetPreview
  isLoadingPage?: boolean
  onPageChange: (newOffset: number) => void
}

export const DatasetPreviewTable: React.FC<DatasetPreviewTableProps> = ({
  preview,
  isLoadingPage = false,
  onPageChange,
}) => {
  const { columns, column_types, rows, total_rows, offset, limit } = preview

  const startRow = Math.min(offset + 1, total_rows)
  const endRow = Math.min(offset + rows.length, total_rows)
  const hasPrev = offset > 0
  const hasNext = offset + limit < total_rows

  const renderCellValue = (value: unknown, colName: string) => {
    if (value === null || value === undefined) {
      return <span className="null-cell-tag">null</span>
    }

    const type = column_types[colName]
    if (type === 'boolean') {
      return (
        <span className={`bool-cell-tag ${value ? 'bool-true' : 'bool-false'}`}>
          {value ? 'TRUE' : 'FALSE'}
        </span>
      )
    }

    if (type === 'float') {
      const num = Number(value)
      return isNaN(num) ? String(value) : num.toLocaleString(undefined, { maximumFractionDigits: 4 })
    }

    if (type === 'integer') {
      const num = Number(value)
      return isNaN(num) ? String(value) : num.toLocaleString()
    }

    return String(value)
  }

  return (
    <div className="preview-table-panel">
      <div className="preview-panel-header">
        <div className="preview-header-info">
          <div className="preview-icon">
            <Table size={18} />
          </div>
          <div>
            <h3>Dataset Preview</h3>
            <p>
              Showing actual raw records received from the server.
            </p>
          </div>
        </div>

        {/* Pagination controls */}
        <div className="table-pagination">
          <span className="pagination-info">
            Rows {startRow.toLocaleString()} – {endRow.toLocaleString()} of{' '}
            {total_rows.toLocaleString()}
          </span>

          <div className="pagination-buttons">
            <button
              type="button"
              className="page-nav-btn"
              onClick={() => onPageChange(Math.max(0, offset - limit))}
              disabled={!hasPrev || isLoadingPage}
              title="Previous page"
            >
              <ChevronLeft size={16} /> Prev
            </button>
            <button
              type="button"
              className="page-nav-btn"
              onClick={() => onPageChange(offset + limit)}
              disabled={!hasNext || isLoadingPage}
              title="Next page"
            >
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>

      <div className={`table-scroll-container ${isLoadingPage ? 'table-loading' : ''}`}>
        <table className="data-preview-table">
          <thead>
            <tr>
              <th className="row-index-header">#</th>
              {columns.map((col) => (
                <th key={col}>
                  <div className="table-col-header">
                    <span className="col-header-name">{col}</span>
                    <span className="col-header-type">
                      {column_types[col] || 'string'}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rIdx) => (
              <tr key={rIdx}>
                <td className="row-index-cell">{offset + rIdx + 1}</td>
                {columns.map((col) => (
                  <td key={col} className={`cell-${column_types[col] || 'string'}`}>
                    {renderCellValue(row[col], col)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

