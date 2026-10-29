import NetworkMetricSummary from "../NetworkMetricSummary";
import { useState, useMemo } from "react";
import { Heading, Qualifications } from "../ui";
import { useGraphCatalog } from "../graph/client";
import { useSession } from "../sessionContext";
import {
  SIMULATED_PRESETS_META,
  getSimulatedPresetResult,
} from "../graph/simulatedData";
import AnalysisGraphCanvas from "../datasetAnalysis/AnalysisGraphCanvas";
import type { AccountNode } from "../datasetAnalysis/types";
import { DatasetReportDownload } from "../DatasetReportDownload";
import { generateDatasetPdfReport } from "../datasetAnalysis/reportGenerator";

export default function GraphExplorer() {
  const {
    selectedGraphAccount: selectedNodeId,
    setSelectedGraphAccount: setSelectedNodeId,
    activeSession,
    graphMode,
    setGraphMode,
    simulatedPreset,
    setSimulatedPreset,
    loadBenchmarkSample,
    backendModel,
  } = useSession();

  const metadata = useGraphCatalog();
  const [researchDataset, setResearchDataset] = useState("ibm-5k");
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
      {activeGraphResult && <NetworkMetricSummary summary={activeGraphResult.summary} />}

      {/* Primary Graph Mode Switcher */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          background: "#101012",
          border: "1px solid #303034",
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
              color: "#77777d",
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
              background: graphMode === "uploaded" ? "#842d35" : "transparent",
              color: graphMode === "uploaded" ? "#ffffff" : "#a6a6a6",
              border: graphMode === "uploaded" ? "1px solid #b44a50" : "1px solid transparent",
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
              background: graphMode === "simulated" ? "#842d35" : "transparent",
              color: graphMode === "simulated" ? "#ffffff" : "#a6a6a6",
              border: graphMode === "simulated" ? "1px solid #b44a50" : "1px solid transparent",
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
              background: graphMode === "research" ? "#842d35" : "transparent",
              color: graphMode === "research" ? "#ffffff" : "#a6a6a6",
              border: graphMode === "research" ? "1px solid #b44a50" : "1px solid transparent",
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
                color: "#f5f5f5",
                padding: "3px 8px",
                background: "#171719",
                border: "1px solid #303034",
                borderRadius: "3px",
              }}
            >
              {activeSession ? (
                <>
                  <b style={{ color: "#c04b52" }}>●</b> Active: {activeSession.summary.datasetName}
                </>
              ) : (
                "○ No dataset loaded"
              )}
            </span>
          )}

          {graphMode === "simulated" && (
            <span
              style={{
                fontSize: "10px",
                fontFamily: "IBM Plex Mono, monospace",
                color: "#f5f5f5",
                padding: "3px 8px",
                background: "#171719",
                border: "1px solid #303034",
                borderRadius: "3px",
              }}
            >
              <b style={{ color: "#c04b52" }}>◈</b> SIMULATED DEMO (NON-REAL DATA)
            </span>
          )}

          {graphMode === "research" && (
            <span
              style={{
                fontSize: "10px",
                fontFamily: "IBM Plex Mono, monospace",
                color: "#f5f5f5",
                padding: "3px 8px",
                background: "#171719",
                border: "1px solid #303034",
                borderRadius: "3px",
              }}
            >
              <b style={{ color: "#c04b52" }}>⚲</b> HISTORICAL CATALOG
            </span>
          )}
        </div>
      </div>

      {/* Simulated Preset Bar (if in simulated mode) */}
      {graphMode === "simulated" && (
        <div
          style={{
            background: "#101012",
            border: "1px solid #303034",
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
                        background: isSelected ? "#842d35" : "#171719",
                        color: isSelected ? "#ffffff" : "#a6a6a6",
                        border: isSelected ? "1px solid #b44a50" : "1px solid #303034",
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
                color: "#a6a6a6",
              }}
            >
              Volume:{" "}
              <b style={{ color: "#f5f5f5" }}>
                {SIMULATED_PRESETS_META[simulatedPreset].totalVolumeFormatted}
              </b>
            </span>
          </div>

          <p style={{ margin: 0, fontSize: "12px", color: "#a6a6a6", lineHeight: 1.5 }}>
            {SIMULATED_PRESETS_META[simulatedPreset].description}
          </p>
        </div>
      )}

      {/* Historical Research Mode Topology Unavailable Card */}
      {graphMode === "research" && (
        <div
          style={{
            background: "#101012",
            border: "1px solid #303034",
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
              <label style={{ fontSize: "12px", color: "#a6a6a6" }}>
                Select Dataset:
                <select
                  value={researchDataset}
                  onChange={(e) => setResearchDataset(e.target.value)}
                  style={{
                    marginLeft: "8px",
                    background: "#171719",
                    color: "#f5f5f5",
                    border: "1px solid #303034",
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
                color: "#f5f5f5",
                padding: "3px 8px",
                background: "#171719",
                border: "1px solid #b44a50",
                borderRadius: "3px",
              }}
            >
              <b style={{ color: "#c04b52" }}>⚠</b> TOPOLOGY RESTRICTED BY RESEARCH SAFEGUARDS
            </span>
          </div>

          <div
            style={{
              background: "#080809",
              border: "1px dashed #303034",
              borderRadius: "6px",
              padding: "24px",
              textAlign: "center",
            }}
          >
            <h3 style={{ fontSize: "16px", color: "#f5f5f5", margin: "0 0 8px 0" }}>
              {dsMeta?.name ?? researchDataset} — Historical Topology Unavailable
            </h3>
            <p
              style={{
                fontSize: "13px",
                color: "#a6a6a6",
                maxWidth: "680px",
                margin: "0 auto 16px auto",
                lineHeight: 1.6,
              }}
            >
              Raw transaction graphs for IBM AML and PaySim contain proprietary or unredacted
              account identifiers that are intentionally excluded from the public deployment. Saved numerical benchmarks, model evaluations (E0–E6), and seed results remain available with their recorded provenance and limitations.
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
                  background: "#842d35",
                  color: "#ffffff",
                  border: "1px solid #b44a50",
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
                  background: "#171719",
                  color: "#f5f5f5",
                  border: "1px solid #303034",
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
            background: "#101012",
            border: "1px dashed #303034",
            borderRadius: "6px",
            padding: "36px 20px",
            textAlign: "center",
            marginBottom: "20px",
          }}
        >
          <h3 style={{ fontSize: "16px", color: "#f5f5f5", margin: "0 0 8px 0" }}>
            No User Dataset Loaded in Current Session
          </h3>
          <p
            style={{
              fontSize: "13px",
              color: "#a6a6a6",
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
                background: "#b44a50",
                color: "#ffffff",
                border: "1px solid #842d35",
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
                background: "#171719",
                color: "#f5f5f5",
                border: "1px solid #303034",
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
          <div className="analysis-ranking-col" style={{ minWidth: 0 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "8px",
                flexWrap: "wrap",
                gap: "6px",
              }}
            >
              <h3 style={{ margin: 0, fontSize: "13px", color: "#f5f5f5" }}>
                Account Review Ranking (Heuristic)
              </h3>
              <span
                style={{
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: "10px",
                  color: "#77777d",
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
                background: "#101012",
                border: "1px solid #303034",
                borderRadius: "4px",
                padding: "6px 10px",
                fontSize: "11px",
                fontFamily: "IBM Plex Mono, monospace",
                color: "#f5f5f5",
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
                    background: patternFilter === pill.key ? "#842d35" : "#101012",
                    color: patternFilter === pill.key ? "#ffffff" : "#a6a6a6",
                    border:
                      patternFilter === pill.key ? "1px solid #b44a50" : "1px solid #303034",
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
                border: "1px solid #303034",
                borderRadius: "4px",
                background: "#080809",
              }}
            >
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
                <thead>
                  <tr
                    style={{
                      borderBottom: "1px solid #303034",
                      color: "#a6a6a6",
                      fontFamily: "IBM Plex Mono, monospace",
                      textAlign: "left",
                      background: "#171719",
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
                          borderBottom: "1px solid #1a1a1d",
                          cursor: "pointer",
                          background: isSelected
                            ? "#241315"
                            : isHigh
                            ? "rgba(180, 74, 80, 0.12)"
                            : "transparent",
                        }}
                      >
                        <td
                          style={{
                            padding: "6px 8px",
                            fontFamily: "IBM Plex Mono, monospace",
                            fontWeight: isSelected ? 700 : 400,
                            color: isSelected ? "#ffffff" : isHigh ? "#fca5a5" : "#e5e7eb",
                          }}
                        >
                          {acc.id}
                        </td>
                        <td
                          style={{
                            padding: "6px 8px",
                            fontFamily: "IBM Plex Mono, monospace",
                            color: isHigh ? "#ef4444" : isMed ? "#b44a50" : "#a6a6a6",
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
                                padding: "1px 5px",
                                borderRadius: "2px",
                                background: "rgba(180, 74, 80, 0.15)",
                                color: "#fca5a5",
                                border: "1px solid #b44a50",
                              }}
                            >
                              {acc.patterns[0]}
                            </span>
                          ) : (
                            <span style={{ color: "#77777d", fontSize: "10px" }}>—</span>
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
              preset={graphMode === "simulated" ? simulatedPreset : undefined}
              modeBadge={
                graphMode === "uploaded"
                  ? `✦ UPLOADED: ${activeGraphResult.summary.datasetName}`
                  : `◈ SIMULATED: ${SIMULATED_PRESETS_META[simulatedPreset].badge}`
              }
            />

            {/* Account Inspector Panel */}
            {selectedAccount && (
              <div
                style={{
                  marginTop: "16px",
                  background: "#101012",
                  border: "1px solid #303034",
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
                        color: "#77777d",
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
                        maxWidth: "340px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        display: "inline-block",
                        verticalAlign: "middle",
                      }}
                      title={selectedAccount.id}
                    >
                      {selectedAccount.id}
                    </span>
                  </div>

                  {/* Pattern tags and PDF Report Download */}
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
                    {selectedAccount.patterns.length > 0 ? (
                      selectedAccount.patterns.map((p) => (
                        <span key={p} className="inspector-pattern-badge">
                          <b style={{ color: "#ef4444" }}>⚠</b> {p.replace("_", " ")}
                        </span>
                      ))
                    ) : (
                      <span
                        style={{
                          fontSize: "10px",
                          fontFamily: "IBM Plex Mono, monospace",
                          padding: "3px 8px",
                          background: "#171719",
                          color: "#f5f5f5",
                          border: "1px solid #303034",
                          borderRadius: "3px",
                        }}
                      >
                        <b style={{ color: "#c04b52" }}>✓</b> STANDARD METRICS
                      </span>
                    )}

                    {graphMode === "uploaded" && activeGraphResult && (
                      <button
                        type="button"
                        onClick={() =>
                          generateDatasetPdfReport(
                            activeGraphResult,
                            activeGraphResult.backendModel || backendModel,
                          )
                        }
                        style={{
                          background: "#842d35",
                          color: "#ffffff",
                          border: "1px solid #b44a50",
                          padding: "3px 8px",
                          borderRadius: "3px",
                          fontFamily: "IBM Plex Mono, monospace",
                          fontSize: "10px",
                          fontWeight: 600,
                          cursor: "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        📄 Download Report (PDF)
                      </button>
                    )}
                  </div>
                </div>

                {/* 3 Metric Cards */}
                <div className="inspector-metrics-grid" style={{ marginBottom: "16px" }}>
                  <div
                    className={`inspector-metric-card ${
                      selectedAccount.anomalyScore >= 0.5 ? "alert" : ""
                    }`}
                  >
                    <span className="metric-label">ANOMALY SCORE</span>
                    <span
                      className="metric-number"
                      style={{
                        color:
                          selectedAccount.anomalyScore >= 0.7
                            ? "#ef4444"
                            : selectedAccount.anomalyScore >= 0.45
                            ? "#b44a50"
                            : "#f5f5f5",
                      }}
                    >
                      {selectedAccount.anomalyScore.toFixed(3)}
                    </span>
                    <span className="metric-hint">
                      {selectedAccount.isFlaggedForReview ? "Flagged for review (heuristic)" : "Not flagged for review"}
                    </span>
                  </div>

                  <div className="inspector-metric-card">
                    <span className="metric-label">TRANSACTION COUNTS</span>
                    <span className="metric-number">
                      {selectedAccount.inDegree}{" "}
                      <small style={{ fontSize: "12px", color: "#a6a6a6" }}>IN</small> /{" "}
                      {selectedAccount.outDegree}{" "}
                      <small style={{ fontSize: "12px", color: "#a6a6a6" }}>OUT</small>
                    </span>
                    <span className="metric-hint">
                      {selectedAccount.totalDegree} transaction incidences; unique neighbors: {selectedAccount.uniqueInDegree ?? "N/A"} in / {selectedAccount.uniqueOutDegree ?? "N/A"} out; counterparties: {selectedAccount.uniqueCounterpartyCount ?? "N/A"}
                    </span>
                  </div>

                  <div
                    className={`inspector-metric-card ${
                      Math.abs(selectedAccount.netFlow) > 10000 ? "alert" : ""
                    }`}
                  >
                    <span className="metric-label">NET FLOW VOLUME</span>
                    <span
                      className="metric-number"
                      style={{
                        color: selectedAccount.netFlow < 0 ? "#ef4444" : "#f5f5f5",
                      }}
                    >
                      {selectedAccount.netFlow < 0 ? "-" : selectedAccount.netFlow > 0 ? "+" : ""}
                      {activeGraphResult.summary.isMixedCurrency ? "Mixed units " : (activeGraphResult.summary.currency || "Unknown") + " "}{Math.abs(selectedAccount.netFlow).toLocaleString("en-US", {
                        maximumFractionDigits: 0,
                      })}
                    </span>
                    <span className="metric-hint">
                      {selectedAccount.netFlow < 0
                        ? "Net Outflow (Dispersal)"
                        : selectedAccount.netFlow > 0
                        ? "Net Inflow (Aggregation)"
                        : "Balanced Flow"}
                    </span>
                  </div>
                </div>

                {/* Counterparties List */}
                <div>
                  <div
                    style={{
                      fontFamily: "IBM Plex Mono, monospace",
                      fontSize: "11px",
                      color: "#a6a6a6",
                      marginBottom: "8px",
                      letterSpacing: "0.06em",
                    }}
                  >
                    TOP COUNTERPARTIES ({selectedAccount.counterparties.length})
                  </div>
                  <div
                    className="counterparties-list-container"
                    style={{ borderRadius: "4px", border: "1px solid #303034" }}
                  >
                    <table className="counterparty-table">
                      <thead>
                        <tr>
                          <th style={{ width: "90px" }}>DIRECTION</th>
                          <th>COUNTERPARTY ID</th>
                          <th style={{ textAlign: "right" }}>VOLUME</th>
                          <th style={{ textAlign: "right", width: "70px" }}>COUNT</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedAccount.counterparties.map((cp, idx) => (
                          <tr
                            key={`${cp.id}-${idx}`}
                            onClick={() => setSelectedNodeId(cp.id)}
                            style={{ cursor: "pointer" }}
                          >
                            <td>
                              <span className={`direction-badge ${cp.direction}`}>
                                {cp.direction === "out" ? "OUT →" : "← IN"}
                              </span>
                            </td>
                            <td style={{ color: "#f5f5f5", fontWeight: 500 }}>{cp.id}</td>
                            <td style={{ textAlign: "right", color: "#ffffff", fontWeight: 600 }}>
                              {(activeGraphResult.summary.isMixedCurrency ? "Mixed units " : (activeGraphResult.summary.currency || "Unknown") + " ")}{(cp.totalAmount ?? cp.amount ?? ((cp.inAmount ?? 0) + (cp.outAmount ?? 0))).toLocaleString("en-US", { maximumFractionDigits: 2 })}
                            </td>
                            <td style={{ textAlign: "right", color: "#a6a6a6" }}>{cp.count ?? ((cp.inCount ?? 0) + (cp.outCount ?? 0))} tx</td>
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
