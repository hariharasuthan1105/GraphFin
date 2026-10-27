/**
 * GraphFin Simulated Demo Graph Engine
 * Generates realistic synthetic transaction topologies with known AML patterns for showcase & demonstration.
 * Clearly marked as synthetic simulation to maintain 100% scientific integrity.
 */
import type {
  AccountNode,
  AnalysisResult,
  TransferEdge,
} from "../datasetAnalysis/types";
import type { SimulatedPresetKey } from "../sessionContext";

export interface SimulatedPresetMeta {
  key: SimulatedPresetKey;
  title: string;
  badge: string;
  description: string;
  motifs: string[];
  totalAccounts: number;
  totalTransfers: number;
  totalVolumeFormatted: string;
}

export const SIMULATED_PRESETS_META: Record<SimulatedPresetKey, SimulatedPresetMeta> = {
  "mule-ring": {
    key: "mule-ring",
    title: "Money Mule Layering Ring",
    badge: "MULE RING",
    description:
      "A primary high-balance origin disperses funds across 6 intermediary mule accounts, which subsequently aggregate into two offshore collection sinks.",
    motifs: ["Fan-Out Dispersal", "Mule Layering", "Fan-In Aggregation"],
    totalAccounts: 24,
    totalTransfers: 38,
    totalVolumeFormatted: "$1,840,000",
  },
  "ponzi-cycle": {
    key: "ponzi-cycle",
    title: "Circular Wash Trading & Cycle",
    badge: "CIRCULAR FLOW",
    description:
      "A 4-account directed circular loop with escalating transaction volumes and reciprocal feedback channels designed to fabricate trading activity.",
    motifs: ["Directed Cycle", "Wash Trading", "Reciprocal Feedback"],
    totalAccounts: 18,
    totalTransfers: 26,
    totalVolumeFormatted: "$3,420,000",
  },
  "smurfing-fanout": {
    key: "smurfing-fanout",
    title: "High-Velocity Smurfing Dispersal",
    badge: "RAPID DISPERSAL",
    description:
      "A corporate treasury node distributes rapid structured transfers just below statutory reporting thresholds ($9,800) to 12 retail recipients.",
    motifs: ["Fan-Out Burst", "Threshold Structuring", "Flow Imbalance"],
    totalAccounts: 20,
    totalTransfers: 32,
    totalVolumeFormatted: "$784,000",
  },
  "fanin-aggregation": {
    key: "fanin-aggregation",
    title: "Multi-Source Funnel Aggregation",
    badge: "FUNNEL AGGREGATION",
    description:
      "10 distinct low-balance consumer feeder accounts funnel accumulated sums into a central consolidation wallet over a compressed time horizon.",
    motifs: ["Fan-In Funnel", "Collection Sink", "Volume Concentration"],
    totalAccounts: 22,
    totalTransfers: 30,
    totalVolumeFormatted: "$965,000",
  },
};

export function getSimulatedPresetResult(preset: SimulatedPresetKey): AnalysisResult {
  switch (preset) {
    case "ponzi-cycle":
      return buildPonziCycle();
    case "smurfing-fanout":
      return buildSmurfingFanout();
    case "fanin-aggregation":
      return buildFanInAggregation();
    case "mule-ring":
    default:
      return buildMuleRing();
  }
}

function buildMuleRing(): AnalysisResult {
  const accounts: AccountNode[] = [];
  const edges: TransferEdge[] = [];

  // Origin account
  accounts.push({
    id: "SIM_ORIGIN_ALPHA",
    inDegree: 1,
    outDegree: 6,
    totalDegree: 7,
    totalSent: 720000,
    totalReceived: 50000,
    netFlow: -670000,
    txCount: 7,
    anomalyScore: 0.885,
    patterns: ["FAN_OUT", "FLOW_IMBALANCE"],
    counterparties: [
      { id: "SIM_MULE_01", direction: "out", amount: 120000, count: 1 },
      { id: "SIM_MULE_02", direction: "out", amount: 120000, count: 1 },
      { id: "SIM_MULE_03", direction: "out", amount: 120000, count: 1 },
      { id: "SIM_MULE_04", direction: "out", amount: 120000, count: 1 },
      { id: "SIM_MULE_05", direction: "out", amount: 120000, count: 1 },
      { id: "SIM_MULE_06", direction: "out", amount: 120000, count: 1 },
      { id: "LEGIT_PAYROLL_01", direction: "in", amount: 50000, count: 1 },
    ],
  });

  // 6 Mule Accounts
  for (let i = 1; i <= 6; i++) {
    const muleId = `SIM_MULE_0${i}`;
    const targetSink = i <= 3 ? "SIM_SINK_OFFSHORE_A" : "SIM_SINK_OFFSHORE_B";
    const amount = 115000;
    accounts.push({
      id: muleId,
      inDegree: 1,
      outDegree: 1,
      totalDegree: 2,
      totalSent: amount,
      totalReceived: 120000,
      netFlow: -5000,
      txCount: 2,
      anomalyScore: 0.65,
      patterns: ["FLOW_IMBALANCE"],
      counterparties: [
        { id: "SIM_ORIGIN_ALPHA", direction: "in", amount: 120000, count: 1 },
        { id: targetSink, direction: "out", amount, count: 1 },
      ],
    });

    edges.push({
      source: "SIM_ORIGIN_ALPHA",
      target: muleId,
      amount: 120000,
      count: 1,
    });
    edges.push({
      source: muleId,
      target: targetSink,
      amount,
      count: 1,
    });
  }

  // 2 Sinks
  accounts.push({
    id: "SIM_SINK_OFFSHORE_A",
    inDegree: 3,
    outDegree: 0,
    totalDegree: 3,
    totalSent: 0,
    totalReceived: 345000,
    netFlow: 345000,
    txCount: 3,
    anomalyScore: 0.79,
    patterns: ["FAN_IN", "FLOW_IMBALANCE"],
    counterparties: [
      { id: "SIM_MULE_01", direction: "in", amount: 115000, count: 1 },
      { id: "SIM_MULE_02", direction: "in", amount: 115000, count: 1 },
      { id: "SIM_MULE_03", direction: "in", amount: 115000, count: 1 },
    ],
  });

  accounts.push({
    id: "SIM_SINK_OFFSHORE_B",
    inDegree: 3,
    outDegree: 0,
    totalDegree: 3,
    totalSent: 0,
    totalReceived: 345000,
    netFlow: 345000,
    txCount: 3,
    anomalyScore: 0.79,
    patterns: ["FAN_IN", "FLOW_IMBALANCE"],
    counterparties: [
      { id: "SIM_MULE_04", direction: "in", amount: 115000, count: 1 },
      { id: "SIM_MULE_05", direction: "in", amount: 115000, count: 1 },
      { id: "SIM_MULE_06", direction: "in", amount: 115000, count: 1 },
    ],
  });

  // Background normal nodes
  for (let i = 1; i <= 15; i++) {
    const normId = `NORMAL_RETAIL_${String(i).padStart(2, "0")}`;
    const nextNorm = `NORMAL_RETAIL_${String((i % 15) + 1).padStart(2, "0")}`;
    accounts.push({
      id: normId,
      inDegree: 1,
      outDegree: 1,
      totalDegree: 2,
      totalSent: 2500,
      totalReceived: 2500,
      netFlow: 0,
      txCount: 2,
      anomalyScore: 0.08,
      patterns: [],
      counterparties: [
        { id: nextNorm, direction: "out", amount: 2500, count: 1 },
      ],
    });
    edges.push({
      source: normId,
      target: nextNorm,
      amount: 2500,
      count: 1,
    });
  }

  edges.push({
    source: "LEGIT_PAYROLL_01",
    target: "SIM_ORIGIN_ALPHA",
    amount: 50000,
    count: 1,
  });

  return {
    summary: {
      datasetName: "simulated_mule_ring_showcase.csv",
      fileSizeBytes: 14200,
      totalTransactions: 38,
      totalVolume: 1840000,
      meanAmount: 48421,
      medianAmount: 2500,
      maxAmount: 120000,
      uniqueAccounts: accounts.length,
      uniqueEdges: edges.length,
      sourceOnlyAccounts: 1,
      sinkOnlyAccounts: 2,
      intermediaryAccounts: 21,
      networkDensity: edges.length / (accounts.length * (accounts.length - 1)),
      maxInDegree: 3,
      maxOutDegree: 6,
      avgDegree: 2.1,
      suspiciousAccountCount: 9,
      patternsDetected: {
        fanOutCount: 1,
        fanInCount: 2,
        cycleCount: 0,
        volumeOutlierCount: 6,
      },
      processedAt: new Date().toISOString(),
    },
    accounts,
    edges,
    topAnomalies: accounts
      .filter((a) => a.anomalyScore >= 0.45)
      .sort((a, b) => b.anomalyScore - a.anomalyScore),
  };
}

function buildPonziCycle(): AnalysisResult {
  const accounts: AccountNode[] = [];
  const edges: TransferEdge[] = [];

  const loopNodes = ["CYCLE_NODE_A", "CYCLE_NODE_B", "CYCLE_NODE_C", "CYCLE_NODE_D"];
  for (let i = 0; i < loopNodes.length; i++) {
    const id = loopNodes[i];
    const nextId = loopNodes[(i + 1) % loopNodes.length];
    const prevId = loopNodes[(i - 1 + loopNodes.length) % loopNodes.length];
    accounts.push({
      id,
      inDegree: 2,
      outDegree: 2,
      totalDegree: 4,
      totalSent: 850000,
      totalReceived: 850000,
      netFlow: 0,
      txCount: 4,
      anomalyScore: 0.915,
      patterns: ["CYCLE", "VOLUME_OUTLIER"],
      counterparties: [
        { id: nextId, direction: "out", amount: 800000, count: 2 },
        { id: prevId, direction: "in", amount: 800000, count: 2 },
      ],
    });

    edges.push({
      source: id,
      target: nextId,
      amount: 800000,
      count: 2,
      isReciprocal: true,
    });
  }

  // Normal surrounding nodes
  for (let i = 1; i <= 14; i++) {
    const normId = `NORMAL_COMMERCE_${i}`;
    const next = `NORMAL_COMMERCE_${(i % 14) + 1}`;
    accounts.push({
      id: normId,
      inDegree: 1,
      outDegree: 1,
      totalDegree: 2,
      totalSent: 1500,
      totalReceived: 1500,
      netFlow: 0,
      txCount: 2,
      anomalyScore: 0.05,
      patterns: [],
      counterparties: [{ id: next, direction: "out", amount: 1500, count: 1 }],
    });
    edges.push({
      source: normId,
      target: next,
      amount: 1500,
      count: 1,
    });
  }

  return {
    summary: {
      datasetName: "simulated_ponzi_cycle_showcase.csv",
      fileSizeBytes: 12400,
      totalTransactions: 26,
      totalVolume: 3420000,
      meanAmount: 131538,
      medianAmount: 1500,
      maxAmount: 800000,
      uniqueAccounts: accounts.length,
      uniqueEdges: edges.length,
      sourceOnlyAccounts: 0,
      sinkOnlyAccounts: 0,
      intermediaryAccounts: accounts.length,
      networkDensity: edges.length / (accounts.length * (accounts.length - 1)),
      maxInDegree: 2,
      maxOutDegree: 2,
      avgDegree: 2.2,
      suspiciousAccountCount: 4,
      patternsDetected: {
        fanOutCount: 0,
        fanInCount: 0,
        cycleCount: 4,
        volumeOutlierCount: 4,
      },
      processedAt: new Date().toISOString(),
    },
    accounts,
    edges,
    topAnomalies: accounts
      .filter((a) => a.anomalyScore >= 0.45)
      .sort((a, b) => b.anomalyScore - a.anomalyScore),
  };
}

function buildSmurfingFanout(): AnalysisResult {
  const accounts: AccountNode[] = [];
  const edges: TransferEdge[] = [];

  const originId = "DISPERSAL_TREASURY_CORP";
  const mules: string[] = [];
  for (let i = 1; i <= 12; i++) {
    mules.push(`SMURF_RECIPIENT_${String(i).padStart(2, "0")}`);
  }

  accounts.push({
    id: originId,
    inDegree: 0,
    outDegree: 12,
    totalDegree: 12,
    totalSent: 117600,
    totalReceived: 0,
    netFlow: -117600,
    txCount: 12,
    anomalyScore: 0.94,
    patterns: ["FAN_OUT", "FLOW_IMBALANCE"],
    counterparties: mules.map((m) => ({
      id: m,
      direction: "out" as const,
      amount: 9800,
      count: 1,
    })),
  });

  for (const m of mules) {
    accounts.push({
      id: m,
      inDegree: 1,
      outDegree: 1,
      totalDegree: 2,
      totalSent: 9500,
      totalReceived: 9800,
      netFlow: -300,
      txCount: 2,
      anomalyScore: 0.52,
      patterns: ["FLOW_IMBALANCE"],
      counterparties: [
        { id: originId, direction: "in", amount: 9800, count: 1 },
        { id: "CASH_CASINO_OUTLET", direction: "out", amount: 9500, count: 1 },
      ],
    });

    edges.push({
      source: originId,
      target: m,
      amount: 9800,
      count: 1,
    });
    edges.push({
      source: m,
      target: "CASH_CASINO_OUTLET",
      amount: 9500,
      count: 1,
    });
  }

  accounts.push({
    id: "CASH_CASINO_OUTLET",
    inDegree: 12,
    outDegree: 0,
    totalDegree: 12,
    totalSent: 0,
    totalReceived: 114000,
    netFlow: 114000,
    txCount: 12,
    anomalyScore: 0.89,
    patterns: ["FAN_IN", "FLOW_IMBALANCE"],
    counterparties: mules.map((m) => ({
      id: m,
      direction: "in" as const,
      amount: 9500,
      count: 1,
    })),
  });

  return {
    summary: {
      datasetName: "simulated_smurfing_fanout_showcase.csv",
      fileSizeBytes: 10800,
      totalTransactions: 24,
      totalVolume: 231600,
      meanAmount: 9650,
      medianAmount: 9650,
      maxAmount: 9800,
      uniqueAccounts: accounts.length,
      uniqueEdges: edges.length,
      sourceOnlyAccounts: 1,
      sinkOnlyAccounts: 1,
      intermediaryAccounts: 12,
      networkDensity: edges.length / (accounts.length * (accounts.length - 1)),
      maxInDegree: 12,
      maxOutDegree: 12,
      avgDegree: 2.8,
      suspiciousAccountCount: 14,
      patternsDetected: {
        fanOutCount: 1,
        fanInCount: 1,
        cycleCount: 0,
        volumeOutlierCount: 0,
      },
      processedAt: new Date().toISOString(),
    },
    accounts,
    edges,
    topAnomalies: accounts
      .filter((a) => a.anomalyScore >= 0.45)
      .sort((a, b) => b.anomalyScore - a.anomalyScore),
  };
}

function buildFanInAggregation(): AnalysisResult {
  const accounts: AccountNode[] = [];
  const edges: TransferEdge[] = [];
  const sinkId = "CENTRAL_COLLECTION_VAULT";
  const feeders: string[] = [];

  for (let i = 1; i <= 10; i++) {
    const fid = `FEEDER_DEPOSITOR_${String(i).padStart(2, "0")}`;
    feeders.push(fid);
    accounts.push({
      id: fid,
      inDegree: 0,
      outDegree: 1,
      totalDegree: 1,
      totalSent: 48000,
      totalReceived: 0,
      netFlow: -48000,
      txCount: 1,
      anomalyScore: 0.42,
      patterns: ["FLOW_IMBALANCE"],
      counterparties: [
        { id: sinkId, direction: "out" as const, amount: 48000, count: 1 },
      ],
    });
    edges.push({
      source: fid,
      target: sinkId,
      amount: 48000,
      count: 1,
    });
  }

  accounts.push({
    id: sinkId,
    inDegree: 10,
    outDegree: 1,
    totalDegree: 11,
    totalSent: 450000,
    totalReceived: 480000,
    netFlow: 30000,
    txCount: 11,
    anomalyScore: 0.92,
    patterns: ["FAN_IN", "VOLUME_OUTLIER"],
    counterparties: [
      ...feeders.map((f) => ({
        id: f,
        direction: "in" as const,
        amount: 48000,
        count: 1,
      })),
      {
        id: "OFFSHORE_WIRE_SETTLEMENT",
        direction: "out" as const,
        amount: 450000,
        count: 1,
      },
    ],
  });

  edges.push({
    source: sinkId,
    target: "OFFSHORE_WIRE_SETTLEMENT",
    amount: 450000,
    count: 1,
  });

  accounts.push({
    id: "OFFSHORE_WIRE_SETTLEMENT",
    inDegree: 1,
    outDegree: 0,
    totalDegree: 1,
    totalSent: 0,
    totalReceived: 450000,
    netFlow: 450000,
    txCount: 1,
    anomalyScore: 0.81,
    patterns: ["VOLUME_OUTLIER"],
    counterparties: [
      { id: sinkId, direction: "in" as const, amount: 450000, count: 1 },
    ],
  });

  // Background accounts
  for (let i = 1; i <= 10; i++) {
    const id = `MERCHANT_PAY_${i}`;
    const next = `MERCHANT_PAY_${(i % 10) + 1}`;
    accounts.push({
      id,
      inDegree: 1,
      outDegree: 1,
      totalDegree: 2,
      totalSent: 1200,
      totalReceived: 1200,
      netFlow: 0,
      txCount: 2,
      anomalyScore: 0.04,
      patterns: [],
      counterparties: [{ id: next, direction: "out", amount: 1200, count: 1 }],
    });
    edges.push({
      source: id,
      target: next,
      amount: 1200,
      count: 1,
    });
  }

  return {
    summary: {
      datasetName: "simulated_fanin_aggregation_showcase.csv",
      fileSizeBytes: 11200,
      totalTransactions: 21,
      totalVolume: 965000,
      meanAmount: 45952,
      medianAmount: 48000,
      maxAmount: 450000,
      uniqueAccounts: accounts.length,
      uniqueEdges: edges.length,
      sourceOnlyAccounts: 10,
      sinkOnlyAccounts: 1,
      intermediaryAccounts: 11,
      networkDensity: edges.length / (accounts.length * (accounts.length - 1)),
      maxInDegree: 10,
      maxOutDegree: 1,
      avgDegree: 2.1,
      suspiciousAccountCount: 2,
      patternsDetected: {
        fanOutCount: 0,
        fanInCount: 1,
        cycleCount: 0,
        volumeOutlierCount: 2,
      },
      processedAt: new Date().toISOString(),
    },
    accounts,
    edges,
    topAnomalies: accounts
      .filter((a) => a.anomalyScore >= 0.45)
      .sort((a, b) => b.anomalyScore - a.anomalyScore),
  };
}
