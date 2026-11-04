import React, { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import {
  filterDashboard,
  getCategoryDrilldown,
  getDatasetDashboard,
} from '../../services/api'
import type {
  DashboardResponse,
  DrillDownResponse,
  FilterRule,
} from '../../types/dashboard'
import { ChartExplorer } from './ChartExplorer'
import { ChartRecommendations } from './ChartRecommendations'
import { DashboardFilters } from './DashboardFilters'
import { DrillDownPanel } from './DrillDownPanel'
import { KPICard } from './KPICard'

interface DashboardOverviewProps {
  datasetId: string
  datasetFilename: string
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  datasetId,
  datasetFilename,
}) => {
  const [dashboardData, setDashboardData] = useState<DashboardResponse | null>(null)
  const [selectedNumericCol, setSelectedNumericCol] = useState<string | undefined>(undefined)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isFiltering, setIsFiltering] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Drilldown state
  const [drillDownData, setDrillDownData] = useState<DrillDownResponse | null>(null)
  const [isDrillDownLoading, setIsDrillDownLoading] = useState<boolean>(false)

  const fetchDashboard = useCallback(
    async (numericCol?: string) => {
      setIsLoading(true)
      setErrorMessage(null)
      try {
        const data = await getDatasetDashboard(datasetId, numericCol)
        setDashboardData(data)
        if (!selectedNumericCol && data.kpis.selected_column) {
          setSelectedNumericCol(data.kpis.selected_column)
        }
      } catch (err) {
        setErrorMessage(
          err instanceof Error
            ? err.message
            : 'Failed to load visual dashboard data.'
        )
      } finally {
        setIsLoading(false)
      }
    },
    [datasetId, selectedNumericCol]
  )

  useEffect(() => {
    fetchDashboard(selectedNumericCol)
  }, [datasetId])

  const handleSelectNumericColumn = (colName: string) => {
    setSelectedNumericCol(colName)
    fetchDashboard(colName)
  }

  const handleApplyFilters = async (filters: FilterRule[]) => {
    setIsFiltering(true)
    setErrorMessage(null)
    try {
      const updated = await filterDashboard(datasetId, {
        filters,
        selected_numeric_column: selectedNumericCol,
      })
      setDashboardData(updated)
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to apply filters.'
      )
    } finally {
      setIsFiltering(false)
    }
  }

  const handleResetFilters = async () => {
    fetchDashboard(selectedNumericCol)
  }

  const handleCategoryClick = async (column: string, value: string) => {
    setIsDrillDownLoading(true)
    setDrillDownData(null)
    try {
      const res = await getCategoryDrilldown(datasetId, {
        category_column: column,
        category_value: value,
        limit: 50,
        filters: dashboardData?.active_filters,
      })
      setDrillDownData(res)
    } catch (err) {
      alert(`Drill-down error: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsDrillDownLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="dashboard-loading-view">
        <div className="spinner-large" />
        <h4>Generating Automated Visual Dashboard...</h4>
        <p>Analyzing schema distributions, outlier bounds, and trend trajectories.</p>
      </div>
    )
  }

  if (errorMessage && !dashboardData) {
    return (
      <div className="dashboard-error-view">
        <AlertCircle size={32} />
        <h4>Dashboard Generation Error</h4>
        <p>{errorMessage}</p>
        <button
          type="button"
          className="button button-primary"
          onClick={() => fetchDashboard(selectedNumericCol)}
        >
          <RefreshCw size={15} /> Retry
        </button>
      </div>
    )
  }

  if (!dashboardData) {
    return null
  }

  return (
    <div className="visual-dashboard-container">
      {/* Dashboard Top Banner */}
      <div className="dashboard-top-banner">
        <div>
          <div className="eyebrow">
            <Sparkles size={13} /> AUTOMATED VISUAL DASHBOARDS
          </div>
          <h2>
            Visual Analytics: <span className="gradient-text">{datasetFilename}</span>
          </h2>
          <p>
            Real-time interactive charts, automated recommendations, and exploratory
            drill-downs powered by Pandas and Plotly.
          </p>
        </div>
      </div>

      {/* Dataset Filter Bar */}
      <DashboardFilters
        filterOptions={dashboardData.filter_options}
        activeFilters={dashboardData.active_filters}
        isFiltered={dashboardData.is_filtered}
        filteredRowCount={dashboardData.filtered_row_count}
        totalRowCount={dashboardData.total_row_count}
        onApplyFilters={handleApplyFilters}
        onResetFilters={handleResetFilters}
        isLoading={isFiltering}
      />

      {/* KPI Summary Cards */}
      <KPICard
        kpis={dashboardData.kpis}
        availableColumns={dashboardData.available_columns}
        onSelectNumericColumn={handleSelectNumericColumn}
      />

      {/* Recommended Charts Section */}
      <ChartRecommendations
        charts={dashboardData.recommended_charts}
        onCategoryClick={handleCategoryClick}
      />

      {/* Interactive Custom Chart Explorer */}
      <ChartExplorer
        datasetId={datasetId}
        availableColumns={dashboardData.available_columns}
        activeFilters={dashboardData.active_filters}
        onCategoryClick={handleCategoryClick}
      />

      {/* Drill-down slide-out panel */}
      {(drillDownData || isDrillDownLoading) && (
        <DrillDownPanel
          drillDownData={drillDownData}
          isLoading={isDrillDownLoading}
          onClose={() => setDrillDownData(null)}
        />
      )}
    </div>
  )
}
