from hashlib import sha256
from io import BytesIO
from threading import BoundedSemaphore
from unittest.mock import patch
import pytest
from pypdf import PdfReader
from backend.tests.test_phase7_research_api import research
from backend.app.services.dataset_report_service import dataset_report_service, TITLE


@pytest.mark.parametrize('dataset',['ibm-5k','ibm-50k','paysim'])
def test_valid_bounded_pdf(research,dataset):
    client=research[0]
    response=client.get(f'/api/v1/research-reports/datasets/{dataset}/report.pdf')
    assert response.status_code==200 and response.headers['content-type']=='application/pdf'
    assert response.headers['content-disposition']==f'attachment; filename="GraphFin_{dataset}_dataset_report.pdf"'
    assert response.headers['cache-control']=='private, no-store'
    assert response.headers['x-content-type-options']=='nosniff'
    assert response.headers['etag']=='"'+sha256(response.content).hexdigest()+'"'
    assert len(response.content)<2*1024*1024
    reader=PdfReader(BytesIO(response.content));assert len(reader.pages)==4
    text=' '.join(page.extract_text() for page in reader.pages)
    assert TITLE in text and 'Scientific limitations' in text and 'not fraud probabilities' in text
    assert 'SECRET_' not in text and str(research[5]) not in text
    if dataset=='paysim':
        assert '2 account disagreements' in text and '1-positive and 3-positive' in text
        assert 'Detector metrics unavailable' in text
    else:
        assert 'Sample SD' in text and 'E6_BASE' in text


def test_deterministic_read_only_no_execution(research):
    client,service,_,_,_,root,_=research
    before={p:sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    def forbidden(*a,**k):raise AssertionError('No model or graph execution during export')
    with patch('sklearn.ensemble.IsolationForest.fit',forbidden),patch('joblib.load',forbidden),patch('backend.app.services.graph_service.GraphService.build_graph',forbidden):
        a=dataset_report_service.generate('ibm-5k',service);b=dataset_report_service.generate('ibm-5k',service)
    assert a==b
    assert before=={p:sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('dataset',['unknown','%2e%2e','a%5cb','a%2fb'])
def test_invalid_ids_never_resolve_paths(research,dataset):
    response=research[0].get(f'/api/v1/research-reports/datasets/{dataset}/report.pdf')
    assert response.status_code==404


def test_busy_response_and_get_only(research,monkeypatch):
    import backend.app.api.routes.dataset_reports as module
    monkeypatch.setattr(module,'_slots',BoundedSemaphore(0))
    assert research[0].get('/api/v1/research-reports/datasets/ibm-5k/report.pdf').status_code==429
    for verb in ('post','put','patch','delete'):
        assert getattr(research[0],verb)('/api/v1/research-reports/datasets/ibm-5k/report.pdf').status_code==405


def test_tampered_evidence_fails_closed(research):
    client,service,reg,_,_,_,_=research
    service._path(reg['entries']['datasets']['path']).write_text('{}')
    response=client.get('/api/v1/research-reports/datasets/ibm-5k/report.pdf')
    assert response.status_code==503 and response.json()['error']=='ARTIFACT_CHECKSUM_MISMATCH'


def test_pdf_endpoint_openapi(research):
    from backend.app.main import app
    item=research[0].get(app.openapi_url).json()['paths']['/api/v1/research-reports/datasets/{dataset_id}/report.pdf']
    assert list(item)==['get']
    assert 'application/pdf' in item['get']['responses']['200']['content']
