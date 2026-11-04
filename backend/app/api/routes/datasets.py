from typing import Optional
from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.json_encoder import sanitize_for_json
from app.models.dataset import (
    DatasetDeleteResponse,
    DatasetDetail,
    DatasetListResponse,
    DatasetOverview,
    DatasetPreview,
)
from app.services.dataset_storage import dataset_storage

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "/upload",
    summary="Upload and profile a dataset (CSV, XLSX, XLS)",
    status_code=status.HTTP_201_CREATED,
)
async def upload_dataset(
    file: UploadFile = File(..., description="CSV or Excel file to upload"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Upload a dataset file (CSV, XLSX, XLS), validate constraints, and compute
    in-depth Pandas statistical profiling and row preview.
    """
    detail = await dataset_storage.save_and_profile_upload(file, session_id=x_session_id)
    sanitized = sanitize_for_json(detail.model_dump())
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=sanitized)


@router.get(
    "",
    summary="List all uploaded datasets",
    response_model=DatasetListResponse,
)
async def list_datasets(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """List all currently stored datasets along with workspace totals."""
    datasets = dataset_storage.list_datasets(session_id=x_session_id)
    total_datasets = len(datasets)
    total_rows_all = sum(d.row_count for d in datasets)
    total_columns_all = sum(d.column_count for d in datasets)

    response_data = {
        "datasets": [d.model_dump() for d in datasets],
        "total_datasets": total_datasets,
        "total_rows_all": total_rows_all,
        "total_columns_all": total_columns_all,
    }
    return JSONResponse(content=sanitize_for_json(response_data))


@router.get(
    "/{dataset_id}",
    summary="Get full dataset profile and preview",
)
async def get_dataset(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """Retrieve full profile metadata, column statistics, and preview for a dataset."""
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)
    return JSONResponse(content=sanitize_for_json(detail.model_dump()))


@router.get(
    "/{dataset_id}/profile",
    summary="Get dedicated dataset profile and column statistics",
)
async def get_dataset_profile(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """Retrieve dedicated column profiling, statistics, distributions, and dataset overview."""
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)
    profile_data = {
        "overview": detail.overview.model_dump(),
        "columns": [col.model_dump() for col in detail.columns],
    }
    return JSONResponse(content=sanitize_for_json(profile_data))


@router.get(
    "/{dataset_id}/preview",
    summary="Get paginated preview rows",
)
async def get_dataset_preview(
    dataset_id: str,
    offset: int = Query(0, ge=0, description="Row offset for pagination"),
    limit: int = Query(50, ge=1, le=1000, description="Max rows to return"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """Fetch a paginated slice of dataset rows."""
    preview = dataset_storage.get_preview(
        dataset_id, offset=offset, limit=limit, session_id=x_session_id
    )
    return JSONResponse(content=sanitize_for_json(preview.model_dump()))


@router.delete(
    "/{dataset_id}",
    summary="Delete a dataset",
    response_model=DatasetDeleteResponse,
)
async def delete_dataset(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """Delete a dataset and its stored files."""
    # Verify authorization and existence first
    dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)
    deleted = dataset_storage.delete_dataset(dataset_id, session_id=x_session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return DatasetDeleteResponse(
        message="Dataset deleted successfully",
        id=dataset_id,
        success=True,
    )

