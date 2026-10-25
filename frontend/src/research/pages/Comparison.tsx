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
      <Heading index="04" title="Model comparison">
        Compare methods within one exact dataset, label set and held-out split.
      </Heading>
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
