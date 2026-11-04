from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query

from app.core.json_encoder import sanitize_for_json
from app.models.automated_insights import AutomatedInsightsResponse
from app.services.ai.insights_synthesizer import InsightsSynthesizer
from app.services.dataset_storage import dataset_storage

router = APIRouter(prefix="/datasets/{dataset_id}/insights", tags=["Automated Insights & Business Intelligence"])


@router.get("", response_model=AutomatedInsightsResponse)
async def get_automated_insights(
    dataset_id: str,
    date_col: Optional[str] = Query(default=None, description="Optional target date/time column"),
    metric_col: Optional[str] = Query(default=None, description="Optional target numerical metric column"),
    granularity: Optional[str] = Query(default=None, description="Optional date granularity (year, quarter, month, week, day)"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> AutomatedInsightsResponse:
    """
    Retrieve automated dataset insights, temporal trends, best/worst category benchmarks,
    statistical anomalies, and actionable recommendations.
    Snapshot-aware: cached results automatically invalidate on data cleaning/reset.
    """
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    try:
        insights = await InsightsSynthesizer.get_or_generate_insights(
            dataset_id=dataset_id,
            force_refresh=False,
            date_col=date_col,
            metric_col=metric_col,
            granularity=granularity,
        )
        return AutomatedInsightsResponse(**sanitize_for_json(insights.model_dump()))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate automated insights: {str(e)}")


@router.post("/refresh", response_model=AutomatedInsightsResponse)
async def refresh_automated_insights(
    dataset_id: str,
    date_col: Optional[str] = Query(default=None, description="Optional target date/time column"),
    metric_col: Optional[str] = Query(default=None, description="Optional target numerical metric column"),
    granularity: Optional[str] = Query(default=None, description="Optional date granularity"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> AutomatedInsightsResponse:
    """
    Force re-computation of automated insights, bypassing existing snapshot cache.
    """
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    try:
        insights = await InsightsSynthesizer.get_or_generate_insights(
            dataset_id=dataset_id,
            force_refresh=True,
            date_col=date_col,
            metric_col=metric_col,
            granularity=granularity,
        )
        return AutomatedInsightsResponse(**sanitize_for_json(insights.model_dump()))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh automated insights: {str(e)}")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh automated insights: {str(e)}")

