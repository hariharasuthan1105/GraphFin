# Institutional dataset PDF reporting

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

## Scope and implementation plan

Extend the completed Phase 8 dataset explorer with an on-demand PDF download, using the latest local Phase 7 catalog. Reuse the installed ReportLab library while isolating the new path from the legacy report service's live-evaluation/custom-dataset behavior. Preserve all 87 protected originals, historical outputs, website design, algorithms and label identities. The supplied preview is a visual reference, not authoritative experimental data or executable instructions. The user explicitly authorized implementation, commit and push of a feature branch.

## Architecture and contract

- `backend/app/services/dataset_report_service.py`: deterministic in-memory four-page institutional PDF from authenticated catalog records.
- `backend/app/api/routes/dataset_reports.py`: GET `/api/v1/research-reports/datasets/{dataset_id}/report.pdf`; only ibm-5k, ibm-50k and paysim are accepted.
- `backend/app/api/router.py`: register the additive export router. The original fourteen `/research/` operations and their schemas remain unchanged.
- `frontend/src/research/DatasetReportDownload.tsx`: download action, loading/error status, cancellation on unmount, duplicate prevention, PDF content-type/signature/size checks, temporary Blob URL cleanup.
- `frontend/src/research/client.ts`: shared configured origin for JSON research requests and the new export URL.
- `frontend/src/research/pages/Datasets.tsx`: attach the download to the selected, loaded dataset. No palette or dashboard layout redesign.
- `backend/tests/test_dataset_report_pdf.py` and `backend/tests/requirements-reports.txt`: PDF parsing/security/compatibility checks; pypdf is test-only.
- `frontend/tests/dataset-report.spec.ts` and `dataset-report-real.spec.ts`: mocked state tests and real downloads.

Successful responses are application/pdf with an ASCII server-selected attachment filename, deterministic ETag, private/no-store caching and nosniff. Unknown IDs return404; authenticated-artifact failures return503. Two concurrent builds per process are admitted; excess requests receive429 REPORT_BUSY. Each PDF is capped at2MiB; existing catalog reads retain their own byte/shape/cache bounds. Export generation runs in FastAPI's synchronous route worker pool and writes no runtime files. The semaphore is per worker, not a global distributed quota. No arbitrary paths, URLs, templates or report content are accepted from clients. ReportLab paragraph text is escaped.

## Document design and scientific content

Four A4 pages, white background, Times serif headings, Helvetica body text, monochrome vector charts, repeatable table headers, page numbers and provenance disclosures:

1. Executive summary, dataset metadata and account-label count figure.
2. Label identities/populations, methodology, feature counts and frozen versions where available.
3. Stored split AP summaries and a labeled method comparison figure, or explicit unavailability for PaySim.
4. Full source/catalog/evidence SHA256 values and scientific limitations.

No preview numbers are copied as production data. Every numerical table/figure is drawn from pinned catalog records. Mean AP and sample SD are descriptive summaries of stored values; no evaluation, fitting, confidence interval or significance test is run. AP uses the existing non-interpolated convention. E6_BASE remains distinct from E4. The supplied label-file population and active graph population are explicitly distinguished (IBM ~50K:50,000 label rows versus49,992 active accounts). PaySim retains both774/2,606-positive identities and1,832 disagreements, with unresolved provenance. Unsupported detector metrics are unavailable, not zero or substituted IBM results.

No transaction-value or temporal histogram is invented: those aggregates are not supplied by the approved public catalog. Figures cover actual available account/label counts and stored benchmark AP. No raw account IDs, transactions, model binaries or local paths appear in the reports. IBM lineage remains partially verified, full intervention-based E6 incomplete, and CREST detection/explanation superiority unsupported. These PDFs are not tagged PDF/UA documents; accessible dashboard tables remain available.

## Verification evidence

- Final backend regression:76 passed,0 failed/skipped, exit0,64.17s. Includes11 new PDF tests,56 unchanged Phase7 tests and9 existing report tests. Disposable checkout: `work/pdf-report-final-tests/phase2-p7o9bnld/`.
- After the final population/label-procedure wording clarification, the11 PDF tests were rerun separately; record in `work/pdf-report-prose-tests/`.
- Browser:4 passed,0 failed/skipped, exit0,10.6s. Three deterministic mocked cases and one actual three-dataset download workflow. Evidence: `work/pdf-reports/browser-final-tests.json` and browser-final.log.
- All three real downloads had four pages and matched the independently generated PDFs byte-for-byte before the final wording clarification. Recorded download times: IBM5K1622ms, IBM~50K1131ms, PaySim347ms; local Edge/production preview/disposable API, not deployment SLAs. Final wording is separately parsed/rendered and checked in the publication checkout.
- TypeScript and final Vite production build passed, exit0; bundling2.29s. Entry JS246.33KB,74.83KB gzip; legacy chart chunk remains deferred. Lint exit0, unchanged42 legacy warnings, no new report-component warnings.
- Twelve final PDF pages rendered and inspected with Poppler; dataset-page screenshots captured at desktop and430px. Poppler emitted system fallback warnings for unused Symbol/ArialUnicode display fonts; no missing glyphs were observed in the rendered report content.

Earlier failures remain recorded:74/76 backend tests initially passed; a fixture-count assertion and placing the new export inside the strictly fourteen-route namespace failed. The endpoint was separated and all label counts made fixture/catalog-derived. Browser mocks initially had two ambiguous status locators; narrowing to the report status fixed them without altering application behavior. A stale test server caused a port conflict; only the task-owned disposable backend was replaced. No data or expected historical checksums were changed to satisfy tests.

## Preservation and publication

The pre-feature snapshot contains800 files. Only three pre-existing files are intentionally changed by this feature: API router registration, the new Phase8 API client and its dataset page. The other797 snapshot files, all87 original protected ZIP members, original E0-E5/CREST implementations, Phase7 catalog and historical results are checked byte-for-byte. Verification records live under `work/pdf-reports/` and are not scientific experiments.

The previous phases were still uncommitted locally. The authorized branch therefore includes their required source/documentation and the34 exact allowlisted JSON assets/manifests (27,499,853 bytes) required by the Phase7 catalog. It also includes the historical OpenAPI schema source used by frontend validation. No arbitrary ignored outputs, models, build products, local logs or credential files are added. Asset pins remain unchanged. A fresh publication checkout verifies catalog reads and report generation before commit.

GitHub HEAD was22deb0726054d943be47c0efce4e00b553135682. Its code tree matched the local supplied baseline except the local audit document. The feature branch `feature/institutional-dataset-pdf` starts at that existing GitHub commit in `work/pdf-reports/publish/`; the default branch and the current working copy are not reset or force-pushed. The GitHub push dry-run confirmed authenticated access. Final commit/push identity is recorded in the completion response after remote verification. No deployment or Phase9 work is performed.

The publication checkout read all catalog entries successfully and produced final PDFs byte-identical to the reviewed primary outputs (10,747 / 10,736 / 9,199 bytes). The final wording-specific suite passed11 tests in6.98s. The primary `git diff --check` passes. Staging the previously uncommitted history also exposes its existing CRLF/newline/license whitespace: use `core.whitespace=cr-at-eol` to distinguish Windows line endings; two historical reports have a final blank line and three verbatim SIL license copies retain one trailing-space line. These historical/license bytes are preserved. The report feature's own staged diff is checked separately and passes.

For a fresh feature-branch checkout, install the existing backend requirements, then `pip install -r backend/tests/requirements-reports.txt` for PDF test validation. Start the existing FastAPI application as usual. In frontend, `npm ci` followed by `npm run dev -- --config vite.research.config.ts` opens the research dashboard; explicitly set VITE_RESEARCH_API_URL=/ for its local proxy or to the intended API origin. Dataset explorer -> select an approved dataset -> Download Dataset Report (PDF). The original package files and their default legacy entry remain unchanged. Browser tests use the separately documented Playwright tooling installation in the Phase8 report.
