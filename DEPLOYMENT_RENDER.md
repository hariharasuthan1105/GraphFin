# Deploying GraphFin to Render (Free Tier Single-Service)

**Project Title:** `Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions`  
**Repository:** [https://github.com/hariharasuthan1105/GraphFin](https://github.com/hariharasuthan1105/GraphFin)  
**Target URL:** [https://graphfin.onrender.com](https://graphfin.onrender.com/)  
**Plan:** Free Tier ($0 / ₹0)

---

## 1. Single-Service Architecture

GraphFin runs as a consolidated Free Tier Web Service:
- **Frontend:** Compiled React + Vite Research Dashboard (SPA served at `/`)
- **Gateway:** Authenticated FastAPI reverse proxy & session management
- **Backend:** In-process read-only research API (`/api/v1/research/*`, `/api/v1/graph-explorer/*`)
- **PDF Reports:** In-process institutional dataset evidence PDF generation

---

## 2. Render Web Service Configuration

In the [Render Dashboard](https://dashboard.render.com), configure your existing service **`graphfin-backend`** or deploy from Blueprint:

| Setting | Value |
| :--- | :--- |
| **Service Name** | `graphfin-backend` |
| **Repository** | `https://github.com/hariharasuthan1105/GraphFin` |
| **Branch** | `main` |
| **Root Directory** | *(leave blank / repository root)* |
| **Runtime** | `Python 3` |
| **Instance Type** | `Free` ($0) |
| **Build Command** | `npm --prefix frontend ci && npm --prefix frontend run build && python -m pip install -r requirements.txt` |
| **Start Command** | `python -m uvicorn gateway.single_service:app --host 0.0.0.0 --port $PORT --workers 1` |
| **Health Check Path** | `/health` |

---

## 3. Environment Variables

Configure these variables under **Environment** in the Render Dashboard:

| Key | Value | Description |
| :--- | :--- | :--- |
| `GRAPHFIN_GATEWAY_ENV` | `production` | Enforces production security, cookies & headers |
| `GRAPHFIN_DEPLOYMENT_MODE` | `single_service` | Activates in-process read-only research API |
| `GRAPHFIN_SESSION_SECRET` | *(64-hex token)* | 256-bit cryptographically secure session signing key |
| `EXAMINER_USERNAME` | `examiner` | Examiner login identifier |
| `EXAMINER_PASSWORD_HASH` | *(scrypt hash)* | Salted scrypt password hash (`scrypt$16384$8$1$...`) |
| `PYTHON_VERSION` | `3.11.9` | Python runtime version |
| `PORT` | `10000` | Port assigned by Render runtime |

> [!NOTE]
> Fresh production credentials can be generated locally using:
> ```bash
> python scripts/generate_production_secrets.py
> ```
> Values are saved locally to the gitignored file `.env.production.local`. Never commit production secrets to Git.

---

## 4. Verification

After deployment, verify the live service:

1. **Homepage:** Visit `https://graphfin.onrender.com/` — the new Research Dashboard will load.
2. **Health Check:** `curl -i https://graphfin.onrender.com/health` returns `{"status":"healthy","service":"graphfin-web","mode":"single_service","role":"public-research-service"}`.
3. **Examiner Login:** Click **Examiner Login** in the top navigation to authenticate and unlock protected research routes.
