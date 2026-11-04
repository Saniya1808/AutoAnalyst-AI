from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.models.ai_understanding import (
    AnalyticalInsightsAI,
    ColumnUnderstandingAI,
    ComputedFact,
    DatasetOverviewAI,
    ObservationAI,
    RecommendedChartAI,
    RelationshipAI,
    SuggestedAnalysisAI,
    SuggestedKPI,
    TargetVariableDetection,
)
from app.services.profiler import infer_column_type


class HeuristicFallbackEngine:
    @staticmethod
    def infer_domain(filename: str, columns: List[str]) -> Tuple[str, str]:
        """Infer business domain and analytical purpose using vocabulary heuristics."""
        cols_lower = [c.lower() for c in columns]
        file_lower = filename.lower()

        if any(w in file_lower or w in cols_lower for w in ("survived", "passenger", "ticket", "cabin", "embark")):
            return (
                "Maritime Transport & Passenger Demographics",
                "Analyzing passenger survival determinants and evacuation equity across travel classes.",
            )
        elif any(w in file_lower or w in cols_lower for w in ("sales", "order", "revenue", "price", "product", "customer")):
            return (
                "E-Commerce, Retail & Commercial Sales",
                "Evaluating commercial sales performance, customer purchasing behavior, and revenue trends.",
            )
        elif any(w in file_lower or w in cols_lower for w in ("employee", "salary", "attrition", "department", "tenure")):
            return (
                "Human Resources & Workforce Analytics",
                "Understanding employee retention, compensation parity, and organizational department dynamics.",
            )
        elif any(w in file_lower or w in cols_lower for w in ("patient", "diagnosis", "disease", "treatment", "blood", "medical")):
            return (
                "Healthcare, Clinical & Patient Diagnostics",
                "Investigating clinical health metrics, patient outcomes, and medical intervention effectiveness.",
            )
        elif any(w in file_lower or w in cols_lower for w in ("company", "industry", "sector", "valuation", "headquarters")):
            return (
                "Corporate Information & Industry Analysis",
                "Profiling multinational enterprise presence, industry categorization, and geographic distribution.",
            )
        else:
            return (
                "General Structured Tabular Dataset",
                f"Multi-attribute statistical analysis and exploratory data evaluation for '{filename}'.",
            )

    @classmethod
    def generate_heuristic_understanding(
        cls,
        df: pd.DataFrame,
        filename: str,
        computed_facts: Dict[str, ComputedFact],
        distilled_context: Dict[str, Any],
        error_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes a complete, rigorous dataset understanding directly from Pandas calculations.
        Ensures 100% adherence to actual computed numbers and fact IDs.
        """
        columns = list(df.columns)
        total_rows = len(df)
        total_cols = len(columns)

        domain, likely_purpose = cls.infer_domain(filename, columns)

        # Detect potential target variable
        target_var = None
        target_candidates = ["survived", "churn", "target", "label", "outcome", "status", "price", "sales", "salary"]
        for c in columns:
            if c.lower() in target_candidates:
                col_facts = [fid for fid, f in computed_facts.items() if f.column_name == c]
                target_var = TargetVariableDetection(
                    column_name=c,
                    confidence="high" if c.lower() in ("survived", "churn", "target") else "medium",
                    reasoning=f"Column '{c}' represents a primary business outcome or classification objective.",
                    referenced_fact_ids=col_facts,
                )
                break

        # Dimension fact IDs
        dim_fact_ids = [fid for fid, f in computed_facts.items() if f.category == "dimension"]
        quality_fact_ids = [fid for fid, f in computed_facts.items() if f.category == "quality"]

        exec_summary = (
            f"This dataset comprises {total_rows:,} records across {total_cols} attributes pertaining to {domain}. "
            f"Data completeness and feature distributions suggest it is structured for {likely_purpose.lower()}"
        )

        overview = DatasetOverviewAI(
            domain=domain,
            likely_purpose=likely_purpose,
            executive_summary=exec_summary,
            detected_target_variable=target_var,
            referenced_fact_ids=dim_fact_ids + quality_fact_ids,
        )

        # Column understandings
        column_understandings: List[ColumnUnderstandingAI] = []
        numeric_cols: List[str] = []
        categorical_cols: List[str] = []

        for col in columns:
            series = df[col]
            sem_type = infer_column_type(series)
            nunique = series.nunique(dropna=True)
            null_count = int(series.isna().sum())

            if sem_type in ("integer", "float"):
                numeric_cols.append(col)
            elif sem_type in ("string", "boolean"):
                categorical_cols.append(col)

            is_id = nunique == total_rows and total_rows > 10 and col.lower().endswith(("id", "num", "code"))
            is_key = target_var and target_var.column_name == col or (nunique > 1 and nunique < 50)

            col_fact_ids = [fid for fid, f in computed_facts.items() if f.column_name == col]

            quality_note = None
            if null_count > 0:
                quality_note = f"Contains {null_count} missing values ({round(null_count / total_rows * 100, 1)}%)."

            meaning = f"Records {sem_type} values representing '{col}'."
            if is_id:
                meaning = f"Unique primary record identifier for individual rows."
            elif is_key:
                meaning = f"High-priority analytical attribute capturing '{col}' variations across records."

            column_understandings.append(
                ColumnUnderstandingAI(
                    name=col,
                    semantic_type=sem_type,
                    business_meaning=meaning,
                    is_key_feature=bool(is_key),
                    is_identifier=bool(is_id),
                    data_quality_note=quality_note,
                    referenced_fact_ids=col_fact_ids,
                )
            )

        # Observations
        observations: List[ObservationAI] = []
        # Fact 1: Missing values
        missing_fact = next((f for f in computed_facts.values() if f.metric_name == "missing_cells"), None)
        if missing_fact and missing_fact.value > 0:
            observations.append(
                ObservationAI(
                    observation_type="observed_fact",
                    statement=missing_fact.formatted_statement,
                    business_implication="Requires statistical imputation or filtering to avoid skewing downstream analytics.",
                    referenced_fact_ids=[missing_fact.fact_id],
                    is_verified_fact=True,
                )
            )

        # Fact 2: Numeric summary
        for f in computed_facts.values():
            if f.category == "numeric_statistic":
                observations.append(
                    ObservationAI(
                        observation_type="observed_fact",
                        statement=f.formatted_statement,
                        business_implication=f"Defines baseline operational scale and central tendency for '{f.column_name}'.",
                        referenced_fact_ids=[f.fact_id],
                        is_verified_fact=True,
                    )
                )
                break

        # Fact 3: Categorical concentration
        for f in computed_facts.values():
            if f.category == "categorical_distribution":
                observations.append(
                    ObservationAI(
                        observation_type="observed_fact",
                        statement=f.formatted_statement,
                        business_implication=f"Highlights category concentration and dominance patterns for '{f.column_name}'.",
                        referenced_fact_ids=[f.fact_id],
                        is_verified_fact=True,
                    )
                )
                break

        # Hypothesis
        if target_var:
            observations.append(
                ObservationAI(
                    observation_type="hypothesis",
                    statement=f"Feature variations across demographics likely exert statistically significant influence on '{target_var.column_name}'.",
                    business_implication="Suggests segmenting populations to isolate key predictive drivers.",
                    referenced_fact_ids=target_var.referenced_fact_ids,
                    is_verified_fact=False,
                )
            )

        # Relationships
        relationships: List[RelationshipAI] = []
        if len(numeric_cols) >= 2:
            relationships.append(
                RelationshipAI(
                    primary_column=numeric_cols[0],
                    secondary_column=numeric_cols[1],
                    relationship_description=f"Covariation between '{numeric_cols[0]}' and '{numeric_cols[1]}'.",
                    analytical_type="correlation",
                    referenced_fact_ids=[fid for fid, f in computed_facts.items() if f.category == "correlation"],
                )
            )
        if categorical_cols and numeric_cols:
            relationships.append(
                RelationshipAI(
                    primary_column=categorical_cols[0],
                    secondary_column=numeric_cols[0],
                    relationship_description=f"Distribution of '{numeric_cols[0]}' partitioned by '{categorical_cols[0]}' groups.",
                    analytical_type="comparison",
                    referenced_fact_ids=[],
                )
            )

        insights = AnalyticalInsightsAI(
            key_observations=observations,
            potential_relationships=relationships,
            business_relevance=f"Informing tactical decision-making and performance optimization across {domain.lower()}.",
        )

        # Suggested Analysis (KPIs, Charts, Questions)
        suggested_kpis: List[SuggestedKPI] = []
        if target_var:
            suggested_kpis.append(
                SuggestedKPI(
                    name=f"{target_var.column_name} Metric Rate",
                    calculation=f"Aggregated rate of {target_var.column_name} over total volume",
                    purpose="Primary operational success benchmark",
                    business_value="Direct performance tracking",
                    target_column=target_var.column_name,
                )
            )
        if numeric_cols:
            suggested_kpis.append(
                SuggestedKPI(
                    name=f"Average {numeric_cols[0]}",
                    calculation=f"Mean({numeric_cols[0]})",
                    purpose="Central tendency monitoring",
                    business_value=f"Tracks standard volume per record",
                    target_column=numeric_cols[0],
                )
            )

        recommended_charts: List[RecommendedChartAI] = []
        if categorical_cols and numeric_cols:
            recommended_charts.append(
                RecommendedChartAI(
                    chart_type="bar",
                    title=f"{numeric_cols[0]} by {categorical_cols[0]}",
                    x_column=categorical_cols[0],
                    y_column=numeric_cols[0],
                    aggregation="avg",
                    reason="Compares aggregated averages across distinct categorical cohorts.",
                )
            )
        if numeric_cols:
            recommended_charts.append(
                RecommendedChartAI(
                    chart_type="histogram",
                    title=f"Distribution of {numeric_cols[0]}",
                    x_column=numeric_cols[0],
                    reason="Identifies skewness, bimodal peaks, and frequency concentration.",
                )
            )
        if len(numeric_cols) >= 2:
            recommended_charts.append(
                RecommendedChartAI(
                    chart_type="scatter",
                    title=f"{numeric_cols[0]} vs {numeric_cols[1]}",
                    x_column=numeric_cols[0],
                    y_column=numeric_cols[1],
                    reason="Explores bivariate correlation and dispersion patterns.",
                )
            )

        suggested_questions: List[str] = [
            f"What factors explain the observed variations in {numeric_cols[0] if numeric_cols else 'key metrics'}?",
            f"How do outcomes vary when segmenting records by {categorical_cols[0] if categorical_cols else 'category'}?",
            "Are there noticeable outlier records requiring individual inspection?",
            f"What is the correlation between key numerical features in this {domain.lower()} dataset?",
            "Which subset of records demonstrates the highest performance or reliability?",
            "How does data completeness impact analytical confidence across specific segments?",
        ]

        analysis = SuggestedAnalysisAI(
            suggested_kpis=suggested_kpis,
            recommended_charts=recommended_charts,
            suggested_questions=suggested_questions,
        )

        return {
            "overview": overview.model_dump(),
            "columns": [c.model_dump() for c in column_understandings],
            "analytical_insights": insights.model_dump(),
            "suggested_analysis": analysis.model_dump(),
        }
