"""Convenience script to run GraphFin Single-Service Web Application locally."""
import os
import sys
from pathlib import Path
import uvicorn

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))
env_file = Path(__file__).resolve().parents[1] / ".env.production.local"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

os.environ["GRAPHFIN_DEPLOYMENT_MODE"] = "single_service"
port = int(os.environ.get("PORT", "10000"))

if __name__ == "__main__":
    print(f"\n=======================================================")
    print(f"GraphFin Research Dashboard running locally:")
    print(f"URL: http://localhost:{port}")
    print(f"=======================================================\n")
    uvicorn.run("gateway.single_service:app", host="127.0.0.1", port=port, log_level="info")
