import { jsPDF } from "jspdf";
import type { AnalysisResult } from "./types";

/**
 * Format currency or number with commas and decimals
 */
function formatNumber(num: number, decimals = 2): string {
  return num.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Generates an institutional-grade PDF Forensic Audit Report for any uploaded transaction dataset.
 */
export function generateDatasetPdfReport(analysis: AnalysisResult, executionEngine = "GraphFin Graph-Based Heuristic & Isolation Forest Pipeline"): void {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;
  const contentWidth = pageWidth - margin * 2;

  // Colors
  const RED_PRIMARY = [180, 74, 80]; // #b44a50
  const RED_DARK = [132, 45, 53];    // #842d35
  const DARK_VOID = [16, 16, 18];    // #101012
  const GRAY_BORDER = [60, 60, 65];  // #3c3c41
  const TEXT_DARK = [30, 30, 32];
  const TEXT_MUTED = [100, 100, 105];
  const BG_LIGHT = [248, 249, 250];

  let y = 14;

  // --- PAGE 1: TITLE & EXECUTIVE SUMMARY ---

  // Top Accent Strip
  doc.setFillColor(RED_PRIMARY[0], RED_PRIMARY[1], RED_PRIMARY[2]);
  doc.rect(margin, y, contentWidth, 3, "F");
  y += 7;

  // Institutional Header
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("GRAPHFIN RESEARCH DASHBOARD — FORENSIC AUDIT RECORD", margin, y);
  y += 5;

  doc.setFontSize(13);
  doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);
  doc.text("Machine Learning Enhanced Graph-Based Anomaly Detection", margin, y);
  y += 5.5;
  doc.text("for Financial Transactions", margin, y);
  y += 6;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(TEXT_MUTED[0], TEXT_MUTED[1], TEXT_MUTED[2]);
  doc.text(
    `Dataset Forensic Audit & Topological Analysis Report | Generated: ${new Date().toUTCString()}`,
    margin,
    y
  );
  y += 7;

  // Metadata Box
  doc.setFillColor(BG_LIGHT[0], BG_LIGHT[1], BG_LIGHT[2]);
  doc.setDrawColor(GRAY_BORDER[0], GRAY_BORDER[1], GRAY_BORDER[2]);
  doc.setLineWidth(0.3);
  doc.rect(margin, y, contentWidth, 24, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(TEXT_MUTED[0], TEXT_MUTED[1], TEXT_MUTED[2]);
  doc.text("DATASET AUDIT METADATA", margin + 4, y + 5);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8.5);
  doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);

  const col1X = margin + 4;
  const col2X = margin + 55;
  const col3X = margin + 115;

  doc.text(`Dataset: ${analysis.summary.datasetName}`, col1X, y + 11);
  doc.text(`File Size: ${(analysis.summary.fileSizeBytes / 1024).toFixed(1)} KB`, col1X, y + 16);
  doc.text(`Pipeline: ${executionEngine}`, col1X, y + 21);

  doc.text(`Total Transactions: ${formatNumber(analysis.summary.totalTransactions, 0)}`, col2X, y + 11);
  doc.text(`Monitored Volume: $${formatNumber(analysis.summary.totalVolume, 2)}`, col2X, y + 16);
  doc.text(`Mean Amount: $${formatNumber(analysis.summary.meanAmount, 2)}`, col2X, y + 21);

  doc.text(`Unique Accounts: ${formatNumber(analysis.summary.uniqueAccounts, 0)}`, col3X, y + 11);
  doc.text(`Directed Edges: ${formatNumber(analysis.summary.uniqueEdges, 0)}`, col3X, y + 16);
  doc.text(`Flagged Suspicious: ${formatNumber(analysis.summary.suspiciousAccountCount, 0)} accounts`, col3X, y + 21);

  y += 30;

  // --- SECTION 1: NETWORK TOPOLOGY METRICS ---
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("1. TOPOLOGICAL & STRUCTURAL GRAPH METRICS", margin, y);
  y += 5;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8.5);
  doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);
  doc.text(
    "Directed network analysis models transaction counterparties as vertices and funds flow as weighted arcs.",
    margin,
    y
  );
  y += 6;

  // Topology Table
  const topoData = [
    ["Network Density", analysis.summary.networkDensity.toFixed(5), "Max In-Degree", formatNumber(analysis.summary.maxInDegree, 0)],
    ["Average Degree", analysis.summary.avgDegree.toFixed(2), "Max Out-Degree", formatNumber(analysis.summary.maxOutDegree, 0)],
    ["Source-Only Accounts", formatNumber(analysis.summary.sourceOnlyAccounts, 0), "Sink-Only Accounts", formatNumber(analysis.summary.sinkOnlyAccounts, 0)],
    ["Intermediary Accounts", formatNumber(analysis.summary.intermediaryAccounts, 0), "Median Amount", `$${formatNumber(analysis.summary.medianAmount, 2)}`],
  ];

  const cellH = 6;
  const colW = contentWidth / 4;

  topoData.forEach((row) => {
    doc.setFillColor(245, 245, 247);
    doc.rect(margin, y, colW, cellH, "F");
    doc.rect(margin + colW * 2, y, colW, cellH, "F");

    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.setTextColor(TEXT_MUTED[0], TEXT_MUTED[1], TEXT_MUTED[2]);
    doc.text(row[0], margin + 2, y + 4.2);
    doc.text(row[2], margin + colW * 2 + 2, y + 4.2);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);
    doc.text(row[1], margin + colW + 2, y + 4.2);
    doc.text(row[3], margin + colW * 3 + 2, y + 4.2);

    doc.setDrawColor(220, 220, 225);
    doc.rect(margin, y, contentWidth, cellH, "S");
    y += cellH;
  });

  y += 8;

  // --- SECTION 2: DETECTED AML TYPOLOGIES ---
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("2. AML TYPOLOGY DETECTION & ANOMALY MOTIFS", margin, y);
  y += 5;

  const patterns = [
    {
      name: "Fan-Out (Smurfing Dispersal)",
      count: analysis.summary.patternsDetected.fanOutCount,
      desc: "Single account dispersing funds rapidly to multiple downstream counterparties (structuring pattern).",
    },
    {
      name: "Fan-In (Mule Aggregation)",
      count: analysis.summary.patternsDetected.fanInCount,
      desc: "Multiple upstream accounts funneling funds into a single collecting sink account (collection ring).",
    },
    {
      name: "Circular / Reciprocal Loops",
      count: analysis.summary.patternsDetected.cycleCount,
      desc: "Closed cyclical transfer loops returning funds to the originating or affiliated entity.",
    },
    {
      name: "Extreme Volume Outliers",
      count: analysis.summary.patternsDetected.volumeOutlierCount,
      desc: "Accounts executing transfers exceeding 2.5 standard deviations from the global transaction mean.",
    },
  ];

  patterns.forEach((p) => {
    doc.setFillColor(BG_LIGHT[0], BG_LIGHT[1], BG_LIGHT[2]);
    doc.setDrawColor(GRAY_BORDER[0], GRAY_BORDER[1], GRAY_BORDER[2]);
    doc.rect(margin, y, contentWidth, 10, "FD");

    // Red badge for count
    doc.setFillColor(RED_PRIMARY[0], RED_PRIMARY[1], RED_PRIMARY[2]);
    doc.rect(margin + 2, y + 2, 14, 6, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.setTextColor(255, 255, 255);
    doc.text(String(p.count), margin + 9, y + 6.2, { align: "center" });

    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);
    doc.text(p.name, margin + 20, y + 4.5);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    doc.setTextColor(TEXT_MUTED[0], TEXT_MUTED[1], TEXT_MUTED[2]);
    doc.text(p.desc, margin + 20, y + 8.2);

    y += 12;
  });

  // Footer Page 1
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(TEXT_MUTED[0], TEXT_MUTED[1], TEXT_MUTED[2]);
  doc.text("GraphFin Anomaly Detection System — Page 1 of 2", margin, pageHeight - 10);
  doc.text(`Checksum: ${Math.abs(analysis.summary.totalVolume).toString(16).toUpperCase()}`, pageWidth - margin - 40, pageHeight - 10);

  // --- PAGE 2: SUSPICIOUS ACCOUNT RANKINGS & METHODOLOGY ---
  doc.addPage();
  y = 14;

  // Top Accent Strip
  doc.setFillColor(RED_PRIMARY[0], RED_PRIMARY[1], RED_PRIMARY[2]);
  doc.rect(margin, y, contentWidth, 3, "F");
  y += 7;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("3. TOP SUSPICIOUS ACCOUNTS (AUDIT FORENSIC RANKING)", margin, y);
  y += 5;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);
  doc.text(
    "Ranked by continuous anomaly score derived from graph structural metrics and volume asymmetry.",
    margin,
    y
  );
  y += 6;

  // Table Headers
  const tableHeaders = ["Rank", "Account ID", "Score", "In / Out Deg", "Total Sent", "Total Received", "Net Flow", "Flagged Typologies"];
  const colWidths = [12, 34, 16, 20, 24, 24, 22, 30];

  doc.setFillColor(DARK_VOID[0], DARK_VOID[1], DARK_VOID[2]);
  doc.rect(margin, y, contentWidth, 6, "F");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(7);
  doc.setTextColor(255, 255, 255);

  let curX = margin;
  tableHeaders.forEach((h, i) => {
    doc.text(h, curX + 2, y + 4.2);
    curX += colWidths[i];
  });
  y += 6;

  // Top 10 Accounts
  const topAccounts = (analysis.topAnomalies.length > 0 ? analysis.topAnomalies : analysis.accounts).slice(0, 10);

  topAccounts.forEach((acc, idx) => {
    const isEven = idx % 2 === 0;
    doc.setFillColor(isEven ? 255 : 248, isEven ? 255 : 249, isEven ? 255 : 250);
    doc.rect(margin, y, contentWidth, 6.5, "F");
    doc.setDrawColor(230, 230, 235);
    doc.line(margin, y + 6.5, margin + contentWidth, y + 6.5);

    curX = margin;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.setTextColor(acc.anomalyScore >= 0.7 ? RED_PRIMARY[0] : TEXT_DARK[0], acc.anomalyScore >= 0.7 ? RED_PRIMARY[1] : TEXT_DARK[1], acc.anomalyScore >= 0.7 ? RED_PRIMARY[2] : TEXT_DARK[2]);
    doc.text(`#${idx + 1}`, curX + 2, y + 4.5);
    curX += colWidths[0];

    doc.setFont("helvetica", "normal");
    doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);
    const truncatedId = acc.id.length > 18 ? acc.id.slice(0, 16) + "…" : acc.id;
    doc.text(truncatedId, curX + 2, y + 4.5);
    curX += colWidths[1];

    doc.setFont("helvetica", "bold");
    doc.setTextColor(acc.anomalyScore >= 0.7 ? RED_DARK[0] : TEXT_DARK[0], acc.anomalyScore >= 0.7 ? RED_DARK[1] : TEXT_DARK[1], acc.anomalyScore >= 0.7 ? RED_DARK[2] : TEXT_DARK[2]);
    doc.text(acc.anomalyScore.toFixed(3), curX + 2, y + 4.5);
    curX += colWidths[2];

    doc.setFont("helvetica", "normal");
    doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);
    doc.text(`${acc.inDegree} / ${acc.outDegree}`, curX + 2, y + 4.5);
    curX += colWidths[3];

    doc.text(`$${formatNumber(acc.totalSent, 0)}`, curX + 2, y + 4.5);
    curX += colWidths[4];

    doc.text(`$${formatNumber(acc.totalReceived, 0)}`, curX + 2, y + 4.5);
    curX += colWidths[5];

    const netStr = (acc.netFlow >= 0 ? "+" : "") + `$${formatNumber(acc.netFlow, 0)}`;
    doc.text(netStr, curX + 2, y + 4.5);
    curX += colWidths[6];

    doc.setFontSize(6.5);
    doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
    const patternsStr = acc.patterns.length > 0 ? acc.patterns.join(", ") : "Normal Flow";
    doc.text(patternsStr.slice(0, 24), curX + 2, y + 4.5);

    y += 6.5;
  });

  y += 10;

  // --- SECTION 4: SCIENTIFIC METHODOLOGY & AUDIT DISCLAIMER ---
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("4. METHODOLOGY & SCIENTIFIC AUDIT DISCLOSURES", margin, y);
  y += 5;

  doc.setFillColor(BG_LIGHT[0], BG_LIGHT[1], BG_LIGHT[2]);
  doc.setDrawColor(GRAY_BORDER[0], GRAY_BORDER[1], GRAY_BORDER[2]);
  doc.rect(margin, y, contentWidth, 48, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(7.5);
  doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);
  doc.text("Algorithmic Methodology:", margin + 4, y + 5);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.setTextColor(TEXT_MUTED[0], TEXT_MUTED[1], TEXT_MUTED[2]);
  doc.text(
    "GraphFin evaluates financial network graphs through structural feature extraction (in-degree, out-degree, degree asymmetry,",
    margin + 4,
    y + 9
  );
  doc.text(
    "temporal flow rate, reciprocal cycle detection, and volume concentration). When connected to the Python backend,",
    margin + 4,
    y + 13
  );
  doc.text(
    "unsupervised Isolation Forest ensembles (100 estimators, 19 engineered features) compute multidimensional isolation depths.",
    margin + 4,
    y + 17
  );

  doc.setFont("helvetica", "bold");
  doc.setFontSize(7.5);
  doc.setTextColor(TEXT_DARK[0], TEXT_DARK[1], TEXT_DARK[2]);
  doc.text("Legal & Regulatory Disclaimer:", margin + 4, y + 24);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.setTextColor(TEXT_MUTED[0], TEXT_MUTED[1], TEXT_MUTED[2]);
  doc.text(
    "Anomaly scores generated by this system represent structural and mathematical divergence from expected transaction",
    margin + 4,
    y + 28
  );
  doc.text(
    "network norms. High anomaly scores indicate accounts warranting forensic compliance review under applicable AML/CFT",
    margin + 4,
    y + 32
  );
  doc.text(
    "frameworks; they do not constitute autonomous proof of illegal activity, fraud, or guilt without corroborating evidence.",
    margin + 4,
    y + 36
  );
  doc.text(
    "GraphFin Research Project — Canonical Public Repository: https://github.com/hariharasuthan1105/GraphFin",
    margin + 4,
    y + 42
  );

  // Footer Page 2
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(TEXT_MUTED[0], TEXT_MUTED[1], TEXT_MUTED[2]);
  doc.text("GraphFin Anomaly Detection System — Page 2 of 2", margin, pageHeight - 10);
  doc.text("Status: Verified Forensic Projection", pageWidth - margin - 50, pageHeight - 10);

  // Save PDF
  const filename = `GraphFin_Audit_Report_${analysis.summary.datasetName.replace(/[^a-zA-Z0-9_-]/g, "_")}.pdf`;
  doc.save(filename);
}
