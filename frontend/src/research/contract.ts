// Generated from the pinned Phase 7 OpenAPI; response schemas only.
export type Comparison = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  metric:
    | "average_precision"
    | "roc_auc"
    | "precision_at_10"
    | "precision_at_25"
    | "precision_at_50"
    | "precision_at_100";
  population_identity: string;
  values: ComparisonValue[];
  interpretation?: string;
};
export type ComparisonValue = { experiment_id: string; value: number | null };
export type Dataset = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  dataset_id: string;
  name: string;
  version: string;
  dataset_type?: string;
  tier: string;
  accounts?: number | null;
  transactions?: number | null;
  positives?: number | null;
  negatives?: number | null;
  prevalence?: number | null;
  label_definition: string;
  label_sets?: LabelSet[];
  label_disagreements?: number | null;
  transaction_sha256?: string | null;
  time_semantics: string;
};
export type Diagnostic = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  diagnostic_id: string;
  account_token: string;
  method: string;
  family?: string | null;
  available: boolean;
  valid?: boolean | null;
  reason?: string | null;
  baseline_score: number | null;
  intervened_score?: number | null;
  signed_fidelity?: number | null;
  omitted_count?: number | null;
  omitted_fraction?: number | null;
  omitted_amount_fraction?: number | null;
};
export type Experiment = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  experiment_id: string;
  dataset_id: string;
  tier: string;
  method: string;
  version: string;
  feature_names?: string[];
  split_seed?: number | null;
  model_seed?: number | null;
  population_identity?: string | null;
  dataset_sha256?: string | null;
  label_sha256?: string | null;
  train_sha256?: string | null;
  test_sha256?: string | null;
  metrics?: Metrics | null;
};
export type LabelSet = {
  identity: string;
  sha256: string;
  accounts: number;
  positives: number;
};
export type Limitation = {
  topic: string;
  assessment: string;
  description: string;
};
export type Limitations = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  items: Limitation[];
};
export type Metrics = {
  count?: number | null;
  positives?: number | null;
  prevalence?: number | null;
  average_precision?: number | null;
  roc_auc?: number | null;
  retrieval?: Retrieval[];
  confidence_interval?: unknown[] | null;
  uncertainty_note?: string;
};
export type ModelSeeds = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  runs: SeedRun[];
  summaries: SeedSummary[];
  pairs: SeedPair[];
};
export type Overlap = {
  k: number;
  overlap: number | null;
  jaccard: number | null;
};
export type Overview = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  project_title: string;
  datasets: Dataset[];
  available_methods: string[];
  completed_run_count: number;
  completed_evaluation_count: number;
  scales: string[];
  model_seed_analysis_available: boolean;
  crest_diagnostics_available: boolean;
  reproducibility_available: boolean;
  unavailable_components: string[];
};
export type Page_Dataset_ = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  items: Dataset[];
  total: number;
  page: number;
  page_size: number;
};
export type Page_Diagnostic_ = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  items: Diagnostic[];
  total: number;
  page: number;
  page_size: number;
};
export type Page_Experiment_ = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  items: Experiment[];
  total: number;
  page: number;
  page_size: number;
};
export type Page_Ranking_ = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  items: Ranking[];
  total: number;
  page: number;
  page_size: number;
};
export type Ranking = {
  rank: number;
  account_token: string;
  anomaly_score: number | null;
};
export type Replay = {
  tier: string;
  byte_identical: boolean;
  evidence_sha256: string;
  dataset_sha256: string;
  feature_schema: string;
  model_seed?: number;
};
export type Reproducibility = {
  status:
    "verified" | "historical" | "exploratory" | "incomplete" | "unavailable";
  provenance_status: "verified" | "partially_verified" | "unresolved";
  artifact_id?: string | null;
  artifact_sha256?: string | null;
  limitations?: string[];
  replays: Replay[];
  n_estimators: number;
  max_samples: string;
  contamination: number;
  split_seeds: number[];
};
export type Retrieval = {
  k: number;
  effective_k: number;
  positives: number;
  precision: number | null;
  recall: number | null;
};
export type SeedPair = {
  tier: string;
  method: string;
  first_model_seed: number;
  second_model_seed: number;
  spearman_ordinal: number | null;
  top_k: Overlap[];
};
export type SeedRun = {
  dataset_id: string;
  tier: string;
  method: string;
  split_seed: number;
  model_seed: number;
  metrics: Metrics;
  fit_score_seconds: number | null;
};
export type SeedSummary = {
  tier: string;
  method: string;
  mean_ap: number | null;
  sample_sd_ap: number | null;
  minimum_ap: number | null;
  maximum_ap: number | null;
};
