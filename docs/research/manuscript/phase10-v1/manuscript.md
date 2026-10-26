# Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions

IEEE-style review draft, version phase10-v1, 25 October 2026. This is a new evidence-aligned draft, not a revision of an inspected original manuscript: the earlier six-page manuscript source was not found in this checkout. Author affiliations, correspondence, funding declarations and target-venue formatting are not asserted and require author completion. This Markdown source follows IEEE-style sectioning and numbered references; it is not a compiled IEEE template or submission certification.

**Abstract** - Financial transaction graphs support retrospective account anomaly ranking, but experimental conclusions depend on data identity, split construction and evaluation semantics. GraphFin integrates directed transaction aggregation, structural/behavioral/temporal features and Isolation Forest with versioned saved-score evidence. We review six account splits on two supplied synthetic IBM AML subsets containing 5,000 and 49,992 active accounts. The evaluation is transductive: graph features use the complete observation graph, while unsupervised model fitting uses training-account features. Mean Average Precision varies with split and representation; richer features do not uniformly improve retrieval. Existing exact replay verifies determinism for supplied inputs, not independent generalization. Constrained transaction-evidence omission was also evaluated as a frozen-model sensitivity diagnostic. Thirteen available records represent five distinct account/omission scenarios, and twelve budget-compatible direct explanation comparisons tie. Detector and explanation superiority are unsupported. The accompanying read-only dashboard, bounded graph explorer and institutional PDF export improve evidence inspection without adding detection evidence. Partially verified IBM label lineage, unresolved PaySim labels, graph dependence and limited positive support constrain inference. The defensible contribution is a reproducible empirical system with explicit negative findings and provenance boundaries rather than a newly superior anomaly detector.

**Index Terms** - transaction graphs, anomaly ranking, Isolation Forest, Average Precision, reproducibility, model sensitivity.

## I. Introduction

Retrospective anomaly ranking can prioritize unusual account behavior for further inspection. It does not establish financial crime or calibrated fraud risk. A transaction graph retains directed counterparty relationships and aggregated monetary activity; account vectors make this structure available to conventional unsupervised detectors. Graph features and Isolation Forest are established methods [1]-[3]. The research question is therefore whether the selected representations show consistent descriptive retrieval behavior under a controlled supplied-data protocol, and what can be inferred from constrained evidence omission.

GraphFin contributes (i) explicit dataset, label, feature, split and model identities; (ii) comparable saved-score results across six splits and separate bounded model-seed analysis; and (iii) transaction-to-feature-to-frozen-score diagnostics that retain unavailable and negative outcomes. The application provides evidence access through FastAPI, a research dashboard, a bounded topology viewer and formal reports. These system-engineering accomplishments are distinguished from algorithmic novelty and predictive effectiveness.

## II. Related Work and Differentiation

Isolation Forest isolates observations through randomized partitioning and path lengths [1]. GraphFin applies its existing implementation to account summary vectors; it does not propose a new isolation objective. Dumitrescu et al. [2] already combine bank-transaction graph features, reduced egonets, circular-flow information and unsupervised anomaly detection including Isolation Forest. This 2022 Graphomaly work is the closest documented overlap. GraphFin's E5 uses four project-specific egonet/circular heuristics and is not a faithful full reproduction of that published method. Consequently, graph features plus Isolation Forest is not a first-of-kind claim, and E5 results do not constitute a head-to-head reproduction of Graphomaly.

OddBall [3] models regularities in weighted egonets, whereas GraphFin uses fixed account summaries as detector inputs. Removal-based explanation is an established framework [4]. Here, historical transaction events are omitted under explicit constraints and features are recomputed for a frozen model; that is model-sensitivity evidence rather than proof of causal relevance, minimal recourse or explanation superiority. IBM's synthetic AML work [5] supplies generator context, but does not authenticate the lineage of these particular transformed files. No result from a different task or dataset is inserted into the GraphFin comparison tables. The contribution is bounded empirical/reproducibility evidence and transparent engineering, with substantial methodological overlap acknowledged.

## III. GraphFin Methodology

Let T be validated events (sender, receiver, positive amount, time), excluding self-transfers. Accounts are vertices. For each ordered pair (u,v), create u->v when at least one retained event connects them. Store w(u,v)=sum of retained amounts and c(u,v)=retained multiplicity; reverse edges remain separate. Duplicate event IDs are rejected rather than counted twice. Times are supplied synthetic observations, not authenticated real bank timestamps. Amount currency normalization is not independently established.

The research pipeline constructs a NetworkX graph, extracts a frozen ordered feature matrix and selects a feature subset per method. Labels are used for declared stratified splitting and evaluation, not unsupervised fitting or target-label tuning. Scientific computation and serving are separate: the research API reads checksum-pinned JSON evidence; browser interaction does not fit or rescore models.

### A. Canonical Feature Construction

For account v, let I/O be its incoming/outgoing event multisets, m their combined count, R/S the received/sent sums, N-/N+ distinct predecessors/successors, sorted incident times t1,...,tm, gaps delta_i=t_(i+1)-t_i, and D=max((tm-t1)/86400,1). The canonical nineteen columns, in order, are:

|#|Feature|Definition|
|---|---|---|
|1|in_degree|number of distinct incoming neighbors, size(N-)|
|2|out_degree|size(N+)|
|3|total_degree|in_degree + out_degree; reciprocal counterparties count twice|
|4|weighted_in_degree|R|
|5|weighted_out_degree|S|
|6|betweenness_centrality|directed unweighted normalized shortest-path betweenness, endpoints excluded|
|7|transaction_count|m; repeated ordered pairs retain event multiplicity|
|8|total_sent|S|
|9|total_received|R|
|10|net_flow|R-S|
|11|average_transaction_amount|(R+S)/m when m>0|
|12|maximum_transaction_amount|largest incident event amount|
|13|unique_receivers|size(N+)|
|14|unique_senders|size(N-)|
|15|transactions_per_day|m/D for m>1; 1 for one event; 0 for no events|
|16|transactions_per_week|seven times unrounded daily rate|
|17|average_time_between_transactions|mean delta, or0 when m<2|
|18|minimum_time_between_transactions|min delta, or0 when m<2|
|19|maximum_time_between_transactions|max delta, or0 when m<2|

Directed betweenness normalizes sum over reachable s,t of sigma_st(v)/sigma_st by (n-1)(n-2). The frozen research implementation uses exact calculation through2,000 nodes, k=500 sampled pivots through50,000, k=100 above, with centrality seed42. Preserve the recorded NetworkX implementation and node-order semantics; this is not exact centrality on the larger tiers. Betweenness is rounded to six decimals, monetary summaries to their recorded precision, temporal summaries to four decimals, and the frozen matrix uses float32. Exact rounding/code hashes belong to the evidence manifests.

The columns are redundant: degrees duplicate distinct counterparty counts; weighted degrees duplicate sent/received sums; total degree and net flow are algebraic combinations; weekly rate is a multiple of daily rate. Floating arithmetic/rounding can make these identities near-exact. The nineteen columns are not nineteen independent signals. No new deduplication ablation is claimed. The exported matrix appends four E5 columns (egonet node count, edge count, density and circular-flow heuristic), making23 columns available overall; E4 still uses only the canonical19.

### B. Baseline Definitions and Scores

|Method|Frozen input|Version/definition|
|---|---|---|
|E0|graph-six|e0-source-signed-zero-v2; max signed training-standardized feature, population SD; contribution0 if SD<=1e-9|
|E1|graph-six|isolation-forest-raw-v2|
|E2|graph + behavioral,14|same IF version|
|E3|graph + temporal,11|same IF version|
|E4|canonical19|same IF version|
|E5|four egonet/circular columns|same IF version; project heuristic, not full Graphomaly|

For E0, z_j(v)=(x_j(v)-mu_j)/sigma_j when sigma_j>1e-9 and0 otherwise; s_0(v)=max_j z_j(v), with statistics from training accounts only. Historical absolute/scaled/epsilon-based E0 definitions remain archival and must not be pooled with this version.

For E1-E5, use100 trees, max_samples=auto, contamination0.005, n_jobs=1, raw features without a standard scaler, and model seed42 for split comparisons. Isolation Forest's conceptual isolation score is 2^(-E[h(x)]/c(psi)) [1]. Actual GraphFin ranking uses **-decision_function(x)** from the recorded sklearn version; larger means more anomalous. The conceptual formula is not substituted numerically for stored scores. These scores are not calibrated fraud probabilities.

E6_BASE is the historical source empirical mid-CDF transformation of frozen E4, without interventions. It is a nondecreasing calibration that may merge distinct values into ties. It adds no evidence and is reported separately; it is not a completed E6_CREST evaluation.

## IV. Dataset and Experimental Protocol

The supplied IBM5K tier contains31,463 retained events,5,000 accounts and20 positive account labels; each 70/30 stratified split has3,500 training/1,500 held-out accounts and6 held-out positives. The approximately50K tier contains353,860 source rows,353,850 retained events,49,992 active accounts and249 positive account labels. Each split has34,994 training/14,998 held-out accounts, including75 positives. Its label file has50,000 rows, including eight inactive negative-only accounts; label-file and active populations are distinguished.

The implemented account label rule is endpoint OR involvement in selected flagged source transactions, not proof that each endpoint is culpable. Raw laundering flags and authenticated conversion inputs were not supplied. Conversion labels are assigned before monetary rounding; later positive-amount filtering can remove rounded-zero events. Thus code-level OR semantics and independently reconstructed retained-history truth must not be conflated. IBM lineage is **partially verified**: supplied counts, IDs, active filtering, split coverage and hashes are verified, but original ground truth cannot be independently reconstructed.

PaySim has two label files on the same547,686-account population:774 versus2,606 positives with1,832 disagreements. Neither label definition is silently preferred. Its generation provenance is unresolved and no validated PaySim performance or cross-domain transfer table is included. Simulator publications do not resolve these byte-specific labels.

The six split seeds are42,123,7,2024,99,555; model seed is42; centrality seed is42. The model-seed analysis fixes split42 and varies13,42,101 for E1/E4 only, at both tiers. Features use the full observation graph, including held-out accounts/edges: this is **transductive entity holdout**, not prospective, unseen-network or future-transaction validation. Source-only unsupervised fitting does not remove that transductive information scope.

### A. Metrics and Uncertainty

Average Precision is non-interpolated AP=sum_j (R_j-R_(j-1))*P_j over distinct score thresholds, grouping ties. It is not trapezoidal PR integration. P@K uses score-descending order with account-ID tie-break and divides retrieved positive labels by effective K. Lexical tie-breaking affects top-K/ordinal ranks but not threshold-grouped sklearn AP. Coarsening scores into ties can change AP; a strictly increasing transform that preserves ties cannot.

Six-split mean AP is sum(A_i)/6. **Sample SD** is sqrt(sum((A_i-mean)^2)/5). These overlapping splits are not six independent datasets. SD describes observed dispersion, not a95% confidence interval or a significance test. Tiny held-out positive support, graph dependence and overlapping splits prevent strong winner/generalization claims. Undefined resamples are counted by the corrected bootstrap implementation; this draft adds no new interval or significance claim.

## V. Baseline Results

TablesI-II reproduce saved-score metrics, verified during Phase10 by84 AP reconstructions (2 tiers x6 splits x7 stored methods), maximum difference0.0. No model was refitted. The72 E0-E5 rows are shown here; the twelve E6_BASE rows remain separately identified in `evidence_tables.json`. Full precision, P/R/hits@K and source SHA256 records are retained there. Display values below are rounded to six decimals.

**Table I. IBM5K AP for six split seeds, mean/sample SD, and mean P@100.**

|Method|42|123|7|2024|99|555|Mean AP|Sample SD|Mean P@100|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|E0|0.190758|0.179754|0.175903|0.014686|0.006658|0.012789|0.096758|0.093694|0.013333|
|E1|0.057130|0.054309|0.092981|0.008032|0.005574|0.009934|0.037993|0.035755|0.011667|
|E2|0.184212|0.176109|0.094470|0.007523|0.005467|0.009083|0.079477|0.085020|0.006667|
|E3|0.194830|0.181048|0.179710|0.007888|0.008408|0.010429|0.097052|0.096705|0.013333|
|E4|0.194545|0.177102|0.180686|0.006784|0.006104|0.010239|0.095910|0.096805|0.011667|
|E5|0.017521|0.009286|0.012105|0.004000|0.004000|0.004000|0.008485|0.005581|0.010000|

**Table II. IBM approximately50K; same protocol and descriptive statistics.**

|Method|42|123|7|2024|99|555|Mean AP|Sample SD|Mean P@100|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|E0|0.011613|0.009969|0.038768|0.019384|0.011472|0.039761|0.021828|0.013905|0.025000|
|E1|0.022242|0.013135|0.027132|0.031863|0.010852|0.040036|0.024210|0.011158|0.031667|
|E2|0.017253|0.010568|0.035245|0.028313|0.009605|0.036962|0.022991|0.012166|0.015000|
|E3|0.012099|0.011624|0.036700|0.028948|0.008499|0.036929|0.022466|0.013220|0.025000|
|E4|0.014894|0.012826|0.035697|0.030384|0.009100|0.038065|0.023494|0.012678|0.016667|
|E5|0.009942|0.027769|0.027027|0.007777|0.027428|0.007230|0.017862|0.010499|0.051667|

E3 has the largest displayed mean AP on5K and E1 on50K, but differences and dispersion do not establish a generally superior method. More features do not yield monotone improvement. E5's50K mean AP is lower than E4's while its mean P@100 is higher, illustrating metric-dependent behavior. Network scale, composition, history and prevalence differ simultaneously; no causal network-size effect is isolated. The original paper's single-run E4 lead is not generalized by these multi-split results; historical versions/configurations cannot be silently pooled.

### A. Calibration-only E6_BASE

|Tier|Mean AP|Sample SD|Interpretation|
|---|---:|---:|---|
|5k|0.081992|0.087770|Empirical-CDF calibration only; no intervention evidence|
|50k|0.020825|0.010495|Empirical-CDF calibration only; no intervention evidence|

These values are not evidence of CREST detection improvement. The original intervention-based E6 benchmark is incomplete and has no completed detector-performance table.

## VI. Split Variability, Model Seeds and Reproducibility

Model randomness is a separate axis. Fixed-split model-seed summaries below concern only E1/E4 and three seeds, not all baseline methods or a full variance decomposition.

|Tier|Method|Mean AP|Sample SD|Minimum AP|Maximum AP|
|---|---|---:|---:|---:|---:|
|5k|E1|0.099345|0.072936|0.057130|0.183564|
|5k|E4|0.190727|0.003307|0.188817|0.194545|
|50k|E1|0.017713|0.003935|0.015136|0.022242|
|50k|E4|0.015868|0.002633|0.013860|0.018850|

Large full-ranking correlations do not ensure stable rare-positive retrieval. Same-split reproducibility must be separated from sensitivity to different seeds. Existing independent5K and Phase6C fresh50K replay compared scientific feature/score/membership/result files byte-for-byte, tolerance0; runtime/serialization-dependent metadata were excluded. Phase10 verifies existing evidence and AP values only, without rerunning those fits. Same-input replay is not independent external validation. Manifests identify dataset and label hashes, feature schema, source/configuration hashes, split/model/centrality seeds, software versions and saved score paths; dirty working-tree source hashes are required in addition to git HEAD.

## VII. Constrained Evidence-Sensitivity Diagnostics

For frozen anomaly score s and history-to-features map phi, signed omission fidelity is F(v,O)=s(phi(H,v))-s(phi(H\O,v)). Positive F means omission lowers the score; negative F means it raises the score. O consists only of observed transaction identities, constrained by retained incident count and amount budgets. No synthetic relationship is invented as evidence. Missing valid omissions or matched controls remain unavailable, not an automatically valid zero effect.

The completed bounded Phase6A diagnostic has24 saved rows on six selected accounts. Thirteen rows contain available intervention evidence, representing only five distinct account/omission scenarios, and four accounts have any explanation. All24 original scores match the frozen E4 baseline, with explicit dataset/population/cutoff/model identity checks. Twelve budget-compatible direct explanation comparisons tie; three incompatible comparisons are excluded. Counterparty's single positive fidelity is reproduced by simple heuristics. Temporal fidelity is negative on all four eligible accounts. Available and unavailable rows are retained rather than reporting only favorable responses.

The evidence supports neither CREST detector superiority nor explanation superiority. Omission response is not causal evidence of wrongdoing. Reversal/perturbation probes had limited coverage; general robustness and matched-excess stability remain unestablished. Global sampled betweenness dominated fresh diagnostic work, limiting meaningful coverage. Prior Phase5H ranking development was stopped; the original full E6 intervention detector comparison remains incomplete. This draft recommends retaining CREST as an optional experimental sensitivity/model-inspection component, without launching another scoring formula or experiment.

## VIII. System Architecture and Demonstration

FastAPI exposes checksum-pinned research summaries and deterministic institutional PDF exports separately from preserved operational APIs. React/TypeScript provides overview, datasets, experiments, comparisons, seed analysis, reproducibility, diagnostics and limitations. The graph route reads a private SQLite index of real supplied directed topology, restricted to a fixed600-account lens per dataset, at most250 displayed nodes/500 edges and1-2 hops. Session capabilities and opaque references bind identity/snapshot; repeated sessions do not expand that fixed pool. A validated short-lived Web Worker computes deterministic static layout; accessible account/relationship lists support keyboard inspection. The browser never loads the full50K graph.

These features facilitate evidence inspection and traceability. They are engineering contributions, not new statistical evidence or proof of privacy. Pseudonymized topology can be structurally reidentified. Legacy raw-ID/mutating APIs remain outside this new boundary, and source artifacts themselves contain synthetic account identities. Public deployment and redistribution require separate controls and permission review. Formal PDF exports use serif/sans-serif typography and explicit data/label limitations; visual sophistication does not improve anomaly detection.

## IX. Discussion and Limitations

The strongest supported result is an auditable transductive empirical framework with versioned definitions, deterministic replay and transparent negative diagnostics. The study does not establish a new general anomaly-detection method. Closest prior graph-feature/Isolation-Forest overlap [2] is substantial; E5 cannot substitute for a faithful reproduction of that method. No external-method superiority or cross-domain accuracy is claimed.

Limitations include supplied synthetic data and partially verified endpoint labels; unresolved PaySim definitions; very few held-out positives on5K; dependent graph accounts and overlapping splits; redundant features and sampled centrality; only two related network subsets; narrow fixed-split model-seed analysis; missing source for some historical single runs; limited explanation coverage/stability and expensive global feature recomputation. No calibrated financial-risk interpretation, prospective performance, causal evidence, statistical significance, broad robustness, production security certification or submission probability follows.

The original manuscript source, author metadata and target IEEE venue requirements remain unavailable. Before submission, authors must verify redistribution permissions, complete source-to-claim review, identify an appropriate empirical/system venue and satisfy its formatting/ethics/reproducibility requirements. Independent traceable validation would be required for any future generalization claim; this draft instead narrows its conclusions. No costly CREST experiment is proposed merely to make novelty claims stronger.

## X. Conclusion

GraphFin combines established graph summaries and Isolation Forest in a reproducible, inspectable research system. Saved-score verification and exact replay support supplied-input reproducibility, while six-split comparisons expose substantial variation and nonmonotone feature enrichment. Constrained evidence omission remains an experimental model-sensitivity diagnostic with limited availability and tied direct comparisons. Neither detection nor explanation superiority is established. The application and reporting layer make these boundaries accessible; they do not remove scientific, provenance or deployment limitations.

## References

[1] F. T. Liu, K. M. Ting, and Z.-H. Zhou, "Isolation Forest," IEEE International Conference on Data Mining, 2008. Author-hosted primary paper: https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf .

[2] B. Dumitrescu, A. Baltoiu, and S. Budulan, "Anomaly Detection in Graphs of Bank Transactions for Anti Money Laundering Applications," IEEE Access, vol.10, pp.47699-47714, 2022, doi:10.1109/ACCESS.2022.3170467. Author manuscript: https://graphomaly.upb.ro/Articole/AD_graphs_AML_2022.pdf .

[3] L. Akoglu, M. McGlohon, and C. Faloutsos, "oddball: Spotting Anomalies in Weighted Graphs," PAKDD, LNCS6119, pp.410-421, 2010, doi:10.1007/978-3-642-13672-6_40. Publisher: https://link.springer.com/chapter/10.1007/978-3-642-13672-6_40 .

[4] I. Covert, S. Lundberg, and S.-I. Lee, "Explaining by Removing: A Unified Framework for Model Explanation," JMLR, vol.22, no.209, pp.1-90, 2021. https://www.jmlr.org/papers/v22/20-1316.html .

[5] E. Altman, J. Blanusa, L. von Niederhausern, B. Egressy, A. S. Anghel, and K. Atasu, "Realistic Synthetic Financial Transactions for Anti-Money Laundering Models," NeurIPS, 2023. IBM primary publication record: https://research.ibm.com/publications/realistic-synthetic-financial-transactions-for-anti-money-laundering-models .

Primary records rechecked25 October2026; additional verified comparisons remain in06B_related_work_comparison.md. No academic reference or numerical improvement was invented. Author copies are distinguished from publisher access; no venue page limit is assumed.

## Evidence-to-claim alignment

|Claim/table|Evidence|Boundary|
|---|---|---|
|Tables I-II and calibration table|phase10-v1/evidence_tables.json, pinned Phase6B per-seed metrics and saved score maps|AP reconstruction only; no refits|
|Model-seed table|pinned Phase6C table_F_variability.json and model_seed_per_run.json|E1/E4, split42, three seeds only|
|Feature/method definitions|feature_service.py, Phase1 audit, pinned table_C_configurations.json and baseline protocol|Canonical19 vs appended egonet4; E0 versions distinct|
|IBM/PaySim lineage|06C_label_lineage.md, pinned dataset records and paysim_provenance.json|Partial IBM lineage; unresolved PaySim|
|Exact replay|06C_final_validation.md, 06C_replay_and_seed_analysis.md, pinned replay_comparison.json|Existing same-input comparison, not new Phase10 fitting|
|CREST negative findings|06A_explanation_validation.md; pinned24 diagnostic rows; Phase9 diagnostic identity verification|13 available rows,5 unique scenarios,12 tied compatible comparisons|
|System functionality/security|09_interactive_graph_explorer.md and Phase10 validation/security reports|Functional tests and local lab evidence, not detector improvement|
