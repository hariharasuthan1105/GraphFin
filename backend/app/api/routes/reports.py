"""
Report Generation Routes for GraphFin.
Provides publication-quality evaluation export in PDF, Word (DOCX), and CSV formats
for both official locked research benchmarks and user-uploaded custom datasets.
"""
from fastapi import APIRouter, Response, status

from ...core.logging import get_logger
from ...schemas.report import ReportGenerateRequest
from ...services.report_service import report_service

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports & Exports"])


@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    summary="Generate Evaluation Report",
    description=(
        "Generates publication-quality evaluation reports in PDF, Word (.docx), or CSV format. "
        "Supports both 'official' locked research benchmarks (read-only) and 'custom' live evaluation "
        "on user-uploaded datasets."
    ),
)
async def generate_evaluation_report(req: ReportGenerateRequest):
    """Generate evaluation report file for official or custom dataset evaluation."""
    logger.info(
        f"Generating report: source='{req.source}', format='{req.format}', "
        f"dataset_id='{req.dataset_id}', experiment='{req.experiment_label}'"
    )
    content, media_type, filename = report_service.generate_report(
        source=req.source,
        format_type=req.format,
        dataset_id=req.dataset_id,
        experiment_label=req.experiment_label,
        split_label=req.split_label,
    )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
