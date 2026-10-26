"""Import/configuration validation only; no fit, dataset access or publication."""
import json
from backend.app.runtime import app
from backend.app.research_demo import TITLE
import os


def check():
    assert app.title == TITLE
    assert app.debug is False
    assert app.docs_url is None and app.openapi_url is None
    # This FastAPI version retains lazy included-router objects in app.routes.
    # Inspect the generated effective contract instead of assuming a flat list.
    paths = app.openapi()['paths']
    assert len(paths) == 20
    assert all(set(operations) == {'get'} for operations in paths.values())
    assert all(path in ('/health', '/api/v1/health') or path.startswith((
        '/api/v1/research/', '/api/v1/research-reports/', '/api/v1/graph-explorer/'))
        for path in paths)
    return {'status': 'startup-check-ok', 'mode': os.environ.get('GRAPHFIN_SECURITY_PROFILE', 'local_demo'),
            'deployment_approved': False, 'read_only_paths': len(paths)}


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
