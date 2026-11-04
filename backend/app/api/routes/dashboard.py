from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.core.json_encoder import sanitize_for_json
from app.models.dashboard import (
    ChartConfig,
    ColumnInfo,
    CustomChartRequest,
    DashboardResponse,
    DrillDownRequest,
    DrillDownResponse,
    FilterDashboardRequest,
)
from app.services.dashboard_service import dashboard_service
from app.services.dataset_storage import dataset_storage
from app.services.profiler import infer_column_type

router = APIRouter(prefix="/datasets/{dataset_id}", tags=["dashboards"])


def _get_dataset_and_df(dataset_id: str, session_id: Optional[str] = None):
    """Helper to fetch dataset metadata and loaded DataFrame safely."""
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=session_id)
    df = dataset_storage._load_dataframe(dataset_id)
    return detail, df


@router.get(
    "/dashboard",
    summary="Get complete automatic KPI dashboard and recommended charts",
)
async def get_dataset_dashboard(
    dataset_id: str,
    selected_column: Optional[str] = Query(None, description="Optional numeric column for detailed KPIs"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Generate an executive KPI dashboard and intelligent chart recommendations
    derived directly from the uploaded dataset.
    """
    detail, df = _get_dataset_and_df(dataset_id, session_id=x_session_id)

    kpis = dashboard_service.calculate_kpis(df, selected_col=selected_column)
    filter_opts = dashboard_service.get_filter_options(df)
    rec_charts = dashboard_service.recommend_charts(df, max_charts=6)

    available_cols = [
        ColumnInfo(name=str(col), data_type=infer_column_type(df[col]))
        for col in df.columns
    ]

    response = DashboardResponse(
        dataset_id=dataset_id,
        filename=detail.overview.filename,
        kpis=kpis,
        filter_options=filter_opts,
        active_filters=[],
        recommended_charts=rec_charts,
        available_columns=available_cols,
        is_filtered=False,
        filtered_row_count=len(df),
        total_row_count=len(df),
    )
    return JSONResponse(content=sanitize_for_json(response.model_dump()))


@router.get(
    "/chart-recommendations",
    summary="Get automatic chart recommendations",
)
async def get_chart_recommendations(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """Retrieve up to 6 recommended charts based on dataset distributions and schema."""
    _, df = _get_dataset_and_df(dataset_id, session_id=x_session_id)
    rec_charts = dashboard_service.recommend_charts(df, max_charts=6)
    return JSONResponse(content=sanitize_for_json([c.model_dump() for c in rec_charts]))


@router.post(
    "/charts/generate",
    summary="Generate custom chart via interactive chart explorer",
)
async def generate_custom_chart(
    dataset_id: str,
    req: CustomChartRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Build, validate, and compute a custom Plotly chart dynamically from user selections.
    Guarantees safety by preventing arbitrary expressions or SQL injection.
    """
    _, df = _get_dataset_and_df(dataset_id, session_id=x_session_id)
    chart = dashboard_service.generate_custom_chart(df, req)
    return JSONResponse(content=sanitize_for_json(chart.model_dump()))


@router.post(
    "/dashboard/filter",
    summary="Apply interactive filters and re-calculate KPIs and charts",
)
async def apply_dashboard_filters(
    dataset_id: str,
    req: FilterDashboardRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Apply categorical, numeric range, and datetime range filters.
    Returns dynamically re-calculated KPIs, filter options, and updated charts.
    """
    detail, df = _get_dataset_and_df(dataset_id, session_id=x_session_id)

    filtered_df = dashboard_service.apply_filters(df, req.filters)
    kpis = dashboard_service.calculate_kpis(filtered_df, selected_col=req.selected_numeric_column)
    filter_opts = dashboard_service.get_filter_options(df)  # retain full domain bounds
    rec_charts = dashboard_service.recommend_charts(filtered_df, max_charts=6)

    available_cols = [
        ColumnInfo(name=str(col), data_type=infer_column_type(df[col]))
        for col in df.columns
    ]

    response = DashboardResponse(
        dataset_id=dataset_id,
        filename=detail.overview.filename,
        kpis=kpis,
        filter_options=filter_opts,
        active_filters=req.filters,
        recommended_charts=rec_charts,
        available_columns=available_cols,
        is_filtered=len(req.filters) > 0,
        filtered_row_count=len(filtered_df),
        total_row_count=len(df),
    )
    return JSONResponse(content=sanitize_for_json(response.model_dump()))


@router.post(
    "/dashboard/drilldown",
    summary="Drill down into a specific category segment",
    response_model=DrillDownResponse,
)
async def get_category_drilldown(
    dataset_id: str,
    req: DrillDownRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Drill down into a clicked category segment to inspect matching records
    and localized segment statistics without transferring entire dataset.
    """
    _, df = _get_dataset_and_df(dataset_id, session_id=x_session_id)
    drilldown = dashboard_service.get_drill_down_data(df, req)
    return JSONResponse(content=sanitize_for_json(drilldown.model_dump()))

