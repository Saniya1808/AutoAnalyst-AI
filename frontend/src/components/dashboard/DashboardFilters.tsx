import React, { useState } from 'react'
import {
  Check,
  ChevronDown,
  RotateCcw,
  SlidersHorizontal,
  X,
} from 'lucide-react'
import type { FilterOptions, FilterRule } from '../../types/dashboard'

interface DashboardFiltersProps {
  filterOptions: FilterOptions
  activeFilters: FilterRule[]
  isFiltered: boolean
  filteredRowCount: number
  totalRowCount: number
  onApplyFilters: (filters: FilterRule[]) => void
  onResetFilters: () => void
  isLoading?: boolean
}

export const DashboardFilters: React.FC<DashboardFiltersProps> = ({
  filterOptions,
  activeFilters,
  isFiltered,
  filteredRowCount,
  totalRowCount,
  onApplyFilters,
  onResetFilters,
  isLoading = false,
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [draftFilters, setDraftFilters] = useState<FilterRule[]>(activeFilters)
  const [selectedColToAdd, setSelectedColToAdd] = useState<string>('')

  const catCols = Object.keys(filterOptions.categorical_filters)
  const numCols = Object.keys(filterOptions.numeric_filters)
  const dtCols = Object.keys(filterOptions.datetime_filters)
  const allFilterableCols = [...catCols, ...numCols, ...dtCols]

  const handleAddFilter = (colName: string) => {
    if (!colName) return

    // Prevent duplicates
    if (draftFilters.some((f) => f.column === colName)) {
      return
    }

    if (catCols.includes(colName)) {
      setDraftFilters([
        ...draftFilters,
        {
          column: colName,
          filter_type: 'categorical',
          selected_values: filterOptions.categorical_filters[colName].slice(0, 5),
        },
      ])
    } else if (numCols.includes(colName)) {
      const bounds = filterOptions.numeric_filters[colName]
      setDraftFilters([
        ...draftFilters,
        {
          column: colName,
          filter_type: 'numeric_range',
          min_val: bounds.min,
          max_val: bounds.max,
        },
      ])
    } else if (dtCols.includes(colName)) {
      const bounds = filterOptions.datetime_filters[colName]
      setDraftFilters([
        ...draftFilters,
        {
          column: colName,
          filter_type: 'datetime_range',
          start_date: bounds.min,
          end_date: bounds.max,
        },
      ])
    }
    setSelectedColToAdd('')
  }

  const handleRemoveDraftFilter = (colName: string) => {
    const updated = draftFilters.filter((f) => f.column !== colName)
    setDraftFilters(updated)
    // If we're removing an already applied filter, re-apply
    if (activeFilters.some((f) => f.column === colName)) {
      onApplyFilters(updated)
    }
  }

  const handleUpdateCategoricalVal = (col: string, val: string) => {
    setDraftFilters((prev) =>
      prev.map((f) => {
        if (f.column !== col) return f
        const currentVals = f.selected_values || []
        const exists = currentVals.includes(val)
        const newVals = exists
          ? currentVals.filter((v) => v !== val)
          : [...currentVals, val]
        return { ...f, selected_values: newVals }
      })
    )
  }

  const handleUpdateNumericRange = (col: string, min?: number | null, max?: number | null) => {
    setDraftFilters((prev) =>
      prev.map((f) => {
        if (f.column !== col) return f
        return {
          ...f,
          min_val: min !== undefined ? min : f.min_val,
          max_val: max !== undefined ? max : f.max_val,
        }
      })
    )
  }

  const handleApply = () => {
    onApplyFilters(draftFilters)
    setIsOpen(false)
  }

  const handleReset = () => {
    setDraftFilters([])
    onResetFilters()
    setIsOpen(false)
  }

  return (
    <div className="dashboard-filters-panel">
      <div className="filters-bar-header">
        <div className="filters-title-group">
          <button
            type="button"
            className="filter-toggle-btn"
            onClick={() => setIsOpen(!isOpen)}
          >
            <SlidersHorizontal size={15} />
            <span>Dataset Filters</span>
            {activeFilters.length > 0 && (
              <span className="active-filters-badge">{activeFilters.length}</span>
            )}
            <ChevronDown size={14} className={isOpen ? 'rotate-180' : ''} />
          </button>

          {isFiltered && (
            <div className="filter-summary-pill">
              <span className="dot-filtered" />
              <span>
                Showing <strong>{filteredRowCount.toLocaleString()}</strong> of{' '}
                {totalRowCount.toLocaleString()} rows
              </span>
            </div>
          )}
        </div>

        <div className="filters-actions-right">
          {isFiltered && (
            <button
              type="button"
              className="reset-filters-btn"
              onClick={handleReset}
              disabled={isLoading}
              title="Clear all filters and restore full dataset"
            >
              <RotateCcw size={13} /> Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Active filter pills */}
      {activeFilters.length > 0 && (
        <div className="active-filter-pills-row">
          {activeFilters.map((f) => (
            <div key={f.column} className="filter-pill">
              <span className="pill-col">{f.column}:</span>
              {f.filter_type === 'categorical' && (
                <span className="pill-val">
                  {f.selected_values?.join(', ') || 'None'}
                </span>
              )}
              {f.filter_type === 'numeric_range' && (
                <span className="pill-val">
                  {f.min_val} to {f.max_val}
                </span>
              )}
              {f.filter_type === 'datetime_range' && (
                <span className="pill-val">
                  {f.start_date?.split('T')[0]} to {f.end_date?.split('T')[0]}
                </span>
              )}
              <button
                type="button"
                className="pill-remove-btn"
                onClick={() => handleRemoveDraftFilter(f.column)}
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Expandable Filter Configuration Drawer */}
      {isOpen && (
        <div className="filter-drawer-content">
          <div className="add-filter-row">
            <span className="add-filter-label">Add a Column Filter:</span>
            <select
              className="select-input-sm"
              value={selectedColToAdd}
              onChange={(e) => {
                setSelectedColToAdd(e.target.value)
                handleAddFilter(e.target.value)
              }}
            >
              <option value="">Choose column...</option>
              {allFilterableCols.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {draftFilters.length > 0 && (
            <div className="filter-rules-list">
              {draftFilters.map((rule) => {
                const isCat = rule.filter_type === 'categorical'
                const isNum = rule.filter_type === 'numeric_range'

                return (
                  <div key={rule.column} className="filter-rule-card">
                    <div className="rule-card-top">
                      <strong>{rule.column}</strong>
                      <span className="rule-type-tag">{rule.filter_type}</span>
                      <button
                        type="button"
                        className="rule-remove-btn"
                        onClick={() => handleRemoveDraftFilter(rule.column)}
                      >
                        <X size={14} />
                      </button>
                    </div>

                    {isCat && filterOptions.categorical_filters[rule.column] && (
                      <div className="cat-options-grid">
                        {filterOptions.categorical_filters[rule.column].map((val) => {
                          const isSelected = rule.selected_values?.includes(val)
                          return (
                            <button
                              key={val}
                              type="button"
                              className={`cat-opt-chip ${isSelected ? 'selected' : ''}`}
                              onClick={() => handleUpdateCategoricalVal(rule.column, val)}
                            >
                              {isSelected && <Check size={12} />}
                              <span>{val}</span>
                            </button>
                          )
                        })}
                      </div>
                    )}

                    {isNum && filterOptions.numeric_filters[rule.column] && (
                      <div className="num-range-inputs">
                        <label>
                          Min:
                          <input
                            type="number"
                            className="input-num-sm"
                            value={rule.min_val ?? ''}
                            onChange={(e) =>
                              handleUpdateNumericRange(
                                rule.column,
                                parseFloat(e.target.value),
                                rule.max_val
                              )
                            }
                          />
                        </label>
                        <span>to</span>
                        <label>
                          Max:
                          <input
                            type="number"
                            className="input-num-sm"
                            value={rule.max_val ?? ''}
                            onChange={(e) =>
                              handleUpdateNumericRange(
                                rule.column,
                                rule.min_val,
                                parseFloat(e.target.value)
                              )
                            }
                          />
                        </label>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          <div className="drawer-footer-actions">
            <button
              type="button"
              className="button button-primary"
              onClick={handleApply}
              disabled={isLoading}
            >
              Apply Filter Selection
            </button>
            <button
              type="button"
              className="button button-quiet"
              onClick={() => setIsOpen(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
