// API Contract Types matching FastAPI Pydantic Models

export interface HealthResponse {
  status: string;
  service: string;
}

export interface TimeRange {
  start?: string | null;
  end?: string | null;
}

export interface TransactionSummaryResponse {
  transactions: number;
  users: number;
  total_amount: number;
  average_amount: number;
  min_amount: number;
  max_amount: number;
  time_range: TimeRange;
  currency?: string; // ISO 4217 code; defaults to "USD" if omitted
}

export interface TransactionUploadResponse {
  message: string;
  dataset_id: string;
  status: string;
  total_rows_parsed: number;
  valid_transactions: number;
  invalid_rows_count: number;
  validation_errors: string[];
  duplicate_warnings: string[];
  summary: TransactionSummaryResponse;
  currency?: string; // ISO 4217 code; defaults to "USD"
}

export interface NodeMetrics {
  user_id: string;
  in_degree: number;
  out_degree: number;
  total_degree: number;
  weighted_in_degree: number;
  weighted_out_degree: number;
  betweenness_centrality: number;
}

export interface GraphSummaryResponse {
  nodes: number;
  edges: number;
  density: number;
  is_directed: boolean;
  weakly_connected_components: number;
  strongly_connected_components: number;
  top_in_degree_nodes: NodeMetrics[];
  top_out_degree_nodes: NodeMetrics[];
}

export interface FeatureSchemaResponse {
  feature_count: number;
  features: string[];
  description: string;
}

export interface UserFeatures {
  user_id: string;
  in_degree: number;
  out_degree: number;
  total_degree: number;
  weighted_in_degree: number;
  weighted_out_degree: number;
  betweenness_centrality: number;
  transaction_count: number;
  total_sent: number;
  total_received: number;
  net_flow: number;
  average_transaction_amount: number;
  maximum_transaction_amount: number;
  unique_receivers: number;
  unique_senders: number;
  transactions_per_day: number;
  transactions_per_week: number;
  average_time_between_transactions: number;
  minimum_time_between_transactions: number;
  maximum_time_between_transactions: number;
  feature_vector?: number[] | null;
}

export interface UserAnalyticsResponse {
  total_users: number;
  limit: number;
  offset: number;
  users: UserFeatures[];
}

export interface AnomalyTrainRequest {
  experiment_label?: string;
  feature_groups?: string[];
  n_estimators?: number;
  contamination?: number;
  max_samples?: number | string;
  random_state?: number;
  split_label?: string | null;
}

export interface BaselineTrainRequest {
  experiment_label?: string;
  z_threshold?: number;
  features?: string[];
  feature_groups?: string[];
  split_label?: string | null;
}

export interface ModelMetadata {
  model_type: string;
  method: string;
  sklearn_version: string;
  dataset_id: string;
  experiment_label: string;
  split_label?: string | null;
  evaluation_mode: string;
  feature_groups: string[];
  feature_names: string[];
  feature_count: number;
  n_estimators?: number | null;
  contamination?: number | null;
  max_samples?: any;
  random_state?: number | null;
  z_threshold?: number | null;
  z_score_threshold?: number | null;
  baseline_feature_names?: string[] | null;
  entity_count: number;
  training_entity_count?: number | null;
  training_timestamp: string;
  model_artifact_path?: string | null;
  feature_stats?: Record<string, Record<string, number>>;
}

export interface AnomalyTrainResponse {
  dataset_id: string;
  message: string;
  status: string;
  model_metadata: ModelMetadata;
}

export interface UserAnomalyResult {
  user_id: string;
  raw_score: number;
  prediction: number;
  status: "suspicious" | "normal" | string;
  risk_score: number;
  reasons: string[];
}

export interface UserAnomalyListResponse {
  dataset_id: string;
  experiment_label: string;
  total_users: number;
  suspicious_count: number;
  normal_count: number;
  limit: number;
  offset: number;
  users: UserAnomalyResult[];
}

export interface AnomalySummaryResponse {
  dataset_id: string;
  experiment_label: string;
  total_entities: number;
  suspicious_count: number;
  normal_count: number;
  contamination_rate: number;
  feature_groups: string[];
  feature_count: number;
  model_metadata: ModelMetadata;
}

export interface ExperimentListResponse {
  dataset_id: string;
  total_experiments: number;
  experiments: ModelMetadata[];
}

export interface DatasetLabelsSummaryResponse {
  dataset_id: string;
  total_labels_uploaded: number;
  matched_count: number;
  unmatched_count: number;
  positive_count: number;
  negative_count: number;
  prevalence_rate: number;
  rejected_errors: string[];
}

export interface SplitCreateRequest {
  split_label?: string;
  test_size?: number;
  random_state?: number;
  stratify_by_label?: boolean;
}

export interface SplitSummaryResponse {
  dataset_id: string;
  split_label: string;
  total_users: number;
  train_count: number;
  test_count: number;
  train_positive_count: number;
  train_negative_count: number;
  test_positive_count: number;
  test_negative_count: number;
  train_prevalence: number;
  test_prevalence: number;
  overall_prevalence: number;
  stratified: boolean;
  test_size: number;
  random_state: number;
  warning?: string | null;
  created_at?: string | null;
}

export interface ConfusionMatrix {
  tp: number;
  fp: number;
  tn: number;
  fn: number;
}

export interface ROCCurveData {
  fpr: number[];
  tpr: number[];
  thresholds: number[];
}

export interface PrecisionRecallCurveData {
  precision: number[];
  recall: number[];
  thresholds: number[];
}

export interface ThresholdAnalysis {
  binary_decision_rule: string;
  continuous_score_name: string;
  score_direction: string;
  auc_evaluation_basis: string;
  risk_score_is_probability: boolean;
  risk_score_interpretation: string;
}

export interface ExperimentEvaluationMetrics {
  dataset_id: string;
  experiment_label: string;
  status: "success" | "error" | string;
  error?: string | null;
  model_type?: string | null;
  method?: string | null;
  feature_groups: string[];
  feature_names?: string[];
  feature_count?: number;
  n_estimators?: number | null;
  contamination?: number | null;
  max_samples?: any;
  random_state?: number | null;
  training_entity_count?: number | null;
  training_timestamp?: string | null;
  model_artifact_path?: string | null;
  evaluation_mode: string;
  split_label?: string | null;
  evaluation_mode_note: string;
  labeled_user_count: number;
  usable_labeled_user_count: number;
  usable_labels_count?: number;
  total_dataset_users: number;
  positive_count: number;
  negative_count: number;
  positive_prevalence: number;
  score_name: string;
  score_direction: string;
  threshold_analysis?: ThresholdAnalysis | null;
  confusion_matrix?: ConfusionMatrix | null;
  precision?: number | null;
  recall?: number | null;
  f1_score?: number | null;
  accuracy?: number | null;
  roc_auc?: number | null;
  pr_auc?: number | null;
  headline_metric: string;
  metric_warnings: string[];
  roc_curve?: ROCCurveData | null;
  precision_recall_curve?: PrecisionRecallCurveData | null;
  class_imbalance_note: string;
}

export interface EvaluationComparisonResponse {
  dataset_id: string;
  total_experiments_evaluated: number;
  successful_experiments_count: number;
  failed_experiments_count: number;
  labels_summary: DatasetLabelsSummaryResponse;
  evaluation_mode: string;
  split_label?: string | null;
  evaluation_mode_note: string;
  by_evaluation_mode?: {
    in_sample?: ExperimentEvaluationMetrics[];
    held_out?: ExperimentEvaluationMetrics[];
  };
  headline_metric: string;
  class_imbalance_note: string;
  experiments: ExperimentEvaluationMetrics[];
}

export interface ResearchExportResponse {
  dataset_id: string;
  export_timestamp: string;
  json_path: string;
  csv_path: string;
  total_experiments: number;
  successful_experiments: number;
  failed_experiments: number;
  evaluation_mode: string;
}

// Client-side representation of edge in transaction network
export interface NetworkEdge {
  source: string;
  target: string;
  amount: number;
  count: number;
}

export interface NetworkNode {
  id: string;
  degree?: number;
  in_degree?: number;
  out_degree?: number;
  betweenness?: number;
  status?: "suspicious" | "normal" | "unscored";
  risk_score?: number;
  reasons?: string[];
  // D3 force layout properties
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

// Real-Time Streaming Simulation Types
export interface StreamStartRequest {
  experiment_label: string;
  transactions_per_tick?: number;
  tick_interval_seconds?: number;
  rescoring_interval_ticks?: number;
  split_label?: string | null;
}

export interface StreamNode {
  id: string;
  degree: number;
  status: "suspicious" | "normal" | "unscored" | string;
  risk_score: number;
}

export interface StreamEdge {
  source: string;
  target: string;
  amount: number;
  transactions: number;
}

export interface StreamScoredEntity {
  user_id: string;
  raw_score: number;
  prediction: number;
  status: string;
  risk_score: number;
  reasons: string[];
}

export interface StreamScoringSummary {
  total_users: number;
  suspicious_count: number;
  normal_count: number;
  rescore_tick: number;
  users: StreamScoredEntity[];
}

export interface StreamStateResponse {
  dataset_id: string;
  status: "idle" | "running" | "stopped" | "complete" | "error";
  current_tick: number;
  transactions_revealed: number;
  total_transactions: number;
  current_entity_count: number;
  last_rescoring_tick?: number | null;
  transactions_per_tick: number;
  tick_interval_seconds: number;
  rescoring_interval_ticks: number;
  experiment_label: string;
  scoring_results?: StreamScoringSummary | null;
  newly_flagged_entities: StreamScoredEntity[];
  graph_nodes: StreamNode[];
  graph_edges: StreamEdge[];
  error?: string | null;
  message?: string | null;
}

