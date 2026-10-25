"""Small, explicitly synthetic fixtures. No financial predictions are generated."""
from pathlib import Path
import hashlib
import json
import math
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.research_catalog_service import ResearchCatalogService, get_research_catalog, canonical_hash

def encode(value):return json.dumps(value,sort_keys=True).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()

@pytest.fixture
def research(tmp_path):
    production=Path(__file__).resolve().parents[1]/'app/services/research_catalog_v1.json'
    reg=json.loads(production.read_bytes());root=tmp_path/'v2';root.mkdir()
    config=tmp_path/'catalog.json';values={}
    def metric():return {'count':3,'positives':1,'prevalence':1/3,'average_precision':.5,'roc_auc':.5,
        'top_k':{'10':{'effective_k':3,'retrieved_positives':1,'precision':1/3,'recall':1.0}}}
    protocol={'feature_schema':'canonical19-plus-egonet4-v1','datasets':{},'detector':{'n_estimators':100,'max_samples':'auto','contamination':.005},'primary':{'split_seeds':[42,7]}}
    values.update(rows=[],datasets=[],configs=[{'method':m,'feature_names':['in_degree']} for m in ('E0','E1','E2','E3','E4','E5')],seed_rows=[],seed_summary=[],seed_stability=[])
    for tier in ('5k','50k'):
        protocol['datasets'][tier]={'dataset_id':'fixture-'+tier,'label_set_id':'synthetic-label-'+tier,'transactions_sha256':('a' if tier=='5k' else 'c')*64,'labels_sha256':'b'*64}
        values['datasets'].append({'dataset':tier,'active_accounts':3,'retained_rows':4,'positive_accounts':1,'negative_accounts':2,'prevalence':1/3,'label_rows':3,'label_sha256':'b'*64,'transaction_sha256':protocol['datasets'][tier]['transactions_sha256']})
        for seed in (42,7,123,2024,99,555):
            ids=['SECRET_A','SECRET_B','SECRET_C' if seed==42 else 'SECRET_D']
            reg['memberships'][tier][str(seed)]={'train_sha256':canonical_hash(['SECRET_TRAIN']),'test_sha256':canonical_hash(sorted(ids)),'test_count':3}
            values[f'scores-{tier}-{seed}']={m:dict(zip(ids,[.9,.5,.1])) for m in ('E0','E1','E4','E6_BASE')}
            if seed not in (42,7):continue
            for m in ('E0','E1','E4','E6_BASE'):
                values['rows'].append({'tier':tier,'method':m,'split_seed':seed,'model_seed':42,'version':'fixture-v1',**metric()})
        for m in ('E1','E4'):
            for seed in (13,42,101):
                values['seed_rows'].append({'tier':tier,'method':m,'split_seed':42,'model_seed':seed,'fit_and_score_seconds':.01,**metric()})
            values['seed_summary'].append({'variation':'model','tier':tier,'method':m,'mean_ap':.5,'sample_sd_ap':0,'minimum_ap':.5,'maximum_ap':.5})
    values['protocol']=protocol
    values['paysim']={'files':{'paysim_labels.csv':{'sha256':'d'*64,'accounts':8,'positives':1},'paysim_account_labels.csv':{'sha256':'e'*64,'accounts':8,'positives':3}},'disagreements':2,'transaction_sha256':'f'*64}
    values['replay']={'all_byte_equal':True};values['five_k_results']=values['five_k_replay']=[{'fixture':True}]
    values['diagnostics']=[{'account_id':'SECRET_A','method':'A','family':'counterparty','available':True,'valid':True,'original_score':.4,'intervened_score':.2,'fidelity':.2,'omitted_transaction_ids':['SECRET_TX'],'sparsity':{'omitted_count':1,'omitted_fraction':.25,'omitted_amount_fraction':.1}},
        {'account_id':'SECRET_B','method':'B','available':False,'valid':None,'reason':'no_eligible_whole_group','original_score':.1}]
    values['diagnostic_summary']={};values['diagnostic_timings']={}
    values['limitations']=[{'topic':'Synthetic fixture','status':'PARTIALLY','limitation':'No predictive validity implied.'}]
    def persist():
        manifests={}
        for key,e in reg['entries'].items():
            target=root/e['path'];target.parent.mkdir(parents=True,exist_ok=True)
            raw=encode(values[key]);target.write_bytes(raw);e['sha256']=sha(raw)
            manifest=manifests.setdefault(e['manifest'],{**e['manifest_marker'],e['hash_field']:{}})
            relative=str(Path(e['path']).relative_to(Path(e['manifest']).parent)).replace('\\','/')
            manifest[e['hash_field']][relative]=e['sha256']
        for n,m in manifests.items():(root/n).write_bytes(encode(m))
        for e in reg['entries'].values():e['manifest_sha256']=sha((root/e['manifest']).read_bytes())
        config.write_bytes(encode(reg))
    persist();service=ResearchCatalogService(root,config)
    app.dependency_overrides[get_research_catalog]=lambda:service
    client=TestClient(app)
    yield client,service,reg,values,persist,root,config
    app.dependency_overrides.pop(get_research_catalog,None)

@pytest.mark.parametrize('path', ['overview','datasets','datasets/ibm-5k','datasets/paysim','experiments',
    'experiments/baseline-5k-E4-s42-m42','experiments/baseline-5k-E4-s42-m42/metrics',
    'experiments/baseline-5k-E4-s42-m42/provenance','experiments/baseline-5k-E4-s42-m42/rankings',
    'reproducibility','model-seeds','diagnostics','diagnostics/crest-000','limitations'])
def test_public_endpoints(research,path):
    response=research[0].get('/api/v1/research/'+path)
    assert response.status_code==200,response.text
    body=response.json();assert body['status'] in ('verified','exploratory') and 'provenance_status' in body
    assert 'SECRET_' not in response.text and 'omitted_transaction_ids' not in response.text

def test_dataset_provenance_is_separate(research):
    c=research[0]
    ibm=c.get('/api/v1/research/datasets/ibm-5k').json()
    ps=c.get('/api/v1/research/datasets/paysim').json()
    assert ibm['accounts']==3 and ibm['positives']==1 and ibm['provenance_status']=='partially_verified'
    assert ps['provenance_status']=='unresolved' and ps['positives'] is None
    assert sorted(x['positives'] for x in ps['label_sets'])==[1,3] and ps['label_disagreements']==2

def test_filters_alignment_and_seed_rows(research):
    c=research[0];r=c.get('/api/v1/research/experiments',params={'dataset_id':'ibm-5k','method':'E4','split_seed':42}).json()
    assert r['total']==1 and r['items'][0]['metrics']['count']==3
    assert r['items'][0]['metrics']['average_precision']==.5
    seeds=c.get('/api/v1/research/model-seeds',params={'dataset_id':'ibm-5k','method':'E4'}).json()
    assert [r['model_seed'] for r in seeds['runs']]==[13,42,101]
    assert c.get('/api/v1/research/experiments',params={'version':'absent'}).json()['items']==[]

@pytest.mark.parametrize('query',[{'page_size':101},{'page_size':0},{'page_number':0},{'page_number':1001},{'sort':'raw_account'}])
def test_pagination_and_sort_allowlist(research,query):
    assert research[0].get('/api/v1/research/experiments/baseline-5k-E4-s42-m42/rankings',params=query).status_code==422

def test_rank_pages_are_deterministic_and_private(research):
    c=research[0];url='/api/v1/research/experiments/baseline-5k-E4-s42-m42/rankings'
    a=c.get(url,params={'page_size':1}).json();b=c.get(url,params={'page_size':1}).json()
    assert a==b and a['items'][0]['anomaly_score']==.9
    assert c.get(url,params={'page_size':1,'page_number':2}).json()['items'][0]['rank']==2
    assert c.get(url,params={'page_number':999}).json()['items']==[]
    assert c.get(url,params={'sort':'score_asc'}).json()['items'][0]['anomaly_score']==.1
    assert a['items'][0]['account_token'].startswith('acct_')

def test_compatible_comparison(research):
    r=research[0].get('/api/v1/research/comparisons',params=[('experiment_id','baseline-5k-E4-s42-m42'),('experiment_id','baseline-5k-E6_BASE-s42-m42')])
    assert r.status_code==200 and len(r.json()['values'])==2
    assert 'significance' in r.json()['interpretation']

@pytest.mark.parametrize('other',['baseline-50k-E4-s42-m42','baseline-5k-E4-s7-m42','legacy-e0-e4','phase5-e6-incomplete'])
def test_reject_incompatible_comparison(research,other):
    r=research[0].get('/api/v1/research/comparisons',params=[('experiment_id','baseline-5k-E4-s42-m42'),('experiment_id',other)])
    assert r.status_code==409

def test_unsupported_metric_and_incomplete(research):
    c=research[0]
    assert c.get('/api/v1/research/comparisons',params=[('experiment_id','baseline-5k-E4-s42-m42'),('experiment_id','baseline-5k-E1-s42-m42'),('metric','invented')]).status_code==422
    assert c.get('/api/v1/research/experiments/phase5-e6-incomplete').json()['status']=='incomplete'
    assert c.get('/api/v1/research/experiments/phase5-e6-incomplete/metrics').status_code==409
    assert c.get('/api/v1/research/experiments/legacy-e0-e4').json()['status']=='historical'

@pytest.mark.parametrize('path',['experiments/missing','diagnostics/missing','datasets/missing'])
def test_missing_identifiers(research,path):assert research[0].get('/api/v1/research/'+path).status_code==404

@pytest.mark.parametrize('key',['rows','scores-5k-42','diagnostics'])
def test_hash_mismatch_fails_closed_even_after_cache(research,key):
    c,svc,reg,values,persist,root,_=research
    svc._read(key);(root/reg['entries'][key]['path']).write_bytes(b'{}')
    url='experiments' if key=='rows' else 'diagnostics' if key=='diagnostics' else 'experiments/baseline-5k-E4-s42-m42/rankings'
    r=c.get('/api/v1/research/'+url)
    assert r.status_code==503 and r.json()['error']=='ARTIFACT_CHECKSUM_MISMATCH'
    assert str(root) not in r.text

def test_manifest_mismatch(research):
    c,svc,reg,values,persist,root,_=research
    (root/reg['entries']['rows']['manifest']).write_bytes(b'{}')
    assert c.get('/api/v1/research/experiments').json()['error']=='ARTIFACT_CHECKSUM_MISMATCH'

@pytest.mark.parametrize('version_change',['catalog','artifact'])
def test_schema_version_rejected(research,version_change):
    c,svc,reg,values,persist,root,config=research
    if version_change=='catalog':reg['schema_version']='future-v900'
    else:reg['entries']['rows']['schema']='future-v900'
    config.write_bytes(encode(reg))
    r=c.get('/api/v1/research/experiments');assert r.status_code==503 and r.json()['error']=='UNSUPPORTED_ARTIFACT_SCHEMA'

@pytest.mark.parametrize('path',['../secret.json','/secret.json','C:/secret.json','phase6c-evidence-v1/../../secret.json','phase6c-evidence-v1/secret.joblib','phase6c-evidence-v1\\secret.json'])
def test_path_traversal_rejected(research,path):
    c,svc,reg,values,persist,root,config=research
    reg['entries']['rows']['path']=path;config.write_bytes(encode(reg))
    assert c.get('/api/v1/research/experiments').status_code==503
    with pytest.raises(Exception):svc._path(path)

def test_link_escape_policy(research,monkeypatch):
    c,svc,reg,values,persist,root,_=research
    original=Path.is_symlink
    monkeypatch.setattr(Path,'is_symlink',lambda p:p==root or original(p))
    r=c.get('/api/v1/research/experiments');assert r.status_code==503 and r.json()['error']=='UNSAFE_ARTIFACT_PATH'

def test_missing_artifact_and_diagnostic(research):
    c,svc,reg,values,persist,root,_=research
    (root/reg['entries']['diagnostics']['path']).unlink()
    assert c.get('/api/v1/research/diagnostics').json()['status']=='unavailable'
    assert c.get('/api/v1/research/diagnostics/crest-000').status_code==404
    (root/reg['entries']['rows']['path']).unlink()
    assert c.get('/api/v1/research/overview').json()['status']=='unavailable'

def test_nonfinite_and_missing_are_null(research):
    c,svc,reg,values,persist,root,_=research
    values['rows'][0]['average_precision']=math.nan;values['rows'][0]['roc_auc']=None;persist()
    r=c.get('/api/v1/research/experiments').json()
    item=next(x for x in r['items'] if x['experiment_id']=='baseline-5k-E0-s42-m42')
    assert item['metrics']['average_precision'] is None and item['metrics']['roc_auc'] is None

def test_population_mismatch(research):
    c,svc,reg,values,persist,root,_=research
    values['scores-5k-42']['E4']={'SECRET_OTHER':.5};persist()
    r=c.get('/api/v1/research/experiments/baseline-5k-E4-s42-m42/rankings')
    assert r.status_code==503 and r.json()['error']=='POPULATION_MISMATCH'

def test_no_mutation_no_execution_and_existing_api(research,monkeypatch):
    c,svc,reg,values,persist,root,_=research
    from sklearn.ensemble import IsolationForest
    from backend.app.services.graph_service import GraphService
    from backend.app.research.interventions.intervention_engine import InterventionEngine
    def forbidden(*a,**k):raise AssertionError('Research execution is forbidden')
    monkeypatch.setattr(IsolationForest,'fit',forbidden)
    monkeypatch.setattr(GraphService,'build_graph',forbidden)
    monkeypatch.setattr(InterventionEngine,'generate',forbidden)
    before={p:sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
    assert c.get('/api/v1/research/overview').status_code==200
    assert c.get('/api/v1/research/diagnostics').status_code==200
    assert c.get('/api/v1/evaluation').status_code==200
    for verb in ('post','put','patch','delete'):
        assert getattr(c,verb)('/api/v1/research/overview').status_code==405
    assert before=={p:sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
    paths=c.get(app.openapi_url).json()['paths']
    assert len([p for p in paths if p.startswith('/api/v1/research/')])==14
    assert all(set(v)=={'get'} for p,v in paths.items() if p.startswith('/api/v1/research/'))
    assert paths['/api/v1/research/experiments']['get']['responses']['422']['content']['application/json']['schema']['$ref'].endswith('/ErrorResponse')

@pytest.mark.parametrize('change',['collection','feature_schema','metric_type'])
def test_malformed_structures_are_safe(research,change):
    c,svc,reg,values,persist,root,_=research
    if change=='collection':values['rows']={'unexpected':True}
    elif change=='feature_schema':values['protocol']['feature_schema']='unknown-v9'
    else:values['rows'][0]['average_precision']='SECRET_INVALID'
    persist();r=c.get('/api/v1/research/experiments')
    assert r.status_code==503 and r.json()['error']=='UNSUPPORTED_ARTIFACT_SCHEMA'
    assert 'SECRET_' not in r.text and str(root) not in r.text

@pytest.mark.parametrize('value',['..','%2E%2E','%2Fsecret','abc%5Csecret'])
def test_client_traversal_never_resolves_a_file(research,value):
    r=research[0].get('/api/v1/research/experiments/'+value)
    assert r.status_code in (404,422)

def test_cache_and_read_budget_are_bounded(research,monkeypatch):
    c,svc,reg,values,persist,root,_=research
    for key in ('rows','protocol','configs','datasets','limitations'):svc._read(key)
    assert len(svc._cache)<=4 and sum(x[0] for x in svc._cache.values())<=8*1024*1024
    import backend.app.services.research_catalog_service as module
    monkeypatch.setattr(module,'LIMIT',10)
    assert c.get('/api/v1/research/experiments').json()['error']=='ARTIFACT_TOO_LARGE'
