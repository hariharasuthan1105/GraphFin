import { useResearch, fmt } from "../state";
import { useState } from "react";
import type { Page_Experiment_, ModelSeeds } from "../contract";
import { State, Heading, Panel, Table, Tier, Chart, Notice, Qualifications } from "../ui";
import { query } from "../client";
function summary(values: number[]) {
  const n = values.length;
  if (!n) return null;
  const mean = values.reduce((a, b) => a + b, 0) / n;
  return {
    mean,
    sd:
      n > 1
        ? Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1))
        : null,
    min: Math.min(...values),
    max: Math.max(...values),
  };
}
function Splits({ tier, method }: { tier: string; method: string }) {
  const r = useResearch<Page_Experiment_>(
    query("/experiments", {
      dataset_id: tier,
      method,
      model_seed: 42,
      page_size: 100,
    }),
    "Page_Experiment_",
  );
  if (!r.data) return <State {...r} />;
  const rows = r.data.items
    .filter((x) => x.status === "verified")
    .sort((a, b) => (a.split_seed ?? 0) - (b.split_seed ?? 0));
  const stats = summary(
    rows
      .map((x) => x.metrics?.average_precision)
      .filter((x): x is number => x != null),
  );
  return (
    <>
      <Panel title="Six-split analysis" tag="MODEL SEED / 42">
        <Chart
          labels={rows.map((x) => "S" + x.split_seed)}
          values={rows.map((x) => x.metrics?.average_precision)}
          title={`${method} / Average Precision`}
        />
        <Table
          caption="Split runs are not independent datasets"
          headers={["Split", "Population", "Positive", "AP", "ROC-AUC"]}
          rows={rows.map((x) => [
            x.split_seed,
            fmt(x.metrics?.count, 0),
            fmt(x.metrics?.positives, 0),
            fmt(x.metrics?.average_precision, 8),
            fmt(x.metrics?.roc_auc, 8),
          ])}
        />
      </Panel>
      {stats && (
        <Notice>
          Derived from {rows.length} stored AP values: mean {fmt(stats.mean, 8)}{" "}
          · sample SD {fmt(stats.sd, 8)} · min {fmt(stats.min, 8)} · max{" "}
          {fmt(stats.max, 8)}. SD is not a confidence interval.
        </Notice>
      )}
    </>
  );
}
function Models({ tier, method }: { tier: string; method: string }) {
  const r = useResearch<ModelSeeds>(
    query("/model-seeds", { dataset_id: tier, method }),
    "ModelSeeds",
  );
  if (!r.data) return <State {...r} />;
  return (
    <>
      <Panel title="Model-seed sensitivity" tag="FIXED SPLIT / 42">
        <Chart
          labels={r.data.runs.map((x) => "M" + x.model_seed)}
          values={r.data.runs.map((x) => x.metrics.average_precision)}
          title={`${method} / Average Precision`}
        />
        <Table
          caption="Three model seeds; conditional same-dataset evidence"
          headers={["Split", "Model seed", "AP", "ROC-AUC", "P@10"]}
          rows={r.data.runs.map((x) => [
            x.split_seed,
            x.model_seed,
            fmt(x.metrics.average_precision, 8),
            fmt(x.metrics.roc_auc, 8),
            fmt(x.metrics.retrieval?.find((k) => k.k === 10)?.precision),
          ])}
        />
        <Table
          caption="Saved descriptive variability; not confidence intervals"
          headers={["Mean AP", "Sample SD", "Minimum", "Maximum"]}
          rows={r.data.summaries.map((x) => [
            fmt(x.mean_ap, 8),
            fmt(x.sample_sd_ap, 8),
            fmt(x.minimum_ap, 8),
            fmt(x.maximum_ap, 8),
          ])}
        />
      </Panel>
      <Panel title="Ranking overlap">
        <Table
          caption="Stored pairwise stability on the fixed split"
          headers={[
            "Model pair",
            "Ordinal Spearman",
            "K",
            "Overlap",
            "Jaccard",
          ]}
          rows={r.data.pairs.flatMap((x) =>
            x.top_k.map((k) => [
              `${x.first_model_seed} / ${x.second_model_seed}`,
              fmt(x.spearman_ordinal),
              k.k,
              fmt(k.overlap),
              fmt(k.jaccard),
            ]),
          )}
        />
      </Panel>
      <Notice>
        Three model seeds do not establish general robustness. High overall rank
        correlation does not guarantee stable rare-positive retrieval.
      </Notice>
    </>
  );
}
export default function Seeds() {
  const [mode, setMode] = useState("split");
  const [tier, setTier] = useState("ibm-5k");
  const [method, setMethod] = useState("E4");
  return (
    <>
      <Heading index="05" title="Seed analysis">
        Separate split variability from model randomness.
      </Heading>
      <Qualifications />
      <div className="filters">
        <label>
          Evidence axis
          <select
            value={mode}
            onChange={(e) => {
              setMode(e.target.value);
              setMethod("E4");
            }}
          >
            <option value="split">Split seeds / six runs</option>
            <option value="model">Model seeds / three runs</option>
          </select>
        </label>
        <Tier value={tier} onChange={setTier} />
        <label>
          Method
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            {(mode === "model"
              ? ["E1", "E4"]
              : ["E0", "E1", "E2", "E3", "E4", "E5", "E6_BASE"]
            ).map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
      </div>
      {mode === "split" ? (
        <Splits tier={tier} method={method} />
      ) : (
        <Models tier={tier} method={method} />
      )}
    </>
  );
}
