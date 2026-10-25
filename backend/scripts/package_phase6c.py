"""Derive publication tables and label inventory from verified artifacts only."""
from pathlib import Path
import csv, hashlib, itertools, json, shutil, sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.app.research.benchmark.runner import verify
from backend.app.research.benchmark.metrics import metrics
from backend.app.services.feature_service import FEATURE_NAMES
from backend.app.services.research_protocol import GROUPS

def read(p): return json.loads(Path(p).read_bytes())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x',encoding='utf-8') as f:
        json.dump(v,f,indent=2,sort_keys=True,allow_nan=False); f.write('\n')
def table(dest,name,rows):
    save(dest/(name+'.json'),rows)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (dest/(name+'.csv')).open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerows({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)

def lineage(dest,p):
    rows=[]; audit={}
    for tier in ('5k','50k'):
        spec=p['datasets'][tier]; tx=ROOT/spec['transactions']; lp=ROOT/spec['labels']
        assert sha(tx)==spec['transactions_sha256'] and sha(lp)==spec['labels_sha256']
        df=pd.read_csv(tx,dtype={'sender_id':str,'receiver_id':str,'transaction_id':str})
        lab=pd.read_csv(lp,dtype=str); labels=dict(zip(lab.user_id,lab.label.astype(int)))
        assert not lab.user_id.duplicated().any() and lab.label.isin(['0','1']).all()
        assert not df.transaction_id.duplicated().any()
        active=df[(df.amount>0)&(df.sender_id!=df.receiver_id)]
        ids=set(active.sender_id)|set(active.receiver_id)
        assert ids<=set(labels)
        absent=sorted(set(labels)-ids)
        f=ROOT/f'data/results/v2/phase5-features-{tier}-v1'
        pop=read(f/'population.json'); assert ids==set(pop['ids'])
        assert {u:labels[u] for u in ids}==pop['labels']
        counts=[]
        b=ROOT/f'data/results/v2/phase5-baselines-{tier}-v1'
        for s,split in read(f/'splits.json').items():
            tr,te=split['train_ids'],split['test_ids']
            assert len(set(tr))==len(tr) and len(set(te))==len(te)
            assert not set(tr)&set(te) and set(tr)|set(te)==ids
            scores=read(b/f'split-{s}-model-42/scores.json')
            saved=next(r for r in read(b/'results.json') if r['split_seed']==int(s))
            for m,score in scores.items():
                computed=metrics(te,{u:labels[u] for u in te},score)
                assert all(saved['methods'][m][k]==v for k,v in computed.items())
            counts.append({'split_seed':int(s),'train':len(tr),'train_positive':sum(labels[u] for u in tr),
                'test':len(te),'test_positive':sum(labels[u] for u in te),'test_negative':sum(1-labels[u] for u in te)})
        pos=sum(labels[u] for u in ids)
        row={'dataset':tier,'input_rows':len(df),'retained_rows':len(active),'label_rows':len(lab),
            'active_accounts':len(ids),'positive_accounts':pos,'negative_accounts':len(ids)-pos,
            'prevalence':pos/len(ids),'heldout_accounts':counts[0]['test'],
            'heldout_positive':counts[0]['test_positive'],'heldout_negative':counts[0]['test_negative'],
            'transaction_sha256':sha(tx),'label_sha256':sha(lp),'upstream_lineage':'declared_not_verified'}
        rows.append(row)
        audit[tier]={**row,'transaction_columns':list(df.columns),'unique_transaction_ids':True,
            'unique_account_label_ids':True,'all_evaluation_scores_aligned':True,'splits':counts,
            'inactive_label_accounts':absent,'inactive_label_positives':sum(labels[u] for u in absent),
            'raw_transaction_laundering_flags_present':False,
            'account_label_reconstruction':'blocked: raw Is Laundering flags and authenticated conversion input absent'}
    maps={}; facts={}
    for name in ('paysim_labels.csv','paysim_account_labels.csv'):
        path=ROOT/'data/research'/name; df=pd.read_csv(path,dtype=str)
        col='user_id' if 'user_id' in df else 'account'
        assert not df[col].duplicated().any() and df.label.isin(['0','1']).all()
        maps[name]=dict(zip(df[col],df.label.astype(int)))
        facts[name]={'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'accounts':len(df),
            'positives':int(df.label.astype(int).sum()),'duplicates':0,'columns':list(df.columns)}
    a,b=maps.values();assert set(a)==set(b)
    diff=[u for u in a if a[u]!=b[u]]
    tx=ROOT/'data/research/paysim_transactions.csv'
    senders,receivers=set(),set()
    for chunk in pd.read_csv(tx,dtype=str,chunksize=100000):
        senders.update(chunk.sender_id);receivers.update(chunk.receiver_id)
    prefix=pd.read_csv(tx,dtype=str,nrows=10000)
    ids=set(prefix.sender_id)|set(prefix.receiver_id)
    status={'status':'unresolved_conflict','files':facts,'same_account_population':True,
        'disagreements':len(diff),'smaller_positive_subset':all(b[u]==1 for u in a if a[u]==1),
        'transaction_sha256':sha(tx),'transaction_columns':list(prefix.columns),
        'disagreement_roles':{'sender_only':sum(u in senders and u not in receivers for u in diff),
            'receiver_only':sum(u in receivers and u not in senders for u in diff),
            'both':sum(u in senders and u in receivers for u in diff),
            'absent':sum(u not in senders|receivers for u in diff)},
        'prefix_accounts':len(ids),'prefix_positives':{n:sum(m[u] for u in ids) for n,m in maps.items()},
        'known_procedures':['backend/scripts/convert_paysim.py: OR on retained events before optional account subsetting',
            'backend/app/services/paysim_adapter.py: endpoint max on supplied transaction fraud flags'],
        'unsupported':['Which procedure generated each supplied label file','Original raw isFraud flags',
            'Broader-history or receiver-victim explanation of extra positives'],
        'transfer_consequence':'No independently validated cross-domain performance claim'}
    assert len(diff)==1832 and facts['paysim_labels.csv']['positives']==774 and facts['paysim_account_labels.csv']['positives']==2606
    save(dest/'ibm_lineage.json',audit);save(dest/'paysim_provenance.json',status)
    table(dest,'table_A_datasets',rows)

def main():
    v2=ROOT/'data/results/v2'; dest=v2/'phase6c-evidence-v1';dest.mkdir(exist_ok=False)
    p=read(ROOT/'docs/research/configs/phase5_protocol_v1.json');ph=sha(ROOT/'docs/research/configs/phase5_protocol_v1.json')
    validation=v2/'phase6c-validation-v1';vm=read(validation/'manifest.json')
    for n,h in vm['artifacts'].items(): assert sha(validation/n)==h
    for tier in ('5k','50k'):
        verify(v2/f'phase5-features-{tier}-v1',ph);verify(v2/f'phase5-baselines-{tier}-v1',ph)
    lineage(dest,p)
    definitions=[
        'Number of distinct incoming neighbors','Number of distinct outgoing neighbors','in_degree + out_degree',
        'Sum of incoming transaction amounts','Sum of outgoing transaction amounts',
        'Normalized directed unweighted shortest-path betweenness; exact n<=2000; sampled k=500 n<=50000 else k=100; seed42',
        'Number of incident retained transactions','Sum outgoing amounts S','Sum incoming amounts R','R-S',
        '(R+S)/incident count','Maximum incident amount','Number distinct outgoing neighbors','Number distinct incoming neighbors',
        'count/max(1,(latest-earliest)/86400); singleton=1','7 * daily rate',
        'Mean successive sorted timestamp gap in seconds; fewer than two events=0',
        'Minimum successive gap in seconds; fewer than two events=0',
        'Maximum successive gap in seconds; fewer than two events=0',
        'Node count in one-pass reduced induced in/out-neighbor egonet; total-degree<=1 shortcut gives1',
        'Directed edges within reduced egonet; degree<=1 shortcut gives0',
        'edges/[nodes*(nodes-1)] if nodes>1 else0',
        'sum_{v in out(u)} I(u in out(v))/dout(u) + sum_{v in out(u),w in out(v),w!=u} I(u in out(w))/(dout(u)*dout(v)); not normalized return probability']
    table(dest,'table_B_features',[{'index':i,'feature':n,'category':'graph' if i<6 else 'behavior' if i<14 else 'temporal' if i<19 else 'egonet',
        'definition':definitions[i],'source':'backend/app/services/feature_service.py; graph_service.py',
        'storage':'float32; monetary/gaps round2, rates round4, egonet density/circular round6; nonfinite replaced0'} for i,n in enumerate(FEATURE_NAMES)])
    table(dest,'table_C_configurations',[{'method':m,'version':p['algorithms']['E0' if m=='E0' else 'E1-E5'],
        'feature_names':[FEATURE_NAMES[i] for i in ix],'feature_count':len(ix),'preprocessing':p['preprocessing'],
        'score':'max source signed z; zero std<=1e-9' if m=='E0' else '-decision_function',
        'detector':None if m=='E0' else p['detector'],'model_seed':None if m=='E0' else 42,
        'split_seeds':p['primary']['split_seeds'],'graph':'full-observation transductive','centrality_seed':42} for m,ix in GROUPS.items()])
    source=v2/'phase6b-consolidation-v1';man=read(source/'manifest.json')
    for n,h in man['artifacts'].items(): assert sha(source/n)==h
    rr=read(source/'per_seed_metrics.json');ss=read(source/'summary.json')
    for tier,letter in [('5k','D'),('50k','E')]:
        table(dest,f'table_{letter}_six_split_{tier}',[r for r in rr if r['tier']==tier and r['method']!='E6_BASE'])
        table(dest,f'table_{letter}_summary_{tier}',[r for r in ss if r['tier']==tier and r['method']!='E6_BASE'])
    table(dest,'calibration_only_E6_BASE',[r for r in rr if r['method']=='E6_BASE'])
    table(dest,'model_seed_per_run',read(validation/'model_seed_results.json'))
    table(dest,'model_seed_pairwise_stability',read(validation/'model_seed_stability.json'))
    table(dest,'table_F_variability',[
        *[{'variation':'split','fixed_model_seed':42,'runs':6,**r} for r in ss if r['method'] in ('E1','E4')],
        *[{'variation':'model','runs':3,**r} for r in read(validation/'model_seed_summary.json')]])
    limits=[('IBM labels','PARTIALLY','Byte identity/counts/alignment verified; raw laundering flags absent'),
        ('PaySim','NO','774/2606 positives;1832 disagreements; raw generation evidence absent'),
        ('External validation','NO','Same supplied synthetic subsets; replay is not external validation'),
        ('Model randomness','PARTIALLY','Three seeds; fixed split42; E1/E4 only'),
        ('Graph construction','PARTIALLY','Full-observation transductive; not prospective'),
        ('Uncertainty','PARTIALLY','Graph-dependent accounts/overlapping splits; SD not CI'),
        ('CREST superiority','NO','Ranking stopped;12 compatible fidelity ties'),
        ('Feature mechanisms','PARTIALLY','Redundant columns; no deduplication causal ablation'),
        ('Scalability','PARTIALLY','Measured baseline replay; broad interventions exceed projected budget'),
        ('Release permissions','PARTIALLY','Dataset redistribution license not authenticated')]
    table(dest,'table_G_limitations',[{'topic':a,'status':b,'limitation':c} for a,b,c in limits])
    claims=[('Feature enrichment','UNSUPPORTED','Consistent improvement not observed','table_D_summary_5k.json;table_E_summary_50k.json'),
        ('Detector accuracy on supplied labels','SUPPORTED','Scoped descriptive AP/topK only','table_D_six_split_5k.json;table_E_six_split_50k.json'),
        ('Causal network-scale sensitivity','UNSUPPORTED','Composition/history/prevalence confounded','table_A_datasets.json'),
        ('Multi-seed robustness','PARTIALLY SUPPORTED','Split variation and bounded model variation characterized','table_F_variability.json'),
        ('Cross-dataset transfer','UNSUPPORTED','Unresolved target label provenance','paysim_provenance.json'),
        ('Model generalization','UNSUPPORTED','No independent dataset/time evaluation','table_G_limitations.json'),
        ('CREST methodological novelty','UNSUPPORTED','Substantial prior overlap; no demonstrated superiority','verified_bibliography.md'),
        ('CREST detection improvement','UNSUPPORTED','Original E6 incomplete; ranking stopped','../../../../docs/research/05H_evidence_specificity_revision.md'),
        ('Superior explanation fidelity','UNSUPPORTED','Twelve compatible comparisons tie','../../../../docs/research/06A_explanation_validation.md'),
        ('Reproducibility','SUPPORTED' if read(validation/'replay_comparison.json')['all_byte_equal'] else 'PARTIALLY SUPPORTED',
            'Supplied-file baseline replay, not upstream provenance or external validation','../phase6c-validation-v1/replay_comparison.json'),
        ('Runtime scalability','PARTIALLY SUPPORTED','Bounded baseline timings; no general scaling law','../phase6c-validation-v1/prepare-process.json')]
    table(dest,'claims_audit',[{'claim':a,'status':b,'scope':c,'evidence':d} for a,b,c,d in claims])
    shutil.copyfile(ROOT/'docs/research/06B_related_work_comparison.md',dest/'verified_bibliography.md')
    shutil.copyfile(ROOT/'docs/research/configs/phase5_protocol_v1.json',dest/'baseline_protocol.json')
    shutil.copyfile(validation/'protocol.json',dest/'validation_protocol.json')
    (dest/'flowchart.mmd').write_text('flowchart TD\n A[Supplied transactions and separate label identities] --> B[Positive nonself filter]\n B --> C[Full observation directed graph]\n C --> D[Canonical23 features]\n D --> E[Fixed account split]\n E --> F[Source only E0 or Isolation Forest fit]\n F --> G[Held out scores]\n L[Labels used only for stratification and evaluation] --> E\n L --> H[AP ROC and top K]\n G --> H\n H --> I[Versioned manifests and tables]\n G --> J[Optional constrained omission diagnostic: no superiority claim]\n',encoding='utf-8')
    save(dest/'supporting_artifacts.json',{p.relative_to(ROOT).as_posix():sha(p)
        for folder in ('phase6c-validation-v1','phase6c-features-50k-v1','phase6c-baselines-50k-v1',
                       'phase5-baselines-5k-v1','phase5-baselines-50k-v1','phase6a-explanations-v1-pilot-v2')
        for p in (v2/folder).rglob('*') if p.is_file()})
    save(dest/'manifest.json',{'title':p['project_title'],'package':'phase6c-evidence-v1',
        'script_sha256':sha(__file__),'artifacts':{f.name:sha(f) for f in dest.iterdir() if f.is_file()},
        'purpose':'Local manuscript evidence; redistribution rights not established'})
    print(dest,flush=True)

if __name__=='__main__': main()
