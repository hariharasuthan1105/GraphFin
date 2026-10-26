"""Prepare immutable Phase 9 topology; never starts research/ML experiments."""
from pathlib import Path
import json
import sys
import psutil
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.app.services.research_catalog_service import research_catalog
from backend.app.services.graph_explorer_index import build_index


def main():
    destination=ROOT/'data/results/v3/phase9-topology-v1'
    destination.mkdir(parents=True,exist_ok=False)
    results={}
    protocol=research_catalog._read('protocol')
    diagnostics=research_catalog._read('diagnostics')
    for tier in ('5k','50k'):
        dataset_id='ibm-'+tier;spec=protocol['datasets'][tier]
        if spec.get('row_limit') is not None:raise ValueError('Only full supplied canonical snapshots are supported.')
        scores=research_catalog._read('scores-'+tier+'-42')['E4']
        seeds=sorted(scores,key=lambda u:(-scores[u],u))[:20]
        diag=sorted({r['account_id'] for r in diagnostics if r['available']}) if tier=='5k' else []
        results[dataset_id]=build_index(ROOT/spec['transactions'],destination/(dataset_id+'.sqlite'),dataset_id,spec['transactions_sha256'],seeds,diag)
        results[dataset_id]['memory_rss_after']=psutil.Process().memory_info().rss
        print(dataset_id,results[dataset_id]['total_nodes'],results[dataset_id]['total_edges'],results[dataset_id]['build_seconds'],flush=True)
    (destination/'manifest.json').write_text(json.dumps({'schema_version':'graphfin-topology-bundle-v1','datasets':results},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
