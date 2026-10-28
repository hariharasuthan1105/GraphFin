# Post-release stability and ML correctness audit

Starting release: `6edeaa8cc36f9c26aeadfc32017791c248f64de2`.
Local and remote HEAD matched; working tree was clean before changes. No redesign, artwork changes, research algorithm changes or saved historical evidence changes.

## Verified defects and fixes

- Uploaded sessions had no recovery. Added explicit IndexedDB snapshots with Save analysis locally and Clear saved session. No automatic saving. Raw CSV and preview rows are excluded; account identifiers, aggregated amounts, results and graph mode/selection are retained only after the user chooses Save. Snapshots expire after seven days and are deleted on the next visit. Dataset replacement removes the prior snapshot. Saves are bounded to 12 MB; quota/restricted-storage errors remain visible without claiming success. Saving again updates the snapshot. Clearing does not close the current in-memory analysis. Camera zoom and search filters are not retained.
- Backend upload/training/score requests had no deadline. Each now has a 30-second timeout, including body download, without automatic POST retries. A client timeout does not cancel a job already accepted by a server.
- Partial, mismatched or malformed ML responses could be labelled verified. Verification now requires matching dataset identity, accepted-record count, IsolationForest metadata with the canonical ordered 19 features, 100 trees, correct entity count, and complete unique account mappings with finite raw/risk scores and valid predictions. Raw ML scores remain distinct from unchanged heuristic scores.
- Unknown transaction labels were implicitly negative in evaluation. Formal account evaluation is now withheld when any transaction label is unknown. Transaction label counts are displayed separately from account review flags.
- Average precision depended on order among tied scores. Ties now enter together at each score threshold. Scoring weights and review thresholds did not change.
- `topAnomalies` contained five accounts even when none were flagged. It now contains only flagged accounts. Graph review highlighting now uses the same flag, instead of treating every structural motif as suspicious.
- Self-transfers could masquerade as reciprocal/multihop cycles; string-delimited edge keys could collide. Cycles require distinct vertices, reciprocal transfers require different endpoints, tuple keys distinguish edges, and density excludes self-loops.
- PDF truncated the only dataset filename and described an incomplete review rule. Full filename, transaction-label counts, heuristic column title, account recall and all three flag conditions are now explicit. Optional local-retention wording replaces the ephemeral-only statement.
- Four previous lint warnings were resolved by separating context/provider exports, deriving graph layout with memoization, removing mirrored result state and initializing URL sample configuration once. URL sample autostart now updates the shared session.

## Synthetic benchmark findings

The existing user-supplied 1,000-account / 10,000-transaction INR fixture was parsed without rejection. No raw fixture was added to the repository.

| Quantity | Result |
|---|---:|
| Source / accepted / rejected | 10,000 / 10,000 / 0 |
| Transaction labels normal / anomalous / unknown | 9,600 / 400 / 0 |
| Accounts associated with positive transaction labels | 328 |
| Accounts flagged for heuristic review | 9 |
| Unique directed edges | 9,860 |
| Transaction volume | INR 27,216,411.41 |
| Volume outliers / fan-in / fan-out / noteworthy cycles | 12 / 4 / 4 / 0 |
| Account precision / recall / F1 | 1.0000 / 0.0274 / 0.0534 |
| Tie-aware average precision | 0.5211 |

Nine review flags and the account-volume calculation were already correct in the starting release. This audit does not claim those were newly repaired. Average precision was previously 0.5214. The synthetic label convention is association with at least one positive transaction, not independently confirmed fraud. Low recall remains a material limitation. Fan-in/out use transaction incidences, not unique-counterparty degree. The cycle detector is bounded to high-frequency reciprocal exchange and qualifying 3/4-hop loops, not arbitrary-length cycle enumeration.

## ML and public-hosting verification

Local Python tests actually execute Isolation Forest, verify canonical 19-feature extraction, entity counts and prediction mapping. They do not certify public inference. Public `/health` and `/api/v1/health` returned 200. `/api/v1/openapi.json` advertised the full local API and a training route without declared authentication, unlike the repository's intended read-only gateway. A no-data probe with a nonexistent dataset ID timed out; no valid dataset was sent and no live training success is claimed.

The local research entry point now blocks mutating requests when `RENDER=true` or `GRAPHFIN_GATEWAY_ENV=production`. Existing gateway authentication/read-only controls remain unchanged. Local research training is preserved. Render auto-deployment is disabled in the repository blueprint, and no authenticated Render deployment access was available for this audit: applying/verifying this guard on the running backend requires a separate backend deployment. Do not treat the public service as verified or safe for visitor financial uploads. The interface states: “Client-side graph analysis available; backend ML inference not verified.”

## Validation actually executed

- Baseline reproduced: 149 backend tests, 70 browser checks, 10 focused workflow checks, original 7 frontend analysis tests.
- Final backend: 152 passed (149 baseline plus 3 hosted-mutation guard tests), in a disposable checkout.
- Gateway authentication/read-only suites: 16 passed in an isolated checkout.
- Final TypeScript and production build passed; lint has zero errors and zero warnings.
- Original 7 frontend tests and additional typography/parser tests passed; `node tests/test_stability.cjs` passed aggregation, reciprocal/self-loop semantics, edge identity, empty flags, partial labels, tied AP, snapshot privacy, ML metadata/mapping and request timeout assertions.
- Responsive browser matrix: 70/70 passed. Focused invalid-schema, unavailable-backend, consent, exports, replacement and navigation checks: 10/10 passed.
- Added recovery/benchmark workflow checks: 16/16 passed, including refresh, new tab, clearing, replacement, expiry, quota/restricted storage, back/forward, no transmission, bounded graph and exactly nine review highlights.
- Actual benchmark report downloaded through the UI: three pages rendered and visually inspected; automated text checks match filename, counts, INR volume, scoring method, flags and unverified ML state. No clipping or overlap observed in these pages.
- Benchmark upload-to-results browser flow was approximately 2.4 seconds on the test machine, including navigation. Graph remains capped at 60 visible nodes. This is not a cross-device performance guarantee.

No historical IBM AML, PaySim, E0–E6 or CREST artifacts were edited. No secrets or raw financial datasets are part of this patch. Remaining constraints include low synthetic account recall, browser-managed storage availability/eviction, explicit snapshot updates, unavailable public inference verification, and the pending Render deployment described above.
