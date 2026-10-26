/**
 * GraphFin Dataset Analysis Types
 * Defines data structures for client-side transaction parsing, graph construction,
 * structural anomaly metrics, and interactive inspection.
 */

export interface TransactionRecord {
  transaction_id: string;
  source: string;
  destination: string;
  amount: number;
  timestamp?: string | number;
  type?: string;
  label?: number | boolean | null; // Known ground-truth fraud label if provided
  raw?: Record<string, string>;
}

export interface ColumnMapping {
  transactionIdCol: string;
  sourceCol: string;
  destinationCol: string;
  amountCol: string;
  timestampCol?: string;
  typeCol?: string;
  labelCol?: string;
}

export interface AccountNode {
  id: string;
  inDegree: number;
  outDegree: number;
  totalDegree: number;
  totalSent: number;
  totalReceived: number;
  netFlow: number;
  txCount: number;
  anomalyScore: number; // 0.00 to 1.00
  patterns: AnomalyPattern[];
  counterparties: { id: string; direction: "in" | "out"; amount: number; count: number }[];
  isLabeledFraud?: boolean;
}

export interface TransferEdge {
  source: string;
  target: string;
  amount: number;
  count: number;
  isReciprocal?: boolean;
}

export type AnomalyPattern =
  | "FAN_OUT"          // Rapid fund dispersion to multiple receivers
  | "FAN_IN"           // Fund aggregation from multiple senders into single sink
  | "CYCLE"            // Circular / reciprocal transfer flow
  | "VOLUME_OUTLIER"   // Transaction amount in extreme upper tail (>3 sigma)
  | "FLOW_IMBALANCE";  // High volume asymmetry with minimal counter-flow

export interface AnalysisSummary {
  datasetName: string;
  fileSizeBytes: number;
  totalTransactions: number;
  totalVolume: number;
  meanAmount: number;
  medianAmount: number;
  maxAmount: number;
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
  };
  evaluation?: {
    labeledTotal: number;
    positives: number;
    truePositives: number;
    falsePositives: number;
    precision: number;
    recall: number;
    f1Score: number;
  };
  processedAt: string;
}

export interface AnalysisResult {
  summary: AnalysisSummary;
  accounts: AccountNode[];
  edges: TransferEdge[];
  topAnomalies: AccountNode[];
}
