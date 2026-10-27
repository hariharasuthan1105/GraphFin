import { useResearch, TITLE, fmt } from "../state";
import type { Overview as OverviewData } from "../contract";
import { Metric, Panel, Notice } from "../ui";
import { useSession } from "../sessionContext";

export default function Overview() {
  const r = useResearch<OverviewData>("/overview", "Overview");
  const { appMode, setAppMode, activeSession, loadBenchmarkSample } = useSession();

  return (
    <>
      {/* Hero Header */}
      <section className="hero">
        <div className="hero-network" aria-hidden="true">
          <svg viewBox="0 0 500 350">
            <g fill="none" stroke="#334155" strokeWidth=".8">
              <path d="M20 220L100 100 220 50 300 180 440 80M100 100L170 260 300 180 420 300M220 50L170 260 420 300 440 80M20 220L300 180 480 220M100 100L440 80" />
            </g>
            <g fill="#b44a50">
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
                <circle key={x} cx={x} cy={y} r="3.5" />
              ))}
            </g>
          </svg>
        </div>
        <div className="hero-copy">
          <span className="eyebrow">SYSTEM / 008 — ADVANCED GRAPH INTELLIGENCE</span>
          <div className="hero-word">
            GRAPHFIN<span style={{ color: "#c04b52" }}>_</span>
          </div>
          <h1>Financial Network Intelligence</h1>
          <p>
            An interactive research platform for graph-based anomaly analysis.
            <br />
            Explore verified academic evidence, analyze your own transaction data, and explore simulated topologies.
          </p>

          {/* Mode Switcher Buttons */}
          <div style={{ display: "flex", gap: "10px", marginTop: "20px", flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => setAppMode("interactive")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: appMode === "interactive" ? "#842d35" : "#101012",
                color: appMode === "interactive" ? "#ffffff" : "#a6a6a6",
                border: appMode === "interactive" ? "1px solid #b44a50" : "1px solid #303034",
                padding: "8px 18px",
                fontWeight: 600,
                fontSize: "12px",
                fontFamily: "IBM Plex Mono, monospace",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              <span>✦</span> INTERACTIVE ANALYSIS MODE
            </button>

            <button
              type="button"
              onClick={() => setAppMode("research")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: appMode === "research" ? "#842d35" : "#101012",
                color: appMode === "research" ? "#ffffff" : "#a6a6a6",
                border: appMode === "research" ? "1px solid #b44a50" : "1px solid #303034",
                padding: "8px 18px",
                fontWeight: 600,
                fontSize: "12px",
                fontFamily: "IBM Plex Mono, monospace",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              <span>⚲</span> RESEARCH EVIDENCE MODE
            </button>
          </div>
        </div>
        <div className="hero-foot">
          <span>GRAPH SYSTEMS / EMPIRICAL RESEARCH</span>
          <span>
            {appMode === "interactive"
              ? "INTERACTIVE CLIENT ANALYSIS ACTIVE ■"
              : "VERIFIED HISTORICAL EVIDENCE ■"}
          </span>
        </div>
      </section>

      {/* Mode-Dependent KPI Strip */}
      {appMode === "interactive" ? (
        activeSession ? (
          <div className="metrics" style={{ marginBottom: "24px" }}>
            <Metric
              label="Active accounts"
              value={fmt(activeSession.summary.uniqueAccounts, 0)}
              note={`${activeSession.summary.uniqueEdges} directed transfer edges`}
            />
            <Metric
              label="Total transactions"
              value={fmt(activeSession.summary.totalTransactions, 0)}
              note={`$${activeSession.summary.totalVolume.toLocaleString("en-US", {
                maximumFractionDigits: 2,
              })} total volume`}
            />
            <Metric
              label="Flagged anomalies"
              value={fmt(activeSession.summary.suspiciousAccountCount, 0)}
              note="Score ≥ 0.45 or pattern trigger"
            />
            <Metric
              label="Graph patterns"
              value={fmt(
                activeSession.summary.patternsDetected.fanOutCount +
                  activeSession.summary.patternsDetected.fanInCount +
                  activeSession.summary.patternsDetected.cycleCount +
                  activeSession.summary.patternsDetected.volumeOutlierCount,
                0,
              )}
              note={`${activeSession.summary.patternsDetected.fanOutCount} Fan-out · ${activeSession.summary.patternsDetected.fanInCount} Fan-in · ${activeSession.summary.patternsDetected.cycleCount} Cycle`}
            />
          </div>
        ) : (
          <div
            style={{
              background: "#0c0e14",
              border: "1px dashed #283144",
              borderRadius: "6px",
              padding: "24px",
              textAlign: "center",
              marginBottom: "24px",
            }}
          >
            <h3 style={{ fontSize: "15px", color: "#f8fafc", margin: "0 0 6px 0" }}>
              Interactive Analysis Session Ready
            </h3>
            <p style={{ fontSize: "12px", color: "#94a3b8", margin: "0 0 16px 0" }}>
              Upload your own transaction dataset (CSV, TSV, JSON) or load the synthetic benchmark sample.
            </p>
            <div style={{ display: "flex", justifyContent: "center", gap: "10px" }}>
              <button
                type="button"
                onClick={loadBenchmarkSample}
                style={{
                  background: "#b44a50",
                  color: "#ffffff",
                  border: "1px solid #842d35",
                  padding: "7px 16px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontFamily: "IBM Plex Mono, monospace",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                ✦ Load Benchmark Sample Dataset
              </button>
              <a
                href="#/analyze"
                style={{
                  background: "#171719",
                  color: "#f5f5f5",
                  border: "1px solid #303034",
                  padding: "7px 16px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontFamily: "IBM Plex Mono, monospace",
                  textDecoration: "none",
                }}
              >
                Go to Upload Workbench →
              </a>
            </div>
          </div>
        )
      ) : (
        /* Research Evidence Mode KPIs */
        <div className="metrics" style={{ marginBottom: "24px" }}>
          <Metric
            label="Completed runs"
            value={
              r.data
                ? fmt(r.data.completed_run_count, 0)
                : r.error
                ? "Unavailable"
                : "Loading..."
            }
            note={
              r.data
                ? `${r.data.completed_evaluation_count} method evaluations`
                : r.error
                ? "Evidence not loaded"
                : "Verifying research catalog..."
            }
          />
          <Metric
            label="Research methods"
            value={
              r.data
                ? fmt(r.data.available_methods.length, 0)
                : r.error
                ? "Unavailable"
                : "Loading..."
            }
            note={
              r.data && r.data.available_methods.length > 0
                ? r.data.available_methods.join(" / ")
                : r.error
                ? "Evidence not loaded"
                : "Scanning method benchmarks..."
            }
          />
          <Metric
            label="Network scales"
            value={
              r.data
                ? fmt(r.data.scales.length, 0)
                : r.error
                ? "Unavailable"
                : "Loading..."
            }
            note={
              r.data && r.data.scales.length > 0
                ? r.data.scales.join(" / ") + " accounts"
                : r.error
                ? "Evidence not loaded"
                : "Scanning scale benchmarks..."
            }
          />
          <Metric
            label="Replay evidence"
            value={
              r.data
                ? r.data.reproducibility_available
                  ? "Available"
                  : "Unverified"
                : r.error
                ? "Unavailable"
                : "Loading..."
            }
            note="Reproducible results and analysis"
          />
        </div>
      )}

      {/* Feature Navigation Cards */}
      <div className="grid-two" style={{ marginBottom: "24px" }}>
        <Panel title="Interactive Analysis & Graph" tag="01 / WORKBENCH">
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
                  fontSize: "24px",
                  lineHeight: 1,
                  padding: "8px",
                  background: "#11141c",
                  border: "1px solid #1e2434",
                  borderRadius: "4px",
                }}
              >
                ◈
              </div>
              <div>
                <strong
                  style={{
                    display: "block",
                    color: "#f8fafc",
                    fontSize: "14px",
                    marginBottom: "4px",
                  }}
                >
                  Interactive Graph & Dataset Workbench
                </strong>
                <p style={{ margin: 0, fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
                  Parse client-side transaction logs, build directed networks, compute anomaly scores,
                  and inspect suspicious flow motifs in real-time.
                </p>
              </div>
            </div>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <a
                href="#/analyze"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#b44a50",
                  color: "#ffffff",
                  padding: "8px 16px",
                  fontWeight: 600,
                  fontSize: "11px",
                  fontFamily: "IBM Plex Mono, monospace",
                  borderRadius: "3px",
                  textDecoration: "none",
                }}
              >
                ANALYZE DATASET →
              </a>
              <a
                href="#/graph"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#171719",
                  color: "#f5f5f5",
                  border: "1px solid #303034",
                  padding: "8px 16px",
                  fontSize: "11px",
                  fontFamily: "IBM Plex Mono, monospace",
                  borderRadius: "3px",
                  textDecoration: "none",
                }}
              >
                GRAPH EXPLORER →
              </a>
            </div>
            <span
              style={{
                display: "block",
                marginTop: "12px",
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: "10px",
                color: "#64748b",
              }}
            >
              CSV, TSV, JSON · 100% IN-BROWSER CLIENT PRIVACY
            </span>
          </div>
        </Panel>

        <Panel title="Historical Research Catalog" tag="02 / EVIDENCE">
          <div className="panel-body">
            <p style={{ fontSize: "12px", color: "#94a3b8", lineHeight: 1.6, margin: "0 0 16px 0" }}>
              Access verified experimental evaluations, baseline model comparisons (E0–E6),
              multi-seed stability analyses, and CREST counterparty explanations computed on
              standardized financial benchmark splits.
            </p>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <a
                href="#/experiments"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#11141c",
                  color: "#e2e8f0",
                  border: "1px solid #232a3b",
                  padding: "8px 14px",
                  fontSize: "11px",
                  fontFamily: "IBM Plex Mono, monospace",
                  borderRadius: "3px",
                  textDecoration: "none",
                }}
              >
                EXPERIMENT REGISTRY →
              </a>
              <a
                href="#/comparison"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#11141c",
                  color: "#e2e8f0",
                  border: "1px solid #232a3b",
                  padding: "8px 14px",
                  fontSize: "11px",
                  fontFamily: "IBM Plex Mono, monospace",
                  borderRadius: "3px",
                  textDecoration: "none",
                }}
              >
                MODEL COMPARISON →
              </a>
              <a
                href="#/datasets"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#11141c",
                  color: "#e2e8f0",
                  border: "1px solid #232a3b",
                  padding: "8px 14px",
                  fontSize: "11px",
                  fontFamily: "IBM Plex Mono, monospace",
                  borderRadius: "3px",
                  textDecoration: "none",
                }}
              >
                RESEARCH DATASETS →
              </a>
            </div>
            <span
              style={{
                display: "block",
                marginTop: "12px",
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: "10px",
                color: "#64748b",
              }}
            >
              86 VERIFIED EXPERIMENTS · IBM AML & PAYSIM PROVENANCE
            </span>
          </div>
        </Panel>
      </div>

      {/* Verified Research Datasets Cards */}
      {r.data?.datasets && r.data.datasets.length > 0 && (
        <div style={{ marginBottom: "24px" }}>
          <div
            style={{
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: "11px",
              color: "#64748b",
              marginBottom: "8px",
              letterSpacing: "0.06em",
            }}
          >
            RESEARCH BENCHMARK DATASETS ({r.data.datasets.length})
          </div>
          <div className="grid-three">
            {r.data.datasets.map((d) => (
              <Panel key={d.dataset_id} title={d.name} tag={d.tier.toUpperCase()}>
                <div className="panel-body">
                  <div
                    style={{
                      fontFamily: "IBM Plex Mono, monospace",
                      fontSize: "11px",
                      color: "#94a3b8",
                      marginBottom: "10px",
                    }}
                  >
                    <div>
                      Accounts: <b style={{ color: "#f8fafc" }}>{fmt(d.accounts, 0)}</b>
                    </div>
                    <div>
                      Transactions:{" "}
                      <b style={{ color: "#f8fafc" }}>
                        {d.transactions ? fmt(d.transactions, 0) : "Unavailable"}
                      </b>
                    </div>
                    <div>
                      Provenance:{" "}
                      <span
                        style={{
                          color:
                            d.provenance_status === "partially_verified"
                              ? "#f5f5f5"
                              : "#a6a6a6",
                        }}
                      >
                        {d.provenance_status}
                      </span>
                    </div>
                  </div>
                  <p style={{ margin: "0 0 12px 0", fontSize: "11px", color: "#77777d", lineHeight: 1.4 }}>
                    {d.time_semantics}
                  </p>
                  <a
                    href="#/datasets"
                    style={{
                      fontSize: "11px",
                      fontFamily: "IBM Plex Mono, monospace",
                      color: "#c04b52",
                      textDecoration: "none",
                    }}
                  >
                    View Dataset Details →
                  </a>
                </div>
              </Panel>
            ))}
          </div>
        </div>
      )}

      {/* Scientific Notice */}
      <Notice>
        <strong style={{ display: "block", marginBottom: "4px" }}>
          Scientific Integrity & Dual-Mode Architecture
        </strong>
        <p style={{ margin: 0, fontSize: "12px", lineHeight: 1.5 }}>
          GraphFin cleanly separates <strong>Research Evidence Mode</strong> (displaying frozen,
          verifiable benchmark metrics from IBM AML and PaySim without disclosing raw confidential
          account numbers) from <strong>Interactive Analysis Mode</strong> (executing deterministic
          client-side graph feature extraction and structural anomaly detection on uploaded datasets).
          Heuristic graph scores are not misrepresented as supervised ML classifications.
        </p>
      </Notice>
    </>
  );
}
