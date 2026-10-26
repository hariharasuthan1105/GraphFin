"""Explicitly synthetic topology fixtures; real-source verification is separate."""
import hashlib
import json
from pathlib import Path
import sqlite3
from threading import BoundedSemaphore
from unittest.mock import patch
import pytest
from backend.tests.test_phase7_research_api import research
from backend.app.main import app
from backend.app.services.feature_service import CANONICAL_TRANSFER_FEATURES
from backend.app.services.graph_explorer_index import build_index, file_hash, canonical
from backend.app.services.graph_explorer_service import GraphExplorerService, get_graph_explorer, DIAGNOSTIC_MODEL_SHA256


@pytest.fixture
def lens(research,tmp_path):
    client,catalog,reg,values,persist,_,_=research
    source=tmp_path/'source.csv'
    source.write_text('transaction_id,sender_id,receiver_id,amount,timestamp\n'+
      'TX1,SECRET_A,SECRET_B,5,2020-01-01T00:00:00\n'+
      'TX2,SECRET_A,SECRET_B,7,2020-01-02T00:00:00\n'+
      'TX3,SECRET_B,SECRET_A,3,2020-01-03T00:00:00\n'+
      'TX4,SECRET_B,SECRET_C,4,2020-01-04T00:00:00\n'+
      'TX5,SECRET_C,SECRET_D,8,2020-01-05T00:00:00\n'+
      'TX6,SECRET_D,SECRET_E,1,2020-01-06T00:00:00\n'+
      'TX7,SECRET_C,SECRET_C,6,2020-01-07T00:00:00\n'+
      'TX8,SECRET_E,SECRET_A,0,2020-01-08T00:00:00\n',encoding='utf-8')
    root=tmp_path/'topology';root.mkdir();datasets={}
    for tier in ('5k','50k'):
        values['protocol']['datasets'][tier]['transactions_sha256']=file_hash(source)
        values['datasets'][0 if tier=='5k' else 1].update(active_accounts=5,label_rows=5,positive_accounts=1,negative_accounts=4,retained_rows=6,transaction_sha256=file_hash(source))
        datasets['ibm-'+tier]=build_index(source,root/('ibm-'+tier+'.sqlite'),'ibm-'+tier,file_hash(source),['SECRET_A','SECRET_B','SECRET_C'])
    next(c for c in values['configs'] if c['method']=='E4')['feature_names']=list(CANONICAL_TRANSFER_FEATURES)
    for row in values['rows']:
        if row['method']=='E4':row['version']='isolation-forest-raw-v2'
    values['diagnostics'][0]['original_score']=.9;values['diagnostics'][1]['original_score']=.5;persist()
    experiment=catalog.metric_detail('baseline-5k-E4-s42-m42')
    # Explicit synthetic fixture identity, never edits persisted research originals.
    assert len(experiment.feature_names)==19
    for diagnostic in values['diagnostics']:
        diagnostic['provenance']=dict(algorithm='phase6a-explanation-diagnostics-v1',
            dataset_sha256=file_hash(source),heldout_ids_sha256=experiment.test_sha256,
            model_sha256=DIAGNOSTIC_MODEL_SHA256,feature_count=19,split_seed=42,
            model_seed=42,graph_seed=42,labels_used=False,cutoff='2020-01-06T00:00:00+00:00')
    persist()

    manifest={'schema_version':'graphfin-topology-bundle-v1','datasets':datasets}
    (root/'manifest.json').write_text(json.dumps(manifest))
    clock=[100.];service=GraphExplorerService(root,catalog,lambda:clock[0]);app.dependency_overrides[get_graph_explorer]=lambda:service
    def opening(dataset='ibm-5k',method='E4',**params):
        return client.get('/api/v1/graph-explorer/session',params={'dataset_id':dataset,'experiment_id':f'baseline-{dataset[4:]}-{method}-s42-m42',**params})
    def neighborhood(session,**params):
        return client.get('/api/v1/graph-explorer/neighborhood',headers={'X-Graph-Session':session['session_id']},params={'focus_ref':session['focus_ref'],**params})
    yield client,service,manifest,root,clock,opening,neighborhood,research,source
    app.dependency_overrides.pop(get_graph_explorer,None)


def test_catalog_index_semantics(lens):
    c,g,m,root,_,opening,query,_,_=lens
    catalog=c.get('/api/v1/graph-explorer/catalog');assert catalog.status_code==200
    assert 'SECRET_' not in catalog.text
    assert [x['status'] for x in catalog.json()['datasets']]==['verified','verified','unavailable']
    assert m['datasets']['ibm-5k']['source_rows']==8 and m['datasets']['ibm-5k']['retained_rows']==6
    with sqlite3.connect(root/'ibm-5k.sqlite') as db:
        assert db.execute('SELECT cnt,amount FROM edges WHERE s="SECRET_A" AND t="SECRET_B"').fetchone()==(2,12.)
        assert db.execute('SELECT COUNT(*) FROM edges').fetchone()[0]==5
    session=opening().json();response=query(session);assert response.status_code==200
    assert 'SECRET_' not in response.text and 'TX1' not in response.text and str(root) not in response.text
    refs={n['display_id']:n['node_ref'] for n in response.json()['nodes']};assert len(refs)==2
    assert response.headers['cache-control']=='private, no-store'
    edges=response.json()['edges'];assert len(edges)==2 and all(e['direction']=='sender_to_receiver' for e in edges)
    assert sorted(e['amount'] for e in edges)==[3.,12.]
    assert all(e['reciprocal_in_snapshot'] for e in edges)


@pytest.mark.parametrize('direction,count',[('incoming',1),('outgoing',1),('both',2)])
def test_direction(lens,direction,count):
    s=lens[5]().json();data=lens[6](s,direction=direction).json();assert len(data['edges'])==count
    if direction=='incoming':assert data['edges'][0]['target_ref']==s['focus_ref']
    if direction=='outgoing':assert data['edges'][0]['source_ref']==s['focus_ref']


def test_depth_filters_and_limits(lens):
    s=lens[5]().json()
    one=lens[6](s).json();two=lens[6](s,depth=2).json();assert len(two['nodes'])==3>len(one['nodes'])
    clipped=lens[6](s,depth=2,max_nodes=1,max_edges=0).json();assert len(clipped['nodes'])==1 and not clipped['edges'];assert clipped['truncated']
    selected=lens[6](s,min_count=2).json();assert len(selected['edges'])==1 and selected['edges'][0]['transaction_count']==2
    empty=lens[6](s,min_amount=100).json();assert len(empty['nodes'])==1 and empty['edges']==[]


def test_temporal_aggregation_suppresses_scores(lens):
    s=lens[5]().json();base=lens[6](s).json();start=base['start']+86400
    view=lens[6](s,start=start,end=start).json();assert view['temporal_subset']
    assert len(view['edges'])==1 and view['edges'][0]['amount']==7 and view['edges'][0]['transaction_count']==1
    assert all(n['ranking_status']=='unavailable_temporal' and n['anomaly_score'] is None and n['diagnostic_ids']==[] for n in view['nodes'])
    assert lens[6](s,end=base['end']+1).status_code==422


def test_ranking_and_diagnostic_mapping(lens):
    c,g,_,_,_,opening,query,research,_=lens;s=opening(rank=1).json();view=query(s).json();focus=next(n for n in view['nodes'] if n['node_ref']==s['focus_ref'])
    ranking=c.get('/api/v1/research/experiments/baseline-5k-E4-s42-m42/rankings').json()['items'][0]
    assert focus['display_id']==ranking['account_token'] and focus['anomaly_score']==ranking['anomaly_score']==.9 and focus['saved_rank']==1
    assert focus['diagnostic_ids']==['crest-000']
    other=opening(method='E1').json();assert not any(n['diagnostic_ids'] for n in query(other).json()['nodes'])
    incompatible=c.get('/api/v1/graph-explorer/session',params={'dataset_id':'ibm-50k','experiment_id':'baseline-5k-E4-s42-m42'})
    assert incompatible.status_code==409


def test_training_account_has_no_fabricated_ranking(lens):
    s=lens[5]().json();node=next(a for a in s['anchors'] if 'low-degree' in a['role']);view=lens[6](s,focus_ref=node['node_ref']).json()
    focus=next(x for x in view['nodes'] if x['node_ref']==node['node_ref']);assert focus['anomaly_score'] is None and focus['saved_rank'] is None and focus['ranking_status']=='unavailable_population'


def test_session_identity_expiry_and_worker_boundaries(lens):
    _,g,_,_,clock,opening,query,_,_=lens
    a=opening().json();b=opening().json();assert a['session_id']!=b['session_id'] and a['focus_ref']!=b['focus_ref']
    assert a['anchors'][0]['display_id']==b['anchors'][0]['display_id']
    assert query(a,focus_ref=b['focus_ref']).status_code==403
    other=opening(dataset='ibm-50k').json();assert a['anchors'][0]['display_id']!=other['anchors'][0]['display_id']
    assert query(other,focus_ref=a['focus_ref']).status_code==403
    clock[0]+=601;assert query(a).status_code==410
    g.sessions.clear();assert query(b).status_code==410


@pytest.mark.parametrize('params',[{'depth':0},{'depth':3},{'max_nodes':251},{'max_nodes':0},{'max_edges':501},{'min_count':0},{'min_amount':-1},{'min_amount':'nan'},{'direction':'reverse_raw'},{'focus_ref':'SECRET_A'}])
def test_query_bounds(lens,params):
    s=lens[5]().json();assert lens[6](s,**params).status_code==422


@pytest.mark.parametrize('dataset',['../secret','unknown','ibm-5k\\secret'])
def test_no_arbitrary_dataset_or_paths(lens,dataset):
    assert lens[0].get('/api/v1/graph-explorer/session',params={'dataset_id':dataset,'experiment_id':'baseline-5k-E4-s42-m42'}).status_code==422


def test_unsupported_version_and_ranks(lens):
    assert lens[5](version='untrusted-v2').status_code==422
    assert lens[5](rank=21).status_code==422
    assert lens[5](dataset='paysim').status_code==422


def test_quota_and_get_only(lens):
    c,g,_,_,_,opening,query,_,_=lens;s=opening().json()
    for _ in range(20):assert query(s,min_amount=100).status_code==200
    assert query(s).status_code==429
    for path in ('catalog','session','neighborhood'):
        for verb in ('post','put','patch','delete'):
            assert getattr(c,verb)('/api/v1/graph-explorer/'+path).status_code==405
    g.slots=BoundedSemaphore(0);assert c.get('/api/v1/graph-explorer/catalog').status_code==429


def test_no_refitting_experiment_or_source_mutation(lens):
    _,g,_,root,_,opening,query,_,_=lens
    before={p:file_hash(p) for p in root.rglob('*') if p.is_file()}
    def forbidden(*a,**k):raise AssertionError('No experiment/model/centrality execution')
    with patch('sklearn.ensemble.IsolationForest.fit',forbidden),patch('joblib.load',forbidden),patch('backend.app.services.graph_service.GraphService.build_graph',forbidden),patch('backend.app.services.graph_service.GraphService.compute_betweenness_centrality',forbidden),patch('backend.app.research.interventions.intervention_engine.InterventionEngine.generate',forbidden):
        assert query(opening().json()).status_code==200
    assert before=={p:file_hash(p) for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('damage',['database','manifest_version','dataset_hash','scope_hash'])
def test_integrity_failures(lens,damage):
    c,g,m,root,*_=lens
    if damage=='database':
        with (root/'ibm-5k.sqlite').open('ab') as f:f.write(b'changed')
    elif damage=='manifest_version':m['schema_version']='unknown'
    elif damage=='dataset_hash':m['datasets']['ibm-5k']['dataset_sha256']='0'*64
    else:m['datasets']['ibm-5k']['scope_identity']='0'*64
    (root/'manifest.json').write_text(json.dumps(m))
    r=c.get('/api/v1/graph-explorer/session',params={'dataset_id':'ibm-5k','experiment_id':'baseline-5k-E4-s42-m42'})
    assert r.status_code==503 and 'SECRET_' not in r.text and str(root) not in r.text


def test_fixed_disclosure_scope_not_whole_dataset(lens):
    _,g,m,root,_,opening,query,_,_=lens
    meta=m['datasets']['ibm-5k'];meta['approved_nodes']=['SECRET_A','SECRET_B'];meta['anchors']=[{'account':'SECRET_A','role':'approved anchor'}];meta['scope_identity']=hashlib.sha256(canonical(meta['approved_nodes'])).hexdigest();(root/'manifest.json').write_text(json.dumps(m))
    s=opening().json();data=query(s,depth=2).json();assert len(data['nodes'])==2 and data['truncated'] and 'approved_disclosure_scope' in data['truncation_reasons']
    assert opening(rank=3).status_code==409


def test_links_and_missing_topology_are_safe(lens,monkeypatch):
    c,g,_,root,*_=lens
    original=Path.is_symlink
    with monkeypatch.context() as scoped:
        scoped.setattr(Path,'is_symlink',lambda p:True if p==root/'ibm-5k.sqlite' else original(p))
        assert c.get('/api/v1/graph-explorer/session',params={'dataset_id':'ibm-5k','experiment_id':'baseline-5k-E4-s42-m42'}).status_code==503
    (root/'manifest.json').unlink()
    catalog=c.get('/api/v1/graph-explorer/catalog');assert catalog.status_code==200 and all(x['status']=='unavailable' for x in catalog.json()['datasets'])


def test_deterministic_order_and_capacity(lens):
    _,g,_,_,_,opening,query,_,_=lens;s=opening().json()
    a=query(s).json();b=query(s).json();assert a['nodes']==b['nodes'] and a['edges']==b['edges']
    for _ in range(17):opening()
    assert len(g.sessions)==16 and query(s).status_code==410


def test_private_errors_and_response_byte_budget(lens):
    s=lens[5]().json();lens[4][0]+=601
    expired=lens[6](s)
    assert expired.status_code==410 and expired.headers['cache-control']=='private, no-store'
    assert expired.headers['vary']=='X-Graph-Session'
    data=lens[6](lens[5]().json(),depth=2,max_nodes=250,max_edges=500)
    assert data.status_code==200 and len(data.content)<=512*1024


def test_offline_source_hash_and_exclusive_output(lens,tmp_path):
    source=lens[-1];target=tmp_path/'new.sqlite'
    with pytest.raises(ValueError):build_index(source,target,'ibm-5k','0'*64,['SECRET_A'])
    assert not target.exists()
    target.write_bytes(b'original')
    with pytest.raises(FileExistsError):build_index(source,target,'ibm-5k',file_hash(source),['SECRET_A'])
    assert target.read_bytes()==b'original'


def test_invalid_capability_not_echoed_or_logged(lens,caplog):
    response=lens[0].get('/api/v1/graph-explorer/neighborhood',headers={'X-Graph-Session':'SECRET_BAD_CAPABILITY'},params={'focus_ref':'node_'+'0'*32})
    assert response.status_code==422 and response.headers['cache-control']=='private, no-store'
    assert 'SECRET_BAD_CAPABILITY' not in response.text and 'SECRET_BAD_CAPABILITY' not in caplog.text


@pytest.mark.parametrize('field,value',[
    ('dataset_sha256','0'*64),('heldout_ids_sha256','0'*64),
    ('model_sha256','0'*64),('feature_count',18),('split_seed',7),
    ('model_seed',7),('graph_seed',7),('labels_used',True),
    ('cutoff','2020-01-05T00:00:00+00:00'),('algorithm','unknown')])
def test_incompatible_diagnostic_provenance_is_unavailable(lens,field,value):
    _,_,_,values,persist,_,_=lens[7]
    values['diagnostics'][0]['provenance'][field]=value;persist()
    session=lens[5]().json();view=lens[6](session).json()
    focus=next(n for n in view['nodes'] if n['node_ref']==session['focus_ref'])
    assert focus['ranking_status']=='available' and focus['diagnostic_ids']==[]


def test_incompatible_diagnostic_model_version_is_unavailable(lens):
    _,_,_,values,persist,_,_=lens[7]
    for row in values['rows']:
        if row['method']=='E4':row['version']='unknown-model-version'
    persist()
    session=lens[5]().json()
    assert all(not n['diagnostic_ids'] for n in lens[6](session).json()['nodes'])
