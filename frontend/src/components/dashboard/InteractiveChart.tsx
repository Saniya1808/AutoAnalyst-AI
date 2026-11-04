import React, { useEffect, useRef } from 'react'
import Plotly from 'plotly.js-dist-min'
import { useTheme } from '../../hooks/useTheme'
import type { ChartConfig } from '../../types/dashboard'

interface InteractiveChartProps {
  chart: ChartConfig
  onCategoryClick?: (column: string, value: string) => void
  height?: number
}

export const InteractiveChart: React.FC<InteractiveChartProps> = ({
  chart,
  onCategoryClick,
  height = 360,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const { theme } = useTheme()

  useEffect(() => {
    if (!containerRef.current) return

    const isDark = theme === 'dark'
    const textColor = isDark ? '#eef2ff' : '#0f172a'
    const gridColor = isDark
      ? 'rgba(150, 169, 210, 0.14)'
      : 'rgba(58, 75, 115, 0.12)'
    const axisColor = isDark ? '#929bb2' : '#64748b'

    const layoutDefaults: Record<string, unknown> = {
      autosize: true,
      height: height,
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: {
        family:
          'DM Sans, system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
        color: textColor,
        size: 12,
      },
      title: {
        text: chart.title,
        font: {
          size: 15,
          color: textColor,
          weight: 700,
        },
        x: 0.04,
        y: 0.95,
      },
      xaxis: {
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        tickfont: { color: axisColor, size: 11 },
        title: { font: { color: textColor, size: 12 } },
      },
      yaxis: {
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        tickfont: { color: axisColor, size: 11 },
        title: { font: { color: textColor, size: 12 } },
      },
      legend: {
        font: { color: textColor, size: 11 },
        orientation: 'h',
        y: -0.2,
      },
      margin: { l: 50, r: 30, t: 50, b: 50 },
    }

    const mergedLayout = {
      ...layoutDefaults,
      ...chart.plotly_layout,
      xaxis: {
        ...(layoutDefaults.xaxis as object),
        ...(chart.plotly_layout.xaxis as object),
      },
      yaxis: {
        ...(layoutDefaults.yaxis as object),
        ...(chart.plotly_layout.yaxis as object),
      },
    }

    const config: Record<string, unknown> = {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: [
        'lasso2d',
        'select2d',
        'toggleSpikelines',
        'hoverCompareCartesian',
      ],
      toImageButtonOptions: {
        format: 'png',
        filename: `${chart.title.toLowerCase().replace(/[^a-z0-9]/g, '_')}`,
        height: 500,
        width: 800,
        scale: 2,
      },
    }

    // Render Plotly plot
    Plotly.react(
      containerRef.current,
      chart.plotly_data as unknown as Plotly.Data[],
      mergedLayout as unknown as Partial<Plotly.Layout>,
      config
    )

    // Attach click handler for drill-down
    const currentContainer = containerRef.current
    const clickHandler = (data: { points?: Array<{ x?: unknown; label?: unknown }> }) => {
      if (!onCategoryClick || !data || !data.points || data.points.length === 0) {
        return
      }
      const pt = data.points[0]
      const clickedVal = pt.label ?? pt.x
      if (clickedVal !== undefined && chart.x_column) {
        onCategoryClick(chart.x_column, String(clickedVal))
      }
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(currentContainer as any).on?.('plotly_click', clickHandler)

    // Handle responsive container resize
    const handleResize = () => {
      if (containerRef.current) {
        Plotly.Plots.resize(containerRef.current)
      }
    }

    const resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(containerRef.current)
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      resizeObserver.disconnect()
      if (currentContainer) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ;(currentContainer as any).removeAllListeners?.('plotly_click')
        Plotly.purge(currentContainer)
      }
    }
  }, [chart, theme, height, onCategoryClick])

  return (
    <div className="interactive-chart-wrapper">
      <div ref={containerRef} className="plotly-plot-container" />
      {chart.description && (
        <p className="chart-description-caption">{chart.description}</p>
      )}
    </div>
  )
}

