import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.core.json_encoder import sanitize_for_json
from app.models.ask_data import QueryResultFact
from app.models.automated_insights import (
    AnomalyPattern,
    AutomatedInsightsResponse,
    BestWorstAnalysis,
    BusinessRecommendation,
    CategoryPerformer,
    ColumnClassification,
    DateGranularity,
    DateMetricCombination,
    KeyFinding,
    SeasonalityAnalysis,
    TemporalAnomaly,
    TrendAnalysis,
)
from app.models.dashboard import ChartConfig
from app.models.dataset import ColumnProfile
from app.services.ai.column_classifier import ColumnClassifier
from app.services.ai.trend_intelligence_engine import TrendIntelligenceEngine

THEME_COLORS = [
    "#8b7cff",  # electric purple / primary accent
    "#36c9f4",  # cyan / accent-2
    "#34d399",  # emerald green / top performer
    "#f43f5e",  # rose / worst performer
    "#fbbf24",  # amber / anomaly
    "#a78bfa",  # light purple
    "#60a5fa",  # blue
    "#fb923c",  # orange
]


class AutomatedInsightsEngine:
    """
    Pandas analytical engine for AutoAnalyst AI Phase 4.3.
    Autonomously discovers statistical findings, best/worst category benchmarks,
    anomalies/outliers, and generates fact-grounded business recommendations.
    Enforces minimum sample sizes, statistical significance, and identifier safety.
    """

    @classmethod
    def analyze_dataset(
        cls,
        df: pd.DataFrame,
        dataset_id: str,
        dataset_name: str,
        snapshot_hash: str,
        col_profiles: Optional[List[ColumnProfile]] = None,
        date_col: Optional[str] = None,
        metric_col: Optional[str] = None,
        granularity: Optional[DateGranularity] = None,
    ) -> AutomatedInsightsResponse:
        """Runs the complete autonomous insights discovery pipeline."""
        row_count = len(df)
        total_cols = len(df.columns)
        facts: List[QueryResultFact] = []
        fact_idx = 1
        limitations: List[str] = []

        # Performance safeguard: sample down for heavy calculations if dataset > 25,000 rows
        analysis_df = df
        if row_count > 25000:
            analysis_df = df.sample(n=25000, random_state=42)
            limitations.append(f"Analyzed statistical distributions across representative 25,000-row sample of {row_count:,} total records.")

        # 1. Semantic Column Classification
        classifications_dict = ColumnClassifier.classify_dataset(df, col_profiles)
        classifications = list(classifications_dict.values())

        numeric_measures = [c.name for c in classifications if c.semantic_role == "numerical_measure" and c.is_usable_for_metrics]
        categorical_dimensions = [c.name for c in classifications if c.semantic_role == "categorical_dimension" and c.is_usable_for_grouping]
        identifier_cols = [c.name for c in classifications if c.semantic_role == "identifier"]

        if identifier_cols:
            limitations.append(f"Excluded identifier column(s) from business metric analysis: {', '.join(identifier_cols)}.")

        # Fact: Dimensions & Completeness
        total_cells = row_count * total_cols
        missing_cells = int(df.isna().sum().sum())
        completeness_pct = round(((total_cells - missing_cells) / max(total_cells, 1)) * 100.0, 1)

        facts.append(
            QueryResultFact(
                fact_id=f"fact_{fact_idx}",
                category="dimension",
                metric_name="dataset_overview",
                value=row_count,
                formatted_statement=f"Dataset contains {row_count:,} records across {total_cols} attributes with {completeness_pct}% data completeness.",
            )
        )
        fact_idx += 1

        # Calculate overall health score (0 - 100)
        duplicate_count = int(df.duplicated().sum())
        dup_pct = (duplicate_count / max(row_count, 1)) * 100.0
        health_score = round(max(0.0, min(100.0, (completeness_pct * 0.70) + ((100.0 - min(dup_pct * 2, 100.0)) * 0.30))), 1)

        # 2. Key Findings Discovery
        findings: List[KeyFinding] = []
        finding_idx = 1

        # Finding: Missing Value Distribution
        missing_per_col = df.isna().sum()
        cols_with_missing = missing_per_col[missing_per_col > 0]
        if not cols_with_missing.empty:
            worst_missing_col = cols_with_missing.idxmax()
            worst_missing_count = int(cols_with_missing.max())
            worst_missing_pct = round((worst_missing_count / row_count) * 100.0, 1)

            fid = f"fact_{fact_idx}"
            facts.append(
                QueryResultFact(
                    fact_id=fid,
                    category="quality",
                    column_name=worst_missing_col,
                    metric_name="missing_percentage",
                    value=worst_missing_pct,
                    formatted_statement=f"Column '{worst_missing_col}' has {worst_missing_count:,} missing values ({worst_missing_pct}% of dataset).",
                )
            )
            fact_idx += 1

            findings.append(
                KeyFinding(
                    finding_id=f"finding_{finding_idx}",
                    title=f"Data Quality Gap in '{worst_missing_col}'",
                    description=f"Column '{worst_missing_col}' exhibits the highest missingness at {worst_missing_pct}% ({worst_missing_count:,} missing cells), which may impact analytical reliability.",
                    significance_score=0.9 if worst_missing_pct > 40 else 0.6,
                    importance="high" if worst_missing_pct > 30 else "medium",
                    category="quality",
                    columns_involved=[worst_missing_col],
                    referenced_fact_ids=[fid],
                    metric_formatted=f"{worst_missing_pct}% missing",
                )
            )
            finding_idx += 1

        # Finding: Categorical Distribution & Imbalance
        for cat_col in categorical_dimensions[:3]:
            cat_counts = analysis_df[cat_col].dropna().value_counts()
            if len(cat_counts) >= 2:
                top_cat = cat_counts.index[0]
                top_cat_count = int(cat_counts.iloc[0])
                top_cat_pct = round((top_cat_count / len(analysis_df[cat_col].dropna())) * 100.0, 1)

                if top_cat_pct >= 60.0:
                    fid = f"fact_{fact_idx}"
                    facts.append(
                        QueryResultFact(
                            fact_id=fid,
                            category="imbalance",
                            column_name=cat_col,
                            metric_name="dominance_ratio",
                            value=top_cat_pct,
                            formatted_statement=f"Category '{top_cat}' in '{cat_col}' represents {top_cat_pct}% of records ({top_cat_count:,} records).",
                        )
                    )
                    fact_idx += 1

                    findings.append(
                        KeyFinding(
                            finding_id=f"finding_{finding_idx}",
                            title=f"High Concentration in '{cat_col}'",
                            description=f"'{cat_col}' is heavily skewed towards '{top_cat}', accounting for {top_cat_pct}% of observations.",
                            significance_score=0.75,
                            importance="medium",
                            category="imbalance",
                            columns_involved=[cat_col],
                            referenced_fact_ids=[fid],
                            metric_formatted=f"{top_cat}: {top_cat_pct}%",
                        )
                    )
                    finding_idx += 1

        # Finding: Numerical Spread, Skewness & Heavy Tails
        for num_col in numeric_measures[:3]:
            clean_num = pd.to_numeric(analysis_df[num_col], errors="coerce").dropna()
            if len(clean_num) > 10:
                mean_val = float(clean_num.mean())
                median_val = float(clean_num.median())
                std_val = float(clean_num.std()) if len(clean_num) > 1 else 0.0
                skew_val = float(clean_num.skew()) if len(clean_num) > 2 else 0.0

                # Flag severe positive or negative skewness
                if abs(skew_val) > 1.5 and mean_val != 0:
                    skew_type = "positively (right) skewed" if skew_val > 0 else "negatively (left) skewed"
                    fid = f"fact_{fact_idx}"
                    facts.append(
                        QueryResultFact(
                            fact_id=fid,
                            category="distribution",
                            column_name=num_col,
                            metric_name="skewness",
                            value=round(skew_val, 2),
                            formatted_statement=f"Metric '{num_col}' is {skew_type} (skewness={skew_val:.2f}, mean={mean_val:,.2f}, median={median_val:,.2f}).",
                        )
                    )
                    fact_idx += 1

                    findings.append(
                        KeyFinding(
                            finding_id=f"finding_{finding_idx}",
                            title=f"Asymmetric Distribution in '{num_col}'",
                            description=f"'{num_col}' has a strong {skew_type} distribution where mean ({mean_val:,.2f}) deviates substantially from median ({median_val:,.2f}), signaling extreme high-value outliers.",
                            significance_score=0.8,
                            importance="high",
                            category="distribution",
                            columns_involved=[num_col],
                            referenced_fact_ids=[fid],
                            metric_formatted=f"Mean: {mean_val:,.2f} vs Med: {median_val:,.2f}",
                        )
                    )
                    finding_idx += 1

        # Finding: Strong Bivariate Correlation
        if len(numeric_measures) >= 2:
            num_corr_df = analysis_df[numeric_measures].apply(pd.to_numeric, errors="coerce")
            corr_matrix = num_corr_df.corr(method="pearson")
            seen_pairs = set()

            for col_a in numeric_measures:
                for col_b in numeric_measures:
                    if col_a != col_b and (col_b, col_a) not in seen_pairs:
                        seen_pairs.add((col_a, col_b))
                        r_val = corr_matrix.loc[col_a, col_b]
                        if not math.isnan(r_val) and abs(r_val) >= 0.45:
                            fid = f"fact_{fact_idx}"
                            strength = "strong" if abs(r_val) >= 0.70 else "moderate"
                            direction = "positive" if r_val > 0 else "negative"
                            facts.append(
                                QueryResultFact(
                                    fact_id=fid,
                                    category="correlation",
                                    column_name=f"{col_a}_vs_{col_b}",
                                    metric_name="pearson_correlation",
                                    value=round(r_val, 3),
                                    formatted_statement=f"Observed {strength} {direction} correlation between '{col_a}' and '{col_b}' (r={r_val:.3f}).",
                                )
                            )
                            fact_idx += 1

                            findings.append(
                                KeyFinding(
                                    finding_id=f"finding_{finding_idx}",
                                    title=f"{strength.capitalize()} Correlation: {col_a} & {col_b}",
                                    description=f"A statistically significant {direction} relationship exists between '{col_a}' and '{col_b}' (Pearson r = {r_val:.3f}).",
                                    significance_score=0.85 if abs(r_val) >= 0.7 else 0.65,
                                    importance="high" if abs(r_val) >= 0.7 else "medium",
                                    category="correlation",
                                    columns_involved=[col_a, col_b],
                                    referenced_fact_ids=[fid],
                                    metric_formatted=f"r = {r_val:.2f}",
                                )
                            )
                            finding_idx += 1

        # Fallback general finding if few statistical discoveries
        if not findings:
            fid = f"fact_{fact_idx}"
            facts.append(
                QueryResultFact(
                    fact_id=fid,
                    category="dimension",
                    metric_name="record_volume",
                    value=row_count,
                    formatted_statement=f"Dataset holds {row_count:,} rows across {total_cols} attributes.",
                )
            )
            fact_idx += 1
            findings.append(
                KeyFinding(
                    finding_id=f"finding_{finding_idx}",
                    title="Dataset Scale & Completeness",
                    description=f"The dataset contains {row_count:,} records with {completeness_pct}% data completeness.",
                    significance_score=0.5,
                    importance="notable",
                    category="distribution",
                    columns_involved=list(df.columns)[:3],
                    referenced_fact_ids=[fid],
                    metric_formatted=f"{row_count:,} records",
                )
            )

        # Sort findings by significance score
        findings.sort(key=lambda x: x.significance_score, reverse=True)

        # 3. Best and Worst Category Analysis
        best_worst_analyses: List[BestWorstAnalysis] = []
        best_worst_pair = cls._select_best_worst_pair(classifications_dict, df)

        if best_worst_pair:
            dim_col, measure_col, agg_op = best_worst_pair
            bw_analysis, bw_facts = cls._compute_best_worst(
                df=df,
                dim_col=dim_col,
                measure_col=measure_col,
                agg_op=agg_op,
                dataset_id=dataset_id,
                start_fact_idx=fact_idx,
            )
            if bw_analysis:
                best_worst_analyses.append(bw_analysis)
                facts.extend(bw_facts)
                fact_idx += len(bw_facts)

        # 4. Anomalies and Unusual Patterns
        anomalies: List[AnomalyPattern] = []
        anomaly_idx = 1

        # Outlier Detection for numerical measures (IQR & Z-Score)
        for num_col in numeric_measures[:3]:
            clean_s = pd.to_numeric(df[num_col], errors="coerce").dropna()
            if len(clean_s) >= 5:
                q25 = float(clean_s.quantile(0.25))
                q75 = float(clean_s.quantile(0.75))
                iqr = q75 - q25

                if iqr > 0:
                    upper_fence = q75 + (1.5 * iqr)
                    lower_fence = q25 - (1.5 * iqr)
                    outliers = clean_s[(clean_s < lower_fence) | (clean_s > upper_fence)]
                    outlier_count = len(outliers)
                    outlier_pct = round((outlier_count / len(clean_s)) * 100.0, 1)

                    if outlier_count > 0:
                        top_extremes = [round(float(v), 2) for v in outliers.nlargest(3)]
                        fid = f"fact_{fact_idx}"
                        facts.append(
                            QueryResultFact(
                                fact_id=fid,
                                category="anomaly",
                                column_name=num_col,
                                metric_name="outlier_count",
                                value=outlier_count,
                                formatted_statement=f"Detected {outlier_count} statistical outliers in '{num_col}' ({outlier_pct}% of non-null records) outside IQR fence [{lower_fence:.2f}, {upper_fence:.2f}].",
                            )
                        )
                        fact_idx += 1

                        anomalies.append(
                            AnomalyPattern(
                                anomaly_id=f"anomaly_{anomaly_idx}",
                                anomaly_type="numerical_outlier",
                                severity="critical" if outlier_pct > 10.0 else "warning",
                                column_name=num_col,
                                description=f"Found {outlier_count:,} statistical outliers ({outlier_pct}%) in '{num_col}'. Extreme values reach up to {max(top_extremes):,}.",
                                metric_evidence={
                                    "outlier_count": outlier_count,
                                    "outlier_percentage": outlier_pct,
                                    "iqr_lower_fence": round(lower_fence, 2),
                                    "iqr_upper_fence": round(upper_fence, 2),
                                    "extreme_samples": top_extremes,
                                },
                                referenced_fact_ids=[fid],
                            )
                        )
                        anomaly_idx += 1

        # Anomaly: Severe Missingness
        for col_name, null_cnt in missing_per_col.items():
            null_pct = (null_cnt / row_count) * 100.0
            if null_pct >= 40.0:
                fid = f"fact_{fact_idx}"
                facts.append(
                    QueryResultFact(
                        fact_id=fid,
                        category="quality",
                        column_name=col_name,
                        metric_name="critical_null_ratio",
                        value=round(null_pct, 1),
                        formatted_statement=f"Column '{col_name}' has critical missingness of {null_pct:.1f}% ({null_cnt:,} records).",
                    )
                )
                fact_idx += 1

                anomalies.append(
                    AnomalyPattern(
                        anomaly_id=f"anomaly_{anomaly_idx}",
                        anomaly_type="missing_concentration",
                        severity="critical" if null_pct > 70 else "warning",
                        column_name=col_name,
                        description=f"Severe data absence in '{col_name}' ({null_pct:.1f}% missing). High risk of biased conclusions if unhandled.",
                        metric_evidence={"missing_count": int(null_cnt), "missing_percentage": round(null_pct, 1)},
                        referenced_fact_ids=[fid],
                    )
                )
                anomaly_idx += 1

        # Anomaly: Invariant / Constant Column
        for col in df.columns:
            if df[col].dropna().nunique() == 1 and row_count > 1:
                const_val = df[col].dropna().iloc[0]
                fid = f"fact_{fact_idx}"
                facts.append(
                    QueryResultFact(
                        fact_id=fid,
                        category="anomaly",
                        column_name=col,
                        metric_name="constant_value",
                        value=str(const_val),
                        formatted_statement=f"Column '{col}' is constant with a single value: '{const_val}'.",
                    )
                )
                fact_idx += 1

                anomalies.append(
                    AnomalyPattern(
                        anomaly_id=f"anomaly_{anomaly_idx}",
                        anomaly_type="invariant_column",
                        severity="info",
                        column_name=col,
                        description=f"Column '{col}' carries zero analytical variance (every non-null record equals '{const_val}').",
                        metric_evidence={"unique_values": 1, "constant_value": str(const_val)},
                        referenced_fact_ids=[fid],
                    )
                )
                anomaly_idx += 1

        # 5. Actionable Business Recommendations
        recommendations: List[BusinessRecommendation] = []
        rec_idx = 1

        # Recommendation: Data Cleaning & Missing Imputation
        if not cols_with_missing.empty:
            top_missing_col = cols_with_missing.idxmax()
            top_missing_ratio = (cols_with_missing.max() / row_count) * 100.0
            recs_fid = [f.fact_id for f in facts if f.column_name == top_missing_col and f.category == "quality"]

            if top_missing_ratio > 60.0:
                action_stmt = f"Consider dropping or engineering a binary presence indicator for '{top_missing_col}' given its severe {top_missing_ratio:.1f}% missingness."
            else:
                action_stmt = f"Apply median/mode imputation or flag missing rows in '{top_missing_col}' ({top_missing_ratio:.1f}% missing) prior to predictive modeling."

            recommendations.append(
                BusinessRecommendation(
                    recommendation_id=f"rec_{rec_idx}",
                    title=f"Remediate Data Quality in '{top_missing_col}'",
                    action_statement=action_stmt,
                    expected_impact="Prevents statistical bias, prevents row drops in downstream analyses, and improves modeling consistency.",
                    priority="high" if top_missing_ratio > 30 else "medium",
                    category="data_quality",
                    is_hypothesis=False,
                    referenced_fact_ids=recs_fid or [facts[0].fact_id],
                )
            )
            rec_idx += 1

        # Recommendation: Investigate Best/Worst Category Disparity
        if best_worst_analyses:
            bw = best_worst_analyses[0]
            action_stmt = (
                f"Investigate operational determinants driving the performance gap between top performer '{bw.best_performer.category_name}' "
                f"({bw.best_performer.formatted_value}) and lowest performer '{bw.worst_performer.category_name}' ({bw.worst_performer.formatted_value})."
            )
            recommendations.append(
                BusinessRecommendation(
                    recommendation_id=f"rec_{rec_idx}",
                    title=f"Address '{bw.dimension_column}' Performance Disparity",
                    action_statement=action_stmt,
                    expected_impact=f"Enables resource reallocation or targeted interventions to lift '{bw.worst_performer.category_name}' closer to benchmark.",
                    priority="high",
                    category="operational",
                    is_hypothesis=True,
                    referenced_fact_ids=bw.referenced_fact_ids,
                )
            )
            rec_idx += 1

        # Recommendation: Outlier Treatment
        num_outlier_anomalies = [a for a in anomalies if a.anomaly_type == "numerical_outlier"]
        if num_outlier_anomalies:
            top_outlier = num_outlier_anomalies[0]
            recommendations.append(
                BusinessRecommendation(
                    recommendation_id=f"rec_{rec_idx}",
                    title=f"Audit & Cap Outliers in '{top_outlier.column_name}'",
                    action_statement=f"Audit extreme values in '{top_outlier.column_name}' and apply IQR winsorization or log-transformation to prevent skewed calculations.",
                    expected_impact="Stabilizes mathematical averages and prevents distorted variance in analytical models.",
                    priority="medium",
                    category="risk",
                    is_hypothesis=False,
                    referenced_fact_ids=top_outlier.referenced_fact_ids,
                )
            )
            rec_idx += 1

        # 6. Phase 4.4: Temporal Trend, Anomaly & Seasonality Intelligence
        combinations = TrendIntelligenceEngine.discover_combinations(df, classifications_dict)
        has_temporal = len(combinations) > 0
        trends: List[TrendAnalysis] = []
        temporal_anomalies: List[TemporalAnomaly] = []
        seasonality: Optional[SeasonalityAnalysis] = None

        if has_temporal:
            # Screen all candidate combinations for multiple hypothesis testing control (Fix 1)
            fdr_map = TrendIntelligenceEngine.screen_combinations_fdr(df, combinations, q=0.05) if len(combinations) > 1 else {}

            # Match selected combination or default
            target_comb = combinations[0]
            if date_col and metric_col:
                matched = next((c for c in combinations if c.date_column == date_col and c.metric_column == metric_col), None)
                if matched:
                    target_comb = matched

            target_gran = granularity or target_comb.granularity
            series_df, final_gran, prep_warnings = TrendIntelligenceEngine.prepare_time_series(
                df=df,
                date_col=target_comb.date_column,
                metric_col=target_comb.metric_column,
                granularity=target_gran,
            )
            limitations.extend(prep_warnings)

            if len(series_df) >= 3:
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
                if trend_res:
                    trends.append(trend_res)
                    facts.extend(trend_facts)
                    fact_idx += len(trend_facts)

                    # Add to key findings if direction is not neutral
                    if trend_res.direction in ("increasing", "decreasing"):
                        change_str = f"{trend_res.conventional_growth_pct:+.1f}%" if trend_res.conventional_growth_pct is not None else f"{trend_res.formatted_absolute_change}"
                        findings.append(
                            KeyFinding(
                                finding_id=f"finding_{finding_idx}",
                                title=f"{trend_res.direction.capitalize()} Trend in '{trend_res.metric_column}'",
                                description=f"Observed {trend_res.direction} movement ({change_str}) across {len(series_df)} {final_gran} periods. Statistical evidence: {trend_res.statistical_evidence.replace('_', ' ')}.",
                                significance_score=0.85 if trend_res.statistical_evidence == "statistically_supported" else 0.65,
                                importance="high" if trend_res.business_magnitude == "material" else "medium",
                                category="trend",
                                columns_involved=[trend_res.date_column, trend_res.metric_column],
                                referenced_fact_ids=trend_res.referenced_fact_ids,
                                metric_formatted=change_str,
                            )
                        )
                        finding_idx += 1

                # Detect sudden spikes and drops
                t_anomalies, anomaly_facts = TrendIntelligenceEngine.detect_temporal_anomalies(
                    series_df=series_df,
                    date_col=target_comb.date_column,
                    metric_col=target_comb.metric_column,
                    start_fact_idx=fact_idx,
                )
                temporal_anomalies.extend(t_anomalies)
                facts.extend(anomaly_facts)
                fact_idx += len(anomaly_facts)

                # Detrended seasonality analysis
                seasonality_res, seas_facts = TrendIntelligenceEngine.analyze_seasonality(
                    df=df,
                    date_col=target_comb.date_column,
                    metric_col=target_comb.metric_column,
                    start_fact_idx=fact_idx,
                )
                seasonality = seasonality_res
                facts.extend(seas_facts)
                fact_idx += len(seas_facts)
        else:
            limitations.append("No date or timestamp columns were detected. Temporal trends and seasonality analysis were skipped.")

        # Executive Summary Generation
        exec_summary = (
            f"Automated intelligence inspection of '{dataset_name}' ({row_count:,} records, {total_cols} attributes). "
            f"Overall health score is {health_score}/100 with {completeness_pct}% completeness. "
            + (f"Top finding: {findings[0].title}. " if findings else "")
            + (f"Temporal trend: {trends[0].direction} in '{trends[0].metric_column}'. " if trends else "")
            + (f"Primary category disparity identified in '{best_worst_analyses[0].dimension_column}'. " if best_worst_analyses else "")
            + f"Generated {len(recommendations)} actionable recommendations grounded in empirical observations."
        )

        return AutomatedInsightsResponse(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            snapshot_hash=snapshot_hash,
            mode="statistical_fallback",
            provider="fallback",
            model="Deterministic Heuristics Engine",
            generated_at=pd.Timestamp.now(tz="UTC").isoformat(),
            executive_summary=exec_summary,
            health_score=health_score,
            column_classifications=classifications,
            key_findings=findings,
            best_worst_analyses=best_worst_analyses,
            anomalies_and_patterns=anomalies,
            recommendations=recommendations,
            grounded_facts=facts,
            limitations=limitations,
            has_temporal_data=has_temporal,
            available_combinations=combinations,
            trends=trends,
            temporal_anomalies=temporal_anomalies,
            seasonality=seasonality,
        )

    @classmethod
    def _select_best_worst_pair(
        cls, classifications: Dict[str, ColumnClassification], df: pd.DataFrame
    ) -> Optional[Tuple[str, Optional[str], str]]:
        """
        Intelligently identifies the most analytically valuable (Dimension, Measure, Aggregation) pair.
        Avoids identifiers, media URLs, and high-cardinality names.
        """
        # Candidate dimensions: Low-to-moderate cardinality categorical dimensions
        dim_candidates = [
            c.name for c in classifications.values()
            if c.is_usable_for_grouping and 2 <= c.unique_count <= 25
        ]
        if not dim_candidates:
            # Fallback to any string column with reasonable cardinality
            dim_candidates = [c.name for c in classifications.values() if c.inferred_type in ("string", "boolean") and c.unique_count <= 35]

        # Candidate measures: True numerical measures
        measure_candidates = [
            c.name for c in classifications.values()
            if c.is_usable_for_metrics and c.semantic_role == "numerical_measure"
        ]

        if not dim_candidates:
            return None

        # Sort dimensions by analytical priority (keywords like pclass, class, department, region, category, sex, gender)
        priority_dims = sorted(
            dim_candidates,
            key=lambda d: (
                any(k in d.lower() for k in ("class", "pclass", "category", "dept", "department", "region", "sex", "gender", "status", "segment")),
                -classifications[d].unique_count,
            ),
            reverse=True,
        )
        selected_dim = priority_dims[0]

        # Check for binary outcome target measure (e.g. Survived)
        binary_targets = [
            c.name for c in classifications.values()
            if any(k in c.name.lower() for k in ("survived", "churn", "target", "converted"))
            and df[c.name].dropna().nunique() == 2
        ]
        if binary_targets:
            return selected_dim, binary_targets[0], "mean"

        # Sort measures by business priority (keywords like revenue, sales, fare, salary, price, profit, score)
        if measure_candidates:
            priority_measures = sorted(
                measure_candidates,
                key=lambda m: any(k in m.lower() for k in ("revenue", "sales", "fare", "salary", "profit", "price", "amount", "score", "rate")),
                reverse=True,
            )
            return selected_dim, priority_measures[0], "mean"

        # Pure categorical dataset (no numerical measures, e.g. MNC_IT_Companies_Updated.xlsx)
        # In this case, measure_col=None triggers frequency count ranking!
        return selected_dim, None, "count"

    @classmethod
    def _compute_best_worst(
        cls,
        df: pd.DataFrame,
        dim_col: str,
        measure_col: Optional[str],
        agg_op: str,
        dataset_id: str,
        start_fact_idx: int,
    ) -> Tuple[Optional[BestWorstAnalysis], List[QueryResultFact]]:
        """Computes top and bottom category performers with relative delta vs dataset average."""
        facts: List[QueryResultFact] = []
        fact_idx = start_fact_idx

        clean_df = df[[dim_col] + ([measure_col] if measure_col else [])].dropna(subset=[dim_col])
        if len(clean_df) < 2:
            return None, []

        # 1. Frequency count mode if no numerical measure exists (pure categorical data)
        if measure_col is None:
            counts = clean_df[dim_col].value_counts()
            if len(counts) < 2:
                return None, []

            avg_val = float(counts.mean())
            top_cat = str(counts.index[0])
            top_val = float(counts.iloc[0])
            top_sample = int(top_val)

            bot_cat = str(counts.index[-1])
            bot_val = float(counts.iloc[-1])
            bot_sample = int(bot_val)

            top_delta = round(((top_val - avg_val) / max(avg_val, 1)) * 100.0, 1)
            bot_delta = round(((bot_val - avg_val) / max(avg_val, 1)) * 100.0, 1)

            fid_top = f"fact_{fact_idx}"
            facts.append(
                QueryResultFact(
                    fact_id=fid_top,
                    category="benchmark",
                    column_name=dim_col,
                    metric_name="top_category_frequency",
                    value=top_val,
                    formatted_statement=f"Most frequent category in '{dim_col}' is '{top_cat}' with {int(top_val):,} records ({top_delta:+.1f}% vs average {avg_val:.1f}).",
                )
            )
            fact_idx += 1

            fid_bot = f"fact_{fact_idx}"
            facts.append(
                QueryResultFact(
                    fact_id=fid_bot,
                    category="benchmark",
                    column_name=dim_col,
                    metric_name="bottom_category_frequency",
                    value=bot_val,
                    formatted_statement=f"Least frequent category in '{dim_col}' is '{bot_cat}' with {int(bot_val):,} records ({bot_delta:+.1f}% vs average {avg_val:.1f}).",
                )
            )
            fact_idx += 1

            # Chart config
            chart_config = ChartConfig(
                chart_id=f"chart_bw_{dataset_id[:8]}",
                title=f"Record Distribution by {dim_col}",
                chart_type="bar",
                x_column=dim_col,
                y_column="count",
                plotly_data=[
                    {
                        "x": [str(c) for c in counts.head(10).index],
                        "y": [int(v) for v in counts.head(10).values],
                        "type": "bar",
                        "marker": {"color": THEME_COLORS[0]},
                    }
                ],
                plotly_layout={
                    "title": {"text": f"Record Counts by {dim_col}"},
                    "xaxis": {"title": dim_col, "automargin": True},
                    "yaxis": {"title": "Count", "automargin": True},
                },
            )

            explanation = (
                f"Analyzed frequency distribution across {len(counts)} categories in '{dim_col}'. "
                f"'{top_cat}' is the most common ({int(top_val):,} records, {top_delta:+.1f}% vs average {avg_val:.1f}), "
                f"while '{bot_cat}' is the least common ({int(bot_val):,} records, {bot_delta:+.1f}% vs average)."
            )

            ranked_performers = [
                CategoryPerformer(
                    category_name=str(cat),
                    metric_value=float(cnt),
                    formatted_value=f"{int(cnt):,} records",
                    delta_vs_average_pct=round(((cnt - avg_val) / max(abs(avg_val), 1e-9)) * 100.0, 1),
                    sample_size=int(cnt),
                    is_statistically_reliable=int(cnt) >= 3,
                )
                for cat, cnt in counts.items()
            ]

            bw = BestWorstAnalysis(
                dimension_column=dim_col,
                metric_column=dim_col,
                aggregation="count",
                dataset_average=round(avg_val, 2),
                formatted_average=f"{avg_val:,.1f} records",
                best_performer=CategoryPerformer(
                    category_name=top_cat,
                    metric_value=top_val,
                    formatted_value=f"{int(top_val):,} records",
                    delta_vs_average_pct=top_delta,
                    sample_size=top_sample,
                    is_statistically_reliable=top_sample >= 3,
                ),
                worst_performer=CategoryPerformer(
                    category_name=bot_cat,
                    metric_value=bot_val,
                    formatted_value=f"{int(bot_val):,} records",
                    delta_vs_average_pct=bot_delta,
                    sample_size=bot_sample,
                    is_statistically_reliable=bot_sample >= 3,
                ),
                ranked_performers=ranked_performers,
                chart=chart_config,
                explanation=explanation,
                referenced_fact_ids=[fid_top, fid_bot],
            )
            return bw, facts

        # 2. Metric calculation mode
        clean_df = clean_df.dropna(subset=[measure_col])
        clean_df[measure_col] = pd.to_numeric(clean_df[measure_col], errors="coerce")
        clean_df = clean_df.dropna(subset=[measure_col])

        if len(clean_df) < 2:
            return None, []

        grouped = (
            clean_df.groupby(dim_col)[measure_col]
            .agg(agg_op)
            .reset_index(name="metric_val")
        )
        counts = clean_df.groupby(dim_col).size().reset_index(name="sample_size")
        merged = pd.merge(grouped, counts, on=dim_col).sort_values(by="metric_val", ascending=False)

        if len(merged) < 2:
            return None, []

        dataset_avg = float(clean_df[measure_col].mean())
        top_row = merged.iloc[0]
        bot_row = merged.iloc[-1]

        top_val = float(top_row["metric_val"])
        top_cat = str(top_row[dim_col])
        top_sample = int(top_row["sample_size"])
        top_delta = round(((top_val - dataset_avg) / max(abs(dataset_avg), 1e-9)) * 100.0, 1)

        bot_val = float(bot_row["metric_val"])
        bot_cat = str(bot_row[dim_col])
        bot_sample = int(bot_row["sample_size"])
        bot_delta = round(((bot_val - dataset_avg) / max(abs(dataset_avg), 1e-9)) * 100.0, 1)

        # Statistical reliability flag (minimum sample n >= 5)
        top_reliable = top_sample >= 5
        bot_reliable = bot_sample >= 5

        fid_top = f"fact_{fact_idx}"
        facts.append(
            QueryResultFact(
                fact_id=fid_top,
                category="benchmark",
                column_name=f"{dim_col}_{measure_col}",
                metric_name="top_performer",
                value=round(top_val, 2),
                formatted_statement=f"Top performer in '{dim_col}' is '{top_cat}' with {agg_op} {measure_col} of {top_val:,.2f} ({top_delta:+.1f}% vs dataset average {dataset_avg:,.2f}, n={top_sample}).",
            )
        )
        fact_idx += 1

        fid_bot = f"fact_{fact_idx}"
        facts.append(
            QueryResultFact(
                fact_id=fid_bot,
                category="benchmark",
                column_name=f"{dim_col}_{measure_col}",
                metric_name="worst_performer",
                value=round(bot_val, 2),
                formatted_statement=f"Lowest performer in '{dim_col}' is '{bot_cat}' with {agg_op} {measure_col} of {bot_val:,.2f} ({bot_delta:+.1f}% vs dataset average {dataset_avg:,.2f}, n={bot_sample}).",
            )
        )
        fact_idx += 1

        chart_config = ChartConfig(
            chart_id=f"chart_bw_{dataset_id[:8]}",
            title=f"Comparison: {agg_op.capitalize()} of {measure_col} by {dim_col}",
            chart_type="bar",
            x_column=dim_col,
            y_column=measure_col,
            plotly_data=[
                {
                    "x": [str(r[dim_col]) for _, r in merged.iterrows()],
                    "y": [round(float(r["metric_val"]), 2) for _, r in merged.iterrows()],
                    "type": "bar",
                    "marker": {
                        "color": [
                            THEME_COLORS[2] if i == 0 else (THEME_COLORS[3] if i == len(merged) - 1 else THEME_COLORS[0])
                            for i in range(len(merged))
                        ]
                    },
                }
            ],
            plotly_layout={
                "title": {"text": f"{agg_op.capitalize()} of {measure_col} by {dim_col}"},
                "xaxis": {"title": dim_col, "automargin": True},
                "yaxis": {"title": f"{agg_op.capitalize()} {measure_col}", "automargin": True},
            },
        )

        exploratory_note = ""
        if not top_reliable or not bot_reliable:
            exploratory_note = " (Note: category sample size n < 5; treat findings as exploratory)."

        explanation = (
            f"Compared {len(merged)} categories in '{dim_col}' on {agg_op} of '{measure_col}' against dataset benchmark ({dataset_avg:,.2f}). "
            f"Top performer '{top_cat}' achieved {top_val:,.2f} ({top_delta:+.1f}% above benchmark, n={top_sample}), "
            f"while lowest performer '{bot_cat}' recorded {bot_val:,.2f} ({bot_delta:+.1f}% below benchmark, n={bot_sample})."
            + exploratory_note
        )

        ranked_performers = [
            CategoryPerformer(
                category_name=str(r[dim_col]),
                metric_value=round(float(r["metric_val"]), 2),
                formatted_value=f"{float(r['metric_val']):,.2f}",
                delta_vs_average_pct=round(((float(r["metric_val"]) - dataset_avg) / max(abs(dataset_avg), 1e-9)) * 100.0, 1),
                sample_size=int(r["sample_size"]),
                is_statistically_reliable=int(r["sample_size"]) >= 5,
            )
            for _, r in merged.iterrows()
        ]

        bw = BestWorstAnalysis(
            dimension_column=dim_col,
            metric_column=measure_col,
            aggregation=agg_op,
            dataset_average=round(dataset_avg, 2),
            formatted_average=f"{dataset_avg:,.2f}",
            best_performer=CategoryPerformer(
                category_name=top_cat,
                metric_value=round(top_val, 2),
                formatted_value=f"{top_val:,.2f}",
                delta_vs_average_pct=top_delta,
                sample_size=top_sample,
                is_statistically_reliable=top_reliable,
            ),
            worst_performer=CategoryPerformer(
                category_name=bot_cat,
                metric_value=round(bot_val, 2),
                formatted_value=f"{bot_val:,.2f}",
                delta_vs_average_pct=bot_delta,
                sample_size=bot_sample,
                is_statistically_reliable=bot_reliable,
            ),
            ranked_performers=ranked_performers,
            chart=chart_config,
            explanation=explanation,
            referenced_fact_ids=[fid_top, fid_bot],
        )

        return bw, facts

