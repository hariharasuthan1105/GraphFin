import type { GraphNeighborhood } from "./contract";
import type { Diagnostic } from "../contract";
import { useResearch, fmt } from "../state";
import { State } from "../ui";

function SavedDiagnostic({ id }: { id: string }) {
  const r = useResearch<Diagnostic>("/diagnostics/" + id, "Diagnostic");
  return !r.data ? (
    <State {...r} />
  ) : (
    <div>
      <h3>Experimental model-sensitivity diagnostic</h3>
      <dl>
        <dt>Saved diagnostic</dt>
        <dd>{r.data.diagnostic_id}</dd>
        <dt>Family / method</dt>
        <dd>
          {r.data.family ?? "Unavailable"} / {r.data.method}
        </dd>
        <dt>Evidence available / valid</dt>
        <dd>
          {r.data.available ? "Yes" : "No"} /{" "}
          {r.data.valid == null ? "Unavailable" : r.data.valid ? "Yes" : "No"}
        </dd>
        <dt>Original model score</dt>
        <dd>{fmt(r.data.baseline_score, 8)}</dd>
        <dt>Intervened score</dt>
        <dd>{fmt(r.data.intervened_score, 8)}</dd>
        <dt>Signed score change / fidelity</dt>
        <dd>{fmt(r.data.signed_fidelity, 8)}</dd>
        <dt>Omitted count / fraction</dt>
        <dd>
          {fmt(r.data.omitted_count, 0)} / {fmt(r.data.omitted_fraction)}
        </dd>
        <dt>Stability</dt>
        <dd>Unavailable through the approved diagnostic API.</dd>
      </dl>
      <p>
        {r.data.reason ??
          "Saved evidence only; removed transaction identities are not exposed."}
      </p>
      <p>
        CREST detection and explanation superiority have not been demonstrated.
        Score changes are not causal evidence of wrongdoing.
      </p>
    </div>
  );
}

export default function Inspector({
  data,
  selected,
  onExplore,
  diagnostic,
  setDiagnostic,
}: {
  data: GraphNeighborhood;
  selected: string;
  onExplore: (ref: string) => void;
  diagnostic: string | undefined;
  setDiagnostic: (id: string | undefined) => void;
}) {
  const node = data.nodes.find((n) => n.node_ref === selected);
  const edge = data.edges.find((e) => e.edge_ref === selected);
  return (
    <section
      className="graph-inspector"
      aria-label="Selected graph evidence"
      aria-live="polite"
    >
      <p className="eyebrow">INSPECT / OBSERVED RELATIONSHIPS</p>
      {node ? (
        <>
          <h2>Account detail</h2>
          <dl>
            <dt>Display identity</dt>
            <dd>{node.display_id}</dd>
            <dt>Type</dt>
            <dd>{node.node_type}</dd>
            <dt>Incoming / outgoing degree</dt>
            <dd>
              {node.in_degree} / {node.out_degree}
            </dd>
            <dt>Unique neighbors</dt>
            <dd>{node.neighbors}</dd>
            <dt>Received / sent amount</dt>
            <dd>
              {fmt(node.received_amount, 2)} / {fmt(node.sent_amount, 2)}
            </dd>
            <dt>Statistics scope</dt>
            <dd>Full source snapshot; amounts in dataset units.</dd>
            <dt>Saved experiment</dt>
            <dd>{data.experiment.experiment_id}</dd>
            <dt>Version</dt>
            <dd>{data.experiment.version}</dd>
            <dt>Saved anomaly score / descending rank</dt>
            <dd>
              {node.ranking_status === "available"
                ? `${fmt(node.anomaly_score, 8)} / ${fmt(node.saved_rank, 0)}`
                : node.ranking_status === "unavailable_temporal"
                  ? "Unavailable for temporal subwindows."
                  : "Unavailable: account is outside this experiment’s held-out score population."}
            </dd>
            <dt>CREST</dt>
            <dd>{node.diagnostic_status}</dd>
          </dl>
          <button onClick={() => onExplore(node.node_ref)}>
            Explore this account →
          </button>
          {node.diagnostic_ids.length > 0 && (
            <label>
              Compatible saved diagnostic
              <select
                aria-label="Compatible saved diagnostic"
                value={diagnostic ?? ""}
                onChange={(e) => setDiagnostic(e.target.value || undefined)}
              >
                <option value="">Select saved evidence</option>
                {node.diagnostic_ids.map((id) => (
                  <option key={id}>{id}</option>
                ))}
              </select>
            </label>
          )}
        </>
      ) : edge ? (
        <>
          <h2>Relationship detail</h2>
          <dl>
            <dt>Source (sender)</dt>
            <dd>
              {
                data.nodes.find((n) => n.node_ref === edge.source_ref)
                  ?.display_id
              }
            </dd>
            <dt>Destination (receiver)</dt>
            <dd>
              {
                data.nodes.find((n) => n.node_ref === edge.target_ref)
                  ?.display_id
              }
            </dd>
            <dt>Direction</dt>
            <dd>Sender → receiver</dd>
            <dt>Aggregated transactions</dt>
            <dd>{edge.transaction_count}</dd>
            <dt>Aggregated amount</dt>
            <dd>{fmt(edge.amount, 2)} dataset units</dd>
            <dt>First / last retained timestamp</dt>
            <dd>
              {edge.first_time} / {edge.last_time}
            </dd>
            <dt>Reciprocal in full snapshot</dt>
            <dd>
              {edge.reciprocal_in_snapshot
                ? "Yes; a reverse edge may be hidden by filters."
                : "No"}
            </dd>
            <dt>Graph identity</dt>
            <dd>{data.graph_id}</dd>
            <dt>Source / label lineage</dt>
            <dd>{data.dataset_id} / partially verified</dd>
          </dl>
        </>
      ) : (
        <>
          <h2>Inspect the evidence</h2>
          <p>
            Select an account or directed relationship, or use the accessible
            lists below.
          </p>
        </>
      )}
      {diagnostic && node?.diagnostic_ids.includes(diagnostic) && (
        <SavedDiagnostic id={diagnostic} />
      )}
      <p className="graph-session-note">
        Anomaly scores are not fraud probabilities. Opaque references expire
        with this session and must not be saved as account identities.
      </p>
    </section>
  );
}
