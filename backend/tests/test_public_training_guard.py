import pytest


@pytest.mark.parametrize("environment", ["RENDER", "GRAPHFIN_GATEWAY_ENV"])
def test_public_entry_point_blocks_mutations(client, monkeypatch, environment):
    monkeypatch.setenv(environment, "true" if environment == "RENDER" else "production")
    for path in ["/api/v1/transactions/upload", "/api/v1/anomalies/nonexistent/train", "/api/v1/anomalies/nonexistent/baseline"]:
        response = client.post(path, json={})
        assert response.status_code == 403
        assert response.json()["error"] == "PUBLIC_RESEARCH_READ_ONLY"
    assert client.get("/health").status_code == 200


def test_local_research_is_not_blocked(client, monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("GRAPHFIN_GATEWAY_ENV", raising=False)
    # The normal route validates a missing file; the hosted guard does not intercept it.
    assert client.post("/api/v1/transactions/upload").status_code == 422
