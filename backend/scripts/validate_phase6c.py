"""Bounded append-only validation; no intervention or production-state writes.

Run from repository root: python backend/scripts/validate_phase6c.py
The protocol is persisted before new fits. Existing output IDs are rejected.
"""
from pathlib import Path
import hashlib, itertools, json, platform, subprocess, sys, time
import statistics
import numpy as np
import pandas as pd
import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.research.benchmark.runner import verify
from backend.app.research.benchmark.metrics import metrics, stability
from backend.app.services.research_protocol import ResearchConfig, InputSpec, GROUPS, fit_and_score
from backend.app.services.artifact_integrity import verify_protected

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_bytes())

def save(p, value):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')

def bounded(command, destination, seconds=600, rss_limit=2*1024**3):
    """Terminate this dedicated child only if its prespecified budget is exceeded."""
    start = time.perf_counter()
    peak = 0
    reason = None
    with destination.open('xb') as log:
        child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        while child.poll() is None:
            try:
                peak = max(peak, psutil.Process(child.pid).memory_info().rss)
            except psutil.NoSuchProcess:
                pass
            if time.perf_counter()-start > seconds or peak > rss_limit:
                reason = 'time_budget' if time.perf_counter()-start > seconds else 'memory_budget'
                child.terminate()
                child.wait(timeout=20)
                break
            time.sleep(.25)
    return {'command':command,'exit_code':child.returncode,'wall_seconds':time.perf_counter()-start,
            'sampled_peak_rss':peak,'stop_reason':reason,'limit_seconds':seconds,'rss_limit':rss_limit}

def seeds(dest, p, ph):
    rows, pairs = [], []
    for tier in ('5k','50k'):
        f = ROOT/f'data/results/v2/phase5-features-{tier}-v1'
        verify(f, ph)
        pop, split = read(f/'population.json'), read(f/'splits.json')['42']
        ids = pop['ids']; index = {u:i for i,u in enumerate(ids)}
        x = np.load(f/'features.npy', allow_pickle=False)
        train, test = split['train_ids'], split['test_ids']
        assert not set(train)&set(test) and set(train)|set(test)==set(ids)
        labels = {u:pop['labels'][u] for u in test}
        for method in ('E1','E4'):
            maps = {}
            cols = GROUPS[method]
            tr = x[[index[u] for u in train]][:,cols]
            te = x[[index[u] for u in test]][:,cols]
            for seed in (13,42,101):
                cfg = ResearchConfig(source=InputSpec(**p['datasets'][tier],family='ibm'),
                    experiment=method, model_seed=seed, **{k:v for k,v in p['detector'].items() if k!='n_jobs'})
                start = time.perf_counter()
                scores, predictions, params = fit_and_score(tr,[te],cfg)
                elapsed = time.perf_counter()-start
                score = dict(zip(test,map(float,scores[0]))); maps[seed]=score
                name = f'{tier}-{method}-model-{seed}-scores.json'
                save(dest/name,score)
                m = metrics(test,labels,score)
                if seed==42:
                    old=read(ROOT/f'data/results/v2/phase5-baselines-{tier}-v1/split-42-model-42/scores.json')[method]
                    assert score==old, (tier,method,'seed42 replay mismatch')
                rows.append({'tier':tier,'method':method,'split_seed':42,'model_seed':seed,
                    'score_artifact':name,'feature_manifest_sha256':digest(f/'manifest.json'),
                    'train_ids_sha256':hashlib.sha256(json.dumps(train).encode()).hexdigest(),
                    'test_ids_sha256':hashlib.sha256(json.dumps(test).encode()).hexdigest(),
                    'fit_and_score_seconds':elapsed,'parameters':params,
                    'predicted_anomalies':int(predictions[0].sum()),**m})
            for a,b in itertools.combinations(maps,2):
                pairs.append({'tier':tier,'method':method,'first_model_seed':a,'second_model_seed':b,
                              **stability(test,maps[a],maps[b])})
    summary=[]
    for tier,method in itertools.product(('5k','50k'),('E1','E4')):
        rr=[r for r in rows if r['tier']==tier and r['method']==method]
        ap=[r['average_precision'] for r in rr]
        summary.append({'tier':tier,'method':method,'split_seed':42,'model_seeds':[13,42,101],
            'mean_ap':statistics.mean(ap),'sample_sd_ap':statistics.stdev(ap),
            'minimum_ap':min(ap),'maximum_ap':max(ap)})
    save(dest/'model_seed_results.json',rows)
    save(dest/'model_seed_stability.json',pairs)
    save(dest/'model_seed_summary.json',summary)

def main():
    if len(sys.argv)>1 and sys.argv[1]=='seeds':
        p=read(ROOT/'docs/research/configs/phase5_protocol_v1.json')
        seeds(Path(sys.argv[2]),p,digest(ROOT/'docs/research/configs/phase5_protocol_v1.json'))
        return
    dest=ROOT/'data/results/v2/phase6c-validation-v1'
    dest.mkdir(exist_ok=False)
    # Snapshot is before all scientific work, includes current script.
    before={p.relative_to(ROOT).as_posix():digest(p) for folder in ('backend','data','docs','frontend')
        for p in (ROOT/folder).rglob('*') if p.is_file()
        and not {'node_modules','__pycache__','.pytest_cache','.venv'}&set(p.parts)}
    save(dest/'before.json',before)
    assert not verify_protected()
    p=read(ROOT/'docs/research/configs/phase5_protocol_v1.json')
    ph=digest(ROOT/'docs/research/configs/phase5_protocol_v1.json')
    free=psutil.virtual_memory().available
    protocol={'title':p['project_title'],'version':'phase6c-validation-v1','phase5_protocol_sha256':ph,
        'model_seeds':[13,42,101],'fixed_split_seed':42,'methods':['E1','E4'],'tiers':['5k','50k'],
        'resources':{'each_child_seconds':600,'each_child_rss_bytes':2*1024**3,'available_ram_bytes':free},
        'feasibility':{'previous_50k_feature_seconds':70.35,'previous_50k_baseline_seconds':116.74,
            'previous_50k_peak_bytes_approx':520000000,'centrality_k':500,'centrality_seed':42,
            'decision':'GO' if free>2*1024**3 else 'BLOCK_MEMORY'},
        'script_sha256':digest(__file__),'git_head':subprocess.check_output(['git','-c','safe.directory=*','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'git_diff_sha256':hashlib.sha256(subprocess.check_output(['git','-c','safe.directory=*','diff'],cwd=ROOT)).hexdigest(),
        'python':platform.python_version(),'dependencies':subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines(),
        'label_policy':'no labels in fits; source labels only for split/evaluation; PaySim excluded',
        'external_validation':False,'new_interventions':False}
    save(dest/'protocol.json',protocol)
    if free<=2*1024**3:
        save(dest/'blocked.json',{'reason':'Available memory below prespecified 2 GiB threshold'})
        return
    commands=[('prepare',[sys.executable,'-m','backend.app.research.benchmark.runner','prepare',
        'docs/research/configs/phase5_protocol_v1.json','phase6c-features-50k-v1','--tier','50k']),
        ('evaluate',[sys.executable,'-m','backend.app.research.benchmark.runner','evaluate',
        'docs/research/configs/phase5_protocol_v1.json','phase6c-baselines-50k-v1','--features',
        'data/results/v2/phase6c-features-50k-v1']),
        ('seeds',[sys.executable,str(Path(__file__).resolve()),'seeds',str(dest)])]
    for stage,cmd in commands:
        result=bounded(cmd,dest/f'{stage}.log')
        save(dest/f'{stage}-process.json',result)
        print(stage,json.dumps(result),flush=True)
        if result['exit_code']!=0:
            save(dest/'incomplete.json',{'stage':stage,'reason':result})
            return
    comparisons={}
    for old,new in [('phase5-features-50k-v1','phase6c-features-50k-v1'),
                    ('phase5-baselines-50k-v1','phase6c-baselines-50k-v1')]:
        a,b=ROOT/'data/results/v2'/old,ROOT/'data/results/v2'/new
        ma,mb=verify(a,ph),verify(b,ph)
        names=['features.npy','population.json','splits.json'] if 'features' in old else [
            'results.json','summary.json',*[f'split-{s}-model-42/scores.json' for s in p['primary']['split_seeds']]]
        for n in names:
            comparisons[n]={'original_sha256':digest(a/n),'replay_sha256':digest(b/n),
                'byte_equal':(a/n).read_bytes()==(b/n).read_bytes()}
    save(dest/'replay_comparison.json',{'tolerance':0,'comparisons':comparisons,
        'all_byte_equal':all(x['byte_equal'] for x in comparisons.values()),
        'excluded':'runtime, memory, run identity and feature-manifest identity; model serialization not claimed identical'})
    save(dest/'manifest.json',{'stage':'phase6c-complete','protocol_sha256':digest(dest/'protocol.json'),
        'artifacts':{p.name:digest(p) for p in dest.iterdir() if p.is_file()}})

if __name__=='__main__':
    main()
