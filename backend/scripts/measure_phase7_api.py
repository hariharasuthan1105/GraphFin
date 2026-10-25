"""Measure saved-artifact HTTP projections in an existing disposable test copy.

Run from its repository root: python -m backend.scripts.measure_phase7_api OUTPUT_DIR
No lifespan startup, research execution, or source artifact writes are performed.
"""
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
from unittest.mock import patch

import psutil
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.research_catalog_service import research_catalog


def main():
    root = Path(__file__).resolve().parents[2]
    assert (root / '.graphfin-test-sandbox').read_text() == str(root.resolve())
    output = Path(sys.argv[1]).resolve()
    assert not output.is_relative_to(root)
    output.mkdir(parents=True, exist_ok=False)
    process = psutil.Process()
    rss_before = process.memory_info().rss
    base = '/api/v1/research/'
    experiment = 'experiments/baseline-50k-E4-s42-m42'
    routes = ['overview', 'datasets', 'datasets/paysim', 'experiments', experiment,
              experiment + '/metrics', experiment + '/rankings', experiment + '/provenance',
              'comparisons?experiment_id=baseline-5k-E1-s42-m42&experiment_id=baseline-5k-E4-s42-m42',
              'reproducibility', 'model-seeds', 'diagnostics', 'diagnostics/crest-000', 'limitations']
    records = []
    examples = {}
    def forbidden(*args, **kwargs):
        raise AssertionError('Research execution or model deserialization is forbidden')
    with patch('sklearn.ensemble.IsolationForest.fit', forbidden), \
         patch('backend.app.services.graph_service.GraphService.build_graph', forbidden), \
         patch('backend.app.research.interventions.intervention_engine.InterventionEngine.generate', forbidden), \
         patch('joblib.load', forbidden):
        client = TestClient(app)  # Deliberately do not run legacy application lifespan.
        for route in routes:
            research_catalog._cache.clear()
            samples = []
            for _ in range(6):
                start = time.perf_counter()
                response = client.get(base + route)
                samples.append(1000 * (time.perf_counter() - start))
                assert response.status_code == 200, (route, response.status_code, response.text)
            records.append(dict(route=base + route, status=200, response_bytes=len(response.content),
                                cold_ms=samples[0], warm_ms=samples[1:],
                                warm_median_ms=statistics.median(samples[1:])))
            examples[route] = response.json()
        schema = client.get(app.openapi_url).json()
        client.close()
    memory = process.memory_info()
    result = dict(python=platform.python_version(), platform=platform.platform(),
                  methodology='One cleared-cache request followed by five requests per route; in-process TestClient; no lifespan; no network/deployment load test.',
                  rss_before_bytes=rss_before, rss_after_bytes=memory.rss,
                  peak_working_set_bytes=getattr(memory, 'peak_wset', None), measurements=records,
                  catalog_sha256=hashlib.sha256(research_catalog.catalog_file.read_bytes()).hexdigest())
    for name, value in [('performance.json', result), ('response_examples.json', examples), ('openapi.json', schema)]:
        (output / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
