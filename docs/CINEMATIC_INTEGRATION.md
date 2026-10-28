# Cinematic GraphFin integration validation

## Scope

Added a sidebar-free cinematic cover using environment-only artwork derived from the supplied reference; real React navigation and action cards; shared pixel/system/monospace typography across all eleven application pages; restrained transitions and reduced-motion support. Existing research algorithms and saved data files are unchanged.

Dataset ingestion now rejects over-limit CSV/JSON inputs without silently truncating, records accepted/rejected/source totals and input-text SHA-256, exposes inspection tabs, and preserves the active in-memory session across navigation. Unknown currency no longer defaults to USD. Backend execution remains consent-gated and cannot be reconstructed from aggregated edges; requests are bounded to 1,000 account scores. Replacing a dataset resets backend state and ignores late results for old sessions.

Removed unsupported uploaded-session replay and seed-stability claims. Historical model comparisons use exact saved metrics only when dataset, label, train, test and population hashes match. Report metadata excludes raw CSV; PDF preview uses the actual generated report.

## Checks

- TypeScript and Vite production build: pass.
- Source lint: no errors; four existing React lifecycle/fast-refresh warnings remain.
- Existing frontend recovery suite: 7/7 pass; additional parser bounds, rejection counts, unknown currency and metadata-redaction assertions pass. Run node tests/test_typography_integration.cjs after npm --prefix frontend ci.
- Backend regressions in disposable verify_phase2.py checkout: 149/149 pass (currency, PDF, features, anomalies, research API, graph explorer).
- Browser matrix: 70/70 pass; 12 views at 1440x1000, 834x1112 and 390x844, mobile drawer, keyboard-accessible graph selection, camera controls, safe consent, PDF download, responsive overflow and reduced motion.
- 125% and 150% CSS layout zoom checked on cover, overview, datasets and graph. This does not certify every platform's native browser zoom UI.
- Focused workflow checks: invalid JSON/schema, offline consented request, checksum copy, metadata tabs, JSON redaction, PDF download, dataset replacement and independent sidebar scroll pass.
- No critical JavaScript exceptions in browser matrix; API failures intentionally intercepted to exercise saved-evidence fallback. No financial data sent to real servers during testing.
- Production dependency npm audit: zero reported vulnerabilities.

## Performance and remaining limits

Cover WebP: 328,638 bytes; application header WebP: 210,582 bytes. Pixel/mono fonts are bundled open-license assets; system sans needs no font request. Graph and report code remain lazy route chunks. The graph uses bounded SVG/d3 2.5D rendering, not WebGL, with explicit scope disclosure and no continuous simulation loop.

Uploaded sessions are in-memory and clear on browser refresh. Historical raw graph topology and formal uploaded-session multi-seed/held-out evaluation remain unavailable; UI discloses those limits. Backend ML success was not claimed or tested against a live upload; blocked/unavailable behavior was tested. Exact pixel identity across aspect ratios is not promised; mobile artwork preserves the globe and astronaut while controls reflow.
