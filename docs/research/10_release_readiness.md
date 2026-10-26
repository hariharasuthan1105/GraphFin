# Phase 10 - Release readiness and decision record

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

25 October 2026. This is a review/proposal. No commit, push, merge, force-push, reset, release or deployment was performed.

## Separate decisions

|Purpose|Decision|Evidence and conditions|
|---|---|---|
|A. Final-year demonstration|**CONDITIONAL GO**|Live workflow, bounded graph, three PDFs, keyboard/mobile alternatives and selected regressions execute. Use the complete local tree, pinned assets, loopback-only bounded startup and explicit scientific limitations. Verify assets before presenting.|
|B. Public GitHub data-bearing release or unrestricted deployment|**NO-GO**|Exact derivative-data permissions, raw synthetic IDs in published artifacts, legacy unauthenticated/mutable/expensive APIs, ingress/rate policy and hosting configuration remain unresolved. A separately scoped code-only release could be reconsidered after review.|
|C. IEEE conference submission|**NO-GO for submission; draft ready for critical review**|The new draft aligns validated tables and negative findings. Original manuscript source, author metadata and target-venue requirements are missing; novelty is narrow, provenance qualified and external generalization unestablished.|

No acceptance probability is assigned. Code publication, data redistribution and hosted access are separate decisions; the combined current public-release/deployment gate does not pass.

## Repository and reproducibility hygiene

HEAD remains `2fc9a729efb015029a559c6c2c0f71814ec4e662`, local `feature/phase9-graph-explorer`. Phase 9's five existing-file modifications and 21 additions are preserved. Phase 10 updates README/ignore rules and adds verification/audit/test tooling, an optional dependency profile, review/manuscript/demo documents and their evidence inventory. The final inventory records exact paths and hashes.

Published feature still points to that baseline. Read-only remote heads also show main `7141ac8223ac0b922a81c7267615eb4abfaef4ad` and gh-pages `daa6562c0937edb2140487c525b5bfb14ae03908`. No other remote tree is certified by the local-object scan; do not merge/reset a newer default branch as cleanup.

Root MIT and three exact SIL font notices are retained. The dependency inventory records 56 Python closure and 189 npm lock entries; unknown/native obligations remain open. Exact grants for transformed datasets remain unverified. Initial credential-pattern review found no matches across candidates and 44 local HEAD-reachable revisions/527 blobs; final scan is separate. This is not proof of no secrets or a complete remote/CVE audit.

Ignored generated items include `.phase10-tests`, node_modules/dist, private v3 indexes and evidence copies/logs/screenshots/PDFs outside the checkout. Do not stage them with blanket `git add -f`. Existing tracked research files are not silently removed or relicensed. The audit lists the largest candidate files; being under a file-size limit is not redistribution permission.

Fresh `npm ci --offline` installed 146 packages in 21 s, exit 0. Its lockfile Vite is 8.3.0; prior unsaved tooling had installed 8.3.5. The fresh source build is verified separately; size/timing differences are not improvements. Optional Python constraints record the observed Windows dependency closure and add missing psutil tooling support. Resolver dry-run passed; complete fresh Python/cross-platform wheel installation was not executed.

## Deployment prerequisites

1. Select the intended host, base path, API origin and access model. Current Actions uses the legacy default build, not the additive research config. Root hosting and `/GraphFin/` are not interchangeable.
2. Resolve source/grant/notice records and derived-data disclosure. Review raw IDs in repository objects as well as UI pseudonyms; preserve historical evidence while deciding a new release package.
3. Isolate/authenticate research endpoints and block anonymous legacy uploads, training, mutation and expensive graph work. Add distributed quotas, ingress limits and deployment-specific logging/cache tests.
4. Review current vulnerabilities and full dependency/native/font licenses on the actual platform; execute a clean environment install. Observed constraints are not a universal hashed lock.
5. Ship only approved pinned catalog assets/private indexes. Keep model files trusted and inaccessible to untrusted upload. Test TTL/process-local session behavior and memory/concurrency behind the actual proxy; lab samples are not SLAs.
6. Review CORS's appended origins, TLS, trusted proxies, debug mode, log access and backups. No host/security policy was chosen automatically.

## Proposed commit plan - approval required

Review the exact inventory and unresolved release gates before staging. Do not include all scratch/ignored data.

1. **Phase 9:** the five integration edits and 21 new source/schema/test/report files enumerated in the Phase 9 report. Proposed subject: `feat: add bounded read-only research graph explorer`. Private indexes remain generated local assets with documented source hashes.
2. **Phase 10:** README/ignore changes; optional requirements/constraints; audit/API/table/browser-preparation tools and tests; final browser config/workflow; required reports, dependency/notices/demo inventory; versioned manuscript and derived evidence. Proposed subject: `docs: document final validation and research release gates`. Data rights still govern publication of derived tables.
3. Only with explicit authorization and appropriate gate resolution: review staged diff, verify preservation, select destination and push a feature branch. Do not merge main, dispatch workflow, tag/release or deploy automatically.

The inherited Phase 9 implementation must not be presented as Phase 10-only work. Older PDF push authorization does not authorize publication of this phase.

## Manuscript and presentation

`manuscript/phase10-v1/manuscript.md` is a new IEEE-style Markdown critical-review draft, not a compiled conference template or certified revision of the missing original. It includes ordered feature definitions, six AP values per E0-E5 method/tier, sample SD/P@100, separate E6_BASE/model seeds, qualified lineage/replay and negative CREST results. Verified primary references include Graphomaly 2022; no first-of-kind claim is made.

Authors still need affiliations/correspondence, venue choice, required declarations and source-to-claim review. The demo script uses existing saved features and honest limitations. No slide deck, institutional endorsement or financial-crime certification is fabricated. Presentation readiness does not change the public-release or submission gate.
