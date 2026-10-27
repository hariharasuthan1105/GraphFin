import { useState } from "react";
import { Heading, Panel, Notice, Qualifications } from "../ui";
import { useSession } from "../sessionContext";
import { DatasetReportDownload } from "../DatasetReportDownload";
import { generateDatasetPdfReport } from "../datasetAnalysis/reportGenerator";

export default function Reports() {
  const { activeSession, loadBenchmarkSample, backendModel } = useSession();
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  // Generate downloadable JSON Audit Package for the uploaded session
  const exportSessionJson = () => {
    if (!activeSession) return;
    const dataStr =
      "data:text/json;charset=utf-8," +
      encodeURIComponent(
        JSON.stringify(
          {
            audit_metadata: {
              title: "GraphFin Financial Network Anomaly Audit Report",
              generator: "GraphFin In-Browser Deterministic Analysis Engine v2.0",
              timestamp: activeSession.summary.processedAt,
              dataset_name: activeSession.summary.datasetName,
              file_size_bytes: activeSession.summary.fileSizeBytes,
            },
            network_summary: activeSession.summary,
            flagged_anomalies: activeSession.topAnomalies,
            accounts_profiled: activeSession.accounts.map((a) => ({
              account_id: a.id,
              anomaly_score: a.anomalyScore,
              in_degree: a.inDegree,
              out_degree: a.outDegree,
              net_flow_volume: a.netFlow,
              detected_patterns: a.patterns,
            })),
          },
          null,
          2,
        ),
      );

    const anchor = document.createElement("a");
    anchor.setAttribute("href", dataStr);
    anchor.setAttribute(
      "download",
      `graphfin_audit_report_${activeSession.summary.datasetName.replace(/\.[^/.]+$/, "")}.json`,
    );
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setDownloadSuccess("JSON audit package successfully exported.");
    setTimeout(() => setDownloadSuccess(null), 3000);
  };

  // Generate downloadable CSV Anomaly Rankings
  const exportAnomaliesCsv = () => {
    if (!activeSession) return;
    const header = [
      "rank",
      "account_id",
      "anomaly_score",
      "in_degree",
      "out_degree",
      "total_sent",
      "total_received",
      "net_flow",
      "patterns",
    ].join(",");

    const rows = activeSession.accounts
      .sort((a, b) => b.anomalyScore - a.anomalyScore)
      .map((acc, idx) =>
        [
          idx + 1,
          `"${acc.id}"`,
          acc.anomalyScore.toFixed(4),
          acc.inDegree,
          acc.outDegree,
          acc.totalSent.toFixed(2),
          acc.totalReceived.toFixed(2),
          acc.netFlow.toFixed(2),
          `"${acc.patterns.join(";")}"`,
        ].join(","),
      );

    const csvContent = "data:text/csv;charset=utf-8," + encodeURIComponent([header, ...rows].join("\n"));
    const anchor = document.createElement("a");
    anchor.setAttribute("href", csvContent);
    anchor.setAttribute(
      "download",
      `graphfin_anomalies_${activeSession.summary.datasetName.replace(/\.[^/.]+$/, "")}.csv`,
    );
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setDownloadSuccess("CSV anomaly ranking exported.");
    setTimeout(() => setDownloadSuccess(null), 3000);
  };

  // Open printable HTML executive audit summary
  const printExecutiveSummary = () => {
    if (!activeSession) return;
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;

    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>GraphFin Executive Audit Report - ${activeSession.summary.datasetName}</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 40px; color: #1e293b; line-height: 1.5; }
          h1 { font-size: 20px; border-bottom: 2px solid #0f172a; padding-bottom: 8px; margin-bottom: 4px; }
          .subtitle { color: #64748b; font-size: 12px; margin-bottom: 24px; font-family: monospace; }
          .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
          .kpi-card { border: 1px solid #cbd5e1; padding: 12px; border-radius: 4px; }
          .kpi-val { font-size: 18px; font-weight: 700; color: #0f172a; }
          .kpi-label { font-size: 11px; text-transform: uppercase; color: #64748b; margin-top: 4px; }
          table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 12px; }
          th { text-align: left; padding: 8px; border-bottom: 2px solid #cbd5e1; background: #f8fafc; font-family: monospace; }
          td { padding: 8px; border-bottom: 1px solid #e2e8f0; font-family: monospace; }
          .disclaimer { margin-top: 32px; border-top: 1px solid #cbd5e1; padding-top: 12px; font-size: 11px; color: #64748b; }
        </style>
      </head>
      <body>
        <h1>GraphFin — Transaction Network Anomaly Audit Report</h1>
        <div class="subtitle">DATASET: ${activeSession.summary.datasetName} · PROCESSED: ${activeSession.summary.processedAt}</div>
        
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-val">${activeSession.summary.uniqueAccounts.toLocaleString()}</div>
            <div class="kpi-label">Accounts Profiled</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val">${activeSession.summary.totalTransactions.toLocaleString()}</div>
            <div class="kpi-label">Transactions Parsed</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val">$${activeSession.summary.totalVolume.toLocaleString("en-US", { maximumFractionDigits: 2 })}</div>
            <div class="kpi-label">Total Transfer Volume</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-val" style="color: #e11d48;">${activeSession.summary.suspiciousAccountCount}</div>
            <div class="kpi-label">Flagged Anomalies</div>
          </div>
        </div>

        <h2>Top Flagged Accounts & Anomaly Indicators</h2>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Account ID</th>
              <th>Score</th>
              <th>In/Out Deg</th>
              <th>Net Flow</th>
              <th>Topological Patterns</th>
            </tr>
          </thead>
          <tbody>
            ${activeSession.topAnomalies
              .slice(0, 15)
              .map(
                (a, i) => `
              <tr>
                <td>${i + 1}</td>
                <td><strong>${a.id}</strong></td>
                <td style="color: ${a.anomalyScore >= 0.7 ? "#e11d48" : "#d97706"};">${a.anomalyScore.toFixed(3)}</td>
                <td>${a.inDegree} in / ${a.outDegree} out</td>
                <td>${a.netFlow < 0 ? "-" : "+"}$${Math.abs(a.netFlow).toLocaleString()}</td>
                <td>${a.patterns.join(", ") || "Elevated Degree"}</td>
              </tr>
            `,
              )
              .join("")}
          </tbody>
        </table>

        <div class="disclaimer">
          <strong>Methodology Disclosure:</strong> Anomaly rankings are derived from deterministic topological and transaction flow metrics (in/out degree asymmetry, volume outliers, directed fan-in/fan-out, and cycle participation). These metrics indicate structural network anomalies and do not constitute legal determinations of financial misconduct.
        </div>
      </body>
      </html>
    `;

    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 250);
  };

  return (
    <div className="research-page reports-page">
      <Heading index="11" title="Audit reports & evidence downloads">
        Download verified research PDF reports for benchmark datasets and export structured audit packages from your interactive analysis session.
      </Heading>

      <Qualifications />

      {downloadSuccess && (
        <div
          style={{
            background: "#171719",
            color: "#ffffff",
            border: "1px solid #b44a50",
            borderRadius: "4px",
            padding: "10px 14px",
            marginBottom: "16px",
            fontFamily: "IBM Plex Mono, monospace",
            fontSize: "12px",
          }}
        >
          ✓ {downloadSuccess}
        </div>
      )}

      {/* Uploaded Session Audit Export Card */}
      <Panel title="Interactive Analysis Audit Report" tag="SESSION EXPORT">
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
                  <h3 style={{ margin: "0 0 4px 0", fontSize: "14px", color: "#f8fafc" }}>
                    Active Dataset: {activeSession.summary.datasetName}
                  </h3>
                  <span
                    style={{
                      fontFamily: "IBM Plex Mono, monospace",
                      fontSize: "11px",
                      color: "#94a3b8",
                    }}
                  >
                    {activeSession.summary.uniqueAccounts} accounts ·{" "}
                    {activeSession.summary.totalTransactions} transactions ·{" "}
                    {activeSession.summary.suspiciousAccountCount} anomalies
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
                  <b style={{ color: "#c04b52" }}>●</b> AUDIT READY
                </span>
              </div>

              <p
                style={{
                  fontSize: "12px",
                  color: "#94a3b8",
                  lineHeight: 1.5,
                  margin: "0 0 16px 0",
                }}
              >
                Export complete anomaly rankings, network metrics, detected pattern motifs, and
                counterparty relationships in standard structured formats.
              </p>

              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center" }}>
                <button
                  type="button"
                  onClick={() => {
                    generateDatasetPdfReport(activeSession, activeSession.backendModel || backendModel);
                    setDownloadSuccess("Institutional PDF Audit Report generated and downloaded.");
                    setTimeout(() => setDownloadSuccess(null), 3000);
                  }}
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
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  📄 Download Audit Report (PDF)
                </button>

                <button
                  type="button"
                  onClick={exportSessionJson}
                  style={{
                    background: "#171719",
                    color: "#f5f5f5",
                    border: "1px solid #303034",
                    padding: "8px 16px",
                    borderRadius: "4px",
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  📥 Export JSON Audit Package
                </button>

                <button
                  type="button"
                  onClick={exportAnomaliesCsv}
                  style={{
                    background: "#171719",
                    color: "#f5f5f5",
                    border: "1px solid #303034",
                    padding: "8px 16px",
                    borderRadius: "4px",
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: "11px",
                    cursor: "pointer",
                  }}
                >
                  📥 Export CSV Anomaly Rankings
                </button>

                <button
                  type="button"
                  onClick={printExecutiveSummary}
                  style={{
                    background: "#171719",
                    color: "#f5f5f5",
                    border: "1px solid #303034",
                    padding: "8px 16px",
                    borderRadius: "4px",
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: "11px",
                    cursor: "pointer",
                  }}
                >
                  🖨️ Printable Executive Summary
                </button>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "16px 0" }}>
              <p style={{ fontSize: "12px", color: "#94a3b8", margin: "0 0 12px 0" }}>
                No active session dataset loaded. Load the synthetic benchmark sample or upload a
                transaction file to generate an audit report.
              </p>
              <button
                type="button"
                onClick={loadBenchmarkSample}
                style={{
                  background: "#b44a50",
                  color: "#ffffff",
                  border: "1px solid #842d35",
                  padding: "6px 14px",
                  borderRadius: "4px",
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                ✦ Load Benchmark Sample Dataset
              </button>
            </div>
          )}
        </div>
      </Panel>

      {/* Historical Research PDF Reports */}
      <Panel title="Historical Research Dataset Reports (PDF)" tag="PEER EVIDENCE">
        <div className="panel-body">
          <p
            style={{
              fontSize: "12px",
              color: "#94a3b8",
              lineHeight: 1.6,
              margin: "0 0 16px 0",
            }}
          >
            Download official research audit documents for the historical benchmark datasets.
            Reports include verified record counts, label provenance status, cross-dataset
            limitations, and cryptographic checksums.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "12px",
            }}
          >
            <div
              style={{
                background: "#08090d",
                border: "1px solid #1a1e28",
                borderRadius: "4px",
                padding: "14px",
              }}
            >
              <div
                style={{
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#f8fafc",
                  marginBottom: "4px",
                }}
              >
                IBM AML 5k Dataset Report
              </div>
              <div
                style={{
                  fontSize: "11px",
                  color: "#94a3b8",
                  marginBottom: "12px",
                  fontFamily: "IBM Plex Mono, monospace",
                }}
              >
                5,000 accounts · 31,463 transfers · 20 positives
              </div>
              <DatasetReportDownload datasetId="ibm-5k" />
            </div>

            <div
              style={{
                background: "#08090d",
                border: "1px solid #1a1e28",
                borderRadius: "4px",
                padding: "14px",
              }}
            >
              <div
                style={{
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#f8fafc",
                  marginBottom: "4px",
                }}
              >
                IBM AML 50k Dataset Report
              </div>
              <div
                style={{
                  fontSize: "11px",
                  color: "#94a3b8",
                  marginBottom: "12px",
                  fontFamily: "IBM Plex Mono, monospace",
                }}
              >
                49,992 accounts · 353,850 transfers · 249 positives
              </div>
              <DatasetReportDownload datasetId="ibm-50k" />
            </div>

            <div
              style={{
                background: "#08090d",
                border: "1px solid #1a1e28",
                borderRadius: "4px",
                padding: "14px",
              }}
            >
              <div
                style={{
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#f8fafc",
                  marginBottom: "4px",
                }}
              >
                PaySim Anomaly Audit Report
              </div>
              <div
                style={{
                  fontSize: "11px",
                  color: "#94a3b8",
                  marginBottom: "12px",
                  fontFamily: "IBM Plex Mono, monospace",
                }}
              >
                547,686 accounts · 1,832 label disagreements
              </div>
              <DatasetReportDownload datasetId="paysim" />
            </div>
          </div>
        </div>
      </Panel>

      <Notice>
        <strong style={{ display: "block", marginBottom: "4px" }}>Audit Integrity Guarantee</strong>
        <p style={{ margin: 0, fontSize: "12px", lineHeight: 1.5 }}>
          All exported audit reports adhere strictly to reproducible schemas. Interactive analysis
          exports are derived on-the-fly from verified client-side graph structures, ensuring zero
          data leakage to external networks.
        </p>
      </Notice>
    </div>
  );
}
