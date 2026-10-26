// Explicitly synthetic UI fixture only. Never imported by application code.
export const nodeRef = (n: number) => "node_" + String(n).padStart(32, "0");
export const graphExperiment = {
  experiment_id: "baseline-5k-E4-s42-m42",
  method: "E4",
  version: "fixture-v1",
  split_seed: 42,
  model_seed: 42,
};
export const graphDataset = {
  dataset_id: "ibm-5k",
  name: "IBM AML 5k",
  tier: "5k",
  status: "verified",
  provenance_status: "partially_verified",
  reason: null,
  graph_id: "ibm-5k-fixture",
  version: "canonical-directed-amount-v1",
  dataset_sha256: "a".repeat(64),
  index_sha256: "b".repeat(64),
  snapshot_identity: "c".repeat(64),
  time_start: 1577836800,
  time_end: 1578268800,
  time_semantics: "Synthetic UTC fixture",
  amount_unit: "dataset units",
  total_nodes: 1000,
  total_edges: 2000,
  approved_scope_nodes: 600,
  experiments: [graphExperiment],
};
export const graphCatalog = {
  datasets: [
    graphDataset,
    {
      ...graphDataset,
      dataset_id: "ibm-50k",
      name: "IBM AML 50k",
      tier: "50k",
      experiments: [
        { ...graphExperiment, experiment_id: "baseline-50k-E4-s42-m42" },
      ],
    },
    {
      ...graphDataset,
      dataset_id: "paysim",
      name: "PaySim",
      status: "unavailable",
      provenance_status: "unresolved",
      reason: "TOPOLOGY_UNAVAILABLE",
      experiments: [],
    },
  ],
  limitations: ["Synthetic fixture only."],
};
export const graphSession = {
  session_id: "S".repeat(32),
  expires_in_seconds: 600,
  query_budget: 20,
  dataset: graphDataset,
  experiment: graphExperiment,
  anchors: [1, 2, 3].map((n) => ({
    node_ref: nodeRef(n),
    display_id: "acct_fixture_" + n,
    role:
      n === 2
        ? "high-degree anchor"
        : n === 3
          ? "low-degree anchor"
          : "saved E4 top-20 anchor",
  })),
  focus_ref: nodeRef(1),
};
export function graphNeighborhood(url: URL) {
  const temporal = url.searchParams.has("start");
  const empty = Number(url.searchParams.get("min_amount")) >= 99999;
  return {
    schema_version: "graphfin-neighborhood-v1",
    graph_id: "ibm-5k-fixture",
    dataset_id: "ibm-5k",
    tier: "5k",
    version: "canonical-directed-amount-v1",
    snapshot_identity: "c".repeat(64),
    dataset_sha256: "a".repeat(64),
    index_sha256: "b".repeat(64),
    status: "verified",
    provenance_status: "partially_verified",
    experiment: graphExperiment,
    focus_ref: url.searchParams.get("focus_ref") || nodeRef(1),
    nodes: (empty ? [1] : [1, 2, 3]).map((n) => ({
      node_ref: nodeRef(n),
      display_id: "acct_fixture_" + n,
      node_type: "account",
      in_degree: n === 1 ? 1 : 2,
      out_degree: 1,
      neighbors: 2,
      received_amount: 12,
      sent_amount: 7,
      ranking_status: temporal
        ? "unavailable_temporal"
        : n === 3
          ? "unavailable_population"
          : "available",
      anomaly_score: temporal || n === 3 ? null : n === 1 ? 0.9 : 0.5,
      saved_rank: temporal || n === 3 ? null : n,
      diagnostic_ids: !temporal && n === 1 ? ["crest-000"] : [],
      diagnostic_status:
        !temporal && n === 1
          ? "compatible saved evidence"
          : "Unavailable: no compatible saved diagnostic.",
    })),
    edges: empty
      ? []
      : [
          {
            edge_ref: "edge_" + String(1).padStart(32, "0"),
            source_ref: nodeRef(1),
            target_ref: nodeRef(2),
            direction: "sender_to_receiver",
            transaction_count: 2,
            amount: 12,
            first_time: "2020-01-01T00:00:00+00:00",
            last_time: "2020-01-02T00:00:00+00:00",
            reciprocal_in_snapshot: true,
          },
          {
            edge_ref: "edge_" + String(2).padStart(32, "0"),
            source_ref: nodeRef(2),
            target_ref: nodeRef(3),
            direction: "sender_to_receiver",
            transaction_count: 1,
            amount: 4,
            first_time: "2020-01-03T00:00:00+00:00",
            last_time: "2020-01-03T00:00:00+00:00",
            reciprocal_in_snapshot: false,
          },
        ],
    depth: Number(url.searchParams.get("depth") || 1),
    direction: url.searchParams.get("direction") || "both",
    start: Number(url.searchParams.get("start") || 1577836800),
    end: Number(url.searchParams.get("end") || 1578268800),
    min_count: Number(url.searchParams.get("min_count") || 1),
    min_amount: Number(url.searchParams.get("min_amount") || 0),
    temporal_subset: temporal,
    scope_nodes: 600,
    max_nodes: 100,
    max_edges: 500,
    truncated: true,
    truncation_reasons: ["approved_disclosure_scope"],
    remaining_queries: 19,
    remaining_node_grants: 597,
    query_seconds: 0.01,
    amount_unit: "dataset units",
    limitations: ["Synthetic fixture only."],
  };
}
