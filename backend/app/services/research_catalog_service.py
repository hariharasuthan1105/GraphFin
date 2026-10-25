"""Pinned JSON-only views. No imports of training, graph or serialized-model code."""
from collections import OrderedDict
from functools import wraps
from pathlib import Path, PurePosixPath
from threading import RLock
import hashlib
import hmac
import json
import math
import re
import secrets
from pydantic import ValidationError
from ..core.config import PROJECT_ROOT
from ..core.exceptions import BaseAppException
from ..schemas import research as s

TITLE = 'Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions'
CATALOG_VERSION = 'graphfin-public-catalog-v1'
APPROVED = frozenset(('phase6c-evidence-v1','phase6b-consolidation-v1','phase6c-validation-v1',
    'phase6a-explanations-v1-pilot-v2','phase5-baselines-5k-v1','phase5-baselines-50k-v1','phase5-baselines-5k-replay-v1'))
LIMIT = 16 * 1024 * 1024
WARNINGS = ['IBM upstream account labels are partially verified; features are transductive.',
            'Reproducibility is not independent external validation.',
            'CREST detection and explanation superiority are unsupported.']

class ResearchError(BaseAppException):
    def __init__(self, code, message, status=503):
        super().__init__(message,status_code=status,error_code=code)

def guarded(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        try:
            return fn(*args,**kwargs)
        except ResearchError:
            raise
        except (KeyError,TypeError,ValueError,IndexError,OverflowError,AttributeError,RecursionError,ValidationError):
            raise ResearchError('UNSUPPORTED_ARTIFACT_SCHEMA','Research artifact has an unsupported structure.') from None
    return wrapped

def finite(v):
    if v is None:return None
    if isinstance(v,bool) or not isinstance(v,(int,float)):
        raise ValueError('Numeric metric required')
    return float(v) if math.isfinite(v) else None

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def identifier(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',value):
        raise ResearchError('INVALID_RESEARCH_ID','Invalid research identifier.',422)

class ResearchCatalogService:
    def __init__(self, root=None, catalog_file=None):
        # Constructor injection is server/test-only. No route accepts either value.
        self.root=Path(root) if root is not None else PROJECT_ROOT/'data/results/v2'
        self.catalog_file=Path(catalog_file) if catalog_file else Path(__file__).with_name('research_catalog_v1.json')
        self._cache=OrderedDict();self._lock=RLock();self._secret=secrets.token_bytes(32)

    def _path(self, relative):
        p=PurePosixPath(relative)
        if p.is_absolute() or '\\' in relative or ':' in relative or any(x in ('.','..') for x in relative.split('/')) or p.parts[0] not in APPROVED or p.suffix!='.json':
            raise ResearchError('UNSAFE_ARTIFACT_PATH','Artifact path is not approved.')
        root=self.root.absolute();path=root.joinpath(*p.parts)
        for node in [root,*root.parents,path,*path.parents]:
            if node.is_symlink() or (hasattr(node,'is_junction') and node.is_junction()):
                raise ResearchError('UNSAFE_ARTIFACT_PATH','Linked artifact paths are not supported.')
        if not path.resolve().is_relative_to(root.resolve()):
            raise ResearchError('UNSAFE_ARTIFACT_PATH','Artifact path is not approved.')
        return path

    def _bytes(self, path):
        try:
            with path.open('rb') as f:
                raw=f.read(LIMIT+1)
        except OSError:
            raise ResearchError('RESEARCH_UNAVAILABLE','Approved research evidence is unavailable.') from None
        if len(raw)>LIMIT:raise ResearchError('ARTIFACT_TOO_LARGE','Research artifact exceeds the read budget.')
        return raw

    def _registry(self):
        raw=self._bytes(self.catalog_file)
        try:reg=json.loads(raw)
        except (ValueError,UnicodeError):raise ResearchError('UNSUPPORTED_ARTIFACT_SCHEMA','Catalog is not valid JSON.') from None
        if not isinstance(reg,dict) or reg.get('schema_version')!=CATALOG_VERSION or reg.get('title')!=TITLE:
            raise ResearchError('UNSUPPORTED_ARTIFACT_SCHEMA','Catalog schema is unsupported.')
        return reg

    def _read(self,key):
        reg=self._registry(); entry=reg['entries'][key]
        if entry['schema']!=key and not (key.startswith('scores-') and entry['schema']=='scores') and not (key in ('five_k_results','five_k_replay') and entry['schema']=='baseline_results'):
            raise ResearchError('UNSUPPORTED_ARTIFACT_SCHEMA','Artifact schema is unsupported.')
        manifest_raw=self._bytes(self._path(entry['manifest']))
        if hashlib.sha256(manifest_raw).hexdigest()!=entry['manifest_sha256']:
            raise ResearchError('ARTIFACT_CHECKSUM_MISMATCH','Research manifest checksum mismatch.')
        manifest=json.loads(manifest_raw)
        if any(manifest.get(k)!=v for k,v in entry['manifest_marker'].items()):
            raise ResearchError('UNSUPPORTED_ARTIFACT_SCHEMA','Research manifest version is unsupported.')
        relative=str(PurePosixPath(entry['path']).relative_to(PurePosixPath(entry['manifest']).parent))
        if manifest[entry['hash_field']].get(relative)!=entry['sha256']:
            raise ResearchError('ARTIFACT_CHECKSUM_MISMATCH','Artifact is not authenticated by its manifest.')
        raw=self._bytes(self._path(entry['path']));digest=hashlib.sha256(raw).hexdigest()
        if digest!=entry['sha256']:
            raise ResearchError('ARTIFACT_CHECKSUM_MISMATCH','Research artifact checksum mismatch.')
        # Rehash bytes even on a cache hit: modification cannot be hidden by stale stat metadata.
        cachekey=(key,digest)
        with self._lock:
            if cachekey in self._cache:
                self._cache.move_to_end(cachekey);return self._cache[cachekey][1]
            try:value=json.loads(raw)
            except (ValueError,UnicodeError):raise ResearchError('UNSUPPORTED_ARTIFACT_SCHEMA','Research artifact is not valid JSON.') from None
            lists={'rows':1000,'datasets':10,'configs':10,'limitations':50,'seed_rows':100,
                   'seed_summary':100,'seed_stability':100,'diagnostics':100,
                   'five_k_results':10,'five_k_replay':10}
            if key in lists and (not isinstance(value,list) or len(value)>lists[key] or not all(isinstance(x,dict) for x in value)):
                raise ValueError('Unsupported record collection')
            if key not in lists and not isinstance(value,dict):raise ValueError('Object required')
            if key=='protocol' and value.get('feature_schema')!='canonical19-plus-egonet4-v1':
                raise ValueError('Unsupported feature schema')
            if key.startswith('scores-') and (len(value)>7 or any(not isinstance(x,dict) or len(x)>20000 for x in value.values())):
                raise ValueError('Unsupported score population')
            self._cache[cachekey]=(len(raw),value)
            while len(self._cache)>4 or sum(x[0] for x in self._cache.values())>8*1024*1024:
                self._cache.popitem(last=False)
            return value

    def evidence(self,key,status='verified',provenance='partially_verified'):
        return dict(status=status,provenance_status=provenance,artifact_id=key,
            artifact_sha256=self._registry()['entries'][key]['sha256'],limitations=list(WARNINGS))

    def _token(self,account,scope):
        return 'acct_'+hmac.new(self._secret,(scope+'\0'+account).encode(),hashlib.sha256).hexdigest()[:24]

    @staticmethod
    def _metrics(row):
        return s.Metrics(count=row['count'],positives=row['positives'],prevalence=finite(row['prevalence']),
            average_precision=finite(row['average_precision']),roc_auc=finite(row.get('roc_auc')),
            retrieval=[s.Retrieval(k=int(k),effective_k=v['effective_k'],positives=v['retrieved_positives'],
                precision=finite(v['precision']),recall=finite(v['recall'])) for k,v in sorted(row['top_k'].items(),key=lambda kv:int(kv[0]))],
            uncertainty_note='No per-run AP CI provided. Missing/nonfinite metrics are null; split/model SD is not a CI.')

    @guarded
    def datasets(self):
        p=self._read('protocol');rows=self._read('datasets');out=[]
        for r in rows:
            tier=r['dataset'];spec=p['datasets'][tier]
            out.append(s.Dataset(**self.evidence('datasets'),dataset_id='ibm-'+tier,name='IBM AML '+tier,
                version=spec['dataset_id'],tier=tier,accounts=r['active_accounts'],transactions=r['retained_rows'],
                positives=r['positive_accounts'],negatives=r['negative_accounts'],prevalence=finite(r['prevalence']),
                label_definition=spec['label_set_id'],label_sets=[s.LabelSet(identity=spec['label_set_id'],sha256=r['label_sha256'],accounts=r['label_rows'],positives=r['positive_accounts'])],
                transaction_sha256=r['transaction_sha256'],time_semantics='Synthetic calendar timestamps; retrospective full-observation involvement.'))
        ps=self._read('paysim')
        out.append(s.Dataset(**self.evidence('paysim',provenance='unresolved'),dataset_id='paysim',name='PaySim',
            version='supplied-paysim-conflicting-labels-v1',tier='supplied',accounts=ps['files']['paysim_labels.csv']['accounts'],
            label_definition='unresolved endpoint-involvement label sets',label_disagreements=ps['disagreements'],
            label_sets=[s.LabelSet(identity='paysim-research-774' if n=='paysim_labels.csv' else 'paysim-application-2606',
                sha256=v['sha256'],accounts=v['accounts'],positives=v['positives']) for n,v in sorted(ps['files'].items())],
            transaction_sha256=ps['transaction_sha256'],time_semantics='Simulation hours converted to synthetic timestamps; not observed real-world dates.'))
        return out

    @guarded
    def dataset(self,dataset_id):
        identifier(dataset_id)
        for d in self.datasets():
            if d.dataset_id==dataset_id:return d
        raise ResearchError('DATASET_NOT_FOUND','Research dataset not found.',404)

    @guarded
    def experiments(self,dataset_id=None,tier=None,method=None,version=None,split_seed=None,model_seed=None):
        p=self._read('protocol');reg=self._registry();configs={c['method']:c for c in self._read('configs')};result=[]
        for r in self._read('rows'):
            t=r['tier'];spec=p['datasets'][t];membership=reg['memberships'][t][str(r['split_seed'])]
            method_name=r['method'];cfg=configs['E4' if method_name=='E6_BASE' else method_name]
            if r['count']!=membership['test_count']:raise ValueError('Population count differs')
            identity=canonical_hash([spec['transactions_sha256'],spec['labels_sha256'],membership])
            result.append(s.Experiment(**self.evidence('rows'),experiment_id=f"baseline-{t}-{method_name}-s{r['split_seed']}-m{r['model_seed']}",
                dataset_id='ibm-'+t,tier=t,method=method_name,version=r['version'],feature_names=cfg['feature_names'],
                split_seed=r['split_seed'],model_seed=r['model_seed'],population_identity=identity,
                dataset_sha256=spec['transactions_sha256'],label_sha256=spec['labels_sha256'],
                train_sha256=membership['train_sha256'],test_sha256=membership['test_sha256'],metrics=self._metrics(r)))
        result.extend([
            s.Experiment(status='incomplete',provenance_status='partially_verified',experiment_id='phase5-e6-incomplete',dataset_id='ibm-5k',tier='5k',method='E6_CREST',version='e6-crest-frozen-e4-v1',limitations=['Original intervention benchmark lacks completion; no detector metrics available.']),
            s.Experiment(status='historical',provenance_status='partially_verified',experiment_id='legacy-e0-e4',dataset_id='ibm-historical',tier='historical',method='E0-E4',version='legacy-mixed',limitations=['Historical versions and missing processed inputs prohibit comparison; metrics intentionally unavailable.'])])
        filters={'dataset_id':dataset_id,'tier':tier,'method':method,'version':version,'split_seed':split_seed,'model_seed':model_seed}
        return sorted([r for r in result if all(v is None or getattr(r,k)==v for k,v in filters.items())],key=lambda x:x.experiment_id)

    @guarded
    def experiment(self,experiment_id):
        identifier(experiment_id)
        for r in self.experiments():
            if r.experiment_id==experiment_id:return r
        raise ResearchError('EXPERIMENT_NOT_FOUND','Research experiment not found.',404)

    @guarded
    def metric_detail(self,experiment_id):
        row=self.experiment(experiment_id)
        if row.status!='verified':raise ResearchError('EXPERIMENT_INCOMPLETE','This research record has no comparable completed metrics.',409)
        return row

    @guarded
    def rankings(self,experiment_id,page,page_size,sort):
        row=self.metric_detail(experiment_id)
        key=f'scores-{row.tier}-{row.split_seed}';scores=self._read(key)[row.method]
        if canonical_hash(sorted(scores))!=row.test_sha256:
            raise ResearchError('POPULATION_MISMATCH','Ranking does not match the declared held-out population.')
        # No labels or raw identities leave this projection.
        ordered=sorted(scores,key=lambda u:(-(finite(scores[u]) if finite(scores[u]) is not None else -math.inf),u))
        if sort=='score_asc':ordered=sorted(scores,key=lambda u:((finite(scores[u]) if finite(scores[u]) is not None else math.inf),u))
        start=(page-1)*page_size
        return s.Page[s.Ranking](**self.evidence(key),total=len(ordered),page=page,page_size=page_size,
            items=[s.Ranking(rank=i+start+1,account_token=self._token(u,row.dataset_id),anomaly_score=finite(scores[u])) for i,u in enumerate(ordered[start:start+page_size])])

    @guarded
    def compare(self,ids,metric):
        rows=[self.metric_detail(x) for x in ids]
        if len(set(ids))!=len(ids) or len({r.population_identity for r in rows})!=1:
            raise ResearchError('INCOMPATIBLE_COMPARISON','Comparison requires distinct experiments with identical dataset, labels and train/test population.',409)
        def value(r):
            if metric in ('average_precision','roc_auc'):return getattr(r.metrics,metric)
            k=int(metric.rsplit('_',1)[-1]);return next((x.precision for x in r.metrics.retrieval if x.k==k),None)
        return s.Comparison(**self.evidence('rows'),metric=metric,population_identity=rows[0].population_identity,
            values=[s.ComparisonValue(experiment_id=r.experiment_id,value=value(r)) for r in rows])

    @guarded
    def reproducibility(self):
        p=self._read('protocol');fifty=self._read('replay')
        five=self._read('five_k_results');rep=self._read('five_k_replay')
        return s.Reproducibility(**self.evidence('replay'),replays=[s.Replay(tier=t,byte_identical=ok,
            evidence_sha256=self._registry()['entries'][key]['sha256'],dataset_sha256=p['datasets'][t]['transactions_sha256'],feature_schema=p['feature_schema'])
            for t,ok,key in [('5k',self._registry()['entries']['five_k_results']['sha256']==self._registry()['entries']['five_k_replay']['sha256'],'five_k_replay'),('50k',fifty['all_byte_equal'],'replay')]],
            n_estimators=p['detector']['n_estimators'],max_samples=p['detector']['max_samples'],contamination=p['detector']['contamination'],split_seeds=p['primary']['split_seeds'])

    @guarded
    def model_seeds(self,dataset_id=None,method=None):
        match=lambda r:(dataset_id is None or dataset_id=='ibm-'+r['tier']) and (method is None or method==r['method'])
        return s.ModelSeeds(**self.evidence('seed_rows'),
            runs=[s.SeedRun(dataset_id='ibm-'+r['tier'],tier=r['tier'],method=r['method'],split_seed=r['split_seed'],model_seed=r['model_seed'],metrics=self._metrics(r),fit_score_seconds=finite(r['fit_and_score_seconds'])) for r in self._read('seed_rows') if match(r)],
            summaries=[s.SeedSummary(**{k:(finite(r[k]) if k.endswith('_ap') else r[k]) for k in ('tier','method','mean_ap','sample_sd_ap','minimum_ap','maximum_ap')}) for r in self._read('seed_summary') if r['variation']=='model' and match(r)],
            pairs=[s.SeedPair(tier=r['tier'],method=r['method'],first_model_seed=r['first_model_seed'],second_model_seed=r['second_model_seed'],spearman_ordinal=finite(r['spearman_ordinal_ranks']),
                top_k=[s.Overlap(k=int(k),overlap=finite(v['overlap']),jaccard=finite(v['jaccard'])) for k,v in sorted(r['top_k'].items(),key=lambda kv:int(kv[0]))]) for r in self._read('seed_stability') if match(r)])

    @guarded
    def diagnostics(self):
        try:rows=self._read('diagnostics')
        except ResearchError as e:
            if e.error_code=='RESEARCH_UNAVAILABLE':return []
            raise
        return [s.Diagnostic(**self.evidence('diagnostics',status='exploratory'),diagnostic_id=f'crest-{i:03d}',
            account_token=self._token(r['account_id'],'ibm-5k'),method=r['method'],family=r.get('family'),available=r['available'],valid=r.get('valid'),
            reason=r.get('reason'),baseline_score=finite(r['original_score']),intervened_score=finite(r.get('intervened_score')),signed_fidelity=finite(r.get('fidelity')),
            omitted_count=r.get('sparsity',{}).get('omitted_count'),omitted_fraction=finite(r.get('sparsity',{}).get('omitted_fraction')),
            omitted_amount_fraction=finite(r.get('sparsity',{}).get('omitted_amount_fraction'))) for i,r in enumerate(rows)]

    @guarded
    def diagnostic(self,diagnostic_id):
        identifier(diagnostic_id)
        for r in self.diagnostics():
            if r.diagnostic_id==diagnostic_id:return r
        raise ResearchError('DIAGNOSTIC_UNAVAILABLE','Requested saved diagnostic is unavailable.',404)

    @guarded
    def limitations(self):
        return s.Limitations(**self.evidence('limitations'),items=[s.Limitation(topic=r['topic'],assessment=r['status'],description=r['limitation']) for r in self._read('limitations')])

    @guarded
    def overview(self):
        unavailable=[]
        def optional(name,fn,default):
            try:return fn()
            except ResearchError as e:
                unavailable.append(name+':'+e.error_code);return default
        datasets=optional('datasets',self.datasets,[])
        runs=optional('experiments',self.experiments,[])
        seeds=optional('model-seeds',self.model_seeds,None)
        diagnostics=optional('diagnostics',self.diagnostics,[])
        replay=optional('reproducibility',self.reproducibility,None)
        return s.Overview(status='unavailable' if unavailable else 'verified',provenance_status='unresolved',
            project_title=TITLE,datasets=datasets,available_methods=sorted({r.method for r in runs if r.status=='verified'}),
            completed_run_count=len({(r.dataset_id,r.split_seed,r.model_seed) for r in runs if r.status=='verified'}),
            completed_evaluation_count=sum(r.status=='verified' for r in runs),scales=sorted({r.tier for r in runs if r.status=='verified'}),
            model_seed_analysis_available=bool(seeds and seeds.runs),crest_diagnostics_available=bool(diagnostics),
            reproducibility_available=bool(replay),unavailable_components=unavailable,limitations=list(WARNINGS)+['PaySim label provenance remains unresolved.'])

research_catalog = ResearchCatalogService()

def get_research_catalog():
    return research_catalog
