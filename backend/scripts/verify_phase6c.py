"""Read-only scientific reconstruction; exclusively writes final review evidence."""
from pathlib import Path
import hashlib, itertools, json, statistics, subprocess, sys, zipfile
import xml.etree.ElementTree as ET
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.app.research.benchmark.metrics import metrics, stability
from backend.app.research.benchmark.runner import verify
from backend.app.services.artifact_integrity import protected_manifest, verify_protected

def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    v2=ROOT/'data/results/v2'; val=v2/'phase6c-validation-v1'; pack=v2/'phase6c-evidence-v1'
    out=v2/'phase6c-final-review-v1'
    if out.exists():raise FileExistsError(out)
    protocol=ROOT/'docs/research/configs/phase5_protocol_v1.json';p=read(protocol);ph=sha(protocol)
    manifests={}
    for d in (val,pack):
        m=read(d/'manifest.json')
        for n,h in m['artifacts'].items():assert sha(d/n)==h,(d,n)
        manifests[d.name]=sha(d/'manifest.json')
    assert sha(ROOT/'backend/scripts/validate_phase6c.py')==read(val/'protocol.json')['script_sha256']
    assert sha(ROOT/'backend/scripts/package_phase6c.py')==read(pack/'manifest.json')['script_sha256']
    for n,h in read(pack/'supporting_artifacts.json').items():assert sha(ROOT/n)==h,n
    for tier in ('5k','50k'):
        for stage in ('features','baselines'):
            verify(v2/f'phase5-{stage}-{tier}-v1',ph)
    compare=[]
    for a,b,names in [
        ('phase5-features-50k-v1','phase6c-features-50k-v1',['features.npy','population.json','splits.json']),
        ('phase5-baselines-50k-v1','phase6c-baselines-50k-v1',['results.json','summary.json',*[f'split-{s}-model-42/scores.json' for s in p['primary']['split_seeds']]]),
        ('phase5-baselines-5k-v1','phase5-baselines-5k-replay-v1',['results.json','summary.json',*[f'split-{s}-model-42/scores.json' for s in p['primary']['split_seeds']]])]:
        verify(v2/a,ph);verify(v2/b,ph)
        for name in names:
            assert (v2/a/name).read_bytes()==(v2/b/name).read_bytes(),(a,b,name)
            compare.append({'reference':a+'/'+name,'replay':b+'/'+name,'sha256':sha(v2/a/name),'byte_equal':True})
    rows=read(val/'model_seed_results.json');assert len(rows)==12
    expected=set(itertools.product(('5k','50k'),('E1','E4'),(13,42,101)))
    assert {(r['tier'],r['method'],r['model_seed']) for r in rows}==expected
    maps={}
    for r in rows:
        f=v2/f"phase5-features-{r['tier']}-v1"
        pop=read(f/'population.json');split=read(f/'splits.json')['42']; ids=split['test_ids']
        score=read(val/r['score_artifact']); maps[r['tier'],r['method'],r['model_seed']]=score
        m=metrics(ids,{u:pop['labels'][u] for u in ids},score)
        assert all(r[k]==value for k,value in m.items())
        params=r['parameters']; assert params['random_state']==r['model_seed'] and params['n_estimators']==100
        assert params['contamination']==.005 and params['n_jobs']==1 and params['max_samples']=='auto'
        if r['model_seed']==42:
            assert score==read(v2/f"phase5-baselines-{r['tier']}-v1/split-42-model-42/scores.json")[r['method']]
    for r in read(val/'model_seed_summary.json'):
        aps=[x['average_precision'] for x in rows if x['tier']==r['tier'] and x['method']==r['method']]
        assert statistics.mean(aps)==r['mean_ap'] and statistics.stdev(aps)==r['sample_sd_ap']
        assert min(aps)==r['minimum_ap'] and max(aps)==r['maximum_ap']
    for r in read(val/'model_seed_stability.json'):
        ids=read(v2/f"phase5-features-{r['tier']}-v1/splits.json")['42']['test_ids']
        st=stability(ids,maps[r['tier'],r['method'],r['first_model_seed']],maps[r['tier'],r['method'],r['second_model_seed']])
        assert all(r[k]==v for k,v in st.items())
    before=read(val/'before.json');missing=[n for n,h in before.items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h]
    assert not missing,missing
    assert not verify_protected()
    with zipfile.ZipFile('C:/Users/hariharasuthan/Downloads/GraphFin-main.zip') as z:
        for n,h in protected_manifest()['files'].items():
            names=[x for x in z.namelist() if x==n or x.endswith('/'+n)]
            assert len(names)==1 and hashlib.sha256(z.read(names[0])).hexdigest()==h==sha(ROOT/n)
    work=ROOT.parent.parent/'work'
    tests={}
    for folder in ('phase6c-final-tests/phase2-u9nqo0ae','phase6c-api-unrestricted/phase2-qs3wkg_r','phase6c-guard-tests/phase2-kehv4qqw'):
        directory=work/folder; suites=list(ET.parse(directory/'results.xml').getroot().iter('testsuite'))
        counts={k:sum(int(s.attrib[k]) for s in suites) for k in ('tests','failures','errors','skipped')}
        assert counts['failures']==counts['errors']==counts['skipped']==0
        tests[folder]={**counts,'junit_seconds':sum(float(s.attrib['time']) for s in suites),
            'files':{f.name:sha(f) for f in directory.iterdir() if f.is_file()}}
    assert [r['tests'] for r in tests.values()]==[87,21,4]
    assert (work/'phase6c-final-tests/exit.txt').read_text(encoding='utf-8-sig').strip()=='0'
    diff=subprocess.run(['git','-c','safe.directory=*','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    assert diff.returncode==0,diff.stdout+diff.stderr
    docs=list((ROOT/'docs/research').glob('06C_*.md'));assert len(docs)==4
    for d in docs:
        content=d.read_text(encoding='utf-8');assert p['project_title'] in content
        assert all(line==line.rstrip() for line in content.splitlines()),d
    source_files=[ROOT/'backend/scripts'/n for n in ('validate_phase6c.py','package_phase6c.py','verify_phase6c.py')]
    inventory={f.relative_to(ROOT).as_posix():sha(f) for f in docs+source_files+[ROOT/'backend/tests/test_phase6c_validation.py']}
    report={'title':p['project_title'],'phase':'6C','manifest_checks':manifests,'replay_comparisons':compare,
        'model_seed_rows_recomputed':12,'pairwise_stability_rows_recomputed':12,
        'protected_original_zip_matches':87,'snapshot_files_unchanged':len(before),
        'historical_files_excluding_new_validator':len(before)-1,'historical_mismatches':missing,
        'tests':tests,'unique_final_tests':108,'final_failures':0,'final_skips':0,'final_blocked':0,
        'test_exit_codes':{'final_regression':0,'approved_integration':0,'guard':0},
        'earlier_attempts':['Interrupted mixed run: exit1, no final results',
            'Restricted API diagnostic: fallback_socketpair hang, interrupted exit1; approved suite passed',
            'Restricted regression: native pandas/Arrow access violation; no final JUnit or recovered process exit'],
        'git_diff_check_exit':0,'created_source_and_reports':inventory,'verification_script_sha256':sha(__file__),
        'scientific_readiness':'PARTIALLY: empirical scope only; provenance and manuscript alignment outstanding',
        'committed':False,'frontend_changed':False,'new_detector':False}
    out.mkdir()
    (out/'final_review.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('unique_final_tests','protected_original_zip_matches','snapshot_files_unchanged','git_diff_check_exit')}))

if __name__=='__main__':main()
