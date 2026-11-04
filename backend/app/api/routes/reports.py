from datetime import datetime, timezone
import io
import logging
from pathlib import Path
import re
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.json_encoder import sanitize_for_json
from app.models.reports import (
    ExecutiveReportData,
    ReportConfigRequest,
)
from app.services.dataset_storage import dataset_storage
from app.services.reports import (
    ExcelReportBuilder,
    PdfReportBuilder,
    ReportAssemblyService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/datasets/{dataset_id}/reports",
    tags=["Executive Reports & Business Intelligence"],
)


def _build_download_filename(title: str, dataset_name: str, ext: str) -> str:
    """Builds safe, sanitized download filenames preventing path traversal."""
    clean_title = re.sub(r"[^a-zA-Z0-9_\-]", "_", title).strip("_")
    clean_ds = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(dataset_name).stem).strip("_")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = f"{clean_title[:30]}_{clean_ds[:25]}_{timestamp}"
    base = re.sub(r"_+", "_", base).strip("_")
    if not base:
        base = f"Executive_Report_{timestamp}"
    return f"{base}.{ext.lstrip('.')}"


@router.post(
    "/generate",
    response_model=ExecutiveReportData,
    summary="Generate complete executive intelligence report preview",
    description="Assembles verified analytics across Phases 1-4.4 into a structured executive report data model.",
)
async def generate_report(
    dataset_id: str,
    config: Optional[ReportConfigRequest] = None,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> ExecutiveReportData:
    """
    Generate an executive intelligence report preview JSON response.
    Respects selected sections and chart toggles while maintaining single-snapshot consistency.
    """
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    cfg = config or ReportConfigRequest()
    try:
        report_data = await ReportAssemblyService.assemble_report(
            dataset_id=dataset_id,
            config=cfg,
            force_refresh=False,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=sanitize_for_json(report_data.model_dump()),
        )
    except ValueError as ve:
        err_msg = str(ve)
        if "snapshot changed" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dataset snapshot changed during report assembly. Please refresh and try again.",
            )
        if "not found" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate executive report for '{dataset_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assemble executive report due to an internal server error.",
        )


@router.post(
    "/export/pdf",
    summary="Export executive intelligence report as formatted A4 PDF",
    description="Renders a multi-page executive PDF using Playwright Chromium with embedded vector charts.",
)
async def export_pdf_report(
    dataset_id: str,
    config: Optional[ReportConfigRequest] = None,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Generate and stream an executive A4 PDF report download.
    Renders vector SVG charts, branded cover page, and running headers/footers with page numbers.
    """
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    cfg = config or ReportConfigRequest()
    try:
        report_data = await ReportAssemblyService.assemble_report(
            dataset_id=dataset_id,
            config=cfg,
            force_refresh=False,
        )
        pdf_bytes = await PdfReportBuilder.generate_pdf_bytes(report_data)

        if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
            raise ValueError("PDF generator produced invalid or empty PDF bytes.")

        filename = _build_download_filename(cfg.title, detail.overview.filename, "pdf")
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        }
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers=headers,
        )
    except ValueError as ve:
        err_msg = str(ve)
        if "snapshot changed" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dataset snapshot changed during report assembly. Please refresh and try again.",
            )
        if "not found" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )
    except RuntimeError as re:
        logger.error(f"PDF rendering error for '{dataset_id}': {re}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation engine encountered an internal error. Please check server browser configuration.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error exporting PDF for '{dataset_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report due to an internal server error.",
        )


@router.post(
    "/export/excel",
    summary="Export executive intelligence report as formatted multi-sheet Excel workbook",
    description="Generates an eight-sheet styled Excel workbook using openpyxl.",
)
async def export_excel_report(
    dataset_id: str,
    config: Optional[ReportConfigRequest] = None,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Generate and stream an executive multi-sheet Excel (.xlsx) workbook download.
    Contains exactly 8 styled worksheets with frozen panes, auto-fit column widths, and formula injection escaping.
    """
    detail = dataset_storage.get_authorized_dataset(dataset_id, session_id=x_session_id)

    cfg = config or ReportConfigRequest()
    try:
        report_data = await ReportAssemblyService.assemble_report(
            dataset_id=dataset_id,
            config=cfg,
            force_refresh=False,
        )
        excel_buffer = ExcelReportBuilder.generate_excel_bytes(report_data)
        excel_bytes = excel_buffer.getvalue()

        if not excel_bytes or len(excel_bytes) < 1000:
            raise ValueError("Excel generator produced invalid or empty spreadsheet bytes.")

        filename = _build_download_filename(cfg.title, detail.overview.filename, "xlsx")
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(excel_bytes)),
        }
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    except ValueError as ve:
        err_msg = str(ve)
        if "snapshot changed" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dataset snapshot changed during report assembly. Please refresh and try again.",
            )
        if "not found" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error exporting Excel for '{dataset_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Excel report due to an internal server error.",
        )

