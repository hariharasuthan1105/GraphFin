# Deploying GraphFin Backend to Render

This guide outlines how to deploy the GraphFin FastAPI backend to [Render](https://render.com) and link it with the GitHub Pages frontend.

---

## 1. Prerequisites
- A free [Render account](https://dashboard.render.com).
- Access to your GitHub repository: `https://github.com/hariharasuthan1105/GraphFin`.

---

## 2. Deployment Options

### Option A: Render Blueprint (Recommended — 1-Click Auto Setup)
Render can read the repository's [`render.yaml`](render.yaml) blueprint file to configure the web service automatically:

1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** in the top navigation bar and select **Blueprint**.
3. Connect your GitHub account (if not already connected) and select the **`GraphFin`** repository.
4. Render will detect `render.yaml` with the following configuration:
   - **Service Name**: `graphfin-backend`
   - **Environment**: `Python`
   - **Plan**: `Free`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/v1/health`
   - **Environment Variables**:
     - `PYTHONPATH`: `.`
     - `PYTHON_VERSION`: `3.12.10`
     - `CORS_ORIGINS`: `https://hariharasuthan1105.github.io,http://localhost:5173,http://localhost:3000`
5. Click **Apply**. Render will trigger the initial build and deploy the web service.

---

### Option B: Manual Web Service Setup
If you prefer creating a standalone Web Service without Blueprints:

1. On the [Render Dashboard](https://dashboard.render.com), click **New +** $\rightarrow$ **Web Service**.
2. Select **Build and deploy from a Git repository** $\rightarrow$ connect `GraphFin`.
3. Fill in the service parameters:
   - **Name**: `graphfin-backend`
   - **Region**: Closest to your users (e.g., `Singapore`, `Frankfurt`, or `Ohio`)
   - **Branch**: `main`
   - **Root Directory**: *(Leave empty)*
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Expand **Advanced** settings:
   - **Health Check Path**: `/api/v1/health`
   - **Environment Variables**:
     | Key | Value |
     |:---|:---|
     | `PYTHONPATH` | `.` |
     | `PYTHON_VERSION` | `3.12.10` |
     | `CORS_ORIGINS` | `https://hariharasuthan1105.github.io,http://localhost:5173,http://localhost:3000` |
5. Click **Create Web Service**.

---

## 3. Verify Deployment

Once Render displays **"Your service is live"**, copy your service URL (e.g., `https://graphfin-backend.onrender.com`):

1. **Health Check**:
   ```bash
   curl https://<your-render-subdomain>.onrender.com/api/v1/health
   # Expected response: {"status":"healthy"}
   ```
2. **Interactive API Docs (Swagger UI)**:
   Navigate to:
   ```
   https://<your-render-subdomain>.onrender.com/docs
   ```

---

## 4. Connect Frontend to the Deployed Backend

The GitHub Pages workflow automatically injects the backend API URL into Vite during the build step using the repository variable `VITE_API_URL`:

1. Open your repository on GitHub: `https://github.com/hariharasuthan1105/GraphFin`.
2. Go to **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
3. Under the **Variables** tab, click **New repository variable**.
4. Set:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://<your-render-subdomain>.onrender.com` *(no trailing slash)*
5. Click **Add variable**.
6. Trigger the frontend deployment:
   - Go to **Actions** $\rightarrow$ **Deploy GraphFin Frontend** $\rightarrow$ Click **Run workflow** (or push a commit to `main`).
7. Your GitHub Pages site at `https://hariharasuthan1105.github.io/GraphFin/` will now query the Render backend.

> [!NOTE]
> On Render's Free tier, the web service spins down after 15 minutes of inactivity. The first request after spindown may take 30–50 seconds to wake up the service.
