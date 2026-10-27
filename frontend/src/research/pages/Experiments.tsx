import { useResearch, fmt } from "../state";
import { useState } from "react";
import type { Page_Experiment_, Experiment, Page_Ranking_ } from "../contract";
import {
  State,
  Heading,
  Panel,
  Table,
  Pager,
  Notice,
  Status,
  Hash,
} from "../ui";
import { query } from "../client";
import { useSession } from "../sessionContext";
import { generateDatasetPdfReport } from "../datasetAnalysis/reportGenerator";
function Rankings({ experiment }: { experiment: Experiment }) {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("score_desc");
  const r = useResearch<Page_Ranking_>(
    query("/experiments/" + experiment.experiment_id + "/rankings", {
      page_number: page,
      page_size: 25,
      sort,
    }),
    "Page_Ranking_",
  );
  return (
    <Panel title="Held-out account rankings" tag="25 / PAGE">
      <div className="panel-body">
        <label>
          Score ordering{" "}
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              setPage(1);
            }}
          >
            <option value="score_desc">Highest first</option>
            <option value="score_asc">Lowest first</option>
          </select>
        </label>
        <p>
          {experiment.dataset_id} · {experiment.version}. Anomaly scores are not
          fraud probabilities.
        </p>
      </div>
      {!r.data ? (
        <State {...r} />
      ) : (
        <>
          <Table
            caption="Process-local pseudonyms; diagnostic linkage unavailable across workers"
            headers={[
              "Rank",
              "Account token",
              "Anomaly score",
              "Diagnostic availability",
              "Graph lens",
            ]}
            rows={r.data.items.map((x) => [
              x.rank,
              x.account_token,
              fmt(x.anomaly_score, 8),
              "Not linked by this API",
              sort === "score_desc" &&
              x.rank <= 20 &&
              experiment.split_seed === 42 &&
              experiment.model_seed === 42 ? (
                <a
                  key="graph"
                  href={
                    "#/graph?" +
                    new URLSearchParams({
                      dataset_id: experiment.dataset_id,
                      experiment_id: experiment.experiment_id,
                      rank: String(x.rank),
                    })
                  }
                >
                  Open approved graph →
                </a>
              ) : (
                "Available for supported top20 descending ranks at split42/model42."
              ),
            ])}
          />
          <Pager page={page} setPage={setPage} size={25} total={r.data.total} />
        </>
      )}
    </Panel>
  );
}
function Detail({ id }: { id: string }) {
  const [tab, setTab] = useState("detail");
  const suffix =
    tab === "metrics" ? "/metrics" : tab === "provenance" ? "/provenance" : "";
  const r = useResearch<Experiment>(
    "/experiments/" + id + suffix,
    "Experiment",
  );
  return (
    <>
      <div className="filters" role="group" aria-label="Experiment sections">
        {["detail", "metrics", "provenance", "rankings"].map((x) => (
          <button key={x} onClick={() => setTab(x)} aria-pressed={x === tab}>
            {x}
          </button>
        ))}
      </div>
      {!r.data ? (
        <State {...r} />
      ) : (
        <>
          <Panel
            title={r.data.method + " / " + r.data.tier}
            tag={r.data.status}
          >
            <div className="panel-body">
              <Status value={r.data} />
              <p>
                <code>{r.data.experiment_id}</code>
              </p>
            </div>
            <dl className="definition">
              <dt>Algorithm version</dt>
              <dd>{r.data.version}</dd>
              <dt>Dataset</dt>
              <dd>{r.data.dataset_id}</dd>
              <dt>Features</dt>
              <dd>
                {(r.data.feature_names ?? []).join(", ") || "Unavailable"}
              </dd>
              <dt>Split / model seed</dt>
              <dd>
                {r.data.split_seed ?? "Unavailable"} /{" "}
                {r.data.model_seed ?? "Unavailable"}
              </dd>
              {(
                [
                  "artifact_sha256",
                  "dataset_sha256",
                  "label_sha256",
                  "train_sha256",
                  "test_sha256",
                  "population_identity",
                ] as const
              ).map((k) => (
                <div style={{ display: "contents" }} key={k}>
                  <dt>{k.replaceAll("_", " ")}</dt>
                  <dd>
                    <Hash key="hash" value={r.data![k]} />
                  </dd>
                </div>
              ))}
            </dl>
            {r.data.metrics && (
              <Table
                caption="Stored held-out evaluation"
                headers={[
                  "Accounts",
                  "Positives",
                  "AP",
                  "ROC-AUC",
                  "Confidence interval",
                ]}
                rows={[
                  [
                    fmt(r.data.metrics.count, 0),
                    fmt(r.data.metrics.positives, 0),
                    fmt(r.data.metrics.average_precision, 8),
                    fmt(r.data.metrics.roc_auc, 8),
                    "Unavailable — not supplied",
                  ],
                ]}
              />
            )}
            <div className="panel-body">
              {(r.data.limitations ?? []).map((x) => (
                <p key={x}>{x}</p>
              ))}
              {r.data.status !== "verified" && (
                <Notice>
                  Historical or incomplete record. Comparable detector metrics
                  are unavailable.
                </Notice>
              )}
            </div>
          </Panel>
          {tab === "rankings" && r.data.status === "verified" && (
            <Rankings key={id} experiment={r.data} />
          )}
        </>
      )}
    </>
  );
}
export default function Experiments() {
  const { activeSession, backendModel, backendStatus } = useSession();
  const [tier, setTier] = useState(() => (activeSession ? "runtime-active" : "ibm-5k"));
  const [method, setMethod] = useState("");
  const [page, setPage] = useState(1);
  const [id, setId] = useState<string>();
  const isRuntime = tier === "runtime-active" && activeSession;

  const r = useResearch<Page_Experiment_>(
    query("/experiments", {
      dataset_id: isRuntime ? undefined : tier || undefined,
      method: method || undefined,
      page_number: page,
      page_size: 10,
    }),
    "Page_Experiment_",
  );
  return (
    <>
      <Heading index="05" title="Experiment registry">
        Versioned methods. Frozen populations and active runtime dataset model executions.
      </Heading>

      <div className="filters">
        <label>
          Dataset scope
          <select
            value={tier}
            onChange={(e) => {
              setTier(e.target.value);
              setPage(1);
              setId(undefined);
            }}
          >
            {activeSession && (
              <option value="runtime-active">
                ✦ Active Session ({activeSession.summary.datasetName})
              </option>
            )}
            <option value="ibm-5k">IBM AML / 5K (Historical)</option>
            <option value="ibm-50k">IBM AML / ~50K (Historical)</option>
            <option value="">All Historical Benchmarks (86 runs)</option>
          </select>
        </label>
        {!isRuntime && (
          <label>
            Method
            <select
              value={method}
              onChange={(e) => {
                setMethod(e.target.value);
                setPage(1);
                setId(undefined);
              }}
            >
              <option value="">All methods</option>
              {[
                "E0",
                "E1",
                "E2",
                "E3",
                "E4",
                "E5",
                "E6_BASE",
                "E6_CREST",
                "E0-E4",
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      {isRuntime ? (
        <>
          <Panel
            title={`Active Session Runtime Model: ${activeSession.backendModel || backendModel}`}
            tag={
              (activeSession.backendStatus === "ml_verified" || activeSession.backendStatus === "synced" || backendStatus === "ml_verified")
                ? "BACKEND / TRAINED"
                : "CLIENT / HEURISTIC"
            }
          >
            <div className="panel-body">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                  gap: "12px",
                  marginBottom: "16px",
                }}
              >
                <div>
                  <span style={{ fontSize: "10px", color: "#77777d", display: "block" }}>DATASET ID</span>
                  <strong style={{ fontSize: "13px", color: "#f5f5f5" }}>{activeSession.summary.datasetName}</strong>
                </div>
                <div>
                  <span style={{ fontSize: "10px", color: "#77777d", display: "block" }}>MODEL ARCHITECTURE</span>
                  <strong style={{ fontSize: "13px", color: "#f5f5f5" }}>{activeSession.backendModel || backendModel}</strong>
                </div>
                <div>
                  <span style={{ fontSize: "10px", color: "#77777d", display: "block" }}>TOTAL ACCOUNTS</span>
                  <strong style={{ fontSize: "13px", color: "#f5f5f5" }}>{activeSession.accounts.length} scored</strong>
                </div>
                <div>
                  <span style={{ fontSize: "10px", color: "#77777d", display: "block" }}>FLAGGED ANOMALIES</span>
                  <strong style={{ fontSize: "13px", color: "#c04b52" }}>{activeSession.summary.suspiciousAccountCount} accounts</strong>
                </div>
              </div>

              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center" }}>
                <button
                  type="button"
                  onClick={() => generateDatasetPdfReport(activeSession, activeSession.backendModel || backendModel)}
                  style={{
                    background: "#842d35",
                    color: "#ffffff",
                    border: "1px solid #b44a50",
                    padding: "8px 16px",
                    borderRadius: "4px",
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  📄 Download Audit Report (PDF)
                </button>
                <a
                  href="#/graph"
                  style={{
                    background: "#171719",
                    color: "#f5f5f5",
                    border: "1px solid #303034",
                    padding: "8px 16px",
                    borderRadius: "4px",
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: "11px",
                    textDecoration: "none",
                  }}
                >
                  Inspect in Graph Explorer →
                </a>
                <a
                  href="#/analyze"
                  style={{
                    background: "#171719",
                    color: "#f5f5f5",
                    border: "1px solid #303034",
                    padding: "8px 16px",
                    borderRadius: "4px",
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: "11px",
                    textDecoration: "none",
                  }}
                >
                  Configure Features in Workbench →
                </a>
              </div>
            </div>

            <Table
              caption="Active dataset continuous account anomaly rankings"
              headers={["Rank", "Account ID", "Anomaly score", "In / Out degree", "Net flow", "Flagged patterns", "Graph lens"]}
              rows={activeSession.accounts.slice(0, 25).map((acc, idx) => [
                idx + 1,
                acc.id,
                acc.anomalyScore.toFixed(4),
                `${acc.inDegree} / ${acc.outDegree}`,
                `$${acc.netFlow.toLocaleString("en-US", { maximumFractionDigits: 0 })}`,
                acc.patterns.length > 0 ? acc.patterns.join(", ") : "Normal Flow",
                <a key="lens" href={`#/graph`}>Open in graph →</a>,
              ])}
            />
          </Panel>
          <Notice>
            Scientific Note: Active runtime evaluation scores unstandardized custom transaction data. The 86 historical registered experiments cataloged under the historical scope are frozen benchmark models (E0–E6 Isolation Forest with 19 engineered features) trained on standardized splits.
          </Notice>
        </>
      ) : (
        <>
          {!r.data ? (
            <State {...r} />
          ) : (
            <Panel title="Saved experiments" tag="IMMUTABLE / ARTIFACTS">
              <Table
                caption="Select an experiment to inspect metrics, identities and rankings"
                headers={["Experiment", "Version", "Split", "AP", "Status"]}
                rows={r.data.items.map((x) => [
                  <button
                    key="select"
                    onClick={() => setId(x.experiment_id)}
                    aria-pressed={id === x.experiment_id}
                  >
                    {x.experiment_id}
                  </button>,
                  x.version,
                  x.split_seed ?? "Unavailable",
                  fmt(x.metrics?.average_precision, 6),
                  x.status,
                ])}
              />
              <Pager page={page} setPage={setPage} size={10} total={r.data.total} />
            </Panel>
          )}
          {id && <Detail key={id} id={id} />}
        </>
      )}
    </>
  );
}
