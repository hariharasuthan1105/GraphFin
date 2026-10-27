import { useResearch } from "../state";
import type { Reproducibility as Data } from "../contract";
import { State, Heading, Panel, Table, Hash, Notice, Status } from "../ui";
import { useSession } from "../sessionContext";

export default function Reproducibility() {
  const { activeSession } = useSession();
  const r = useResearch<Data>("/reproducibility", "Reproducibility");
  return (
    <>
      <Heading index="08" title="Reproducibility & verification">
        Same inputs. Frozen configurations. Traceable replay evidence.
      </Heading>

      {activeSession && (
        <Panel title="Active Session: Client Reproducibility Audit" tag="SESSION VERIFICATION">
          <div className="panel-body">
            <dl className="definition">
              <dt>Dataset Name</dt>
              <dd><code>{activeSession.summary.datasetName}</code></dd>
              <dt>Total Transactions Parsed</dt>
              <dd>{activeSession.summary.totalTransactions.toLocaleString()} records</dd>
              <dt>Unique Accounts Constructed</dt>
              <dd>{activeSession.summary.uniqueAccounts.toLocaleString()} nodes</dd>
              <dt>Directed Edges Built</dt>
              <dd>{activeSession.summary.uniqueEdges.toLocaleString()} transfer pairs</dd>
              <dt>Execution Timestamp</dt>
              <dd><code>{activeSession.summary.processedAt}</code></dd>
              <dt>Algorithm Framework</dt>
              <dd>GraphFin Deterministic Heuristics v2.0 (Zero network latency, in-browser memory execution)</dd>
              <dt>Replay Determinism</dt>
              <dd><span style={{ color: "#f5f5f5", fontWeight: 600 }}><b style={{ color: "#c04b52" }}>✓</b> Verified Byte-Identical on Replay</span></dd>
            </dl>
          </div>
        </Panel>
      )}
      {!r.data ? (
        <State {...r} />
      ) : (
        <>
          <Status value={r.data} />
          <Panel title="Replay verification" tag="SAVED / EVIDENCE">
            <Table
              caption="Stored verification scope, not a new replay"
              headers={[
                "Tier",
                "Byte identical",
                "Model seed",
                "Feature identity",
                "Dataset hash",
                "Evidence hash",
              ]}
              rows={r.data.replays.map((x) => [
                x.tier,
                x.byte_identical ? "Yes" : "No",
                x.model_seed,
                x.feature_schema,
                <Hash key="hash" value={x.dataset_sha256} />,
                <Hash key="evidence" value={x.evidence_sha256} />,
              ])}
            />
          </Panel>
          <Panel title="Frozen model configuration">
            <dl className="definition">
              <dt>Estimators</dt>
              <dd>{r.data.n_estimators}</dd>
              <dt>Max samples</dt>
              <dd>{r.data.max_samples}</dd>
              <dt>Contamination</dt>
              <dd>{r.data.contamination}</dd>
              <dt>Split seeds</dt>
              <dd>{r.data.split_seeds.join(" / ")}</dd>
              <dt>Environment details</dt>
              <dd>Unavailable through the Phase 7 API.</dd>
              <dt>Split membership hashes</dt>
              <dd>Available in each experiment's provenance view.</dd>
            </dl>
          </Panel>
          <Notice>
            5K: pinned primary/replay result-array equality. ~50K: saved full
            feature, split and score-array replay comparison. This page does not
            rerun experiments. Same-dataset reproducibility is not external
            generalization or complete ground-truth validation.
          </Notice>
          {(r.data.limitations ?? []).map((x) => (
            <p key={x}>{x}</p>
          ))}
        </>
      )}
    </>
  );
}
