import {
  HealthResponse,
  TransactionUploadResponse,
  TransactionSummaryResponse,
  GraphSummaryResponse,
  NodeMetrics,
  FeatureSchemaResponse,
  UserAnalyticsResponse,
  UserFeatures,
  AnomalyTrainRequest,
  BaselineTrainRequest,
  AnomalyTrainResponse,
  UserAnomalyListResponse,
  AnomalySummaryResponse,
  ExperimentListResponse,
  ModelMetadata,
  DatasetLabelsSummaryResponse,
  SplitCreateRequest,
  SplitSummaryResponse,
  ExperimentEvaluationMetrics,
  EvaluationComparisonResponse,
  ResearchExportResponse,
  StreamStartRequest,
  StreamStateResponse,
} from "../types/api";

const BASE_URL = import.meta.env.VITE_API_URL || "";
const API_PREFIX = `${BASE_URL}/api/v1`;

class ApiError extends Error {
  status: number;
  details?: any;

  constructor(message: string, status: number, details?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_PREFIX}${path}`;
  const response = await fetch(url, options);

  if (!response.ok) {
    let errorMessage = `HTTP error ${response.status}`;
    let errorDetails: any = null;
    try {
      const errorJson = await response.json();
      errorDetails = errorJson;
      if (typeof errorJson.detail === "string") {
        errorMessage = errorJson.detail;
      } else if (Array.isArray(errorJson.detail)) {
        errorMessage = errorJson.detail.map((d: any) => d.msg || JSON.stringify(d)).join("; ");
      } else if (errorJson.message) {
        errorMessage = errorJson.message;
      }
    } catch {
      errorMessage = await response.text().catch(() => errorMessage);
    }
    throw new ApiError(errorMessage, response.status, errorDetails);
  }

  return response.json();
}

export const api = {
  // Health
  checkHealth: (): Promise<HealthResponse> =>
    request<HealthResponse>("/health"),

  // Transactions
  uploadTransactions: (
    file: File,
    strictMode = false,
    currency = "USD"
  ): Promise<TransactionUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    return request<TransactionUploadResponse>(
      `/transactions/upload?strict_mode=${strictMode}&currency=${encodeURIComponent(currency)}`,
      {
        method: "POST",
        body: formData,
      }
    );
  },

  getTransactionSummary: (datasetId: string): Promise<TransactionSummaryResponse> =>
    request<TransactionSummaryResponse>(`/transactions/${datasetId}/summary`),

  getDatasetStatus: (datasetId: string): Promise<{ dataset_id: string; status: string }> =>
    request<{ dataset_id: string; status: string }>(`/transactions/${datasetId}/status`),

  // Graph
  getGraphSummary: (datasetId: string): Promise<GraphSummaryResponse> =>
    request<GraphSummaryResponse>(`/graph/${datasetId}/summary`),

  getNodeMetrics: (datasetId: string, userId: string): Promise<NodeMetrics> =>
    request<NodeMetrics>(`/graph/${datasetId}/nodes/${encodeURIComponent(userId)}`),

  // Analytics & Features
  getFeatureSchema: (): Promise<FeatureSchemaResponse> =>
    request<FeatureSchemaResponse>("/analytics/features/schema"),

  getUserAnalytics: (
    datasetId: string,
    params: { userId?: string; limit?: number; offset?: number } = {}
  ): Promise<UserAnalyticsResponse> => {
    const q = new URLSearchParams();
    if (params.userId) q.append("user_id", params.userId);
    if (params.limit !== undefined) q.append("limit", params.limit.toString());
    if (params.offset !== undefined) q.append("offset", params.offset.toString());
    const queryStr = q.toString() ? `?${q.toString()}` : "";
    return request<UserAnalyticsResponse>(`/analytics/${datasetId}/users${queryStr}`);
  },

  getSingleUserFeatures: (datasetId: string, userId: string): Promise<UserFeatures> =>
    request<UserFeatures>(`/analytics/${datasetId}/users/${encodeURIComponent(userId)}`),

  // Anomalies
  trainAnomalyModel: (
    datasetId: string,
    payload: AnomalyTrainRequest,
    experimentLabel?: string,
    splitLabel?: string
  ): Promise<AnomalyTrainResponse> => {
    const q = new URLSearchParams();
    if (experimentLabel) q.append("experiment_label", experimentLabel);
    if (splitLabel) q.append("split_label", splitLabel);
    const queryStr = q.toString() ? `?${q.toString()}` : "";

    return request<AnomalyTrainResponse>(`/anomalies/${datasetId}/train${queryStr}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  trainBaseline: (
    datasetId: string,
    payload: BaselineTrainRequest
  ): Promise<AnomalyTrainResponse> =>
    request<AnomalyTrainResponse>(`/anomalies/${datasetId}/baseline`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  listExperiments: (datasetId: string): Promise<ExperimentListResponse> =>
    request<ExperimentListResponse>(`/anomalies/${datasetId}/experiments`),

  getUserAnomalies: (
    datasetId: string,
    params: {
      experimentLabel?: string;
      userId?: string;
      limit?: number;
      offset?: number;
      suspiciousOnly?: boolean;
      splitLabel?: string;
    } = {}
  ): Promise<UserAnomalyListResponse> => {
    const q = new URLSearchParams();
    if (params.experimentLabel) q.append("experiment_label", params.experimentLabel);
    if (params.userId) q.append("user_id", params.userId);
    if (params.limit !== undefined) q.append("limit", params.limit.toString());
    if (params.offset !== undefined) q.append("offset", params.offset.toString());
    if (params.suspiciousOnly !== undefined) q.append("suspicious_only", params.suspiciousOnly.toString());
    if (params.splitLabel) q.append("split_label", params.splitLabel);
    return request<UserAnomalyListResponse>(`/anomalies/${datasetId}/users?${q.toString()}`);
  },

  getAnomalySummary: (
    datasetId: string,
    experimentLabel = "default",
    splitLabel?: string
  ): Promise<AnomalySummaryResponse> => {
    const q = new URLSearchParams({ experiment_label: experimentLabel });
    if (splitLabel) q.append("split_label", splitLabel);
    return request<AnomalySummaryResponse>(`/anomalies/${datasetId}/summary?${q.toString()}`);
  },

  getModelMetadata: (datasetId: string, experimentLabel = "default"): Promise<ModelMetadata> =>
    request<ModelMetadata>(`/anomalies/${datasetId}/model?experiment_label=${encodeURIComponent(experimentLabel)}`),

  // Labels & Splits
  uploadLabels: (
    datasetId: string,
    file: File,
    options: { userIdCol?: string; labelCol?: string; strict?: boolean } = {}
  ): Promise<DatasetLabelsSummaryResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    const q = new URLSearchParams();
    if (options.userIdCol) q.append("user_id_col", options.userIdCol);
    if (options.labelCol) q.append("label_col", options.labelCol);
    if (options.strict !== undefined) q.append("strict", options.strict.toString());
    return request<DatasetLabelsSummaryResponse>(
      `/datasets/${datasetId}/labels?${q.toString()}`,
      {
        method: "POST",
        body: formData,
      }
    );
  },

  getLabelsSummary: (datasetId: string): Promise<DatasetLabelsSummaryResponse> =>
    request<DatasetLabelsSummaryResponse>(`/datasets/${datasetId}/labels/summary`),

  createSplit: (datasetId: string, payload: SplitCreateRequest): Promise<SplitSummaryResponse> =>
    request<SplitSummaryResponse>(`/datasets/${datasetId}/splits`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  listSplits: (datasetId: string): Promise<SplitSummaryResponse[]> =>
    request<SplitSummaryResponse[]>(`/datasets/${datasetId}/splits`),

  getSplit: (datasetId: string, splitLabel: string): Promise<SplitSummaryResponse> =>
    request<SplitSummaryResponse>(`/datasets/${datasetId}/splits/${encodeURIComponent(splitLabel)}`),

  // Evaluation
  evaluateSingleExperiment: (
    datasetId: string,
    experimentLabel: string,
    includeCurves = true,
    splitLabel?: string
  ): Promise<ExperimentEvaluationMetrics> => {
    const q = new URLSearchParams({ include_curves: includeCurves.toString() });
    if (splitLabel) q.append("split_label", splitLabel);
    return request<ExperimentEvaluationMetrics>(
      `/evaluation/${datasetId}/${encodeURIComponent(experimentLabel)}?${q.toString()}`
    );
  },

  compareExperiments: (
    datasetId: string,
    includeCurves = true,
    splitLabel?: string
  ): Promise<EvaluationComparisonResponse> => {
    const q = new URLSearchParams({ include_curves: includeCurves.toString() });
    if (splitLabel) q.append("split_label", splitLabel);
    return request<EvaluationComparisonResponse>(
      `/evaluation/${datasetId}/compare?${q.toString()}`
    );
  },

  exportResearchRun: (datasetId: string): Promise<ResearchExportResponse> =>
    request<ResearchExportResponse>(`/evaluation/${datasetId}/export`, {
      method: "POST",
    }),

  // Real-Time Streaming Simulation
  startStream: (datasetId: string, payload: StreamStartRequest): Promise<StreamStateResponse> =>
    request<StreamStateResponse>(`/stream/${datasetId}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  stopStream: (datasetId: string): Promise<StreamStateResponse> =>
    request<StreamStateResponse>(`/stream/${datasetId}/stop`, {
      method: "POST",
    }),

  getStreamState: (datasetId: string): Promise<StreamStateResponse> =>
    request<StreamStateResponse>(`/stream/${datasetId}/state`),

  // Reports & Exports
  generateReport: async (payload: {
    source: "official" | "custom";
    format: "pdf" | "docx" | "csv";
    dataset_id?: string;
    experiment_label?: string;
    split_label?: string;
  }): Promise<{ blob: Blob; filename: string }> => {
    const url = `${API_PREFIX}/reports/generate`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let msg = `HTTP error ${response.status}`;
      try {
        const errJson = await response.json();
        msg = errJson.detail || errJson.message || msg;
      } catch {
        // ignore
      }
      throw new Error(msg);
    }

    const disposition = response.headers.get("Content-Disposition");
    let filename = `graphfin_report.${payload.format}`;
    if (disposition) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    const blob = await response.blob();
    return { blob, filename };
  },
};
