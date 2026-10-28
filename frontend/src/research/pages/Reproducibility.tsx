import { useState } from "react";
import { useResearch } from "../state";
import type { Reproducibility as Data } from "../contract";
import { State, Heading, Panel, Table, Hash, Notice, Status } from "../ui";
import { useSession } from "../sessionContext";

export default function Reproducibility() {
  const [tab, setTab] = useState("Parameters");
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
              <dd>{activeSession.summary.algorithmVersion || "Version not recorded"} (in-browser heuristics)</dd>
              <dt>Input text SHA-256</dt><dd><Hash value={activeSession.summary.inputChecksum} /></dd>
              <dt>Accepted / rejected records</dt><dd>{activeSession.summary.totalRowsAccepted ?? activeSession.summary.totalTransactions} / {activeSession.summary.totalRowsRejected ?? 'Unavailable'}</dd>
              <dt>Replay Determinism</dt>
              <dd><span style={{ color: "#f5f5f5", fontWeight: 600 }}><b style={{ color: "#c04b52" }}>—</b> Not replay-verified for this uploaded session</span></dd>
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
            <div className="panel-body"><div className="session-tabs">{['Environment', 'Parameters', 'Seeds', 'Dataset Identity'].map(label => <button key={label} aria-pressed={tab === label} onClick={() => setTab(label)}>{label}</button>)}</div>
            {tab === 'Environment' && <p>Environment versions are unavailable through the saved API projection. No local environment is inferred.</p>}
            {tab === 'Seeds' && <p className="technical">Recorded split seeds: {r.data.split_seeds.join(' / ')}. Model seeds are recorded per replay above.</p>}
            {tab === 'Dataset Identity' && <>{r.data.replays.map(replay => <p key={replay.tier}>{replay.tier}: <Hash value={replay.dataset_sha256} /></p>)}</>}
            {tab === 'Parameters' && <dl className="definition">
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
            </dl>}</div>
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
