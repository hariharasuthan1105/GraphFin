"""
End-to-end verification script for Financial Anomaly Detection API.
Executes requests against all dataset-scoped endpoints and displays responses.
"""
import json
from pathlib import Path
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

print("=" * 60)
print("1. Testing GET /api/v1/health")
health_resp = client.get("/api/v1/health")
print(f"Status: {health_resp.status_code}")
print("Response:", json.dumps(health_resp.json(), indent=2))

print("\n" + "=" * 60)
print("2. Testing POST /api/v1/transactions/upload with sample dataset")
sample_csv_path = Path("data/raw/sample_transactions.csv")
with open(sample_csv_path, "rb") as f:
    upload_resp = client.post(
        "/api/v1/transactions/upload",
        files={"file": ("sample_transactions.csv", f, "text/csv")},
    )
print(f"Status: {upload_resp.status_code}")
upload_data = upload_resp.json()
print("Response:", json.dumps(upload_data, indent=2))
dataset_id = upload_data["dataset_id"]
print(f"\nCaptured dataset_id: {dataset_id}")

print("\n" + "=" * 60)
print(f"3. Testing GET /api/v1/transactions/{dataset_id}/status")
status_resp = client.get(f"/api/v1/transactions/{dataset_id}/status")
print(f"Status: {status_resp.status_code}")
print("Response:", json.dumps(status_resp.json(), indent=2))

print("\n" + "=" * 60)
print(f"4. Testing GET /api/v1/transactions/{dataset_id}/summary")
summary_resp = client.get(f"/api/v1/transactions/{dataset_id}/summary")
print(f"Status: {summary_resp.status_code}")
print("Response:", json.dumps(summary_resp.json(), indent=2))

print("\n" + "=" * 60)
print(f"5. Testing GET /api/v1/graph/{dataset_id}/summary")
graph_resp = client.get(f"/api/v1/graph/{dataset_id}/summary")
print(f"Status: {graph_resp.status_code}")
print("Response:", json.dumps(graph_resp.json(), indent=2))

print("\n" + "=" * 60)
print(f"6. Testing GET /api/v1/graph/{dataset_id}/nodes/USR_ALICE")
node_resp = client.get(f"/api/v1/graph/{dataset_id}/nodes/USR_ALICE")
print(f"Status: {node_resp.status_code}")
print("Response:", json.dumps(node_resp.json(), indent=2))

print("\n" + "=" * 60)
print(f"7. Testing GET /api/v1/analytics/{dataset_id}/users?limit=3")
analytics_resp = client.get(f"/api/v1/analytics/{dataset_id}/users?limit=3")
print(f"Status: {analytics_resp.status_code}")
print("Response:", json.dumps(analytics_resp.json(), indent=2))

print("\n" + "=" * 60)
print("8. Testing GET /api/v1/analytics/features/schema (global schema)")
schema_resp = client.get("/api/v1/analytics/features/schema")
print(f"Status: {schema_resp.status_code}")
print("Response:", json.dumps(schema_resp.json(), indent=2))

print("\n" + "=" * 60)
print("9. Testing Negative Case: Upload invalid CSV (negative amount in strict mode)")
bad_csv = (
    "transaction_id,sender_id,receiver_id,amount,timestamp\n"
    "TX_BAD,USR_A,USR_B,-50.0,2026-03-01 10:00:00\n"
)
bad_resp = client.post(
    "/api/v1/transactions/upload?strict_mode=true",
    files={"file": ("bad.csv", bad_csv.encode(), "text/csv")},
)
print(f"Status: {bad_resp.status_code}")
print("Response:", json.dumps(bad_resp.json(), indent=2))

print("\n" + "=" * 60)
print("10. Testing Negative Case: Querying non-existent dataset ID")
random_id = str(uuid.uuid4())
missing_resp = client.get(f"/api/v1/transactions/{random_id}/summary")
print(f"Status: {missing_resp.status_code}")
print("Response:", json.dumps(missing_resp.json(), indent=2))
print("=" * 60)
