from typing import Optional
from fastapi import APIRouter, Header, HTTPException

from app.core.json_encoder import sanitize_for_json
from app.models.cleaning import (
    CleaningApplyRequest,
    CleaningApplyResponse,
    CleaningPreviewRequest,
    CleaningPreviewResponse,
    DataQualityProfile,
    ResetResponse,
    TransformationHistoryResponse,
    UndoResponse,
)
from app.services.cleaning_service import CleaningService
from app.services.dataset_storage import dataset_storage

router = APIRouter(prefix="/datasets/{dataset_id}/cleaning", tags=["Data Cleaning"])


@router.get("/profile", response_model=DataQualityProfile)
async def get_cleaning_profile(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> DataQualityProfile:
    """
    Retrieve comprehensive data quality analysis, missing value metrics,
    duplicate counts, and outlier boundaries for a dataset (or its active cleaned version).
    """
    clean_id = f"clean_{dataset_id}"
    orig_detail = None
    try:
        orig_detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)
    except HTTPException:
        pass

    clean_detail = None
    try:
        clean_detail = dataset_storage.get_authorized_dataset(clean_id, session_id=x_session_id)
    except HTTPException:
        pass

    if not orig_detail and not clean_detail:
        raise HTTPException(status_code=404, detail="Dataset not found")

    target_detail = clean_detail or orig_detail
    df = dataset_storage._load_dataframe(target_detail.overview.id)

    # Compute original file SHA-256
    orig_path = dataset_storage.get_dataset_file_path(orig_detail.overview.id if orig_detail else dataset_id)
    orig_hash = dataset_storage.compute_sha256(orig_path)

    profile = CleaningService.calculate_quality_profile(
        df=df,
        dataset_id=target_detail.overview.id,
        filename=target_detail.overview.filename,
        is_cleaned=target_detail.overview.is_cleaned,
        version=target_detail.overview.version,
        parent_id=target_detail.overview.parent_id,
        original_file_hash=orig_hash,
    )
    return DataQualityProfile(**sanitize_for_json(profile.model_dump()))


@router.post("/preview", response_model=CleaningPreviewResponse)
async def preview_cleaning_operation(
    dataset_id: str,
    request: CleaningPreviewRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> CleaningPreviewResponse:
    """
    Simulate a cleaning operation on an in-memory copy without persisting any changes.
    Returns affected row/cell counts, warnings, and sample diff records.
    """
    # Verify dataset exists and caller is authorized
    dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    preview = CleaningService.preview_operation(dataset_id=dataset_id, req=request)
    return CleaningPreviewResponse(**sanitize_for_json(preview.model_dump()))


@router.post("/apply", response_model=CleaningApplyResponse)
async def apply_cleaning_operation(
    dataset_id: str,
    request: CleaningApplyRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> CleaningApplyResponse:
    """
    Apply a cleaning transformation, create an undo snapshot, update the cleaned dataset,
    and verify original file immutability via SHA-256.
    """
    dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    result = CleaningService.apply_operation(dataset_id=dataset_id, req=request)
    return CleaningApplyResponse(**sanitize_for_json(result.model_dump()))


@router.get("/history", response_model=TransformationHistoryResponse)
async def get_cleaning_history(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> TransformationHistoryResponse:
    """
    Retrieve the chronological audit trail of all applied transformations.
    """
    dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    clean_id = f"clean_{dataset_id}"
    clean_detail = dataset_storage.get_dataset(clean_id)
    current_version = clean_detail.overview.version if clean_detail else 0
    history = CleaningService.get_history(dataset_id)

    return TransformationHistoryResponse(
        dataset_id=dataset_id,
        cleaned_dataset_id=clean_id if clean_detail else None,
        current_version=current_version,
        history=history,
    )


@router.post("/undo", response_model=UndoResponse)
async def undo_cleaning_operation(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> UndoResponse:
    """
    Undo the most recent cleaning transformation, restoring the previous snapshot.
    """
    dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    result = CleaningService.undo_operation(dataset_id=dataset_id)
    return UndoResponse(**sanitize_for_json(result.model_dump()))


@router.post("/reset", response_model=ResetResponse)
async def reset_cleaning_dataset(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> ResetResponse:
    """
    Reset all transformations, discard intermediate snapshots, and restore pristine original data.
    """
    dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    result = CleaningService.reset_dataset(dataset_id=dataset_id)
    return ResetResponse(**sanitize_for_json(result.model_dump()))

