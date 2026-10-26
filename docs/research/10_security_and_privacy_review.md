# Phase 10 - Security and privacy review

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Review date: 25 October 2026. Keep the complete application **loopback-only for a controlled research demonstration**. Unrestricted public deployment is **NO-GO**. This is source/configuration review and bounded regression/probe evidence, not penetration-test certification. No production security settings were weakened.

## Assets and trust boundaries

Assets include supplied transactions/labels, pinned scores/diagnostics, private SQLite indexes and identity maps, graph capabilities, model persistence and reports. Threat actors include anonymous callers, browsers on allowed/untrusted origins, recipients joining topology to published source files, and local users able to change evidence. Hashes assume trusted pins and immutable local storage; replacing both evidence and its pin defeats that assumption.

1. `/api/v1/research/*`: fourteen GET operations, allowlisted bounded JSON reads, checksums, explicit population identities and pseudonym projection.
2. `/api/v1/research-reports/datasets/{id}/report.pdf`: three approved datasets, escaped server-derived text, fixed filename, two concurrent builds per worker and 2 MiB output limit.
3. `/api/v1/graph-explorer/{catalog,session,neighborhood}`: fixed source/snapshot/lens, ephemeral capabilities and bounded queries/layouts.
4. Preserved legacy APIs: uploads, mutable datasets, graph/features, training, evaluation, reports, simulation and tax. They do not inherit the new research projection's privacy/computation guarantees.
5. Git distribution: tracked synthetic source/label/score files themselves contain raw account identities. UI pseudonyms do not conceal data included in a recipient's checkout.

## Findings

|ID|Severity and observed evidence|Required release action|
|---|---|---|
|S1|HIGH: live OpenAPI exposes 62 operations without standard security requirements. Graph neighborhoods require a capability header, but no user authentication/authorization boundary is configured.|Do not expose the full backend anonymously. Isolate/authenticate an allowlisted research service and block legacy mutation/training paths before deployment.|
|S2|HIGH: legacy upload calls `await file.read()` before parsing; no reviewed global ingress-size/rate limit. Legacy graph/feature/training requests can invoke expensive work.|Bound ingress, execution time and principal-level concurrency; separate jobs from serving. New graph/PDF limits do not constrain the rest of the application. No flood test was run.|
|S3|HIGH: legacy projections and tracked research files retain synthetic raw IDs. Degrees, amounts, timestamps and neighborhoods permit structural joins.|Pseudonymization is not anonymity. Review repository and API disclosure together, including count-one aggregates and time-window probing.|
|S4|HIGH: exact redistribution permission/lineage for supplied transformed IBM/PaySim files is not established.|No unrestricted data-bearing release. Obtain source/grant/notice records; preserve historical files while deciding a separately approved release package.|
|S5|MEDIUM: credentialed CORS includes declared local/public origins; `Settings.CORS_ORIGINS` appends fixed origins despite environment overrides.|CORS is not authentication. Review deployment-specific origins and access controls. Actual preflight checks: untrusted origin 400, declared local origin 200.|
|S6|MEDIUM: global validation logs `exc.errors()`; legacy startup logs paths/IDs and calls a preferred PaySim file “ground-truth” despite unresolved provenance.|Restrict/redact logs and qualify legacy terminology before public service. New graph validation omits capability-bearing inputs and its errors are regression tested.|
|S7|MEDIUM: legacy persistence calls `joblib.load`; model paths interpolate dataset/experiment/split identifiers.|Load only trusted server-owned models. Adversarial review of legacy path/identifier boundaries remains necessary; no remote-code-execution exploit is asserted here. New research routes do not deserialize models.|
|S8|MEDIUM: graph quotas are process-local; new sessions reset query budgets and multiple workers multiply throughput.|Repeated sessions cannot expand the fixed 600-account pool, but can reconstruct more relationships within it. Add authenticated, distributed quotas before changing exposure.|
|S9|MEDIUM: normal lifespan automatically processes legacy data. Logs span 19:02:58-19:07:08 with PaySim feature extraction and preferred-label loading.|Use documented `--lifespan off` for saved-evidence demonstration. This skips preload, not research validation. The host-contended interval is not a graph-query benchmark.|
|S10|LOW/MEDIUM: root ignore rules did not protect local `.env` overrides.|Fixed additively; examples and tracked frontend production URL config remain intentional. Ignore rules do not protect already tracked secrets.|
|S11|MEDIUM: Actions builds the legacy entry; Python requirements are broad lower bounds; unsaved browser tooling changed the installed Vite tree.|No automatic workflow dispatch. Document research config/base/API settings, test the lockfile build, and add optional observed constraints/psutil. Cross-platform installation is not certified.|

## Graph protection and residual disclosure

Capabilities are random 32-character values sent in `X-Graph-Session`, not URLs. Node/edge references are HMAC-derived per session; cross-session/dataset/worker substitution fails. Dataset hash, cutoff, version and index identity bind the snapshot. Limits are TTL 600 s, 16 sessions/worker, 20 queries/session, 600 grants, 1-2 hops, 250 nodes, 500 edges, 512 KiB response, bounded adjacency work, four admitted requests and a 1.5 s SQLite VM deadline. Allowlisted files are hash-checked/read-only; linked paths and unsupported populations fail closed. Abort, expiry and worker cleanup prevent stale rendering.

These controls prevent arbitrary account search, token reversal, unrestricted traversal, row export and API-triggered experiments **through the new namespace**. They do not guarantee anonymity, prevent reconstruction of the approved pool, conceal full-snapshot node statistics, enforce distributed quotas or secure legacy routes. A single-event aggregate can reveal its amount; time probes reveal patterns. Inspectors do not disclose omitted transaction IDs or fabricate deleted-edge overlays. Saved full-snapshot scores are not recomputed under filters.

Current recommendation: controlled local demonstration with understood source permissions. A hosted demonstration needs authentication, namespace restriction, disclosure assessment and deployment limits. Do not expose all 62 operations because the dashboard itself uses GET.

## PDF, files and serialization

Only three server-selected dataset IDs reach PDF generation. No client path, URL, template, filename or report text is accepted. Filename construction follows allowlisting; ReportLab paragraph content is escaped. MIME/signature, Content-Disposition, nosniff, no-store, byte and concurrency guards are tested. Reports contain supported aggregate statistics and hashes, not transaction rows/raw IDs. Actual unknown/traversal-shaped PDF requests return 404. Missing/tampered artifacts fail closed in isolated regressions.

Research catalog paths reject absolute/traversal/backslash/linked/non-JSON/unapproved paths. Graph files have equivalent allowlisting, size and checksum checks. These reviewed paths do not establish equivalent protection across every historical operational API. Unhandled HTTP errors omit details unless debug is enabled, while operator logs may still contain exception details; debug/log configuration needs review before hosting.

## Repository, dependencies and permissions

Initial `audit_release.py` scan: 44 local HEAD-reachable revisions, 527 distinct blobs, zero configured credential-pattern matches, plus zero candidate-tree matches. Patterns cover common GitHub/AWS/API tokens and private keys; matched values are never output. This is not entropy/semantic detection, proof of no secrets, or an audit of every remote branch/fork/cache/secret store. Final scan is recorded separately.

Read-only remote heads confirm published feature `2fc9a729efb015029a559c6c2c0f71814ec4e662`; remote main is `7141ac8223ac0b922a81c7267615eb4abfaef4ad`. No push/fetch/merge was performed. Other remote branch contents are not certified from local baseline objects.

`10_dependency_inventory.json` records 56 Python closure entries and 189 npm lock entries, including optional platform records. Unknown/native license obligations remain review items. Three exact SIL font notices and sources are preserved. PDF body text uses standard Times/Helvetica names, not dashboard pixel fonts. Root MIT does not license all third-party data or establish binary-distribution compliance. Offline npm output is not a current advisory audit.

[IBM's upstream notice](https://github.com/IBM/AML-Data) distinguishes repository code and actual data licenses. The [PaySim simulator record](https://github.com/EdgarLopezPhD/PaySim) does not establish the grant for these transformed files. Obtain byte-specific source, permission and notice records before redistribution. This report records unresolved obligations, not legal clearance.

## Executed checks and limits

The 115-case backend run covers research, PDF, graph, health and missing-data startup. Graph guard tests patch fitting, model loading, graph/centrality construction and intervention generation to raise if invoked. Live workflows used GET only. The API probe passed 34 GET checks, six concurrent reads, CORS checks and OpenAPI inspection. New audit-tool tests and final browser results are in the system ledger. No body-flooding, public-host penetration, distributed-load or formal privacy certification was performed.

**Final decision: NO-GO for unrestricted public deployment.** Successful UI tests do not close these security boundaries.
