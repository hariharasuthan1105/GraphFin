import { useResearch, TITLE, fmt } from "../state";
import type { Overview as OverviewData } from "../contract";
import { Metric, Panel, Notice } from "../ui";

export default function Overview() {
  const r = useResearch<OverviewData>("/overview", "Overview");

  return (
    <>
      <section className="hero">
        <div className="hero-network" aria-hidden="true">
          <svg viewBox="0 0 500 350">
            <g fill="none" stroke="#77777d" strokeWidth=".7">
              <path d="M20 220L100 100 220 50 300 180 440 80M100 100L170 260 300 180 420 300M220 50L170 260 420 300 440 80M20 220L300 180 480 220M100 100L440 80" />
            </g>
            <g fill="#f5f5f5">
              {[
                [20, 220],
                [100, 100],
                [220, 50],
                [300, 180],
                [440, 80],
                [170, 260],
                [420, 300],
                [480, 220],
              ].map(([x, y]) => (
                <rect key={x} x={x - 3} y={y - 3} width="6" height="6" />
              ))}
            </g>
          </svg>
        </div>
        <div className="hero-copy">
          <span className="eyebrow">SYSTEM / 008 — RESEARCH TERMINAL</span>
          <div className="hero-word">
            GRAPHFIN<span className="red">_</span>
          </div>
          <h1>Financial Network Intelligence</h1>
          <p>
            An interactive research platform for graph-based anomaly analysis.
            <br />
            Explore the evidence, analyze your own data, and understand its boundaries.
          </p>
          <div style={{ display: "flex", gap: "12px", marginTop: "22px", flexWrap: "wrap" }}>
            <a
              href="#/analyze"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "#b44a50",
                color: "#ffffff",
                padding: "10px 22px",
                fontWeight: 600,
                fontSize: "12px",
                letterSpacing: "0.04em",
                borderRadius: "2px",
                textDecoration: "none",
              }}
            >
              <span>↑</span> UPLOAD DATASET <span>→</span>
            </a>
            <a
              href="#/analyze"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "#171719",
                color: "#f5f5f5",
                border: "1px solid #303034",
                padding: "10px 22px",
                fontSize: "12px",
                letterSpacing: "0.04em",
                borderRadius: "2px",
                textDecoration: "none",
              }}
            >
              <span>📊</span> ANALYZE DATASET <span>→</span>
            </a>
          </div>
        </div>
        <div className="hero-foot">
          <span>GRAPH SYSTEMS / EMPIRICAL RESEARCH</span>
          <span>INTERACTIVE RESEARCH ENVIRONMENT ■</span>
        </div>
      </section>

      {/* Metrics KPI Strip matching visual specification */}
      <div className="metrics" style={{ marginBottom: "24px" }}>
        <Metric
          label="Completed runs"
          value={r.data ? fmt(r.data.completed_run_count, 0) : "0"}
          note={
            r.data
              ? `${r.data.completed_evaluation_count} method evaluations`
              : "0 method evaluations"
          }
        />
        <Metric
          label="Research methods"
          value={r.data ? fmt(r.data.available_methods.length, 0) : "0"}
          note={
            r.data && r.data.available_methods.length > 0
              ? r.data.available_methods.join(" / ")
              : "methods implemented"
          }
        />
        <Metric
          label="Network scales"
          value={r.data ? fmt(r.data.scales.length, 0) : "0"}
          note={
            r.data && r.data.scales.length > 0
              ? r.data.scales.join(" / ") + " accounts"
              : "accounts analyzed"
          }
        />
        <Metric
          label="Replay evidence"
          value="Available"
          note="Reproducible results and analysis"
        />
      </div>

      {/* Two-Column Feature Cards */}
      <div className="grid-two" style={{ marginBottom: "24px" }}>
        <Panel title="Upload your dataset" tag="01 / ANALYZE">
          <div className="panel-body">
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "16px",
                marginBottom: "16px",
              }}
            >
              <div
                style={{
                  fontSize: "28px",
                  lineHeight: 1,
                  padding: "8px",
                  background: "#171719",
                  border: "1px solid #303034",
                  borderRadius: "2px",
                }}
              >
                🗄️
              </div>
              <div>
                <strong
                  style={{
                    display: "block",
                    color: "#f5f5f5",
                    fontSize: "14px",
                    marginBottom: "4px",
                  }}
                >
                  Dataset Analysis
                </strong>
                <p style={{ margin: 0, fontSize: "12px", color: "#a6a6a6" }}>
                  Analyze financial network data with our research methods. Get
                  insights, run experiments, and explore graph-based evidence.
                </p>
              </div>
            </div>
            <a
              href="#/analyze"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "#b44a50",
                color: "#ffffff",
                padding: "10px 22px",
                fontWeight: 600,
                fontSize: "12px",
                borderRadius: "2px",
                textDecoration: "none",
                marginBottom: "12px",
              }}
            >
              <span>↑</span> UPLOAD DATASET <span>→</span>
            </a>
            <p
              className="eyebrow technical"
              style={{ margin: 0, fontSize: "10px" }}
            >
              SUPPORTS CSV, TSV, JSON • 100% IN-BROWSER CLIENT PRIVACY
            </p>
          </div>
        </Panel>

        <Panel title="Explore the research" tag="02 / SCOPE">
          <div className="panel-body">
            <p style={{ fontSize: "12px", color: "#a6a6a6", marginBottom: "16px" }}>
              Browse datasets, experiments, model comparisons, and interactive visualizations.
            </p>
            <a
              className="action-link"
              href="#/datasets"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "#171719",
                color: "#f5f5f5",
                border: "1px solid #303034",
                padding: "8px 16px",
                fontSize: "12px",
                textDecoration: "none",
                borderRadius: "2px",
              }}
            >
              VIEW RESEARCH SECTIONS <span>→</span>
            </a>
            <p className="eyebrow" style={{ marginTop: 20 }}>
              MODEL-SEED EVIDENCE /{" "}
              {r.data?.model_seed_analysis_available ? "AVAILABLE" : "READY"}
            </p>
            <p className="eyebrow">
              CREST DIAGNOSTICS /{" "}
              {r.data?.crest_diagnostics_available ? "AVAILABLE" : "READY"}
            </p>
          </div>
        </Panel>
      </div>

      {/* Dataset Inventory & Research Findings if available */}
      {r.data && (
        <>
          <div className="grid-two">
            <Panel title="Research coverage" tag="01 / DATASETS">
              {r.data.datasets.map((d) => (
                <a className="list-item" key={d.dataset_id} href={"#/datasets"}>
                  <div>
                    <strong>{d.name}</strong>
                    <small>{d.provenance_status.replaceAll("_", " ")}</small>
                  </div>
                  <code>
                    {fmt(d.accounts, 0)}{" "}
                    <span className="muted">accounts ↗</span>
                  </code>
                </a>
              ))}
            </Panel>
            <Panel title="Evidence, not assumptions" tag="02 / SCOPE">
              <div className="panel-body">
                <p>
                  Compare frozen baselines on compatible held-out populations.
                  Keep calibration, split variation and model randomness
                  distinct.
                </p>
                <a className="action-link" href="#/comparison">
                  Explore model comparison <span>↗</span>
                </a>
              </div>
            </Panel>
          </div>
          <Notice>
            IBM AML label lineage is partially verified. PaySim label provenance
            remains unresolved. CREST detection and explanation superiority have
            not been demonstrated.
          </Notice>
        </>
      )}

      <Panel title="The research project" tag="PROJECT / INFORMATION">
        <div className="panel-body">
          <p className="project-title">{TITLE}</p>
          <p>
            Reproducible experiments and transparent limitations for
            synthetic financial transaction networks. This system is not a
            certified real-world fraud-monitoring service.
          </p>
        </div>
      </Panel>
    </>
  );
}
