import { useResearch, fmt } from "../state";
import { useState } from "react";
import type { Page_Experiment_, Comparison as Data } from "../contract";
import {
  State,
  Heading,
  Panel,
  Table,
  Tier,
  Chart,
  Notice,
  Qualifications,
  Hash,
} from "../ui";
import { query } from "../client";
import { useSession } from "../sessionContext";
function Compare({ ids, metric }: { ids: string[]; metric: string }) {
  const path =
    "/comparisons?" +
    ids.map((id) => "experiment_id=" + encodeURIComponent(id)).join("&") +
    "&metric=" +
    metric;
  const r = useResearch<Data>(path, "Comparison");
  return !r.data ? (
    <State {...r} />
  ) : (
    <Panel title="Compatible model comparison" tag="DESCRIPTIVE / ONLY">
      <Chart
        labels={r.data.values.map((x) => x.experiment_id.split("-")[2])}
        values={r.data.values.map((x) => x.value)}
        title={metric.replaceAll("_", " ")}
      />
      <Table
        caption="Exact stored values on the same held-out population"
        headers={["Experiment", "Metric value"]}
        rows={r.data.values.map((x) => [x.experiment_id, fmt(x.value, 8)])}
      />
      <div className="panel-body">
        <Hash key="hash" value={r.data.population_identity} />
        <p>{r.data.interpretation}</p>
      </div>
    </Panel>
  );
}
export default function Comparison() {
  const { activeSession } = useSession();
  const [tier, setTier] = useState("ibm-5k");
  const [seed, setSeed] = useState("42");
  const [metric, setMetric] = useState("average_precision");
  const r = useResearch<Page_Experiment_>(
    query("/experiments", {
      dataset_id: tier,
      split_seed: seed,
      model_seed: 42,
      page_size: 100,
    }),
    "Page_Experiment_",
  );
  const rows = r.data?.items.filter((x) => x.status === "verified") ?? [];
  return (
    <>
      <Heading index="06" title="Model & indicator comparison">
        Compare methods within exact benchmark populations, or evaluate topological feature contributions on your active dataset.
      </Heading>

      {activeSession && (
        <Panel title="Active Dataset: Topological Indicator Contribution" tag="HEURISTIC SENSITIVITY">
          <div className="panel-body">
            <p style={{ margin: "0 0 12px 0", fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
              Analysis of structural anomaly drivers on <strong>{activeSession.summary.datasetName}</strong>:
            </p>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                gap: "10px",
                marginBottom: "14px",
              }}
            >
              <div style={{ background: "#08090d", padding: "10px", borderRadius: "4px" }}>
                <span style={{ fontSize: "10px", color: "#64748b", display: "block" }}>FAN-OUT</span>
                <strong style={{ fontSize: "14px", color: "#f59e0b" }}>
                  {activeSession.summary.patternsDetected.fanOutCount} detected
                </strong>
                <span style={{ fontSize: "10px", color: "#94a3b8", display: "block" }}>Rapid dispersal</span>
              </div>
              <div style={{ background: "#08090d", padding: "10px", borderRadius: "4px" }}>
                <span style={{ fontSize: "10px", color: "#64748b", display: "block" }}>FAN-IN</span>
                <strong style={{ fontSize: "14px", color: "#f59e0b" }}>
                  {activeSession.summary.patternsDetected.fanInCount} detected
                </strong>
                <span style={{ fontSize: "10px", color: "#94a3b8", display: "block" }}>Mule aggregation</span>
              </div>
              <div style={{ background: "#08090d", padding: "10px", borderRadius: "4px" }}>
                <span style={{ fontSize: "10px", color: "#64748b", display: "block" }}>CYCLES</span>
                <strong style={{ fontSize: "14px", color: "#a855f7" }}>
                  {activeSession.summary.patternsDetected.cycleCount} detected
                </strong>
                <span style={{ fontSize: "10px", color: "#94a3b8", display: "block" }}>Reciprocal loops</span>
              </div>
              <div style={{ background: "#08090d", padding: "10px", borderRadius: "4px" }}>
                <span style={{ fontSize: "10px", color: "#64748b", display: "block" }}>VOL OUTLIERS</span>
                <strong style={{ fontSize: "14px", color: "#f43f5e" }}>
                  {activeSession.summary.patternsDetected.volumeOutlierCount} detected
                </strong>
                <span style={{ fontSize: "10px", color: "#94a3b8", display: "block" }}>Extreme values</span>
              </div>
            </div>
            <p style={{ margin: 0, fontSize: "11px", color: "#64748b", lineHeight: 1.4 }}>
              <strong>Scientific Honesty Note:</strong> The comparison below reflects historical E0–E6 Isolation Forest models trained on frozen IBM AML splits. The active uploaded session executes deterministic graph algorithms and does not fabricate supervised ML model reruns on arbitrary input files.
            </p>
          </div>
        </Panel>
      )}
      <div className="filters">
        <Tier value={tier} onChange={setTier} />
        <label>
          Split seed
          <select value={seed} onChange={(e) => setSeed(e.target.value)}>
            {[42, 123, 7, 2024, 99, 555].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
        <label>
          Metric
          <select value={metric} onChange={(e) => setMetric(e.target.value)}>
            {[
              "average_precision",
              "roc_auc",
              "precision_at_10",
              "precision_at_25",
              "precision_at_50",
              "precision_at_100",
            ].map((m) => (
              <option key={m}>{m}</option>
            ))}
          </select>
        </label>
      </div>
      <Notice>
        Average Precision uses the non-interpolated PR-AUC convention. E6_BASE
        is calibration-only: ties can change rankings relative to E4. Incomplete
        intervention-based E6 results are excluded.
      </Notice>
      {!r.data ? (
        <State {...r} />
      ) : rows.length < 2 ? (
        <Notice>Not enough compatible completed methods.</Notice>
      ) : (
        <>
          <Compare
            key={tier + seed + metric}
            ids={rows.map((x) => x.experiment_id)}
            metric={metric}
          />
          <Panel title="Retrieval evidence" tag="POSITIVE HITS / RECALL">
            <Table
              caption="Stored retrieval counts, precision and recall; effective K may differ"
              headers={[
                "Method",
                "Version",
                "K",
                "Effective K",
                "Positive hits",
                "Precision",
                "Recall",
              ]}
              rows={rows.flatMap(
                (r) =>
                  r.metrics?.retrieval?.map((k) => [
                    r.method,
                    r.version,
                    k.k,
                    k.effective_k,
                    k.positives,
                    fmt(k.precision),
                    fmt(k.recall),
                  ]) ?? [],
              )}
            />
          </Panel>
        </>
      )}
      <Qualifications />
    </>
  );
}
