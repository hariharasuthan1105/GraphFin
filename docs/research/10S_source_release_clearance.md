# Phase 10S — Public source release clearance

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Audit date: 25 October 2026. **Current-base public source release: NO-GO.** This is a bounded engineering clearance assessment, not a finding that synthetic data is inherently confidential or that every research output is legally restricted. Verified upstream terms and unresolved rights are separated below.

The proposed 44-file delta adds no dataset or binary paths, but its complete tree inherits existing transaction, label and identity-bearing research files. Those files are also reachable from the currently advertised remote feature branch. A source-only diff, `.gitignore` change, deletion in a later commit, or runtime API restriction cannot clear that history.

## 1. Repository, evidence and inspection boundaries

The inspected latest checkout is task-relative `work/pdf-reports/publish`, rather than the earlier `outputs/GraphFin-main` research archive. The latter and the supplied ZIP were not modified. No application change, test run, experiment, service start, staging operation, commit, push, merge, deployment or history rewrite was performed for this audit.

|Item|Observed state|
|---|---|
|Local branch|`feature/phase9-graph-explorer`|
|HEAD|`2fc9a729efb015029a559c6c2c0f71814ec4e662`|
|Other local heads|`feature/institutional-dataset-pdf` at HEAD; `master` at `cd4a3fd8202f521e6ccbf088815a1e87ce8df803`|
|Local remote-tracking ref|`origin/feature/institutional-dataset-pdf` at HEAD|
|Remote configuration|HTTPS `hariharasuthan1105/GraphFin`; ordinary heads fetch mapping; no embedded credentials observed|
|Actual staging area|Empty before and after; no staged changes; stage-entry digest preserved|
|Working tree at audit start|7 modified tracked files and 51 individual untracked source/document files; 428 file hashes captured. Prior work was preserved.|
|HEAD inventory|377 files, 104,350,688 bytes; 63 `data/` paths, including documentation and placeholders; 51 under `data/results/`|
|Reachable local history|45 commits across all local refs, including 44 HEAD ancestors; 379 distinct paths and 527 distinct blob objects|
|Candidate|Existing alternate index `work/phase10r/candidate-accepted/candidate.index`; 44 changed paths, 415-file complete tree|

Read-only `git ls-remote --heads origin` reconfirmed these advertised tips:

|Remote branch|Commit|Local content inspection|
|---|---|---|
|`feature/institutional-dataset-pdf`|`2fc9a729efb015029a559c6c2c0f71814ec4e662`|Commit and its 44-commit ancestry inspected|
|`main`|`7141ac8223ac0b922a81c7267615eb4abfaef4ad`|Object unavailable locally; hash verified only|
|`gh-pages`|`daa6562c0937edb2140487c525b5bfb14ae03908`|Object unavailable locally; hash verified only|

Initial sandbox DNS resolution failed; the authorized read-only remote query succeeded. No fetch was performed. Remote branch advertisement establishes that the feature history is published to that remote, not whether every file has been downloaded by others. Repository visibility, remote-only main/pages contents, pull-request refs, forks, caches, reflogs and unreachable objects were not exhaustively assessed. No claim of absence is made for those scopes.

Inspection used `rev-list --all`, `for-each-ref`, per-commit `ls-tree -r -l -z`, alternate-index `ls-files --stage`, and path/hash/size comparisons. A 250-commit ceiling was applied; actual history fit within it. Raw records and private identifiers were not printed. Metadata inventories retain object IDs and sizes, not dataset contents.

Task evidence is outside the repository in `work/phase10s/`: `audit.py`, `before.json`, `history_inventory.json`, `current_and_candidate.json`, `candidate_comparison.json`, `credential_scan.json`, `protected.json`, and `final_verification.json`. Paths here are task-relative unless repository-relative paths are explicitly used. These local audit files are not proposed publication assets.

## 2. Tracked content and redistribution classifications

In the table, **tree** means HEAD and the inherited complete candidate tree. **Delta** means the 44 newly changed paths only. Every current HEAD path is already at the advertised remote feature tip; prior blob variants can also remain in its ancestry. `UNCLEARED` means evidence is insufficient for public distribution, not a fabricated assertion that a license prohibits it.

|Category and representative paths|Tree / history / delta|Permission and public suitability|Exclusion and historical decision|
|---|---|---|---|
|IBM transaction subsets: `data/research/ibm_aml_medium_5k.csv`, `ibm_aml_large_50k.csv`|Tracked; history and remote feature; inherited; no delta|**UNCLEARED exact supplied derivatives.** Upstream data license identified, but acquisition/version/conversion lineage and distribution compliance not authenticated.|Future exclusion alone insufficient. Owner must clear existing copies/history or approve a separate distribution approach.|
|PaySim transactions: `data/research/paysim_transactions.csv`|Tracked; history and remote feature; inherited; no delta|**UNCLEARED.** Simulator license is not a grant for these transformed bytes.|Same historical decision required.|
|Account labels: two IBM `*_labels.csv` files; `paysim_labels.csv`, `paysim_account_labels.csv`; root `graphfin_demo_labels.csv`|Tracked; history and remote feature; inherited; no delta|Research label grants/lineage **UNCLEARED**. Root demo ownership/source requires confirmation; a small size does not prove original authorship.|Retain exact identities privately pending review; do not select or replace the conflicting PaySim label set.|
|Other transaction samples: `data/raw/sample_transactions.csv`, root `graphfin_sample_transactions.csv`|Tracked; history and remote feature; inherited; no delta|Reported sample/demo intent is not byte-level permission evidence. **UNCLEARED** provenance pending owner attestation.|Review even small samples; future ignore rules do not retract current/history copies.|
|Processed persistence/model directories|Only `.gitkeep` placeholders tracked in `data/processed/`, `data/models/`; no model/persistence binaries found in scoped history|Placeholders suitable as project scaffolding. No model redistribution clearance inferred from absence.|No historical model removal indicated by this scope. Future trained models require upstream-data and disclosure review.|
|Derived graph topology|No SQLite/DB files in HEAD/candidate/history. Three ignored local files under `data/results/v3/phase9-topology-v1/`|Two indexes and their manifest are **UNCLEARED for distribution**; they retain relationships and account identifiers.|Keeping these local files excluded is sufficient only for these not-observed-published files; it does not clear their tracked source data.|
|Identity maps, memberships and diagnostic records|Tracked `phase5-baselines-*/split-*/scores.json`, `phase6a-explanations-v1-pilot-v2/explanations.json`, case-study account profile; history/remote; inherited; no delta|**UNCLEARED artifact classification.** Per-account records expose identities, labels, features/scores, split information or intervention provenance. They are not automatically anonymous aggregate Results.|Review existing historical copies separately. Local graph manifest additionally contains approved-node/anchor identity lists; no such list is reproduced here.|
|Research results and manifests|Tracked `data/results/`, including final single/multi-seed comparisons, transfer results, v2 manifests and validation records; also two benchmark files under `frontend/public/data/`|Aggregate outputs may qualify for separate clearance. Row-level payloads need distinct review; blanket **UNCLEARED** until artifact-level classification. No claim that all 51 results-directory paths are restricted.|Public frontend assets can ship with a static build; audit beyond `data/`. Old result versions remain reachable.|
|Generated PDF/DOCX reports|None found by file extension in scoped tracked trees/history/candidate. Preview PDF is external to this checkout.|Generator code may be distributed subject to ownership; contents of future exports need their own release review. External preview/template permission **UNCLEARED** if later copied.|No generated report removal required in scoped history. Do not package external previews automatically.|
|Web fonts|Three WOFF2 files, three OFL notices and `sources.json` tracked and remote; inherited; no delta|Documented **SIL OFL 1.1**, conditionally suitable with notices/license retained and reserved-name conditions respected; exact remote binary provenance was not independently re-downloaded.|Exclusion not necessary solely due to OFL. Preserve notices in any source/bundle distribution; MIT does not replace OFL.|
|Other frontend resources|`frontend/src/assets/hero.png`, React/Vite SVGs, public favicon/icons tracked/history/remote; inherited; no delta|Hero/image/icon authorship or source attribution **UNCLEARED**. Framework template association alone does not clear copied image bytes or trademark use.|Owner attribution review needed for full-tree and source-export options; no new binaries in delta.|
|Local/environment/deployment config|Tracked `frontend/.env.production`, `.env.research.example`, Python version, Render/Vite/Actions configuration; inherited history. New tooling/config in delta.|Observed Vite values are API addresses/examples, not demonstrated secrets. Frontend Vite values are public build input. Machine-specific operational settings still require owner review.|Ignore additions protect future local overrides only; they do not untrack an existing file. Confirm intended endpoints and automated deployment behavior before publication.|
|Credentials|No confirmed credential found by bounded rules; see scan limits below|No evidence justifying a claim of exposed live credentials; also no comprehensive secret-clearance certificate.|If owner review identifies one, revoke/rotate immediately, then separately plan repository remediation. Deleting a file is insufficient.|
|Project-authored source/tests/docs|Root `LICENSE` declares MIT, copyright 2026 Hariharasuthan. Most delta is source/tests/tooling and three 10R docs.|MIT notice supports intended project-code distribution; external contributions, institutional ownership or copied snippets are not proven solely by that declaration. Conditional on owner confirmation.|Review source plus inline fixtures/docs for embedded records; preserve attribution. A code license does not license data in the same repository.|

Concrete Git metadata illustrates exposure without disclosing records:

|Path|Git blob SHA-1 (object identity)|Bytes|
|---|---|---:|
|`data/research/ibm_aml_large_50k.csv`|`1e77a80733caba2451ff6e24dae39471a644eb26`|28,906,134|
|`data/research/paysim_transactions.csv`|`75711ebe414ee2f71c0388b9515e587fcaddc3e7`|22,658,793|
|`data/research/paysim_account_labels.csv`|`9ea2d36949b27e9218d30b866050ae4a5f52177f`|11,238,433|
|`data/research/paysim_labels.csv`|`9384e3aa80629d2a0c21d9411d9d3cc8e3f757ae`|7,383,769|
|`data/results/v2/phase5-baselines-50k-v1/split-99-model-42/scores.json`|`aebb4008b63f7f7eedc06484e47a9e65dedbbd3a`|4,139,194|

Object SHA-1 identifies Git content; protected research identity uses the existing SHA-256 manifest. Neither is a license or proof of anonymization.

## 3. Historical and local-only exposure

Two paths occur only in earlier scoped commits, absent from HEAD and the candidate complete tree:

|Historical-only path|Blob versions and bytes|Exposure finding|
|---|---|---|
|`data/results/cross_dataset/transfer_ibm_aml_to_paysim.json`|`489746c4330104f47e0f233a9747623b01c01708` (13,743); `d38d12b0cca6341ea30ef6931e6d3365201eaaa9` (14,209)|Both remain in advertised feature-branch ancestry|
|`data/results/cross_dataset/transfer_paysim_to_ibm_aml.json`|`bfd58b0d50b7a8a38e24a1522418d9588593a5ca` (14,169)|Remains in advertised feature-branch ancestry|

These older result names need content/permission classification even though absent from the latest tree. Historical object versions of still-current paths also remain relevant; the complete path/version inventory is retained externally. All 379 scoped paths occur somewhere in HEAD ancestry. The additional local `master` commit does not introduce another path outside that ancestry's path inventory; it is not asserted to be remotely published as that exact commit.

Bounded ignored-data inventory found only the following three local topology artifacts in this checkout: `ibm-5k.sqlite` (5,185,536 bytes), `ibm-50k.sqlite` (60,940,288 bytes), and `manifest.json` (41,297 bytes). Their SHA-256 identities and final preservation comparison are recorded externally. They are absent from the inspected Git history/candidate. This is a statement about these exact files, not evidence that their underlying transactions are unpublished. Generated caches, installed dependency/build folders and earlier task archives were not recursively audited as potential release packages; they must remain outside any future reviewed export.

The working tree's unpublished Phase 9/10/10R code and documentation are local changes, not remote feature-tip contents. The alternate candidate is a proposal, not a commit. No new Phase 10S publication candidate was constructed.

## 4. Licensing evidence and unresolved clearance

Primary sources were checked read-only on the audit date; no data was downloaded:

- [IBM AML-Data](https://github.com/IBM/AML-Data) explicitly distinguishes Apache-2.0 repository code from CDLA-Sharing-1.0 actual data and describes the generator's synthetic world. This is authoritative upstream information, not authentication of the supplied transformed files. Historical `data/research/README.md` still says fixture CSVs are untracked and the CDLA variant is uncertain. The first claim contradicts actual Git inventory; the upstream variant is now known, while exact local lineage remains unresolved. That historical document was preserved.
- [CDLA-Sharing-1.0](https://cdla.dev/sharing-1-0/), sections 1.11 and 3.5: qualifying computational Results must not retain more than a de minimis portion of source Data; their publication has no obligations under this agreement. Data/Enhanced Data instead has section 3 sharing, change-notice, attribution and license-access requirements, without additional use restrictions. This supports artifact-specific review, not a blanket ban on derived statistics or a blanket exemption for score/topology files. Owner clearance must establish acquisition terms, lineage and classification.
- [PaySim simulator](https://github.com/EdgarLopezPhD/PaySim) identifies GPL-3.0 for simulator code and links a separate dataset. The [linked Kaggle dataset](https://www.kaggle.com/datasets/ealaxi/paysim1) and [IBM Kaggle page](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml) yielded no usable license body in the browser extraction. Their exact dataset grants/version receipts were not verified here. PaySim transformed data and both label sets remain **UNCLEARED**. Public download availability and simulator GPL are not substitutes for those records.
- [SIL's official OFL 1.1 text](https://openfontlicense.org/open-font-license-official-text/) permits font bundling subject to its conditions. Local copyright/license notices for IBM Plex Mono, Pixelify Sans and Silkscreen and download-source URLs are retained. Keep OFL and copyright attribution with redistributed font copies, respect reserved names for modified fonts, and do not relicense fonts under project MIT.

The existing `docs/research/10_dependency_inventory.json` inventories 189 npm lock entries and 56 observed Python distributions. npm license declarations comprise 147 MIT, 21 ISC, 12 MPL-2.0, 5 Apache-2.0, 2 BSD-3-Clause, 1 CC-BY-4.0 and 1 combined MIT/ISC. These are metadata declarations, including optional/platform entries, not a verified installed-binary license bill of materials. Retain relevant notices and review MPL file obligations, attribution licenses and native-library components for the actual distributed build. Python requirements are lower-bounded; optional constraints describe one observed Windows environment. Complete source/build/native dependency clearance remains **UNCLEARED** until exact package notices and distribution contents are approved. No dependency directories, wheels or native binaries are newly included in the candidate.

`backend/app/services/dataset_report_service.py` uses ReportLab drawings and standard Times/Helvetica font names. No custom font registration or imported preview PDF was found there. The external professional preview was not copied into the candidate. Source template ownership and exported report content must be assessed independently from standard font names and the ReportLab package's license metadata. No blanket template or PDF-content rights are inferred.

## 5. Candidate and ignore-rule audit

The existing Phase 10R safe commit plan was reviewed. Its accepted alternate index contains **38 additions and 6 modifications**, grouped as 25 Phase 9, 9 Phase 10 and 10 Phase 10R paths. The full tree contains **415 paths**, retaining all **63 baseline data-directory paths**. No new data, font, image, PDF, model, archive or index path is added by the delta. The seven modified files in the real working tree include README, which is intentionally outside that candidate.

All 44 candidate paths were compared with current working bytes: 37 exact matches; seven Python files differ only by CRLF-to-LF normalization required by existing `*.py text eol=lf`. No other difference was found. `candidate_comparison.json` records both hashes and exact paths. No bytes or index entries were changed to perform this comparison. Phase 10R's saved full-blob content scan reported no credential, absolute-machine-path or raw-account-ID findings; that prior scan is evidence of its stated rules, not proof of complete clearance.

Existing `.gitignore` explicitly whitelists canonical research CSVs and several results. Ignore rules cannot remove tracked files. New `.env` override/cache rules are useful future hygiene but do not clear the already tracked `.env.production` or data history. Existing `.gitattributes` preserves data/frontend bytes and normalizes Python staging. No normalization or deletion was performed in this audit.

The prior candidate's plain staged whitespace check returned 2 for preserved frontend CRLF; its explicit `blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol` check returned 0. This is retained as the prior result, not relabeled a plain-check pass. Current ordinary working-tree `git diff --check` returned 0 after this report was added.

The candidate also holds back broader README, manuscript and evidence-package documentation. It is not yet a self-contained release package, irrespective of licensing. Future approved preparation must reconcile links/setup instructions and separately provisioned artifact requirements.

## 6. Sensitive-information assessment

**High severity:** transaction relations, identity-bearing labels/scores/intervention records and unresolved derivative grants already occur in remote-reachable history. Upstream synthetic generation reduces real-person concerns for authenticated upstream bytes; it does not authenticate every local file, establish a redistribution grant, or make record linkage disappear. Hashing a public account ID alone would not remove graph-linkage risk.

**High severity:** treating the source-only delta as a source-only repository would republish inherited content without resolving these questions. Historical-only paths demonstrate why new ignore rules or ordinary deletions are insufficient.

**Medium severity:** legacy image/resource ownership, exact dependency/bundle obligations, incomplete acquisition receipts and contradictory historical tracking documentation need explicit owner review. Public frontend assets and downloadable reports are disclosure surfaces in addition to API responses.

A bounded credential-pattern scan inspected 512 text blobs across reachable local refs (8,698,624 bytes read across eligible blobs), retaining only path/object/rule metadata. Rules cover private keys, GitHub tokens, AWS access IDs, literal credential assignments and credential-bearing HTTP URLs. **Zero candidates were detected.** Eleven blobs larger than 2 MB were excluded from credential-content scanning and four binary blobs were not text-scanned; their paths, hashes and sizes remain inventoried. Nonstandard/encoded secrets, large datasets, external ignored configuration, remote-only histories and other services are outside that conclusion. This audit does not call the repository secret-free. No immediate rotation is claimed necessary absent a confirmed exposure; any subsequently discovered credential requires immediate owner-led revocation/rotation before relying on a removal or rewrite.

## 7. Safe release choices

|Option|Preconditions and license implications|Risks and preservation/reproducibility impact|Required owner authorization|
|---|---|---|---|
|A — Existing history|Clear all current and historical data/resources, exact derivative provenance, required notices and actual distributed dependencies; review complete candidate documentation.|Best history continuity; presently blocked. Source-only delta still carries inherited artifacts. No extra preservation changes needed if genuinely cleared.|Explicit publication approval after documented clearance; current audit is not that approval.|
|B — Pause further publication / consider private handling|Freeze public release actions while owner obtains grants and reviews exposure. Existing-public copies are not recalled by changing visibility.|Preserves all originals, history and reproducibility locally. Already published material may persist elsewhere; private handling is not a license cure.|No publication performed now. Any remote visibility/access change needs explicit approval and collaborator assessment.|
|C — Separately reviewed source-only distribution|Owner approves a new package/base with an exact allowlist; review inline fixtures/assets/notices, no inherited data/history; retain acquisition/checksum/manifests and missing-artifact behavior.|Can preserve scientific archives independently without publishing them. A clean export loses ordinary ancestry continuity; external data may remain necessary and some results may not be publicly reproducible until authorized access is available. Source licensing still requires review.|Separate explicit approval to prepare and later publish the chosen package/repository; this audit creates neither.|
|D — Coordinated history rewrite|Explicitly establish affected objects/refs and rights, archive originals privately, coordinate collaborators, remote cleanup and any credential response.|Highest disruption to commit IDs, branches and citations; forks/caches/copies are not erased. Reproducibility needs old-to-new identity mapping and retained protected archive.|Specific approval of scope, backup/coordination plan, rewrite and any force-push; never automatic.|

**Recommendation:** use B immediately (no further publication); prefer an owner-approved C as a future release route if complete historical clearance for A cannot be established. This is a recommendation, not authorization to export, delete, create an orphan branch or rewrite history. D is a separate last-resort coordinated decision, not an assumed prerequisite. Existing restricted local-demo GO does not authorize public deployment or distribution of its evidence.

## 8. Reproducibility requirements for any approved source-only package

Preserve the exact project title, feature/method definitions, E0–E5 history and scientific limitations. Keep protected originals and locked experiment archives intact in their existing location; do not manufacture replacement data or hashes to make a release smaller.

The reviewed package must carry:

1. IBM/PaySim authoritative acquisition URLs, dataset versions, source receipts/terms and conversion commands (`convert_ibm_aml.py`, `convert_paysim.py`) with their limitations. Do not promise those procedures recreate supplied bytes when source receipts are missing.
2. `protected_artifacts_v1.json` identities and byte-provenance policy; publish permitted checksums and expected schemas without embedding unauthorized records. Preserve the supplied ZIP SHA-256 identity `02c3b4d4d4c41c259ba1efb668c12551992d174ee2deb2960dcc00fba00a4531`.
3. Dataset/label identities, separate split/model/bootstrap seeds, algorithm versions, environment/constraints, feature-generation and transductive scope, append-only manifest and score-artifact contracts. Paths to withheld artifacts must remain explicit unavailable dependencies, not broken claims of a complete checkout.
4. Both PaySim label identities: 774 versus 2,606 positives on 547,686 accounts with 1,832 disagreements; provenance remains unresolved. Do not silently prefer a label set or tune transfer against target labels.
5. Safe disposable test instructions and fictional unit fixtures. Full scientific replays may require separately authorized data/artifacts. Existing `10_reproducibility_guide.md` must be reconciled with `10R_controlled_demo_readiness.md`: use the restricted `backend.app.research_demo:app` loopback profile for controlled demonstrations, not the guide's earlier legacy-main example as a public launch recipe.
6. Optional, separately provisioned catalog-pinned saved evidence, graph indexes and original Phase 6C archive with their checksums/access terms. Current serving catalog pins 35 files including the catalog; availability is not permission. The publication checkout omits 25 of 33 original evidence-package members; the original archive remains separate.
7. Limits on claims: incomplete frozen E6 evaluation; no detector-superiority inference from rank changes; limited explanation coverage; no unrestricted deployment or IEEE submission clearance. A source-only release does not repair those scientific gates.

## 9. Verification, owner decisions and final gate

|Check|Executed result|
|---|---|
|Reachable-history/tree metadata audit|Completed, script exit 0; 45 commits / 527 blobs / 379 distinct paths|
|Remote branch metadata|Read-only query exit 0; remote-only main/pages content not locally inspectable|
|Protected originals|**87/87** current files match existing SHA-256 manifest and corresponding supplied ZIP entries; supplied ZIP hash matches manifest|
|Candidate comparison|44 checked; 37 exact, 7 policy-only line-ending differences, 0 other mismatches|
|Credential rules|512 text blobs inspected; 0 candidates; documented exclusions apply|
|Existing source preservation|428 pre-audit source/document files unchanged; 3 ignored topology files unchanged; only this report newly added inside the repository|
|Git state|HEAD, refs and real staging preserved; alternate candidate index preserved|
|`git diff --check`|Exit 0 after report creation|
|Supplementary new-report whitespace inspection|`git diff --no-index --check -- NUL docs/research/10S_source_release_clearance.md` returned 1 with no stdout/stderr; retained as a nonzero comparison result, not counted as an exit-0 check.|
|Application/regression/experimental tests|Not rerun: no code changes. Prior Phase 10R reports record 44 new boundary tests, 113 existing tests in separate runs and 4 live browser cases passed; those are prior evidence, not newly executed counts.|

Owner decisions still required: authenticate dataset acquisition/transformation records; classify and clear each derived artifact; resolve image/template/contribution ownership and complete distribution notices; assess already published material and remote-only branches; choose A/B/C/D; approve any remote access change, export preparation, commit/publication or coordinated rewrite separately. No secrets, raw records or private anchor lists are included in this report.

**Final decision: NO-GO for public source release from the current base/history.** Audit completion criteria are satisfied within the stated bounds; release clearance is not. Controlled local demonstration remains the previously approved restricted-profile decision. Unrestricted deployment and manuscript submission remain NO-GO. Stop here; no other phase or publication action is initiated.
