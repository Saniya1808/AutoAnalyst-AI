import React, { useState } from 'react'
import {
  AlertTriangle,
  Columns,
  Fingerprint,
  Search,
  Star,
} from 'lucide-react'
import type { ColumnUnderstandingAI, ComputedFact } from '../../types/ai'

interface ColumnUnderstandingTableProps {
  columns: ColumnUnderstandingAI[]
  computedFacts: Record<string, ComputedFact>
  onSelectFact?: (factId: string) => void
}

export const ColumnUnderstandingTable: React.FC<ColumnUnderstandingTableProps> = ({
  columns,
  computedFacts,
  onSelectFact,
}) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [filterRole, setFilterRole] = useState<'all' | 'key' | 'id'>('all')

  const filteredColumns = columns.filter((col) => {
    const matchesSearch = col.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      col.business_meaning.toLowerCase().includes(searchQuery.toLowerCase())
    if (!matchesSearch) return false
    if (filterRole === 'key') return col.is_key_feature
    if (filterRole === 'id') return col.is_identifier
    return true
  })

  return (
    <div className="ai-columns-container">
      <div className="ai-section-card">
        <div className="ai-columns-toolbar">
          <div>
            <h3 className="ai-subheading">
              <Columns size={18} className="text-blue-500" /> Semantic Column Catalog ({columns.length})
            </h3>
            <p className="ai-subheading-desc">
              AI-inferred domain definitions, functional roles, and quality alerts.
            </p>
          </div>

          <div className="toolbar-controls">
            <div className="search-box">
              <Search size={15} />
              <input
                type="text"
                placeholder="Search columns or meanings..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="role-filter-group">
              <button
                type="button"
                className={`filter-btn ${filterRole === 'all' ? 'active' : ''}`}
                onClick={() => setFilterRole('all')}
              >
                All
              </button>
              <button
                type="button"
                className={`filter-btn ${filterRole === 'key' ? 'active' : ''}`}
                onClick={() => setFilterRole('key')}
              >
                Key Features
              </button>
              <button
                type="button"
                className={`filter-btn ${filterRole === 'id' ? 'active' : ''}`}
                onClick={() => setFilterRole('id')}
              >
                Identifiers
              </button>
            </div>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="ai-table">
            <thead>
              <tr>
                <th>Column Name</th>
                <th>Semantic Type</th>
                <th>Role</th>
                <th>Inferred Business Meaning</th>
                <th>Quality Alerts</th>
                <th>Facts</th>
              </tr>
            </thead>
            <tbody>
              {filteredColumns.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-6 text-muted">
                    No columns match your filter criteria.
                  </td>
                </tr>
              ) : (
                filteredColumns.map((col) => (
                  <tr key={col.name}>
                    <td className="col-name-cell">
                      <code>{col.name}</code>
                    </td>
                    <td>
                      <span className={`type-badge type-${col.semantic_type}`}>
                        {col.semantic_type}
                      </span>
                    </td>
                    <td>
                      <div className="role-badges">
                        {col.is_key_feature && (
                          <span className="role-badge role-key" title="Key analytical driver">
                            <Star size={12} /> Key
                          </span>
                        )}
                        {col.is_identifier && (
                          <span className="role-badge role-id" title="Unique record identifier">
                            <Fingerprint size={12} /> ID
                          </span>
                        )}
                        {!col.is_key_feature && !col.is_identifier && (
                          <span className="role-badge role-feature">Feature</span>
                        )}
                      </div>
                    </td>
                    <td className="business-meaning-cell">{col.business_meaning}</td>
                    <td>
                      {col.data_quality_note ? (
                        <div className="quality-alert-cell">
                          <AlertTriangle size={13} className="text-amber-500" />
                          <span>{col.data_quality_note}</span>
                        </div>
                      ) : (
                        <span className="text-muted-xs">—</span>
                      )}
                    </td>
                    <td>
                      {col.referenced_fact_ids.length > 0 ? (
                        <div className="fact-pills-cell">
                          {col.referenced_fact_ids.map((fid) => (
                            <button
                              key={fid}
                              type="button"
                              className="fact-pill-mini"
                              title={computedFacts[fid]?.formatted_statement || fid}
                              onClick={() => onSelectFact?.(fid)}
                            >
                              #{fid}
                            </button>
                          ))}
                        </div>
                      ) : (
                        <span className="text-muted-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
