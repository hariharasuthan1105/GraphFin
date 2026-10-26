"""Release tooling checks; no real keys, model fits or research jobs."""
import json
import pytest
from backend.scripts.audit_release import secret_findings, write_exclusive


def test_pattern_audit_redacts_values():
    sample = b"ghp_" + b"A" * 36
    findings = secret_findings(sample)
    assert findings == {"github_token": 1}
    assert sample.decode() not in json.dumps(findings)


def test_audit_output_is_exclusive(tmp_path):
    output = tmp_path / "audit.json"
    write_exclusive(output, {"first": True})
    before = output.read_bytes()
    with pytest.raises(FileExistsError): write_exclusive(output, {"first": False})
    assert output.read_bytes() == before


@pytest.mark.parametrize("base", ["https://127.0.0.1", "http://example.invalid", "http://user:password@127.0.0.1"])
def test_probe_rejects_nonlocal_or_credential_urls(base, monkeypatch):
    from backend.scripts.verify_final_api import verify
    def forbidden(*args, **kwargs): raise AssertionError("Network must not start")
    monkeypatch.setattr("httpx.Client", forbidden)
    with pytest.raises(ValueError, match="local demonstration"): verify(base)
