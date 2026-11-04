import React, { useState } from 'react'
import {
  AlertCircle,
  BarChart2,
  Box,
  Compass,
  LineChart,
  PieChart,
  RefreshCw,
  ScatterChart,
} from 'lucide-react'
import { generateCustomChart } from '../../services/api'
import type {
  ChartConfig,
  ColumnInfo,
  CustomChartRequest,
  FilterRule,
} from '../../types/dashboard'
import { InteractiveChart } from './InteractiveChart'

interface ChartExplorerProps {
  datasetId: string
  availableColumns: ColumnInfo[]
  activeFilters: FilterRule[]
  onCategoryClick?: (column: string, value: string) => void
}

type SupportedChartType = 'bar' | 'line' | 'scatter' | 'histogram' | 'box' | 'pie'

export const ChartExplorer: React.FC<ChartExplorerProps> = ({
  datasetId,
  availableColumns,
  activeFilters,
  onCategoryClick,
}) => {
  const [chartType, setChartType] = useState<SupportedChartType>('bar')
  const [xColumn, setXColumn] = useState<string>(
    availableColumns[0]?.name || ''
  )
  const [yColumn, setYColumn] = useState<string>('')
  const [groupColumn, setGroupColumn] = useState<string>('')
  const [aggregation, setAggregation] = useState<'sum' | 'avg' | 'count' | 'min' | 'max'>('count')

  const [generatedChart, setGeneratedChart] = useState<ChartConfig | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const numericCols = availableColumns.filter(
    (c) => c.data_type === 'integer' || c.data_type === 'float'
  )

  const handleGenerate = async () => {
    setIsLoading(true)
    setErrorMessage(null)

    const req: CustomChartRequest = {
      chart_type: chartType,
      x_column: xColumn || undefined,
      y_column: yColumn || undefined,
      group_column: groupColumn || undefined,
      aggregation: aggregation,
      filters: activeFilters.length > 0 ? activeFilters : undefined,
    }

    try {
      const chart = await generateCustomChart(datasetId, req)
      setGeneratedChart(chart)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to generate custom chart.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="chart-explorer-card">
      <div className="explorer-header">
        <div className="explorer-title-group">
          <div className="explorer-icon">
            <Compass size={20} />
          </div>
          <div>
            <h3>Interactive Chart Explorer</h3>
            <p>Configure custom axes, chart types, and aggregations dynamically.</p>
          </div>
        </div>
      </div>

      <div className="explorer-form-grid">
        {/* Chart Type Selector */}
        <div className="form-group">
          <label>CHART TYPE</label>
          <div className="chart-type-selector-buttons">
            <button
              type="button"
              className={`type-select-btn ${chartType === 'bar' ? 'active' : ''}`}
              onClick={() => {
                setChartType('bar')
                setAggregation('count')
              }}
            >
              <BarChart2 size={14} /> Bar
            </button>
            <button
              type="button"
              className={`type-select-btn ${chartType === 'line' ? 'active' : ''}`}
              onClick={() => {
                setChartType('line')
                setAggregation('avg')
              }}
            >
              <LineChart size={14} /> Line
            </button>
            <button
              type="button"
              className={`type-select-btn ${chartType === 'scatter' ? 'active' : ''}`}
              onClick={() => setChartType('scatter')}
            >
              <ScatterChart size={14} /> Scatter
            </button>
            <button
              type="button"
              className={`type-select-btn ${chartType === 'histogram' ? 'active' : ''}`}
              onClick={() => setChartType('histogram')}
            >
              <BarChart2 size={14} /> Histogram
            </button>
            <button
              type="button"
              className={`type-select-btn ${chartType === 'box' ? 'active' : ''}`}
              onClick={() => setChartType('box')}
            >
              <Box size={14} /> Box Plot
            </button>
            <button
              type="button"
              className={`type-select-btn ${chartType === 'pie' ? 'active' : ''}`}
              onClick={() => setChartType('pie')}
            >
              <PieChart size={14} /> Donut/Pie
            </button>
          </div>
        </div>

        {/* X-Axis Selector */}
        <div className="form-group">
          <label>X-AXIS COLUMN</label>
          <select
            className="input-select"
            value={xColumn}
            onChange={(e) => setXColumn(e.target.value)}
          >
            <option value="">Select column...</option>
            {availableColumns.map((col) => (
              <option key={col.name} value={col.name}>
                {col.name} ({col.data_type})
              </option>
            ))}
          </select>
        </div>

        {/* Y-Axis Selector (when applicable) */}
        {chartType !== 'histogram' && (
          <div className="form-group">
            <label>Y-AXIS COLUMN (NUMERIC)</label>
            <select
              className="input-select"
              value={yColumn}
              onChange={(e) => setYColumn(e.target.value)}
            >
              <option value="">None / Row Count</option>
              {numericCols.map((col) => (
                <option key={col.name} value={col.name}>
                  {col.name} ({col.data_type})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Aggregation Selector (when applicable) */}
        {(chartType === 'bar' || chartType === 'line' || chartType === 'pie') && yColumn && (
          <div className="form-group">
            <label>AGGREGATION</label>
            <select
              className="input-select"
              value={aggregation}
              onChange={(e) =>
                setAggregation(
                  e.target.value as 'sum' | 'avg' | 'count' | 'min' | 'max'
                )
              }
            >
              <option value="sum">Sum</option>
              <option value="avg">Average (Mean)</option>
              <option value="min">Minimum</option>
              <option value="max">Maximum</option>
              <option value="count">Count</option>
            </select>
          </div>
        )}

        {/* Grouping Column (when applicable) */}
        {chartType === 'box' && (
          <div className="form-group">
            <label>GROUP BY COLUMN (OPTIONAL)</label>
            <select
              className="input-select"
              value={groupColumn}
              onChange={(e) => setGroupColumn(e.target.value)}
            >
              <option value="">No grouping</option>
              {availableColumns.map((col) => (
                <option key={col.name} value={col.name}>
                  {col.name} ({col.data_type})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="explorer-action-row">
        <button
          type="button"
          className="button button-primary"
          onClick={handleGenerate}
          disabled={isLoading || !xColumn}
        >
          {isLoading ? (
            <>
              <RefreshCw size={15} className="spin-animation" />
              <span>Generating...</span>
            </>
          ) : (
            <>
              <RefreshCw size={15} />
              <span>Generate Custom Chart</span>
            </>
          )}
        </button>
      </div>

      {/* Error message if generation fails */}
      {errorMessage && (
        <div className="explorer-error-banner">
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Display Generated Chart */}
      {generatedChart && (
        <div className="generated-chart-container">
          <div className="generated-chart-header">
            <h4>{generatedChart.title}</h4>
            <span className="badge-custom">CUSTOM EXPLORER</span>
          </div>
          <InteractiveChart
            chart={generatedChart}
            onCategoryClick={onCategoryClick}
            height={380}
          />
        </div>
      )}
    </div>
  )
}

