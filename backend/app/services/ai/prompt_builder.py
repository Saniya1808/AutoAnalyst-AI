import json
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.core.json_encoder import sanitize_for_json
from app.models.ai_understanding import ComputedFact
from app.services.profiler import infer_column_type


class PromptContextBuilder:
    @classmethod
    def extract_computed_facts_and_context(
        cls, df: pd.DataFrame, filename: str, max_profiled_columns: int = 35
    ) -> Tuple[Dict[str, ComputedFact], Dict[str, Any]]:
        """
        Calculates all numerical statistics via Pandas and generates stable fact IDs (fact_1, fact_2, ...).
        Enforces privacy: NEVER includes raw data rows.
        Limits prompt context size for wide datasets (up to 200 columns).
        """
        facts: Dict[str, ComputedFact] = {}
        fact_counter = 1

        total_rows = len(df)
        total_cols = len(df.columns)
        total_cells = total_rows * total_cols
        total_missing = int(df.isna().sum().sum())
        missing_pct = round((total_missing / total_cells * 100.0), 2) if total_cells > 0 else 0.0

        try:
            duplicate_rows = int(df.duplicated().sum())
        except Exception:
            duplicate_rows = 0
        duplicate_pct = round((duplicate_rows / total_rows * 100.0), 2) if total_rows > 0 else 0.0

        # Dimension Facts
        fact_id_rows = f"fact_{fact_counter}"
        facts[fact_id_rows] = ComputedFact(
            fact_id=fact_id_rows,
            category="dimension",
            metric_name="total_rows",
            value=total_rows,
            formatted_statement=f"Dataset has {total_rows:,} total rows.",
        )
        fact_counter += 1

        fact_id_cols = f"fact_{fact_counter}"
        facts[fact_id_cols] = ComputedFact(
            fact_id=fact_id_cols,
            category="dimension",
            metric_name="total_columns",
            value=total_cols,
            formatted_statement=f"Dataset has {total_cols} total columns.",
        )
        fact_counter += 1

        fact_id_missing = f"fact_{fact_counter}"
        facts[fact_id_missing] = ComputedFact(
            fact_id=fact_id_missing,
            category="quality",
            metric_name="missing_cells",
            value=total_missing,
            formatted_statement=f"Dataset contains {total_missing:,} missing cells ({missing_pct}% of all data).",
        )
        fact_counter += 1

        fact_id_dups = f"fact_{fact_counter}"
        facts[fact_id_dups] = ComputedFact(
            fact_id=fact_id_dups,
            category="quality",
            metric_name="duplicate_rows",
            value=duplicate_rows,
            formatted_statement=f"Dataset contains {duplicate_rows:,} duplicate rows ({duplicate_pct}%).",
        )
        fact_counter += 1

        # Determine columns to profile in detail
        columns_to_profile = list(df.columns)
        if total_cols > max_profiled_columns:
            # Score column relevance
            def col_priority(col: str) -> float:
                series = df[col]
                nunique = series.nunique(dropna=True)
                null_cnt = series.isna().sum()
                score = 0.0
                if infer_column_type(series) in ("integer", "float"):
                    score += 10.0
                elif 2 <= nunique <= 50:
                    score += 8.0
                if null_cnt > 0:
                    score += 3.0
                return score

            sorted_cols = sorted(columns_to_profile, key=col_priority, reverse=True)
            columns_to_profile = sorted_cols[:max_profiled_columns]

        column_context_list = []

        for col in columns_to_profile:
            series = df[col]
            sem_type = infer_column_type(series)
            null_count = int(series.isna().sum())
            null_pct = round((null_count / total_rows * 100.0), 2) if total_rows > 0 else 0.0
            unique_count = int(series.nunique(dropna=True))

            col_fact_id = f"fact_{fact_counter}"
            facts[col_fact_id] = ComputedFact(
                fact_id=col_fact_id,
                category="column_metadata",
                column_name=col,
                metric_name="type_and_cardinality",
                value={"type": sem_type, "unique_count": unique_count, "null_count": null_count},
                formatted_statement=f"Column '{col}' is {sem_type} with {unique_count:,} unique values and {null_count} nulls ({null_pct}%).",
            )
            fact_counter += 1

            col_summary: Dict[str, Any] = {
                "fact_id": col_fact_id,
                "name": col,
                "type": sem_type,
                "unique_count": unique_count,
                "null_count": null_count,
                "null_pct": null_pct,
            }

            if sem_type in ("integer", "float"):
                num_series = pd.to_numeric(series, errors="coerce").dropna()
                if len(num_series) > 0:
                    min_v = round(float(num_series.min()), 2)
                    mean_v = round(float(num_series.mean()), 2)
                    median_v = round(float(num_series.median()), 2)
                    max_v = round(float(num_series.max()), 2)

                    num_fact_id = f"fact_{fact_counter}"
                    facts[num_fact_id] = ComputedFact(
                        fact_id=num_fact_id,
                        category="numeric_statistic",
                        column_name=col,
                        metric_name="five_number_summary",
                        value={"min": min_v, "mean": mean_v, "median": median_v, "max": max_v},
                        formatted_statement=f"Column '{col}' statistics: min={min_v}, mean={mean_v}, median={median_v}, max={max_v}.",
                    )
                    fact_counter += 1

                    col_summary["statistics"] = {
                        "fact_id": num_fact_id,
                        "min": min_v,
                        "mean": mean_v,
                        "median": median_v,
                        "max": max_v,
                    }

            elif sem_type in ("string", "boolean"):
                top_counts = series.astype(str).value_counts(dropna=True).head(3)
                top_items = [
                    {"category": k, "count": int(v), "pct": round(int(v) / total_rows * 100.0, 1)}
                    for k, v in top_counts.items()
                ]

                cat_summary_str = ", ".join(f"{it['category']} ({it['pct']}%)" for it in top_items)
                cat_fact_id = f"fact_{fact_counter}"
                facts[cat_fact_id] = ComputedFact(
                    fact_id=cat_fact_id,
                    category="categorical_distribution",
                    column_name=col,
                    metric_name="top_categories",
                    value=top_items,
                    formatted_statement=f"Column '{col}' top values: {cat_summary_str}.",
                )
                fact_counter += 1

                col_summary["top_categories"] = {
                    "fact_id": cat_fact_id,
                    "values": top_items,
                }

            column_context_list.append(col_summary)

        # Look for a potential high-level correlation between 2 numeric columns
        numeric_cols = [c for c in columns_to_profile if infer_column_type(df[c]) in ("integer", "float")]
        if len(numeric_cols) >= 2:
            try:
                corr_val = float(df[numeric_cols[0]].corr(df[numeric_cols[1]]))
                if not pd.isna(corr_val):
                    corr_fact_id = f"fact_{fact_counter}"
                    facts[corr_fact_id] = ComputedFact(
                        fact_id=corr_fact_id,
                        category="correlation",
                        column_name=f"{numeric_cols[0]}_vs_{numeric_cols[1]}",
                        metric_name="pearson_correlation",
                        value=round(corr_val, 3),
                        formatted_statement=f"Pearson correlation between '{numeric_cols[0]}' and '{numeric_cols[1]}' is {corr_val:.3f}.",
                    )
                    fact_counter += 1
            except Exception:
                pass

        distilled_context = {
            "filename": filename,
            "dimensions": {
                "total_rows": total_rows,
                "total_columns": total_cols,
                "total_missing_cells": total_missing,
                "duplicate_rows": duplicate_rows,
                "referenced_fact_ids": [fact_id_rows, fact_id_cols, fact_id_missing, fact_id_dups],
            },
            "columns": column_context_list,
            "profiled_columns_count": len(column_context_list),
            "total_columns_count": total_cols,
        }

        return facts, sanitize_for_json(distilled_context)

    @classmethod
    def build_prompt_and_system_instruction(
        cls, distilled_context: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Builds the structured prompt and system instruction.
        Mandates output schema and fact ID referencing.
        """
        system_instruction = (
            "You are the senior autonomous data analyst for AutoAnalyst AI (Powered by Saniya). "
            "Your objective is to provide an intelligent, accurate, and deeply insightful explanation of the dataset. "
            "CRITICAL RULES FOR STATISTICAL INTEGRITY:\n"
            "1. Ground all numbers and empirical observations strictly in the provided computed facts and fact IDs.\n"
            "2. Never fabricate numbers, row counts, percentages, or non-existent columns.\n"
            "3. Every observation must cite the corresponding 'fact_id' from the context in 'referenced_fact_ids'.\n"
            "4. Clearly distinguish observed facts ('observation_type': 'observed_fact') from domain hypotheses ('observation_type': 'hypothesis').\n"
            "5. Return strictly valid JSON conforming exactly to the requested output structure.\n"
            "6. Explain technical insights in accessible, professional language."
        )

        prompt = f"""Analyze the following dataset context and produce a structured JSON explanation.

DATASET CONTEXT (COMPUTED FACTS):
{json.dumps(distilled_context, indent=2)}

OUTPUT SCHEMA REQUIRED (JSON ONLY):
{{
  "overview": {{
    "domain": "<Inferred industry or subject domain, e.g. Maritime Passenger Logistics, E-commerce Retail, Healthcare>",
    "likely_purpose": "<What this dataset was likely collected for>",
    "executive_summary": "<Comprehensive 2-4 sentence executive overview>",
    "detected_target_variable": {{
      "column_name": "<Column likely to be predicted or analyzed as primary outcome, or 'None'>",
      "confidence": "high|medium|low",
      "reasoning": "<Why this column is the likely objective target>",
      "referenced_fact_ids": ["<fact_id>"]
    }},
    "referenced_fact_ids": ["<fact_ids>"]
  }},
  "columns": [
    {{
      "name": "<column_name>",
      "semantic_type": "<type>",
      "business_meaning": "<Clear plain-language business meaning of this column>",
      "is_key_feature": true|false,
      "is_identifier": true|false,
      "data_quality_note": "<Quality note or null>",
      "referenced_fact_ids": ["<fact_ids>"]
    }}
  ],
  "analytical_insights": {{
    "key_observations": [
      {{
        "observation_type": "observed_fact|interpretation|hypothesis",
        "statement": "<Concise observation statement>",
        "business_implication": "<Why this matters to decision makers>",
        "referenced_fact_ids": ["<fact_ids>"],
        "is_verified_fact": true|false
      }}
    ],
    "potential_relationships": [
      {{
        "primary_column": "<column A>",
        "secondary_column": "<column B>",
        "relationship_description": "<How they relate or contrast>",
        "analytical_type": "correlation|segmentation|temporal_trend|comparison",
        "referenced_fact_ids": ["<fact_ids>"]
      }}
    ],
    "business_relevance": "<Broader operational or strategic relevance of analyzing this data>"
  }},
  "suggested_analysis": {{
    "suggested_kpis": [
      {{
        "name": "<Metric name>",
        "calculation": "<Math formula or formula description>",
        "purpose": "<Analytical goal>",
        "business_value": "<Strategic utility>",
        "target_column": "<column name or null>"
      }}
    ],
    "recommended_charts": [
      {{
        "chart_type": "bar|line|scatter|box|histogram|pie",
        "title": "<Chart Title>",
        "x_column": "<col>",
        "y_column": "<col or null>",
        "aggregation": "avg|sum|count|null",
        "reason": "<Why this chart is valuable>"
      }}
    ],
    "suggested_questions": [
      "<5 to 10 insightful business/exploratory questions for future Q&A>"
    ]
  }}
}}"""

        return prompt, system_instruction
