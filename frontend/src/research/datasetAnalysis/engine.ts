/**
 * GraphFin Client-Side Graph Analysis & Anomaly Detection Engine
 * Constructs directed weighted transaction graphs, extracts structural metrics,
 * detects topological anomaly patterns, and computes deterministic, statistically
 * defensible anomaly scores with explainable indicators.
 */
import type {
  AccountCounterparty,
  AccountNode,
  AnalysisResult,
  AnalysisSummary,
  AnomalyPattern,
  GroundTruthEvaluation,
  ThresholdConfig,
  TransactionRecord,
  TransferEdge,
} from "./types";

export const DEFAULT_THRESHOLDS: ThresholdConfig = {
  volumeZThreshold: 2.5,
  degreeZThreshold: 2.5,
  fanOutRatio: 2.5,
  fanInRatio: 2.5,
  suspiciousScoreThreshold: 0.60,
  version: "GraphFin-Analytical-v2.1",
};

export function analyzeTransactionGraph(
  records: TransactionRecord[],
  datasetName = "uploaded_dataset.csv",
  fileSizeBytes = 0,
  customThresholds?: Partial<ThresholdConfig>,
  totalRawRows?: number,
  rejectedRowsCount = 0,
): AnalysisResult {
  if (records.length === 0) {
    throw new Error("Cannot analyze an empty transaction set.");
  }

  const thresholds: ThresholdConfig = {
    ...DEFAULT_THRESHOLDS,
    ...customThresholds,
  };

  // 1. Currency Detection
  const currencyCounts = new Map<string, number>();
  for (const r of records) {
    if (r.currency) {
      currencyCounts.set(r.currency, (currencyCounts.get(r.currency) || 0) + 1);
    }
  }

  let dominantCurrency = "Unknown";
  let isMixedCurrency = false;
  const currencyBreakdown: Record<string, number> = {};

  if (currencyCounts.size > 0) {
    let maxCount = -1;
    currencyCounts.forEach((count, ccy) => {
      currencyBreakdown[ccy] = count;
      if (count > maxCount) {
        maxCount = count;
        dominantCurrency = ccy;
      }
    });
    if (currencyCounts.size > 1) {
      isMixedCurrency = true;
    }
  }

  // 2. Transaction-Level Volume Distribution
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

  // 3. Build Node & Directed Edge Graph
  interface RawNodeData {
    inDegree: number;
    outDegree: number;
    totalSent: number;
    totalReceived: number;
    txCount: number;
    counterparties: Map<
      string,
      { inCount: number; inAmount: number; outCount: number; outAmount: number }
    >;
    isLabeledFraud: boolean;
    patternType?: string;
  }

  const nodeMap = new Map<string, RawNodeData>();

  const getOrCreateNode = (id: string): RawNodeData => {
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

    // Ground truth label handling (synthetic test convention: account participated in >= 1 labeled anomaly transaction)
    if (tx.label === 1 || tx.label === true) {
      srcNode.isLabeledFraud = true;
      dstNode.isLabeledFraud = true;
    }
    if (tx.pattern_type && tx.pattern_type !== "normal") {
      srcNode.patternType = tx.pattern_type;
      dstNode.patternType = tx.pattern_type;
    }

    // Bidirectional counterparty tracking on Source
    let srcCp = srcNode.counterparties.get(tx.destination);
    if (!srcCp) {
      srcCp = { inCount: 0, inAmount: 0, outCount: 0, outAmount: 0 };
      srcNode.counterparties.set(tx.destination, srcCp);
    }
    srcCp.outCount++;
    srcCp.outAmount += tx.amount;

    // Bidirectional counterparty tracking on Destination
    let dstCp = dstNode.counterparties.get(tx.source);
    if (!dstCp) {
      dstCp = { inCount: 0, inAmount: 0, outCount: 0, outAmount: 0 };
      dstNode.counterparties.set(tx.source, dstCp);
    }
    dstCp.inCount++;
    dstCp.inAmount += tx.amount;

    // Directed Edge accumulation
    const edgeKey = JSON.stringify([tx.source, tx.destination]);
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

  // 4. Mark Reciprocal Edges (direct bilateral exchange u <-> v)
  for (const [, edge] of edgeMap.entries()) {
    const reverseKey = JSON.stringify([edge.target, edge.source]);
    if (edge.source !== edge.target && edgeMap.has(reverseKey)) {
      edge.isReciprocal = true;
    }
  }

  // 5. Account-Level Distribution Analysis (Compare Comparable Quantities)
  const totalAccounts = nodeMap.size;
  let sumAccountVolumes = 0;
  let sumTotalDegrees = 0;
  let sumOutDegrees = 0;
  let sumInDegrees = 0;

  const accountVolumes: number[] = [];

  for (const [, raw] of nodeMap.entries()) {
    const totVol = raw.totalSent + raw.totalReceived;
    accountVolumes.push(totVol);
    sumAccountVolumes += totVol;

    sumTotalDegrees += (raw.inDegree + raw.outDegree);
    sumOutDegrees += raw.outDegree;
    sumInDegrees += raw.inDegree;
  }

  accountVolumes.sort((a, b) => a - b);
  const accountVolumeMean = sumAccountVolumes / Math.max(1, totalAccounts);
  const medianAccountVolume =
    accountVolumes.length % 2 === 0
      ? (accountVolumes[accountVolumes.length / 2 - 1] + accountVolumes[accountVolumes.length / 2]) / 2
      : accountVolumes[Math.floor(accountVolumes.length / 2)];

  // Account volume standard deviation
  let accVolVariance = 0;
  for (const vol of accountVolumes) {
    accVolVariance += Math.pow(vol - accountVolumeMean, 2);
  }
  const accountVolumeStdDev = Math.sqrt(accVolVariance / Math.max(1, totalAccounts));

  // Account-level volume outlier threshold (statistically defensible mean + 2.5 std)
  const accountVolumeThreshold = accountVolumeMean + thresholds.volumeZThreshold * accountVolumeStdDev;

  // Degree distributions
  const avgDegree = sumTotalDegrees / Math.max(1, totalAccounts);
  const meanOutDegree = sumOutDegrees / Math.max(1, totalAccounts);
  const meanInDegree = sumInDegrees / Math.max(1, totalAccounts);

  let degVariance = 0;
  let outVariance = 0;
  let inVariance = 0;

  for (const [, raw] of nodeMap.entries()) {
    degVariance += Math.pow((raw.inDegree + raw.outDegree) - avgDegree, 2);
    outVariance += Math.pow(raw.outDegree - meanOutDegree, 2);
    inVariance += Math.pow(raw.inDegree - meanInDegree, 2);
  }

  const degStdDev = Math.sqrt(degVariance / Math.max(1, totalAccounts));
  const outDegStdDev = Math.sqrt(outVariance / Math.max(1, totalAccounts));
  const inDegStdDev = Math.sqrt(inVariance / Math.max(1, totalAccounts));

  const outDegreeThreshold = meanOutDegree + thresholds.degreeZThreshold * Math.max(1, outDegStdDev);
  const inDegreeThreshold = meanInDegree + thresholds.degreeZThreshold * Math.max(1, inDegStdDev);

  // 6. Detect Structural Patterns & Calculate Continuous Anomaly Scores
  let sourceOnlyCount = 0;
  let sinkOnlyCount = 0;
  let intermediaryCount = 0;
  let maxInDeg = 0;
  let maxOutDeg = 0;

  let fanOutTotal = 0;
  let fanInTotal = 0;
  let cycleTotal = 0;
  let volumeOutlierTotal = 0;
  let flowImbalanceTotal = 0;

  const accounts: AccountNode[] = [];

  for (const [id, raw] of nodeMap.entries()) {
    const inDeg = raw.inDegree;
    const outDeg = raw.outDegree;
    const totDeg = inDeg + outDeg;
    const totalNodeVolume = raw.totalSent + raw.totalReceived;
    const netFlow = raw.totalReceived - raw.totalSent;

    if (inDeg > maxInDeg) maxInDeg = inDeg;
    if (outDeg > maxOutDeg) maxOutDeg = outDeg;

    if (inDeg === 0 && outDeg > 0) sourceOnlyCount++;
    else if (outDeg === 0 && inDeg > 0) sinkOnlyCount++;
    else if (inDeg > 0 && outDeg > 0) intermediaryCount++;

    const patterns: AnomalyPattern[] = [];

    // Pattern 1: Account-Level Volume Outlier (Statistically defensible Z >= 2.5)
    const volumeZScore =
      accountVolumeStdDev > 0
        ? (totalNodeVolume - accountVolumeMean) / accountVolumeStdDev
        : 0;

    if (totalNodeVolume > accountVolumeThreshold) {
      patterns.push("VOLUME_OUTLIER");
      volumeOutlierTotal++;
    }

    // Pattern 2: Fan-Out Dispersal Hub (High out-degree vs network distribution & strong out/in ratio)
    if (
      outDeg > outDegreeThreshold &&
      outDeg >= thresholds.fanOutRatio * Math.max(1, inDeg)
    ) {
      patterns.push("FAN_OUT");
      fanOutTotal++;
    }

    // Pattern 3: Fan-In Aggregation Hub (High in-degree vs network distribution & strong in/out ratio)
    if (
      inDeg > inDegreeThreshold &&
      inDeg >= thresholds.fanInRatio * Math.max(1, outDeg)
    ) {
      patterns.push("FAN_IN");
      fanInTotal++;
    }

    // Pattern 4: Flow Imbalance (Extreme asymmetry on active account)
    if (
      totalNodeVolume > medianAccountVolume &&
      Math.abs(netFlow) / totalNodeVolume > 0.85
    ) {
      patterns.push("FLOW_IMBALANCE");
      flowImbalanceTotal++;
    }

    // Pattern 5: Noteworthy Cycle (Clearly distinguishes ordinary bilateral trade from laundering loops)
    // A. High-intensity reciprocal round-tripping (>= 5 transfers back and forth, or heavy reciprocal volume)
    // B. Directed multi-hop circular forwarding loop (3-hop u -> v -> w -> u or 4-hop u -> v -> w -> x -> u)
    let hasNoteworthyCycle = false;
    for (const [cpId, cp] of raw.counterparties.entries()) {
      if (cpId === id) continue;
      if (cp.outCount >= 5 && cp.inCount >= 5) {
        hasNoteworthyCycle = true;
        break;
      }
      if (cp.outCount > 0) {
        const vNode = nodeMap.get(cpId);
        if (vNode) {
          for (const [wId, wCp] of vNode.counterparties.entries()) {
            if (wId !== id && wId !== cpId && wCp.outCount > 0) {
              const wNode = nodeMap.get(wId);
              if (wNode) {
                // 3-hop check: u -> v -> w -> u
                const wToU = wNode.counterparties.get(id);
                if (wToU && wToU.outCount > 0) {
                  const loopMinVol = Math.min(cp.outAmount, wCp.outAmount, wToU.outAmount);
                  if (loopMinVol > accountVolumeMean * 0.15 || accountVolumeMean === 0) {
                    hasNoteworthyCycle = true;
                    break;
                  }
                }

                // 4-hop check: u -> v -> w -> x -> u
                for (const [xId, xCp] of wNode.counterparties.entries()) {
                  if (xId !== id && xId !== cpId && xId !== wId && xCp.outCount > 0) {
                    const xNode = nodeMap.get(xId);
                    if (xNode) {
                      const xToU = xNode.counterparties.get(id);
                      if (xToU && xToU.outCount > 0) {
                        const loop4Vol = Math.min(cp.outAmount, wCp.outAmount, xCp.outAmount, xToU.outAmount);
                        if (loop4Vol > accountVolumeMean * 0.15 || accountVolumeMean === 0) {
                          hasNoteworthyCycle = true;
                          break;
                        }
                      }
                    }
                  }
                }
                if (hasNoteworthyCycle) break;
              }
            }
          }
        }
      }
      if (hasNoteworthyCycle) break;
    }

    if (hasNoteworthyCycle) {
      patterns.push("CYCLE");
      cycleTotal++;
    }

    // Normalized Continuous Score Components (0.00 to 1.00)
    const degreeZScore =
      degStdDev > 0 ? (totDeg - avgDegree) / degStdDev : 0;

    // Component 1: Volume extremity (bounded Z-score)
    const cVolume = Math.min(1.0, Math.max(0.0, volumeZScore / 3.5));

    // Component 2: Degree extremity (bounded Z-score)
    const cDegree = Math.min(1.0, Math.max(0.0, degreeZScore / 3.5));

    // Component 3: Flow asymmetry (moderated by account volume relative to mean)
    const degAsym = totDeg > 0 ? Math.abs(outDeg - inDeg) / totDeg : 0;
    const volAsym = totalNodeVolume > 0 ? Math.abs(netFlow) / totalNodeVolume : 0;
    const cAsymmetry =
      (degAsym * 0.5 + volAsym * 0.5) * Math.min(1.0, totalNodeVolume / accountVolumeMean);

    // Component 4: Structural Motifs (0.25 per noteworthy pattern, max 1.0)
    const cPatterns = Math.min(1.0, patterns.length * 0.25);

    // Composite Weighted Score
    const rawScore =
      0.30 * cVolume +
      0.25 * cDegree +
      0.20 * cAsymmetry +
      0.25 * cPatterns;

    const anomalyScore = Math.min(
      1.0,
      Math.max(0.01, parseFloat(rawScore.toFixed(4))),
    );

    // Flagged for Forensic Review:
    // Statistically defensible: high composite score (>= 0.60) OR compounding patterns (>= 2) with elevated score (>= 0.40) OR extreme volume outlier (Z >= 3.0)
    const isFlaggedForReview =
      anomalyScore >= thresholds.suspiciousScoreThreshold ||
      (patterns.length >= 2 && anomalyScore >= 0.40) ||
      volumeZScore >= 3.0;

    // Build counterparties list with bidirectional fields
    const counterpartiesList: AccountCounterparty[] = Array.from(
      raw.counterparties.entries(),
    )
      .map(([cpId, cp]) => {
        let direction: "in" | "out" | "both" = "out";
        if (cp.inCount > 0 && cp.outCount > 0) direction = "both";
        else if (cp.inCount > 0) direction = "in";
        return {
          id: cpId,
          inCount: cp.inCount,
          inAmount: Math.round(cp.inAmount * 100) / 100,
          outCount: cp.outCount,
          outAmount: Math.round(cp.outAmount * 100) / 100,
          totalAmount: Math.round((cp.inAmount + cp.outAmount) * 100) / 100,
          direction,
        };
      })
      .sort((a, b) => b.totalAmount - a.totalAmount)
      .slice(0, 15);

    accounts.push({
      id,
      inDegree: inDeg,
      outDegree: outDeg,
      totalDegree: totDeg,
      totalSent: Math.round(raw.totalSent * 100) / 100,
      totalReceived: Math.round(raw.totalReceived * 100) / 100,
      netFlow: Math.round(netFlow * 100) / 100,
      txCount: raw.txCount,
      anomalyScore,
      isFlaggedForReview,
      patterns,
      counterparties: counterpartiesList,
      volumeZScore: parseFloat(volumeZScore.toFixed(2)),
      degreeZScore: parseFloat(degreeZScore.toFixed(2)),
      isLabeledFraud: raw.isLabeledFraud,
      syntheticPatternType: raw.patternType,
    });
  }

  // Sort accounts by anomaly score descending
  accounts.sort((a, b) => b.anomalyScore - a.anomalyScore);

  const topAnomalies = accounts.filter((a) => a.isFlaggedForReview);
  const suspiciousCount = topAnomalies.length;

  // 7. Network Density: E / (V * (V - 1))
  const density =
    totalAccounts > 1
      ? Array.from(edgeMap.values()).filter(e => e.source !== e.target).length / (totalAccounts * (totalAccounts - 1))
      : 0;

  // 8. Ground-Truth Validation Evaluation (Only if labels are explicitly present)
  let evaluation: GroundTruthEvaluation | undefined = undefined;
  const labeledNodes = accounts.filter((a) => a.isLabeledFraud !== undefined);
  const positiveLabels = accounts.filter((a) => a.isLabeledFraud === true);

  const transactionLabels = {
    normal: records.filter(r => r.label === 0 || r.label === false).length,
    anomalous: records.filter(r => r.label === 1 || r.label === true).length,
    unknown: records.filter(r => ![0, 1, false, true].includes(r.label as number | boolean)).length,
  };
  // Missing labels must not be silently treated as negative ground truth.
  if (transactionLabels.unknown === 0 && positiveLabels.length > 0) {
    const totalPositives = positiveLabels.length;
    const totalNegatives = accounts.length - totalPositives;

    const truePositives = topAnomalies.filter((a) => a.isLabeledFraud).length;
    const falsePositives = topAnomalies.length - truePositives;
    const falseNegatives = totalPositives - truePositives;
    const trueNegatives = totalNegatives - falsePositives;

    const precision =
      topAnomalies.length > 0 ? truePositives / topAnomalies.length : 0.0;
    const recall = totalPositives > 0 ? truePositives / totalPositives : 0.0;
    const f1Score =
      precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0.0;

    // Threshold-based average precision: tied scores enter together, independent of input order.
    let cumulativeTP = 0;
    let sumPrecision = 0;
    for (let i = 0; i < accounts.length;) {
      let end = i;
      let groupTP = 0;
      while (end < accounts.length && accounts[end].anomalyScore === accounts[i].anomalyScore) {
        if (accounts[end].isLabeledFraud) groupTP++;
        end++;
      }
      cumulativeTP += groupTP;
      sumPrecision += groupTP * cumulativeTP / end;
      i = end;
    }
    const prAuc = sumPrecision / totalPositives;

    evaluation = {
      labeledTotal: labeledNodes.length,
      positives: totalPositives,
      negatives: totalNegatives,
      truePositives,
      falsePositives,
      falseNegatives,
      trueNegatives,
      precision: parseFloat(precision.toFixed(4)),
      recall: parseFloat(recall.toFixed(4)),
      f1Score: parseFloat(f1Score.toFixed(4)),
      prAuc: parseFloat(prAuc.toFixed(4)),
      aggregationRule:
        "Account-Level Synthetic Label Convention: An account is classified as associated with an injected anomaly if it participated as source or destination in >= 1 transaction labeled is_anomaly == 1.",
      disclaimer:
        "Synthetic test-label convention for algorithmic benchmarking only; does not represent independently confirmed real-world fraud or legal liability.",
    };
  }

  const rawTotal = totalRawRows || records.length + rejectedRowsCount;
  const completeness =
    rawTotal > 0 ? parseFloat(((records.length / rawTotal) * 100).toFixed(1)) : 100.0;

  const summary: AnalysisSummary = {
    datasetName,
    sourceRecords: rawTotal,
    transactionLabels,
    fileSizeBytes,
    totalTransactions: records.length,
    totalVolume: Math.round(totalVolume * 100) / 100,
    currency: dominantCurrency,
    isMixedCurrency,
    currencyBreakdown: Object.keys(currencyBreakdown).length > 0 ? currencyBreakdown : undefined,
    meanAmount: Math.round(meanAmount * 100) / 100,
    medianAmount: Math.round(medianAmount * 100) / 100,
    maxAmount: Math.round(maxAmount * 100) / 100,
    accountVolumeMean: Math.round(accountVolumeMean * 100) / 100,
    accountVolumeStdDev: Math.round(accountVolumeStdDev * 100) / 100,
    accountVolumeThreshold: Math.round(accountVolumeThreshold * 100) / 100,
    uniqueAccounts: totalAccounts,
    uniqueEdges: edgeMap.size,
    sourceOnlyAccounts: sourceOnlyCount,
    sinkOnlyAccounts: sinkOnlyCount,
    intermediaryAccounts: intermediaryCount,
    networkDensity: parseFloat(density.toFixed(6)),
    maxInDegree: maxInDeg,
    maxOutDegree: maxOutDeg,
    avgDegree: parseFloat(avgDegree.toFixed(2)),
    suspiciousAccountCount: suspiciousCount,
    patternsDetected: {
      fanOutCount: fanOutTotal,
      fanInCount: fanInTotal,
      cycleCount: cycleTotal,
      volumeOutlierCount: volumeOutlierTotal,
      flowImbalanceCount: flowImbalanceTotal,
    },
    thresholdConfig: thresholds,
    analysisEngine: "GraphFin Client-Side Graph Topological Heuristics Engine v2.1",
    algorithmVersion: thresholds.version,
    totalRowsAccepted: records.length,
    totalRowsRejected: rejectedRowsCount,
    dataCompletenessPct: completeness,
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
