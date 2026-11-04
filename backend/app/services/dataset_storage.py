import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, UploadFile
import pandas as pd

from app.core.config import settings
from app.core.json_encoder import sanitize_for_json
from app.models.dataset import (
    ColumnProfile,
    DatasetDetail,
    DatasetOverview,
    DatasetPreview,
)
from app.services.profiler import (
    compute_dataset_overview,
    generate_dataset_preview,
    profile_column,
)


class DatasetStorageService:
    def __init__(self, upload_dir: Optional[str] = None):
        self.upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        # In-memory registry of datasets for rapid access: id -> DatasetDetail
        self._cache: Dict[str, DatasetDetail] = {}
        # In-memory cached dataframes for preview/query operations
        self._df_cache: Dict[str, pd.DataFrame] = {}
        self._load_persisted_metadata()

    def _load_persisted_metadata(self) -> None:
        """Scan upload directory for persisted dataset metadata on startup."""
        try:
            for meta_file in self.upload_dir.glob("*_meta.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    detail = DatasetDetail(**data)
                    self._cache[detail.overview.id] = detail
                except Exception:
                    # Ignore corrupt or unreadable metadata
                    pass
        except Exception:
            pass

    def _get_storage_path(self, dataset_id: str, extension: str) -> Path:
        """Get internal file path for a dataset (never returned to frontend)."""
        safe_ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        return self.upload_dir / f"{dataset_id}{safe_ext}"

    def _get_meta_path(self, dataset_id: str) -> Path:
        """Get internal metadata JSON path."""
        return self.upload_dir / f"{dataset_id}_meta.json"

    def _load_dataframe(self, dataset_id: str) -> pd.DataFrame:
        """Load DataFrame from memory cache or persisted disk storage."""
        if dataset_id in self._df_cache:
            return self._df_cache[dataset_id]

        detail = self.get_dataset(dataset_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Dataset not found")

        ext = detail.overview.file_type.lower()
        file_path = self._get_storage_path(dataset_id, ext)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Underlying dataset file is missing")

        df = self._read_file_to_df(file_path, ext)
        self._df_cache[dataset_id] = df
        return df

    @staticmethod
    def _read_file_to_df(file_path: Path, extension: str) -> pd.DataFrame:
        """Read CSV, XLSX, or XLS into a Pandas DataFrame with encoding fallbacks."""
        ext = extension.lower()
        if ext == ".csv":
            try:
                # Try UTF-8 first
                return pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    # Fallback to Latin-1
                    return pd.read_csv(file_path, encoding="latin-1")
                except Exception as e:
                    raise ValueError(f"Failed to decode CSV file: {str(e)}")
            except Exception as e:
                raise ValueError(f"Failed to parse CSV file: {str(e)}")

        elif ext == ".xlsx":
            try:
                return pd.read_excel(file_path, engine="openpyxl")
            except Exception as e:
                raise ValueError(f"Failed to parse XLSX file: {str(e)}")

        elif ext == ".xls":
            try:
                return pd.read_excel(file_path, engine="xlrd")
            except Exception as e:
                raise ValueError(f"Failed to parse XLS file: {str(e)}")

        else:
            raise ValueError(f"Unsupported file format '{ext}'")

    async def save_and_profile_upload(
        self,
        upload_file: UploadFile,
        session_id: Optional[str] = None,
        is_sample: bool = False,
    ) -> DatasetDetail:
        """
        Stream, validate, profile, and persist an uploaded dataset file.
        Guarantees cleanup of partial files on failure.
        """
        # Validate filename
        if not upload_file.filename:
            raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

        raw_filename = upload_file.filename
        # Sanitize filename (strip directory components to prevent path traversal)
        safe_filename = Path(raw_filename).name.strip()
        _, ext = os.path.splitext(safe_filename)
        ext = ext.lower()

        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension '{ext}'. Allowed extensions are: {', '.join(settings.ALLOWED_EXTENSIONS)}",
            )

        # Generate secure, unguessable dataset ID
        dataset_id = uuid.uuid4().hex

        # Temporary path for incoming stream
        temp_file_path = self.upload_dir / f"tmp_{dataset_id}{ext}"
        final_file_path = self._get_storage_path(dataset_id, ext)
        meta_file_path = self._get_meta_path(dataset_id)

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        total_bytes = 0

        try:
            # Stream upload in chunks to enforce size limit and prevent memory exhaustion
            with open(temp_file_path, "wb") as buffer:
                while True:
                    chunk = await upload_file.read(64 * 1024)  # 64 KB chunks
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"File exceeds maximum allowed size limit of {settings.MAX_UPLOAD_SIZE_MB} MB",
                        )
                    buffer.write(chunk)

            # Check for empty file (0 bytes)
            if total_bytes == 0:
                raise HTTPException(status_code=400, detail="The uploaded file is empty (0 bytes)")

            # Parse DataFrame with Pandas
            try:
                df = self._read_file_to_df(temp_file_path, ext)
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not parse spreadsheet data: {str(e)}",
                )

            # Validate DataFrame dimensions
            if df.empty or len(df.columns) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded file contains no data rows or columns",
                )

            if len(df.columns) > settings.MAX_DATASET_COLUMNS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dataset has {len(df.columns)} columns, which exceeds the maximum limit of {settings.MAX_DATASET_COLUMNS}",
                )

            if len(df) > settings.MAX_DATASET_ROWS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dataset has {len(df):,} rows, which exceeds the maximum limit of {settings.MAX_DATASET_ROWS:,}",
                )

            # Compute Pandas profiling
            now_iso = datetime.now(timezone.utc).isoformat()
            overview = compute_dataset_overview(
                df=df,
                dataset_id=dataset_id,
                filename=safe_filename,
                file_size_bytes=total_bytes,
                file_type=ext,
                uploaded_at=now_iso,
            )
            if session_id:
                overview.session_id = session_id
            overview.is_sample = is_sample

            columns: List[ColumnProfile] = [
                profile_column(df[col], idx) for idx, col in enumerate(df.columns)
            ]

            preview = generate_dataset_preview(
                df=df,
                offset=0,
                limit=settings.PREVIEW_ROW_LIMIT,
            )

            detail = DatasetDetail(
                overview=overview,
                columns=columns,
                preview=preview,
            )

            # Promote temp file to final storage path
            shutil.move(str(temp_file_path), str(final_file_path))

            # Persist metadata to disk (sanitized for JSON)
            sanitized_detail = sanitize_for_json(detail.model_dump())
            with open(meta_file_path, "w", encoding="utf-8") as f:
                json.dump(sanitized_detail, f, indent=2)

            # Store in caches
            self._cache[dataset_id] = detail
            self._df_cache[dataset_id] = df

            return detail

        except Exception as e:
            # Clean up partial temporary file on failure
            if temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except Exception:
                    pass
            # Clean up final and meta file if partially created
            if final_file_path.exists():
                try:
                    final_file_path.unlink()
                except Exception:
                    pass
            if meta_file_path.exists():
                try:
                    meta_file_path.unlink()
                except Exception:
                    pass
            # Re-raise HTTPExceptions directly, wrap unexpected exceptions
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred while processing dataset: {str(e)}",
            )
        finally:
            await upload_file.close()

    def list_datasets(self, session_id: Optional[str] = None) -> List[DatasetOverview]:
        """List available datasets sorted by upload date descending.
        
        If session_id is provided, returns:
        - Datasets owned by this session (session_id == session_id)
        - Public sample datasets (is_sample is True)
        - Legacy/unowned datasets (session_id is None)
        """
        if session_id:
            overviews = [
                detail.overview
                for detail in self._cache.values()
                if detail.overview.session_id == session_id
                or detail.overview.is_sample
                or detail.overview.session_id is None
            ]
        else:
            overviews = [detail.overview for detail in self._cache.values()]

        # Sort newest first
        overviews.sort(key=lambda o: o.uploaded_at, reverse=True)
        return overviews

    def get_authorized_dataset(
        self, dataset_id: str, session_id: Optional[str] = None
    ) -> DatasetDetail:
        """
        Fetch dataset metadata while strictly enforcing session ownership for external API routes.
        Raises HTTP 404 if dataset does not exist, or if the dataset is owned by a different
        session or no session header was provided for a private dataset.
        Public sample datasets and unowned test datasets are accessible to all.
        """
        detail = self._cache.get(dataset_id)
        if not detail:
            raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

        # If dataset is private (owned by a session and not a sample):
        if detail.overview.session_id is not None and not detail.overview.is_sample:
            if not session_id or detail.overview.session_id != session_id:
                raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

        return detail

    def get_dataset(
        self, dataset_id: str, session_id: Optional[str] = None
    ) -> Optional[DatasetDetail]:
        """Get full dataset details including column profile and preview.
        If session_id is provided, enforces that the caller owns the dataset
        (unless it is a public sample dataset).
        If session_id is None, returns the dataset directly for trusted internal services
        and test callers.
        """
        detail = self._cache.get(dataset_id)
        if not detail:
            return None

        # If caller explicitly provided a session token, enforce ownership on private datasets
        if session_id is not None and detail.overview.session_id is not None and not detail.overview.is_sample:
            if detail.overview.session_id != session_id:
                return None

        return detail

    def get_preview(
        self,
        dataset_id: str,
        offset: int = 0,
        limit: int = 50,
        session_id: Optional[str] = None,
    ) -> DatasetPreview:
        """Get paginated preview rows for a dataset."""
        detail = self.get_authorized_dataset(dataset_id, session_id=session_id)
        df = self._load_dataframe(dataset_id)
        return generate_dataset_preview(df=df, offset=offset, limit=limit)

    def delete_dataset(self, dataset_id: str, session_id: Optional[str] = None) -> bool:
        """Delete a dataset from memory and disk, verifying ownership and protecting sample datasets."""
        detail = self._cache.get(dataset_id)
        if not detail:
            return False

        if detail.overview.is_sample:
            raise HTTPException(
                status_code=403,
                detail="Sample datasets are protected and cannot be deleted.",
            )

        if detail.overview.session_id is not None:
            if not session_id or detail.overview.session_id != session_id:
                return False

        self._cache.pop(dataset_id, None)
        self._df_cache.pop(dataset_id, None)

        ext = detail.overview.file_type.lower()
        file_path = self._get_storage_path(dataset_id, ext)
        meta_path = self._get_meta_path(dataset_id)

        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass

        if meta_path.exists():
            try:
                meta_path.unlink()
            except Exception:
                pass

        return True


    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute SHA-256 checksum of a file on disk."""
        if not file_path.exists():
            return ""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_dataset_file_path(self, dataset_id: str) -> Path:
        """Get the storage path of a dataset file."""
        detail = self.get_dataset(dataset_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Dataset not found")
        ext = detail.overview.file_type.lower()
        return self._get_storage_path(dataset_id, ext)

    def register_cleaned_dataset(
        self, parent_id: str, cleaned_df: pd.DataFrame, version: int
    ) -> DatasetDetail:
        """Persist, profile, and register a cleaned DataFrame as an independent dataset."""
        parent_detail = self.get_dataset(parent_id)
        if not parent_detail:
            raise HTTPException(status_code=404, detail="Parent dataset not found")

        clean_id = f"clean_{parent_id}"
        clean_ext = ".csv"
        clean_filename = f"Cleaned_{parent_detail.overview.filename}"
        if not clean_filename.endswith(".csv"):
            base_name, _ = os.path.splitext(clean_filename)
            clean_filename = f"{base_name}.csv"

        clean_file_path = self._get_storage_path(clean_id, clean_ext)
        clean_meta_path = self._get_meta_path(clean_id)

        # Write clean dataframe to CSV
        cleaned_df.to_csv(clean_file_path, index=False, encoding="utf-8")
        file_size_bytes = clean_file_path.stat().st_size

        now_iso = datetime.now(timezone.utc).isoformat()
        overview = compute_dataset_overview(
            df=cleaned_df,
            dataset_id=clean_id,
            filename=clean_filename,
            file_size_bytes=file_size_bytes,
            file_type=clean_ext,
            uploaded_at=now_iso,
        )
        overview.is_cleaned = True
        overview.parent_id = parent_id
        overview.version = version
        overview.session_id = parent_detail.overview.session_id
        overview.is_sample = parent_detail.overview.is_sample

        columns: List[ColumnProfile] = [
            profile_column(cleaned_df[col], idx)
            for idx, col in enumerate(cleaned_df.columns)
        ]

        preview = generate_dataset_preview(
            df=cleaned_df, offset=0, limit=settings.PREVIEW_ROW_LIMIT
        )

        detail = DatasetDetail(
            overview=overview,
            columns=columns,
            preview=preview,
        )

        # Persist metadata JSON
        sanitized_detail = sanitize_for_json(detail.model_dump())
        with open(clean_meta_path, "w", encoding="utf-8") as f:
            json.dump(sanitized_detail, f, indent=2)

        # Update in-memory caches
        self._cache[clean_id] = detail
        self._df_cache[clean_id] = cleaned_df

        return detail

    def delete_cleaned_dataset(self, parent_id: str) -> None:
        """Remove cleaned dataset for a parent if it exists."""
        clean_id = f"clean_{parent_id}"
        self.delete_dataset(clean_id)


# Global service instance
dataset_storage = DatasetStorageService()

