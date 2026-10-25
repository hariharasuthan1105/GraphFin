# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

## Phase 3 — Constrained financial transaction evidence-intervention engine

Implemented 2026-10-20. This extension studies how bounded omissions of historically available transaction evidence change account representations. It does **not** implement E6/CREST scores, sensitivity aggregation, ranking fusion, supervised learning, or a dashboard. An omission is a hypothetical analytical view, not a proven causal explanation of fraud. No novelty, improved detection accuracy, or publication readiness is asserted.

### Architecture and integration

The Phase 1 audit and Phase 2 correctness report remain the baseline. Existing `services/graph_service.py` builds directed pair-aggregated graphs with transaction ID lists, counts and monetary weights. `services/feature_service.py` extracts the original float32 23-column matrix; this extension takes exactly its first 19 columns, in their original order. No E0–E5 algorithm, scaler, Isolation Forest fit, adapter, dataset registry, global cache or frontend is changed.

New opt-in package `backend/app/research/interventions/`:

| File | Responsibility |
|---|---|
| `schemas.py` | Frozen validated configuration, budget and implementation ID |
| `historical_evidence.py` | Immutable events, source identity, time validation and cutoff extraction |
| `intervention_engine.py` | Incident-event index, three candidate families, shared budget validation and deterministic orchestration |
| `feature_recomputation.py` | Isolated global reference computation and preserved account universe |
| `artifact_writer.py` | Phase 2 manifest envelope extended by an intervention stage; streamed JSONL records |
| `__main__.py` | Reproducible CLI using explicit transaction/config files |

`backend/app/research/__init__.py` and the package initializer define the namespace. Additional files are `backend/tests/test_phase3_interventions.py`, `backend/scripts/benchmark_phase3.py`, `docs/research/fixtures/phase3_transactions.csv`, `docs/research/configs/phase3_demo.json`, and this document. Phase 2 edits remain uncommitted and are not discarded. The Phase 3 work adds these files without editing existing E0–E5 or Phase 2 service implementations.

The IBM converter already emits canonical IDs, directed endpoints, amounts and timestamps. The PaySim adapter uses a synthetic 2023-01-01 epoch plus hourly steps and also touches labels; the new engine does not invoke label-loading adapters. Supply their canonical transaction columns directly. A simulation input must contain `step`, or must explicitly declare `simulation_timestamp_origin` for a canonical timestamp column. For the supplied PaySim transaction CSV that declared origin is `2023-01-01T00:00:00Z`, based on the inspected adapter. This reconstructs simulator hours, not observed dates. Raw bank/account schema conversion remains the existing adapter's responsibility; no new raw-data converter or label generator is claimed.

### Canonical evidence and cutoff

An event is `(id, sender, receiver, amount, time, source_row)`. Different IDs preserve otherwise identical legitimate events; repeated directed pairs remain separate evidence even though GraphFin aggregates their graph edge. Native IDs must be unique within the eligible history. If a native ID is absent, an explicit immutable `source_row_id` is required and the generated ID is `SHA256(canonical_JSON([source_identity, source_row_id]))`. A physical CSV line number is diagnostic only; it is not used as generated identity because inserting future rows would shift it. Source-row IDs must be assigned by the upstream source, not reconstructed from each filtered slice.

Amounts are retained as decimal strings in immutable events; GraphFin receives the same float conversion used by its existing features. No omission changes an amount, reverses an edge, or adds a transfer. The original float32/two-decimal feature quantization remains; exact decimal arithmetic is not claimed for the feature matrix. Invalid/missing times, nonpositive/nonfinite amounts, empty/padded account IDs, duplicate native IDs and eligible self-transfers fail explicitly. Self-transfers are rejected, consistent with the existing nonself canonical preprocessing contract, rather than double-counted or silently removed.

For scoring cutoff T, `E_T={e: t(e)≤T}`. The boundary is inclusive. Timestamp inputs are normalized to UTC; naive timestamps are explicitly interpreted as UTC. Simulation steps must be nonnegative integral hours. They are embedded at a synthetic 1970 epoch **only inside the unchanged FeatureService** to calculate elapsed seconds, daily rates and weekly rates. This embedding is documented in the manifest and is not a real-world date assertion.

The loader validates every row's time to determine eligibility, but does not use future endpoints, amounts, IDs or labels in its history. An invalid future timestamp cannot be classified and therefore fails rather than being silently admitted. Eligible rows retain their source-relative order; adding valid future rows before or after historical rows does not change that order. History hashes exclude physical line offsets and full-file hashes; the latter necessarily change when new evidence is appended and remain provenance metadata only.

`V_T` is the set of eligible endpoints plus explicitly declared `known_accounts`, which callers must establish as known at T. It is never inferred from future rows. Every omission retains this same universe, including newly isolated nodes. An account with no eligible history must be explicitly declared; it gets a zero 19-vector and a `no_historical_evidence` rejection. Future-only evaluation requires a separate predeclared model-training and outcome protocol: a historical snapshot by itself does not establish an inductive or prospective fraud experiment.

### Operators and budget mathematics

Let `H_v={e∈E_T: sender(e)=v or receiver(e)=v}`, `m=|H_v|`, and `A=Σ_(e∈H_v) amount(e)`. The budget denominators refer to the focal account's **historical incident events**, not global graph edges, full future history or distinct counterparties. All retained unrelated events are identical to their baseline records.

**Counterparty family:** for c≠v, `S_C(v,c)={e∈H_v: other_endpoint(e,v)=c}`. The operator is `I_C(G_T,v,c,B)=GraphFin(E_T\\S_C,V_T)` only if the entire set passes B. Inbound, outbound and reciprocal relations to c belong to one group. A group exceeding any budget is rejected intact; no partial group receives the complete-group label. A one-counterparty account will normally reject whole-group omission under default fraction/minimum-retention limits; explicitly allowing fraction 1 and minimum retention 0 permits complete removal while preserving the isolated node.

**Temporal family:** with fixed duration w and cutoff anchor T, block `b=floor((T−t)/w)` corresponds to `(T−(b+1)w,T−bw]`. `S_T(v,b)` contains all incident events in that block. Repeated timestamps remain together; only occupied blocks are emitted, so inactive periods create no synthetic events or empty interventions. Calendar mode accepts seconds or hours; simulation mode accepts hours only. Blocks are identified by their integer index rendered as a string; candidate traversal is lexicographic, not a claim of temporal importance.

**Budgeted family:** rank individual historical events by `SHA256([implementation_version, intervention_seed, focal_account, transaction_id])`. Starting with an empty S, scan this order and add an event only if the enlarged set still satisfies all budgets. Emit one resulting nonempty set, explicitly labeled `budgeted/seeded_greedy`. This is a deterministic bounded omission, not a whole-counterparty omission or uniform random sample. It is not an optimization of fraud labels, model scores, or feature changes. Empty feasible output is rejected with a reason. The independent intervention seed does not change the fixed graph-centrality seed 42.

For any candidate S, require:

`0 < |S| ≤ max_count`

`|S| ≤ max_fraction × m`

`m−|S| ≥ min_retained`

and, if configured,

`Σ_(e∈S) amount(e) ≤ max_amount_fraction × A`.

Count/fraction boundaries are inclusive, compared using decimal representations of configured fractions. Monetary budget comparisons use decimal amounts rather than rounded feature values. The maximum accepted interventions per account is enforced across families in the configured family order. Earlier families can consume the cap; this is recorded selection policy, not balanced sampling. Every rejected candidate retains its whole ID set and reason; a high cap does not imply all candidates are feasible. Families may yield identical omitted sets, but IDs remain family-specific.

### Feature semantics and validity

Baseline and each accepted omission call fresh GraphService/FeatureService instances. All graph, behavioral and temporal features are globally recomputed; no local-delta equivalence is asserted. For small graphs centrality is exact directed unweighted normalized NetworkX betweenness, with the original six-decimal rounding. Above 2,000 nodes the existing seed-42 sampled policy is retained (k=500 through 50,000; k=100 thereafter), and explicitly recorded as sampled. The node order is saved because sampling depends on it. A reference-node limit (default 10,000) fails before computation unless explicitly increased; it is a workload guard, not a scalability claim.

GraphFin's empty-data and active-account feature matrix omit isolates. The wrapper adds the original universe to the analytical graph, invalidates structural/centrality caches when needed, recomputes centrality using the preserved normalization population, and supplies zero canonical vectors for isolated accounts. This does not change production GraphFin. Where the baseline has no additional declared isolates, zero omission reproduces the existing first 19 columns bit-for-bit in tests. If additional known isolates are declared, the normalization population deliberately includes them; this is an explicit universe extension, not identity with a graph that drops those accounts.

The legacy centrality function can return fallback zeros on errors. The wrapper checks its successful cache population and raises if computation failed. No failed centrality calculation becomes a valid intervention record. There is no optimized approximation beyond the existing sampled centrality policy, so no new approximation-versus-reference accuracy claim is made. Sampled centrality changes can include pivot-sampling effects as well as topology effects; Phase 4 must not interpret them as exact local causal effects.

### Reproducibility and artifacts

The writer reuses Phase 2 `PROTOCOL=graphfin-research-v2`, `canonical`, `sha`, root policy, feature schema identifier and manifest field conventions. The stage is `evidence-interventions`; implementation is `transaction-evidence-omission-v1`. It writes only new `data/results/v2/<run-id>` directories inside the repository, or an explicit external output root, rejecting existing run IDs. The manifest is written last; a directory without it is an incomplete run and must not be treated as valid. No historical result path is an output destination.

Files: `config.json`, `baseline.json`, `interventions.jsonl`, `report.md`, `manifest.json`. Shared manifest metadata supplies dataset/full-file/history checksums, cutoff/time units, configuration, universe/population, schema, seed, candidate policy, budgets, recomputation policy, code hashes, library versions, artifact hashes and runtime. Each accepted JSONL record adds focal account, family/key, intervention ID, exact omitted transaction IDs, counts/fractions, baseline/intervened 19-vectors, their elementwise difference, recomputation metadata and measured runtime. Rejections carry reasons and available budget facts. No labels or fraud scores are read or persisted.

Intervention IDs hash the implementation, historical content, cutoff, universe, focal identity, family/key, omitted IDs and configuration. Repeat equality excludes measured runtime; manifest/file hashes containing runtime naturally differ. Replay checks compare IDs, evidence, vectors, deltas and baseline bytes. Cross-version numerical identity is not promised; code/package versions and graph node order are recorded. The Phase 2 E0/E4 smoke artifacts remain unchanged.

### Complexity and scalability limits

One immutable event tuple and an incident index are shared across accounts. The baseline is computed once per engine; one analytical graph is built and discarded per accepted candidate. We do not retain independent graph copies for every candidate. Group indexing costs O(m_v) per focal; seeded ordering costs O(m_v log m_v). Candidate groups are never selected using labels.

With n accounts, e graph edges, M events and K accepted interventions, reference computation costs roughly `(K+1)` times original graph/feature extraction, including O(ne) exact betweenness or O(ke) sampled betweenness plus pandas aggregation and the existing egonet computation. Peak working storage is O(M+n+e), plus current candidate groups, feature matrices and output/report metadata; all accepted feature matrices are not retained. JSONL persists focal vectors rather than full population matrices. Counterparty/time indexes could be cached across repeated requests; time-range indexes and affected-account aggregates could reduce work. They are not implemented as purported substitutes for global centrality. This first correctness path is deliberately bounded and not certified for full PaySim scale.

### Demonstration and measured validation

The synthetic fixture is explicitly artificial, with repeated A→C events, reciprocal A/B transfers, disconnected X/Y, a declared isolated account, equal timestamps, and a transaction after cutoff. It contains no fraud labels. Original network events are directly inspectable in `docs/research/fixtures/phase3_transactions.csv`; `baseline.json` supplies original vectors, JSONL supplies each family's omitted evidence and recomputed vectors, and `report.md` lists observed deltas.

From the repository root:

```powershell
python -m backend.app.research.interventions docs/research/fixtures/phase3_transactions.csv docs/research/configs/phase3_demo.json data/results/v2 my-phase3-demo
python -m backend.scripts.benchmark_phase3 data/results/v2 my-phase3-benchmark
python backend/scripts/verify_phase2.py ../phase3-tests -- -q backend/tests/test_phase3_interventions.py backend/tests/test_phase2_correctness.py
```

The benchmark repeats the demo and selects fixed 500-/1,500-row prefixes of the existing IBM medium transaction file, with the largest incident-count focal (lexical tie break), without labels. It saves the derived subset bytes only in new versioned output directories, along with original/subset checksums. Measurements include traced Python peak allocation via `tracemalloc`, which is **not total RSS/native memory**, and single-run wall time under that tracing overhead. No extrapolation to larger networks or speedup claim is justified.

Executed verification:

| Run | Result | Pytest wall time | Exit |
|---|---|---:|---:|
| Initial intervention checks, `phase2-z2xaggp6` | 30 passed | 8.06 s | 0 |
| Intervention + relevant existing backend regressions, `phase2-0vhhxwah` | 189 passed, 1 skipped | 84.73 s | 0 |
| Final omission-validation/manual-vector changes + Phase 2/features/graph checks, `phase2-p8n0njlc` | 79 passed | 21.46 s | 0 |

The final test file contains 31 intervention cases. Across overlapping runs there are **190 distinct passes, 0 failures, 1 skipped and 0 blocked**. This is a targeted backend regression set, not a claim that the entire backend suite was rerun in Phase 3. Existing exercised modules cover GraphFin features/graphs, anomaly training, demo workflow, evaluation, splits, transfer, IBM/AMLSim adapters, research runner, transactions, protected artifacts and all Phase 2 correctness cases. Unchanged frontend, tax, report rendering and production PaySim-loading tests were not rerun; their earlier results remain Phase 2 evidence.

The sole skipped test is `test_locked_datasets_backend_resolvability`, still missing the two historical processed IBM UUID CSVs. No dataset was regenerated to satisfy it. Tests ran through the existing guarded disposable-copy workflow and approved Windows execution environment; no application event-loop workaround was introduced.

Coverage includes deterministic repeat generation; unchanged inputs; future rows inserted before and after history; label-provider access blocked and label values permuted; bidirectional counterparty grouping; preserved directions and repeated identical events; generated IDs; explicit self-transfer/time/config rejection; equal timestamps and blocks; inactive accounts and single-event accounts; disconnected components; complete-group rejection under each budget; accepted-count cap; zero-omission baseline equality; preserved isolated-node normalization; independently calculated all-19-vector after removing t1/t2; existing sampled global centrality and failure detection; unknown/duplicate omission rejection; manifest checksums and replay.

Observed demo evidence, focal A at simulated hour 9:

| Family | Accepted candidates | Example omitted IDs | Example measured effect |
|---|---:|---|---|
| Counterparty | 5 | B: `t1,t2` | Incident count 7→5; incoming amount 29→17; outgoing amount 35→25 |
| Temporal | 2 | Block 0 `(6,9]`: `t6,t10` | Incident count 7→5; net flow −6→−4 |
| Budgeted | 1 | Seeded greedy: `t4,t5` | Incident count 7→5; incoming amount 29→21; outgoing amount 35→28 |

One temporal block was rejected because its four events exceeded the maximum count of two. The unrelated X/Y component and future event t11 were not omitted into or added to any accepted view. The baseline and all accepted records match between `phase3-verified-demo-a` and `phase3-verified-demo-b` after excluding runtime. `phase3-final-cli` successfully exercises the documented CLI on the final implementation. These are feature changes, not fraud-detection improvements.

Measured bounded workloads (single machine, tracing enabled):

| Workload | Historical events / accounts | Accepted omissions | Wall time | Peak traced Python bytes |
|---|---:|---:|---:|---:|
| Synthetic demo A | 10 / 9 | 8 | 2.574 s | 732,993 |
| Synthetic demo replay B | 10 / 9 | 8 | 2.254 s | 395,603 |
| IBM first 500 rows | 500 / 533 | 3 | 4.171 s | 3,200,553 |
| IBM first 1,500 rows | 1,500 / 1,586 | 3 | 33.467 s | 7,308,430 |

Both IBM workloads used exact centrality; the above-2,000 sampled branch was exercised separately by a synthetic sparse regression. The IBM cap was three accepted interventions, consumed by counterparty candidates; it is a computational workload test, not balanced comparison across families. Timing includes output and code-hash collection under tracemalloc and was collected while independent disposable tests were also executing; resource contention and first-run overhead limit comparisons. No confidence interval or performance generalization is asserted.

Machine-readable measurements and derived prefix checksums are in `data/results/v2/phase3-verified-evidence/benchmark.json`. The four corresponding run directories contain complete manifests. Generated v2 outputs follow the existing Git-ignore policy; preserve them separately when moving or committing the source. In the enclosing workspace, `outputs/phase3_evidence/` contains copied JUnit reports, logs, exact commands, benchmark data and `verification.json` with per-test outcomes and protected-file checksums.

Integrity checks compared all **87 protected files** to both the supplied ZIP and Phase 2 manifest: all match. Every pre-existing `backend/app/*.py` file (recursively, including Phase 2 additions) was also byte-compared against the final Phase 2 disposable snapshot and is unchanged. `git diff --check` passed. The title, datasets, labels, historical E0–E5 metrics and React frontend are unchanged.

### Acceptance disposition

| Criterion | Result |
|---|---|
| Three constrained families implemented and tested | Satisfied: group, temporal and seeded budgeted omissions |
| Historical cutoff enforcement | Satisfied: inclusive boundary and future insertion/append invariance |
| Validity and budgets | Satisfied: shared checks, whole-group rejection, reasons and caps |
| Baseline reproduction | Satisfied: exact existing 19-vector comparison under the same account universe |
| Correct feature changes | Satisfied: global recomputation, independent manual vector and isolate normalization tests |
| Determinism | Satisfied: repeat IDs/evidence/features; saved-config replay |
| Protected inputs unchanged | Satisfied: 87/87 checks and unchanged existing application source |
| Versioned manifest outputs | Satisfied: Phase 2 protocol stage, checksums, append-only destination |
| Tests and transparent failures | Satisfied: 190 distinct passes; one explicitly documented unavailable-fixture skip |
| Demonstration and documentation | Satisfied: CLI, synthetic fixture, machine-readable records, human report and measured workloads |

Phase 3 is complete at this scope. No Git commit or Phase 4 implementation was performed.

### Phase 4 interface and limitations

Use `load_history(bytes, InterventionConfig)`, `InterventionEngine(history, config).generate(focal)`, or the append-only writer. Phase 4 can consume baseline/intervened vectors together with exact omitted sets and rejection reasons, then apply a separately versioned, source-fitted model without refitting on intervention/test labels. No final scoring or ranking API exists here.

Unresolved PaySim label provenance (774 versus 2,606 positives) remains unchanged and irrelevant to correctness tests. Mixed-currency source amounts, incomplete upstream histories, legacy float32 rounding, global graph dependence and sampled-centrality variability remain limitations. Callers are responsible for truthful source-row identity, event-time semantics and accounts declared known at cutoff. Real-world delayed-arrival/availability timestamps are absent: this phase enforces event-time cutoff, not a claim that all historical events were operationally observable at T.
