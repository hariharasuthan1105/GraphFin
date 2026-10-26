"""Private indexed topology -> short-lived, bounded public graph lenses."""
from collections import OrderedDict, deque
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from hashlib import sha256
import hmac
import json
import math
from pathlib import Path
import re
import secrets
import sqlite3
from threading import RLock, BoundedSemaphore
import time

from ..core.config import PROJECT_ROOT
from ..schemas import graph_explorer as s
from .graph_explorer_index import VERSION, INDEX_SCHEMA, file_hash, canonical
from .research_catalog_service import ResearchError, get_research_catalog, canonical_hash, guarded

LIMITATIONS = [
    'Observed synthetic dataset relationships are not verified real-world wrongdoing.',
    'IBM account-label lineage is partially verified; PaySim label provenance remains unresolved.',
    'CREST detection and explanation superiority are unsupported; original full E6 evaluation remains incomplete.',
    'Node statistics and reciprocity refer to the full source snapshot, not the displayed filtered subset.',
    'Filters query topology only; frozen anomaly scores are never recomputed. Temporal subwindows suppress score/diagnostic annotations.',
    'The fixed approved disclosure lens is not a random sample or the complete dataset.',
]
AMOUNT_UNIT = 'canonical dataset units; currency validity not independently established'
TIME_SEMANTICS = 'supplied synthetic timestamps interpreted as UTC; full observed snapshot'
# Frozen Phase 6A E4 model identity recorded in 06A_explanation_validation.md.
DIAGNOSTIC_MODEL_SHA256 = '81758da48c8de36f7d3ee08e5a00881ef7d6beaf14877ad758b9e4422f02a298'


def diagnostic_matches(diagnostic, experiment, metadata):
    p=diagnostic.get('provenance',{})
    try:
        cutoff=datetime.fromisoformat(p['cutoff'].replace('Z','+00:00'))
        if cutoff.tzinfo is None:cutoff=cutoff.replace(tzinfo=timezone.utc)
        return (p.get('algorithm')=='phase6a-explanation-diagnostics-v1'
            and p.get('dataset_sha256')==metadata['dataset_sha256']
            and p.get('heldout_ids_sha256')==experiment.test_sha256
            and experiment.version=='isolation-forest-raw-v2'
            and p.get('model_sha256')==DIAGNOSTIC_MODEL_SHA256
            and p.get('feature_count')==len(experiment.feature_names)==19
            and p.get('split_seed')==experiment.split_seed==42
            and p.get('model_seed')==experiment.model_seed==42
            and p.get('graph_seed')==42 and p.get('labels_used') is False
            and cutoff.timestamp()==metadata['time_end'])
    except (KeyError,TypeError,ValueError,AttributeError):return False



def safe_graph(fn):
    @wraps(fn)
    @guarded
    def wrapped(*args,**kwargs):
        try:return fn(*args,**kwargs)
        except (sqlite3.Error,OSError):
            raise ResearchError('TOPOLOGY_UNAVAILABLE','Verified graph topology is unavailable or exceeded its query budget.') from None
    return wrapped


def bounded_request(fn):
    @wraps(fn)
    def wrapped(self,*args,**kwargs):
        if not self.slots.acquire(blocking=False):
            raise ResearchError('GRAPH_BUSY','Graph service is busy. Retry shortly.',429)
        try:return fn(self,*args,**kwargs)
        finally:self.slots.release()
    return wrapped


@dataclass
class Session:
    dataset_id: str
    meta: dict
    experiment: object
    scores: dict
    ranks: dict
    diagnostics: dict
    expires: float
    secret: bytes = field(default_factory=lambda:secrets.token_bytes(32))
    refs: dict = field(default_factory=dict)
    reverse: dict = field(default_factory=dict)
    queries: int = 20


class GraphExplorerService:
    def __init__(self, root=None, catalog=None, clock=time.monotonic):
        self.root=Path(root) if root is not None else PROJECT_ROOT/'data/results/v3/phase9-topology-v1'
        self.catalog=catalog or get_research_catalog()
        self.clock=clock;self.sessions=OrderedDict();self.lock=RLock();self.slots=BoundedSemaphore(4)

    def _path(self,name):
        if name not in ('manifest.json','ibm-5k.sqlite','ibm-50k.sqlite'):
            raise ResearchError('UNSAFE_TOPOLOGY_PATH','Topology path is not approved.')
        p=self.root/name
        for part in (p,*p.parents):
            if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):
                raise ResearchError('UNSAFE_TOPOLOGY_PATH','Linked topology paths are not supported.')
        return p

    def _meta(self,dataset_id):
        if dataset_id not in ('ibm-5k','ibm-50k'):
            raise ResearchError('TOPOLOGY_UNAVAILABLE','This dataset has no approved topology index.')
        p=self._path('manifest.json')
        with p.open('rb') as f:raw=f.read(1024*1024+1)
        if len(raw)>1024*1024:raise ValueError('Manifest read limit')
        manifest=json.loads(raw)
        if manifest['schema_version']!='graphfin-topology-bundle-v1':raise ValueError('Bundle version')
        m=manifest['datasets'][dataset_id]
        if m['schema_version']!=INDEX_SCHEMA or m['version']!=VERSION or m['dataset_id']!=dataset_id:
            raise ValueError('Index identity')
        expected=self.catalog._read('protocol')['datasets'][dataset_id[4:]]['transactions_sha256']
        if m['dataset_sha256']!=expected:raise ResearchError('GRAPH_DATASET_MISMATCH','Graph source identity differs from the research dataset.')
        if not isinstance(m['approved_nodes'],list) or not 0<len(m['approved_nodes'])<=600 or len(set(m['approved_nodes']))!=len(m['approved_nodes']):
            raise ValueError('Disclosure scope')
        if sha256(canonical(sorted(m['approved_nodes']))).hexdigest()!=m['scope_identity']:
            raise ResearchError('GRAPH_SCOPE_MISMATCH','Graph disclosure scope integrity check failed.')
        if len(m['anchors'])>30 or any(x['account'] not in m['approved_nodes'] for x in m['anchors']):raise ValueError('Anchors')
        db=self._path(dataset_id+'.sqlite')
        if db.stat().st_size>250*1024*1024:raise ValueError('Index size limit')
        if file_hash(db)!=m['index_sha256']:
            raise ResearchError('GRAPH_CHECKSUM_MISMATCH','Graph index checksum mismatch.')
        if m['graph_id']!=dataset_id+'-'+m['index_sha256'][:20]:raise ValueError('Graph ID')
        m['snapshot_identity']=sha256(canonical({'dataset_sha256':expected,'time_start':m['time_start'],'time_end':m['time_end'],'version':VERSION})).hexdigest()
        return m

    def _db(self,dataset_id):
        db=sqlite3.connect(self._path(dataset_id+'.sqlite').resolve().as_uri()+'?mode=ro&immutable=1',uri=True,timeout=.2)
        db.row_factory=sqlite3.Row
        deadline=time.perf_counter()+1.5
        db.set_progress_handler(lambda:int(time.perf_counter()>deadline),1000)
        db.execute('PRAGMA query_only=ON')
        return db

    def _experiment(self,row):
        return s.GraphExperiment(experiment_id=row.experiment_id,method=row.method,version=row.version,split_seed=row.split_seed,model_seed=row.model_seed)

    def _dataset(self,dataset_id):
        ds=self.catalog.dataset(dataset_id)
        m=self._meta(dataset_id)
        experiments=self.catalog.experiments(dataset_id=dataset_id,split_seed=42,model_seed=42)
        return s.GraphDataset(dataset_id=dataset_id,name=ds.name,tier=ds.tier,status='verified',provenance_status='partially_verified',reason=None,
            graph_id=m['graph_id'],version=VERSION,dataset_sha256=m['dataset_sha256'],index_sha256=m['index_sha256'],snapshot_identity=m['snapshot_identity'],
            time_start=m['time_start'],time_end=m['time_end'],time_semantics=TIME_SEMANTICS,amount_unit=AMOUNT_UNIT,
            total_nodes=m['total_nodes'],total_edges=m['total_edges'],approved_scope_nodes=len(m['approved_nodes']),
            experiments=[self._experiment(x) for x in experiments if x.status=='verified'])

    @safe_graph
    @bounded_request
    def catalog_info(self):
        datasets=[]
        for dataset_id in ('ibm-5k','ibm-50k','paysim'):
            try:datasets.append(self._dataset(dataset_id))
            except ResearchError as e:
                datasets.append(s.GraphDataset(dataset_id=dataset_id,name={'ibm-5k':'IBM AML 5k','ibm-50k':'IBM AML 50k','paysim':'PaySim'}[dataset_id],tier=dataset_id[4:] if dataset_id.startswith('ibm-') else 'supplied',
                    status='unavailable',provenance_status='unresolved' if dataset_id=='paysim' else 'partially_verified',reason=e.error_code,
                    graph_id=None,version=VERSION,dataset_sha256=None,index_sha256=None,snapshot_identity=None,time_start=None,time_end=None,
                    time_semantics=TIME_SEMANTICS,amount_unit=AMOUNT_UNIT,total_nodes=None,total_edges=None,approved_scope_nodes=0,experiments=[]))
            except OSError:
                datasets.append(s.GraphDataset(dataset_id=dataset_id,name=dataset_id,tier=dataset_id[4:],status='unavailable',provenance_status='partially_verified',reason='TOPOLOGY_UNAVAILABLE',graph_id=None,version=VERSION,dataset_sha256=None,index_sha256=None,snapshot_identity=None,time_start=None,time_end=None,time_semantics=TIME_SEMANTICS,amount_unit=AMOUNT_UNIT,total_nodes=None,total_edges=None,approved_scope_nodes=0,experiments=[]))
        return s.GraphCatalog(datasets=datasets,limitations=LIMITATIONS)

    def _grant(self,state,account):
        if account not in state.reverse:
            if len(state.reverse)>=600:raise ResearchError('GRAPH_DISCLOSURE_LIMIT','Session node disclosure limit reached.',429)
            ref='node_'+hmac.new(state.secret,account.encode(),sha256).hexdigest()[:32]
            state.reverse[account]=ref;state.refs[ref]=account
        return state.reverse[account]

    @safe_graph
    @bounded_request
    def open_session(self,dataset_id,experiment_id,rank=None):
        dataset=self._dataset(dataset_id);m=self._meta(dataset_id)
        row=self.catalog.metric_detail(experiment_id)
        if row.dataset_id!=dataset_id or row.split_seed!=42 or row.model_seed!=42 or row.dataset_sha256!=m['dataset_sha256']:
            raise ResearchError('INCOMPATIBLE_GRAPH_EXPERIMENT','Graph requires the same dataset and supported split42/model42 experiment.',409)
        label_hash=self.catalog._read('protocol')['datasets'][dataset_id[4:]]['labels_sha256']
        if row.label_sha256!=label_hash:raise ResearchError('INCOMPATIBLE_GRAPH_EXPERIMENT','Graph label identity differs from the experiment.',409)
        scores=self.catalog._read('scores-'+row.tier+'-42')[row.method]
        if canonical_hash(sorted(scores))!=row.test_sha256 or len(scores)!=row.metrics.count:
            raise ResearchError('POPULATION_MISMATCH','Saved graph annotation scores do not match held-out membership.')
        if any(not math.isfinite(v) for v in scores.values()):raise ValueError('Nonfinite score')
        ordered=sorted(scores,key=lambda u:(-scores[u],u));ranks={u:i+1 for i,u in enumerate(ordered)}
        diagnostics={}
        if dataset_id=='ibm-5k' and row.method=='E4':
            for i,d in enumerate(self.catalog._read('diagnostics')):
                u=d['account_id']
                if diagnostic_matches(d,row,m) and u in scores and abs(scores[u]-d['original_score'])<=1e-12:
                    diagnostics.setdefault(u,[]).append(f'crest-{i:03d}')
        focus=m['anchors'][0]['account']
        if rank is not None:
            if not 1<=rank<=min(20,len(ordered)):raise ResearchError('GRAPH_RANK_OUTSIDE_SCOPE','Only the approved top20 descending ranks can open a graph.',409)
            focus=ordered[rank-1]
            if focus not in m['approved_nodes']:raise ResearchError('GRAPH_RANK_OUTSIDE_SCOPE','Ranked account lies outside the approved disclosure lens.',409)
        state=Session(dataset_id,m,row,scores,ranks,diagnostics,self.clock()+600)
        with closing(self._db(dataset_id)) as db:
            placeholders=','.join('?' for _ in m['approved_nodes'])
            dense=db.execute(f'SELECT id FROM nodes WHERE id IN ({placeholders}) ORDER BY (in_degree+out_degree) DESC,id LIMIT 1',m['approved_nodes']).fetchone()['id']
            sparse=db.execute(f'SELECT id FROM nodes WHERE id IN ({placeholders}) AND neighbors>0 ORDER BY (in_degree+out_degree),id LIMIT 1',m['approved_nodes']).fetchone()['id']
        anchors=[]
        for x in m['anchors'][:30]:
            role=x['role']
            if x['account']==dense and 'high-degree' not in role:role+=' / high-degree anchor'
            if x['account']==sparse and 'low-degree' not in role:role+=' / low-degree anchor'
            if x['account'] in diagnostics:role+=' / compatible saved diagnostic'
            anchors.append(s.GraphAnchor(node_ref=self._grant(state,x['account']),display_id=self.catalog._token(x['account'],dataset_id),role=role))
        focus_ref=self._grant(state,focus)
        token=secrets.token_urlsafe(24)
        with self.lock:
            for key in list(self.sessions):
                if self.sessions[key].expires<=self.clock():del self.sessions[key]
            self.sessions[token]=state
            while len(self.sessions)>16:self.sessions.popitem(last=False)
        return s.GraphSession(session_id=token,expires_in_seconds=600,query_budget=20,dataset=dataset,experiment=self._experiment(row),anchors=anchors,focus_ref=focus_ref)

    @safe_graph
    @bounded_request
    def neighborhood(self,session_id,focus_ref,depth=1,direction='both',max_nodes=100,max_edges=250,min_count=1,min_amount=0,start=None,end=None):
        started=time.perf_counter()
        with self.lock:
            state=self.sessions.get(session_id)
            if state is None or state.expires<=self.clock():
                self.sessions.pop(session_id,None)
                raise ResearchError('GRAPH_SESSION_EXPIRED','Graph session expired or belongs to another worker. Open a new lens.',410)
            if focus_ref not in state.refs:
                raise ResearchError('GRAPH_REFERENCE_DENIED','Node reference was not granted to this session.',403)
            if state.queries<=0:raise ResearchError('GRAPH_QUERY_LIMIT','Session query budget reached. Open a new approved lens.',429)
            # Route validation is repeated for direct service callers/tests.
            if depth not in (1,2) or direction not in ('both','incoming','outgoing') or not 1<=max_nodes<=250 or not 0<=max_edges<=500 or not 1<=min_count<=1000000 or not math.isfinite(min_amount) or not 0<=min_amount<=1e15:
                raise ResearchError('GRAPH_QUERY_INVALID','Graph query bounds are invalid.',422)
            m=self._meta(state.dataset_id)
            if m['index_sha256']!=state.meta['index_sha256']:raise ResearchError('GRAPH_SNAPSHOT_CHANGED','Graph snapshot changed. Open a new lens.',410)
            begin=m['time_start'] if start is None else start;finish=m['time_end'] if end is None else end
            if not math.isfinite(begin) or not math.isfinite(finish) or not m['time_start']<=begin<=finish<=m['time_end']:
                raise ResearchError('GRAPH_TIME_INVALID','Time window must stay within the verified source snapshot.',422)
            temporal=begin!=m['time_start'] or finish!=m['time_end']
            state.queries-=1
            scope=set(m['approved_nodes']);focus=state.refs[focus_ref]
            reasons=set(['approved_disclosure_scope'] if len(scope)<m['total_nodes'] else [])
            selected={focus};queue=deque([(focus,0)]);edges={};new_grants=0
            placeholders=','.join('?' for _ in scope);scope_args=sorted(scope)
            with closing(self._db(state.dataset_id)) as db:
                while queue:
                    cur,level=queue.popleft()
                    if level>=depth:continue
                    side={'incoming':'t=?','outgoing':'s=?','both':'(s=? OR t=?)'}[direction]
                    args=[cur,cur] if direction=='both' else [cur]
                    other='CASE WHEN s=? THEN t ELSE s END'
                    if temporal:
                        sql=f'''SELECT s,t,SUM(amount) amount,COUNT(*) cnt,MIN(ts) first,MAX(ts) last FROM events
                          WHERE {side} AND {other} IN ({placeholders}) AND ts>=? AND ts<=?
                          GROUP BY s,t HAVING COUNT(*)>=? AND SUM(amount)>=? ORDER BY s,t LIMIT 502'''
                        values=[*args,cur,*scope_args,begin,finish,min_count,min_amount]
                    else:
                        sql=f'''SELECT * FROM edges WHERE {side} AND {other} IN ({placeholders})
                          AND cnt>=? AND amount>=? ORDER BY s,t LIMIT 502'''
                        values=[*args,cur,*scope_args,min_count,min_amount]
                    found=db.execute(sql,values).fetchall()
                    if len(found)>501:reasons.add('adjacency_scan_limit')
                    for edge in found[:501]:
                        peer=edge['t'] if edge['s']==cur else edge['s']
                        if peer not in selected:
                            if len(selected)>=max_nodes:reasons.add('node_limit');continue
                            if peer not in state.reverse and len(state.reverse)+new_grants>=600:
                                reasons.add('session_disclosure_limit');continue
                            if peer not in state.reverse:new_grants+=1
                            selected.add(peer);queue.append((peer,level+1))
                        edges[edge['s'],edge['t']]=dict(edge)
                        if len(edges)>500:
                            reasons.add('edge_limit');break
                    if len(edges)>500:break
                ordered_edges=sorted(edges.values(),key=lambda e:(0 if focus in (e['s'],e['t']) else 1,e['s'],e['t']))
                if len(ordered_edges)>max_edges:reasons.add('edge_limit')
                ordered_edges=ordered_edges[:max_edges]
                nodes=[]
                for u in sorted(selected):
                    ref=self._grant(state,u);row=db.execute('SELECT * FROM nodes WHERE id=?',(u,)).fetchone()
                    status='unavailable_temporal' if temporal else 'available' if u in state.scores else 'unavailable_population'
                    diag=[] if temporal else state.diagnostics.get(u,[])
                    nodes.append(s.ExplorerNode(node_ref=ref,display_id=self.catalog._token(u,state.dataset_id),node_type='account',
                        in_degree=row['in_degree'],out_degree=row['out_degree'],neighbors=row['neighbors'],received_amount=row['received'],sent_amount=row['sent'],
                        ranking_status=status,anomaly_score=state.scores.get(u) if status=='available' else None,saved_rank=state.ranks.get(u) if status=='available' else None,
                        diagnostic_ids=diag,diagnostic_status='compatible saved evidence' if diag else 'Unavailable: no compatible saved diagnostic for this experiment/snapshot.'))
                public_edges=[]
                for e in ordered_edges:
                    reverse=db.execute('SELECT 1 FROM edges WHERE s=? AND t=?',(e['t'],e['s'])).fetchone() is not None
                    edge_ref='edge_'+hmac.new(state.secret,(e['s']+'\0'+e['t']).encode(),sha256).hexdigest()[:32]
                    public_edges.append(s.ExplorerEdge(edge_ref=edge_ref,source_ref=state.reverse[e['s']],target_ref=state.reverse[e['t']],direction='sender_to_receiver',
                        transaction_count=e['cnt'],amount=e['amount'],first_time=datetime.fromtimestamp(e['first'],timezone.utc).isoformat(),last_time=datetime.fromtimestamp(e['last'],timezone.utc).isoformat(),reciprocal_in_snapshot=reverse))
            result=s.GraphNeighborhood(schema_version='graphfin-neighborhood-v1',graph_id=m['graph_id'],dataset_id=state.dataset_id,tier=state.experiment.tier,version=VERSION,
                snapshot_identity=m['snapshot_identity'],dataset_sha256=m['dataset_sha256'],index_sha256=m['index_sha256'],status='verified',provenance_status='partially_verified',
                experiment=self._experiment(state.experiment),focus_ref=focus_ref,nodes=nodes,edges=public_edges,depth=depth,direction=direction,start=begin,end=finish,min_count=min_count,min_amount=min_amount,
                temporal_subset=temporal,scope_nodes=len(scope),max_nodes=max_nodes,max_edges=max_edges,truncated=bool(reasons),truncation_reasons=sorted(reasons),remaining_queries=state.queries,
                remaining_node_grants=600-len(state.reverse),query_seconds=time.perf_counter()-started,amount_unit=AMOUNT_UNIT,limitations=LIMITATIONS)
            if len(result.model_dump_json().encode())>512*1024:
                raise ResearchError('GRAPH_RESPONSE_LIMIT','Graph response exceeded its byte budget.')
            return result


graph_explorer_service=GraphExplorerService()


def get_graph_explorer():return graph_explorer_service
