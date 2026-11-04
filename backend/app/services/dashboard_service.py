import math
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
import numpy as np
import pandas as pd

from app.core.json_encoder import sanitize_for_json
from app.models.dashboard import (
    ChartConfig,
    ColumnInfo,
    CustomChartRequest,
    DashboardKPI,
    DashboardResponse,
    DrillDownRequest,
    DrillDownResponse,
    FilterOptions,
    FilterRule,
)
from app.services.profiler import infer_column_type

# Color palette aligned with AutoAnalyst AI design tokens
THEME_COLORS = [
    "#8b7cff",  # electric purple / accent
    "#36c9f4",  # cyan / accent-2
    "#34d399",  # emerald green
    "#fbbf24",  # amber
    "#f472b6",  # pink
    "#a78bfa",  # light purple
    "#60a5fa",  # blue
    "#fb923c",  # orange
]


class DashboardService:
    @staticmethod
    def _validate_column_exists(df: pd.DataFrame, col_name: str) -> None:
        if col_name not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{col_name}' does not exist in dataset. Available columns: {list(df.columns)}",
            )

    @classmethod
    def apply_filters(cls, df: pd.DataFrame, filters: List[FilterRule]) -> pd.DataFrame:
        """Safely apply a list of categorical, numeric range, and datetime range filters."""
        if not filters:
            return df

        filtered = df.copy()

        for rule in filters:
            col = rule.column
            cls._validate_column_exists(filtered, col)

            if rule.filter_type == "categorical":
                if rule.selected_values is not None:
                    # Convert to string for consistent comparison
                    str_vals = set(str(v) for v in rule.selected_values)
                    mask = filtered[col].astype(str).isin(str_vals)
                    filtered = filtered[mask]

            elif rule.filter_type == "numeric_range":
                nums = pd.to_numeric(filtered[col], errors="coerce")
                mask = pd.Series(True, index=filtered.index)
                if rule.min_val is not None:
                    mask &= nums >= rule.min_val
                if rule.max_val is not None:
                    mask &= nums <= rule.max_val
                filtered = filtered[mask]

            elif rule.filter_type == "datetime_range":
                dates = pd.to_datetime(filtered[col], errors="coerce")
                mask = pd.Series(True, index=filtered.index)
                if rule.start_date:
                    try:
                        dt_start = pd.to_datetime(rule.start_date)
                        mask &= dates >= dt_start
                    except Exception:
                        pass
                if rule.end_date:
                    try:
                        dt_end = pd.to_datetime(rule.end_date)
                        mask &= dates <= dt_end
                    except Exception:
                        pass
                filtered = filtered[mask]

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported filter type '{rule.filter_type}' for column '{col}'",
                )

        return filtered

    @classmethod
    def calculate_kpis(
        cls, df: pd.DataFrame, selected_col: Optional[str] = None
    ) -> DashboardKPI:
        """Calculate executive KPI summary cards from active (filtered) DataFrame."""
        total_rows = len(df)
        total_columns = len(df.columns)
        total_cells = total_rows * total_columns
        missing_cells = int(df.isna().sum().sum())
        missing_percentage = (
            round((missing_cells / total_cells * 100.0), 2) if total_cells > 0 else 0.0
        )

        try:
            duplicate_rows = int(df.duplicated().sum())
        except Exception:
            duplicate_rows = 0
        duplicate_percentage = (
            round((duplicate_rows / total_rows * 100.0), 2) if total_rows > 0 else 0.0
        )
        data_completeness = round(100.0 - missing_percentage, 2)

        selected_stats = None
        if selected_col:
            cls._validate_column_exists(df, selected_col)
            clean_series = pd.to_numeric(df[selected_col], errors="coerce").dropna()
            if len(clean_series) > 0:
                selected_stats = {
                    "column": selected_col,
                    "count": int(clean_series.count()),
                    "sum": round(float(clean_series.sum()), 2),
                    "average": round(float(clean_series.mean()), 2),
                    "minimum": round(float(clean_series.min()), 2),
                    "maximum": round(float(clean_series.max()), 2),
                    "std": round(float(clean_series.std(ddof=1)), 2)
                    if len(clean_series) > 1
                    else None,
                    "zeros_count": int((clean_series == 0).sum()),
                }
            else:
                selected_stats = {
                    "column": selected_col,
                    "count": 0,
                    "sum": 0.0,
                    "average": None,
                    "minimum": None,
                    "maximum": None,
                    "std": None,
                    "zeros_count": 0,
                }

        return DashboardKPI(
            total_rows=total_rows,
            total_columns=total_columns,
            total_cells=total_cells,
            missing_cells=missing_cells,
            missing_percentage=missing_percentage,
            duplicate_rows=duplicate_rows,
            duplicate_percentage=duplicate_percentage,
            data_completeness=data_completeness,
            selected_column=selected_col,
            selected_column_stats=sanitize_for_json(selected_stats),
        )

    @classmethod
    def get_filter_options(cls, df: pd.DataFrame) -> FilterOptions:
        """Extract bounds and unique values for dashboard filter controls."""
        categorical_filters: Dict[str, List[str]] = {}
        numeric_filters: Dict[str, Dict[str, float]] = {}
        datetime_filters: Dict[str, Dict[str, str]] = {}

        for col in df.columns:
            series = df[col]
            sem_type = infer_column_type(series)

            if sem_type in ("integer", "float"):
                nums = pd.to_numeric(series, errors="coerce").dropna()
                if len(nums) > 0:
                    min_v = float(nums.min())
                    max_v = float(nums.max())
                    if not (math.isnan(min_v) or math.isnan(max_v) or math.isinf(min_v) or math.isinf(max_v)):
                        numeric_filters[col] = {
                            "min": round(min_v, 2),
                            "max": round(max_v, 2),
                        }

            elif sem_type == "datetime":
                dts = pd.to_datetime(series, errors="coerce").dropna()
                if len(dts) > 0:
                    datetime_filters[col] = {
                        "min": dts.min().isoformat(),
                        "max": dts.max().isoformat(),
                    }

            # For categorical or low-cardinality integers, offer categorical filter
            unique_count = series.nunique(dropna=True)
            if sem_type in ("string", "boolean") or (sem_type == "integer" and unique_count <= 25):
                if 1 <= unique_count <= 60:
                    vals = sorted([str(v) for v in series.dropna().unique()])
                    categorical_filters[col] = vals

        return FilterOptions(
            categorical_filters=categorical_filters,
            numeric_filters=numeric_filters,
            datetime_filters=datetime_filters,
        )

    @classmethod
    def recommend_charts(cls, df: pd.DataFrame, max_charts: int = 6) -> List[ChartConfig]:
        """Automatically analyze dataset schema and recommend up to 6 diverse, meaningful charts."""
        charts: List[ChartConfig] = []
        if df.empty or len(df.columns) == 0:
            return charts

        numeric_cols = [c for c in df.columns if infer_column_type(df[c]) in ("integer", "float")]
        cat_cols = [c for c in df.columns if infer_column_type(df[c]) in ("string", "boolean")]
        dt_cols = [c for c in df.columns if infer_column_type(df[c]) == "datetime"]

        # If no explicit datetime column, check if any column name suggests date and parses well
        if not dt_cols:
            for c in df.columns:
                if c.lower().endswith(("date", "time", "dt", "year", "month")):
                    parsed = pd.to_datetime(df[c], errors="coerce")
                    if parsed.notna().mean() > 0.7:
                        dt_cols.append(c)
                        if c in cat_cols:
                            cat_cols.remove(c)
                        break

        # 1. Categorical + Numeric Aggregation (Bar Chart)
        for cat in cat_cols:
            nunique = df[cat].nunique(dropna=True)
            if 2 <= nunique <= 25 and numeric_cols:
                num = numeric_cols[0]
                grouped = df.groupby(cat)[num].agg(["sum", "mean"]).reset_index()
                grouped = grouped.sort_values(by="sum", ascending=False).head(15)

                x_vals = grouped[cat].astype(str).tolist()
                y_vals = [round(float(v), 2) for v in grouped["sum"]]

                charts.append(
                    ChartConfig(
                        chart_id=f"rec_bar_{cat}_{num}",
                        title=f"Total {num} by {cat}",
                        chart_type="bar",
                        x_column=cat,
                        y_column=num,
                        aggregation="sum",
                        description=f"Aggregated sum of {num} grouped by {cat}.",
                        plotly_data=[
                            {
                                "x": x_vals,
                                "y": y_vals,
                                "type": "bar",
                                "marker": {"color": THEME_COLORS[0]},
                                "name": num,
                            }
                        ],
                        plotly_layout={
                            "title": {"text": f"Total {num} by {cat}"},
                            "xaxis": {"title": cat, "automargin": True},
                            "yaxis": {"title": f"Sum of {num}", "automargin": True},
                            "margin": {"l": 50, "r": 30, "t": 50, "b": 60},
                        },
                    )
                )
                break

        # 2. Datetime + Numeric Trend (Line Chart)
        if dt_cols and numeric_cols:
            dt_col = dt_cols[0]
            num_col = numeric_cols[0]
            temp_df = df[[dt_col, num_col]].dropna().copy()
            temp_df["_dt_parsed"] = pd.to_datetime(temp_df[dt_col], errors="coerce")
            temp_df = temp_df.dropna(subset=["_dt_parsed"]).sort_values(by="_dt_parsed")

            if len(temp_df) > 1:
                # Group by date or day if many rows
                temp_df["_date_str"] = temp_df["_dt_parsed"].dt.strftime("%Y-%m-%d")
                trend = temp_df.groupby("_date_str")[num_col].mean().reset_index()

                charts.append(
                    ChartConfig(
                        chart_id=f"rec_line_{dt_col}_{num_col}",
                        title=f"{num_col} Trend Over Time",
                        chart_type="line",
                        x_column=dt_col,
                        y_column=num_col,
                        aggregation="avg",
                        description=f"Chronological trajectory of {num_col} across {dt_col}.",
                        plotly_data=[
                            {
                                "x": trend["_date_str"].tolist(),
                                "y": [round(float(v), 2) for v in trend[num_col]],
                                "type": "scatter",
                                "mode": "lines+markers",
                                "line": {"color": THEME_COLORS[1], "width": 2.5},
                                "marker": {"size": 6},
                                "name": f"Avg {num_col}",
                            }
                        ],
                        plotly_layout={
                            "title": {"text": f"{num_col} Trend Over Time"},
                            "xaxis": {"title": dt_col, "automargin": True},
                            "yaxis": {"title": f"Avg {num_col}", "automargin": True},
                            "margin": {"l": 50, "r": 30, "t": 50, "b": 60},
                        },
                    )
                )

        # 3. Two Numeric Relationship (Scatter Plot)
        if len(numeric_cols) >= 2:
            x_num = numeric_cols[0]
            y_num = numeric_cols[1]
            scatter_df = df[[x_num, y_num]].dropna()
            # Subsample if large
            if len(scatter_df) > 1000:
                scatter_df = scatter_df.sample(n=1000, random_state=42)

            charts.append(
                ChartConfig(
                    chart_id=f"rec_scatter_{x_num}_{y_num}",
                    title=f"Correlation: {x_num} vs {y_num}",
                    chart_type="scatter",
                    x_column=x_num,
                    y_column=y_num,
                    description=f"Scatter plot investigating the relationship between {x_num} and {y_num}.",
                    plotly_data=[
                        {
                            "x": [round(float(v), 3) for v in scatter_df[x_num]],
                            "y": [round(float(v), 3) for v in scatter_df[y_num]],
                            "type": "scatter",
                            "mode": "markers",
                            "marker": {
                                "color": THEME_COLORS[2],
                                "size": 7,
                                "opacity": 0.75,
                            },
                            "name": f"{x_num} vs {y_num}",
                        }
                    ],
                    plotly_layout={
                        "title": {"text": f"{x_num} vs {y_num}"},
                        "xaxis": {"title": x_num, "automargin": True},
                        "yaxis": {"title": y_num, "automargin": True},
                        "margin": {"l": 50, "r": 30, "t": 50, "b": 60},
                    },
                )
            )

        # 4. Low-cardinality Categorical Composition (Donut/Pie Chart)
        for cat in cat_cols:
            nunique = df[cat].nunique(dropna=True)
            if 2 <= nunique <= 7:
                counts = df[cat].astype(str).value_counts().head(7)
                charts.append(
                    ChartConfig(
                        chart_id=f"rec_pie_{cat}",
                        title=f"{cat} Distribution",
                        chart_type="pie",
                        x_column=cat,
                        description=f"Proportional breakdown across {cat} segments.",
                        plotly_data=[
                            {
                                "labels": counts.index.tolist(),
                                "values": counts.values.tolist(),
                                "type": "pie",
                                "hole": 0.45,
                                "marker": {"colors": THEME_COLORS[: len(counts)]},
                                "textinfo": "label+percent",
                            }
                        ],
                        plotly_layout={
                            "title": {"text": f"{cat} Composition"},
                            "margin": {"l": 30, "r": 30, "t": 50, "b": 40},
                        },
                    )
                )
                break

        # 5. Numeric Distribution (Histogram)
        if numeric_cols:
            # Pick a numeric column not yet displayed or the primary one
            num = numeric_cols[-1] if len(numeric_cols) > 2 else numeric_cols[0]
            clean_num = pd.to_numeric(df[num], errors="coerce").dropna()
            if len(clean_num) > 0:
                charts.append(
                    ChartConfig(
                        chart_id=f"rec_hist_{num}",
                        title=f"{num} Distribution (Histogram)",
                        chart_type="histogram",
                        x_column=num,
                        description=f"Frequency distribution and bin spread for {num}.",
                        plotly_data=[
                            {
                                "x": [round(float(v), 2) for v in clean_num],
                                "type": "histogram",
                                "marker": {"color": THEME_COLORS[3]},
                                "name": num,
                            }
                        ],
                        plotly_layout={
                            "title": {"text": f"{num} Distribution"},
                            "xaxis": {"title": num, "automargin": True},
                            "yaxis": {"title": "Frequency", "automargin": True},
                            "margin": {"l": 50, "r": 30, "t": 50, "b": 60},
                        },
                    )
                )

        # 6. Numeric Outliers & Spread (Box Plot)
        if numeric_cols:
            target_num = numeric_cols[0]
            clean_num = pd.to_numeric(df[target_num], errors="coerce").dropna()
            if len(clean_num) > 0:
                charts.append(
                    ChartConfig(
                        chart_id=f"rec_box_{target_num}",
                        title=f"{target_num} Outliers & Spread (Box Plot)",
                        chart_type="box",
                        y_column=target_num,
                        description=f"Interquartile ranges, median, and outlier detection for {target_num}.",
                        plotly_data=[
                            {
                                "y": [round(float(v), 2) for v in clean_num],
                                "type": "box",
                                "marker": {"color": THEME_COLORS[4]},
                                "name": target_num,
                                "boxpoints": "outliers",
                            }
                        ],
                        plotly_layout={
                            "title": {"text": f"{target_num} Box Plot"},
                            "yaxis": {"title": target_num, "automargin": True},
                            "margin": {"l": 50, "r": 30, "t": 50, "b": 40},
                        },
                    )
                )

        # Ensure we return at most max_charts
        return charts[:max_charts]

    @classmethod
    def generate_custom_chart(
        cls, df: pd.DataFrame, req: CustomChartRequest
    ) -> ChartConfig:
        """Dynamically generate a validated Plotly chart according to user configuration."""
        valid_types = ["bar", "line", "scatter", "histogram", "box", "pie"]
        if req.chart_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid chart type '{req.chart_type}'. Supported types: {valid_types}",
            )

        # Apply active filters if provided
        active_df = cls.apply_filters(df, req.filters or [])
        if active_df.empty:
            raise HTTPException(
                status_code=400,
                detail="No data available matching the selected filters.",
            )

        # Validation per chart type
        chart_id = f"custom_{req.chart_type}_{abs(hash(str(req)))}"

        if req.chart_type == "histogram":
            if not req.x_column:
                raise HTTPException(status_code=400, detail="Histogram requires an X-axis column.")
            cls._validate_column_exists(active_df, req.x_column)
            clean_series = pd.to_numeric(active_df[req.x_column], errors="coerce").dropna()
            if len(clean_series) == 0:
                raise HTTPException(status_code=400, detail=f"Column '{req.x_column}' contains no numeric values.")

            return ChartConfig(
                chart_id=chart_id,
                title=f"Histogram of {req.x_column}",
                chart_type="histogram",
                x_column=req.x_column,
                plotly_data=[
                    {
                        "x": [round(float(v), 3) for v in clean_series],
                        "type": "histogram",
                        "marker": {"color": THEME_COLORS[0]},
                        "name": req.x_column,
                    }
                ],
                plotly_layout={
                    "title": {"text": f"Histogram: {req.x_column}"},
                    "xaxis": {"title": req.x_column, "automargin": True},
                    "yaxis": {"title": "Count", "automargin": True},
                    "margin": {"l": 50, "r": 30, "t": 50, "b": 60},
                },
            )

        elif req.chart_type == "box":
            target_col = req.y_column or req.x_column
            if not target_col:
                raise HTTPException(status_code=400, detail="Box plot requires a numeric column.")
            cls._validate_column_exists(active_df, target_col)
            clean_series = pd.to_numeric(active_df[target_col], errors="coerce").dropna()
            if len(clean_series) == 0:
                raise HTTPException(status_code=400, detail=f"Column '{target_col}' has no numeric data.")

            plotly_data = []
            if req.group_column:
                cls._validate_column_exists(active_df, req.group_column)
                # Grouped box plot
                groups = active_df[req.group_column].dropna().unique()[:10]
                for idx, g in enumerate(groups):
                    sub = active_df[active_df[req.group_column] == g]
                    y_sub = pd.to_numeric(sub[target_col], errors="coerce").dropna()
                    if len(y_sub) > 0:
                        plotly_data.append(
                            {
                                "y": [round(float(v), 3) for v in y_sub],
                                "type": "box",
                                "name": str(g),
                                "marker": {"color": THEME_COLORS[idx % len(THEME_COLORS)]},
                            }
                        )
            else:
                plotly_data = [
                    {
                        "y": [round(float(v), 3) for v in clean_series],
                        "type": "box",
                        "name": target_col,
                        "marker": {"color": THEME_COLORS[1]},
                        "boxpoints": "outliers",
                    }
                ]

            return ChartConfig(
                chart_id=chart_id,
                title=f"Box Plot of {target_col}",
                chart_type="box",
                y_column=target_col,
                group_column=req.group_column,
                plotly_data=plotly_data,
                plotly_layout={
                    "title": {"text": f"Box Plot: {target_col}"},
                    "yaxis": {"title": target_col, "automargin": True},
                    "margin": {"l": 50, "r": 30, "t": 50, "b": 50},
                },
            )

        elif req.chart_type == "scatter":
            if not req.x_column or not req.y_column:
                raise HTTPException(status_code=400, detail="Scatter plot requires both X and Y columns.")
            cls._validate_column_exists(active_df, req.x_column)
            cls._validate_column_exists(active_df, req.y_column)

            sub_df = active_df[[req.x_column, req.y_column]].dropna()
            if len(sub_df) > 1500:
                sub_df = sub_df.sample(n=1500, random_state=42)

            return ChartConfig(
                chart_id=chart_id,
                title=f"{req.x_column} vs {req.y_column} (Scatter)",
                chart_type="scatter",
                x_column=req.x_column,
                y_column=req.y_column,
                plotly_data=[
                    {
                        "x": [round(float(v), 3) for v in sub_df[req.x_column]],
                        "y": [round(float(v), 3) for v in sub_df[req.y_column]],
                        "type": "scatter",
                        "mode": "markers",
                        "marker": {"color": THEME_COLORS[2], "size": 7, "opacity": 0.8},
                        "name": f"{req.x_column} vs {req.y_column}",
                    }
                ],
                plotly_layout={
                    "title": {"text": f"{req.x_column} vs {req.y_column}"},
                    "xaxis": {"title": req.x_column, "automargin": True},
                    "yaxis": {"title": req.y_column, "automargin": True},
                    "margin": {"l": 50, "r": 30, "t": 50, "b": 60},
                },
            )

        elif req.chart_type == "pie":
            if not req.x_column:
                raise HTTPException(status_code=400, detail="Pie chart requires a category column.")
            cls._validate_column_exists(active_df, req.x_column)

            if req.y_column and req.aggregation:
                cls._validate_column_exists(active_df, req.y_column)
                agg_func = "sum" if req.aggregation == "sum" else "mean"
                grouped = (
                    active_df.groupby(req.x_column)[req.y_column]
                    .agg(agg_func)
                    .dropna()
                    .sort_values(ascending=False)
                    .head(10)
                )
                labels = [str(x) for x in grouped.index]
                values = [round(float(v), 2) for v in grouped.values]
            else:
                counts = active_df[req.x_column].astype(str).value_counts().head(10)
                labels = counts.index.tolist()
                values = counts.values.tolist()

            return ChartConfig(
                chart_id=chart_id,
                title=f"{req.x_column} Proportions",
                chart_type="pie",
                x_column=req.x_column,
                plotly_data=[
                    {
                        "labels": labels,
                        "values": values,
                        "type": "pie",
                        "hole": 0.4,
                        "marker": {"colors": THEME_COLORS[: len(labels)]},
                    }
                ],
                plotly_layout={
                    "title": {"text": f"{req.x_column} Composition"},
                    "margin": {"l": 30, "r": 30, "t": 50, "b": 40},
                },
            )

        elif req.chart_type in ("bar", "line"):
            if not req.x_column:
                raise HTTPException(status_code=400, detail=f"{req.chart_type.capitalize()} chart requires an X-axis column.")
            cls._validate_column_exists(active_df, req.x_column)

            valid_aggs = ["sum", "avg", "average", "mean", "count", "min", "max"]
            agg = (req.aggregation or "count").lower()
            if agg not in valid_aggs:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid aggregation '{agg}'. Supported aggregations: ['sum', 'avg', 'count', 'min', 'max']",
                )
            if agg in ("average", "mean"):
                agg = "avg"

            if agg == "count" or not req.y_column:
                grouped = active_df[req.x_column].astype(str).value_counts().head(20)
                x_vals = grouped.index.tolist()
                y_vals = grouped.values.tolist()
                y_label = "Count"
            else:
                cls._validate_column_exists(active_df, req.y_column)
                pandas_agg = {
                    "sum": "sum",
                    "avg": "mean",
                    "min": "min",
                    "max": "max",
                }.get(agg, "mean")

                grouped = (
                    active_df.groupby(req.x_column)[req.y_column]
                    .agg(pandas_agg)
                    .dropna()
                    .sort_values(ascending=False)
                    .head(25)
                )
                x_vals = [str(x) for x in grouped.index]
                y_vals = [round(float(v), 2) for v in grouped.values]
                y_label = f"{agg.upper()} of {req.y_column}"

            if req.chart_type == "bar":
                trace = {
                    "x": x_vals,
                    "y": y_vals,
                    "type": "bar",
                    "marker": {"color": THEME_COLORS[0]},
                    "name": y_label,
                }
            else:
                trace = {
                    "x": x_vals,
                    "y": y_vals,
                    "type": "scatter",
                    "mode": "lines+markers",
                    "line": {"color": THEME_COLORS[1], "width": 2.5},
                    "marker": {"size": 6},
                    "name": y_label,
                }

            return ChartConfig(
                chart_id=chart_id,
                title=f"{y_label} by {req.x_column}",
                chart_type=req.chart_type,
                x_column=req.x_column,
                y_column=req.y_column,
                aggregation=agg,
                plotly_data=[trace],
                plotly_layout={
                    "title": {"text": f"{y_label} by {req.x_column}"},
                    "xaxis": {"title": req.x_column, "automargin": True},
                    "yaxis": {"title": y_label, "automargin": True},
                    "margin": {"l": 50, "r": 30, "t": 50, "b": 60},
                },
            )

        raise HTTPException(status_code=400, detail="Invalid chart configuration.")

    @classmethod
    def get_drill_down_data(
        cls, df: pd.DataFrame, req: DrillDownRequest
    ) -> DrillDownResponse:
        """Filter dataset by clicked category value and calculate slice summary statistics."""
        cls._validate_column_exists(df, req.category_column)
        active_df = cls.apply_filters(df, req.filters or [])

        # Match category value (string comparison)
        mask = active_df[req.category_column].astype(str) == str(req.category_value)
        slice_df = active_df[mask]

        total_matching = len(slice_df)
        summary_stats: Dict[str, Any] = {
            "category_column": req.category_column,
            "category_value": req.category_value,
            "matching_rows": total_matching,
            "percentage_of_total": round(
                (total_matching / len(active_df) * 100.0) if len(active_df) > 0 else 0.0,
                2,
            ),
        }

        # Calculate quick sums & averages for numeric columns
        numeric_summaries = {}
        for col in slice_df.columns:
            if pd.api.types.is_numeric_dtype(slice_df[col]):
                nums = slice_df[col].dropna()
                if len(nums) > 0:
                    numeric_summaries[col] = {
                        "sum": round(float(nums.sum()), 2),
                        "mean": round(float(nums.mean()), 2),
                        "min": round(float(nums.min()), 2),
                        "max": round(float(nums.max()), 2),
                    }
        summary_stats["numeric_metrics"] = numeric_summaries

        # Slice sample records safely
        paginated_slice = slice_df.iloc[req.offset : req.offset + req.limit]
        sample_records: List[Dict[str, Any]] = []
        for _, row in paginated_slice.iterrows():
            row_dict = {}
            for col_name in slice_df.columns:
                val = row[col_name]
                row_dict[str(col_name)] = None if pd.isna(val) else sanitize_for_json(val)
            sample_records.append(row_dict)

        return DrillDownResponse(
            category_column=req.category_column,
            category_value=req.category_value,
            total_matching_rows=total_matching,
            summary_stats=sanitize_for_json(summary_stats),
            sample_records=sample_records,
        )


# Global service instance
dashboard_service = DashboardService()
