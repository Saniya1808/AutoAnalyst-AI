import React, { useState } from 'react'
import { Check, Search } from 'lucide-react'
import type { ColumnProfile, SemanticDataType } from '../../types/dataset'

interface ColumnProfileViewProps {
  columns: ColumnProfile[]
}

const TYPE_CONFIG: Record<
  SemanticDataType,
  { label: string; className: string }
> = {
  integer: { label: 'INTEGER', className: 'type-badge-int' },
  float: { label: 'FLOAT', className: 'type-badge-float' },
  string: { label: 'STRING', className: 'type-badge-str' },
  boolean: { label: 'BOOLEAN', className: 'type-badge-bool' },
  datetime: { label: 'DATETIME', className: 'type-badge-date' },
}

export const ColumnProfileView: React.FC<ColumnProfileViewProps> = ({ columns }) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('all')

  const filteredColumns = columns.filter((col) => {
    const matchesSearch = col.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType =
      selectedTypeFilter === 'all' || col.data_type === selectedTypeFilter
    return matchesSearch && matchesType
  })

  // Count by type
  const typeCounts = columns.reduce<Record<string, number>>((acc, col) => {
    acc[col.data_type] = (acc[col.data_type] || 0) + 1
    return acc
  }, {})

  return (
    <div className="column-profiling-panel">
      <div className="column-panel-header">
        <div>
          <h3>Schema & Column Profiling</h3>
          <p>
            Detailed distributions, distinct cardinality, and statistical metrics
            calculated via Pandas.
          </p>
        </div>

        <div className="column-controls">
          <div className="column-search-box">
            <Search size={14} />
            <input
              type="text"
              placeholder="Filter columns..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="type-filter-group">
            <button
              type="button"
              className={`filter-btn ${selectedTypeFilter === 'all' ? 'active' : ''}`}
              onClick={() => setSelectedTypeFilter('all')}
            >
              All ({columns.length})
            </button>
            {Object.entries(typeCounts).map(([type, count]) => (
              <button
                key={type}
                type="button"
                className={`filter-btn ${selectedTypeFilter === type ? 'active' : ''}`}
                onClick={() => setSelectedTypeFilter(type)}
              >
                {type.toUpperCase()} ({count})
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="columns-cards-list">
        {filteredColumns.map((col) => {
          const typeMeta = TYPE_CONFIG[col.data_type] || {
            label: col.data_type.toUpperCase(),
            className: 'type-badge-str',
          }

          return (
            <article key={col.name} className="column-card">
              <div className="column-card-header">
                <div className="column-name-row">
                  <span className="column-pos">#{col.position + 1}</span>
                  <h4 className="column-name">{col.name}</h4>
                  <span className={`type-badge ${typeMeta.className}`}>
                    {typeMeta.label}
                  </span>
                  {col.is_unique && (
                    <span className="unique-pill" title="100% Unique / Primary Key Candidate">
                      <Check size={11} /> Unique Key
                    </span>
                  )}
                </div>

                <div className="column-null-stat">
                  {col.null_count > 0 ? (
                    <span className="null-indicator has-nulls">
                      {col.null_count.toLocaleString()} nulls ({col.null_percentage}%)
                    </span>
                  ) : (
                    <span className="null-indicator zero-nulls">
                      <Check size={12} /> 100% complete
                    </span>
                  )}
                </div>
              </div>

              {/* Statistical details */}
              <div className="column-stats-body">
                <div className="col-stat-item">
                  <small>DISTINCT VALUES</small>
                  <strong>{col.unique_count.toLocaleString()}</strong>
                </div>

                <div className="col-stat-item">
                  <small>NON-NULL ROWS</small>
                  <strong>{col.non_null_count.toLocaleString()}</strong>
                </div>

                {col.min !== null && col.min !== undefined && (
                  <div className="col-stat-item">
                    <small>MIN</small>
                    <strong>{col.min.toLocaleString()}</strong>
                  </div>
                )}

                {col.max !== null && col.max !== undefined && (
                  <div className="col-stat-item">
                    <small>MAX</small>
                    <strong>{col.max.toLocaleString()}</strong>
                  </div>
                )}

                {col.mean !== null && col.mean !== undefined && (
                  <div className="col-stat-item">
                    <small>MEAN (AVG)</small>
                    <strong>{col.mean.toLocaleString()}</strong>
                  </div>
                )}

                {col.median !== null && col.median !== undefined && (
                  <div className="col-stat-item">
                    <small>MEDIAN</small>
                    <strong>{col.median.toLocaleString()}</strong>
                  </div>
                )}

                {col.std !== null && col.std !== undefined && (
                  <div className="col-stat-item">
                    <small>STD DEV</small>
                    <strong>{col.std.toLocaleString()}</strong>
                  </div>
                )}

                {col.zeros_count !== null && col.zeros_count !== undefined && col.zeros_count > 0 && (
                  <div className="col-stat-item">
                    <small>ZEROS COUNT</small>
                    <strong>{col.zeros_count.toLocaleString()}</strong>
                  </div>
                )}
              </div>

              {/* Categorical Top Values */}
              {col.top_values && col.top_values.length > 0 && (
                <div className="top-values-container">
                  <small className="top-values-label">TOP FREQUENT VALUES</small>
                  <div className="top-values-pills">
                    {col.top_values.map((item, idx) => (
                      <span key={idx} className="category-pill">
                        <span className="cat-val">{item.value || '""'}</span>
                        <span className="cat-count">{item.count.toLocaleString()}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Sample values preview */}
              {col.sample_values && col.sample_values.length > 0 && (
                <div className="sample-values-container">
                  <small className="sample-values-label">SAMPLE VALUES</small>
                  <div className="sample-pills">
                    {col.sample_values.map((sample, idx) => (
                      <code key={idx} className="sample-code">
                        {sample === null ? 'null' : String(sample)}
                      </code>
                    ))}
                  </div>
                </div>
              )}
            </article>
          )
        })}

        {filteredColumns.length === 0 && (
          <div className="column-empty-filter">
            <p>No columns matching your search criteria.</p>
          </div>
        )}
      </div>
    </div>
  )
}
