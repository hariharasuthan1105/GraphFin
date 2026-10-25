"""Read-only preservation verification; append a new Phase 7 evidence package."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT.parents[1] / 'work'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    output = ROOT / 'data/results/v2/phase7-api-verification-v1'
    if output.exists():
        raise FileExistsError(output)
    before = json.loads((WORK / 'phase7-state/before.json').read_bytes())
    allowed = {'backend/app/api/router.py', 'docs/research/07_readonly_api_integration.md'}
    changed = [n for n, h in before.items() if not (ROOT/n).is_file() or sha(ROOT/n) != h]
    assert set(changed) == allowed, changed
    protected = json.loads((ROOT/'docs/research/protected_artifacts_v1.json').read_bytes())
    archive = Path('C:/Users/hariharasuthan/Downloads/GraphFin-main.zip')
    assert sha(archive) == protected['source_archive_sha256']
    with zipfile.ZipFile(archive) as z:
        for n, digest in protected['files'].items():
            assert sha(ROOT/n) == digest, n
            assert hashlib.sha256(z.read('GraphFin-main/'+n)).hexdigest() == digest, n
    tests = WORK/'phase7-release-tests/phase2-l1u43zup'
    suites = ET.parse(tests/'final-results.xml').getroot().findall('testsuite')
    counts = {k: sum(int(s.attrib[k]) for s in suites) for k in ('tests','failures','errors','skipped')}
    assert counts == {'tests':119,'failures':0,'errors':0,'skipped':0}, counts
    assert (tests/'final-exit.txt').read_text(encoding='utf-8-sig').strip() == '0'
    perf = json.loads((WORK/'phase7-measurements-v1/performance.json').read_bytes())
    assert len(perf['measurements']) == 14 and all(r['status'] == 200 for r in perf['measurements'])
    check = subprocess.run(['git','-c','safe.directory=*','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    assert check.returncode == 0, check.stdout+check.stderr
    source = ['backend/app/api/router.py','backend/app/api/routes/research.py',
              'backend/app/schemas/research.py','backend/app/services/research_catalog_service.py',
              'backend/app/services/research_catalog_v1.json','backend/tests/test_phase7_research_api.py',
              'backend/scripts/measure_phase7_api.py','backend/scripts/verify_phase7.py',
              'docs/research/07_readonly_api_integration.md']
    for n in source:
        assert all(line == line.rstrip() for line in (ROOT/n).read_text(encoding='utf-8').splitlines()), n
    output.mkdir()
    for folder, name in [(WORK/'phase7-measurements-v1','performance.json'),
                         (WORK/'phase7-measurements-v1','response_examples.json'),
                         (WORK/'phase7-measurements-v1','openapi-final.json'),
                         (tests,'final-results.xml'),(tests,'final-pytest.log'),(tests,'final-exit.txt'),
                         (WORK/'phase7-state','before.json')]:
        shutil.copyfile(folder/name, output/name)
    report = dict(phase='7', protected_zip_matches=len(protected['files']),
                  snapshot_files=len(before), snapshot_unchanged=len(before)-len(changed),
                  allowed_changes=changed, tests=counts, blocked=0, test_exit_code=0,
                  junit_seconds=sum(float(s.attrib['time']) for s in suites),
                  actual_artifact_http_requests=84, measurement_exit_code=0,
                  git_diff_check_exit=check.returncode, source_sha256={n:sha(ROOT/n) for n in source},
                  evidence_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()},
                  limitations=['Local in-process measurements, not deployment/load testing.',
                               'IBM label lineage partially verified; PaySim unresolved.',
                               'No CREST superiority demonstrated.'])
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('protected_zip_matches','snapshot_unchanged','tests','git_diff_check_exit')}))


if __name__ == '__main__':
    main()
