import json
from typing import Any, Dict, List, Optional, Tuple

from app.models.ask_data import AnalyticalCalculationResult, QueryPlan
from app.services.ai.base_provider import BaseLLMProvider


class HeuristicAnswerGenerator:
    """
    Deterministic answer generator when offline or unkeyed.
    Synthesizes professional responses directly from calculated Pandas results.
    """

    @classmethod
    def generate(
        cls,
        question: str,
        plan: QueryPlan,
        calc_result: AnalyticalCalculationResult,
    ) -> Tuple[str, List[str]]:
        """
        Returns: (direct_answer, suggested_follow_ups)
        """
        if plan.is_ambiguous:
            msg = plan.clarification_reason or "Your question could refer to multiple columns or calculations."
            return (
                f"I need a bit more detail to answer accurately: {msg}",
                plan.suggested_clarifications or ["What is the average of a specific column?", "Show summary statistics.", "Give me an overview of this data."],
            )

        if not calc_result.success:
            return (
                calc_result.direct_summary or "Unable to compute the requested analysis from the dataset.",
                ["Give me an overview of this data", "Which columns have missing values?"],
            )

        # Build clean direct answer from calculated result
        direct_answer = calc_result.direct_summary

        # Add notes about limitations if present
        if calc_result.limitations_and_warnings:
            # Only append if not redundant
            non_redundant = [lim for lim in calc_result.limitations_and_warnings if lim not in direct_answer]
            if non_redundant and len(non_redundant) <= 2:
                direct_answer += f" ({'; '.join(non_redundant)})"

        # Generate intelligent follow-up questions tailored to intent
        follow_ups = []
        cols = calc_result.columns_used
        col_name = cols[0] if cols else "records"

        if plan.intent == "automated_insights":
            follow_ups.append("Which categories perform best and worst?")
            follow_ups.append("Are there any unusual patterns or outliers?")
            follow_ups.append("What actions would you recommend based on the data?")
        elif plan.intent == "best_worst_performers":
            follow_ups.append("Are there unusual patterns in this data?")
            follow_ups.append("What actions would you recommend based on the data?")
            follow_ups.append("What are the most important findings?")
        elif plan.intent == "anomaly_detection":
            follow_ups.append("What actions would you recommend based on the data?")
            follow_ups.append("Which categories perform best and worst?")
            follow_ups.append("What are the most important findings?")
        elif plan.intent == "business_recommendations":
            follow_ups.append("Which categories perform best and worst?")
            follow_ups.append("What are the most important findings?")
            follow_ups.append("Are there unusual patterns?")
        elif plan.intent == "data_quality_insights":
            follow_ups.append("What are the most important findings?")
            follow_ups.append("Which categories perform best and worst?")
            follow_ups.append("What actions would you recommend?")
        elif plan.intent == "trend_analysis":
            follow_ups.append("Which period performed best and worst?")
            follow_ups.append("Are there any sudden drops in performance?")
            follow_ups.append("Are there recurring seasonal patterns?")
        elif plan.intent == "period_benchmark":
            follow_ups.append("Is this metric increasing or decreasing over time?")
            follow_ups.append("Are there any sudden drops or spikes?")
            follow_ups.append("What actions would you recommend based on the data?")
        elif plan.intent == "temporal_anomaly":
            follow_ups.append("Which period performed best and worst?")
            follow_ups.append("Is this metric increasing or decreasing over time?")
            follow_ups.append("What actions would you recommend?")
        elif plan.intent == "seasonality_analysis":
            follow_ups.append("Is performance increasing or decreasing over time?")
            follow_ups.append("Which period performed best and worst?")
            follow_ups.append("Are there unusual patterns or sudden drops?")
        elif plan.intent == "text_search":
            follow_ups.append(f"List all unique {col_name} values?")
            follow_ups.append(f"Which {col_name} appears most frequently?")
            follow_ups.append("Give me an overview of this data.")
        elif plan.intent == "distinct_values":
            follow_ups.append(f"Which {col_name} appears most frequently?")
            follow_ups.append(f"Show distribution of {col_name}.")
            follow_ups.append("How many total records are in this dataset?")
        elif plan.intent == "dataset_summary":
            follow_ups.append("Which columns have missing values?")
            if cols:
                follow_ups.append(f"List all unique {cols[0]} values.")
                if len(cols) >= 2:
                    follow_ups.append(f"Show breakdown of {cols[1]} by {cols[0]}.")
        elif len(cols) == 1:
            follow_ups.append(f"Compare {cols[0]} across different categories?")
            follow_ups.append(f"What are the highest and lowest values of {cols[0]}?")
            follow_ups.append(f"Show distribution of {cols[0]}.")
        elif len(cols) >= 2:
            follow_ups.append(f"Are there any outliers in {cols[0]}?")
            follow_ups.append(f"How does this distribution change across {cols[1]}?")
            follow_ups.append("Which category has the highest count?")
        else:
            follow_ups.append("Which category has the highest count?")
            follow_ups.append("Show missing values summary.")

        return direct_answer, follow_ups[:3]


class AnswerGenerator:
    """
    Synthesizes natural-language business answers from Pandas analytical results.
    Uses Gemini for contextual explanation when available, with strict factual grounding.
    """

    @classmethod
    async def generate_answer(
        cls,
        question: str,
        plan: QueryPlan,
        calc_result: AnalyticalCalculationResult,
        provider: Optional[BaseLLMProvider] = None,
        timeout_seconds: int = 25,
    ) -> Tuple[str, List[str], str]:
        """
        Generates grounded explanation and follow-up prompts.
        Returns: (direct_answer, suggested_follow_ups, mode: 'ai_generated' | 'statistical_fallback')
        """
        if plan.is_ambiguous:
            ans, follow_ups = HeuristicAnswerGenerator.generate(question, plan, calc_result)
            return ans, follow_ups, "statistical_fallback"

        if not provider or not getattr(provider, "_api_key", None):
            ans, follow_ups = HeuristicAnswerGenerator.generate(question, plan, calc_result)
            return ans, follow_ups, "statistical_fallback"

        facts_payload = [f.model_dump() for f in calc_result.grounded_facts]
        metric_payload = calc_result.primary_metric.model_dump() if calc_result.primary_metric else None

        system_instruction = (
            "You are the executive data analyst for AutoAnalyst AI (Powered by Saniya). "
            "Your objective is to provide a clear, professional, direct answer to the user's question "
            "based strictly on the Pandas-calculated analytical results provided. "
            "CRITICAL INTEGRITY RULES:\n"
            "1. Ground all numbers strictly in the provided primary_metric and grounded_facts.\n"
            "2. Never alter, fabricate, or recalculate numbers; use the exact figures provided.\n"
            "3. For text queries (such as listing names or searching for prefixes), clearly state the matching entities and the total match count.\n"
            "4. For general dataset overview queries, explain the dataset contents, structure, and available columns based strictly on the provided summary.\n"
            "5. For broad analytical queries (automated insights, best/worst performers, anomaly detection, recommendations, data quality), clearly communicate executive conclusions, high-level benchmarks, and strategic actions based strictly on the provided summary and facts.\n"
            "6. State any exclusions or caveats mentioned in limitations_and_warnings.\n"
            "7. Provide 2-3 insightful follow-up questions the user might ask next.\n"
            "8. Return strictly JSON matching the required schema."
        )

        prompt = f"""Synthesize an executive data analyst response for the following question and computed results.

USER QUESTION:
"{question}"

COMPUTED ANALYTICAL RESULT:
- Direct Summary: {calc_result.direct_summary}
- Primary Metric: {json.dumps(metric_payload)}
- Calculation Method: {calc_result.calculation_method}
- Columns Used: {calc_result.columns_used}
- Limitations / Caveats: {calc_result.limitations_and_warnings}
- Grounded Facts: {json.dumps(facts_payload)}

OUTPUT JSON SCHEMA:
{{
  "direct_answer": "<Concise 1-3 sentence professional executive answer stating the exact calculated figures and entity names>",
  "suggested_follow_ups": ["<follow up question 1>", "<follow up question 2>"]
}}
"""

        try:
            res_dict = await provider.generate_json(
                prompt=prompt,
                system_instruction=system_instruction,
                timeout_seconds=timeout_seconds,
            )

            direct_ans = res_dict.get("direct_answer", "").strip()
            follow_ups = res_dict.get("suggested_follow_ups", [])

            if not direct_ans:
                direct_ans, follow_ups = HeuristicAnswerGenerator.generate(question, plan, calc_result)
                return direct_ans, follow_ups, "statistical_fallback"

            return direct_ans, follow_ups[:3], "ai_generated"

        except Exception:
            direct_ans, follow_ups = HeuristicAnswerGenerator.generate(question, plan, calc_result)
            return direct_ans, follow_ups, "statistical_fallback"
