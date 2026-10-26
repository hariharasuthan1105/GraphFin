from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from ...schemas import graph_explorer as s
from ...services.graph_explorer_service import GraphExplorerService, get_graph_explorer
from ...core.exceptions import ErrorResponse
from ...services.research_catalog_service import ResearchError


class PrivateGraphRoute(APIRoute):
    def get_route_handler(self):
        original=super().get_route_handler()
        async def handler(request):
            try:
                result=await original(request)
            except ResearchError as exc:
                result=JSONResponse({'error':exc.error_code,'message':exc.message,'details':exc.details},status_code=exc.status_code)
            except RequestValidationError as exc:
                # Do not forward capability-bearing header inputs to the global
                # validation logger. Preserve the public validation envelope.
                details=[{'loc':[str(x) for x in e['loc']],'msg':e['msg'],'type':e['type']} for e in exc.errors()]
                result=JSONResponse({'error':'VALIDATION_ERROR','message':'Graph query validation failed.','details':details},status_code=422)
            result.headers['Cache-Control']='private, no-store'
            result.headers['Vary']='X-Graph-Session'
            return result
        return handler

router=APIRouter(prefix='/graph-explorer',route_class=PrivateGraphRoute,tags=['Bounded Research Graph'],responses={c:{'model':ErrorResponse} for c in (403,409,410,422,429,503)})
Service=Annotated[GraphExplorerService,Depends(get_graph_explorer)]
Dataset=Literal['ibm-5k','ibm-50k','paysim']


def private(response):
    response.headers['Cache-Control']='private, no-store'
    response.headers['Vary']='X-Graph-Session'


@router.get('/catalog',response_model=s.GraphCatalog)
def catalog(service:Service,response:Response):
    private(response);return service.catalog_info()


@router.get('/session',response_model=s.GraphSession)
def session(service:Service,response:Response,dataset_id:Dataset,experiment_id:Annotated[str,Query(pattern=r'^baseline-(5k|50k)-(E[0-5]|E6_BASE)-s42-m42$')],
            version:Literal['canonical-directed-amount-v1']='canonical-directed-amount-v1',rank:Annotated[int|None,Query(ge=1,le=20)]=None):
    private(response);return service.open_session(dataset_id,experiment_id,rank)


@router.get('/neighborhood',response_model=s.GraphNeighborhood)
def neighborhood(service:Service,response:Response,x_graph_session:Annotated[str,Header(pattern=r'^[A-Za-z0-9_-]{32}$')],
                 focus_ref:Annotated[str,Query(pattern=r'^node_[a-f0-9]{32}$')],depth:Annotated[int,Query(ge=1,le=2)]=1,
                 direction:Literal['both','incoming','outgoing']='both',max_nodes:Annotated[int,Query(ge=1,le=250)]=100,
                 max_edges:Annotated[int,Query(ge=0,le=500)]=250,min_count:Annotated[int,Query(ge=1,le=1000000)]=1,
                 min_amount:Annotated[float,Query(ge=0,le=1e15,allow_inf_nan=False)]=0,
                 start:Annotated[float|None,Query(allow_inf_nan=False)]=None,end:Annotated[float|None,Query(allow_inf_nan=False)]=None):
    private(response)
    return service.neighborhood(x_graph_session,focus_ref,depth,direction,max_nodes,max_edges,min_count,min_amount,start,end)
