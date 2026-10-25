"""GET-only public research projections; never executes research work."""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query
from ...schemas import research as s
from ...core.exceptions import ErrorResponse
from ...services.research_catalog_service import ResearchCatalogService, get_research_catalog

router=APIRouter(prefix='/research',tags=['Read-only Research'],responses={
    code:{'model':ErrorResponse} for code in (404,409,422,503)})
Service=Annotated[ResearchCatalogService,Depends(get_research_catalog)]
PageNumber=Annotated[int,Query(ge=1,le=1000)]
PageSize=Annotated[int,Query(ge=1,le=100)]
DatasetFilter=Literal['ibm-5k','ibm-50k','paysim','ibm-historical']
MethodFilter=Literal['E0','E1','E2','E3','E4','E5','E6_BASE','E6_CREST','E0-E4']

def page(items,number,size,status='verified',provenance='partially_verified'):
    return dict(status=status,provenance_status=provenance,items=items[(number-1)*size:number*size],
        total=len(items),page=number,page_size=size)

@router.get('/overview',response_model=s.Overview)
def overview(service:Service):return service.overview()

@router.get('/datasets',response_model=s.Page[s.Dataset])
def datasets(service:Service):return page(service.datasets(),1,3,provenance='unresolved')

@router.get('/datasets/{dataset_id}',response_model=s.Dataset)
def dataset(dataset_id:str,service:Service):return service.dataset(dataset_id)

@router.get('/experiments',response_model=s.Page[s.Experiment])
def experiments(service:Service,page_number:PageNumber=1,page_size:PageSize=25,
        dataset_id:DatasetFilter|None=None,tier:Literal['5k','50k','historical']|None=None,
        method:MethodFilter|None=None,version:Annotated[str|None,Query(max_length=100)]=None,
        split_seed:Annotated[int|None,Query(ge=0,le=2**32-1)]=None,
        model_seed:Annotated[int|None,Query(ge=0,le=2**32-1)]=None):
    return page(service.experiments(dataset_id,tier,method,version,split_seed,model_seed),page_number,page_size)

@router.get('/experiments/{experiment_id}',response_model=s.Experiment)
def experiment(experiment_id:str,service:Service):return service.experiment(experiment_id)

@router.get('/experiments/{experiment_id}/metrics',response_model=s.Experiment)
def metrics(experiment_id:str,service:Service):return service.metric_detail(experiment_id)

@router.get('/experiments/{experiment_id}/rankings',response_model=s.Page[s.Ranking])
def rankings(experiment_id:str,service:Service,page_number:PageNumber=1,page_size:PageSize=25,
        sort:Literal['score_desc','score_asc']='score_desc'):
    return service.rankings(experiment_id,page_number,page_size,sort)

@router.get('/experiments/{experiment_id}/provenance',response_model=s.Experiment)
def provenance(experiment_id:str,service:Service):
    return service.experiment(experiment_id).model_copy(update={'metrics':None})

@router.get('/comparisons',response_model=s.Comparison)
def comparisons(service:Service,experiment_id:Annotated[list[str],Query(min_length=2,max_length=12)],
        metric:s.MetricName='average_precision'):
    return service.compare(experiment_id,metric)

@router.get('/reproducibility',response_model=s.Reproducibility)
def reproducibility(service:Service):return service.reproducibility()

@router.get('/model-seeds',response_model=s.ModelSeeds)
def model_seeds(service:Service,dataset_id:Literal['ibm-5k','ibm-50k']|None=None,
        method:Literal['E1','E4']|None=None):return service.model_seeds(dataset_id,method)

@router.get('/diagnostics',response_model=s.Page[s.Diagnostic])
def diagnostics(service:Service,page_number:PageNumber=1,page_size:PageSize=25):
    items=service.diagnostics()
    return page(items,page_number,page_size,status='exploratory' if items else 'unavailable')

@router.get('/diagnostics/{diagnostic_id}',response_model=s.Diagnostic)
def diagnostic(diagnostic_id:str,service:Service):return service.diagnostic(diagnostic_id)

@router.get('/limitations',response_model=s.Limitations)
def limitations(service:Service):return service.limitations()
