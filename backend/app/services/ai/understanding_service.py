import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.core.config import settings
from app.core.json_encoder import sanitize_for_json
from app.models.ai_understanding import (
    AnalyticalInsightsAI,
    ColumnUnderstandingAI,
    ComputedFact,
    DatasetOverviewAI,
    DatasetUnderstandingResponse,
    ObservationAI,
    RecommendedChartAI,
    RelationshipAI,
    SuggestedAnalysisAI,
    SuggestedKPI,
    TargetVariableDetection,
)
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.heuristic_fallback import HeuristicFallbackEngine
from app.services.ai.prompt_builder import PromptContextBuilder
from app.services.dataset_storage import dataset_storage


class DatasetUnderstandingService:
    @staticmethod
    def _compute_snapshot_hash(file_path: Path) -> str:
        """Compute SHA-256 hash of current dataset snapshot."""
        if not file_path.exists():
            return "unknown_hash"
        return dataset_storage.compute_sha256(file_path)

    @classmethod
    def _get_cache_path(
        cls, dataset_id: str, snapshot_hash: str, model_name: str, schema_ver: str
    ) -> Path:
        """
        Cache identity combines dataset ID, snapshot hash, model, and schema version.
        Guarantees that cleaning, undo, and reset never return stale cache.
        """
        short_hash = snapshot_hash[:12]
        clean_model = model_name.replace("/", "_").replace(":", "_")
        cache_filename = f"cache_ai_{dataset_id}_{short_hash}_{clean_model}_{schema_ver}.json"
        return dataset_storage.upload_dir / cache_filename

    @classmethod
    def _atomic_write_cache(cls, cache_path: Path, data: Dict[str, Any]) -> None:
        """Atomically persist cache JSON to prevent corrupted partial reads."""
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
    def _validate_referenced_facts(
        cls,
        parsed_data: Dict[str, Any],
        computed_facts: Dict[str, ComputedFact],
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Verifies every cited fact ID against backend-computed facts.
        Separates observed facts from unsupported claims.
        """
        warnings: List[str] = []
        valid_fact_ids = set(computed_facts.keys())

        # Validate overview
        overview_refs = parsed_data.get("overview", {}).get("referenced_fact_ids", [])
        for fid in overview_refs:
            if fid not in valid_fact_ids:
                warnings.append(f"Overview cited unverified fact '{fid}'.")

        # Validate target variable
        target_var = parsed_data.get("overview", {}).get("detected_target_variable")
        if target_var and isinstance(target_var, dict):
            for fid in target_var.get("referenced_fact_ids", []):
                if fid not in valid_fact_ids:
                    warnings.append(f"Target variable cited unverified fact '{fid}'.")

        # Validate columns
        for col_item in parsed_data.get("columns", []):
            if isinstance(col_item, dict):
                col_name = col_item.get("name")
                col_refs = col_item.get("referenced_fact_ids", [])
                for fid in col_refs:
                    if fid not in valid_fact_ids:
                        warnings.append(f"Column '{col_name}' cited unverified fact '{fid}'.")

        # Validate observations (empirical fact check)
        obs_list = parsed_data.get("analytical_insights", {}).get("key_observations", [])
        for obs in obs_list:
            if isinstance(obs, dict):
                obs_type = obs.get("observation_type", "hypothesis")
                refs = obs.get("referenced_fact_ids", [])
                has_valid_ref = any(fid in valid_fact_ids for fid in refs)

                if obs_type == "observed_fact" and has_valid_ref:
                    obs["is_verified_fact"] = True
                elif obs_type == "observed_fact" and not has_valid_ref:
                    # Downgrade unverified fact to hypothesis
                    obs["is_verified_fact"] = False
                    obs["observation_type"] = "hypothesis"
                    warnings.append(f"Downgraded observation without verified fact reference to hypothesis: '{obs.get('statement')}'.")
                else:
                    obs["is_verified_fact"] = False

        return parsed_data, warnings

    @classmethod
    async def get_or_generate_understanding(
        cls, dataset_id: str, force_refresh: bool = False
    ) -> DatasetUnderstandingResponse:
        """
        Main entry point for AI Dataset Understanding.
        Loads dataset, verifies cache identity, queries Gemini or executes heuristic fallback,
        validates fact references, and returns response.
        """
        # Determine whether this is an original or cleaned dataset
        target_detail = dataset_storage.get_dataset(dataset_id)
        if not target_detail:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        df = dataset_storage._load_dataframe(dataset_id)
        if df.empty:
            raise ValueError(f"Dataset '{dataset_id}' contains no data rows.")

        file_path = dataset_storage.get_dataset_file_path(dataset_id)
        snapshot_hash = cls._compute_snapshot_hash(file_path)
        model_name = settings.AI_MODEL_NAME
        schema_ver = settings.PROMPT_SCHEMA_VERSION

        cache_path = cls._get_cache_path(dataset_id, snapshot_hash, model_name, schema_ver)

        # Check Cache
        if not force_refresh and settings.AI_CACHE_ENABLED and cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                cached_data["is_cached"] = True
                return DatasetUnderstandingResponse(**cached_data)
            except Exception:
                # Corrupt cache, proceed to fresh generation
                pass

        # Extract verified facts and build prompt context
        computed_facts, distilled_context = PromptContextBuilder.extract_computed_facts_and_context(
            df=df, filename=target_detail.overview.filename
        )

        api_key = settings.effective_gemini_api_key
        mode = "ai_generated" if api_key else "statistical_fallback"
        provider_name = "gemini" if api_key else "heuristic"
        active_model = model_name if api_key else "statistical_engine"
        error_detail = None
        can_retry = False
        parsed_result = None

        if api_key:
            prompt, system_instruction = PromptContextBuilder.build_prompt_and_system_instruction(distilled_context)
            gemini = GeminiProvider(api_key=api_key, model_name=model_name)

            try:
                parsed_result = await gemini.generate_understanding(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    timeout_seconds=settings.AI_TIMEOUT_SECONDS,
                )
            except Exception as e:
                # Fallback to heuristic on failure, record error detail for user notification
                error_detail = f"AI Provider Notice: {str(e)}"
                can_retry = True
                mode = "statistical_fallback"
                provider_name = "heuristic_fallback"
                active_model = "statistical_engine"

        # If fallback needed or active
        if not parsed_result:
            parsed_result = HeuristicFallbackEngine.generate_heuristic_understanding(
                df=df,
                filename=target_detail.overview.filename,
                computed_facts=computed_facts,
                distilled_context=distilled_context,
                error_context=error_detail,
            )

        # Validate referenced facts
        sanitized_result, validation_warnings = cls._validate_referenced_facts(
            parsed_data=parsed_result, computed_facts=computed_facts
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        response = DatasetUnderstandingResponse(
            dataset_id=dataset_id,
            filename=target_detail.overview.filename,
            is_cleaned=target_detail.overview.is_cleaned,
            version=target_detail.overview.version,
            snapshot_hash=snapshot_hash,
            mode=mode,
            provider=provider_name,
            model=active_model,
            generated_at=now_iso,
            is_cached=False,
            computed_facts=computed_facts,
            overview=DatasetOverviewAI(**sanitized_result.get("overview", {})),
            columns=[ColumnUnderstandingAI(**c) for c in sanitized_result.get("columns", [])],
            analytical_insights=AnalyticalInsightsAI(**sanitized_result.get("analytical_insights", {})),
            suggested_analysis=SuggestedAnalysisAI(**sanitized_result.get("suggested_analysis", {})),
            validation_warnings=validation_warnings,
            error_detail=error_detail,
            can_retry=can_retry,
        )

        # Cache valid response atomically if caching is enabled
        if settings.AI_CACHE_ENABLED and not error_detail:
            cls._atomic_write_cache(cache_path, response.model_dump())

        return response
