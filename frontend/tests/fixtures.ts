// Deliberately synthetic test-only fixtures. Never imported by application code.
export const evidence = {
  status: "verified",
  provenance_status: "partially_verified",
  artifact_id: "synthetic",
  artifact_sha256: "a".repeat(64),
  limitations: ["Synthetic fixture; not a research result."],
};
export const metric = {
  count: 30,
  positives: 3,
  prevalence: 0.1,
  average_precision: 0.25,
  roc_auc: 0.6,
  retrieval: [
    { k: 10, effective_k: 10, positives: 2, precision: 0.2, recall: 2 / 3 },
  ],
  confidence_interval: null,
  uncertainty_note: "Fixture only",
};
export const dataset = {
  ...evidence,
  dataset_id: "ibm-5k",
  name: "IBM AML 5k",
  version: "synthetic-v1",
  dataset_type: "synthetic",
  tier: "5k",
  accounts: 100,
  transactions: 200,
  positives: 10,
  negatives: 90,
  prevalence: 0.1,
  label_definition: "fixture",
  label_sets: [
    {
      identity: "fixture-labels",
      sha256: "b".repeat(64),
      accounts: 100,
      positives: 10,
    },
  ],
  label_disagreements: null,
  transaction_sha256: "c".repeat(64),
  time_semantics: "Synthetic simulation",
};
export const paysim = {
  ...dataset,
  dataset_id: "paysim",
  name: "PaySim",
  provenance_status: "unresolved",
  positives: null,
  negatives: null,
  prevalence: null,
  label_disagreements: 1832,
  label_sets: [
    {
      identity: "paysim-research-774",
      sha256: "d".repeat(64),
      accounts: 547686,
      positives: 774,
    },
    {
      identity: "paysim-application-2606",
      sha256: "e".repeat(64),
      accounts: 547686,
      positives: 2606,
    },
  ],
};
export const experiment = {
  ...evidence,
  experiment_id: "baseline-5k-E4-s42-m42",
  dataset_id: "ibm-5k",
  tier: "5k",
  method: "E4",
  version: "fixture-v1",
  feature_names: ["in_degree"],
  split_seed: 42,
  model_seed: 42,
  population_identity: "f".repeat(64),
  dataset_sha256: "c".repeat(64),
  label_sha256: "b".repeat(64),
  train_sha256: "1".repeat(64),
  test_sha256: "2".repeat(64),
  metrics: metric,
};
export const diagnostic = {
  ...evidence,
  status: "exploratory",
  diagnostic_id: "crest-000",
  account_token: "acct_fixture",
  method: "fixture-A",
  family: "outgoing",
  available: true,
  valid: true,
  reason: null,
  baseline_score: 0.3,
  intervened_score: 0.2,
  signed_fidelity: 0.1,
  omitted_count: 1,
  omitted_fraction: 0.1,
  omitted_amount_fraction: 0.1,
};
export const page = (items: unknown[], total = items.length, number = 1) => ({
  ...evidence,
  items,
  total,
  page: number,
  page_size: 10,
});
export function response(url: URL) {
  const p = url.pathname.split("/research")[1];
  const seed = Number(url.searchParams.get("split_seed") || 42);
  const method = url.searchParams.get("method") || "E4";
  if (p === "/overview")
    return {
      ...evidence,
      provenance_status: "unresolved",
      project_title:
        "Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions",
      datasets: [dataset, paysim],
      available_methods: ["E0", "E1", "E4"],
      completed_run_count: 12,
      completed_evaluation_count: 84,
      scales: ["5k", "50k"],
      model_seed_analysis_available: true,
      crest_diagnostics_available: true,
      reproducibility_available: true,
      unavailable_components: [],
    };
  if (p === "/datasets") return page([dataset, paysim]);
  if (p.startsWith("/datasets/"))
    return p.endsWith("paysim") ? paysim : dataset;
  if (p === "/experiments") {
    const rows = url.searchParams.get("method")
      ? [42, 123, 7, 2024, 99, 555].map((s) => ({
          ...experiment,
          method,
          split_seed: s,
          experiment_id: `baseline-5k-${method}-s${s}-m42`,
        }))
      : [0, 1, 2, 3, 4, 5].map((n) => ({
          ...experiment,
          method: "E" + n,
          split_seed: seed,
          experiment_id: `baseline-5k-E${n}-s${seed}-m42`,
        }));
    return page(rows, 16, Number(url.searchParams.get("page_number") || 1));
  }
  if (p.endsWith("/rankings"))
    return page(
      [{ rank: 1, account_token: "acct_fixture", anomaly_score: 0.3 }],
      60,
      Number(url.searchParams.get("page_number") || 1),
    );
  if (p.startsWith("/experiments/"))
    return { ...experiment, experiment_id: p.split("/")[2] };
  if (p === "/comparisons")
    return {
      ...evidence,
      metric: url.searchParams.get("metric") || "average_precision",
      population_identity: "f".repeat(64),
      values: url.searchParams
        .getAll("experiment_id")
        .map((experiment_id) => ({ experiment_id, value: 0.25 })),
      interpretation: "Descriptive comparison only.",
    };
  if (p === "/model-seeds")
    return {
      ...evidence,
      runs: [13, 42, 101].map((model_seed) => ({
        dataset_id: "ibm-5k",
        tier: "5k",
        method,
        split_seed: 42,
        model_seed,
        metrics: metric,
        fit_score_seconds: 1,
      })),
      summaries: [
        {
          tier: "5k",
          method,
          mean_ap: 0.25,
          sample_sd_ap: 0,
          minimum_ap: 0.25,
          maximum_ap: 0.25,
        },
      ],
      pairs: [
        {
          tier: "5k",
          method,
          first_model_seed: 13,
          second_model_seed: 42,
          spearman_ordinal: 0.9,
          top_k: [{ k: 10, overlap: 0.8, jaccard: 0.7 }],
        },
      ],
    };
  if (p === "/reproducibility")
    return {
      ...evidence,
      replays: ["5k", "50k"].map((tier) => ({
        tier,
        byte_identical: true,
        evidence_sha256: "a".repeat(64),
        dataset_sha256: "b".repeat(64),
        feature_schema: "fixture-v1",
        model_seed: 42,
      })),
      n_estimators: 100,
      max_samples: "auto",
      contamination: 0.005,
      split_seeds: [42, 123, 7, 2024, 99, 555],
    };
  if (p === "/diagnostics")
    return { ...page([diagnostic]), status: "exploratory" };
  if (p.startsWith("/diagnostics/")) return diagnostic;
  return {
    ...evidence,
    items: [
      {
        topic: "Synthetic limitation",
        assessment: "unresolved",
        description: "Not an experimental claim.",
      },
    ],
  };
}
