# Phase 6C — Label lineage

**Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions**

Date: 2026-10-23. IBM status **PARTIALLY verified**; PaySim **unresolved_conflict**. No dataset download, replacement, label rewrite or performance-driven label choice was performed.

## IBM: trace and boundaries

The rule implemented in `backend/scripts/convert_ibm_aml.py` is

\[
y_v=\max_{e\in H_{selected,valid}}\mathbf1\{\mathrm{IsLaundering}_e=1\}\mathbf1\{v\in\{sender_e,receiver_e\}\}.
\]

An account is positive if incident to at least one flagged retained transaction. This is involvement, not proof of culpability. A receiver may be a victim or intermediary. Neither an unsupervised anomaly score nor an endpoint label establishes real laundering.

| Step | Verified code/evidence | Status |
|---|---|---|
| Raw source | `data/research/README.md` declares HI-Small, 5,078,345 raw rows and seed42 commands. No authenticated original `HI-Small_Trans.csv`, raw flags or conversion-run input checksum is supplied in the repository. | Declared only |
| Account selection | `collect_sampled_accounts` streams until target account count is reached, then seed-shuffles only any overshoot; conversion keeps events with both endpoints in that set. This is not a uniform random sample of the entire raw population. | Code verified; original invocation/bytes not authenticated |
| Composite identity | Stripped bank + `_` + stripped bank-local account, separately for sender/receiver. Tests check different-bank separation and whitespace handling. Supplied IDs are unique in label files. | Implementation and supplied IDs verified; raw identity reconstruction blocked |
| Transaction flag | Numeric `Is Laundering`, missing/non-numeric becomes0, then positive iff equal1. This coercion could conceal invalid raw flags; no such raw-data audit is possible here. | Code verified, actual raw flags absent |
| Validity filtering | Positive pre-rounded Amount Paid, nonself endpoints, nonempty timestamp/identifiers; selected-endpoint filter. | Implementation verified |
| Endpoint aggregation | OR over sender and receiver, before monetary rounding to two decimals. Converter writes only canonical columns, dropping transaction flags. | Synthetic regression verified; supplied labels cannot be reconstructed from flag-free CSV |
| Post-rounding population | Research `load_input` again removes nonpositive/nonself transactions. Thus pre-rounding label aggregation is not automatically identical to OR over post-rounding retained events. | Supplied population differences independently checked; event-level equality remains unverified |
| Registration | Legacy `research_runner.py` preprocesses/registers transactions via dataset registry and loads labels separately. Phase 5/6C bypass mutable registry with explicit hash-checked `InputSpec` paths. Historical UUID CSVs are absent. | Current explicit path verified; historical UUID reconstruction incomplete |
| Split | `benchmark/runner.py:prepare`, sorted IDs, 70/30 sklearn stratified account split; six fixed seeds. Full graph built before split. | All memberships disjoint/unique, partition verified |
| Evaluation | Independent CSV-to-population label mapping compared; every E0–E5/E6_BASE saved score map exactly covers its test IDs; all 84 metrics recalculated. | Verified |

Both supplied IBM transaction files have columns `transaction_id,sender_id,receiver_id,amount,timestamp,transaction_type`; neither retains `Is Laundering`. Executing a converter test on synthetic raw rows validates the code, **not** the lineage of these supplied files. Account IDs alone cannot reveal missing event labels. No fabricated reconstruction is reported.

## Independently counted populations

| Tier | Label rows | Active accounts | Positive | Negative | Full prevalence | Held-out positive / negative |
|---|---:|---:|---:|---:|---:|---|
| 5K | 5,000 | 5,000 | 20 | 4,980 | .004 | 6 / 1,494 |
| ~50K | 50,000 | 49,992 | 249 | 49,743 | .004980796928 | 75 / 14,923 |

All six split counts verified. 5K train positives=14; 50K train positives=174. Transaction IDs and account-label IDs are unique; labels are explicit binary values; no active account lacks a label. The 50K file has 353,860 rows before filtering and 353,850 afterward; eight inactive label accounts are all negative. Their exact IDs are retained in `data/results/v2/phase6c-evidence-v1/ibm_lineage.json`. This verifies membership effects, not the claim that no flagged event was removed.

Exact IBM file hashes, schema and counts are in `table_A_datasets.json` and the frozen Phase 5 configuration. Feature construction remains full-observation transductive. The data README's historical “real” terminology does not make simulated IBM data real bank observations. Supplied currency amounts are not an authenticated common-currency valuation.

## PaySim conflict

| File | SHA256 | Population | Positives |
|---|---|---:|---:|
| `data/research/paysim_labels.csv` | `59b99a79e6c77b09fb5f63d03037a003e9b08deaea4f9227b8843a16f0abfecb` | 547,686 | 774 |
| `data/research/paysim_account_labels.csv` | `3cf7a6f6c0bae57393fc59679cb586c2d797b7edeb8663524aa88ae18debb085` | 547,686 | 2,606 |

Independent recount confirms the **same account set**, no duplicate IDs, **1,832 disagreements**, and the 774 positives are a subset of 2,606. Among disagreements in the supplied transaction history, 1,831 are receiver-only and one is sender-only. This suggests possible history/role differences but does not prove a generation procedure. The 10,000-row production prefix has 18,711 accounts, with 12 versus129 positives; prefix selection does not explain disagreement on the common full label population.

`backend/scripts/convert_paysim.py` aggregates endpoint OR on valid raw events, then its optional label-aware account subset retains previously aggregated labels without recomputing after edge filtering. `backend/app/services/paysim_adapter.py:derive_paysim_account_labels` instead takes endpoint maximum over supplied raw fraud flags. These procedures can have different history scopes. Neither is authenticated as the generator of both supplied label files; the extra `label_meaning` column is descriptive, not evidence of correctness. No authoritative script/run provenance for that file was found.

The supplied `paysim_transactions.csv` has no `isFraud`/`is_fraud` column (SHA256 `194d3d0527106464350af8d5b9e40c14c112b7531396cd49755dcc88fa31eb7c`). Raw fraud labels, original generation logs and matched raw-file hashes are missing. Generic PaySim documentation cannot determine which file matches these bytes. No substitute dataset was downloaded.

Machine-readable record: `data/results/v2/phase6c-evidence-v1/paysim_provenance.json` includes hashes, roles, procedures, unsupported assumptions and consequences. Both files remain unchanged. No validated transfer result is included in the manuscript tables. Historical transfer flags/metrics remain archival and cannot certify cross-domain accuracy.

## Minimum provenance action

Obtain authenticated raw files/flags and generation commands/manifests, then reconstruct labels into a **new** namespace and compare exact IDs/assignments, including before/after rounding and edge filtering. Until then, frame IBM results as reproducibility on supplied, upstream-unverified labels; exclude PaySim performance claims. Dataset redistribution licensing remains unverified; this local evidence package is not a public-data release.
