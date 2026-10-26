"""Bounded localhost GET-only validation; no uploads, training or research jobs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import time
from urllib.parse import urlsplit
import httpx
try:
    from audit_release import write_exclusive
except ModuleNotFoundError:
    from backend.scripts.audit_release import write_exclusive


def verify(base):
    parsed=urlsplit(base)
    if parsed.scheme != "http" or parsed.hostname not in ("localhost","127.0.0.1") or parsed.username or parsed.password:
        raise ValueError("Use an explicit local demonstration API URL.")
    records=[]
    with httpx.Client(base_url=base,timeout=60) as client:
        def read(path,expected=200,headers=None):
            started=time.perf_counter();response=client.get(path,headers=headers)
            record={"path":path.split("?")[0],"status":response.status_code,"seconds":time.perf_counter()-started,"bytes":len(response.content)}
            assert response.status_code==expected,(record,response.text[:100])
            records.append(record);return response
        paths=["/api/v1/research/overview","/api/v1/research/datasets","/api/v1/research/model-seeds","/api/v1/research/reproducibility"]
        for path in paths:
            for _ in range(3):read(path)
        comparisons="/api/v1/research/comparisons?"+"&".join("experiment_id=baseline-5k-E"+str(i)+"-s42-m42" for i in range(6))+"&metric=average_precision"
        for _ in range(2):read(comparisons)
        for dataset in ("ibm-5k","ibm-50k","paysim"):
            for _ in range(2):
                r=read("/api/v1/research-reports/datasets/"+dataset+"/report.pdf")
                assert r.content.startswith(b"%PDF-") and len(r.content)<=2*1024*1024
                assert r.headers["cache-control"]=="private, no-store"
        read("/api/v1/research/datasets/unknown",404)
        read("/api/v1/research-reports/datasets/unknown/report.pdf",404)
        read("/api/v1/research-reports/datasets/..%2Fsecret/report.pdf",404)
        read("/api/v1/graph-explorer/session?dataset_id=ibm-50k&experiment_id=baseline-5k-E4-s42-m42",409)
        sessions=[]
        for dataset in ("ibm-5k","ibm-50k"):
            state=read("/api/v1/graph-explorer/session?dataset_id="+dataset+"&experiment_id=baseline-"+dataset[4:]+"-E4-s42-m42").json()
            headers={"X-Graph-Session":state["session_id"]}
            for _ in range(3):
                graph=read("/api/v1/graph-explorer/neighborhood?focus_ref="+state["focus_ref"]+"&depth=2&max_nodes=250&max_edges=500",headers=headers).json()
                assert len(graph["nodes"])<=250 and len(graph["edges"])<=500
            sessions.append(state)
        read("/api/v1/graph-explorer/neighborhood?focus_ref="+sessions[1]["focus_ref"],403,{"X-Graph-Session":sessions[0]["session_id"]})
        def concurrent_read(path):
            started=time.perf_counter();r=client.get(path);return {"path":path,"status":r.status_code,"seconds":time.perf_counter()-started,"bytes":len(r.content)}
        with ThreadPoolExecutor(max_workers=3) as pool:
            concurrent=list(pool.map(concurrent_read, paths[:3]*2))
        assert all(r["status"]==200 for r in concurrent)
        denied=client.options("/api/v1/research/overview",headers={"Origin":"https://untrusted.invalid","Access-Control-Request-Method":"GET"})
        allowed=client.options("/api/v1/research/overview",headers={"Origin":"http://localhost:5173","Access-Control-Request-Method":"GET"})
        assert denied.status_code==400 and allowed.status_code==200
        schema=read("/api/v1/openapi.json").json()
        methods={p:{m:{"security":v.get("security",schema.get("security",[]))} for m,v in ops.items() if m in ("get","post","put","patch","delete")} for p,ops in schema["paths"].items()}
        summary=[]
        for path in sorted({r["path"] for r in records}):
            samples=[r["seconds"] for r in records if r["path"]==path and r["status"]==200]
            if samples:summary.append({"path":path,"samples":len(samples),"median_seconds":statistics.median(samples),"min_seconds":min(samples),"max_seconds":max(samples)})
    return {"conditions":"Local API, normal lifespan disposable checkout; warm saved evidence; sequential 2-3 samples and one 3-worker six-read burst. Not a load test/SLA.",
        "requests":records,"summary":summary,"concurrent_read_burst":concurrent,"cors":{"untrusted":denied.status_code,"declared_local":allowed.status_code},"openapi_routes":methods,
        "limitations":["No full-graph UI calculation/model fitting endpoint called.","Body flooding/DoS and distributed quotas were not exercised.","Graph routes retain stricter per-session limits; legacy endpoints require separate deployment controls."]}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--base",default="http://127.0.0.1:8000");parser.add_argument("--output",required=True);args=parser.parse_args()
    result=verify(args.base);write_exclusive(args.output,result)
    print(json.dumps({"requests":len(result["requests"]),"concurrent_reads":len(result["concurrent_read_burst"]),"summary":result["summary"]},indent=2))
