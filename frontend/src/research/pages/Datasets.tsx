import SessionDataset from "../SessionDataset";
import { useState } from "react";
import { useResearch, fmt } from "../state";
import { DatasetReportDownload } from "../DatasetReportDownload";
import type { Page_Dataset_, Dataset } from "../contract";
import { State, Heading, Panel, Table, Status, Hash, Notice, Qualifications } from "../ui";
import { useSession } from "../sessionContext";
import { generateDatasetPdfReport } from "../datasetAnalysis/reportGenerator";

function Detail({ id }: { id: string }) {
  const r = useResearch<Dataset>("/datasets/" + id, "Dataset");
  return !r.data ? (
    <State {...r} />
  ) : (
    <Panel title={r.data.name} tag="DATASET / IDENTITY">
      <div className="panel-body">
        <Status value={r.data} />
        <p style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: "12px", color: "#e2e8f0" }}>
          Version: {r.data.version}
        </p>
        <p style={{ fontSize: "12px", color: "#94a3b8" }}>{r.data.label_definition}</p>
        <p style={{ fontSize: "12px", color: "#94a3b8" }}>{r.data.time_semantics}</p>
        <Hash key="hash" value={r.data.transaction_sha256} />
        <div style={{ marginTop: "12px", marginBottom: "12px" }}>
          <DatasetReportDownload key={id} datasetId={id} />
        </div>
        {r.data.label_disagreements != null && (
          <Notice>
            Unresolved label conflict: {fmt(r.data.label_disagreements, 0)} account disagreements between research and
            application label sets. Neither set is privileged.
          </Notice>
        )}
      </div>
      <Table
        caption="Distinct label sets — never merged"
        headers={["Label identity", "Accounts", "Positives", "Checksum"]}
        rows={(r.data.label_sets ?? []).map((l) => [
          l.identity,
          fmt(l.accounts, 0),
          fmt(l.positives, 0),
          <Hash key="hash" value={l.sha256} />,
        ])}
      />
    </Panel>
  );
}

export default function Datasets() {
  const r = useResearch<Page_Dataset_>("/datasets", "Page_Dataset_");
  const { activeSession, loadBenchmarkSample, backendModel } = useSession();
  const [activeTab, setActiveTab] = useState<"historical" | "custom">("custom");
  const [id, setId] = useState(() => {
    const requested = new URLSearchParams(location.hash.split("?")[1] ?? "").get("dataset_id");
    return requested && ["ibm-5k", "ibm-50k", "paysim"].includes(requested) ? requested : "ibm-5k";
  });

  return (
    <div className="research-page datasets-page">
      <Heading index="02" title="Dataset Explorer">
        Explore verified historical benchmark datasets (IBM AML, PaySim) or inspect your active uploaded custom transaction dataset.
      </Heading>

      <Qualifications />

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          borderBottom: "1px solid #1e2434",
          marginBottom: "20px",
          paddingBottom: "8px",
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab("custom")}
          style={{
            background: activeTab === "custom" ? "#842d35" : "transparent",
            color: activeTab === "custom" ? "#ffffff" : "#a6a6a6",
            border: activeTab === "custom" ? "1px solid #b44a50" : "1px solid transparent",
            borderRadius: "4px",
            padding: "8px 16px",
            fontFamily: "IBM Plex Mono, monospace",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          ✦ Custom Dataset Ingestion {activeSession ? `(Active)` : ""}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("historical")}
          style={{
            background: activeTab === "historical" ? "#842d35" : "transparent",
            color: activeTab === "historical" ? "#ffffff" : "#a6a6a6",
            border: activeTab === "historical" ? "1px solid #b44a50" : "1px solid transparent",
            borderRadius: "4px",
            padding: "8px 16px",
            fontFamily: "IBM Plex Mono, monospace",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          ⚲ Historical Benchmark Catalog (IBM / PaySim)
        </button>
      </div>

      {activeTab === "custom" ? (
        <div>
          <SessionDataset />
          {/* Custom Ingestion Card */}
          <Panel title="Active Custom Dataset Session" tag="CLIENT-SIDE PIPELINE">
            <div className="panel-body">
              {activeSession ? (
                <div>
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
                    <div>
                      <h3 style={{ margin: "0 0 4px 0", fontSize: "15px", color: "#f8fafc" }}>
                        {activeSession.summary.datasetName}
                      </h3>
                      <span
                        style={{
                          fontFamily: "IBM Plex Mono, monospace",
                          fontSize: "11px",
                          color: "#64748b",
                        }}
                      >
                        Ingested at: {activeSession.summary.processedAt}
                      </span>
                    </div>

                    <span
                      style={{
                        fontFamily: "IBM Plex Mono, monospace",
                        fontSize: "10px",
                        color: "#f5f5f5",
                        padding: "3px 8px",
                        background: "#171719",
                        border: "1px solid #303034",
                        borderRadius: "3px",
                      }}
                    >
                      <b style={{ color: "#c04b52" }}>●</b> SESSION ACTIVE
                    </span>
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                      gap: "12px",
                      marginBottom: "16px",
                    }}
                  >
                    <div style={{ background: "#08090d", padding: "10px", borderRadius: "4px" }}>
                      <span style={{ fontSize: "10px", color: "#64748b", display: "block" }}>
                        ACCOUNTS
                      </span>
                      <strong style={{ fontSize: "16px", color: "#f8fafc" }}>
                        {activeSession.summary.uniqueAccounts.toLocaleString()}
                      </strong>
                    </div>
                    <div style={{ background: "#08090d", padding: "10px", borderRadius: "4px" }}>
                      <span style={{ fontSize: "10px", color: "#64748b", display: "block" }}>
                        TRANSFERS
                      </span>
                      <strong style={{ fontSize: "16px", color: "#f8fafc" }}>
                        {activeSession.summary.totalTransactions.toLocaleString()}
                      </strong>
                    </div>
                    <div style={{ background: "#08090d", padding: "10px", borderRadius: "4px" }}>
                      <span style={{ fontSize: "10px", color: "#64748b", display: "block" }}>
                        TOTAL VOLUME
                      </span>
                      <strong style={{ fontSize: "16px", color: "#f8fafc" }}>
                        ${activeSession.summary.totalVolume.toLocaleString("en-US", {
                          maximumFractionDigits: 2,
                        })}
                      </strong>
                    </div>
                    <div style={{ background: "#08090d", padding: "10px", borderRadius: "4px" }}>
                      <span style={{ fontSize: "10px", color: "#64748b", display: "block" }}>
                        ANOMALIES
                      </span>
                      <strong style={{ fontSize: "16px", color: "#c04b52" }}>
                        {activeSession.summary.suspiciousAccountCount}
                      </strong>
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
                      href="#/analyze"
                      style={{
                        background: "#b44a50",
                        color: "#ffffff",
                        padding: "8px 16px",
                        borderRadius: "4px",
                        fontFamily: "IBM Plex Mono, monospace",
                        fontSize: "11px",
                        fontWeight: 600,
                        textDecoration: "none",
                      }}
                    >
                      Open Full Analysis Workbench →
                    </a>
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
                      View in Graph Explorer →
                    </a>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "20px 0" }}>
                  <p style={{ fontSize: "13px", color: "#94a3b8", margin: "0 0 16px 0" }}>
                    No dataset uploaded in the current session. You can upload any transaction file
                    or immediately initialize the synthetic benchmark sample.
                  </p>
                  <div style={{ display: "flex", justifyContent: "center", gap: "10px" }}>
                    <button
                      type="button"
                      onClick={loadBenchmarkSample}
                      style={{
                        background: "#b44a50",
                        color: "#ffffff",
                        border: "1px solid #842d35",
                        padding: "8px 18px",
                        borderRadius: "4px",
                        fontFamily: "IBM Plex Mono, monospace",
                        fontSize: "11px",
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
                        fontFamily: "IBM Plex Mono, monospace",
                        fontSize: "11px",
                        textDecoration: "none",
                      }}
                    >
                      Upload CSV / TSV / JSON File →
                    </a>
                  </div>
                </div>
              )}
            </div>
          </Panel>
        </div>
      ) : (
        /* Historical Benchmark Tab */
        <>
          {!r.data ? (
            <State {...r} />
          ) : (
            <>
              <Panel title="Network Inventory" tag="SOURCE / METADATA">
                <Table
                  caption="Dataset counts; unavailable fields are clearly denoted"
                  headers={[
                    "Dataset",
                    "Accounts",
                    "Transactions",
                    "Positive",
                    "Negative",
                    "Prevalence",
                    "Provenance",
                  ]}
                  rows={r.data.items.map((d) => [
                    <button
                      key="select"
                      onClick={() => setId(d.dataset_id)}
                      aria-pressed={id === d.dataset_id}
                      style={{
                        background: id === d.dataset_id ? "#842d35" : "transparent",
                        color: id === d.dataset_id ? "#ffffff" : "#f8fafc",
                        border: id === d.dataset_id ? "1px solid #b44a50" : "none",
                        padding: "4px 8px",
                        borderRadius: "3px",
                        fontFamily: "IBM Plex Mono, monospace",
                        cursor: "pointer",
                      }}
                    >
                      {d.name}
                    </button>,
                    fmt(d.accounts, 0),
                    fmt(d.transactions, 0),
                    fmt(d.positives, 0),
                    fmt(d.negatives, 0),
                    fmt(d.prevalence, 6),
                    d.provenance_status.replaceAll("_", " "),
                  ])}
                />
              </Panel>
              <Detail id={id} />
            </>
          )}
        </>
      )}
    </div>
  );
}
