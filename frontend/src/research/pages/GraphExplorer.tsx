import { useState, useMemo } from "react";
import { Heading, Qualifications } from "../ui";
import { fmt } from "../state";
import { useGraphCatalog } from "../graph/client";
import { useSession } from "../sessionContext";
import {
  SIMULATED_PRESETS_META,
  getSimulatedPresetResult,
} from "../graph/simulatedData";
import AnalysisGraphCanvas from "../datasetAnalysis/AnalysisGraphCanvas";
import type { AccountNode } from "../datasetAnalysis/types";
import { DatasetReportDownload } from "../DatasetReportDownload";

export default function GraphExplorer() {
  const {
    activeSession,
    graphMode,
    setGraphMode,
    simulatedPreset,
    setSimulatedPreset,
    loadBenchmarkSample,
  } = useSession();

  const metadata = useGraphCatalog();
  const [researchDataset, setResearchDataset] = useState("ibm-5k");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [patternFilter, setPatternFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Determine active graph data based on current graphMode
  const activeGraphResult = useMemo(() => {
    if (graphMode === "uploaded" && activeSession) {
      return activeSession;
    }
    if (graphMode === "simulated") {
      return getSimulatedPresetResult(simulatedPreset);
    }
    return null;
  }, [graphMode, activeSession, simulatedPreset]);

  // Accounts list with search & pattern filters
  const filteredAccounts = useMemo(() => {
    if (!activeGraphResult) return [];
    return activeGraphResult.accounts.filter((acc) => {
      if (searchQuery.trim() && !acc.id.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      if (patternFilter === "ALL") return true;
      if (patternFilter === "HIGH_RISK") return acc.anomalyScore >= 0.7;
      if (patternFilter === "LOW_RISK") return acc.anomalyScore < 0.2;
      return acc.patterns.includes(patternFilter as any);
    });
  }, [activeGraphResult, searchQuery, patternFilter]);

  // Selected account entity for Inspector
  const selectedAccount: AccountNode | null = useMemo(() => {
    if (!activeGraphResult) return null;
    if (selectedNodeId) {
      const found = activeGraphResult.accounts.find((a) => a.id === selectedNodeId);
      if (found) return found;
    }
    // Default to the first anomaly or first account
    return activeGraphResult.topAnomalies[0] || activeGraphResult.accounts[0] || null;
  }, [activeGraphResult, selectedNodeId]);

  const dsMeta = metadata.data?.datasets.find((x) => x.dataset_id === researchDataset);

  return (
    <div className="research-page graph-explorer-page">
      <Heading index="04" title="Transaction network graph explorer">
        Interactive directed transaction graph exploration. Examine topology structures, fan-in/fan-out motifs, circular flow patterns, and deep account-level flow metrics.
      </Heading>

      <Qualifications />

      {/* Primary Graph Mode Switcher */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          background: "#0c0e14",
          border: "1px solid #1c2230",
          borderRadius: "6px",
          padding: "8px 12px",
          marginBottom: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
          <span
            style={{
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: "10px",
              color: "#64748b",
              marginRight: "6px",
              letterSpacing: "0.08em",
            }}
          >
            GRAPH SOURCE:
          </span>

          <button
            type="button"
            onClick={() => setGraphMode("uploaded")}
            style={{
              background: graphMode === "uploaded" ? "#162238" : "transparent",
              color: graphMode === "uploaded" ? "#38bdf8" : "#94a3b8",
              border: graphMode === "uploaded" ? "1px solid #0284c7" : "1px solid #232a3b",
              borderRadius: "4px",
              padding: "6px 12px",
              fontSize: "11px",
              fontFamily: "IBM Plex Mono, monospace",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            ✦ Uploaded Dataset {activeSession ? `(${activeSession.accounts.length})` : ""}
          </button>

          <button
            type="button"
            onClick={() => setGraphMode("simulated")}
            style={{
              background: graphMode === "simulated" ? "#221c38" : "transparent",
              color: graphMode === "simulated" ? "#c084fc" : "#94a3b8",
              border: graphMode === "simulated" ? "1px solid #9333ea" : "1px solid #232a3b",
              borderRadius: "4px",
              padding: "6px 12px",
              fontSize: "11px",
              fontFamily: "IBM Plex Mono, monospace",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            ◈ Simulated Demo Graph
          </button>

          <button
            type="button"
            onClick={() => setGraphMode("research")}
            style={{
              background: graphMode === "research" ? "#1a221f" : "transparent",
              color: graphMode === "research" ? "#2dd4bf" : "#94a3b8",
              border: graphMode === "research" ? "1px solid #0d9488" : "1px solid #232a3b",
              borderRadius: "4px",
              padding: "6px 12px",
              fontSize: "11px",
              fontFamily: "IBM Plex Mono, monospace",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            ⚲ Historical Research Catalog
          </button>
        </div>

        {/* Current status pill */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {graphMode === "uploaded" && (
            <span
              style={{
                fontSize: "10px",
                fontFamily: "IBM Plex Mono, monospace",
                color: activeSession ? "#38bdf8" : "#f59e0b",
                padding: "3px 8px",
                background: "#0f172a",
                border: "1px solid #1e293b",
                borderRadius: "3px",
              }}
            >
              {activeSession ? `● Active: ${activeSession.summary.datasetName}` : "○ No dataset loaded"}
            </span>
          )}

          {graphMode === "simulated" && (
            <span
              style={{
                fontSize: "10px",
                fontFamily: "IBM Plex Mono, monospace",
                color: "#c084fc",
                padding: "3px 8px",
                background: "#1c142c",
                border: "1px solid #3b2164",
                borderRadius: "3px",
              }}
            >
              ◈ SIMULATED SHOWCASE (NON-REAL DATA)
            </span>
          )}

          {graphMode === "research" && (
            <span
              style={{
                fontSize: "10px",
                fontFamily: "IBM Plex Mono, monospace",
                color: "#2dd4bf",
                padding: "3px 8px",
                background: "#0a1f1d",
                border: "1px solid #134e48",
                borderRadius: "3px",
              }}
            >
              ⚲ HISTORICAL CATALOG
            </span>
          )}
        </div>
      </div>

      {/* Simulated Preset Bar (if in simulated mode) */}
      {graphMode === "simulated" && (
        <div
          style={{
            background: "#090a0f",
            border: "1px solid #1c2130",
            borderRadius: "6px",
            padding: "12px 14px",
            marginBottom: "16px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "10px",
              flexWrap: "wrap",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {(Object.keys(SIMULATED_PRESETS_META) as (keyof typeof SIMULATED_PRESETS_META)[]).map(
                (key) => {
                  const meta = SIMULATED_PRESETS_META[key];
                  const isSelected = simulatedPreset === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => {
                        setSimulatedPreset(key);
                        setSelectedNodeId(null);
                      }}
                      style={{
                        background: isSelected ? "#2a1b42" : "#11141c",
                        color: isSelected ? "#e9d5ff" : "#94a3b8",
                        border: isSelected ? "1px solid #a855f7" : "1px solid #202738",
                        borderRadius: "4px",
                        padding: "5px 10px",
                        fontSize: "11px",
                        fontFamily: "IBM Plex Mono, monospace",
                        cursor: "pointer",
                      }}
                    >
                      {meta.title}
                    </button>
                  );
                },
              )}
            </div>

            <span
              style={{
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: "11px",
                color: "#94a3b8",
              }}
            >
              Volume:{" "}
              <b style={{ color: "#f8fafc" }}>
                {SIMULATED_PRESETS_META[simulatedPreset].totalVolumeFormatted}
              </b>
            </span>
          </div>

          <p style={{ margin: 0, fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
            {SIMULATED_PRESETS_META[simulatedPreset].description}
          </p>
        </div>
      )}

      {/* Historical Research Mode Topology Unavailable Card */}
      {graphMode === "research" && (
        <div
          style={{
            background: "#0c0e14",
            border: "1px solid #232938",
            borderRadius: "6px",
            padding: "20px",
            marginBottom: "20px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "10px",
              marginBottom: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <label style={{ fontSize: "12px", color: "#94a3b8" }}>
                Select Dataset:
                <select
                  value={researchDataset}
                  onChange={(e) => setResearchDataset(e.target.value)}
                  style={{
                    marginLeft: "8px",
                    background: "#121622",
                    color: "#f8fafc",
                    border: "1px solid #2a344a",
                    padding: "4px 8px",
                    borderRadius: "4px",
                    fontFamily: "IBM Plex Mono, monospace",
                  }}
                >
                  <option value="ibm-5k">IBM AML 5k (5,000 accounts)</option>
                  <option value="ibm-50k">IBM AML 50k (49,992 accounts)</option>
                  <option value="paysim">PaySim (547,686 accounts)</option>
                </select>
              </label>
            </div>

            <span
              style={{
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: "10px",
                color: "#f59e0b",
                padding: "3px 8px",
                background: "#241808",
                border: "1px solid #452c08",
                borderRadius: "3px",
              }}
            >
              TOPOLOGY RESTRICTED BY RESEARCH SAFEGUARDS
            </span>
          </div>

          <div
            style={{
              background: "#08090d",
              border: "1px dashed #283144",
              borderRadius: "6px",
              padding: "24px",
              textAlign: "center",
            }}
          >
            <h3 style={{ fontSize: "16px", color: "#f8fafc", margin: "0 0 8px 0" }}>
              {dsMeta?.name ?? researchDataset} — Aggregate Evidence Validated
            </h3>
            <p
              style={{
                fontSize: "13px",
                color: "#94a3b8",
                maxWidth: "680px",
                margin: "0 auto 16px auto",
                lineHeight: 1.6,
              }}
            >
              Raw transaction graphs for IBM AML and PaySim contain proprietary or unredacted
              account identifiers that are intentionally excluded from the public deployment. All
              numerical benchmarks, model evaluations (E0–E6), and seed stability metrics are fully
              verified.
            </p>

            <div
              style={{
                display: "flex",
                justifyContent: "center",
                gap: "12px",
                flexWrap: "wrap",
              }}
            >
              <button
                type="button"
                onClick={() => setGraphMode("simulated")}
                style={{
                  background: "#221c38",
                  color: "#c084fc",
                  border: "1px solid #9333ea",
                  padding: "8px 16px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontFamily: "IBM Plex Mono, monospace",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                ◈ Switch to Simulated Demo Graph
              </button>

              <button
                type="button"
                onClick={() => {
                  if (!activeSession) loadBenchmarkSample();
                  setGraphMode("uploaded");
                }}
                style={{
                  background: "#162238",
                  color: "#38bdf8",
                  border: "1px solid #0284c7",
                  padding: "8px 16px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontFamily: "IBM Plex Mono, monospace",
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                ✦ Open Interactive Uploaded Graph
              </button>

              {researchDataset && (
                <div style={{ display: "inline-block" }}>
                  <DatasetReportDownload
                    datasetId={researchDataset}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Empty State when in Uploaded Mode but no dataset loaded */}
      {graphMode === "uploaded" && !activeSession && (
        <div
          style={{
            background: "#0c0e14",
            border: "1px dashed #242c3c",
            borderRadius: "6px",
            padding: "36px 20px",
            textAlign: "center",
            marginBottom: "20px",
          }}
        >
          <h3 style={{ fontSize: "16px", color: "#f8fafc", margin: "0 0 8px 0" }}>
            No User Dataset Loaded in Current Session
          </h3>
          <p
            style={{
              fontSize: "13px",
              color: "#94a3b8",
              maxWidth: "580px",
              margin: "0 auto 16px auto",
              lineHeight: 1.6,
            }}
          >
            Upload your own financial transaction CSV, TSV, or JSON file in the Interactive Analysis
            workbench, or instantly load the pre-computed synthetic benchmark sample to explore graph
            anomalies.
          </p>

          <div style={{ display: "flex", justifyContent: "center", gap: "12px" }}>
            <button
              type="button"
              onClick={loadBenchmarkSample}
              style={{
                background: "#0284c7",
                color: "#ffffff",
                border: "none",
                padding: "8px 18px",
                borderRadius: "4px",
                fontSize: "12px",
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
                background: "#161b26",
                color: "#38bdf8",
                border: "1px solid #232d42",
                padding: "8px 18px",
                borderRadius: "4px",
                fontSize: "12px",
                fontFamily: "IBM Plex Mono, monospace",
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
              }}
            >
              Go to Upload Workbench →
            </a>
          </div>
        </div>
      )}

      {/* Main Interactive Workbench (When result exists) */}
      {activeGraphResult && (
        <div className="analysis-workbench-grid">
          {/* Left Column: Account Anomaly Filter & Ranking */}
          <div className="analysis-ranking-col">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "8px",
              }}
            >
              <h3 style={{ margin: 0, fontSize: "13px", color: "#f8fafc" }}>
                Flagged Accounts & Risk Ranking
              </h3>
              <span
                style={{
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: "10px",
                  color: "#64748b",
                }}
              >
                {filteredAccounts.length} accounts
              </span>
            </div>

            {/* Search Input */}
            <input
              type="text"
              placeholder="Search account ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                background: "#0c0e14",
                border: "1px solid #1e2434",
                borderRadius: "4px",
                padding: "6px 10px",
                fontSize: "11px",
                fontFamily: "IBM Plex Mono, monospace",
                color: "#f8fafc",
                marginBottom: "8px",
                boxSizing: "border-box",
              }}
            />

            {/* Pattern Filter Badges */}
            <div
              style={{
                display: "flex",
                gap: "4px",
                flexWrap: "wrap",
                marginBottom: "10px",
              }}
            >
              {[
                { key: "ALL", label: "All" },
                { key: "FAN_OUT", label: "Fan-Out" },
                { key: "FAN_IN", label: "Fan-In" },
                { key: "CYCLE", label: "Cycles" },
                { key: "VOLUME_OUTLIER", label: "Volume" },
                { key: "HIGH_RISK", label: "Risk ≥ 70%" },
              ].map((pill) => (
                <button
                  key={pill.key}
                  type="button"
                  onClick={() => setPatternFilter(pill.key)}
                  style={{
                    background: patternFilter === pill.key ? "#1e293b" : "#0d1017",
                    color: patternFilter === pill.key ? "#38bdf8" : "#64748b",
                    border:
                      patternFilter === pill.key ? "1px solid #0284c7" : "1px solid #1a202c",
                    borderRadius: "3px",
                    padding: "3px 6px",
                    fontSize: "10px",
                    fontFamily: "IBM Plex Mono, monospace",
                    cursor: "pointer",
                  }}
                >
                  {pill.label}
                </button>
              ))}
            </div>

            {/* Scrollable Accounts Table */}
            <div
              style={{
                maxHeight: "440px",
                overflowY: "auto",
                border: "1px solid #1a202c",
                borderRadius: "4px",
                background: "#08090d",
              }}
            >
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
                <thead>
                  <tr
                    style={{
                      borderBottom: "1px solid #1e2434",
                      color: "#64748b",
                      fontFamily: "IBM Plex Mono, monospace",
                      textAlign: "left",
                      background: "#0d1017",
                    }}
                  >
                    <th style={{ padding: "6px 8px" }}>ACCOUNT ID</th>
                    <th style={{ padding: "6px 8px" }}>SCORE</th>
                    <th style={{ padding: "6px 8px" }}>PATTERNS</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAccounts.map((acc) => {
                    const isSelected = selectedAccount?.id === acc.id;
                    const isHigh = acc.anomalyScore >= 0.7;
                    const isMed = acc.anomalyScore >= 0.45;
                    return (
                      <tr
                        key={acc.id}
                        onClick={() => setSelectedNodeId(acc.id)}
                        style={{
                          borderBottom: "1px solid #131620",
                          cursor: "pointer",
                          background: isSelected
                            ? "#162238"
                            : isHigh
                            ? "rgba(244, 63, 94, 0.05)"
                            : "transparent",
                        }}
                      >
                        <td
                          style={{
                            padding: "6px 8px",
                            fontFamily: "IBM Plex Mono, monospace",
                            fontWeight: isSelected ? 700 : 400,
                            color: isSelected ? "#38bdf8" : "#e2e8f0",
                          }}
                        >
                          {acc.id}
                        </td>
                        <td
                          style={{
                            padding: "6px 8px",
                            fontFamily: "IBM Plex Mono, monospace",
                            color: isHigh ? "#f43f5e" : isMed ? "#f59e0b" : "#38bdf8",
                            fontWeight: 600,
                          }}
                        >
                          {acc.anomalyScore.toFixed(3)}
                        </td>
                        <td style={{ padding: "6px 8px" }}>
                          {acc.patterns.length > 0 ? (
                            <span
                              style={{
                                fontSize: "9px",
                                fontFamily: "IBM Plex Mono, monospace",
                                padding: "1px 4px",
                                borderRadius: "2px",
                                background: acc.patterns.includes("CYCLE")
                                  ? "#2d163d"
                                  : "#2a151b",
                                color: acc.patterns.includes("CYCLE") ? "#c084fc" : "#f43f5e",
                                border: "1px solid rgba(255,255,255,0.1)",
                              }}
                            >
                              {acc.patterns[0]}
                            </span>
                          ) : (
                            <span style={{ color: "#475569", fontSize: "10px" }}>—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Column: Dynamic Graph Canvas & Responsive Account Inspector */}
          <div className="analysis-canvas-col">
            <AnalysisGraphCanvas
              accounts={activeGraphResult.accounts}
              edges={activeGraphResult.edges}
              selectedNode={selectedAccount?.id || null}
              onSelectNode={(id) => setSelectedNodeId(id)}
              modeBadge={
                graphMode === "uploaded"
                  ? `✦ UPLOADED: ${activeGraphResult.summary.datasetName}`
                  : `◈ SIMULATION: ${SIMULATED_PRESETS_META[simulatedPreset].badge}`
              }
            />

            {/* Account Inspector Panel */}
            {selectedAccount && (
              <div
                style={{
                  marginTop: "16px",
                  background: "#0c0e14",
                  border: "1px solid #1c2230",
                  borderRadius: "6px",
                  padding: "16px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "12px",
                    flexWrap: "wrap",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span
                      style={{
                        fontFamily: "IBM Plex Mono, monospace",
                        fontSize: "11px",
                        color: "#64748b",
                      }}
                    >
                      ENTITY INSPECTION:
                    </span>
                    <span
                      style={{
                        fontFamily: "IBM Plex Mono, monospace",
                        fontSize: "14px",
                        fontWeight: 700,
                        color: "#ffffff",
                      }}
                    >
                      {selectedAccount.id}
                    </span>
                  </div>

                  {/* Pattern tags */}
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    {selectedAccount.patterns.length > 0 ? (
                      selectedAccount.patterns.map((p) => (
                        <span
                          key={p}
                          style={{
                            fontSize: "10px",
                            fontFamily: "IBM Plex Mono, monospace",
                            padding: "3px 8px",
                            background: p === "CYCLE" ? "#2b1438" : "#321319",
                            color: p === "CYCLE" ? "#c084fc" : "#f43f5e",
                            border: p === "CYCLE" ? "1px solid #6b21a8" : "1px solid #881337",
                            borderRadius: "3px",
                            fontWeight: 600,
                          }}
                        >
                          ⚠ {p.replace("_", " ")}
                        </span>
                      ))
                    ) : (
                      <span
                        style={{
                          fontSize: "10px",
                          fontFamily: "IBM Plex Mono, monospace",
                          padding: "3px 8px",
                          background: "#0a1f1d",
                          color: "#10b981",
                          border: "1px solid #064e3b",
                          borderRadius: "3px",
                        }}
                      >
                        ✓ STANDARD METRICS
                      </span>
                    )}
                  </div>
                </div>

                {/* 3 Metric Cards */}
                <div className="inspector-metrics-grid" style={{ marginBottom: "16px" }}>
                  <div className="inspector-metric-card">
                    <span className="metric-label">ANOMALY SCORE</span>
                    <span
                      className="metric-val"
                      style={{
                        color:
                          selectedAccount.anomalyScore >= 0.7
                            ? "#f43f5e"
                            : selectedAccount.anomalyScore >= 0.45
                            ? "#f59e0b"
                            : "#38bdf8",
                      }}
                    >
                      {selectedAccount.anomalyScore.toFixed(3)}
                    </span>
                    <span className="metric-sub">
                      {selectedAccount.anomalyScore >= 0.7
                        ? "Critical Risk Tier"
                        : selectedAccount.anomalyScore >= 0.45
                        ? "Elevated Structural Risk"
                        : "Low Statistical Deviation"}
                    </span>
                  </div>

                  <div className="inspector-metric-card">
                    <span className="metric-label">TOPOLOGICAL DEGREE</span>
                    <span className="metric-val" style={{ color: "#f8fafc" }}>
                      {selectedAccount.inDegree} <small style={{ fontSize: "14px", color: "#64748b" }}>IN</small> /{" "}
                      {selectedAccount.outDegree} <small style={{ fontSize: "14px", color: "#64748b" }}>OUT</small>
                    </span>
                    <span className="metric-sub">
                      {selectedAccount.totalDegree} total transfer relationships
                    </span>
                  </div>

                  <div className="inspector-metric-card">
                    <span className="metric-label">NET FLOW VOLUME</span>
                    <span
                      className="metric-val"
                      style={{
                        color:
                          selectedAccount.netFlow < 0
                            ? "#f43f5e"
                            : selectedAccount.netFlow > 0
                            ? "#10b981"
                            : "#94a3b8",
                      }}
                    >
                      {selectedAccount.netFlow < 0 ? "-" : selectedAccount.netFlow > 0 ? "+" : ""}
                      ${Math.abs(selectedAccount.netFlow).toLocaleString("en-US")}
                    </span>
                    <span className="metric-sub">
                      {selectedAccount.netFlow < 0
                        ? "Net Outflow (Dispersal/Smurfing)"
                        : selectedAccount.netFlow > 0
                        ? "Net Inflow (Aggregation/Sink)"
                        : "Balanced In/Out Transfers"}
                    </span>
                  </div>
                </div>

                {/* Counterparties List */}
                <div>
                  <div
                    style={{
                      fontFamily: "IBM Plex Mono, monospace",
                      fontSize: "11px",
                      color: "#64748b",
                      marginBottom: "6px",
                      letterSpacing: "0.06em",
                    }}
                  >
                    TOP COUNTERPARTIES ({selectedAccount.counterparties.length})
                  </div>
                  <div
                    style={{
                      maxHeight: "180px",
                      overflowY: "auto",
                      border: "1px solid #1a202c",
                      borderRadius: "4px",
                      background: "#08090d",
                    }}
                  >
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
                      <thead>
                        <tr
                          style={{
                            borderBottom: "1px solid #1a202c",
                            color: "#64748b",
                            fontFamily: "IBM Plex Mono, monospace",
                            textAlign: "left",
                            background: "#0e111a",
                          }}
                        >
                          <th style={{ padding: "5px 8px" }}>DIRECTION</th>
                          <th style={{ padding: "5px 8px" }}>COUNTERPARTY ID</th>
                          <th style={{ padding: "5px 8px", textAlign: "right" }}>VOLUME</th>
                          <th style={{ padding: "5px 8px", textAlign: "right" }}>COUNT</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedAccount.counterparties.map((cp, idx) => (
                          <tr
                            key={`${cp.id}-${idx}`}
                            onClick={() => setSelectedNodeId(cp.id)}
                            style={{
                              borderBottom: "1px solid #12151e",
                              cursor: "pointer",
                            }}
                          >
                            <td style={{ padding: "5px 8px" }}>
                              <span
                                style={{
                                  fontSize: "9px",
                                  fontFamily: "IBM Plex Mono, monospace",
                                  padding: "2px 5px",
                                  borderRadius: "2px",
                                  background: cp.direction === "out" ? "#2a151b" : "#0d221e",
                                  color: cp.direction === "out" ? "#f43f5e" : "#2dd4bf",
                                  border:
                                    cp.direction === "out"
                                      ? "1px solid #5c1d28"
                                      : "1px solid #134e48",
                                }}
                              >
                                {cp.direction === "out" ? "OUT →" : "← IN"}
                              </span>
                            </td>
                            <td
                              style={{
                                padding: "5px 8px",
                                fontFamily: "IBM Plex Mono, monospace",
                                color: "#38bdf8",
                              }}
                            >
                              {cp.id}
                            </td>
                            <td
                              style={{
                                padding: "5px 8px",
                                fontFamily: "IBM Plex Mono, monospace",
                                textAlign: "right",
                                color: "#f8fafc",
                              }}
                            >
                              ${cp.amount.toLocaleString("en-US")}
                            </td>
                            <td
                              style={{
                                padding: "5px 8px",
                                fontFamily: "IBM Plex Mono, monospace",
                                textAlign: "right",
                                color: "#94a3b8",
                              }}
                            >
                              {cp.count} tx
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
