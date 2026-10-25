"""Resource/append-only safeguards for the research validation orchestrator."""
from types import SimpleNamespace
import pytest
from backend.scripts import validate_phase6c as validation

def test_existing_record_is_never_overwritten(tmp_path):
    path=tmp_path/'record.json'
    validation.save(path, {'original':True})
    before=path.read_bytes()
    with pytest.raises(FileExistsError):
        validation.save(path, {'replacement':True})
    assert path.read_bytes()==before

@pytest.mark.parametrize('elapsed,rss,reason',[(601,1,'time_budget'),(1,101,'memory_budget')])
def test_child_resource_guard_terminates_only_owned_child(tmp_path,monkeypatch,elapsed,rss,reason):
    class Child:
        pid=12345
        returncode=None
        terminated=False
        def poll(self): return self.returncode
        def terminate(self): self.terminated=True;self.returncode=-1
        def wait(self,timeout): return self.returncode
    child=Child()
    clock=iter([0,elapsed,elapsed,elapsed])
    monkeypatch.setattr(validation.time,'perf_counter',lambda:next(clock))
    monkeypatch.setattr(validation.subprocess,'Popen',lambda *a,**k:child)
    monkeypatch.setattr(validation.psutil,'Process',lambda pid:SimpleNamespace(memory_info=lambda:SimpleNamespace(rss=rss)))
    result=validation.bounded(['test-only'],tmp_path/'worker.log',600,100)
    assert child.terminated and result['stop_reason']==reason and result['exit_code']==-1

def test_successful_child_is_not_terminated(tmp_path,monkeypatch):
    child=SimpleNamespace(returncode=0,poll=lambda:0)
    monkeypatch.setattr(validation.subprocess,'Popen',lambda *a,**k:child)
    result=validation.bounded(['test-only'],tmp_path/'worker.log')
    assert result['exit_code']==0 and result['stop_reason'] is None
