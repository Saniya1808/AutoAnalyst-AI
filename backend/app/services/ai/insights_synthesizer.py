import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from app.core.config import settings
from app.core.json_encoder import sanitize_for_json
from app.models.automated_insights import AutomatedInsightsResponse
from app.services.ai.automated_insights_engine import AutomatedInsightsEngine
from app.services.ai.gemini_provider import GeminiProvider
from app.services.dataset_storage import dataset_storage


class InsightsSynthesizer:
    """
    Coordinates Automated Insights generation, atomic disk caching,
    and Gemini LLM narrative synthesis with deterministic offline fallback.
    """

    SCHEMA_VERSION = "v2"

    @classmethod
    def _get_cache_path(
        cls,
        dataset_id: str,
        snapshot_hash: str,
        date_col: Optional[str] = None,
        metric_col: Optional[str] = None,
        granularity: Optional[str] = None,
    ) -> Path:
        """Constructs an immutable snapshot-aware cache path."""
        clean_model = settings.AI_MODEL_NAME.replace("/", "_").replace(":", "_")
        short_hash = snapshot_hash[:12]
        param_suffix = f"_{date_col}_{metric_col}_{granularity}" if (date_col and metric_col) else ""
        filename = f"cache_insights_{dataset_id}_{short_hash}{param_suffix}_{clean_model}_{cls.SCHEMA_VERSION}.json"
        return dataset_storage.upload_dir / filename

    @classmethod
    def _atomic_write_cache(cls, cache_path: Path, data: Dict[str, Any]) -> None:
        """Atomically writes cache JSON to prevent corrupted reads."""
        temp_path = cache_path.with_name(f"tmp_{cache_path.name}")
        sanitized = sanitize_for_json(data)
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(sanitized, f, indent=2)
            shutil.move(str(temp_path), str(cache_path))
        except Exception:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    @classmethod
    async def get_or_generate_insights(
        cls,
        dataset_id: str,
        force_refresh: bool = False,
        date_col: Optional[str] = None,
        metric_col: Optional[str] = None,
        granularity: Optional[str] = None,
    ) -> AutomatedInsightsResponse:
        """
        Retrieves cached automated insights or computes fresh analytics
        using Pandas and Gemini (with deterministic heuristic fallback).
        """
        clean_id = f"clean_{dataset_id}"
        active_id = clean_id if dataset_storage.get_dataset(clean_id) else dataset_id
        detail = dataset_storage.get_dataset(active_id)
        if not detail:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        file_path = dataset_storage.get_dataset_file_path(active_id)
        snapshot_hash = dataset_storage.compute_sha256(file_path)
        cache_path = cls._get_cache_path(dataset_id, snapshot_hash, date_col, metric_col, granularity)

        # 1. Check cache if not forcing refresh
        if not force_refresh and cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                cached_resp = AutomatedInsightsResponse.model_validate(cached_data)
                cached_resp.is_cached = True
                return cached_resp
            except Exception:
                # If cache read fails, proceed to regenerate
                pass

        # 2. Load DataFrame
        df = dataset_storage._load_dataframe(active_id)

        # 3. Compute baseline analytics via AutomatedInsightsEngine
        insights_res = AutomatedInsightsEngine.analyze_dataset(
            df=df,
            dataset_id=dataset_id,
            dataset_name=detail.overview.filename,
            snapshot_hash=snapshot_hash,
            col_profiles=detail.columns,
            date_col=date_col,
            metric_col=metric_col,
            granularity=granularity,
        )

        # 4. Synthesize with Gemini if API key configured
        api_key = settings.effective_gemini_api_key
        if api_key:
            provider = GeminiProvider(api_key=api_key, model_name=settings.AI_MODEL_NAME)
            facts_payload = [f.model_dump() for f in insights_res.grounded_facts]
            findings_summary = [f.model_dump() for f in insights_res.key_findings]
            bw_summary = [bw.model_dump() for bw in insights_res.best_worst_analyses]
            anomaly_summary = [a.model_dump() for a in insights_res.anomalies_and_patterns]
            trends_summary = [t.model_dump(exclude={"chart"}) for t in insights_res.trends]

            system_instruction = (
                "You are the executive business intelligence director for AutoAnalyst AI (Powered by Saniya). "
                "Your objective is to review pre-calculated statistical findings, temporal trends, best/worst performance benchmarks, "
                "and anomalies, and synthesize an executive briefing. "
                "CRITICAL INTEGRITY RULES:\n"
                "1. Ground all numbers strictly in the provided facts and calculations. Never invent or recalculate statistics.\n"
                "2. Clearly separate verified empirical facts from analytical hypotheses.\n"
                "3. Explain why the detected trends and performance disparities matter for business decision-making.\n"
                "4. Output strictly JSON matching the required schema."
            )

            prompt = f"""Synthesize an executive intelligence briefing based on the following verified facts and analytics.

DATASET: {detail.overview.filename} (Rows: {len(df):,}, Columns: {len(df.columns)})

KEY FINDINGS:
{json.dumps(findings_summary, indent=2)}

TEMPORAL TRENDS:
{json.dumps(trends_summary, indent=2)}

BEST & WORST CATEGORY BENCHMARKS:
{json.dumps(bw_summary, indent=2)}

ANOMALIES & UNUSUAL PATTERNS:
{json.dumps(anomaly_summary, indent=2)}

SUPPORTING FACT EVIDENCE:
{json.dumps(facts_payload[:15], indent=2)}

OUTPUT JSON SCHEMA:
{{
  "executive_summary": "<Professional 2-3 paragraph executive briefing highlighting the dataset health, the primary performance disparity or temporal trend, and key data risks>",
  "best_performer_context": "<Strategic context explaining why the top performing category or peak period achieved this result>",
  "worst_performer_context": "<Tactical context explaining the challenges or bottlenecks faced by the lowest category or period>"
}}
"""

            try:
                ai_dict = await provider.generate_json(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    timeout_seconds=settings.AI_TIMEOUT_SECONDS,
                )
                if ai_dict.get("executive_summary"):
                    insights_res.executive_summary = ai_dict["executive_summary"].strip()
                    insights_res.mode = "ai_generated"
                    insights_res.provider = "gemini"
                    insights_res.model = settings.AI_MODEL_NAME

                if ai_dict.get("best_performer_context") and insights_res.best_worst_analyses:
                    insights_res.best_worst_analyses[0].explanation += f" Strategic Insight: {ai_dict['best_performer_context'].strip()}"
            except Exception:
                # Fallback to deterministic heuristic narrative if Gemini fails
                pass

        # 5. Persist to atomic cache
        cls._atomic_write_cache(cache_path, insights_res.model_dump())

        return insights_res

