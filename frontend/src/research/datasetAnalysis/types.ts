import type { CycleDiagnostics } from "./networkMetrics";
/**
 * GraphFin Dataset Analysis Types
 * Defines data structures for client-side transaction parsing, graph construction,
 * statistically defensible anomaly metrics, and interactive inspection.
 */

export interface TransactionRecord {
  transaction_id: string;
  source: string;
  destination: string;
  amount: number;
  timestamp?: string | number;
  type?: string;
  currency?: string;
  label?: number | boolean | null; // Known ground-truth fraud label if provided
  pattern_type?: string;
  raw?: Record<string, string>;
}

export interface ColumnMapping {
  transactionIdCol: string;
  sourceCol: string;
  destinationCol: string;
  amountCol: string;
  timestampCol?: string;
  typeCol?: string;
  currencyCol?: string;
  labelCol?: string;
  patternTypeCol?: string;
}

export interface AccountCounterparty {
  id: string;
  amount?: number;
  count?: number;
  inCount?: number;
  inAmount?: number;
  outCount?: number;
  outAmount?: number;
  totalAmount?: number;
  direction: "in" | "out" | "both";
}

export interface AccountNode {
  incomingTransactionCount?: number;
  outgoingTransactionCount?: number;
  uniqueInDegree?: number;
  uniqueOutDegree?: number;
  uniqueCounterpartyCount?: number;
  id: string;
  inDegree: number;
  outDegree: number;
  totalDegree: number;
  totalSent: number;
  totalReceived: number;
  netFlow: number;
  txCount: number;
  anomalyScore: number; // 0.00 to 1.00 (composite continuous score)
  heuristicScore?: number;
  mlScore?: number;
  mlRawScore?: number;
  mlRiskScore?: number;
  mlStatus?: string;
  isFlaggedForReview?: boolean; // Statistically defensible classification
  patterns: AnomalyPattern[];
  counterparties: AccountCounterparty[];
  volumeZScore?: number;
  degreeZScore?: number;
  isLabeledFraud?: boolean; // Ground-truth flag from synthetic injection
  syntheticPatternType?: string;
}

export interface TransferEdge {
  source: string;
  target: string;
  amount: number;
  count: number;
  isReciprocal?: boolean;
}

export type AnomalyPattern =
  | "FAN_OUT"          // Dispersal hub (out-degree >= threshold & >= 2.5x in-degree)
  | "FAN_IN"           // Aggregation hub (in-degree >= threshold & >= 2.5x out-degree)
  | "CYCLE"            // Noteworthy multi-hop loop or high-frequency reciprocal round-tripping
  | "VOLUME_OUTLIER"   // Account-level volume in upper tail (>= 2.5 sigma from account distribution)
  | "FLOW_IMBALANCE";  // Extreme volume asymmetry on active account with minimal return flow

export interface ThresholdConfig {
  volumeZThreshold: number;         // e.g. 2.5 standard deviations above account volume mean
  degreeZThreshold: number;         // e.g. 2.5 standard deviations above account degree mean
  fanOutRatio: number;              // e.g. 2.5 (outDegree / max(1, inDegree))
  fanInRatio: number;               // e.g. 2.5 (inDegree / max(1, outDegree))
  suspiciousScoreThreshold: number; // e.g. 0.60
  version: string;                  // e.g. "GraphFin-Analytical-v2.1"
}

export interface GroundTruthEvaluation {
  labeledTotal: number;
  positives: number;
  negatives: number;
  truePositives: number;
  falsePositives: number;
  falseNegatives: number;
  trueNegatives: number;
  precision: number;
  recall: number;
  f1Score: number;
  prAuc?: number;
  aggregationRule: string;
  disclaimer: string;
}

export interface AnalysisSummary {
  datasetOrigin?: 'synthetic' | 'uploaded';
  timestampCoverage?: { present: number; parseable: number; earliest?: string; latest?: string };
  averageIncomingTransactions?: number;
  averageOutgoingTransactions?: number;
  averageTransactionIncidences?: number;
  averageUniqueTotalDegree?: number;
  maxUniqueInDegree?: number;
  maxUniqueOutDegree?: number;
  simpleDirectedEdges?: number;
  selfTransferTransactions?: number;
  selfLoopEdges?: number;
  repeatedDirectedPairs?: number;
  extraRepeatedTransactions?: number;
  cycleDiagnostics?: CycleDiagnostics;
  transactionLabels?: { normal: number; anomalous: number; unknown: number };
  sourceRecords?: number;
  inputChecksum?: string;
  sourceColumns?: string[];
  columnMapping?: ColumnMapping;
  datasetName: string;
  fileSizeBytes: number;
  totalTransactions: number;
  totalVolume: number;
  currency?: string;               // Detected dataset currency ("INR", "USD", etc.)
  isMixedCurrency?: boolean;
  currencyBreakdown?: Record<string, number>;
  meanAmount: number;
  medianAmount: number;
  maxAmount: number;
  accountVolumeMean?: number;
  accountVolumeStdDev?: number;
  accountVolumeThreshold?: number;
  uniqueAccounts: number;
  uniqueEdges: number;
  sourceOnlyAccounts: number;
  sinkOnlyAccounts: number;
  intermediaryAccounts: number;
  networkDensity: number;
  maxInDegree: number;
  maxOutDegree: number;
  avgDegree: number;
  suspiciousAccountCount: number;
  patternsDetected: {
    fanOutCount: number;
    fanInCount: number;
    cycleCount: number;
    volumeOutlierCount: number;
    flowImbalanceCount?: number;
  };
  thresholdConfig?: ThresholdConfig;
  analysisEngine?: string;
  algorithmVersion?: string;
  totalRowsAccepted?: number;
  totalRowsRejected?: number;
  dataCompletenessPct?: number;
  backendDatasetId?: string;
  backendStatus?: BackendMLStatus;
  backendModel?: string;
  backendError?: string;
  rawCsvContent?: string;
  evaluation?: GroundTruthEvaluation;
  processedAt: string;
}

export type BackendMLStatus =
  | "client_completed"
  | "ml_pending"
  | "ml_verified"
  | "ml_unavailable"
  | "ml_failed"
  | "idle"
  | "syncing"
  | "synced";

export interface AnalysisResult {
  datasetPreview?: { headers: string[]; rows: string[][] };
  summary: AnalysisSummary;
  accounts: AccountNode[];
  edges: TransferEdge[];
  topAnomalies: AccountNode[];
  backendDatasetId?: string;
  backendStatus?: BackendMLStatus;
  backendModel?: string;
}
