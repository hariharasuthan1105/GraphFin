"""Read-only Phase 8 preservation and public-schema verification.

Run from any directory with Python. Writes verification evidence outside the repo.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT.parents[1] / 'work/phase8'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    before = json.loads((WORK/'before.json').read_bytes())
    changed = [n for n,h in before.items() if not (ROOT/n).is_file() or sha(ROOT/n) != h]
    allowed = set()
    assert set(changed) == allowed, changed
    assert sha(ROOT/'frontend/src/LegacyApp.tsx') == before['frontend/src/App.tsx']
    protected = json.loads((ROOT/'docs/research/protected_artifacts_v1.json').read_bytes())
    archive = Path('C:/Users/hariharasuthan/Downloads/GraphFin-main.zip')
    assert sha(archive) == protected['source_archive_sha256']
    with zipfile.ZipFile(archive) as z:
        for n,h in protected['files'].items():
            assert sha(ROOT/n) == h, n
            assert hashlib.sha256(z.read('GraphFin-main/'+n)).hexdigest() == h, n
    spec = json.loads((ROOT/'data/results/v2/phase7-api-verification-v1/openapi-final.json').read_bytes())
    public = json.loads((ROOT/'frontend/src/research/contract.schema.json').read_bytes())
    assert all(s == spec['components']['schemas'][n] for n,s in public.items())
    calls = json.loads((WORK/'visual-release/real-api.json').read_bytes())['calls']
    assert len(calls) >= 14 and all(r['method']=='GET' and r['status']==200 for r in calls)
    check = subprocess.run(['git','-c','safe.directory=*','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    assert check.returncode == 0, check.stdout+check.stderr
    files = [p for p in (ROOT/'frontend').rglob('*') if p.is_file() and not any(x in p.parts for x in ('node_modules','dist'))]
    files += [ROOT/'docs/research/08_frontend_dashboard_integration.md']
    inventory = {p.relative_to(ROOT).as_posix():sha(p) for p in files if p.relative_to(ROOT).as_posix() not in before or p.relative_to(ROOT).as_posix() in changed}
    tests = {}
    for name, count in [('browser-tests-complete.json',35), ('affected-tests.json',9),
                        ('adapter-api-tests.json',3), ('seed-final-tests.json',2)]:
        stats = json.loads((WORK/name).read_bytes())['stats']
        assert stats['expected'] == count and stats['unexpected'] == stats['skipped'] == stats['flaky'] == 0, (name,stats)
        tests[name] = stats
    for name in inventory:
        p = ROOT/name
        if p.suffix in ('.ts','.tsx','.css','.py','.md','.json','.html'):
            assert all(line == line.rstrip() for line in p.read_text(encoding='utf-8').splitlines()), name
    report = dict(protected_originals=len(protected['files']),snapshot_files=len(before),unchanged=len(before)-len(changed),
                  changed_existing=changed,legacy_app_byte_identical=True,public_schemas_match=len(public),
                  actual_http_successes=len(calls),git_diff_check_exit=check.returncode,tests=tests,phase8_files=inventory)
    (WORK/'preservation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='phase8_files'},indent=2))


if __name__ == '__main__':
    main()
