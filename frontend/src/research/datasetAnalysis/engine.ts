/**
 * GraphFin Client-Side Graph Analysis & Anomaly Detection Engine
 * Constructs directed weighted transaction graphs, extracts structural metrics,
 * detects topological anomaly patterns, and computes deterministic anomaly scores.
 */
import type {
  AccountNode,
  AnalysisResult,
  AnalysisSummary,
  AnomalyPattern,
  TransactionRecord,
  TransferEdge,
} from "./types";

export function analyzeTransactionGraph(
  records: TransactionRecord[],
  datasetName = "uploaded_dataset.csv",
  fileSizeBytes = 0,
): AnalysisResult {
  if (records.length === 0) {
    throw new Error("Cannot analyze an empty transaction set.");
  }

  // 1. Accumulate Basic Transaction Metrics
  let totalVolume = 0;
  const amounts = records.map((r) => {
    totalVolume += r.amount;
    return r.amount;
  });

  amounts.sort((a, b) => a - b);
  const meanAmount = totalVolume / records.length;
  const medianAmount =
    amounts.length % 2 === 0
      ? (amounts[amounts.length / 2 - 1] + amounts[amounts.length / 2]) / 2
      : amounts[Math.floor(amounts.length / 2)];
  const maxAmount = amounts[amounts.length - 1];

  // Variance & Standard Deviation
  const variance =
    amounts.reduce((sum, val) => sum + Math.pow(val - meanAmount, 2), 0) /
    amounts.length;
  const stdDev = Math.sqrt(variance);
  const volumeThreshold = meanAmount + 2.5 * stdDev;

  // 2. Build Graph Structure
  const nodeMap = new Map<
    string,
    {
      inDegree: number;
      outDegree: number;
      totalSent: number;
      totalReceived: number;
      txCount: number;
      counterparties: Map<string, { direction: "in" | "out"; amount: number; count: number }>;
      isLabeledFraud: boolean;
    }
  >();

  const getOrCreateNode = (id: string) => {
    let node = nodeMap.get(id);
    if (!node) {
      node = {
        inDegree: 0,
        outDegree: 0,
        totalSent: 0,
        totalReceived: 0,
        txCount: 0,
        counterparties: new Map(),
        isLabeledFraud: false,
      };
      nodeMap.set(id, node);
    }
    return node;
  };

  const edgeMap = new Map<string, TransferEdge>();

  for (const tx of records) {
    const srcNode = getOrCreateNode(tx.source);
    const dstNode = getOrCreateNode(tx.destination);

    srcNode.outDegree++;
    srcNode.totalSent += tx.amount;
    srcNode.txCount++;

    dstNode.inDegree++;
    dstNode.totalReceived += tx.amount;
    dstNode.txCount++;

    if (tx.label === 1 || tx.label === true) {
      srcNode.isLabeledFraud = true;
      dstNode.isLabeledFraud = true;
    }

    // Counterparty tracking
    const srcCp = srcNode.counterparties.get(tx.destination) || {
      direction: "out" as const,
      amount: 0,
      count: 0,
    };
    srcCp.amount += tx.amount;
    srcCp.count++;
    srcNode.counterparties.set(tx.destination, srcCp);

    const dstCp = dstNode.counterparties.get(tx.source) || {
      direction: "in" as const,
      amount: 0,
      count: 0,
    };
    dstCp.amount += tx.amount;
    dstCp.count++;
    dstNode.counterparties.set(tx.source, dstCp);

    // Edge accumulation
    const edgeKey = `${tx.source}->${tx.destination}`;
    const edge = edgeMap.get(edgeKey);
    if (edge) {
      edge.amount += tx.amount;
      edge.count++;
    } else {
      edgeMap.set(edgeKey, {
        source: tx.source,
        target: tx.destination,
        amount: tx.amount,
        count: 1,
      });
    }
  }

  // 3. Mark Reciprocal Edges (Direct 2-Cycles)
  for (const [key, edge] of edgeMap.entries()) {
    const reverseKey = `${edge.target}->${edge.source}`;
    if (edgeMap.has(reverseKey)) {
      edge.isReciprocal = true;
    }
  }

  // 4. Detect Structural Patterns and Compute Anomaly Scores
  const totalAccounts = nodeMap.size;
  let sourceOnlyCount = 0;
  let sinkOnlyCount = 0;
  let intermediaryCount = 0;
  let maxInDeg = 0;
  let maxOutDeg = 0;
  let totalDegSum = 0;

  let fanOutTotal = 0;
  let fanInTotal = 0;
  let cycleTotal = 0;
  let volumeOutlierTotal = 0;

  const accounts: AccountNode[] = [];

  for (const [id, raw] of nodeMap.entries()) {
    const inDeg = raw.inDegree;
    const outDeg = raw.outDegree;
    const totDeg = inDeg + outDeg;

    totalDegSum += totDeg;
    if (inDeg > maxInDeg) maxInDeg = inDeg;
    if (outDeg > maxOutDeg) maxOutDeg = outDeg;

    if (inDeg === 0 && outDeg > 0) sourceOnlyCount++;
    else if (outDeg === 0 && inDeg > 0) sinkOnlyCount++;
    else if (inDeg > 0 && outDeg > 0) intermediaryCount++;

    const patterns: AnomalyPattern[] = [];

    // Pattern 1: Fan-Out (Dispersal / Smurfing)
    if (outDeg >= 3 && outDeg >= (inDeg === 0 ? 3 : inDeg * 2.5)) {
      patterns.push("FAN_OUT");
      fanOutTotal++;
    }

    // Pattern 2: Fan-In (Aggregation / Mule Collection)
    if (inDeg >= 3 && inDeg >= (outDeg === 0 ? 3 : outDeg * 2.5)) {
      patterns.push("FAN_IN");
      fanInTotal++;
    }

    // Pattern 3: Circular / Reciprocal Flow (2-hop or 3-hop directed cycles)
    let hasCycle = false;
    for (const [cpId, cp] of raw.counterparties.entries()) {
      if (cp.direction === "out") {
        // Direct reciprocal flow u -> v and v -> u
        if (edgeMap.has(`${cpId}->${id}`)) {
          hasCycle = true;
          break;
        }
        // 3-hop circular ring u -> v -> w -> u
        const vNode = nodeMap.get(cpId);
        if (vNode) {
          for (const [wId, wCp] of vNode.counterparties.entries()) {
            if (wCp.direction === "out" && wId !== id) {
              if (edgeMap.has(`${wId}->${id}`)) {
                hasCycle = true;
                break;
              }
            }
          }
        }
        if (hasCycle) break;
      }
    }
    if (hasCycle) {
      patterns.push("CYCLE");
      cycleTotal++;
    }

    // Pattern 4: Volume Outlier
    if (raw.totalSent > volumeThreshold || raw.totalReceived > volumeThreshold) {
      patterns.push("VOLUME_OUTLIER");
      volumeOutlierTotal++;
    }

    // Pattern 5: Flow Imbalance
    const totalVolumeNode = raw.totalSent + raw.totalReceived;
    const flowDiff = Math.abs(raw.totalReceived - raw.totalSent);
    if (totalVolumeNode > meanAmount && flowDiff / totalVolumeNode > 0.9) {
      patterns.push("FLOW_IMBALANCE");
    }

    // 5. Composite Normalized Graph Anomaly Score (0.00 to 1.00)
    // Degree extremity (30%) + Flow asymmetry (25%) + Pattern boost (25%) + Volume weight (20%)
    const degreeComponent = Math.min(1.0, totDeg / Math.max(10, Math.sqrt(totalAccounts)));
    const asymmetryComponent = totalVolumeNode > 0 ? flowDiff / totalVolumeNode : 0;
    const patternComponent = Math.min(1.0, patterns.length * 0.35);
    const volumeComponent = Math.min(1.0, totalVolumeNode / Math.max(1, meanAmount * 3));

    const rawScore =
      0.30 * degreeComponent +
      0.25 * asymmetryComponent +
      0.25 * patternComponent +
      0.20 * volumeComponent;

    const anomalyScore = Math.min(1.0, Math.max(0.01, parseFloat(rawScore.toFixed(3))));

    const counterpartiesList = Array.from(raw.counterparties.entries())
      .map(([cpId, cp]) => ({ id: cpId, ...cp }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 10);

    accounts.push({
      id,
      inDegree: inDeg,
      outDegree: outDeg,
      totalDegree: totDeg,
      totalSent: Math.round(raw.totalSent * 100) / 100,
      totalReceived: Math.round(raw.totalReceived * 100) / 100,
      netFlow: Math.round((raw.totalReceived - raw.totalSent) * 100) / 100,
      txCount: raw.txCount,
      anomalyScore,
      patterns,
      counterparties: counterpartiesList,
      isLabeledFraud: raw.isLabeledFraud,
    });
  }

  // Sort accounts by anomaly score descending
  accounts.sort((a, b) => b.anomalyScore - a.anomalyScore);

  const topAnomalies = accounts.filter((a) => a.anomalyScore >= 0.45 || a.patterns.length > 0);
  const suspiciousCount = topAnomalies.length;

  // 6. Network density: E / (V * (V - 1))
  const density =
    totalAccounts > 1
      ? edgeMap.size / (totalAccounts * (totalAccounts - 1))
      : 0;

  // 7. Ground-Truth Validation Evaluation (if labels exist in input)
  let evaluation: AnalysisSummary["evaluation"] = undefined;
  const labeledNodes = accounts.filter((a) => a.isLabeledFraud !== undefined);
  const positiveLabels = accounts.filter((a) => a.isLabeledFraud === true);

  if (positiveLabels.length > 0) {
    const topK = Math.max(5, positiveLabels.length * 2);
    const predictedPositive = accounts.slice(0, topK);
    const truePositives = predictedPositive.filter((a) => a.isLabeledFraud).length;
    const falsePositives = predictedPositive.length - truePositives;
    const precision = truePositives / predictedPositive.length;
    const recall = truePositives / positiveLabels.length;
    const f1Score =
      precision + recall > 0
        ? (2 * (precision * recall)) / (precision + recall)
        : 0;

    evaluation = {
      labeledTotal: labeledNodes.length,
      positives: positiveLabels.length,
      truePositives,
      falsePositives,
      precision: parseFloat(precision.toFixed(4)),
      recall: parseFloat(recall.toFixed(4)),
      f1Score: parseFloat(f1Score.toFixed(4)),
    };
  }

  const summary: AnalysisSummary = {
    datasetName,
    fileSizeBytes,
    totalTransactions: records.length,
    totalVolume: Math.round(totalVolume * 100) / 100,
    meanAmount: Math.round(meanAmount * 100) / 100,
    medianAmount: Math.round(medianAmount * 100) / 100,
    maxAmount: Math.round(maxAmount * 100) / 100,
    uniqueAccounts: totalAccounts,
    uniqueEdges: edgeMap.size,
    sourceOnlyAccounts: sourceOnlyCount,
    sinkOnlyAccounts: sinkOnlyCount,
    intermediaryAccounts: intermediaryCount,
    networkDensity: parseFloat(density.toFixed(6)),
    maxInDegree: maxInDeg,
    maxOutDegree: maxOutDeg,
    avgDegree: parseFloat((totalDegSum / Math.max(1, totalAccounts)).toFixed(2)),
    suspiciousAccountCount: suspiciousCount,
    patternsDetected: {
      fanOutCount: fanOutTotal,
      fanInCount: fanInTotal,
      cycleCount: cycleTotal,
      volumeOutlierCount: volumeOutlierTotal,
    },
    evaluation,
    processedAt: new Date().toISOString(),
  };

  return {
    summary,
    accounts,
    edges: Array.from(edgeMap.values()),
    topAnomalies,
  };
}
