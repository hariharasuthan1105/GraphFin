import { useState, useId, useEffect } from "react";
import { Heading, Panel, Notice } from "../ui";
import { fmt } from "../state";
import { SAMPLE_CSV_DATA } from "../datasetAnalysis/sampleData";
import {
  parseDelimitedText,
  parseJsonTransactions,
  autoDetectColumnMapping,
  buildTransactionRecords,
  type ParsedTable,
} from "../datasetAnalysis/parser";
import { analyzeTransactionGraph } from "../datasetAnalysis/engine";
import { AnalysisGraphCanvas } from "../datasetAnalysis/AnalysisGraphCanvas";
import type {
  AnalysisResult,
  ColumnMapping,
} from "../datasetAnalysis/types";
import { useSession } from "../sessionContext";
import { generateDatasetPdfReport } from "../datasetAnalysis/reportGenerator";

export default function DatasetAnalysis() {
  const {
    activeSession,
    setActiveSession,
    setGraphMode,
    syncSessionToBackend,
    backendStatus,
    backendModel,
  } = useSession();
  const [step, setStep] = useState<"upload" | "mapping" | "results">(
    activeSession ? "results" : "upload"
  );
  const [fileName, setFileName] = useState(activeSession?.summary.datasetName || "");
  const [fileSize, setFileSize] = useState(activeSession?.summary.fileSizeBytes || 0);
  const [rawCsvText, setRawCsvText] = useState<string>(activeSession?.summary.rawCsvContent || "");
  const [parsedTable, setParsedTable] = useState<ParsedTable | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping>({
    sourceCol: "",
    destinationCol: "",
    amountCol: "",
    transactionIdCol: "",
    timestampCol: "",
    typeCol: "",
    labelCol: "",
  });
  const [errorMsg, setErrorMsg] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(activeSession);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(
    activeSession?.topAnomalies[0]?.id || activeSession?.accounts[0]?.id || null
  );
  const [filterPattern, setFilterPattern] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const fileInputId = useId();

  // Auto-load sample benchmark if URL hash contains sample=1 or demo=1
  useEffect(() => {
    const hash = window.location.hash || "";
    if (hash.includes("sample=1") || hash.includes("demo=1")) {
      setFileName("synthetic_financial_network_benchmark.csv");
      setFileSize(SAMPLE_CSV_DATA.length);
      try {
        const table = parseDelimitedText(SAMPLE_CSV_DATA);
        const autoMap = autoDetectColumnMapping(table.headers);
        setParsedTable(table);
        setMapping(autoMap);
        if (hash.includes("autostart=1") || hash.includes("run=1")) {
          const records = buildTransactionRecords(table, autoMap);
          const analysis = analyzeTransactionGraph(
            records,
            "synthetic_financial_network_benchmark.csv",
            SAMPLE_CSV_DATA.length,
          );
          setResult(analysis);
          if (analysis.topAnomalies.length > 0) {
            setSelectedNodeId(analysis.topAnomalies[0].id);
          }
          setStep("results");
        } else {
          setStep("mapping");
        }
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Failed to load sample dataset.");
      }
    }
  }, []);

  // 1. Handle File Selection
  const handleFile = (file: File) => {
    setErrorMsg("");
    setFileName(file.name);
    setFileSize(file.size);

    if (file.size > 25 * 1024 * 1024) {
      setErrorMsg("File exceeds the 25 MB browser memory safety limit.");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        setRawCsvText(text);
        let table: ParsedTable;
        if (file.name.endsWith(".json")) {
          table = parseJsonTransactions(text);
        } else {
          table = parseDelimitedText(text);
        }

        const autoMap = autoDetectColumnMapping(table.headers);
        setParsedTable(table);
        setMapping(autoMap);
        setStep("mapping");
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Failed to parse file.");
      }
    };
    reader.onerror = () => setErrorMsg("Failed to read the selected file.");
    reader.readAsText(file);
  };

  // 2. Load Sample Benchmark
  const handleLoadSample = () => {
    setErrorMsg("");
    setFileName("synthetic_financial_network_benchmark.csv");
    setFileSize(SAMPLE_CSV_DATA.length);
    setRawCsvText(SAMPLE_CSV_DATA);
    try {
      const table = parseDelimitedText(SAMPLE_CSV_DATA);
      const autoMap = autoDetectColumnMapping(table.headers);
      setParsedTable(table);
      setMapping(autoMap);
      setStep("mapping");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to load sample dataset.");
    }
  };

  // 3. Run Graph Analysis
  const handleRunAnalysis = () => {
    if (!parsedTable) return;
    setErrorMsg("");
    setIsProcessing(true);

    setTimeout(() => {
      try {
        const records = buildTransactionRecords(parsedTable, mapping);
        const analysis = analyzeTransactionGraph(records, fileName, fileSize);
        analysis.summary.rawCsvContent = rawCsvText;
        setResult(analysis);
        setActiveSession(analysis);
        setGraphMode("uploaded");
        if (analysis.topAnomalies.length > 0) {
          setSelectedNodeId(analysis.topAnomalies[0].id);
        } else if (analysis.accounts.length > 0) {
          setSelectedNodeId(analysis.accounts[0].id);
        }
        setStep("results");
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Graph analysis encountered an error.");
      } finally {
        setIsProcessing(false);
      }
    }, 50);
  };

  // Keep result updated when activeSession changes (e.g. backend scores arrived)
  useEffect(() => {
    if (activeSession) {
      setResult(activeSession);
    }
  }, [activeSession]);

  // 4. Reset
  const handleReset = () => {
    setStep("upload");
    setParsedTable(null);
    setResult(null);
    setSelectedNodeId(null);
    setErrorMsg("");
  };

  // 5. Exports
  const handleExportJson = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result.summary, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `GraphFin_Analysis_${fileName.replace(/\.[^.]+$/, "")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCsv = () => {
    if (!result) return;
    const header = "Account_ID,Anomaly_Score,In_Degree,Out_Degree,Total_Degree,Total_Sent,Total_Received,Net_Flow,Patterns\n";
    const rows = result.accounts
      .map(
        (a) =>
          `"${a.id}",${a.anomalyScore},${a.inDegree},${a.outDegree},${a.totalDegree},${a.totalSent},${a.totalReceived},${a.netFlow},"${a.patterns.join(";")}"`
      )
      .join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `GraphFin_Account_Anomalies_${fileName.replace(/\.[^.]+$/, "")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const selectedAccount = result?.accounts.find((a) => a.id === selectedNodeId);

  // Filter accounts
  const displayedAccounts = (result?.accounts || []).filter((a) => {
    const matchesSearch = searchQuery
      ? a.id.toLowerCase().includes(searchQuery.toLowerCase())
      : true;
    const matchesPattern =
      filterPattern === "ALL"
        ? true
        : a.patterns.includes(filterPattern as any);
    return matchesSearch && matchesPattern;
  });

  return (
    <>
      <Heading index="02" title="Financial Dataset Analysis">
        Client-side transaction network construction, structural graph feature extraction, and anomaly pattern detection.
      </Heading>

      {errorMsg && (
        <div className="auth-error-banner" role="alert" style={{ marginBottom: 20 }}>
          {errorMsg}
        </div>
      )}

      {/* STEP 1: UPLOAD / DROPZONE */}
      {step === "upload" && (
        <div className="analysis-upload-flow">
          <Panel title="Upload Financial Transaction Data" tag="INPUT / INGESTION">
            <div className="panel-body">
              <div
                className="dropzone-box"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
                }}
                style={{
                  border: "2px dashed #303034",
                  padding: "48px 24px",
                  textAlign: "center",
                  background: "#080809",
                  borderRadius: "2px",
                  cursor: "pointer",
                  marginBottom: "24px",
                }}
                onClick={() => document.getElementById(fileInputId)?.click()}
              >
                <input
                  id={fileInputId}
                  type="file"
                  accept=".csv,.tsv,.json,.txt"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    if (e.target.files?.[0]) handleFile(e.target.files[0]);
                  }}
                />
                <div style={{ fontSize: "36px", marginBottom: "12px", color: "#b44a50" }}>
                  ↑
                </div>
                <h3 style={{ margin: "0 0 8px 0" }}>Choose a transaction dataset or drag and drop</h3>
                <p style={{ maxWidth: "480px", margin: "0 auto 16px auto", color: "#a6a6a6" }}>
                  Supports CSV, TSV, or JSON formats. Requires sender account, receiver account, and transfer amount.
                </p>
                <button
                  type="button"
                  className="action-btn-red"
                  style={{
                    background: "#b44a50",
                    color: "#ffffff",
                    border: "none",
                    fontWeight: 600,
                    padding: "10px 24px",
                    borderRadius: "2px",
                  }}
                >
                  SELECT LOCAL FILE ↗
                </button>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "16px",
                  background: "#171719",
                  border: "1px solid #303034",
                  borderRadius: "2px",
                }}
              >
                <div>
                  <strong style={{ display: "block", color: "#f5f5f5" }}>
                    No dataset ready? Try our synthetic benchmark network
                  </strong>
                  <span style={{ color: "#a6a6a6", fontSize: "12px" }}>
                    Pre-configured transaction set containing known smurfing (fan-out), mule collection (fan-in), cycles, and volume outliers.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleLoadSample}
                  style={{
                    background: "#202023",
                    color: "#f5f5f5",
                    border: "1px solid #303034",
                    padding: "8px 16px",
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  LOAD SAMPLE BENCHMARK ↗
                </button>
              </div>
            </div>
          </Panel>

          <Notice>
            <strong>Privacy &amp; Bounded Execution Guarantee:</strong> Transaction datasets are parsed and analyzed entirely inside your browser's local sandbox. No raw financial account identifiers or transaction figures are sent to any external server.
          </Notice>
        </div>
      )}

      {/* STEP 2: COLUMN MAPPING & PREVIEW */}
      {step === "mapping" && parsedTable && (
        <div className="analysis-mapping-flow">
          <Panel title={`Configure Schema Mapping: ${fileName}`} tag="SCHEMA / MAPPING">
            <div className="panel-body">
              <p style={{ color: "#a6a6a6", marginBottom: "20px" }}>
                Map your dataset's columns to GraphFin's transaction schema. Source account, destination account, and amount are mandatory to build the directed transfer network.
              </p>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: "16px",
                  marginBottom: "28px",
                }}
              >
                {/* Source Column */}
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#b44a50", fontWeight: 600, marginBottom: "4px" }}>
                    SOURCE ACCOUNT (SENDER) * REQUIRED
                  </label>
                  <select
                    style={{ width: "100%", background: "#171719", color: "#f5f5f5", border: "1px solid #303034", padding: "8px" }}
                    value={mapping.sourceCol}
                    onChange={(e) => setMapping({ ...mapping, sourceCol: e.target.value })}
                  >
                    <option value="">-- Select Column --</option>
                    {parsedTable.headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Destination Column */}
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#b44a50", fontWeight: 600, marginBottom: "4px" }}>
                    DESTINATION ACCOUNT (RECEIVER) * REQUIRED
                  </label>
                  <select
                    style={{ width: "100%", background: "#171719", color: "#f5f5f5", border: "1px solid #303034", padding: "8px" }}
                    value={mapping.destinationCol}
                    onChange={(e) => setMapping({ ...mapping, destinationCol: e.target.value })}
                  >
                    <option value="">-- Select Column --</option>
                    {parsedTable.headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Amount Column */}
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#b44a50", fontWeight: 600, marginBottom: "4px" }}>
                    TRANSACTION AMOUNT * REQUIRED
                  </label>
                  <select
                    style={{ width: "100%", background: "#171719", color: "#f5f5f5", border: "1px solid #303034", padding: "8px" }}
                    value={mapping.amountCol}
                    onChange={(e) => setMapping({ ...mapping, amountCol: e.target.value })}
                  >
                    <option value="">-- Select Column --</option>
                    {parsedTable.headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Transaction ID */}
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#a6a6a6", marginBottom: "4px" }}>
                    TRANSACTION ID (OPTIONAL)
                  </label>
                  <select
                    style={{ width: "100%", background: "#171719", color: "#f5f5f5", border: "1px solid #303034", padding: "8px" }}
                    value={mapping.transactionIdCol || ""}
                    onChange={(e) => setMapping({ ...mapping, transactionIdCol: e.target.value })}
                  >
                    <option value="">Auto-generate index</option>
                    {parsedTable.headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Timestamp */}
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#a6a6a6", marginBottom: "4px" }}>
                    TIMESTAMP / STEP (OPTIONAL)
                  </label>
                  <select
                    style={{ width: "100%", background: "#171719", color: "#f5f5f5", border: "1px solid #303034", padding: "8px" }}
                    value={mapping.timestampCol || ""}
                    onChange={(e) => setMapping({ ...mapping, timestampCol: e.target.value })}
                  >
                    <option value="">None</option>
                    {parsedTable.headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Fraud Label */}
                <div>
                  <label style={{ display: "block", fontSize: "11px", color: "#a6a6a6", marginBottom: "4px" }}>
                    KNOWN FRAUD LABEL (OPTIONAL)
                  </label>
                  <select
                    style={{ width: "100%", background: "#171719", color: "#f5f5f5", border: "1px solid #303034", padding: "8px" }}
                    value={mapping.labelCol || ""}
                    onChange={(e) => setMapping({ ...mapping, labelCol: e.target.value })}
                  >
                    <option value="">Unlabeled (Structural Anomaly Only)</option>
                    {parsedTable.headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Data Preview Table */}
              <div style={{ marginBottom: "24px" }}>
                <span className="eyebrow technical" style={{ display: "block", marginBottom: "8px" }}>
                  DATASET SAMPLE PREVIEW (FIRST 5 ROWS)
                </span>
                <div style={{ overflowX: "auto", border: "1px solid #303034" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", fontFamily: "IBM Plex Mono, monospace" }}>
                    <thead>
                      <tr style={{ background: "#101012", borderBottom: "1px solid #303034" }}>
                        {parsedTable.headers.map((h) => (
                          <th key={h} style={{ padding: "8px 12px", textAlign: "left", color: "#f5f5f5" }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {parsedTable.rows.slice(0, 5).map((row, rIdx) => (
                        <tr key={rIdx} style={{ borderBottom: "1px solid #202023" }}>
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} style={{ padding: "6px 12px", color: "#a6a6a6" }}>
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: "12px" }}>
                <button
                  type="button"
                  onClick={handleReset}
                  style={{ background: "#171719", color: "#a6a6a6", border: "1px solid #303034", padding: "10px 20px" }}
                >
                  CANCEL
                </button>
                <button
                  type="button"
                  disabled={!mapping.sourceCol || !mapping.destinationCol || !mapping.amountCol || isProcessing}
                  onClick={handleRunAnalysis}
                  style={{
                    background: "#b44a50",
                    color: "#ffffff",
                    border: "none",
                    fontWeight: 600,
                    padding: "10px 24px",
                    cursor: "pointer",
                  }}
                >
                  {isProcessing ? "BUILDING TRANSACTION NETWORK..." : "EXECUTE GRAPH ANOMALY ANALYSIS ↗"}
                </button>
              </div>
            </div>
          </Panel>
        </div>
      )}

      {/* STEP 3: RESULTS DASHBOARD */}
      {step === "results" && result && (
        <div className="analysis-results-flow">
          {/* Header Controls */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "20px",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px", flexWrap: "wrap" }}>
                <span className="eyebrow red">ANALYSIS COMPLETE</span>
                <span
                  style={{
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: "10px",
                    padding: "2px 8px",
                    borderRadius: "3px",
                    background:
                      backendStatus === "ml_verified" || backendStatus === "synced"
                        ? "#132318"
                        : backendStatus === "ml_pending" || backendStatus === "syncing"
                        ? "#231f13"
                        : backendStatus === "ml_failed"
                        ? "#261517"
                        : "#171719",
                    border:
                      backendStatus === "ml_verified" || backendStatus === "synced"
                        ? "1px solid #22c55e"
                        : backendStatus === "ml_pending" || backendStatus === "syncing"
                        ? "1px solid #f59e0b"
                        : backendStatus === "ml_failed"
                        ? "1px solid #ef4444"
                        : "1px solid #303034",
                    color:
                      backendStatus === "ml_verified" || backendStatus === "synced"
                        ? "#4ade80"
                        : backendStatus === "ml_pending" || backendStatus === "syncing"
                        ? "#fbbf24"
                        : backendStatus === "ml_failed"
                        ? "#f87171"
                        : "#f5f5f5",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                  }}
                >
                  <span
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "50%",
                      background:
                        backendStatus === "ml_verified" || backendStatus === "synced"
                          ? "#22c55e"
                          : backendStatus === "ml_pending" || backendStatus === "syncing"
                          ? "#f59e0b"
                          : backendStatus === "ml_failed"
                          ? "#ef4444"
                          : "#b44a50",
                      display: "inline-block",
                    }}
                  />
                  {backendStatus === "ml_verified" || backendStatus === "synced"
                    ? `Backend ML completed and verified: ${result.backendModel || backendModel}`
                    : backendStatus === "ml_pending" || backendStatus === "syncing"
                    ? "Backend ML pending..."
                    : backendStatus === "ml_unavailable"
                    ? "Backend ML unavailable"
                    : backendStatus === "ml_failed"
                    ? "Backend ML failed"
                    : "Client-side heuristic analysis completed"}
                </span>
              </div>
              <h2 style={{ margin: 0 }}>{result.summary.datasetName}</h2>
            </div>
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => generateDatasetPdfReport(result, result.backendModel || backendModel)}
                style={{
                  background: "#842d35",
                  color: "#ffffff",
                  border: "1px solid #b44a50",
                  padding: "8px 16px",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  borderRadius: "2px",
                }}
              >
                📄 DOWNLOAD AUDIT REPORT (PDF)
              </button>
              <button
                type="button"
                onClick={handleExportCsv}
                style={{ background: "#171719", color: "#f5f5f5", border: "1px solid #303034", padding: "8px 14px", fontSize: "12px", cursor: "pointer", borderRadius: "2px" }}
              >
                📥 EXPORT ANOMALIES (CSV)
              </button>
              <button
                type="button"
                onClick={handleExportJson}
                style={{ background: "#171719", color: "#f5f5f5", border: "1px solid #303034", padding: "8px 14px", fontSize: "12px", cursor: "pointer", borderRadius: "2px" }}
              >
                📥 EXPORT SUMMARY (JSON)
              </button>
              <button
                type="button"
                onClick={handleReset}
                style={{ background: "#101012", color: "#a6a6a6", border: "1px solid #303034", padding: "8px 14px", fontSize: "12px", cursor: "pointer", borderRadius: "2px" }}
              >
                ↺ UPLOAD NEW
              </button>
            </div>
          </div>

          {/* Metric KPI Strip */}
          <div className="metrics" style={{ marginBottom: "20px" }}>
            <div className="metric">
              <span className="eyebrow">TRANSACTIONS</span>
              <strong>{fmt(result.summary.totalTransactions, 0)}</strong>
              <small>Total volume: {result.summary.currency === "INR" ? "₹" : (result.summary.currency ? result.summary.currency + " " : "$")}{fmt(result.summary.totalVolume, 2)}</small>
            </div>
            <div className="metric">
              <span className="eyebrow">UNIQUE ACCOUNTS</span>
              <strong>{fmt(result.summary.uniqueAccounts, 0)}</strong>
              <small>{fmt(result.summary.uniqueEdges, 0)} directed transfer edges</small>
            </div>
            <div className="metric">
              <span className="eyebrow">SUSPICIOUS ACCOUNTS</span>
              <strong style={{ color: "#e05252" }}>
                {fmt(result.summary.suspiciousAccountCount, 0)}
              </strong>
              <small>Score &ge; 0.60, or multi-pattern, or |z| &ge; 3.0</small>
            </div>
            <div className="metric">
              <span className="eyebrow">TOPOLOGICAL PATTERNS</span>
              <strong>
                {result.summary.patternsDetected.fanOutCount +
                  result.summary.patternsDetected.fanInCount +
                  result.summary.patternsDetected.cycleCount}
              </strong>
              <small>
                {result.summary.patternsDetected.fanOutCount} Fan-out | {result.summary.patternsDetected.fanInCount} Fan-in | {result.summary.patternsDetected.cycleCount} Cycle
              </small>
            </div>
          </div>

          {/* Backend ML Verification Section with Explicit Privacy & Consent Safeguards */}
          <Panel
            title="Backend Machine Learning Verification (Isolation Forest)"
            tag={
              backendStatus === "ml_verified" || backendStatus === "synced"
                ? "ML VERIFIED"
                : backendStatus === "ml_pending" || backendStatus === "syncing"
                ? "ML PENDING"
                : backendStatus === "ml_unavailable"
                ? "ML UNAVAILABLE"
                : backendStatus === "ml_failed"
                ? "ML FAILED"
                : "CONSENT REQUIRED"
            }
          >
            <div className="panel-body" style={{ padding: "16px 20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "20px", flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: "280px" }}>
                  <p style={{ margin: "0 0 10px 0", fontSize: "12px", color: "#f5f5f5", lineHeight: 1.5 }}>
                    {backendStatus === "ml_verified" || backendStatus === "synced" ? (
                      <>
                        <strong style={{ color: "#4ade80" }}>✓ Verified Isolation Forest Execution:</strong>{" "}
                        Trained on {result.summary.uniqueAccounts} entities across canonical 19 graph, behavioral, and temporal features (100 trees, 0.05 contamination).
                      </>
                    ) : (
                      <>
                        <strong>Privacy Safeguard:</strong> This dataset was analyzed entirely in local browser memory. To fit GraphFin's 19-dimensional scikit-learn Isolation Forest on the remote Render backend, explicit consent is required.
                      </>
                    )}
                  </p>
                  <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", fontSize: "11px", color: "#a6a6a6" }}>
                    <span>• <strong>Destination:</strong> https://graphfin.onrender.com/api/v1</span>
                    <span>• <strong>Storage:</strong> Ephemeral in-memory (no permanent retention)</span>
                    <span>• <strong>Budget:</strong> Max 15,000 transactions, 10 MB payload</span>
                  </div>
                </div>

                <div>
                  {backendStatus === "ml_verified" || backendStatus === "synced" ? (
                    <span
                      style={{
                        padding: "8px 14px",
                        background: "#132318",
                        border: "1px solid #22c55e",
                        color: "#4ade80",
                        fontSize: "11px",
                        fontWeight: 600,
                        fontFamily: "IBM Plex Mono, monospace",
                        borderRadius: "2px",
                      }}
                    >
                      ✓ MODEL ACTIVE
                    </span>
                  ) : (
                    <button
                      type="button"
                      disabled={isProcessing || backendStatus === "ml_pending" || backendStatus === "syncing"}
                      onClick={async () => {
                        const confirmed = window.confirm(
                          "GraphFin Privacy Consent:\n\n" +
                          "Do you authorize transmitting this dataset to https://graphfin.onrender.com for remote Isolation Forest fitting?\n\n" +
                          "• Purpose: 19 canonical graph feature extraction & Isolation Forest inference\n" +
                          "• Ephemeral: Data is kept in memory during model fitting and NOT permanently saved\n" +
                          "• Limits: Max 15,000 transactions, max 10 MB"
                        );
                        if (confirmed) {
                          await syncSessionToBackend(result, rawCsvText || result.summary.rawCsvContent, true);
                        }
                      }}
                      style={{
                        background: backendStatus === "ml_pending" || backendStatus === "syncing" ? "#202023" : "#842d35",
                        color: "#ffffff",
                        border: "1px solid #b44a50",
                        padding: "8px 16px",
                        fontSize: "11px",
                        fontWeight: 600,
                        cursor: backendStatus === "ml_pending" || backendStatus === "syncing" ? "not-allowed" : "pointer",
                        borderRadius: "2px",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {backendStatus === "ml_pending" || backendStatus === "syncing"
                        ? "FITTING ISOLATION FOREST..."
                        : "TRANSMIT & VERIFY WITH BACKEND ML ↗"}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </Panel>

          {/* Ground Truth Validation Box (if label provided) */}
          {result.summary.evaluation && (
            <Panel title="Empirical Ground-Truth Evaluation" tag="VALIDATION / LABELS">
              <div className="panel-body">
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px" }}>
                  <div className="metric">
                    <span className="eyebrow">LABELED FRAUD</span>
                    <strong>{result.summary.evaluation.positives}</strong>
                    <small>out of {result.summary.evaluation.labeledTotal} accounts</small>
                  </div>
                  <div className="metric">
                    <span className="eyebrow">PRECISION</span>
                    <strong>{(result.summary.evaluation.precision * 100).toFixed(1)}%</strong>
                    <small>{result.summary.evaluation.truePositives} TP / {result.summary.evaluation.falsePositives} FP</small>
                  </div>
                  <div className="metric">
                    <span className="eyebrow">RECALL</span>
                    <strong>{(result.summary.evaluation.recall * 100).toFixed(1)}%</strong>
                    <small>Fraud capture rate</small>
                  </div>
                  <div className="metric">
                    <span className="eyebrow">F1-SCORE</span>
                    <strong>{result.summary.evaluation.f1Score.toFixed(3)}</strong>
                    <small>Harmonic mean</small>
                  </div>
                </div>
              </div>
            </Panel>
          )}

          {/* Two-Column Grid: Accounts Ranking & Interactive Graph Canvas */}
          <div className="analysis-workbench-grid">
            {/* Column 1: Suspicious Accounts Table */}
            <Panel title="Flagged Accounts & Anomaly Ranking" tag="RANKING / RISK">
              <div className="panel-body" style={{ padding: "16px" }}>
                {/* Filter and Search Bar */}
                <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
                  <input
                    type="text"
                    placeholder="Search account ID..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      flex: 1,
                      minWidth: "160px",
                      background: "#080809",
                      color: "#f5f5f5",
                      border: "1px solid #303034",
                      padding: "6px 10px",
                      fontSize: "12px",
                      fontFamily: "IBM Plex Mono, monospace",
                    }}
                  />
                  <select
                    value={filterPattern}
                    onChange={(e) => setFilterPattern(e.target.value)}
                    style={{
                      background: "#080809",
                      color: "#f5f5f5",
                      border: "1px solid #303034",
                      padding: "6px 10px",
                      fontSize: "12px",
                    }}
                  >
                    <option value="ALL">All Patterns</option>
                    <option value="FAN_OUT">Fan-Out (Dispersal)</option>
                    <option value="FAN_IN">Fan-In (Collection)</option>
                    <option value="CYCLE">Circular / Reciprocal</option>
                    <option value="VOLUME_OUTLIER">Volume Outlier</option>
                  </select>
                </div>

                <div style={{ maxHeight: "420px", overflowY: "auto", border: "1px solid #303034" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace" }}>
                    <thead>
                      <tr style={{ background: "#101012", borderBottom: "1px solid #303034", position: "sticky", top: 0 }}>
                        <th style={{ padding: "8px", textAlign: "left" }}>Account ID</th>
                        <th style={{ padding: "8px", textAlign: "right" }}>Score</th>
                        <th style={{ padding: "8px", textAlign: "center" }}>Deg (In/Out)</th>
                        <th style={{ padding: "8px", textAlign: "left" }}>Patterns</th>
                      </tr>
                    </thead>
                    <tbody>
                      {displayedAccounts.length === 0 ? (
                        <tr>
                          <td colSpan={4} style={{ padding: "24px", textAlign: "center", color: "#77777d" }}>
                            No accounts match the current filter.
                          </td>
                        </tr>
                      ) : (
                        displayedAccounts.map((acc) => {
                          const isSel = acc.id === selectedNodeId;
                          return (
                            <tr
                              key={acc.id}
                              onClick={() => setSelectedNodeId(acc.id)}
                              style={{
                                cursor: "pointer",
                                background: isSel ? "#202023" : "transparent",
                                borderBottom: "1px solid #171719",
                              }}
                            >
                              <td style={{ padding: "6px 8px", color: isSel ? "#fff" : "#f5f5f5", fontWeight: isSel ? 600 : 400 }}>
                                {acc.id.length > 16 ? acc.id.slice(0, 14) + "…" : acc.id}
                              </td>
                              <td
                                style={{
                                  padding: "6px 8px",
                                  textAlign: "right",
                                  color: acc.anomalyScore >= 0.7 ? "#e05252" : acc.anomalyScore >= 0.45 ? "#b44a50" : "#a6a6a6",
                                  fontWeight: 600,
                                }}
                              >
                                {acc.anomalyScore.toFixed(3)}
                              </td>
                              <td style={{ padding: "6px 8px", textAlign: "center", color: "#a6a6a6" }}>
                                {acc.inDegree}/{acc.outDegree}
                              </td>
                              <td style={{ padding: "6px 8px" }}>
                                {acc.patterns.map((p) => (
                                  <span
                                    key={p}
                                    style={{
                                      display: "inline-block",
                                      background: "#842d35",
                                      color: "#fff",
                                      fontSize: "9px",
                                      padding: "1px 4px",
                                      marginRight: "4px",
                                      borderRadius: "1px",
                                    }}
                                  >
                                    {p.replace("_", "-")}
                                  </span>
                                ))}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </Panel>

            {/* Column 2: Interactive Graph Visualization & Inspector */}
            <div>
              <Panel title="Transaction Topology Visualization" tag="GRAPH / VISUALIZER">
                <div className="panel-body" style={{ padding: 0 }}>
                  <AnalysisGraphCanvas
                    accounts={result.accounts}
                    edges={result.edges}
                    selectedNode={selectedNodeId}
                    onSelectNode={(id) => setSelectedNodeId(id)}
                  />
                </div>
              </Panel>

              {/* Selected Account Inspector */}
              {selectedAccount && (
                <Panel title={`Account Inspector: ${selectedAccount.id}`} tag="ENTITY / DETAILS">
                  <div className="panel-body">
                    {/* Responsive Metrics Grid */}
                    <div className="inspector-metrics-grid">
                      <div className={`inspector-metric-card ${selectedAccount.anomalyScore >= 0.6 ? "alert" : ""}`}>
                        <span className="metric-label">HEURISTIC SCORE</span>
                        <div
                          className="metric-number"
                          style={{ color: selectedAccount.anomalyScore >= 0.6 ? "#e05252" : "#f5f5f5" }}
                        >
                          {selectedAccount.anomalyScore.toFixed(3)}
                        </div>
                        <span className="metric-hint">
                          {selectedAccount.anomalyScore >= 0.7
                            ? "Critical risk tier"
                            : selectedAccount.anomalyScore >= 0.6
                            ? "Suspicious activity"
                            : "Baseline activity"}
                        </span>
                      </div>

                      {selectedAccount.mlScore !== undefined && (
                        <div className={`inspector-metric-card ${selectedAccount.mlScore >= 0.5 ? "alert" : ""}`}>
                          <span className="metric-label">ISOLATION FOREST</span>
                          <div
                            className="metric-number"
                            style={{ color: selectedAccount.mlScore >= 0.5 ? "#e05252" : "#4ade80" }}
                          >
                            {selectedAccount.mlScore.toFixed(3)}
                          </div>
                          <span className="metric-hint">
                            Decision depth: {selectedAccount.mlStatus || "verified"}
                          </span>
                        </div>
                      )}

                      <div className="inspector-metric-card">
                        <span className="metric-label">TOPOLOGICAL DEGREE</span>
                        <div className="metric-number">
                          {selectedAccount.inDegree} <span style={{ fontSize: "11px", color: "#a6a6a6" }}>IN</span> / {selectedAccount.outDegree} <span style={{ fontSize: "11px", color: "#a6a6a6" }}>OUT</span>
                        </div>
                        <span className="metric-hint">
                          {selectedAccount.totalDegree} total transfer edges
                        </span>
                      </div>

                      <div className={`inspector-metric-card ${selectedAccount.netFlow < 0 ? "alert" : "positive"}`}>
                        <span className="metric-label">NET FLOW VOLUME</span>
                        <div
                          className="metric-number"
                          style={{
                            color: selectedAccount.netFlow < 0 ? "#e05252" : "#4ade80",
                            wordBreak: "break-all",
                          }}
                        >
                          {selectedAccount.netFlow < 0 ? "-" : "+"}{result.summary.currency === "INR" ? "₹" : (result.summary.currency ? result.summary.currency + " " : "$")}{fmt(Math.abs(selectedAccount.netFlow), 2)}
                        </div>
                        <span className="metric-hint">
                          {selectedAccount.netFlow < 0 ? "Net outflow (dispersal)" : "Net inflow (accumulation)"}
                        </span>
                      </div>
                    </div>

                    {/* Detected Patterns Strip */}
                    {selectedAccount.patterns.length > 0 && (
                      <div className="inspector-patterns-strip">
                        {selectedAccount.patterns.map((p) => (
                          <span key={p} className="inspector-pattern-badge">
                            <span>⚠</span> {p.replace("_", " ")}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Counterparty Table */}
                    <div>
                      <span className="eyebrow technical" style={{ display: "block", marginBottom: "8px" }}>
                        TOP TRANSFER COUNTERPARTIES ({selectedAccount.counterparties.length})
                      </span>
                      {selectedAccount.counterparties.length === 0 ? (
                        <div style={{ color: "#77777d", fontSize: "11px", fontFamily: "IBM Plex Mono, monospace" }}>
                          No direct counterparty transactions recorded.
                        </div>
                      ) : (
                        <div className="counterparties-list-container">
                          <table className="counterparty-table">
                            <thead>
                              <tr>
                                <th style={{ textAlign: "left", width: "80px" }}>Flow</th>
                                <th style={{ textAlign: "left" }}>Counterparty ID</th>
                                <th style={{ textAlign: "right" }}>Volume</th>
                                <th style={{ textAlign: "right", width: "70px" }}>Count</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedAccount.counterparties.map((cp) => (
                                <tr
                                  key={cp.id}
                                  onClick={() => setSelectedNodeId(cp.id)}
                                  style={{ cursor: "pointer" }}
                                >
                                  <td>
                                    <span className={`direction-badge ${cp.direction}`}>
                                      {cp.direction === "out" ? "OUT →" : "← IN"}
                                    </span>
                                  </td>
                                  <td style={{ color: "#f5f5f5", fontWeight: 500 }}>
                                    {cp.id}
                                  </td>
                                  <td style={{ textAlign: "right", color: "#f5f5f5", fontVariantNumeric: "tabular-nums" }}>
                                    {(activeSession?.summary.currency === "INR" ? "₹" : "$")}{fmt(cp.totalAmount ?? cp.amount ?? ((cp.inAmount ?? 0) + (cp.outAmount ?? 0)), 2)}
                                  </td>
                                  <td style={{ textAlign: "right", color: "#a6a6a6" }}>
                                    {cp.count ?? ((cp.inCount ?? 0) + (cp.outCount ?? 0))} tx
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>
                </Panel>
              )}
            </div>
          </div>

          <Notice>
            <strong>Scientific Note:</strong> Anomaly scores reflect deterministic topological and flow metrics (degree extremity, volume outliers, fan-in/out structures, and cycle participation). They are derived empirically from the submitted network without fabricating opaque pre-trained model claims.
          </Notice>
        </div>
      )}
    </>
  );
}
