# Phase 10R - Safe source-review and commit plan

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

25 October 2026. No commit, push, merge, reset, force-push, history rewrite or deployment was performed. The actual staging area is preserved. Candidate staging uses separate index files under task `work/phase10r`, not a blanket `git add` in the user's index.

## Scope of the source candidate

The proposed additions consist only of explicitly listed application code, schemas, styles, test fixtures/code, optional dependency constraints and these new review documents. No raw transaction/label file, score array, topology SQLite file, model, PDF/image/font binary, runtime map, experimental output or build/dependency directory is added. Synthetic unit fixtures are explicitly fictional, not production samples.

`backend/scripts/prepare_source_candidate.py` defines three review groups and prepares a complete staged delta using `GIT_INDEX_FILE`, starting from existing HEAD. It audits every candidate blob, stores complete group/combined patches and records hashes. Read-only Git inspection of the working and candidate indexes verifies the real staged diff remains unchanged. The candidate files are not a commit or publication authorization.

|Boundary|Contents|Proposed subject|
|---|---|---|
|1 Phase 9 source|Five integration edits plus twenty new source/schema/style/browser/backend test files. The historical Phase 9 findings report and private indexes remain outside this source candidate.|`feat: add bounded research graph explorer`|
|2 Phase 10 source tooling|Optional requirements/constraints, audit/API/saved-table/browser-preparation scripts, their tests and final browser config/workflow. These are code, not generated results.|`test: add final research validation tooling`|
|3 Phase 10R safety|Isolated research app, boundary tests, isolated browser harness/config, candidate-audit tool, ignore additions and three review documents.|`fix: isolate controlled research demonstration`|

README's safer current local instructions remain in the working tree; they are held with the broader Phase 10 documentation because its links include the held manuscript/evidence package. This avoids presenting an incomplete source delta as a complete publication/documentation release. The reviewed candidate is a preparation artifact; reconcile documentation/link scope before an authorized commit.

All previously uncommitted Phase 9/10 reports, manuscript and generated numerical tables are preserved locally. Their exclusion is a conservative release choice, not a declaration that every aggregate statistic is legally restricted. Do not delete or falsify them to obtain a “clean” tree.

## License/distribution findings

|Material|Evidence and appropriate treatment|
|---|---|
|Project source|Root MIT license supplies the project code notice; retain it. Owner approval remains necessary for publication decisions. No externally copied/vendored code or binaries are added by this delta.|
|IBM|The [official repository](https://github.com/IBM/AML-Data) distinguishes Apache-2.0 repository code and CDLA-Sharing-1.0 actual data. This does not authenticate the lineage/grant for the supplied transformed bytes.|
|CDLA classification|The [official terms](https://cdla.dev/sharing-1-0/) distinguish Data/Enhanced Data from computational Results; sections 1.11/3.5 limit the Results category and remove license restrictions on qualifying Results. Publishing Data has separate conditions/notices. Do not automatically classify row-level scores, topology or account maps as unrestricted Results. Exact classification and other applicable obligations remain for owner review.|
|PaySim|The [simulator source](https://github.com/EdgarLopezPhD/PaySim) identifies GPL-3.0 and a separate dataset source; that does not establish the grant or generator for these supplied label/transaction files. Hold affected data outside proposed additions.|
|Research artifacts|Raw data, score maps, memberships, diagnostic transaction identities, indexes and model files are not source-only additions. Keep them private pending source/grant/disclosure classification. Aggregate manuscript tables are held conservatively with the review package.|
|Fonts|Three exact SIL notices/source metadata were previously verified and remain unchanged. No font binary/notice is newly staged. Root MIT does not relicense those fonts.|
|Frontend/backend packages|Existing metadata inventory covers 189 npm lock entries/56 observed Python distributions. Constraints and imports are code/configuration; no node_modules, wheels or native binaries are staged. Installed metadata is not full native-license or vulnerability clearance.|
|PDF resources|Existing ReportLab standard Times/Helvetica font names; no embedded pixel-font body, new font binary or PDF output is staged. The generator/resources remain unchanged.|
|Legacy images/logos|No new asset is staged. Existing repository images/logos still need owner/source attribution review before a complete redistributable package is certified.|

These are evidence-based scope decisions, not legal clearance. Public upstream availability alone is not a redistribution grant for all transformed artifacts.

## Already tracked material is a separate blocker

Existing HEAD already tracks raw datasets, label files and identity-bearing saved evidence. Ignore rules do **not** remove them from the tree or history. A zero-data-addition staged diff does not make a new commit based on that parent a source-only public repository.

Therefore **public source-code commit from the current release base remains NO-GO**, even if the new delta passes content checks. Resolve permission/notices for existing tracked material, or separately authorize a genuinely clean source-only release base/package. Do not rewrite history, remove protected originals, or silently stage deletions in this phase. A source-only export/new release history would require an explicit reviewed plan; none is created automatically.

## Staged audit and complete diff review

The machine-readable candidate manifest records exact paths/group assignments, working-file and staged-blob SHA256, full patch digests and these checks:

- Explicit allowlist, text-only file types, per-file size limit and zero additions under `data/`, model/index/export/cache directories.
- Redacted credential patterns, absolute local-machine path patterns, raw-account identity patterns outside documented synthetic tests, and process-specific map/export indicators.
- No added font/image/PDF/model/archive binary or generated statistical evidence file.
- Full candidate tree inventory of already tracked data/model/asset paths; these are flagged, not ignored because unchanged.
- Complete staged patch/numstat/name-status, integration review, and line-ending-aware whitespace checks without altering tested Phase 9/10 bytes.

The reviewed candidate contains **44 files**: 25 Phase 9 source files, 9 Phase 10 tooling files and 10 Phase 10R safety/documentation files. All candidate blobs and complete patches were scanned. There are **zero new data/binary paths and zero detected credential, absolute-machine-path or raw-account-ID findings**. The real staging area remains unchanged. The candidate's parent already contains **63 tracked data-directory paths**, including harmless documentation/placeholders as well as raw datasets and identity-bearing research files; not all 63 are sensitive, but the affected subset prevents public-tree clearance.

Plain staged `git diff --check` returns 2 because preserved frontend CRLF is treated as trailing whitespace. The explicit full check `blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol` returns 0, retaining all three normal whitespace checks while recognizing CRLF. Existing bytes were not rewritten to change this result. The normal unstaged working-tree check passes separately. Group patches and `complete-staged.diff`, with SHA256 and exact file lists in `audit.json`, are available under task `work/phase10r/candidate-accepted/`. Digests are kept externally to avoid self-referential document hashes.

The first candidate preflight stopped on its own generic Unix-home regex literal, rather than a real machine path. Splitting that declaration preserves the identical detection rule without making the source resemble a concrete path. The corrected complete audit passes; no file-wide exception or disabled content rule was introduced. This was an audit-helper correction, not permission to overlook an actual private path.

Line-ending policy matters: `.gitattributes` preserves original data/frontend bytes. If plain staged checking flags CRLF as trailing whitespace, the audit retains that result and also runs `core.whitespace=cr-at-eol`. Neither historical/source bytes nor expected checksums are silently normalized. Real trailing-space findings remain failures. The normal working-tree `git diff --check` result is separately reported.

Review focus: Phase 9 changes are additive route/client/schema wiring; the graph source and limits are unchanged. Phase 10 tooling writes exclusive evidence and does not run research fitting. Phase 10R directly mounts only approved routers and has no operational import/lifespan, as verified by targeted tests. Complete patches are available for independent review; content-pattern checks are not semantic-secret detection, a complete security audit or a permission certificate.

## Approval boundary

Do not run `git add .`, force-add ignored evidence, commit these candidates, push a feature branch or merge main based on this report. First resolve the release-base blocker and review every proposed path and staged diff. If authorization later arrives, stage only the approved group against the chosen clean/cleared base and rerun the audit. No authorization is inferred from the earlier PDF publication task.
