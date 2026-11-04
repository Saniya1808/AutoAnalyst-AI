from typing import Optional
from fastapi import APIRouter, Header, HTTPException

from app.core.json_encoder import sanitize_for_json
from app.models.ai_understanding import DatasetUnderstandingResponse
from app.services.ai.understanding_service import DatasetUnderstandingService
from app.services.dataset_storage import dataset_storage

router = APIRouter(prefix="/datasets/{dataset_id}/understanding", tags=["AI Dataset Understanding"])


@router.get("", response_model=DatasetUnderstandingResponse)
async def get_dataset_understanding(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> DatasetUnderstandingResponse:
    """
    Retrieve intelligent, structured AI dataset understanding.
    Returns cached analysis if available for the current snapshot hash,
    or generates a fresh analysis via Gemini (or deterministic statistical fallback).
    """
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    try:
        response = await DatasetUnderstandingService.get_or_generate_understanding(
            dataset_id=dataset_id, force_refresh=False
        )
        return DatasetUnderstandingResponse(**sanitize_for_json(response.model_dump()))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dataset understanding: {str(e)}")


@router.post("/refresh", response_model=DatasetUnderstandingResponse)
async def refresh_dataset_understanding(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> DatasetUnderstandingResponse:
    """
    Force regeneration of AI dataset understanding, bypassing the existing cache.
    """
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    try:
        response = await DatasetUnderstandingService.get_or_generate_understanding(
            dataset_id=dataset_id, force_refresh=True
        )
        return DatasetUnderstandingResponse(**sanitize_for_json(response.model_dump()))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh dataset understanding: {str(e)}")

