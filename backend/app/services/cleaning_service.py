import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.json_encoder import sanitize_for_json
from app.models.cleaning import (
    CleaningApplyRequest,
    CleaningApplyResponse,
    CleaningPreviewRequest,
    CleaningPreviewResponse,
    ColumnQualitySummary,
    DataQualityMetric,
    DataQualityProfile,
    IQRBoundaries,
    ResetResponse,
    TransformationHistoryResponse,
    TransformationStep,
    UndoResponse,
    ZScoreBoundaries,
)
from app.services.dataset_storage import dataset_storage
from app.services.profiler import infer_column_type


class CleaningService:
    @staticmethod
    def _get_snapshots_dir(dataset_id: str) -> Path:
        """Directory for intermediate undo version snapshots."""
        snap_dir = dataset_storage.upload_dir / f"snapshots_{dataset_id}"
        snap_dir.mkdir(parents=True, exist_ok=True)
        return snap_dir

    @staticmethod
    def _get_history_file(dataset_id: str) -> Path:
        """JSON file for transformation history."""
        return dataset_storage.upload_dir / f"{dataset_id}_history.json"

    @classmethod
    def get_history(cls, dataset_id: str) -> List[TransformationStep]:
        """Read transformation history from disk."""
        hist_path = cls._get_history_file(dataset_id)
        if not hist_path.exists():
            return []
        try:
            with open(hist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [TransformationStep(**item) for item in data]
        except Exception:
            return []

    @classmethod
    def _save_history(cls, dataset_id: str, history: List[TransformationStep]) -> None:
        """Persist transformation history to disk."""
        hist_path = cls._get_history_file(dataset_id)
        sanitized = [sanitize_for_json(step.model_dump()) for step in history]
        with open(hist_path, "w", encoding="utf-8") as f:
            json.dump(sanitized, f, indent=2)

    @classmethod
    def _save_snapshot(cls, dataset_id: str, version: int, df: pd.DataFrame) -> None:
        """Persist a version snapshot for undo."""
        snap_dir = cls._get_snapshots_dir(dataset_id)
        snap_file = snap_dir / f"v{version}.csv"
        df.to_csv(snap_file, index=False, encoding="utf-8")

    @classmethod
    def _load_snapshot(cls, dataset_id: str, version: int) -> Optional[pd.DataFrame]:
        """Load a specific version snapshot."""
        snap_dir = cls._get_snapshots_dir(dataset_id)
        snap_file = snap_dir / f"v{version}.csv"
        if not snap_file.exists():
            return None
        return pd.read_csv(snap_file, encoding="utf-8")

    @classmethod
    def _remove_snapshot(cls, dataset_id: str, version: int) -> None:
        """Delete a snapshot file when popped from stack."""
        snap_dir = cls._get_snapshots_dir(dataset_id)
        snap_file = snap_dir / f"v{version}.csv"
        if snap_file.exists():
            try:
                snap_file.unlink()
            except Exception:
                pass

    @classmethod
    def _clean_snapshots_dir(cls, dataset_id: str) -> None:
        """Remove entire snapshots directory on reset."""
        snap_dir = dataset_storage.upload_dir / f"snapshots_{dataset_id}"
        if snap_dir.exists():
            try:
                shutil.rmtree(str(snap_dir))
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Core Quality Analysis
    # -------------------------------------------------------------------------
    @classmethod
    def calculate_quality_profile(
        cls,
        df: pd.DataFrame,
        dataset_id: str,
        filename: str,
        is_cleaned: bool = False,
        version: int = 0,
        parent_id: Optional[str] = None,
        original_file_hash: Optional[str] = None,
    ) -> DataQualityProfile:
        """
        Calculate comprehensive data quality metrics, column summaries, and outlier bounds.
        """
        total_rows = len(df)
        total_columns = len(df.columns)
        total_cells = total_rows * total_columns
        total_missing = int(df.isna().sum().sum())
        missing_pct = round((total_missing / total_cells * 100.0), 2) if total_cells > 0 else 0.0

        try:
            duplicate_rows = int(df.duplicated().sum())
        except Exception:
            duplicate_rows = 0
        duplicate_pct = round((duplicate_rows / total_rows * 100.0), 2) if total_rows > 0 else 0.0

        # Completeness score: ratio of non-missing cells
        completeness_score = round(100.0 - missing_pct, 2)

        # Uniqueness score: ratio of non-duplicate rows
        uniqueness_score = round(100.0 - duplicate_pct, 2)

        # Validity score: proportion of column values matching inferred types
        invalid_cells = 0
        for col in df.columns:
            series = df[col]
            semantic_type = infer_column_type(series)
            if semantic_type in ("integer", "float"):
                # Non-null values that fail numeric coercion or are infinite
                non_null = series.dropna()
                coerced = pd.to_numeric(non_null, errors="coerce")
                invalid_cells += int(coerced.isna().sum())
                # Infinite values count as invalid
                invalid_cells += int(np.isinf(coerced.dropna()).sum())
            elif semantic_type == "datetime":
                non_null = series.dropna()
                parsed = pd.to_datetime(non_null, errors="coerce")
                invalid_cells += int(parsed.isna().sum())

        validity_score = (
            round((1.0 - (invalid_cells / total_cells)) * 100.0, 2)
            if total_cells > 0
            else 100.0
        )
        validity_score = max(0.0, min(100.0, validity_score))

        # Overall composite score: 0.50*Comp + 0.30*Valid + 0.20*Uniq
        overall_score = round(
            (0.50 * completeness_score) + (0.30 * validity_score) + (0.20 * uniqueness_score),
            2,
        )

        if overall_score >= 90:
            quality_grade = "Excellent"
        elif overall_score >= 75:
            quality_grade = "Good"
        elif overall_score >= 50:
            quality_grade = "Fair"
        else:
            quality_grade = "Needs Attention"

        quality_metric = DataQualityMetric(
            completeness_score=completeness_score,
            uniqueness_score=uniqueness_score,
            validity_score=validity_score,
            overall_quality_score=overall_score,
            quality_grade=quality_grade,
        )

        # Column summaries & outlier profiling
        columns_summary: List[ColumnQualitySummary] = []
        outlier_details: Dict[str, Dict[str, Any]] = {}

        for idx, col in enumerate(df.columns):
            series = df[col]
            semantic_type = infer_column_type(series)
            col_missing = int(series.isna().sum())
            col_missing_pct = (
                round((col_missing / total_rows * 100.0), 2) if total_rows > 0 else 0.0
            )
            col_unique = int(series.nunique(dropna=True))
            is_num = semantic_type in ("integer", "float")

            iqr_count = None
            z_count = None

            if is_num:
                num_series = pd.to_numeric(series, errors="coerce").dropna()
                if len(num_series) >= 4:
                    # IQR method
                    q1 = float(num_series.quantile(0.25))
                    q3 = float(num_series.quantile(0.75))
                    iqr = float(q3 - q1)
                    lower_iqr = round(q1 - 1.5 * iqr, 3)
                    upper_iqr = round(q3 + 1.5 * iqr, 3)
                    iqr_mask = (num_series < lower_iqr) | (num_series > upper_iqr)
                    iqr_count = int(iqr_mask.sum())
                    iqr_pct = round(iqr_count / len(num_series) * 100.0, 2)

                    # Z-Score method
                    mean_val = float(num_series.mean())
                    std_val = float(num_series.std(ddof=1)) if len(num_series) > 1 else 0.0
                    threshold = 3.0
                    if std_val > 0:
                        z_scores = np.abs((num_series - mean_val) / std_val)
                        z_mask = z_scores > threshold
                        z_count = int(z_mask.sum())
                        z_pct = round(z_count / len(num_series) * 100.0, 2)
                        lower_z = round(mean_val - threshold * std_val, 3)
                        upper_z = round(mean_val + threshold * std_val, 3)
                    else:
                        z_count = 0
                        z_pct = 0.0
                        lower_z = round(mean_val, 3)
                        upper_z = round(mean_val, 3)

                    outlier_details[col] = {
                        "iqr": IQRBoundaries(
                            q1=round(q1, 3),
                            q3=round(q3, 3),
                            iqr=round(iqr, 3),
                            lower_bound=lower_iqr,
                            upper_bound=upper_iqr,
                            outlier_count=iqr_count,
                            outlier_percentage=iqr_pct,
                        ).model_dump(),
                        "zscore": ZScoreBoundaries(
                            mean=round(mean_val, 3),
                            std=round(std_val, 3),
                            threshold=threshold,
                            lower_bound=lower_z,
                            upper_bound=upper_z,
                            outlier_count=z_count,
                            outlier_percentage=z_pct,
                        ).model_dump(),
                    }

            columns_summary.append(
                ColumnQualitySummary(
                    column_name=col,
                    position=idx,
                    data_type=semantic_type,
                    total_count=total_rows,
                    missing_count=col_missing,
                    missing_percentage=col_missing_pct,
                    unique_count=col_unique,
                    is_numeric=is_num,
                    outliers_iqr_count=iqr_count,
                    outliers_zscore_count=z_count,
                )
            )

        return DataQualityProfile(
            dataset_id=dataset_id,
            filename=filename,
            is_cleaned=is_cleaned,
            parent_id=parent_id,
            version=version,
            total_rows=total_rows,
            total_columns=total_columns,
            total_cells=total_cells,
            total_missing_cells=total_missing,
            missing_percentage=missing_pct,
            duplicate_rows=duplicate_rows,
            duplicate_percentage=duplicate_pct,
            quality_metrics=quality_metric,
            columns=columns_summary,
            outlier_details=sanitize_for_json(outlier_details),
            original_file_hash=original_file_hash,
        )

    # -------------------------------------------------------------------------
    # Safe Transformation Execution
    # -------------------------------------------------------------------------
    @classmethod
    def execute_transformation(
        cls,
        df: pd.DataFrame,
        operation_type: str,
        strategy: str,
        column_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, int, int, str, List[str]]:
        """
        Executes a transformation on a DataFrame copy.
        Returns: (transformed_df, affected_rows, affected_cells, description, warnings)
        """
        params = parameters or {}
        transformed = df.copy()
        warnings: List[str] = []
        affected_rows = 0
        affected_cells = 0
        description = ""

        # Validate column existence if column_name provided
        if column_name is not None and column_name != "":
            if column_name not in transformed.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column '{column_name}' does not exist in dataset. Available: {list(transformed.columns)}",
                )

        # 1. Missing Values
        if operation_type == "missing_values":
            if not column_name and strategy not in ("remove_rows", "remove_all_missing_rows"):
                raise HTTPException(
                    status_code=400,
                    detail="Missing value strategy requires a column to be specified.",
                )

            if strategy == "mean_replacement":
                series = transformed[column_name]
                clean = pd.to_numeric(series, errors="coerce").dropna()
                if len(clean) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column '{column_name}' contains no valid numeric values to calculate mean.",
                    )
                fill_val = round(float(clean.mean()), 4)
                missing_mask = transformed[column_name].isna()
                affected_cells = int(missing_mask.sum())
                affected_rows = affected_cells
                transformed[column_name] = transformed[column_name].fillna(fill_val)
                description = f"Imputed {affected_cells} missing values in '{column_name}' with mean ({fill_val})."

            elif strategy == "median_replacement":
                series = transformed[column_name]
                clean = pd.to_numeric(series, errors="coerce").dropna()
                if len(clean) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column '{column_name}' contains no valid numeric values to calculate median.",
                    )
                fill_val = round(float(clean.median()), 4)
                missing_mask = transformed[column_name].isna()
                affected_cells = int(missing_mask.sum())
                affected_rows = affected_cells
                transformed[column_name] = transformed[column_name].fillna(fill_val)
                description = f"Imputed {affected_cells} missing values in '{column_name}' with median ({fill_val})."

            elif strategy == "mode_replacement":
                series = transformed[column_name].dropna()
                if len(series) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column '{column_name}' is entirely empty. No mode can be calculated.",
                    )
                mode_vals = series.mode()
                if len(mode_vals) == 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"No mode found for column '{column_name}'.",
                    )
                fill_val = mode_vals.iloc[0]
                missing_mask = transformed[column_name].isna()
                affected_cells = int(missing_mask.sum())
                affected_rows = affected_cells
                transformed[column_name] = transformed[column_name].fillna(fill_val)
                description = f"Imputed {affected_cells} missing values in '{column_name}' with mode ('{fill_val}')."

            elif strategy == "constant_replacement":
                if "value" not in params:
                    raise HTTPException(
                        status_code=400,
                        detail="Constant replacement strategy requires a 'value' parameter.",
                    )
                fill_val = params["value"]
                missing_mask = transformed[column_name].isna()
                affected_cells = int(missing_mask.sum())
                affected_rows = affected_cells
                transformed[column_name] = transformed[column_name].fillna(fill_val)
                description = f"Imputed {affected_cells} missing values in '{column_name}' with constant ({fill_val})."

            elif strategy == "remove_rows":
                if column_name:
                    missing_mask = transformed[column_name].isna()
                    affected_rows = int(missing_mask.sum())
                    affected_cells = affected_rows
                    transformed = transformed[~missing_mask].reset_index(drop=True)
                    description = f"Removed {affected_rows} rows with missing values in '{column_name}'."
                else:
                    missing_mask = transformed.isna().any(axis=1)
                    affected_rows = int(missing_mask.sum())
                    affected_cells = int(transformed.isna().sum().sum())
                    transformed = transformed[~missing_mask].reset_index(drop=True)
                    description = f"Removed {affected_rows} rows containing missing values."

            elif strategy == "remove_column":
                missing_count = int(transformed[column_name].isna().sum())
                affected_cells = missing_count
                affected_rows = len(transformed)
                transformed = transformed.drop(columns=[column_name])
                description = f"Removed column '{column_name}' ({missing_count} missing cells)."

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported missing value strategy '{strategy}'.",
                )

        # 2. Duplicate Removal
        elif operation_type == "duplicates":
            keep = params.get("keep", "first")
            if keep not in ("first", "last", False):
                keep = "first"

            dup_mask = transformed.duplicated(keep=keep)
            affected_rows = int(dup_mask.sum())
            affected_cells = affected_rows * len(transformed.columns)
            transformed = transformed.drop_duplicates(keep=keep).reset_index(drop=True)
            description = f"Removed {affected_rows} duplicate rows (keeping '{keep}' occurrences)."

        # 3. Data Type Conversion
        elif operation_type == "type_conversion":
            if not column_name:
                raise HTTPException(
                    status_code=400, detail="Data type conversion requires a column_name."
                )

            target_type = strategy.lower()
            series = transformed[column_name]
            total_vals = len(series)

            if target_type in ("integer", "int"):
                # Detect invalid non-convertible items
                coerced = pd.to_numeric(series, errors="coerce")
                invalid_count = int(coerced.isna().sum() - series.isna().sum())
                if invalid_count > 0:
                    warnings.append(
                        f"Found {invalid_count} values in '{column_name}' that cannot be converted to integer. They will be coerced to null."
                    )
                # Convert using nullable Int64
                transformed[column_name] = pd.to_numeric(series, errors="coerce").round().astype("Int64")
                affected_cells = total_vals
                description = f"Converted column '{column_name}' to Integer."

            elif target_type in ("float", "numeric"):
                coerced = pd.to_numeric(series, errors="coerce")
                invalid_count = int(coerced.isna().sum() - series.isna().sum())
                if invalid_count > 0:
                    warnings.append(
                        f"Found {invalid_count} values in '{column_name}' that cannot be converted to float. They will be coerced to null."
                    )
                transformed[column_name] = coerced.astype("float64")
                affected_cells = total_vals
                description = f"Converted column '{column_name}' to Float."

            elif target_type in ("string", "str"):
                transformed[column_name] = series.astype(str)
                affected_cells = total_vals
                description = f"Converted column '{column_name}' to String."

            elif target_type in ("boolean", "bool"):
                def to_bool(val: Any) -> Optional[bool]:
                    if pd.isna(val):
                        return None
                    s = str(val).strip().lower()
                    if s in ("true", "1", "yes", "t", "y"):
                        return True
                    if s in ("false", "0", "no", "f", "n"):
                        return False
                    return None

                converted = series.map(to_bool)
                invalid_count = int(converted.isna().sum() - series.isna().sum())
                if invalid_count > 0:
                    warnings.append(
                        f"Found {invalid_count} non-boolean values in '{column_name}'. Coerced to null."
                    )
                transformed[column_name] = converted.astype("boolean")
                affected_cells = total_vals
                description = f"Converted column '{column_name}' to Boolean."

            elif target_type in ("datetime", "date"):
                parsed = pd.to_datetime(series, errors="coerce")
                invalid_count = int(parsed.isna().sum() - series.isna().sum())
                if invalid_count > 0:
                    warnings.append(
                        f"Found {invalid_count} values in '{column_name}' that cannot be parsed as datetime. Coerced to null."
                    )
                transformed[column_name] = parsed
                affected_cells = total_vals
                description = f"Converted column '{column_name}' to Datetime."

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported target type '{target_type}'. Supported: integer, float, string, boolean, datetime.",
                )

        # 4. Outlier Detection & Treatment
        elif operation_type == "outliers":
            if not column_name:
                raise HTTPException(status_code=400, detail="Outlier operation requires a column_name.")

            method = params.get("method", "iqr").lower()
            action = strategy.lower()  # keep, remove_rows, cap_values

            num_series = pd.to_numeric(transformed[column_name], errors="coerce")
            valid_nums = num_series.dropna()
            if len(valid_nums) < 4:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column '{column_name}' has insufficient numeric observations to calculate outliers.",
                )

            if method == "zscore":
                mean_val = float(valid_nums.mean())
                std_val = float(valid_nums.std(ddof=1)) if len(valid_nums) > 1 else 0.0
                thresh = float(params.get("threshold", 3.0))
                if std_val == 0.0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column '{column_name}' has standard deviation of 0. No Z-score outliers can exist.",
                    )
                lower_b = round(mean_val - thresh * std_val, 3)
                upper_b = round(mean_val + thresh * std_val, 3)
            else:  # IQR default
                q1 = float(valid_nums.quantile(0.25))
                q3 = float(valid_nums.quantile(0.75))
                iqr = float(q3 - q1)
                lower_b = round(q1 - 1.5 * iqr, 3)
                upper_b = round(q3 + 1.5 * iqr, 3)

            outlier_mask = (num_series < lower_b) | (num_series > upper_b)
            outlier_count = int(outlier_mask.sum())
            affected_rows = outlier_count
            affected_cells = outlier_count

            if action == "keep":
                description = f"Inspected outliers in '{column_name}' ({outlier_count} detected). Kept without modification."
            elif action == "remove_rows":
                transformed = transformed[~outlier_mask].reset_index(drop=True)
                description = f"Removed {outlier_count} outlier rows from '{column_name}' (outside [{lower_b}, {upper_b}])."
            elif action in ("cap_values", "winsorize"):
                capped = num_series.clip(lower=lower_b, upper=upper_b)
                transformed[column_name] = capped
                description = f"Capped {outlier_count} extreme values in '{column_name}' to boundaries [{lower_b}, {upper_b}]."
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported outlier treatment action '{action}'. Supported: keep, remove_rows, cap_values.",
                )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported operation_type '{operation_type}'. Supported: missing_values, duplicates, type_conversion, outliers.",
            )

        return transformed, affected_rows, affected_cells, description, warnings

    # -------------------------------------------------------------------------
    # Preview Operation
    # -------------------------------------------------------------------------
    @classmethod
    def preview_operation(
        cls, dataset_id: str, req: CleaningPreviewRequest
    ) -> CleaningPreviewResponse:
        """
        Preview transformation on the active working copy of dataset WITHOUT persisting.
        Verifies original dataset SHA-256 remains pristine.
        """
        # Determine working DataFrame: clean version if exists, else original
        clean_id = f"clean_{dataset_id}"
        clean_detail = dataset_storage.get_dataset(clean_id)
        if clean_detail:
            df = dataset_storage._load_dataframe(clean_id)
        else:
            df = dataset_storage._load_dataframe(dataset_id)

        # Checksum of original file before operation
        orig_path = dataset_storage.get_dataset_file_path(dataset_id)
        hash_before = dataset_storage.compute_sha256(orig_path)

        transformed, affected_rows, affected_cells, desc, warnings = cls.execute_transformation(
            df=df,
            operation_type=req.operation_type,
            strategy=req.strategy,
            column_name=req.column_name,
            parameters=req.parameters,
        )

        # Checksum of original file after operation (must remain identical!)
        hash_after = dataset_storage.compute_sha256(orig_path)
        if hash_before != hash_after:
            raise RuntimeError("CRITICAL ERROR: Original dataset file was modified during preview!")

        # Sample diff records
        sample_size = 5
        orig_sample: List[Dict[str, Any]] = []
        clean_sample: List[Dict[str, Any]] = []

        if len(df) > 0:
            for _, r in df.head(sample_size).iterrows():
                orig_sample.append(
                    {str(k): (None if pd.isna(v) else sanitize_for_json(v)) for k, v in r.items()}
                )
        if len(transformed) > 0:
            for _, r in transformed.head(sample_size).iterrows():
                clean_sample.append(
                    {str(k): (None if pd.isna(v) else sanitize_for_json(v)) for k, v in r.items()}
                )

        return CleaningPreviewResponse(
            operation_type=req.operation_type,
            column_name=req.column_name,
            strategy=req.strategy,
            affected_rows=affected_rows,
            affected_cells=affected_cells,
            is_valid=True,
            validation_warnings=warnings,
            original_sample=orig_sample,
            cleaned_sample=clean_sample,
            summary=desc,
        )

    # -------------------------------------------------------------------------
    # Apply Operation & Snapshot Management
    # -------------------------------------------------------------------------
    @classmethod
    def apply_operation(
        cls, dataset_id: str, req: CleaningApplyRequest
    ) -> CleaningApplyResponse:
        """
        Apply transformation, increment version, persist snapshot, update cleaned dataset,
        and verify original dataset immutability via SHA-256.
        """
        # Verify original file exists and compute hash
        orig_path = dataset_storage.get_dataset_file_path(dataset_id)
        hash_before = dataset_storage.compute_sha256(orig_path)

        clean_id = f"clean_{dataset_id}"
        clean_detail = dataset_storage.get_dataset(clean_id)
        history = cls.get_history(dataset_id)

        if clean_detail:
            active_df = dataset_storage._load_dataframe(clean_id)
            current_version = clean_detail.overview.version
        else:
            active_df = dataset_storage._load_dataframe(dataset_id)
            current_version = 0

        # Execute transformation
        transformed, affected_rows, affected_cells, desc, _ = cls.execute_transformation(
            df=active_df,
            operation_type=req.operation_type,
            strategy=req.strategy,
            column_name=req.column_name,
            parameters=req.parameters,
        )

        new_version = current_version + 1
        now_iso = datetime.now(timezone.utc).isoformat()

        # Save snapshot for undo
        cls._save_snapshot(dataset_id, new_version, transformed)

        # Log transformation step
        step = TransformationStep(
            step_id=len(history) + 1,
            version=new_version,
            operation_type=req.operation_type,
            column_name=req.column_name,
            strategy=req.strategy,
            parameters=sanitize_for_json(req.parameters or {}),
            affected_rows=affected_rows,
            affected_cells=affected_cells,
            description=desc,
            timestamp=now_iso,
        )
        history.append(step)
        cls._save_history(dataset_id, history)

        # Register updated cleaned dataset in dataset_storage
        cleaned_detail = dataset_storage.register_cleaned_dataset(
            parent_id=dataset_id,
            cleaned_df=transformed,
            version=new_version,
        )

        # Re-verify original file hash has NOT changed
        hash_after = dataset_storage.compute_sha256(orig_path)
        if hash_before != hash_after:
            raise RuntimeError("CRITICAL ERROR: Original dataset file was modified during apply!")

        # Recalculate quality profile for cleaned dataset
        quality = cls.calculate_quality_profile(
            df=transformed,
            dataset_id=clean_id,
            filename=cleaned_detail.overview.filename,
            is_cleaned=True,
            version=new_version,
            parent_id=dataset_id,
            original_file_hash=hash_after,
        )

        return CleaningApplyResponse(
            success=True,
            message=desc,
            cleaned_dataset_id=clean_id,
            version=new_version,
            step=step,
            updated_quality=quality,
            original_file_hash_verified=(hash_before == hash_after),
        )

    # -------------------------------------------------------------------------
    # Undo Last Transformation
    # -------------------------------------------------------------------------
    @classmethod
    def undo_operation(cls, dataset_id: str) -> UndoResponse:
        """
        Roll back the most recent transformation step.
        If rolling back to version 0, resets to the original dataset.
        """
        orig_path = dataset_storage.get_dataset_file_path(dataset_id)
        hash_before = dataset_storage.compute_sha256(orig_path)

        clean_id = f"clean_{dataset_id}"
        clean_detail = dataset_storage.get_dataset(clean_id)
        if not clean_detail:
            raise HTTPException(status_code=400, detail="No active cleaned dataset to undo.")

        history = cls.get_history(dataset_id)
        if not history:
            raise HTTPException(status_code=400, detail="Transformation history is empty.")

        current_version = clean_detail.overview.version
        # Remove snapshot of current version
        cls._remove_snapshot(dataset_id, current_version)

        # Pop latest step
        history.pop()
        cls._save_history(dataset_id, history)

        target_version = current_version - 1

        if target_version > 0:
            # Revert to snapshot of target_version
            prev_df = cls._load_snapshot(dataset_id, target_version)
            if prev_df is None:
                raise HTTPException(
                    status_code=500, detail=f"Snapshot for version {target_version} is missing."
                )
            cleaned_detail = dataset_storage.register_cleaned_dataset(
                parent_id=dataset_id,
                cleaned_df=prev_df,
                version=target_version,
            )
            quality = cls.calculate_quality_profile(
                df=prev_df,
                dataset_id=clean_id,
                filename=cleaned_detail.overview.filename,
                is_cleaned=True,
                version=target_version,
                parent_id=dataset_id,
                original_file_hash=hash_before,
            )
            msg = f"Reverted transformation back to version {target_version}."
        else:
            # Revert back to original dataset
            dataset_storage.delete_cleaned_dataset(dataset_id)
            orig_df = dataset_storage._load_dataframe(dataset_id)
            orig_detail = dataset_storage.get_dataset(dataset_id)
            quality = cls.calculate_quality_profile(
                df=orig_df,
                dataset_id=dataset_id,
                filename=orig_detail.overview.filename,
                is_cleaned=False,
                version=0,
                original_file_hash=hash_before,
            )
            msg = "Reverted all transformations back to original uploaded dataset."

        hash_after = dataset_storage.compute_sha256(orig_path)
        if hash_before != hash_after:
            raise RuntimeError("CRITICAL ERROR: Original file was modified during undo!")

        return UndoResponse(
            success=True,
            message=msg,
            current_version=target_version,
            remaining_steps=len(history),
            cleaned_dataset_id=clean_id if target_version > 0 else dataset_id,
            updated_quality=quality,
        )

    # -------------------------------------------------------------------------
    # Reset to Original Dataset
    # -------------------------------------------------------------------------
    @classmethod
    def reset_dataset(cls, dataset_id: str) -> ResetResponse:
        """
        Immediately resets all transformations, deletes intermediate snapshots,
        removes the cleaned version, and restores pristine original data.
        Guarantees original dataset integrity.
        """
        orig_path = dataset_storage.get_dataset_file_path(dataset_id)
        hash_before = dataset_storage.compute_sha256(orig_path)

        # Delete cleaned dataset from memory and disk
        dataset_storage.delete_cleaned_dataset(dataset_id)

        # Clear snapshots and history
        cls._clean_snapshots_dir(dataset_id)
        hist_path = cls._get_history_file(dataset_id)
        if hist_path.exists():
            try:
                hist_path.unlink()
            except Exception:
                pass

        hash_after = dataset_storage.compute_sha256(orig_path)
        if hash_before != hash_after:
            raise RuntimeError("CRITICAL ERROR: Original file was modified during reset!")

        # Load pristine original dataset
        orig_df = dataset_storage._load_dataframe(dataset_id)
        orig_detail = dataset_storage.get_dataset(dataset_id)

        quality = cls.calculate_quality_profile(
            df=orig_df,
            dataset_id=dataset_id,
            filename=orig_detail.overview.filename,
            is_cleaned=False,
            version=0,
            original_file_hash=hash_after,
        )

        return ResetResponse(
            success=True,
            message="Cleaned dataset reset successfully. Original uploaded data restored.",
            original_dataset_id=dataset_id,
            original_file_hash_verified=(hash_before == hash_after),
            updated_quality=quality,
        )

