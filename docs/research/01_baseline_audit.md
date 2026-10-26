# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

## Phase 1 — Repository Audit and Research Baseline Verification

Audit date: 2026-10-19 (Asia/Calcutta). Scope: the supplied `GraphFin-main.zip`, not an inferred upstream revision. This is an audit, not an E6 implementation or a new benchmark. Repository documents and comments were treated as evidence to check, not as authorization to execute their later-phase instructions.

**Decision:** retain E0–E5 and all historical artifacts unchanged. The repository provides a useful working baseline, but its present source, dataset-loading paths, metric implementations, and historical reports do not form one fully reproducible research protocol. E6_CREST should be an independently versioned experimental extension. No improvement or novelty is established by this audit.

### 1. Scope and evidence identity

The archive contains 198 files, including 100 Python files. All Python files parsed successfully. The inventory covers backend routes, schemas, core configuration, every service family, scripts and tests; frontend API client, context, nine screens, graph/chart/UI components, assets and build configuration; datasets, stored results, deployment and project documentation. There is no Git history, dependency environment lock for Python, raw IBM/PaySim source CSV, saved model bundle, or separate paper manuscript in this archive. Consequently, “the paper's single-run rankings” below refers to the supplied locked single-run table; an unpublished manuscript's exact claims cannot be verified.

Archive SHA-256:

`02c3b4d4d4c41c259ba1efb668c12551992d174ee2deb2960dcc00fba00a4531`

The repository was extracted under `outputs/GraphFin-main`. Executable checks ran in a disposable `work/test-repo` copy because `backend/tests/conftest.py` invokes global cleanup that deletes model and split artifacts. No historical benchmark generator was executed. A full archive-to-delivery byte comparison is the preservation check; the only intended repository addition is this document.

Source paths below are relative to the repository. Function names identify implementation evidence. References to historical numbers describe stored artifacts, not newly reproduced model performance.

### 2. Architecture and execution workflow

```text
IBM / PaySim raw files                  Custom canonical CSV
          |                                    |
conversion scripts / adapters          transactions.upload
          |                                    |
canonical transaction CSV --------> PreprocessingService
                                               |
                               DatasetRegistry.create_dataset(UUID4)
                                               |
                              StateStore.load_transactions
                                 /                         \
                 GraphService: directed graph       FeatureService
                 pair-aggregated amount/count/IDs   sorted entities, float32
                                 \                         /
                                  23-column feature matrix
                                              |
label CSV -> LabelRegistry -> SplitService (labeled entity 70/30 split)
                                              |
                    E0 train statistics / E1–E5 IsolationForest
                                              |
                  joblib artifacts + metadata + score caches
                                              |
                      EvaluationService / TransferService
                                              |
                   JSON / CSV / PDF / DOCX; React screens
```

**Runtime and persistence.** `backend/app/main.py` mounts ten route modules through `api/router.py`, adds CORS and exception handlers, and attempts sample and PaySim loading at startup. `core/config.py` creates raw, processed, model and simulation directories under repository `data/`; data directory configuration is not an environment override. `DatasetRegistry` stores per-dataset `StateStore` objects and currencies in memory, persists CSVs by UUID, and reconstructs state on demand. `StateStore` eagerly computes features after graph construction. Therefore deferring betweenness in `build_graph` does not avoid it during full ingestion: feature extraction immediately requests it. Labels and splits are separate registries; splits persist entity lists. Model caches use dataset, experiment and split, with unsplit aliases for backward compatibility. This is local filesystem/in-process state, not a shared database; multiple workers can have divergent caches.

**Graph representation.** One directed edge per ordered account pair; repeated transactions accumulate `weight`, `count` and a list of transaction IDs. It is not a transaction multigraph. Amount weights affect strength features but are not supplied as shortest-path distances. Graph insertion order follows transaction order; feature row order is sorted account ID. These two orderings have different reproducibility consequences.

**API map** (all under `/api/v1`, with root `/health` and `/docs` also available):

| Module | Operations and responsibilities |
|---|---|
| `health` | Liveness |
| `transactions` | Upload, dataset status and transaction summary |
| `graph` | Dataset graph summary and account structural metrics |
| `analytics` | Ordered feature schema, paginated account features, single account |
| `datasets` | Registered/locked dataset discovery; PaySim load/status/exploration; label upload/summary; split creation/read/list |
| `anomalies` | Train IF, train statistical baseline, list experiments, predictions, summary and model metadata |
| `evaluation` | Source-to-target transfer, saved transfer artifacts, PaySim report, experiment comparison, research export, single experiment evaluation |
| `reports` | Official locked or custom evaluation reports in CSV/PDF/DOCX |
| `stream` | Start/stop/status for transaction replay and fixed-model rescoring |
| `tax` | Separate deterministic tax calculations, jurisdiction list and rules; outside anomaly research |

`schemas/` supplies typed request/response contracts for these services. `report_service.py` reads official locked files or evaluates custom experiments; `report_charts.py` renders in-memory matplotlib charts. `exploration_service.py` summarizes the loaded PaySim slice. `stream_simulator.py` rebuilds features on revealed transactions and scores existing models without refitting. `amlsim_adapter.py` additionally supports transaction/account/SAR files, closed-world negatives or positive-only labels; this is distinct from the IBM CSV converter. Tax providers cover India, US, UK, Germany and France and are independent of model fitting.

**Frontend.** `frontend/src/main.tsx` → `App.tsx` → `context/AppContext.tsx` → `api/client.ts`. Context persists dataset, research tier, experiment, split and upload history in local storage. The fetch client uses `VITE_API_URL` plus `/api/v1`; local Vite proxies `/api` to port 8000 and uses `/GraphFin/` as its base path. Screens: Overview (summaries), Datasets (upload/discovery), Graph (D3 force view and replay), Features (account matrix), Anomaly (training/predictions), LabelsSplit, Evaluation, PaySimExploration, Tax. Recharts supplies research charts. Evaluation separates static official JSON under `frontend/public/data/` from custom live evaluations and transfer results. Graph context initially has bundled sample edges; limited display data must not be mistaken for the entire research graph. The UI's benchmark button trains E0–E4 with default IF contamination, not the locked per-tier configuration. The official screen still says multi-seed verification is pending, despite stored multi-seed artifacts. No screen was changed.

**Entry points and their differences.**

| Entry point | Actual workflow |
|---|---|
| `python -m backend.app.research_runner` | Delegates to service runner; `baseline_statistical`, E1–E4; optional explicit split; otherwise in-sample |
| `backend/scripts/run_final_research_evaluation.py` | Starts/reuses HTTP server; uploads IBM tiers; six split seeds; current source includes E0–E5; writes directly to locked filenames |
| `backend/scripts/run_transfer_experiment.py` | Hardcoded IBM UUID plus PaySim UUID alias; creates splits, runs both directions and overwrites canonical transfer outputs |
| `backend/scripts/run_phase_b_c_experiments.py` | Separate scaled IF fits, permutation importance and label-selected case study; assumes hardcoded IBM processed data |
| `backend/scripts/generate_final_reports.py` | Reads artifacts, emits historical summary documents; several audit criteria are constants |
| `verify_live_api.py` | Live-server verification; not a replacement for isolated local tests |
| `.github/workflows/deploy-frontend.yml` | Frontend install/build/deploy; no backend research/test gate |

The final benchmark script is **not a safe reproduction command against the preserved checkout**: current source would produce 12 single-seed records / 72 multi-seed records including E5, while locked files contain 10 / 60 E0–E4 records. Its comments still say five models. A future runner must use new output paths and an explicit historical configuration, never silently regenerate these files.

### 3. Canonical features: mathematical and implementation verification

Let transaction set T contain validated non-self transfers `(sender, receiver, amount, timestamp)`. For account v, let `I(v)` and `O(v)` be incoming and outgoing transaction multisets, `T(v)=I(v) union O(v)`, `m=|T(v)|`, `R=sum incoming amounts`, `S=sum outgoing amounts`, `N−`/`N+` distinct predecessors/successors. Let sorted incident timestamps be `t1,...,tm`, gaps `Δi=t(i+1)−ti` in seconds, and `D=max((tm−t1)/86400,1)`.

The first 19 entries of `FEATURE_NAMES` are canonical E4/transfer features. Four E5 features are appended, making the actual exported matrix **23 columns**, not 19. `validate_19_feature_schema` checks a canonical prefix and banned columns; it permits extra columns. `research_runner` additionally checks the full current schema. Definitions below come directly from `feature_service.py` and `graph_service.py`.

| # | Feature | Definition and units |
|---|---|---|
| 1 | `in_degree` | `|N−(v)|`; distinct incoming neighbors |
| 2 | `out_degree` | `|N+(v)|`; distinct outgoing neighbors |
| 3 | `total_degree` | `in_degree + out_degree`; reciprocal neighbors count twice |
| 4 | `weighted_in_degree` | `sum_u w(u,v) = R`; cumulative incoming amount |
| 5 | `weighted_out_degree` | `sum_u w(v,u) = S`; cumulative outgoing amount |
| 6 | `betweenness_centrality` | Directed, unweighted, normalized shortest-path betweenness; excludes endpoints; six-decimal rounding |
| 7 | `transaction_count` | `m`, incoming plus outgoing transaction count; repeated pairs remain separate events |
| 8 | `total_sent` | `S` |
| 9 | `total_received` | `R` |
| 10 | `net_flow` | `R−S`, positive for net inflow |
| 11 | `average_transaction_amount` | `(R+S)/m` for incident events |
| 12 | `maximum_transaction_amount` | `max(amount in T(v))` |
| 13 | `unique_receivers` | `|N+(v)|` |
| 14 | `unique_senders` | `|N−(v)|` |
| 15 | `transactions_per_day` | `m/D` if m>1; 1 if m=1; 0 if m=0 |
| 16 | `transactions_per_week` | `7 × transactions_per_day` before independent rounding; not a weekly-window count |
| 17 | `average_time_between_transactions` | `sum Δ/(m−1) = (tm−t1)/(m−1)` for m>1; otherwise 0 seconds |
| 18 | `minimum_time_between_transactions` | `min Δ` for m>1; otherwise 0 seconds |
| 19 | `maximum_time_between_transactions` | `max Δ` for m>1; otherwise 0 seconds |

For n>2, exact directed betweenness is `sum_{s≠v≠t} σ_st(v)/σ_st / ((n−1)(n−2))`, with unreachable pairs contributing zero. Implementation calls NetworkX without a weight argument. It is exact for n≤2,000, sampled with k=500 for 2,000<n≤50,000, and k=100 above 50,000, always seed 42. Approximation details depend on the installed NetworkX version; preserve that version and sampled pivot IDs. The official [NetworkX definition](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.centrality.betweenness_centrality.html) confirms the directed normalization and sampling API; it is not evidence of the version used by the historical run.

Implementation quantization: amount and gap columns round to two decimals; rate columns to four; betweenness to six; all columns finally cast to float32. Missing intervals become zero, then NaN/infinity values are replaced by zero. Consequently the feature validation summary runs after imputation and cannot recover original missingness. Single-event zero gaps and simultaneous-event zero gaps are indistinguishable without transaction count.

**Exact structural redundancies:** in-degree = unique senders; out-degree = unique receivers; weighted in-degree = total received; weighted out-degree = total sent; total degree = in-degree + out-degree. The weighted equalities are mathematical identities; independent floating-point aggregation can in principle produce rounding differences. All four duplicate column pairs were bit-equal in the measured IBM 5K, IBM 50K and PaySim 10K matrices.

**Deterministic/near-exact redundancies:** net flow is received minus sent; weekly rate is seven times daily rate; average amount is total incident amount divided by count. Average gap, count and daily rate also obey `daily=m/max((m−1)*average_gap/86400,1)` before rounding. Thus 19 columns do not represent 19 independent measurements. Six linear constraints (four duplicates, total degree, weekly rate) imply rank at most 13 before rounding; adding net-flow dependence gives at most 12. Rounding can raise numerical rank without adding independent information. These dependencies invalidate a naive interpretation of feature-group additions as entirely new information. Duplicate columns change IF's opportunity to select certain signals.

`transaction_count = total_degree` only where ordered neighbor pairs have no repeated transactions. The supplied full PaySim CSV has no repeated directed pair, so this identity holds there by construction. It is not universal: equality held for 25.98% of IBM 5K accounts and 26.3242% of IBM 50K accounts. For m=1, average=maximum amount and all gaps=0; for m=2, all three gap summaries coincide. Such sparse-account degeneracies must be reported.

Measured maximum `|weekly−7*daily|` after float32 was 0.0004272461 (IBM 5K), 0.00146484375 (IBM 50K), and 0 (PaySim 10K). Maximum `|net−(received−sent)|` was 50.8299866, 214.55859375, and 0 respectively: float32 cancellation with large monetary totals can produce materially large absolute residuals. These are representational errors, not new behavioral signals.

**E5 definitions.** For each v, form the union of predecessors/successors plus v. Remove other nodes once if their global total degree≤1 or they have at most one distinct neighbor within that initial set; this is not iterative k-core pruning. Count retained nodes and directed edges and compute `edges/[nodes*(nodes−1)]` (0 when denominator=0). Degree≤1 centers short-circuit to (1,0,0,0). The circular indicator is

`C(v)=sum_{u in N+(v)} 1[v in N+(u)]/d+(v) + sum_{u in N+(v)} sum_{w in N+(u),w≠v} 1[v in N+(w)]/(d+(v)*d+(u))`.

This is an unweighted two-/three-hop closure heuristic computed on the original graph, not the reduced egonet. It lacks the final return-edge transition probability, can exceed 1, and is not a probability of a completed random walk or proof of timed circular money flow. The code's author attribution is not verified here and must not be elevated into an academic reference or claim of faithful reproduction. The measured PaySim 10K slice has constant betweenness and all four egonet columns; their IF cannot rank that slice meaningfully.

### 4. E0–E5 protocols and score semantics

| Method | Features | Fit / scoring |
|---|---|---|
| E0 | Locked/API graph group: 6; generic service runner default: 3 (`weighted_out_degree`, betweenness, total degree) | Training-population means/std; maximum one-sided z-score; suspicious if z≥2 |
| E1 | Graph, 6 | IF |
| E2 | Graph + behavioral, 14 | IF |
| E3 | Graph + temporal, 11 | IF |
| E4 | Graph + behavioral + temporal, 19 | IF |
| E5 | Reduced-egonet counts/density + circular indicator, 4 | IF; included in transfer and current final-run source, absent from frozen IBM E0–E4 tables |

API IF defaults: 100 trees, `max_samples='auto'`, contamination 0.1, random state 42, `n_jobs=-1`; raw feature matrix without a scaler. Train row selection precedes fitting and feature-statistic estimation. No evaluation-label vector is passed to `IsolationForest.fit`. Labels are used for labeled-entity eligibility and split stratification, which must be disclosed but is not supervised fitting.

For IF, `decision_function` is lower for anomalies; prediction −1 is suspicious. Presentation risk uses the inverse empirical training-score percentile, `100*(1−(#train<s + 0.5 #train=s)/N)`. API inference rounds decision values to six decimals before percentile lookup and risk to two decimals. `evaluation_service.py` computes AP and ROC-AUC on this presentation risk, not on raw continuous anomaly scores. Percentile saturation and quantization introduce ties. AP here means `average_precision_score`, not trapezoidal area under a PR curve; see the [scikit-learn evaluation documentation](https://github.com/scikit-learn/scikit-learn/blob/main/doc/modules/model_evaluation.rst). Risk is not a calibrated fraud probability.

The source-only transfer branch refits source means/std and 100-tree IF on source training rows, applies source scaling to target rows, fixes contamination at 0.005 in both directions, and uses source-training percentiles for evaluation. Target labels are used for target splitting/evaluation, not model fitting or a tuning loop. This separation is good, but the current API passes both label dictionaries into the broad orchestration function rather than enforcing a narrow label-free fit interface.

### 5. Dataset processing and label audit

| Supplied file set | Transaction rows | Positive-amount nonself rows | Active accounts | Label rows / positives |
|---|---:|---:|---:|---:|
| IBM medium | 31,463 | 31,463 | 5,000 | 5,000 / 20 |
| IBM large | 353,860 | 353,850 | 49,992 | 50,000 / 249 |
| PaySim research | 299,999 | 299,999 | 547,686 | 547,686 / 774 (`paysim_labels.csv`) |
| PaySim runtime prefix | 10,000 | 10,000 | 18,711 | 12 positives using research labels; 129 using preferred loader labels |

Counts were independently read from the archive's CSVs; positive/nonself filtering here is not a claim of a complete raw-source reconversion. IBM's 10 zero-valued rows remove eight negative-only accounts; all 249 positive labels remain matched. PaySim timestamps cover 2023-01-01 01:00 through 2023-01-31 21:00, corresponding to steps 1–741 and 552 distinct hourly timestamps. IBM medium spans 2022-09-01–10; large spans 2022-09-01–18. Source raw files and conversion manifests are absent, so seed-based reconversion from original raw bytes is unverified.

**IBM:** `convert_ibm_aml.py` combines bank and bank-local account IDs, uses `Amount Paid`, excludes self/nonpositive transfers, keeps transactions whose endpoints both belong to a selected account set, and OR-aggregates laundering flags across retained transactions. Selection takes the first encountered accounts until the target is reached; the seed only shuffles to trim overshoot. This is not a uniform random account sample or guaranteed connected sample. Labels describe retained transaction involvement, not necessarily the complete original history. Amounts are rounded after positivity checks, explaining zero rows. Different originating currencies are summed without currency normalization or retained currency information; the USD UI metadata does not make those sums economically comparable. Both IBM AML and PaySim are simulator-derived data, despite historical `*_real` tier names.

**PaySim:** `convert_paysim.py --sample-rows` actually reads the entire raw file, uniformly samples row indices with a seed and restores original order; its CLI help still says “first N rows.” The adapter's `nrows` instead uses a prefix. Timestamps are a fixed epoch plus integer step hours. Balances and `isFlaggedFraud` are excluded; type is metadata; canonical feature computation never reads fraud flags. Optional `--sample-accounts` uses labels to favor positive accounts up to a nominal 5% and filters endpoint pairs afterward; this is a label-dependent sampling path and unsuitable as an unqualified unsupervised benchmark. Labels can remain for selected accounts without retained edges or fraud evidence.

**Critical label discrepancy:** `paysim_labels.csv` has 774 positives; `paysim_account_labels.csv` has 2,606 positives for the same 547,686 accounts. All 774 remain positive, with 1,832 additional positives in the second file. `DatasetRegistry.load_paysim` prefers the second file, whereas research scripts explicitly reload the first. No generator/provenance in the supplied source establishes why these 1,832 labels differ. Full-history involvement versus sampled-history involvement is a hypothesis, not a verified explanation. Preserve both files, record their separate hashes and label scopes, and reconcile against raw flagged transactions before further comparative claims.

**Provenance investigation, confirmed versus unresolved.** Both ID sets exactly equal the union of sender and receiver IDs in the 299,999-row transaction file; neither label file contains duplicate accounts. The account file's `label_meaning` is consistently `normal` or `fraud-involved`. After joining `user_id` to `account`, the complete contingency table is:

| Research label | Application label 0 | Application label 1 |
|---|---:|---:|
| 0 | 545,080 | 1,832 |
| 1 | 0 | 774 |

The shared 774 positives comprise 387 sender-only and 387 receiver-only accounts **in the supplied sample**. The extra 1,832 comprise one sender-only and 1,831 receiver-only accounts; none is absent from the transactions and none has merchant prefix `M`. Their incident transaction-type counts are CASH_OUT 1,391, CASH_IN 934, TRANSFER 388, DEBIT 17 (transaction counts, not disjoint account counts). This rules out a different entity population, duplicate rows, and a simple sender-only versus both-endpoints distinction as sufficient explanations. The receiver-heavy difference is compatible with a broader evidence history, but cannot prove that history or a different fraud definition.

`backend/scripts/convert_paysim.py:121` samples raw rows before aggregation; lines 184–188 OR `isFraud` for both retained endpoints; lines 231–234 emit `user_id,label`, not `account,label,label_meaning`. The adapter similarly aggregates the raw rows passed to it. No supplied Python/script/workflow generates the latter file or specifies its evidence window. The canonical transaction CSV omits `isFraud`, original balances and raw row indices. The account-label tests check schema/coverage and a synthetic aggregation example; they do not regenerate these labels from raw evidence. **Conclusion:** the population and stated involvement concept match, assignments differ, and the exact generation procedure is unresolved from this archive. Do not declare either file ground-truth-correct based on this audit. Phase 2 needs the original flagged CSV and generator/version/seed, then separate reconstructions for sampled-history involvement and full-history involvement restricted to these IDs, with source-row mappings and disagreement attribution.

**Critical population discrepancy:** the PaySim UUID alias always resolves to `load_paysim`, which reads `nrows=10000`. Writing a full processed CSV under that alias in `run_transfer_experiment.py` does not bypass the alias. Thus rerunning current code does not reconstruct the historical 547,686-account transfer population. Direct StateStore/research loading and production loading also bypass `PreprocessingService`; ingestion semantics differ from the upload path. The archive lacks the processed IBM UUID CSVs needed by the hardcoded scripts and locked discovery, even though research CSVs exist.

### 6. Reproducibility, leakage and correctness risks

| Priority | Evidence / finding | Consequence and future requirement |
|---|---|---|
| Critical | PaySim label and loader discrepancies above | Explicit dataset/label manifests and separate runtime/research IDs before comparisons |
| Critical | `_load_artifact` and `_get_model_path` fall back from a missing requested split to an unsplit alias | A model trained on another partition can be evaluated as held-out; require exact split identity and fail closed in new research code |
| Critical | `evaluation_service.evaluate_experiment` requests only 100,000 predictions | Full PaySim test partition (~164K) is truncated through this path; evaluate all matched IDs with coverage assertions |
| High | Graph/features computed from the full observation dataset before entity splitting | Transductive entity holdout, not inductive unseen-graph or temporal forecasting; train/test share edges and graph context. No direct label feature leak found, but future-observation leakage exists if marketed as prospective detection |
| High | Locked contamination 0.004/0.005 derived from whole-dataset labeled prevalence | Label-informed threshold calibration includes evaluation prevalence. It does not fit IF trees with y, but violates a strict label-free threshold protocol; retain as historical behavior and predeclare new thresholds independently |
| High | Bootstrap custom AP formula breaks tied-score semantics | Historical CIs are not validated uncertainty for their AP estimand; ties are especially frequent after percentile scoring / degenerate E5 |
| High | Report CIs described as preserving exact prevalence, but indices sampled IID from all entities | Prevalence fluctuates per resample. IID accounts also ignore graph dependence; six overlapping splits are not independent datasets |
| High | Report generator sets criteria 6, 8, 10 to `True` | Claimed centrality verification, permutation verification and test/hash integrity are not performed by those checks |
| High | Historical final benchmark files E0–E4; present writer E0–E5 | Current runner would overwrite protected evidence with incompatible content |
| Medium | Generic runner 3-feature E0 vs 6-feature E0 elsewhere; final script's unused list mentions PageRank/clustering | Actual model metadata and feature columns, not comments, define the experiment |
| Medium | API raw features; transfer source scaling; permutation script StandardScaler and contamination 0.05 IBM / 0.01 PaySim | These are different pipelines. Scaling ideally preserves many IF partitions but finite precision, constant features and score mapping prevent assuming exact equivalence |
| Medium | Transfer/report metadata hardcodes k=500 | Full PaySim actually selects k=100; 10K slice k=500. Require effective graph settings per run |
| Medium | Source/target split names may reuse existing persisted partitions without validating requested seed | Seed in response can differ from actual split seed; persist and check exact ID lists |
| Medium | No dataset/code/config hashes in historical per-run manifests; UUIDs and v1 tags are insufficient | Dependency lock, source revision/archive hash, feature schema, data bytes, split IDs and all seed roles needed |
| Medium | Python requirements are lower bounds, not pinned; `n_jobs=-1` and runtime metadata incomplete | Environment-dependent semantics/performance; collect exact versions and CPU/thread settings |
| Medium | `test_paysim_evaluation_report.py` imports `pypdf`, absent from `backend/requirements.txt` | A clean requirements-only environment may fail collection; the audit's installed environment happened to contain it |
| Medium | Graph sample pivots depend on insertion order; centrality failures return zeros | Fixed seed alone does not establish row-order invariance; record pivots and fail explicitly for research |
| Medium | PaySim loader processes the entire 547,686-row label CSV twice for its two aliases, using `LabelRegistry.store_labels_from_csv` row iteration | Prefix loading does not bound label-ingestion cost; startup/test latency includes repeated full-file parsing. Future optimization must preserve exact matched labels and aliases |
| Medium | Feature float32 and blanket nonfinite-to-zero handling | Precision loss and hidden malformed data; retain quality diagnostics before conversion |
| Medium | `validate_amount` accepts positive infinity and checks positivity before rounding | Tiny positive uploads may round to zero, unlike already-rounded converter CSVs; add future input invariants |
| Medium | Unix timestamps use local `datetime.fromtimestamp` | Host timezone affects canonical timestamps; explicit timezone policy required |
| Medium | Generic `research_runner --demo` labels are assigned to first sorted IDs | Pipeline validation only; never mix with authentic dataset results |
| Medium | `stream_simulator` E0 uses absolute z and a fallback leading-column slice, unlike baseline one-sided z/selected columns | Replay E0 is not guaranteed equivalent to offline E0; do not use replay as an intervention oracle |
| Medium | Scored cache says “ranked” but appends users in feature-row order, without sorting | API limit/offset is account order, not guaranteed top-anomaly ranking; E6 must explicitly sort raw scores with a documented tie rule |
| Medium | Test fixtures delete global model/split state; transfer export guard depends on “test” in dataset IDs | Run tests only in disposable copies; UUID-based tests can write transfer filenames in their copy |
| Low | README says fixtures ignored, `.gitignore` explicitly whitelists them | Documentation and packaging disagree; licensing/provenance remains unresolved, no public redistribution performed |

A diagnostic cache fixture confirmed requesting `split_B` can return the cached `split_A` artifact. A tied-score fixture `y=[1,0,1,0]`, scores all 1, gives scikit-learn AP=0.5 but the bootstrap's rank-by-rank formula gives 0.833333 on the same sequence. This is a reproducible metric-definition mismatch, not a new benchmark result. Correct AP groups tied thresholds; choosing a stable arbitrary ordering does not fix the estimand. P@K similarly needs an explicit tie policy. The transfer degeneracy rule (rounded ROC=0.5 OR AP≤prevalence) does not prove constant scores; distinguish constant-score degeneracy from poor or reversed ranking.

**Cross-split fallback mechanism (Critical).** `anomaly_service.py:428` first looks for the requested split cache/file. On a miss or caught load error it continues to the unsplit cache at lines 452–454. `_get_model_path` at line 176 also permits a legacy unsplit disk path. The fallback does not require the artifact's split metadata to equal the requested split. Evaluation can therefore filter test IDs using partition B while scoring a model trained on partition A; some B test accounts may have been A training accounts. The cache diagnostic proves the lookup defect, not that a particular historical run actually suffered leakage. A future strict research loader must reject missing/mismatched split artifacts and validate training-ID hashes; maintain explicitly versioned legacy behavior rather than silently changing historical E0–E5.

**E0 is not one implementation (Medium).** `baseline_service.py:46` prioritizes feature groups over an explicit feature list; the generic default uses three columns while graph-group calls use six. At lines 101–125 a source-constant column contributes zero for every account, and the score is the maximum signed z-score. Lines 149–157 round z to four decimals, threshold it, then map risk using the **entire scored population**, including held-out accounts. In `transfer_service.py:321–337`, source standard deviations below 1e-9 are instead replaced by 1, so a target shift in a source-constant column contributes its signed deviation. Transfer E0 evaluates raw maximum z, whereas transfer IF evaluates source-percentile risk. `stream_simulator.py:316–331` defaults missing `col_indices` to the leading columns and uses absolute z; baseline artifacts do not persist those indices and persist rounded statistics. Replay also uses clipped linear risk. Thus feature selection, zero-variance handling, tail direction and risk normalization differ. For source values all 5 and a target value 8, the constant-column contribution is 0 offline versus 3 in transfer; for mean 5, std 1, observation 2 it is −3 signed versus +3 absolute. These are algebraic counterexamples, not benchmark scores.

**Why tied bootstrap AP differs (High).** `transfer_service.py:50` uses sklearn AP for the point estimate, but lines 81–86 sort each bootstrap draw stably and average precision at individual positive ranks. Correct AP is `sum_k (recall_k−recall_(k−1))*precision_k` across distinct score thresholds. All-equal scores have one threshold and AP equals positive prevalence (0.5 in the diagnostic). Arbitrary row ordering instead gives `(1 + 2/3)/2 = 5/6`; permuting tied labels can change that result without changing predictions. Resampling also repeats observations even when original scores were distinct. Percentile saturation, score rounding and constant E5 scores aggravate this mismatch. Future tests must compare every resampled statistic against sklearn on the same indices, including constant scores, duplicated observations, permutations within ties and single-class handling. No historical interval is corrected or replaced here.

Scoring clarification: `evaluation_service.py` uses baseline **raw rounded maximum z**, but IF **presentation risk**, for AP/ROC-AUC. Thus E0's whole-population risk mapping is a presentation inconsistency, not direct evidence that its offline AP uses test-population percentile normalization. Split filtering occurs inside anomaly scoring before pagination; the 100,000 cap truncates the test pool when it exceeds that size.

Training/source-only separation should remain intact: never tune E6 intervention budgets, score weights, feature exclusions or thresholds against evaluation labels or target labels. Existing permutation and case-study labels are post-hoc diagnostics, but using those same test-driven findings to select an improved model would turn the test set into development data.

Source locator index (line numbers refer to the supplied archive, whose source bytes are preserved):

| Finding | Source |
|---|---|
| Canonical feature ordering and extraction | `backend/app/services/feature_service.py:16`, `:98`; structural/BC implementation `backend/app/services/graph_service.py:86` |
| PaySim preference, prefix and alias | `backend/app/services/dataset_registry.py:77` (`load_paysim`), `:102` (`nrows`), `get` |
| PaySim generator and schema | `backend/scripts/convert_paysim.py:121`, `:184`, `:231` |
| Cross-split fallback | `backend/app/services/anomaly_service.py:176`, `:428`, `:452` |
| E0 offline/transfer/replay divergence | `backend/app/services/baseline_service.py:46`, `:101`, `:149`; `backend/app/services/transfer_service.py:321`; `backend/app/services/stream_simulator.py:316` |
| Evaluation coverage cap | `backend/app/services/evaluation_service.py:62` |
| Bootstrap point/resample mismatch | `backend/app/services/transfer_service.py:50`, `:67`, `:81` |
| Split versus estimator seeds | `backend/scripts/run_final_research_evaluation.py:201`, `:256` |
| Checklist hardcoded passes / case criterion | `backend/scripts/generate_final_reports.py:464`, `:487`, `:496`, `:505` |

### 7. Why single-run and multi-seed rankings differ

The stored files contain 60 evaluations: two tiers × five methods × six split seeds `[42,123,7,2024,99,555]`. Independent recalculation of mean, sample standard deviation (ddof=1), minimum and maximum matched every stored summary for AP, ROC-AUC, precision, recall and F1. Seed-42 metrics/confusion counts match the single-run JSON. E5 has no stored IBM multi-seed row in this artifact; transfer E5 is a different result set.

| Tier | Method | Seed-42 AP | Six-split mean AP ± sample SD |
|---|---|---:|---:|
| IBM 5K | E0 | 0.1891 | 0.0966 ± 0.0930 |
| IBM 5K | E1 | 0.0597 | 0.0305 ± 0.0246 |
| IBM 5K | E2 | 0.1854 | 0.0544 ± 0.0690 |
| IBM 5K | E3 | 0.1955 | 0.0649 ± 0.0742 |
| IBM 5K | E4 | 0.1969 | 0.0826 ± 0.0882 |
| IBM 50K | E0 | 0.0122 | 0.0224 ± 0.0145 |
| IBM 50K | E1 | 0.0159 | 0.0202 ± 0.0104 |
| IBM 50K | E2 | 0.0170 | 0.0212 ± 0.0106 |
| IBM 50K | E3 | 0.0116 | 0.0167 ± 0.0076 |
| IBM 50K | E4 | 0.0136 | 0.0176 ± 0.0077 |

5K seed-42 order: E4>E3>E0>E2>E1; mean order: E0>E4>E3>E2>E1. 50K seed-42 order: E2>E1>E4>E0>E3; mean order: E0>E2>E1>E4>E3. These are AP rankings; ROC-AUC and thresholded F1 need not produce the same order.

The final-run script varies **split seed**, while passing `random_state: 42` to every IF fit. Centrality also stays at seed 42. The stored robustness is therefore robustness to entity partitions and changed training membership, not independent IF-seed robustness. With only six positive test accounts in 5K, one positive's rank can strongly change AP; 50K has 75 positives per test split but remains sparse. AP weights precision at positive retrieval thresholds, so a few top-ranked positives have substantial influence. For distinct scores, `AP=(1/P) sum_{r:y(r)=1} precision@r`; ties use grouped thresholds. Feature redundancy also changes IF signal-selection frequency across representations, but the historical artifacts alone do not prove it caused the reversal.

The reversal is empirically verified in stored results; its causal decomposition into split variation, model randomization, feature redundancy and score ties has not been experimentally isolated. Six split SDs are not confidence intervals and do not establish superiority. Use a predeclared crossed split-seed/model-seed design with paired per-entity predictions in future evaluation. Do not select a favorable seed or change the historical table.

### 8. Investigation of “not fully paper-reportable”

`data/results/final_report/paper_reportable_status.md` says false, pipeline validation, one failed criterion (#9). `generate_final_reports.py` computes #9 as rank≤10, positive ground truth, and exact disclaimer. The stored case study is account `C546529`, rank 51, score 0.8102. `run_phase_b_c_experiments.py` deliberately falls back to the highest-ranked positive when the top ten contain none. The case-study prose nevertheless claims the strict top-10 criterion. Rank 51 is the honest outcome; selecting a different seed or altering the criterion after observing it would not repair validation.

That single failed checklist item is **not the sole scientific blocker**. The generator hardcodes passes for centrality documentation, permutation computation and test/hash integrity. Other checks mainly inspect fields/counts rather than rerunning the claimed procedure. Service-level flags also differ: ordinary evaluation calls held-out runs with ≥500 accounts and both classes paper-reportable; transfer checks successful results and ≥500 target accounts; locked metadata hardcodes a large-tier pass. None is a publication certification.

The report date is hardcoded to 2026-09-28 (`generate_final_reports.py:524`), while transfer artifacts carry later dates. The checklist describes 500 bootstrap iterations, whereas stored transfer configuration records 1,000. These are documentation/configuration discrepancies, not evidence that either count was independently replayed in this audit.

Additional blockers are the conflicting PaySim labels/populations, missing source/environment provenance, split fallback, capped evaluation, score-tie bootstrap inconsistency, and limited external validity of simulator-derived data. Ordinary CI overlap does not constitute a paired significance test; overlap cannot demonstrate equivalence or lack of a difference. No corrected CIs are manufactured here. Permutation importance uses all positives plus subsampled negatives above 10K test entities, changing prevalence and the AP estimand. Its individual-column permutations violate deterministic feature relationships; correlated/duplicate features make causal “driver” interpretations unsafe. The prose's claim that PaySim has no intermediate forwarding is not established merely by zero sampled, rounded betweenness. The case study's one-event profile cannot establish rapid accumulation, illicit intent or causal fraud behavior.

### 9. Proposed E6_CREST integration contract — design only

**Purpose:** test whether an account's anomaly ranking is supported by a small concentration of valid transaction evidence and remains stable under bounded nuisance interventions. Sensitivity is diagnostic evidence about a fitted detector, not proof of fraud, a causal effect, or established novelty. A literature review and evaluation are required before novelty claims.

Use a separate future research module, e.g. `backend/app/research/crest/`, an isolated runner and a new artifact namespace. Preserve `FEATURE_NAMES`, E0–E5 services, existing model labels, locked writers and frontend. Reuse the transaction-to-graph/feature definitions through fresh instances; do not mutate `DatasetRegistry`'s cached state. Read a verified frozen E4 scorer through an adapter with explicit feature order, split identity, preprocessing and score direction. The current private `_load_artifact` fallback and replay E0 are unsuitable as trusted interfaces.

Proposed interfaces:

```python
DatasetSnapshot(transactions, ordered_entity_ids, transaction_sha256,
                schema_version, observation_window, preprocessing_manifest)
FrozenScorer.score(feature_matrix, feature_names) -> raw_anomaly_scores
EvidencePolicy.propose(snapshot, account_id, config, rng) -> interventions
EvidencePolicy.validate(original, intervention) -> constraint_diagnostics
FeatureRecompute.apply(snapshot, intervention, fixed_entity_universe) -> matrix
CrestScorer.score(snapshot, frozen_scorer, config) -> CrestResult
ResearchEvaluator.evaluate(ordered_ids, raw_scores, evaluation_labels) -> metrics
```

`DatasetSnapshot`, scorer and policies must not accept evaluation/target labels. Labels enter only the final evaluator. Frozen scorer validates hashes of fitted model/scaler/feature schema and the actual training split. `CrestResult` records base scores, signed score changes, evidence membership/transaction IDs, feasible budgets, concentration, nuisance variation, final ranking, timings and complete provenance. An independent optional API can be considered after the research is validated; no dashboard work belongs in this phase.

**Constrained evidence interventions.** Let `φ(T,v)` be the existing feature map and `s_v(T)=−decision_function(φ(T,v))` for a fixed detector. Define admissible edits `T' in A_v(T;b)` by predeclared policies: modify only permitted incident evidence blocks; preserve transaction IDs/endpoints/timestamps unless that operator explicitly changes them; enforce finite positive amounts, no self-transfer, fixed observation window and bounded total relative amount change or bounded removed count. Evidence ablation is an analytical removal, not a claim that a real transaction can be undone. Derive all affected features from edited transactions, never independently edit redundant matrix columns. Keep the account universe fixed and explicitly define zero-evidence account features; current extraction otherwise drops isolated accounts. Record whether global betweenness is recomputed exactly or approximately with fixed pivots. A change in sampled pivots must not masquerade as transaction sensitivity.

**Sensitivity.** For evidence block j, `d_vj=s_v(T)−s_v(T^(−j))`. Positive d means the removed/attenuated evidence supported the detector's anomaly score; negative d is retained and reported rather than hidden. Normalize only with source-training-derived scale if comparability is needed. Fixed-model rescoring isolates input sensitivity from refitting noise. It remains model-dependent and interventions can be out of distribution.

**Evidence concentration.** For nonoverlapping predeclared blocks, `a_j=max(d_vj,0)`, `A=sum a_j`, `p_j=a_j/A` when A>0, and `H_v=sum p_j²`; set a defined no-support flag when A=0 rather than inventing evidence. For J positive-support blocks, `1/J≤H_v≤1`. A normalized `(H−1/J)/(1−1/J)` is possible for J>1, with J=1 handled explicitly. Report J and total A: a single tiny influence must not look like strong concentrated evidence. Blocks should be transaction-, counterparty- or time-based with a fixed policy; overlapping groups require separate accounting to prevent double counting. This concentration statistic measures localization, not legitimacy.

**Robustness-aware ranking.** Let `R_v` be the median absolute deviation of scores under predeclared feasible nuisance perturbations, `median_b |s_v(T_b)−median_c s_v(T_c)|`. A candidate family is `q_v = z_source(s_v) + α z_source(A_v*H_v) − λ z_source(R_v)`, with α,λ≥0 fixed in advance and all transformations estimated only on source training data. This is a testable proposal, not an adopted algorithm: concentrated legitimate large payments may be penalized or rewarded incorrectly, and strong anomaly evidence may itself be fragile. Compare alternatives via planned ablations rather than choosing a sign after seeing test labels. Median/MAD reduce domination by a few extreme nuisance draws; empirical validation must determine utility. No probability interpretation is intended.

For an explicit candidate transformation, `z_source(x)=(x−median_source(x))/max(MAD_source(x), ε)` with a predeclared positive ε in the component's units, a recorded constant-component policy, and separate source-training estimates for each component. This is only a proposed robust scaling convention. Intervention effects need not be additive; A is a sum of single-block sensitivities, not the score reduction from jointly removing those blocks. Evaluate interactions before interpreting A as total evidence.

**Future acceptance gates:** independent fit/evaluate label barrier; exact split and dataset hashes; all-entity coverage; tied-score AP parity; unit tests for evidence budgets, algebraic consistency, fixed-universe empty cases and deterministic seeds; integration tests for E0–E5 byte/score preservation; source-only transfer with no target tuning; paired per-entity raw scores; baseline-only, sensitivity-only, concentration-only and robustness ablations; comparisons at equal query/runtime budgets. Measure graph construction, feature recomputation, base fitting, interventions and ranking separately, including peak memory and model-call counts. Naive recomputation for N accounts × B interventions can dominate the budget; benchmark an exact small-graph oracle before approving local approximations. No new algorithm has been implemented in Phase 1.

### 10. Verification results and performance

Existing tests ran unchanged in the disposable repository, with results distinguished from scientific validation. No historical benchmark replay or raw-source reconversion was performed. Audit evidence is delivered separately in `outputs/phase1_evidence/`, outside the repository; JSON diagnostics, JUnit reports and `verification_manifest.json` identify actual completed tests and every uncompleted test ID. Intermediate aborted runs are excluded from final pass counts.

**Final existing-test accounting: 227 collected = 94 passed + 2 failed + 1 skipped + 130 blocked/not completed.** The 130 are not claimed as individually executed failures: full-suite attempts encountered the socket blocker, and the remaining request-dependent cases were not run to completion. There are no errors in the four final JUnit reports. The two frontend commands are additional blocked checks, outside the 227 pytest cases.

| Final batch | Passed | Failed | Skipped | Wall time |
|---|---:|---:|---:|---:|
| AMLSim/IBM adapters, tax engine, transfer units, stored final-run checks, two locked-file checks | 52 | 1 | 0 | 8.388 s |
| PaySim direct-service integration selection (four API cases deselected) | 17 | 0 | 0 | 2.877 s |
| Research runner, metric/normalization checks, PaySim account labels, direct report checks | 25 | 1 | 0 | 488.613 s |
| Locked backend resolvability, missing processed UUID CSVs | 0 | 0 | 1 | 0.066 s |

Failed nodes are `backend/tests/test_locked_datasets_regression.py::test_locked_benchmark_files_byte_integrity` and `backend/tests/test_reports.py::test_locked_research_artifacts_remain_untouched_after_chart_rendering`. Both fail the same pre-existing JSON hash assertion described below. The CSV CRLF mismatch was independently checked even though the first failed assertion prevents those tests from reaching it. The skipped node is `backend/tests/test_locked_datasets_regression.py::test_locked_datasets_backend_resolvability`; its required two processed IBM UUID CSVs are absent from the archive. They were not fabricated or regenerated to obtain a pass.

The two completed PaySim loader calls took 223.60 s and 213.13 s in pytest; repeated PDF/DOCX generation and figure cleanup took 18.26 s. These whole-test timings include their service work and differ from the isolated feature-stage timings below. They support the label-ingestion latency concern but are not repeated controlled benchmarks.

**Environment:** Windows, installed Python 3.12.10; NumPy 2.3.5, pandas 3.0.5, NetworkX 3.6.1, scikit-learn 1.9.1, pytest 9.1.1, FastAPI 0.141.1, httpx 0.28.1, Pydantic 2.13.4. These are measured audit versions, not a reconstructed historical environment. The initially selected bundled Python 3.12.14 lacked several dependencies; network package installation failed DNS resolution. An existing complete local Python installation enabled the service tests. Pytest plugin autoload was disabled, TEMP/TMP and basetemp pointed inside `work/`, and matplotlib used a writable workspace cache. No application/test source was patched to obtain passes.

**API environment blocker:** TestClient requests stalled before application dispatch in AnyIO's asyncio portal, Windows Proactor self-pipe creation, then `socket._fallback_socketpair` → `socket.accept`. A repository-independent `socket.socketpair()` probe also stalled and was terminated by a 15-second faulthandler deadline at `socket.py:295/627`. This confirms a local socket/runtime execution blocker; its underlying OS/security cause is not established. It is not evidence of a GraphFin route assertion failure. Full API, upload-dependent graph/features/anomaly/evaluation/split/stream/report/tax tests remain unverified. Automatic approval review could not authorize the requested unrestricted rerun because its review model was at capacity. No alternative event-loop monkeypatch or application change was used to disguise this limitation.

**Frontend environment blocker:** `npm run build` exited 1 at `tsc` not recognized; `npm run lint` exited 1 at `oxlint` not recognized. `node_modules` is absent. These commands did not reach source compilation/linting, so frontend correctness is unverified. The archive includes package manifests/lock data; dependency restoration and rerunning these checks in a provisioned environment remain required. No frontend source or lockfile changed.

**Historical hash assertion failure:** the supplied locked JSON and CSV use LF. The tests expect hashes of the same contents encoded with CRLF. An in-memory LF→CRLF transformation exactly matches both expected hashes; nothing was rewritten. JSON actual SHA-256 is `525b7b696044bd3af0017e8f8b6bba7c4a28e2dfba74837c4b0dcb84b5f1ba9d`, expected `e16e2d5948b66f0cde493fadf43e1491fee219b582faa6a38eabfe53be786ad2`. CSV actual is `5beff23b238d9db217d15f410a1599842f157e59fdf209843c3898602a141aa9`, expected `ba89012faf612cfe96d9e5049a869c40596894d167d37bb26a1581d976efa40a`. This is a packaging/byte-contract mismatch already present in the ZIP, not benchmark mutation by this audit. Future policy should record the supplied bytes and separately define canonical semantic comparison; do not normalize protected artifacts just to satisfy existing assertions.

**Independent diagnostic checks:** all 100 Python files parsed; all 19 canonical columns matched a hand-derived three-account fixture exactly after float32 conversion; repeated extraction returned the same matrix. Fixture transactions were A→B 100 and A→B 50 on Jan 1, B→C 20 on Jan 3, C→A 30 on Jan 4, A→C 40 on Jan 6. Expected directed BC was (0.5,0,0.5); duplicate and temporal columns were checked independently. Full IBM medium/large and PaySim 10K feature diagnostics verified the redundancies in section 3. Joined label checks and stored-result recalculations support sections 5 and 7. The split-fallback and tied-AP diagnostics reproduce defects rather than pass a corrected implementation. They are additional audit checks, not counted as existing pytest tests.

**Measured performance, seconds (one observation each):**

| Data / active accounts | Graph build | Feature extraction | IF fit | IF score |
|---|---:|---:|---:|---:|
| IBM medium / 5,000 | 3.2005 | 0.4661 | 2.4190 | 0.0505 |
| IBM large / 49,992 | 1.6519 | 54.9708 | 0.7715 | 0.2830 |
| PaySim first 10,000 transactions / 18,711 | 0.0733 | 16.4851 | 0.4859 | 0.1465 |

Configuration: positive/nonself transaction filtering, existing GraphService/FeatureService, first 19 columns, 100-tree IF, random_state=42, contamination=0.005, n_jobs=1. Fit/score used the full diagnostic population without labels; these are **not held-out accuracy experiments**. BC runs inside graph construction for the medium graph and inside feature extraction for the larger graphs, so columns are not pure algorithm-isolated timings. Includes possible warmup and competing-process effects; no repetitions, memory measurements, speedup claim or performance confidence interval. These timings establish practical execution cost only, not an E6 budget.

**Coverage caveats:** a passing test name is not proof of its stated research property. Several stored-result tests inspect metadata rather than refitting. Some transfer tests merely construct a request or assert an E5 feature list; the small-graph centrality repeat test exercises exact BC, not sampled pivot reproducibility. Direct transfer integrations use small synthetic account sets and do not reproduce full cross-dataset performance. The account-label suite verifies file structure and loader behavior, not the historical label generator. PDF/DOCX service checks do not substitute for unexecuted HTTP-route checks.

The startup-resilience test constructs `TestClient(app)` without entering its context manager, despite a comment claiming construction triggers lifespan. It also redirects raw/processed paths rather than the research directory used by PaySim. Its intended “no local data, full startup” guarantee therefore needs a stronger future lifecycle fixture; this audit does not count its blocked execution as startup proof. Slow-loader faulthandler traces during the completed direct-service run are diagnostic stack dumps, not pytest timeout failures.

**Reproduction commands:** run only in a fresh disposable copy. Select the interpreter with the versions above; set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, workspace `TEMP`, `TMP`, `MPLCONFIGDIR`, and use a fresh `--basetemp`. Completed node IDs and outcomes are in `verification_manifest.json`; replay those exact IDs using `python -m pytest -vv --junitxml=<new-output.xml> <node IDs>`. Collection is `python -m pytest --collect-only -q` (227 cases). In an environment with working socketpair, run the full suite without exclusion; then run `npm ci`, `npm run build`, and `npm run lint` in the disposable frontend. A full benchmark writer is not part of these commands.

Minimal defect reproducers from the disposable repository root:

```python
import tempfile
import numpy as np
from sklearn.metrics import average_precision_score
from backend.app.services.anomaly_service import AnomalyService
y = np.array([1, 0, 1, 0]); scores = np.ones(4)
order = np.argsort(-scores, kind="mergesort")
ys = y[order]
rank_ap = np.dot(np.cumsum(ys) / np.arange(1, 5), ys) / ys.sum()
assert average_precision_score(y, scores) == 0.5
assert np.isclose(rank_ap, 5 / 6)  # transfer bootstrap inner formula
with tempfile.TemporaryDirectory() as d:
    from pathlib import Path
    service = AnomalyService(models_dir=Path(d))
    service._cache[("fixture", "E4", None)] = {"split_label": "A"}
    assert service._load_artifact("fixture", "E4", "B")["split_label"] == "A"
```

Minimal label reconciliation (read-only):

```python
from pathlib import Path
import pandas as pd
p = Path("data/research")
t = pd.read_csv(p / "paysim_transactions.csv")
a = pd.read_csv(p / "paysim_labels.csv").set_index("user_id").label
b = pd.read_csv(p / "paysim_account_labels.csv").set_index("account").label
assert a.index.is_unique and b.index.is_unique
assert set(a.index) == set(b.index) == set(t.sender_id) | set(t.receiver_id)
b = b.reindex(a.index)
assert (int(a.sum()), int(b.sum()), int((a != b).sum())) == (774, 2606, 1832)
assert int(((a == 1) & (b == 0)).sum()) == 0
print(pd.crosstab(a.rename("research"), b.rename("application")))
```

### 11. Phase acceptance and next-phase boundary

The required deliverable is this audit. Architecture, 19-feature definitions/redundancies, seed/configuration/leakage risks, stored ranking differences, reportability investigation and E6 interfaces are documented. Identified defects remain intentionally unfixed in Phase 1. Publication readiness and baseline numerical reproducibility are not certified. E6 implementation, revised benchmark generation, and frontend redesign require a separately requested phase.

| Acceptance item | Outcome |
|---|---|
| Repository architecture, workflow, API/frontend and source inventory | Satisfied for supplied archive |
| All 19 canonical definitions, redundancies and reproducible diagnostic checks | Satisfied; numerical and sampling limitations documented |
| Stored multi-seed consistency, single-run ranking comparison and reportability investigation | Satisfied as artifact/source verification; not a fresh historical replay |
| PaySim discrepancy investigation | Same population and exact disagreements verified; original generation/evidence horizon unresolved because provenance is absent |
| Execute feasible existing tests and identify failures/environment blockers | Satisfied as an audit task; full green-suite verification is **not** satisfied |
| Preserve title, algorithms, datasets, locked history and frontend | Satisfied: all 198 archive files byte-identical; only repository addition is this audit |
| E6 interfaces and scientific rationale, with no implementation | Satisfied as a proposal; novelty and effectiveness unvalidated |

**Phase 1 disposition:** audit deliverable complete, with qualified/partial baseline-verification acceptance. The project is not certified paper-ready or fully reproducible. Missing label provenance, unavailable original execution inputs, two existing byte-contract failures and blocked API/frontend validation remain open. No Phase 2 algorithm, evaluation repair, research result regeneration or frontend redesign was implemented. Stop at this boundary.

**Files:** completed/edited `docs/research/01_baseline_audit.md`; created the external `outputs/phase1_evidence/` bundle listed in its README. No original repository file was modified. Final preservation was verified by comparing every original file directly to its ZIP member, not merely trusting a Git working tree or an earlier manifest. Data/result SHA-256 values are retained in `audit_probe.json`, and the final comparison and test accounting are in `verification_manifest.json`.

**Recommended Phase 2 fixes, not implemented:**

1. Resolve dataset identity first: preserve both PaySim labels, obtain missing raw flagged data/generators, record evidence windows, seed/sampling policy, source-row IDs and SHA-256 manifests; give the 10K runtime slice and full research population distinct explicit identities. Acceptance: regenerate each declared label definition and explain every disagreement.
2. Introduce a strict research artifact adapter keyed by dataset, schema, config, split and training-ID hashes. Fail on cross-split fallback. Acceptance: A-trained artifact cannot satisfy a B request in either cache or disk tests; legacy artifacts remain untouched.
3. Version the evaluation protocol: all-entity coverage, continuous raw score direction, sklearn-compatible tied AP for each bootstrap draw, declared single-class and P@K tie handling, and an uncertainty design acknowledging graph dependence. Acceptance: metric oracle parity, exactly expected evaluation IDs, and no changed historical result files.
4. Declare E0 variants explicitly and specify feature order, constant-column behavior, signed/absolute tails, source-only scaling and risk mapping. Do not silently relabel different implementations as one baseline. Acceptance: constant-column, lower-tail and replay-column fixtures distinguish versions; new research uses one documented contract.
5. Lock a reproducible environment; make test fixtures own temporary data/model roots; repair the test byte contract through reviewed provenance rather than data rewriting. Replace hardcoded report checklist passes with measured validations and runtime timestamps. Acceptance: full backend tests, frontend checks and reproducible manifests in a provisioned environment, with all remaining failures explained.
6. Only after those gates, specify E6 budgets and predeclare source-only hyperparameters/ablations. Keep E0–E5 and frontend behavior intact. No target-label tuning, no synthetic improvement claims, no retrospective seed selection.

