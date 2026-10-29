# Graph metrics and professional audit PDF validation

Validation date: 29 October 2026. Baseline: `c2a84a4162618f5e168307564352dd3ebadc49cd`.

## Findings and corrected definitions

The previous `inDegree`, `outDegree` and `avgDegree` fields counted transaction occurrences. Labels implied distinct-neighbor graph degrees. Those legacy fields remain unchanged for scoring and recovered-session compatibility; new explicit fields expose unique directional neighbors and counterparty union, excluding self. UI tooltips, inspectors, CSV/JSON and PDF labels now distinguish them.

* Incoming/outgoing transaction counts count every accepted transfer. A self-transfer contributes once to each.
* Unique in/out degrees count distinct other source/destination accounts. A reciprocal neighbor contributes to both directional degrees, once to the counterparty union.
* Unique directed edges count ordered account pairs, including a self-pair if present. Simple directed edges exclude self-pairs.
* Mean simple total degree is `2 * simple directed edges / accounts`; mean transaction incidences is `2 * accepted transfers / accounts`.
* Repeated directed pairs have more than one transfer. Additional repeated transfers are `transfers - ordered pairs`.

The old noteworthy-cycle field counted participating accounts passing a threshold, rather than all observed cycles. Zero was a valid qualifying count on the benchmark but the label obscured ordinary cycles. The replacement enumerates directed 3/4-account cycles once per rotation; reverse direction is distinct. Repeated transfers are aggregated before enumeration. Each cycle scan has a 2,000,000-operation limit; incomplete scans disclose lower bounds and withhold benchmark evaluation. Reciprocal pairs are counted separately. Qualifying loops retain the existing rule: at least five transfers each way, or minimum aggregate loop-edge amount greater than 15% of mean account volume. Self-loops are excluded. Longer cycles are not enumerated.

## Benchmark, independently recomputed

The existing 10,000-transfer synthetic CSV was read locally, never committed or transmitted. Independent Python NetworkX and scikit-learn calculations agree with the TypeScript engine.

| Metric | Previous report | Corrected report |
|---|---:|---:|
| Accepted transactions / accounts / directed edges | 10,000 / 1,000 / 9,860 | unchanged |
| Average degree | 20.00, ambiguous | 19.72 unique-neighbor total degree; 20.00 transaction incidences |
| ACC000662 incoming / outgoing | 5 / 59, ambiguous | 5 / 59 transactions; 5 / 10 unique neighbors; 15 counterparties |
| Repeated pairs / additional transfers | unavailable | 44 / 140 |
| Directed 3-account / 4-account cycles | unavailable | 335 / 2,362 |
| Reciprocal pairs | unavailable | 47 |
| Qualifying loops / participating accounts | 0 | 0 / 0 |
| Total transaction amount | INR 27,216,411.41 | unchanged |
| Review flags | 9 | unchanged |
| Account-associated positives | 328 | unchanged |
| Transaction labels, positive / normal | 400 / 9,600 | unchanged |
| Precision | 100% | 100% |
| Recall | approximately 2.7% | 2.743902439% (display 2.74%) |
| F1 | 0.0534 | 0.0534124629 (display 0.0534) |
| Average precision | 0.5211 | 0.5211393115 (display 0.5211) |
| TP / FP / FN / TN | not shown together | 9 / 0 / 319 / 672 |

The three edges in `ACC000801 -> ACC000183 -> ACC000711 -> ACC000801` are present. None of the 335 three-cycles, 2,362 four-cycles or 47 reciprocal pairs qualifies: the loop-edge threshold is INR 8,164.923423 and no pair has five transfers each way.

All 1,000 account scores, flags and pattern lists exactly match the baseline engine. Weights remain 30% volume extremity, 25% transaction-count divergence, 20% flow asymmetry and 25% structural indicators. Review conditions and four-decimal rounding are preserved. Removing all labels and pattern annotations leaves every score unchanged. Evaluation aggregates positive labels to either participating account, groups tied scores for AP and excludes unknown labels from asserted complete-label evaluation. High precision on nine flags coexists with 319 missed label-associated accounts.

## Report and interface

One canonical report model feeds every section. The new compressed, searchable A4 report uses jsPDF's standard Helvetica, white/charcoal surfaces, crimson accents, consistent margins, numbered sections, page headers/footers, wrapping cells and repeated table headings. It has five pages for the benchmark and four when evaluation is unavailable. Large flag tables paginate; only the top 15 flags are shown with explicit disclosure. Extremely long cell content is explicitly marked truncated after 22 lines. Monetary totals retain currency, mixed units disclose no FX normalization, and net flows retain signs.

The cover, artwork, navigation and historical research evidence remain unchanged. UI changes are limited to corrected metric labels, descriptive metrics and a mobile grid sizing correction discovered with an active benchmark account. Upload parsing, consent and optional local recovery remain intact. Reports contain account aggregates, not raw transfer rows, and are generated locally.

## Validation results

* TypeScript and production build: pass. Frontend lint: pass, no warnings.
* Relevant backend suite: 152 tests pass (106.13 seconds); no backend changes.
* Existing seven recovery/analysis regressions, typography integration and stability suite: pass.
* New graph/report tests: repeated transfers, reciprocal/self transfers, directed cycles, reverse orientation, threshold qualification, bounded scans, timezone ordering, label leakage and tied AP pass.
* Eleven PDF fixtures: ordinary, repeated, directed cycle, reciprocal, missing labels, mixed currency, no flags, many flags, long identifiers/filename, 25,000 transfers and the 10,000-transfer benchmark. All 46 pages rendered and visually reviewed. Searchable text, margins, footer exclusion and page numbering checked programmatically.
* Browser regression: all 70 screen/navigation/responsive/consent checks pass; 16 recovery/benchmark checks pass. Dedicated report check verifies ACC000662, 335 versus zero cycles, 19.72 versus 20.00, real PDF download and no page overflow at 1440/768/390 px. Zero dataset POSTs and critical JavaScript errors.
* Independent NetworkX cycle census and scikit-learn confusion matrix/precision/recall/F1/AP: pass. Baseline account score/flag/pattern comparison: 1,000 of 1,000 unchanged.

Rendered reports, browser evidence and machine-readable verification are saved in the task's `outputs/professional-report` directory outside the public repository. Raw benchmark CSV and generated account-level evidence are not committed.

## Scientific limits

This is deterministic heuristic prioritization, not a calibrated fraud probability or proof of wrongdoing. Transaction-count features deliberately retain established scoring semantics. The cycle census is bounded and covers length 3/4 only; reciprocal loops use their separate rule. Mixed currencies lack FX normalization. Source calendar timestamps retain original timezone representations. Uploaded origin is unverified; only the built-in demonstration is explicitly marked synthetic. Older recovered sessions disclose unavailable new metrics until reanalysis. Backend Isolation Forest inference is unverified unless a validated actual model response exists; the report's rankings remain heuristic. Synthetic label association does not establish real-world detection or causal validity.
