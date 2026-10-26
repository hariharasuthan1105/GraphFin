"""Independent source/index checks and bounded query profiling; no ML jobs.

Run --mode source and --mode queries in separate processes so reference-data
memory does not pollute the query-only RSS observations.
"""
import argparse
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import gc
import hashlib
import json
import sqlite3
import statistics
import subprocess
import sys
import time
import psutil

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.app.services.graph_explorer_service import GraphExplorerService
from backend.app.services.graph_explorer_index import file_hash
from backend.app.services.research_catalog_service import get_research_catalog


def source_check():
    import pandas as pd
    catalog=get_research_catalog();root=ROOT/'data/results/v3/phase9-topology-v1'
    manifest=json.loads((root/'manifest.json').read_bytes());result=[]
    for tier in ('5k','50k'):
        dataset='ibm-'+tier;meta=manifest['datasets'][dataset]
        spec=catalog._read('protocol')['datasets'][tier]
        expected={};rows=retained=0;ids=set()
        source=ROOT/spec['transactions'];assert file_hash(source)==meta['dataset_sha256']
        for frame in pd.read_csv(source,dtype={'sender_id':str,'receiver_id':str,'transaction_id':str},chunksize=50000):
            rows+=len(frame);frame.amount=pd.to_numeric(frame.amount,errors='raise')
            frame=frame[(frame.amount>0)&(frame.sender_id!=frame.receiver_id)]
            times=pd.to_datetime(frame.timestamp,utc=True).astype('datetime64[ns, UTC]').astype('int64')/1e9
            for u,v,amount,ts in zip(frame.sender_id,frame.receiver_id,frame.amount,times):
                retained+=1;ids.update((u,v));a=expected.setdefault((u,v),[0.,0,float('inf'),-float('inf')])
                a[0]+=float(amount);a[1]+=1;a[2]=min(a[2],ts);a[3]=max(a[3],ts)
        assert rows==meta['source_rows'] and retained==meta['retained_rows'] and len(ids)==meta['total_nodes']
        with closing(sqlite3.connect(root/(dataset+'.sqlite'))) as db:
            edges=db.execute('SELECT s,t,amount,cnt,first,last FROM edges').fetchall()
            assert len(edges)==len(expected)==meta['total_edges']
            maximum=0.
            for u,v,amount,count,first,last in edges:
                a=expected[u,v];assert count==a[1] and first==a[2] and last==a[3]
                maximum=max(maximum,abs(amount-a[0]));assert amount==a[0]
        assert file_hash(root/(dataset+'.sqlite'))==meta['index_sha256']
        result.append({'dataset':dataset,'source_rows':rows,'retained_rows':retained,'nodes':len(ids),'directed_pairs':len(edges),'maximum_amount_difference':maximum,'timestamp_and_count_exact':True,'dataset_sha256':meta['dataset_sha256'],'index_sha256':meta['index_sha256']})
        del expected,edges;gc.collect()
    return result


def query_measurements():
    service=GraphExplorerService();process=psutil.Process();before=process.memory_info().rss
    rows=[]
    for dataset in ('ibm-5k','ibm-50k'):
        started=time.perf_counter();session=service.open_session(dataset,f'baseline-{dataset[4:]}-E4-s42-m42');session_seconds=time.perf_counter()-started
        for role in ('high-degree','low-degree'):
            anchor=next(x for x in session.anchors if role in x.role)
            for depth in (1,2):
                samples=[];server=[];payloads=[];counts=[]
                for _ in range(3):
                    start=time.perf_counter();data=service.neighborhood(session.session_id,anchor.node_ref,depth=depth,max_nodes=250,max_edges=500)
                    raw=data.model_dump_json().encode();samples.append(time.perf_counter()-start);server.append(data.query_seconds);payloads.append(len(raw));counts.append((len(data.nodes),len(data.edges)))
                    assert len(data.nodes)<=250 and len(data.edges)<=500 and len(raw)<=512*1024
                rows.append({'dataset':dataset,'anchor_kind':role,'depth':depth,'session_open_seconds':session_seconds,'wall_seconds':samples,'median_wall_seconds':statistics.median(samples),'server_seconds':server,'payload_bytes':payloads,'node_edge_counts':counts,'truncation':data.truncation_reasons})
    memory=process.memory_info()
    return {'conditions':'Fresh Python process; direct service calls; 3 warm/cold mixed samples per approved dense/sparse case; no NetworkX/ML execution. SQLite file SHA verified on every call.','rss_before_bytes':before,'rss_after_bytes':memory.rss,'os_peak_working_set_bytes':getattr(memory,'peak_wset',None),'rows':rows}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('source','queries'),required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=source_check() if args.mode=='source' else query_measurements()
    code={str(p.relative_to(ROOT)).replace('\\','/'):file_hash(p) for p in (ROOT/'backend/app/services/graph_explorer_service.py',ROOT/'backend/app/services/graph_explorer_index.py',Path(__file__))}
    report={'mode':args.mode,'git_head':subprocess.check_output(['git','-c','safe.directory=*','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'code_sha256':code,'result':result}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists():raise FileExistsError(args.output)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
