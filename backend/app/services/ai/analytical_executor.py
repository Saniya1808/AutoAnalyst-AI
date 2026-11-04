import math
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.core.json_encoder import sanitize_for_json
from app.models.ask_data import (
    AnalyticalCalculationResult,
    PrimaryMetric,
    QueryFilterCondition,
    QueryPlan,
    QueryResultFact,
)
from app.models.dashboard import ChartConfig
from app.services.ai.automated_insights_engine import AutomatedInsightsEngine
from app.services.ai.column_classifier import ColumnClassifier
from app.services.ai.trend_intelligence_engine import TrendIntelligenceEngine
from app.services.profiler import infer_column_type

# Color palette aligned with AutoAnalyst AI design tokens
THEME_COLORS = [
    "#8b7cff",  # electric purple / primary accent
    "#36c9f4",  # cyan / accent-2
    "#34d399",  # emerald green
    "#fbbf24",  # amber
    "#f472b6",  # pink
    "#a78bfa",  # light purple
    "#60a5fa",  # blue
    "#fb923c",  # orange
]


class AnalyticalExecutor:
    """
    Hardened Pandas analytical engine for AutoAnalyst AI.
    Executes validated QueryPlans with zero arbitrary code execution (no eval/exec).
    """

    @classmethod
    def apply_filters_safely(
        cls, df: pd.DataFrame, filters: List[QueryFilterCondition]
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]], List[str]]:
        """
        Applies filter conditions safely using vectorized boolean indexing.
        Returns: (filtered_df, applied_filters_list, warnings)
        """
        if not filters:
            return df, [], []

        filtered = df.copy()
        applied = []
        warnings = []

        for f in filters:
            col = f.column
            if col not in filtered.columns:
                warnings.append(f"Filter column '{col}' does not exist; filter skipped.")
                continue

            op = f.operator
            val = f.value

            try:
                if op == "eq":
                    filtered = filtered[filtered[col].astype(str) == str(val)]
                elif op == "ne":
                    filtered = filtered[filtered[col].astype(str) != str(val)]
                elif op in ("gt", "gte", "lt", "lte", "between"):
                    num_series = pd.to_numeric(filtered[col], errors="coerce")
                    if op == "gt":
                        filtered = filtered[num_series > float(val)]
                    elif op == "gte":
                        filtered = filtered[num_series >= float(val)]
                    elif op == "lt":
                        filtered = filtered[num_series < float(val)]
                    elif op == "lte":
                        filtered = filtered[num_series <= float(val)]
                    elif op == "between" and isinstance(val, (list, tuple)) and len(val) == 2:
                        filtered = filtered[(num_series >= float(val[0])) & (num_series <= float(val[1]))]
                elif op == "in" and isinstance(val, list):
                    str_vals = [str(v) for v in val]
                    filtered = filtered[filtered[col].astype(str).isin(str_vals)]
                elif op == "not_in" and isinstance(val, list):
                    str_vals = [str(v) for v in val]
                    filtered = filtered[~filtered[col].astype(str).isin(str_vals)]
                elif op == "contains":
                    filtered = filtered[filtered[col].astype(str).str.contains(re.escape(str(val)), case=False, na=False)]
                elif op == "not_contains":
                    filtered = filtered[~filtered[col].astype(str).str.contains(re.escape(str(val)), case=False, na=False)]
                elif op == "starts_with":
                    filtered = filtered[filtered[col].astype(str).str.strip().str.lower().str.startswith(str(val).strip().lower(), na=False)]
                elif op == "ends_with":
                    filtered = filtered[filtered[col].astype(str).str.strip().str.lower().str.endswith(str(val).strip().lower(), na=False)]
                elif op == "exact":
                    filtered = filtered[filtered[col].astype(str).str.strip().str.lower() == str(val).strip().lower()]

                applied.append({"column": col, "operator": op, "value": val})
            except Exception as e:
                warnings.append(f"Could not apply filter on '{col}': {str(e)}")

        return filtered, applied, warnings

    @classmethod
    def execute_plan(
        cls, df: pd.DataFrame, plan: QueryPlan, dataset_id: str
    ) -> AnalyticalCalculationResult:
        """
        Executes a validated QueryPlan against a DataFrame.
        Produces grounded numerical figures and fact IDs.
        """
        if plan.is_ambiguous:
            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=plan.clarification_reason or "Your query is ambiguous. Please clarify your objective.",
                calculation_method="Query clarification required.",
                limitations_and_warnings=[plan.clarification_reason or "Ambiguous query."],
            )

        # 1. Apply any filters safely
        working_df, applied_filters, filter_warnings = cls.apply_filters_safely(df, plan.filters)
        limitations: List[str] = list(filter_warnings)
        facts: List[QueryResultFact] = []
        fact_idx = 1

        total_rows = len(working_df)
        if total_rows == 0:
            target_col = plan.primary_column or (plan.filters[0].column if plan.filters else "column")
            filter_desc = f"{plan.filters[0].operator.replace('_', ' ')} '{plan.filters[0].value}'" if plan.filters else "the specified filter"
            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=f"No records found where '{target_col}' matches {filter_desc}. Verified across {len(df):,} total dataset rows.",
                primary_metric=PrimaryMetric(
                    label=f"Matching {target_col}",
                    value=0,
                    formatted="0 matches",
                ),
                calculation_method=f"Evaluated filter condition ({filter_desc}) on '{target_col}' across {len(df):,} rows; 0 matching records found.",
                columns_used=[target_col],
                filters_applied=applied_filters,
                tabular_data=[],
                limitations_and_warnings=["0 rows matched the filter criteria."],
            )

        # =========================================================================
        # 1. BROAD ANALYTICAL INSIGHTS & BUSINESS INTELLIGENCE (PHASE 4.3)
        # =========================================================================
        # 1A. Automated Insights / Important Findings
        if plan.intent == "automated_insights" or plan.operation == "discover_insights":
            insights = AutomatedInsightsEngine.analyze_dataset(
                df=working_df,
                dataset_id=dataset_id,
                dataset_name="Active Dataset",
                snapshot_hash="working_snapshot",
            )
            top_findings = insights.key_findings[:5]
            findings_table = []
            for f in top_findings:
                findings_table.append({
                    "Importance": f.importance.upper(),
                    "Category": f.category.replace("_", " ").title(),
                    "Finding": f.title,
                    "Description": f.description,
                })

            top_summaries = [f"- {f.title}: {f.description}" for f in top_findings]
            direct_ans = (
                f"Discovered {len(top_findings)} automated insights (Health Score: {insights.health_score:.0f}/100):\n"
                + "\n".join(top_summaries)
            )

            primary_chart = insights.best_worst_analyses[0].chart if insights.best_worst_analyses and insights.best_worst_analyses[0].chart else None

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=direct_ans,
                primary_metric=PrimaryMetric(
                    label="Discovered Insights",
                    value=len(top_findings),
                    formatted=f"{len(top_findings)} Key Findings (Score: {insights.health_score:.0f}/100)",
                ),
                calculation_method=f"Autonomously evaluated distributions, category benchmarks, correlations, and anomalies across {len(working_df):,} records.",
                columns_used=[c.name for c in insights.column_classifications if c.is_usable_for_metrics or c.is_usable_for_grouping][:6],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(findings_table),
                chart=primary_chart,
                grounded_facts=insights.grounded_facts,
                limitations_and_warnings=limitations + insights.limitations,
            )

        # 1B. Best and Worst Performing Categories
        if plan.intent == "best_worst_performers" or plan.operation == "benchmark_performers":
            insights = AutomatedInsightsEngine.analyze_dataset(
                df=working_df,
                dataset_id=dataset_id,
                dataset_name="Active Dataset",
                snapshot_hash="working_snapshot",
            )
            if not insights.best_worst_analyses:
                return AnalyticalCalculationResult(
                    plan_id=plan.plan_id,
                    success=True,
                    direct_summary="No suitable categorical dimension and numerical metric combination was found to benchmark best and worst performers.",
                    primary_metric=PrimaryMetric(label="Category Comparison", value=0, formatted="N/A"),
                    calculation_method="Evaluated categorical column cardinality and variance; insufficient grouping dimensions found.",
                    columns_used=[],
                    filters_applied=applied_filters,
                    tabular_data=[],
                    grounded_facts=insights.grounded_facts,
                    limitations_and_warnings=limitations + ["Insufficient categorical variance for category benchmarking."],
                )

            bw = insights.best_worst_analyses[0]
            performers_list = getattr(bw, "ranked_performers", None)
            if not performers_list:
                # Safe fallback to best and worst, avoiding duplicates if single category
                if bw.best_performer.category_name == bw.worst_performer.category_name:
                    performers_list = [bw.best_performer]
                else:
                    performers_list = [bw.best_performer, bw.worst_performer]

            ranked_table = []
            for rank_idx, p in enumerate(performers_list, start=1):
                ranked_table.append({
                    "Rank": rank_idx,
                    bw.dimension_column: p.category_name,
                    "Metric Value": round(p.metric_value, 2),
                    "Delta vs Avg (%)": f"{p.delta_vs_average_pct:+.1f}%",
                    "Record Count": p.sample_size,
                    "Status": "Reliable" if p.is_statistically_reliable else "Exploratory (n < 5)",
                })

            best_p = bw.best_performer
            worst_p = bw.worst_performer

            direct_ans = (
                f"In '{bw.dimension_column}' benchmarking ({bw.aggregation} of {bw.metric_column or 'frequency'}): "
                f"Best performer is '{best_p.category_name}' with {best_p.metric_value:,.2f} ({best_p.delta_vs_average_pct:+.1f}% vs average {bw.dataset_average:,.2f}). "
                f"Lowest performer is '{worst_p.category_name}' with {worst_p.metric_value:,.2f} ({worst_p.delta_vs_average_pct:+.1f}% vs average)."
            )

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=direct_ans,
                primary_metric=PrimaryMetric(
                    label=f"Top {bw.dimension_column}: {best_p.category_name}",
                    value=round(best_p.metric_value, 2),
                    formatted=f"{best_p.metric_value:,.2f} ({best_p.delta_vs_average_pct:+.1f}% vs avg)",
                ),
                calculation_method=f"Computed {bw.aggregation} of {bw.metric_column or 'records'} grouped by '{bw.dimension_column}' across {len(working_df):,} records.",
                columns_used=[bw.dimension_column] + ([bw.metric_column] if bw.metric_column else []),
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(ranked_table),
                chart=bw.chart,
                grounded_facts=insights.grounded_facts,
                limitations_and_warnings=limitations + insights.limitations,
            )

        # 1C. Anomaly & Unusual Pattern Detection
        if plan.intent == "anomaly_detection" or plan.operation == "detect_anomalies":
            insights = AutomatedInsightsEngine.analyze_dataset(
                df=working_df,
                dataset_id=dataset_id,
                dataset_name="Active Dataset",
                snapshot_hash="working_snapshot",
            )
            anomalies = insights.anomalies_and_patterns
            if not anomalies:
                direct_ans = "No statistically severe outliers, rare categories (< 1%), or unusual pattern anomalies were detected in the dataset."
                total_anomalies = 0
            else:
                anomalies_to_show = anomalies[:5]
                total_anomalies = len(anomalies)
                summaries = [f"- {a.column_name}: {a.description}" for a in anomalies_to_show]
                heading_note = f" (showing top {len(anomalies_to_show)})" if total_anomalies > len(anomalies_to_show) else ""
                direct_ans = f"Detected {total_anomalies} unusual pattern(s) and anomaly condition(s){heading_note}:\n" + "\n".join(summaries)

            anomalies_table = []
            for a in anomalies:
                aff_rows = a.metric_evidence.get("outlier_count") or a.metric_evidence.get("affected_rows") or 0
                aff_pct = a.metric_evidence.get("outlier_percentage") or a.metric_evidence.get("share_pct") or 0.0
                anomalies_table.append({
                    "Pattern Type": a.anomaly_type.replace("_", " ").title(),
                    "Column": a.column_name,
                    "Severity": a.severity.upper(),
                    "Affected Records": aff_rows,
                    "Share (%)": f"{aff_pct:.1f}%",
                    "Details": a.description,
                })

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=direct_ans,
                primary_metric=PrimaryMetric(
                    label="Detected Anomalies",
                    value=total_anomalies,
                    formatted=f"{total_anomalies} unusual patterns",
                ),
                calculation_method=f"Applied IQR fencing (1.5×IQR), rare-frequency filters (<1%), and missingness thresholds across {len(working_df):,} rows.",
                columns_used=[a.column_name for a in anomalies][:5],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(anomalies_table),
                grounded_facts=insights.grounded_facts,
                limitations_and_warnings=limitations + insights.limitations,
            )

        # 1D. Actionable Recommendations
        if plan.intent == "business_recommendations" or plan.operation == "recommend_actions":
            insights = AutomatedInsightsEngine.analyze_dataset(
                df=working_df,
                dataset_id=dataset_id,
                dataset_name="Active Dataset",
                snapshot_hash="working_snapshot",
            )
            recs = insights.recommendations
            if not recs:
                direct_ans = "The dataset has uniform distributions and healthy quality; no immediate corrective or optimization recommendations required."
            else:
                recs_to_show = recs[:5]
                rec_lines = [f"- [{r.priority.upper()}] {r.title}: {r.action_statement}" for r in recs_to_show]
                heading_note = f" (showing top {len(recs_to_show)})" if len(recs) > len(recs_to_show) else ""
                direct_ans = (
                    f"Generated {len(recs)} actionable data-driven recommendation(s){heading_note} grounded strictly in validated dataset facts:\n"
                    + "\n".join(rec_lines)
                )

            recs_table = []
            for r in recs:
                recs_table.append({
                    "Priority": r.priority.upper(),
                    "Category": r.category.replace("_", " ").title(),
                    "Recommended Action": r.action_statement,
                    "Classification": "Analytical Hypothesis" if r.is_hypothesis else "Fact Grounded",
                    "Expected Impact": r.expected_impact,
                })

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=direct_ans,
                primary_metric=PrimaryMetric(
                    label="Actionable Recommendations",
                    value=len(recs),
                    formatted=f"{len(recs)} Strategic Actions",
                ),
                calculation_method="Synthesized evidence-based actions strictly cross-referencing Pandas computed facts and performance benchmarks.",
                columns_used=[c.name for c in insights.column_classifications if c.is_usable_for_metrics][:5],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(recs_table),
                grounded_facts=insights.grounded_facts,
                limitations_and_warnings=limitations + insights.limitations,
            )

        # 1E. Data Quality Issues Audit
        if plan.intent == "data_quality_insights" or plan.operation == "data_quality_audit":
            insights = AutomatedInsightsEngine.analyze_dataset(
                df=working_df,
                dataset_id=dataset_id,
                dataset_name="Active Dataset",
                snapshot_hash="working_snapshot",
            )
            quality_findings = [f for f in insights.key_findings if f.category == "quality"]
            missing_patterns = [a for a in insights.anomalies_and_patterns if a.anomaly_type in ("missing_concentration", "invariant_column")]

            direct_ans = (
                f"Data Quality Audit: Overall Health Score is {insights.health_score:.1f}/100. "
                f"Identified {len(quality_findings)} data quality finding(s) and {len(missing_patterns)} column integrity issue(s)."
            )

            dq_table = []
            for f in quality_findings:
                dq_table.append({
                    "Issue": f.title,
                    "Details": f.description,
                    "Importance": f.importance.upper(),
                })
            for a in missing_patterns:
                dq_table.append({
                    "Issue": f"Quality Concern in {a.column_name}",
                    "Details": a.description,
                    "Importance": a.severity.upper(),
                })

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=direct_ans,
                primary_metric=PrimaryMetric(
                    label="Data Health Score",
                    value=insights.health_score,
                    formatted=f"{insights.health_score:.1f} / 100",
                ),
                calculation_method=f"Audited missing values, constant columns, duplicate risks, and type validity across {len(working_df):,} records.",
                columns_used=[c.name for c in insights.column_classifications if not c.is_usable_for_metrics or not c.is_usable_for_grouping][:5],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(dq_table),
                grounded_facts=insights.grounded_facts,
                limitations_and_warnings=limitations + insights.limitations,
            )

        # =========================================================================
        # 1F. TEMPORAL TREND INTELLIGENCE & BENCHMARKS (PHASE 4.4)
        # =========================================================================
        if plan.intent in ("trend_analysis", "period_benchmark", "temporal_anomaly", "seasonality_analysis") or plan.operation in ("analyze_trend", "benchmark_periods", "detect_temporal_anomalies", "detect_seasonality"):
            classifications = ColumnClassifier.classify_dataset(working_df)
            combinations = TrendIntelligenceEngine.discover_combinations(working_df, classifications)

            # No-Date Dataset Guard: never invent temporal trends if dates do not exist
            if not combinations:
                avail_cols = ", ".join(list(working_df.columns)[:8]) + ("..." if len(working_df.columns) > 8 else "")
                return AnalyticalCalculationResult(
                    plan_id=plan.plan_id,
                    success=True,
                    direct_summary=f"This dataset does not contain any date or time columns to measure trends over time. Available attributes are: {avail_cols}.",
                    calculation_method="Temporal analysis skipped: dataset lacks date/time attributes.",
                    limitations_and_warnings=["Dataset contains no date or timestamp columns."],
                )

            # Match target combination or default to highest ranked
            target_comb = combinations[0]
            if plan.primary_column or plan.secondary_column:
                req_col = (plan.primary_column or "").lower()
                req_sec = (plan.secondary_column or "").lower()
                for c in combinations:
                    if c.date_column.lower() in (req_col, req_sec) or c.metric_column.lower() in (req_col, req_sec):
                        target_comb = c
                        break

            target_gran = plan.date_granularity or target_comb.granularity
            series_df, final_gran, prep_warnings = TrendIntelligenceEngine.prepare_time_series(
                df=working_df,
                date_col=target_comb.date_column,
                metric_col=target_comb.metric_column,
                granularity=target_gran,
            )
            limitations.extend(prep_warnings)

            # -----------------------------------------------------------------
            # 1F.1 Trend Analysis
            # -----------------------------------------------------------------
            if plan.intent == "trend_analysis" or plan.operation == "analyze_trend":
                fdr_map = TrendIntelligenceEngine.screen_combinations_fdr(working_df, combinations, q=0.05) if len(combinations) > 1 else {}
                target_fdr = fdr_map.get(target_comb.combination_id, (None, None))[1] if len(combinations) > 1 else None

                trend_res, trend_facts = TrendIntelligenceEngine.analyze_trend(
                    series_df=series_df,
                    date_col=target_comb.date_column,
                    metric_col=target_comb.metric_column,
                    granularity=final_gran,
                    start_fact_idx=fact_idx,
                    p_value_fdr_adjusted=target_fdr,
                    total_hypotheses_screened=len(combinations),
                )
                if not trend_res:
                    return AnalyticalCalculationResult(
                        plan_id=plan.plan_id,
                        success=False,
                        direct_summary="Insufficient chronological periods to evaluate time-series trends.",
                        limitations_and_warnings=["Fewer than 3 valid time periods found."],
                    )

                trend_table = [
                    {
                        "Period": p.period_label,
                        target_comb.metric_column: p.formatted_value,
                        "Completeness": f"{p.temporal_completeness_pct:.0f}%",
                        "Status": "Partial Period" if p.is_partial_period else "Complete",
                    }
                    for p in trend_res.data_points
                ]

                primary_label = f"{trend_res.direction.capitalize()} Trend: {target_comb.metric_column}"
                primary_val = trend_res.conventional_growth_pct if trend_res.conventional_growth_pct is not None else trend_res.absolute_change
                primary_fmt = f"{trend_res.conventional_growth_pct:+.1f}%" if trend_res.conventional_growth_pct is not None else f"{trend_res.formatted_absolute_change}"

                return AnalyticalCalculationResult(
                    plan_id=plan.plan_id,
                    success=True,
                    direct_summary=trend_res.explanation,
                    primary_metric=PrimaryMetric(
                        label=primary_label,
                        value=primary_val,
                        formatted=primary_fmt,
                    ),
                    calculation_method=f"Evaluated OLS regression (R²={trend_res.trend_strength_r2:.2f}), Durbin-Watson autocorrelation, and Mann-Kendall direction across {len(series_df)} {final_gran} periods.",
                    columns_used=[target_comb.date_column, target_comb.metric_column],
                    filters_applied=applied_filters,
                    tabular_data=sanitize_for_json(trend_table),
                    chart=trend_res.chart,
                    grounded_facts=trend_facts,
                    limitations_and_warnings=limitations,
                )

            # -----------------------------------------------------------------
            # 1F.2 Period Benchmarking (Chronological vs Cyclical)
            # -----------------------------------------------------------------
            if plan.intent == "period_benchmark" or plan.operation == "benchmark_periods":
                if plan.period_mode == "cyclical":
                    # Delegate to seasonality cyclical patterns
                    seas_res, seas_facts = TrendIntelligenceEngine.analyze_seasonality(
                        df=working_df,
                        date_col=target_comb.date_column,
                        metric_col=target_comb.metric_column,
                        start_fact_idx=fact_idx,
                    )
                    top_pat = seas_res.patterns[0] if seas_res.patterns else None
                    bot_pat = seas_res.patterns[-1] if seas_res.patterns else None
                    summary_msg = f"Cyclical performance across {seas_res.cycle_type or 'periods'}: Peak occurs on '{top_pat.period_name if top_pat else 'N/A'}' ({top_pat.formatted_average if top_pat else 'N/A'}, {top_pat.delta_vs_overall_avg_pct:+.1f}% vs average); Lowest occurs on '{bot_pat.period_name if bot_pat else 'N/A'}' ({bot_pat.formatted_average if bot_pat else 'N/A'}, {bot_pat.delta_vs_overall_avg_pct:+.1f}% vs average)." if top_pat else "Insufficient data for cyclical period benchmarking."

                    bench_table = [
                        {
                            "Period": p.period_name,
                            "Average Value": p.formatted_average,
                            "Delta vs Average (%)": f"{p.delta_vs_overall_avg_pct:+.1f}%",
                            "Occurrences": p.sample_occurrences,
                        }
                        for p in seas_res.patterns
                    ]

                    return AnalyticalCalculationResult(
                        plan_id=plan.plan_id,
                        success=True,
                        direct_summary=summary_msg,
                        primary_metric=PrimaryMetric(
                            label=f"Peak {seas_res.cycle_type or 'Cycle'}: {top_pat.period_name if top_pat else 'N/A'}",
                            value=top_pat.delta_vs_overall_avg_pct if top_pat else 0.0,
                            formatted=f"{top_pat.formatted_average if top_pat else 'N/A'} ({top_pat.delta_vs_overall_avg_pct:+.1f}%)" if top_pat else "N/A",
                        ),
                        calculation_method="Aggregated detrended residuals across calendar cycle buckets.",
                        columns_used=[target_comb.date_column, target_comb.metric_column],
                        filters_applied=applied_filters,
                        tabular_data=sanitize_for_json(bench_table),
                        chart=seas_res.chart,
                        grounded_facts=seas_facts,
                        limitations_and_warnings=limitations,
                    )

                # Chronological period benchmarking: exclude partial periods from peak/trough
                clean_periods = series_df[~series_df["is_partial_period"]]
                if len(clean_periods) < 2:
                    clean_periods = series_df

                peak_idx = clean_periods["value"].idxmax()
                trough_idx = clean_periods["value"].idxmin()
                peak_row = clean_periods.loc[peak_idx]
                trough_row = clean_periods.loc[trough_idx]

                avg_period_val = float(clean_periods["value"].mean())
                peak_val = float(peak_row["value"])
                trough_val = float(trough_row["value"])
                peak_p = str(peak_row["period_label"])
                trough_p = str(trough_row["period_label"])

                peak_delta = round(((peak_val - avg_period_val) / max(abs(avg_period_val), 1e-6)) * 100.0, 1)
                trough_delta = round(((trough_val - avg_period_val) / max(abs(avg_period_val), 1e-6)) * 100.0, 1)

                bench_table = []
                for _, r in series_df.sort_values(by="value", ascending=False).iterrows():
                    val = float(r["value"])
                    d_pct = round(((val - avg_period_val) / max(abs(avg_period_val), 1e-6)) * 100.0, 1)
                    bench_table.append({
                        "Period": str(r["period_label"]),
                        target_comb.metric_column: f"{val:,.2f}",
                        "Delta vs Average (%)": f"{d_pct:+.1f}%",
                        "Status": "Partial (Excluded from Benchmark)" if r["is_partial_period"] else "Complete",
                    })

                direct_ans = (
                    f"In chronological {final_gran} benchmarking for '{target_comb.metric_column}': "
                    f"Highest period was {peak_p} with {peak_val:,.2f} ({peak_delta:+.1f}% vs period average {avg_period_val:,.2f}). "
                    f"Lowest period was {trough_p} with {trough_val:,.2f} ({trough_delta:+.1f}% vs period average)."
                )

                chart_bench = ChartConfig(
                    chart_id=f"chart_pbench_{uuid.uuid4().hex[:8]}",
                    title=f"{target_comb.metric_column.replace('_', ' ').title()} by {final_gran.capitalize()}",
                    chart_type="bar",
                    x_column="Period",
                    y_column=target_comb.metric_column,
                    plotly_data=[
                        {
                            "x": [r["Period"] for r in bench_table],
                            "y": [float(r[target_comb.metric_column].replace(",", "")) for r in bench_table],
                            "type": "bar",
                            "marker": {
                                "color": [
                                    THEME_COLORS[2] if r["Period"] == peak_p else (THEME_COLORS[3] if r["Period"] == trough_p else THEME_COLORS[0])
                                    for r in bench_table
                                ]
                            },
                        }
                    ],
                    plotly_layout={
                        "title": {"text": f"Period Comparison: {target_comb.metric_column.replace('_', ' ').title()}"},
                        "xaxis": {"title": "Period", "automargin": True},
                        "yaxis": {"title": target_comb.metric_column.replace('_', ' ').title(), "automargin": True},
                    },
                )

                fid_p = f"fact_{fact_idx}"
                fact_idx += 1
                facts = [
                    QueryResultFact(
                        fact_id=fid_p,
                        category="period_benchmark",
                        column_name=f"{target_comb.date_column}_{target_comb.metric_column}",
                        metric_name="peak_period",
                        value=peak_val,
                        formatted_statement=f"Highest performing period for '{target_comb.metric_column}' was {peak_p} with {peak_val:,.2f}.",
                    )
                ]

                return AnalyticalCalculationResult(
                    plan_id=plan.plan_id,
                    success=True,
                    direct_summary=direct_ans,
                    primary_metric=PrimaryMetric(
                        label=f"Highest Period: {peak_p}",
                        value=round(peak_val, 2),
                        formatted=f"{peak_val:,.2f} ({peak_delta:+.1f}% vs avg)",
                    ),
                    calculation_method=f"Benchmarked {len(clean_periods)} complete {final_gran} periods against period average ({avg_period_val:,.2f}).",
                    columns_used=[target_comb.date_column, target_comb.metric_column],
                    filters_applied=applied_filters,
                    tabular_data=sanitize_for_json(bench_table),
                    chart=chart_bench,
                    grounded_facts=facts,
                    limitations_and_warnings=limitations,
                )

            # -----------------------------------------------------------------
            # 1F.3 Temporal Anomaly Detection
            # -----------------------------------------------------------------
            if plan.intent == "temporal_anomaly" or plan.operation == "detect_temporal_anomalies":
                t_anomalies, anomaly_facts = TrendIntelligenceEngine.detect_temporal_anomalies(
                    series_df=series_df,
                    date_col=target_comb.date_column,
                    metric_col=target_comb.metric_column,
                    start_fact_idx=fact_idx,
                )
                if not t_anomalies:
                    direct_ans = f"No sudden spikes, drops, or volatility bursts were detected in '{target_comb.metric_column}' over '{target_comb.date_column}' across {len(series_df)} periods."
                    total_tanom = 0
                else:
                    total_tanom = len(t_anomalies)
                    items_desc = [f"- {a.period_label}: {a.detection_reason} ({a.detection_method})" for a in t_anomalies[:5]]
                    direct_ans = f"Detected {total_tanom} temporal anomaly event(s) in '{target_comb.metric_column}':\n" + "\n".join(items_desc)

                anom_table = [
                    {
                        "Period": a.period_label,
                        "Anomaly Type": a.anomaly_type.replace("_", " ").title(),
                        "Severity": a.severity.upper(),
                        "Previous Value": f"{a.previous_value:,.2f}",
                        "New Value": f"{a.current_value:,.2f}",
                        "Delta": f"{a.delta_abs:+,.2f}" + (f" ({a.delta_pct:+.1f}%)" if a.delta_pct is not None else ""),
                        "Reason": a.detection_reason,
                    }
                    for a in t_anomalies
                ]

                chart_anom = ChartConfig(
                    chart_id=f"chart_tanom_{uuid.uuid4().hex[:8]}",
                    title=f"Temporal Anomalies in {target_comb.metric_column.replace('_', ' ').title()}",
                    chart_type="line",
                    x_column="Period",
                    y_column=target_comb.metric_column,
                    plotly_data=[
                        {
                            "x": [str(p) for p in series_df["period_label"]],
                            "y": [round(float(v), 2) for v in series_df["value"]],
                            "type": "scatter",
                            "mode": "lines+markers",
                            "name": target_comb.metric_column,
                            "line": {"color": THEME_COLORS[0], "width": 2.5},
                            "marker": {
                                "color": [
                                    THEME_COLORS[4] if p in [a.period_label for a in t_anomalies] else THEME_COLORS[0]
                                    for p in series_df["period_label"]
                                ],
                                "size": [
                                    10 if p in [a.period_label for a in t_anomalies] else 5
                                    for p in series_df["period_label"]
                                ],
                            },
                        }
                    ],
                    plotly_layout={
                        "title": {"text": f"Anomaly Timeline: {target_comb.metric_column.replace('_', ' ').title()}"},
                        "xaxis": {"title": "Period", "automargin": True},
                        "yaxis": {"title": target_comb.metric_column.replace('_', ' ').title(), "automargin": True},
                    },
                )

                return AnalyticalCalculationResult(
                    plan_id=plan.plan_id,
                    success=True,
                    direct_summary=direct_ans,
                    primary_metric=PrimaryMetric(
                        label="Temporal Anomalies",
                        value=total_tanom,
                        formatted=f"{total_tanom} event(s) flagged",
                    ),
                    calculation_method="Evaluated Modified Z-Score on consecutive period differences with Zero-MAD fallback.",
                    columns_used=[target_comb.date_column, target_comb.metric_column],
                    filters_applied=applied_filters,
                    tabular_data=sanitize_for_json(anom_table),
                    chart=chart_anom,
                    grounded_facts=anomaly_facts,
                    limitations_and_warnings=limitations,
                )

            # -----------------------------------------------------------------
            # 1F.4 Seasonality Analysis
            # -----------------------------------------------------------------
            if plan.intent == "seasonality_analysis" or plan.operation == "detect_seasonality":
                seas_res, seas_facts = TrendIntelligenceEngine.analyze_seasonality(
                    df=working_df,
                    date_col=target_comb.date_column,
                    metric_col=target_comb.metric_column,
                    start_fact_idx=fact_idx,
                )
                seas_table = [
                    {
                        "Cycle Period": p.period_name,
                        "Average Value": p.formatted_average,
                        "Delta vs Average (%)": f"{p.delta_vs_overall_avg_pct:+.1f}%",
                        "Occurrences": p.sample_occurrences,
                    }
                    for p in seas_res.patterns
                ]

                return AnalyticalCalculationResult(
                    plan_id=plan.plan_id,
                    success=True,
                    direct_summary=seas_res.explanation,
                    primary_metric=PrimaryMetric(
                        label=f"Seasonality Status: {seas_res.status.replace('_', ' ').title()}",
                        value=seas_res.status,
                        formatted=f"{seas_res.status.replace('_', ' ').title()} ({seas_res.cycle_type or 'no cycle'})",
                    ),
                    calculation_method="Performed One-Way ANOVA and Kruskal-Wallis hypothesis tests on detrended residuals.",
                    columns_used=[target_comb.date_column, target_comb.metric_column],
                    filters_applied=applied_filters,
                    tabular_data=sanitize_for_json(seas_table),
                    chart=seas_res.chart,
                    grounded_facts=seas_facts,
                    limitations_and_warnings=limitations,
                )

        # =========================================================================
        # 2. GENERAL DATASET SUMMARY / OVERVIEW INTENT
        # =========================================================================
        if plan.intent == "dataset_summary" or plan.operation == "overview":
            row_count = len(df)
            col_count = len(df.columns)
            total_cells = row_count * col_count
            missing_cells = int(df.isna().sum().sum())
            completeness_pct = round(((total_cells - missing_cells) / max(total_cells, 1)) * 100.0, 1)

            num_cols = [c for c in df.columns if infer_column_type(df[c]) in ("integer", "float")]
            cat_cols = [c for c in df.columns if infer_column_type(df[c]) in ("string", "boolean")]
            dt_cols = [c for c in df.columns if infer_column_type(df[c]) == "datetime"]

            # Detect primary entity column (e.g. column with 'name' or most unique categorical column)
            entity_col = next((c for c in cat_cols if "name" in c.lower()), None) or (cat_cols[0] if cat_cols else None)

            facts.append(
                QueryResultFact(
                    fact_id=f"fact_{fact_idx}",
                    category="dataset_dimension",
                    metric_name="row_count",
                    value=row_count,
                    formatted_statement=f"Dataset contains {row_count:,} total records.",
                )
            )
            fact_idx += 1
            facts.append(
                QueryResultFact(
                    fact_id=f"fact_{fact_idx}",
                    category="dataset_dimension",
                    metric_name="column_count",
                    value=col_count,
                    formatted_statement=f"Dataset has {col_count} columns ({len(num_cols)} numerical, {len(cat_cols)} categorical).",
                )
            )
            fact_idx += 1
            facts.append(
                QueryResultFact(
                    fact_id=f"fact_{fact_idx}",
                    category="data_quality",
                    metric_name="completeness_percentage",
                    value=completeness_pct,
                    formatted_statement=f"Overall data completeness is {completeness_pct}% with {missing_cells:,} missing cells.",
                )
            )

            # Build structured column summary table
            col_summary_table = []
            for col_name in df.columns:
                c_type = infer_column_type(df[col_name])
                n_null = int(df[col_name].isna().sum())
                n_unique = int(df[col_name].nunique(dropna=True))
                col_summary_table.append({
                    "Column Name": col_name,
                    "Data Type": c_type,
                    "Unique Values": n_unique,
                    "Missing Cells": n_null,
                })

            summary_text = (
                f"This dataset contains {row_count:,} records across {col_count} columns ({len(num_cols)} numerical, {len(cat_cols)} categorical). "
                + (f"Primary entity column: '{entity_col}'. " if entity_col else "")
                + f"Overall data completeness is {completeness_pct}%. Key columns: {', '.join(list(df.columns)[:5])}."
            )

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=summary_text,
                primary_metric=PrimaryMetric(
                    label="Dataset Dimensions",
                    value=row_count,
                    formatted=f"{row_count:,} rows × {col_count} cols",
                ),
                calculation_method=f"Profiled dataset structure, schema types, and completeness metrics across {row_count:,} rows.",
                columns_used=list(df.columns)[:6],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(col_summary_table),
                grounded_facts=facts,
                limitations_and_warnings=limitations,
            )

        # =========================================================================
        # 3. TEXT SEARCH / STRING FILTERING (STARTS_WITH, ENDS_WITH, CONTAINS)
        # =========================================================================
        if plan.intent == "text_search" or plan.operation == "filter_records":
            target_col = plan.primary_column or (plan.filters[0].column if plan.filters else working_df.columns[0])
            if target_col not in working_df.columns:
                target_col = working_df.columns[0]

            unique_matches = list(working_df[target_col].dropna().astype(str).unique())
            unique_matches.sort()
            match_rows_count = len(working_df)
            distinct_count = len(unique_matches)

            facts.append(
                QueryResultFact(
                    fact_id=f"fact_{fact_idx}",
                    category="text_search",
                    column_name=target_col,
                    metric_name="distinct_matches_count",
                    value=distinct_count,
                    formatted_statement=f"Found {distinct_count} distinct '{target_col}' values matching criteria.",
                )
            )
            fact_idx += 1
            facts.append(
                QueryResultFact(
                    fact_id=f"fact_{fact_idx}",
                    category="text_search",
                    column_name=target_col,
                    metric_name="total_matching_rows",
                    value=match_rows_count,
                    formatted_statement=f"Total matching records: {match_rows_count} out of {len(df):,}.",
                )
            )

            # Exclude raw image/logo URL columns from the display table unless explicitly the target column
            display_cols = [c for c in working_df.columns if not any(m in c.lower() for m in ("logo", "(url)", "image", "avatar")) or c == target_col]
            if not display_cols:
                display_cols = list(working_df.columns)

            sample_df = working_df[display_cols].drop_duplicates(subset=[target_col]).head(plan.limit or 25)
            table_records = sample_df.to_dict(orient="records")

            op_desc = plan.filters[0].operator.replace("_", " ") if plan.filters else "matching"
            val_desc = plan.filters[0].value if plan.filters else ""
            sample_list_str = ", ".join(unique_matches[:5]) + ("..." if len(unique_matches) > 5 else "")
            direct_ans = f"Found {distinct_count} distinct '{target_col}' values {op_desc} '{val_desc}' (total {match_rows_count} records): {sample_list_str}."

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=direct_ans,
                primary_metric=PrimaryMetric(
                    label=f"Matching {target_col}s",
                    value=distinct_count,
                    formatted=f"{distinct_count} distinct ({match_rows_count} records)",
                ),
                calculation_method=f"Filtered column '{target_col}' with {op_desc} '{val_desc}' across {len(df):,} records; extracted {distinct_count} distinct values.",
                columns_used=[target_col] + [c for c in display_cols if c != target_col][:2],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(table_records),
                grounded_facts=facts,
                limitations_and_warnings=limitations,
            )

        # =========================================================================
        # 4. DISTINCT / UNIQUE VALUES LISTING
        # =========================================================================
        if plan.intent == "distinct_values" or plan.operation == "unique_values":
            target_col = plan.primary_column or working_df.columns[0]
            if target_col not in working_df.columns:
                target_col = working_df.columns[0]

            val_counts = working_df[target_col].astype(str).value_counts(dropna=True)
            unique_count = len(val_counts)

            facts.append(
                QueryResultFact(
                    fact_id=f"fact_{fact_idx}",
                    category="distinct_values",
                    column_name=target_col,
                    metric_name="unique_values_count",
                    value=unique_count,
                    formatted_statement=f"Column '{target_col}' has {unique_count} distinct values across {len(working_df):,} records.",
                )
            )

            table_records = []
            limit_val = plan.limit or 50
            for val, count in val_counts.head(limit_val).items():
                table_records.append({
                    target_col: str(val),
                    "occurrences": int(count),
                })

            sample_list_str = ", ".join(list(val_counts.index[:5])) + ("..." if unique_count > 5 else "")
            direct_ans = f"There are {unique_count} unique values in '{target_col}'. Examples: {sample_list_str}."

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=direct_ans,
                primary_metric=PrimaryMetric(
                    label=f"Unique {target_col}s",
                    value=unique_count,
                    formatted=f"{unique_count:,}",
                ),
                calculation_method=f"Extracted unique values from '{target_col}' using nunique() across {len(working_df):,} records.",
                columns_used=[target_col],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(table_records),
                grounded_facts=facts,
                limitations_and_warnings=limitations,
            )

        # =========================================================================
        # 5. MISSING VALUE INSPECTION
        # =========================================================================
        if plan.intent == "missing_value_inspection" or plan.operation == "missing_summary":
            missing_series = working_df.isna().sum()
            missing_data = []
            for col, count in missing_series.items():
                if count > 0:
                    pct = round((count / total_rows) * 100.0, 2)
                    missing_data.append({
                        "column_name": col,
                        "missing_count": int(count),
                        "missing_percentage": pct,
                    })

            missing_data.sort(key=lambda x: x["missing_count"], reverse=True)
            top_missing = missing_data[: plan.limit or 15]

            for item in top_missing[:3]:
                facts.append(
                    QueryResultFact(
                        fact_id=f"fact_{fact_idx}",
                        category="missing_values",
                        column_name=item["column_name"],
                        metric_name="missing_percentage",
                        value=item["missing_percentage"],
                        formatted_statement=f"Column '{item['column_name']}' has {item['missing_count']} missing values ({item['missing_percentage']}%).",
                    )
                )
                fact_idx += 1

            total_missing_cells = int(missing_series.sum())
            chart_config = None
            if plan.chart and plan.chart.chart_type != "none" and top_missing:
                chart_config = ChartConfig(
                    chart_id=f"chart_missing_{dataset_id[:8]}",
                    title="Missing Values by Column",
                    chart_type="bar",
                    x_column="column_name",
                    y_column="missing_count",
                    plotly_data=[
                        {
                            "x": [item["column_name"] for item in top_missing],
                            "y": [item["missing_count"] for item in top_missing],
                            "type": "bar",
                            "marker": {"color": THEME_COLORS[3]},
                            "name": "Missing Count",
                        }
                    ],
                    plotly_layout={
                        "title": {"text": "Missing Values by Column"},
                        "xaxis": {"title": "Column", "automargin": True},
                        "yaxis": {"title": "Missing Cells", "automargin": True},
                    },
                )

            summary_text = (
                f"Found {total_missing_cells:,} total missing cells across {len(missing_data)} columns. "
                + (f"Highest missing column is '{top_missing[0]['column_name']}' with {top_missing[0]['missing_count']} missing values ({top_missing[0]['missing_percentage']}%)." if top_missing else "No columns have missing values.")
            )

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=summary_text,
                primary_metric=PrimaryMetric(
                    label="Total Missing Cells",
                    value=total_missing_cells,
                    formatted=f"{total_missing_cells:,}",
                ),
                calculation_method=f"Computed null cell counts using isna().sum() across {total_rows:,} records.",
                columns_used=[item["column_name"] for item in top_missing],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(top_missing),
                chart=chart_config,
                grounded_facts=facts,
                limitations_and_warnings=limitations,
            )

        # =========================================================================
        # 6. CORRELATION ANALYSIS
        # =========================================================================
        if plan.intent == "correlation_analysis" or plan.operation == "correlation":
            col1 = plan.primary_column
            col2 = plan.secondary_column

            if not col1 or not col2 or col1 not in working_df.columns or col2 not in working_df.columns:
                return AnalyticalCalculationResult(
                    plan_id=plan.plan_id,
                    success=False,
                    direct_summary="Correlation analysis requires two valid numeric columns.",
                    error_message=f"Columns '{col1}' or '{col2}' not found.",
                )

            s1 = pd.to_numeric(working_df[col1], errors="coerce")
            s2 = pd.to_numeric(working_df[col2], errors="coerce")
            clean_pair = pd.DataFrame({"x": s1, "y": s2}).dropna()

            if len(clean_pair) < 2:
                return AnalyticalCalculationResult(
                    plan_id=plan.plan_id,
                    success=False,
                    direct_summary="Insufficient non-null numeric pairs to calculate correlation.",
                    limitations_and_warnings=["Fewer than 2 valid paired data points."],
                )

            corr_val = float(clean_pair["x"].corr(clean_pair["y"]))
            if math.isnan(corr_val):
                corr_val = 0.0

            strength = "strong" if abs(corr_val) >= 0.7 else ("moderate" if abs(corr_val) >= 0.3 else "weak")
            direction = "positive" if corr_val > 0 else "negative"

            fact_stmt = f"Pearson correlation between '{col1}' and '{col2}' is {corr_val:.3f} ({strength} {direction})."
            facts.append(
                QueryResultFact(
                    fact_id=f"fact_{fact_idx}",
                    category="correlation",
                    column_name=f"{col1}_vs_{col2}",
                    metric_name="pearson_correlation",
                    value=round(corr_val, 3),
                    formatted_statement=fact_stmt,
                )
            )

            sampled = clean_pair if len(clean_pair) <= 500 else clean_pair.sample(n=500, random_state=42)
            chart_config = None
            if plan.chart and plan.chart.chart_type != "none":
                chart_config = ChartConfig(
                    chart_id=f"chart_corr_{dataset_id[:8]}",
                    title=f"Correlation: {col1} vs {col2} (r={corr_val:.2f})",
                    chart_type="scatter",
                    x_column=col1,
                    y_column=col2,
                    plotly_data=[
                        {
                            "x": [round(float(v), 2) for v in sampled["x"]],
                            "y": [round(float(v), 2) for v in sampled["y"]],
                            "mode": "markers",
                            "type": "scatter",
                            "marker": {"color": THEME_COLORS[0], "size": 6, "opacity": 0.7},
                            "name": "Data points",
                        }
                    ],
                    plotly_layout={
                        "title": {"text": f"Correlation: {col1} vs {col2} (r={corr_val:.2f})"},
                        "xaxis": {"title": col1, "automargin": True},
                        "yaxis": {"title": col2, "automargin": True},
                    },
                )

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=f"The Pearson correlation between '{col1}' and '{col2}' is {corr_val:.3f}, indicating a {strength} {direction} correlation.",
                primary_metric=PrimaryMetric(
                    label="Pearson Correlation",
                    value=round(corr_val, 3),
                    formatted=f"{corr_val:.3f}",
                ),
                calculation_method=f"Computed Pearson correlation coefficient on {len(clean_pair):,} non-null paired observations.",
                columns_used=[col1, col2],
                filters_applied=applied_filters,
                chart=chart_config,
                grounded_facts=facts,
                limitations_and_warnings=limitations,
            )

        # =========================================================================
        # 7. RANKING TOP / BOTTOM (ROW-LEVEL WHEN NO GROUP-BY)
        # =========================================================================
        if plan.intent == "ranking_top_bottom" and not plan.group_by_columns:
            sort_col = (plan.sort.column if plan.sort else None) or plan.primary_column
            if not sort_col or sort_col not in working_df.columns:
                sort_col = working_df.columns[0]

            is_desc = plan.sort.direction == "descending" if plan.sort else True
            num_series = pd.to_numeric(working_df[sort_col], errors="coerce")
            if num_series.notna().sum() > 0:
                working_df = working_df.copy()
                working_df["_sort_num"] = num_series
                sorted_df = working_df.sort_values(by="_sort_num", ascending=not is_desc).drop(columns=["_sort_num"])
            else:
                sorted_df = working_df.sort_values(by=sort_col, ascending=not is_desc)

            limit_val = plan.limit or 5
            top_records_df = sorted_df.head(limit_val)
            table_records = sanitize_for_json(top_records_df.to_dict(orient="records"))

            first_val = top_records_df[sort_col].iloc[0] if len(top_records_df) > 0 else None
            first_val_formatted = f"{first_val}"

            facts.append(
                QueryResultFact(
                    fact_id=f"fact_{fact_idx}",
                    category="ranking",
                    column_name=sort_col,
                    metric_name=f"{'top' if is_desc else 'bottom'}_record",
                    value=first_val,
                    formatted_statement=f"The {'highest' if is_desc else 'lowest'} value in '{sort_col}' is {first_val_formatted}.",
                )
            )

            direct_ans = f"Ranked top {len(top_records_df)} records by '{sort_col}'. Highest record has {sort_col} = {first_val_formatted}."

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=direct_ans,
                primary_metric=PrimaryMetric(
                    label=f"{'Top' if is_desc else 'Bottom'} {sort_col}",
                    value=first_val,
                    formatted=first_val_formatted,
                ),
                calculation_method=f"Ranked dataset rows by '{sort_col}' ({'descending' if is_desc else 'ascending'}) across {len(working_df):,} records.",
                columns_used=[sort_col],
                filters_applied=applied_filters,
                tabular_data=table_records,
                grounded_facts=facts,
                limitations_and_warnings=limitations,
            )

        # =========================================================================
        # 8. GROUP-BY COMPARISON ANALYSIS
        # =========================================================================
        if plan.group_by_columns and len(plan.group_by_columns) > 0:
            grp_col = plan.group_by_columns[0]
            val_col = plan.primary_column or grp_col

            if grp_col not in working_df.columns:
                return AnalyticalCalculationResult(
                    plan_id=plan.plan_id,
                    success=False,
                    direct_summary=f"Grouping column '{grp_col}' not found in dataset.",
                    error_message=f"Column '{grp_col}' does not exist.",
                )

            op = plan.operation if plan.operation in ("sum", "mean", "median", "count", "min", "max", "std") else "count"

            if op != "count":
                if val_col not in working_df.columns:
                    val_col = grp_col
                    op = "count"
                else:
                    val_series = pd.to_numeric(working_df[val_col], errors="coerce")
                    working_df = working_df.copy()
                    working_df["_clean_val"] = val_series
                    val_col_to_use = "_clean_val"
            else:
                val_col_to_use = val_col

            if op == "count":
                grouped = working_df.groupby(grp_col, dropna=True).size().reset_index(name="count")
                metric_col_name = "count"
            else:
                grouped = (
                    working_df.groupby(grp_col, dropna=True)[val_col_to_use]
                    .agg(op)
                    .reset_index(name=f"{op}_{val_col}")
                )
                metric_col_name = f"{op}_{val_col}"

            is_desc = plan.sort.direction == "descending" if plan.sort else True
            grouped = grouped.sort_values(by=metric_col_name, ascending=not is_desc)
            limit_val = plan.limit or 10
            grouped_limited = grouped.head(limit_val)

            table_records = []
            for _, r in grouped_limited.iterrows():
                val_rounded = round(float(r[metric_col_name]), 2) if isinstance(r[metric_col_name], (int, float, np.number)) else r[metric_col_name]
                table_records.append({
                    grp_col: str(r[grp_col]),
                    metric_col_name: val_rounded,
                })

            for item in table_records[:3]:
                facts.append(
                    QueryResultFact(
                        fact_id=f"fact_{fact_idx}",
                        category="group_comparison",
                        column_name=grp_col,
                        metric_name=f"{op}_{item[grp_col]}",
                        value=item[metric_col_name],
                        formatted_statement=f"For '{grp_col}' = {item[grp_col]}, the {op} of {val_col} is {item[metric_col_name]}.",
                    )
                )
                fact_idx += 1

            chart_config = None
            if plan.chart and plan.chart.chart_type in ("bar", "pie"):
                c_type = plan.chart.chart_type
                if c_type == "pie" and len(table_records) <= 8:
                    chart_config = ChartConfig(
                        chart_id=f"chart_grp_pie_{dataset_id[:8]}",
                        title=f"{val_col} Breakdown by {grp_col}",
                        chart_type="pie",
                        x_column=grp_col,
                        y_column=metric_col_name,
                        plotly_data=[
                            {
                                "labels": [r[grp_col] for r in table_records],
                                "values": [r[metric_col_name] for r in table_records],
                                "type": "pie",
                                "marker": {"colors": THEME_COLORS},
                            }
                        ],
                        plotly_layout={
                            "title": {"text": f"{val_col} Breakdown by {grp_col}"},
                            "margin": {"l": 20, "r": 20, "t": 40, "b": 20},
                        },
                    )
                else:
                    chart_config = ChartConfig(
                        chart_id=f"chart_grp_bar_{dataset_id[:8]}",
                        title=f"{op.capitalize()} of {val_col} by {grp_col}",
                        chart_type="bar",
                        x_column=grp_col,
                        y_column=metric_col_name,
                        plotly_data=[
                            {
                                "x": [r[grp_col] for r in table_records],
                                "y": [r[metric_col_name] for r in table_records],
                                "type": "bar",
                                "marker": {"color": THEME_COLORS[0]},
                                "name": metric_col_name,
                            }
                        ],
                        plotly_layout={
                            "title": {"text": f"{op.capitalize()} of {val_col} by {grp_col}"},
                            "xaxis": {"title": grp_col, "automargin": True},
                            "yaxis": {"title": metric_col_name, "automargin": True},
                        },
                    )

            top_item = table_records[0] if table_records else None
            top_stmt = (
                f"The highest {op} of {val_col} occurs in '{grp_col}' = {top_item[grp_col]} with {top_item[metric_col_name]}."
                if top_item
                else "No grouped data available."
            )

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=top_stmt,
                primary_metric=PrimaryMetric(
                    label=f"Top {grp_col}",
                    value=top_item[metric_col_name] if top_item else None,
                    formatted=f"{top_item[grp_col]}: {top_item[metric_col_name]}" if top_item else "N/A",
                ),
                calculation_method=f"Grouped by '{grp_col}', aggregated '{val_col}' using {op}(), and sorted.",
                columns_used=[grp_col, val_col],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(table_records),
                chart=chart_config,
                grounded_facts=facts,
                limitations_and_warnings=limitations,
            )

        # =========================================================================
        # 8. CATEGORICAL FREQUENCY / VALUE COUNTS
        # =========================================================================
        if plan.operation == "value_counts" or (plan.intent == "distribution_analysis" and plan.primary_column and infer_column_type(working_df[plan.primary_column]) in ("string", "boolean")):
            col = plan.primary_column or working_df.columns[0]
            vc = working_df[col].astype(str).value_counts(dropna=True).head(plan.limit or 10)
            table_records = []
            for cat, count in vc.items():
                pct = round((count / total_rows) * 100.0, 2)
                table_records.append({
                    col: str(cat),
                    "count": int(count),
                    "percentage": pct,
                })

            for item in table_records[:3]:
                facts.append(
                    QueryResultFact(
                        fact_id=f"fact_{fact_idx}",
                        category="frequency",
                        column_name=col,
                        metric_name=f"frequency_{item[col]}",
                        value=item["count"],
                        formatted_statement=f"Category '{item[col]}' appears {item['count']:,} times ({item['percentage']}%).",
                    )
                )
                fact_idx += 1

            chart_config = None
            if plan.chart and plan.chart.chart_type in ("bar", "pie"):
                chart_config = ChartConfig(
                    chart_id=f"chart_vc_{dataset_id[:8]}",
                    title=f"Distribution of {col}",
                    chart_type="bar",
                    x_column=col,
                    y_column="count",
                    plotly_data=[
                        {
                            "x": [r[col] for r in table_records],
                            "y": [r["count"] for r in table_records],
                            "type": "bar",
                            "marker": {"color": THEME_COLORS[1]},
                        }
                    ],
                    plotly_layout={
                        "title": {"text": f"Frequency of {col}"},
                        "xaxis": {"title": col, "automargin": True},
                        "yaxis": {"title": "Count", "automargin": True},
                    },
                )

            top_cat = table_records[0] if table_records else None
            summary_msg = (
                f"The most frequent '{col}' is '{top_cat[col]}' with {top_cat['count']:,} occurrences ({top_cat['percentage']}%)."
                if top_cat
                else "No categories found."
            )

            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=summary_msg,
                primary_metric=PrimaryMetric(
                    label=f"Most Frequent {col}",
                    value=top_cat["count"] if top_cat else None,
                    formatted=f"{top_cat[col]} ({top_cat['count']:,})" if top_cat else "N/A",
                ),
                calculation_method=f"Computed value_counts() on column '{col}' across {total_rows:,} records.",
                columns_used=[col],
                filters_applied=applied_filters,
                tabular_data=sanitize_for_json(table_records),
                chart=chart_config,
                grounded_facts=facts,
                limitations_and_warnings=limitations,
            )

        # =========================================================================
        # 9. SINGLE COLUMN AGGREGATION (COUNT, MEAN, SUM, MEDIAN, MIN, MAX, STD)
        # =========================================================================
        col = plan.primary_column
        if not col or col not in working_df.columns:
            num_cols = [c for c in working_df.columns if infer_column_type(working_df[c]) in ("integer", "float")]
            col = num_cols[0] if num_cols else working_df.columns[0]

        op = plan.operation if plan.operation in ("sum", "mean", "median", "min", "max", "std", "count") else "mean"

        # Handle 'count' on any data type (numerical or categorical) without numeric coercion
        if op == "count":
            clean_series = working_df[col].dropna()
            total_count = len(clean_series)
            facts.append(
                QueryResultFact(
                    fact_id=f"fact_{fact_idx}",
                    category="count",
                    column_name=col,
                    metric_name="record_count",
                    value=total_count,
                    formatted_statement=f"Found {total_count:,} matching records for column '{col}'.",
                )
            )
            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=True,
                direct_summary=f"Found {total_count:,} records in column '{col}'.",
                primary_metric=PrimaryMetric(
                    label=f"Count of {col}",
                    value=total_count,
                    formatted=f"{total_count:,}",
                ),
                calculation_method=f"Counted non-null values in column '{col}' across filtered dataset.",
                columns_used=[col],
                filters_applied=applied_filters,
                grounded_facts=facts,
                limitations_and_warnings=limitations,
            )

        # For mathematical operations (mean, sum, median, min, max, std), require numeric series
        series = pd.to_numeric(working_df[col], errors="coerce")
        clean_series = series.dropna()

        null_count = int(series.isna().sum())
        if null_count > 0:
            limitations.append(f"{null_count:,} missing values in '{col}' were excluded from the calculation.")

        if len(clean_series) == 0:
            return AnalyticalCalculationResult(
                plan_id=plan.plan_id,
                success=False,
                direct_summary=f"Column '{col}' has zero valid numeric values to compute {op}.",
                limitations_and_warnings=[f"Column '{col}' is completely empty or non-numeric."],
            )

        calc_val = float(clean_series.agg(op))
        rounded_val = round(calc_val, 2)

        col_min = round(float(clean_series.min()), 2)
        col_max = round(float(clean_series.max()), 2)

        facts.append(
            QueryResultFact(
                fact_id=f"fact_{fact_idx}",
                category="numeric_statistic",
                column_name=col,
                metric_name=f"{op}_{col}",
                value=rounded_val,
                formatted_statement=f"The {op} of '{col}' is {rounded_val:,.2f}.",
            )
        )
        fact_idx += 1

        facts.append(
            QueryResultFact(
                fact_id=f"fact_{fact_idx}",
                category="sample_size",
                column_name=col,
                metric_name="non_null_count",
                value=len(clean_series),
                formatted_statement=f"Calculated across {len(clean_series):,} non-null records.",
            )
        )

        chart_config = None
        if plan.chart and plan.chart.chart_type in ("histogram", "box"):
            c_type = plan.chart.chart_type
            if c_type == "box":
                chart_config = ChartConfig(
                    chart_id=f"chart_box_{dataset_id[:8]}",
                    title=f"Box Plot of {col}",
                    chart_type="box",
                    y_column=col,
                    plotly_data=[
                        {
                            "y": [round(float(v), 2) for v in clean_series.sample(min(1000, len(clean_series)), random_state=42)],
                            "type": "box",
                            "name": col,
                            "marker": {"color": THEME_COLORS[0]},
                        }
                    ],
                    plotly_layout={
                        "title": {"text": f"Distribution Spread of {col}"},
                        "yaxis": {"title": col, "automargin": True},
                    },
                )
            else:
                chart_config = ChartConfig(
                    chart_id=f"chart_hist_{dataset_id[:8]}",
                    title=f"Histogram of {col}",
                    chart_type="histogram",
                    x_column=col,
                    plotly_data=[
                        {
                            "x": [round(float(v), 2) for v in clean_series.sample(min(1000, len(clean_series)), random_state=42)],
                            "type": "histogram",
                            "marker": {"color": THEME_COLORS[0]},
                        }
                    ],
                    plotly_layout={
                        "title": {"text": f"Frequency Distribution of {col}"},
                        "xaxis": {"title": col, "automargin": True},
                        "yaxis": {"title": "Count", "automargin": True},
                    },
                )

        direct_ans = f"The {op} of '{col}' is {rounded_val:,.2f} (ranging from {col_min:,.2f} to {col_max:,.2f})."

        return AnalyticalCalculationResult(
            plan_id=plan.plan_id,
            success=True,
            direct_summary=direct_ans,
            primary_metric=PrimaryMetric(
                label=f"{op.capitalize()} of {col}",
                value=rounded_val,
                formatted=f"{rounded_val:,.2f}",
            ),
            calculation_method=f"Applied Pandas agg('{op}') on column '{col}' over {len(clean_series):,} non-null records.",
            columns_used=[col],
            filters_applied=applied_filters,
            chart=chart_config,
            grounded_facts=facts,
            limitations_and_warnings=limitations,
        )
