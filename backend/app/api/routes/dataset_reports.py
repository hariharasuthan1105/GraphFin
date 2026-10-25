"""Read-only institutional dataset exports; no client-supplied paths or jobs."""
from hashlib import sha256
from threading import BoundedSemaphore
from typing import Annotated
from fastapi import APIRouter, Depends, Response
from ...services.research_catalog_service import ResearchCatalogService, get_research_catalog, ResearchError
from ...services.dataset_report_service import dataset_report_service
from ...core.exceptions import ErrorResponse

router = APIRouter(prefix='/research-reports/datasets', tags=['Research PDF Reports'])
_slots = BoundedSemaphore(2)


@router.get('/{dataset_id}/report.pdf', response_class=Response,
            responses={200:{'content':{'application/pdf':{}},'description':'Institutional four-page dataset evidence report'},
                       **{code:{'model':ErrorResponse} for code in (404,429,503)}})
def dataset_pdf(dataset_id: str, catalog: Annotated[ResearchCatalogService, Depends(get_research_catalog)]):
    if not _slots.acquire(blocking=False):
        raise ResearchError('REPORT_BUSY', 'Report generation is busy. Please retry shortly.', 429)
    try:
        content = dataset_report_service.generate(dataset_id, catalog)
    finally:
        _slots.release()
    return Response(content, media_type='application/pdf', headers={
        'Content-Disposition':f'attachment; filename="GraphFin_{dataset_id}_dataset_report.pdf"',
        'Access-Control-Expose-Headers':'Content-Disposition', 'X-Content-Type-Options':'nosniff',
        'Cache-Control':'private, no-store', 'ETag':'"'+sha256(content).hexdigest()+'"',
    })
