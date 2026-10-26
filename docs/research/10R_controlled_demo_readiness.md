# Phase 10R - Controlled demonstration readiness

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

25 October 2026. Scope: an operator-controlled local demonstration and source-review preparation. No release, submission, model fit, new experiment, commit, push, merge or deployment is authorized or performed.

## Recovery and minimal remediation

The existing publication checkout remains on local `feature/phase9-graph-explorer`, HEAD `2fc9a729efb015029a559c6c2c0f71814ec4e662`. Current remote heads were read without fetch/merge: the published `feature/institutional-dataset-pdf` still points to this commit; remote main is `7141ac8223ac0b922a81c7267615eb4abfaef4ad`. HEAD and the published feature reference have zero commits of divergence. The local Phase 9 branch has no tracking upstream configured; none was changed.

The 422-file pre-remediation snapshot includes all available Phase 9/10 source, documentation, supplied data and versioned serving/index files. Existing changes were not discarded. Only README's current startup guidance and the ignore file receive additive/corrective edits; prior Phase 9/10 implementation, results and reports are preserved. The actual Git staging area was initially empty and is not used for the candidate audit.

Phase 10 correctly identified that `--lifespan off` avoids startup computation but leaves the legacy routers exposed. The smallest practical correction is a separate entry point, `backend/app/research_demo.py`, rather than editing the original application or research algorithms. Its default app:

- Mounts only saved research, institutional PDF, bounded graph and health routes.
- Does not import `backend.app.main` or `backend.app.api.router`; it has no legacy preload lifespan.
- Accepts only loopback peers, including IPv4/IPv6 loopback; remote peers cannot gain access with a forwarded header.
- Requires a loopback Host, rejects malformed/duplicate Host and Origin headers, and uses an exact local-origin allowlist.
- Allows GET only; operational HTTP methods and websockets are denied before handlers.
- Disables API docs/OpenAPI by default. Explicit docs opt-in exposes only the restricted schema.
- Adds private/no-store and nosniff to successful and denied responses. It does not enable CORS wildcard/credentials.

This is a local access boundary, not user authentication or public-host certification. Do not expose the backend or Vite server through a tunnel/reverse proxy that makes outside callers appear local. Pseudonymized topology retains structural reidentification risk. The original full application remains unchanged for separately trusted operational use and must not be confused with this profile.

## Current startup commands

Use approved, already available local artifacts and the existing optional research environment. No dependency upgrade or graph rebuild is required by this phase.

```powershell
# Repository root; docs disabled and browser origins restricted to the local dev server.
$env:GRAPHFIN_DEMO_ENABLE_DOCS='0'
$env:GRAPHFIN_DEMO_ORIGINS='http://127.0.0.1:5173,http://localhost:5173'
python -m uvicorn backend.app.research_demo:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

In a second terminal:

```powershell
cd frontend
$env:VITE_RESEARCH_API_URL='/'
npm run dev -- --config vite.research.config.ts --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/GraphFin/`. Use the same-origin `/api` proxy, not direct browser CORS access. `GRAPHFIN_DEMO_ORIGINS` may contain exact loopback origins only; a public host, wildcard or credential-bearing URL fails configuration validation. An empty value allows no Origin-bearing requests. `GRAPHFIN_DEMO_ENABLE_DOCS` accepts only `0` or `1`; omit it or use `0` for the least permissive profile. There is no flag to reenable legacy routes in this app.

For an existing production build, use `npm run preview -- --config vite.research.config.ts --host 127.0.0.1 --port 4190` and explicitly add that loopback origin if needed. Phase 10R tested preview 4290 and dev 5290, configured as exact allowed origins. Frontend application inputs match the Phase 10 locked build; that successful build was reused, not rebuilt or presented as new installation evidence. The `/GraphFin/` base remains unchanged; no production host is selected.

The supplied source/label files, 35 pinned serving assets and existing private topology bundle remain local. Missing evidence must stay unavailable rather than fabricated. Permission to use local research materials does not grant public redistribution or disclosure to an unrestricted audience.

## Accessible and absent routes

|Surface|Controlled profile behavior|
|---|---|
|GET `/health`, `/api/v1/health`|Health/mode only; `public_deployment_approved=false`|
|GET `/api/v1/research/*`|Existing fourteen saved-evidence operations, same versions/population checks|
|GET `/api/v1/research-reports/datasets/{id}/report.pdf`|Existing three-dataset report service|
|GET `/api/v1/graph-explorer/{catalog,session,neighborhood}`|Existing fixed-lens/session/size/query limits unchanged|
|Legacy `/graph`, `/analytics`, `/datasets`, `/transactions`, `/anomalies`, `/evaluation`, `/reports`, `/stream`, `/tax`|Not mounted; tested legacy GETs return 404|
|Training/upload/mutation HTTP requests|405 `DEMO_READ_ONLY`; no operational handler runs|
|Websocket operational access|Closed with code 1008|
|Docs/OpenAPI default|404; opt-in schema contains only 20 GET paths including both health aliases|

The original legacy frontend entry is retained, but its operational APIs are intentionally unavailable under this profile. Research overview, dataset metadata, comparisons, seeds, reproducibility, saved diagnostics, graph exploration and PDF downloads still work. Do not interpret a rendered legacy shell as permission to upload or train.

## Executed validation

|Run/check|Actual result|Exit/evidence under task `work/phase10r`|
|---|---|---|
|Initial combined backend run|124 passed, 24 setup errors, 94.06 s. All 113 existing research/graph/PDF cases passed; new fixture-dependent cases lacked an explicit `research` fixture import.|1; `backend.log`, disposable JUnit/log|
|Corrected new-profile run|35 passed, 26.04 s|0; `backend-profile-final.log`, JUnit|
|Expanded final boundary suite|44 passed, 25.52 s; peer spoofing, Host/origin, docs, websocket, startup/no-computation and real synthetic fixture projections|0; `backend-boundary.log`, JUnit|
|Actual browser workflow|4 passed, 53.2 s: profile denials; complete saved-evidence workflow; three genuine PDFs; actual sparse/dense graph and available/unavailable diagnostics|0; `browser-live.json/log`, exit file|
|Frontend/API startup and bind|Health/HTML 200; all three listeners at `127.0.0.1` only; legacy endpoints 404|0; `startup-bindings.json`|
|Shutdown|Recorded task PIDs exited and all three listening sockets were absent|0; `shutdown-final.json`|
|Preservation, candidate and diff checks|Final exact results are in the safe-commit report and verification manifest|See final audit|

Distinct successful backend coverage is **157 cases**: 113 unchanged cases plus the final 44 profile cases. Repeated/debug runs are not added as independent cases. Four actual browser cases passed against the restricted app, rather than using fabricated production data. Final selected tests have no unresolved failures/skips/environment blocks. The initial missing-fixture error was test discovery, not an application fix; its evidence is retained.

The first immediate HTTP shutdown poll timed out. Subsequent process/listener inspection confirmed all recorded PIDs had already exited after interruption; no additional process was stopped. Shell interrupt exit 1 is an intentional shutdown mechanism, not a passed test-runner exit. Unrelated existing tabs/servers were not stopped.

The new import-isolation and startup spies confirm no fit, model load, graph construction or PaySim preload is invoked by the controlled entry. Graph source/scope and saved scores remain unchanged; nothing is recomputed to make the demo appear successful. Existing Phase 10 PDF visual/numerical QA is preserved; no PDF design/generator rewrite or new resource embedding occurred.

Final preservation checks found **87/87 protected originals identical to both their manifest and supplied ZIP**, **35/35 pinned serving assets unchanged**, and **420/422 pre-remediation files byte-identical**. The two intentional edits are README startup guidance and an appended browser-harness ignore rule. All inherited Phase 9/10 implementation, scientific results and manuscript files remain unchanged. Phase 10R adds nine files. The normal working-tree `git diff --check` passes; candidate CRLF behavior is reported separately rather than hidden.

## Four separate decisions

|Decision|Status|Boundary|
|---|---|---|
|Controlled local demonstration|**GO**|Operator-controlled, loopback-only, approved local artifacts, documented command and explicit scientific limits. This is not clearance for an unrestricted audience or tunnel.|
|Safe public source-code commit from the present repository|**NO-GO until the release base is resolved**|A source-only proposed delta is auditable, but the parent tree/history already includes data and identity-bearing artifacts. Excluding new data additions does not clear that parent.|
|Unrestricted public deployment|**NO-GO**|Local peer/origin restrictions are not authenticated multiuser/public hosting, distributed quotas or formal anonymity.|
|IEEE manuscript submission|**NO-GO**|Critical-review draft and checklist available; provenance, validation scope, authors and venue requirements remain unresolved.|

Phase 10R completes the controlled-demo remediation and review preparation. It does not manufacture permission clearance or a positive public/submission gate. No commit, push, merge, public deployment or submission occurred.
