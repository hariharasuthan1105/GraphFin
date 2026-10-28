import { jsPDF } from "jspdf";
import type { AnalysisResult } from "./types";

/**
 * Format number with commas and specified decimals
 */
function formatNumber(num: number, decimals = 2): string {
  if (num === undefined || num === null || isNaN(num)) return "0.00";
  return num.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format currency amount with detected dataset currency label
 */
function formatCurrency(amount: number, currency = "Unknown", decimals = 2): string {
  const formatted = formatNumber(amount, decimals);
  const cleanCcy = (currency || "Unknown").toUpperCase().trim();
  if (cleanCcy === "USD") {
    return `$${formatted}`;
  }
  return `${cleanCcy} ${formatted}`;
}

/**
 * Generates an institutional-grade PDF Forensic Audit Report for any uploaded transaction dataset.
 * Adheres strictly to GraphFin's original red/black/white visual identity, eliminates text
 * overlap via computed grid layouts, respects dataset currency, wraps pattern names, and
 * separates structural motifs from flagged forensic compliance reviews.
 */
export function generateDatasetPdfReport(
  analysis: AnalysisResult,
  executionEngine?: string,
  download = true,
): jsPDF {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;
  const contentWidth = pageWidth - margin * 2;

  // Authentic GraphFin Color Palette
  const RED_PRIMARY = [180, 74, 80]; // #b44a50
  const RED_DARK = [132, 45, 53];    // #842d35
  const DARK_TEXT = [24, 24, 27];     // #18181b
  const MUTED_TEXT = [95, 95, 102];   // #5f5f66
  const BG_CARD = [250, 250, 252];    // #fafafc
  const BORDER_LIGHT = [225, 225, 230];
  const WHITE = [255, 255, 255];

  const currency = analysis.summary.currency || "Unknown";
  const engine =
    executionEngine ||
    analysis.summary.analysisEngine ||
    "GraphFin Client-Side Graph Topological Heuristics Engine v2.1";

  const totalPages = analysis.summary.evaluation ? 3 : 2;

  const renderHeader = (pageNumber: number) => {
    // Top Accent Strip
    doc.setFillColor(RED_PRIMARY[0], RED_PRIMARY[1], RED_PRIMARY[2]);
    doc.rect(margin, 10, contentWidth, 2.5, "F");

    // Header Meta
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
    doc.text("GRAPHFIN RESEARCH DASHBOARD - FORENSIC AUDIT RECORD", margin, 17);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
    doc.text(`A4 Forensic Audit | Page ${pageNumber} of ${totalPages}`, pageWidth - margin, 17, {
      align: "right",
    });
  };

  const renderFooter = (_pageNumber: number) => {
    const yFoot = pageHeight - 10;
    doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
    doc.setLineWidth(0.2);
    doc.line(margin, yFoot - 3, margin + contentWidth, yFoot - 3);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
    doc.text(
      "GraphFin Anomaly Detection System | Canonical: https://github.com/hariharasuthan1105/GraphFin",
      margin,
      yFoot,
    );

    const auditStatus =
      analysis.backendStatus === "ml_verified"
        ? "Status: Backend ML Verified (Isolation Forest)"
        : "Status: Client-Side Forensic Heuristic Audit";

    doc.text(auditStatus, pageWidth - margin, yFoot, { align: "right" });
  };

  // ==========================================
  // PAGE 1: TITLE, DATASET METADATA & GRAPH TOPOLOGY
  // ==========================================
  renderHeader(1);
  let y = 23;

  // Institutional Title
  doc.setFont("helvetica", "bold");
  doc.setFontSize(13);
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text("Machine Learning Enhanced Graph-Based Anomaly Detection", margin, y);
  y += 5.5;
  doc.text("for Financial Transactions", margin, y);
  y += 5.5;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  const genDate = analysis.summary.processedAt
    ? new Date(analysis.summary.processedAt).toUTCString()
    : new Date().toUTCString();
  doc.text(
    `Dataset Forensic Audit & Topological Analysis Report | Timestamp: ${genDate}`,
    margin,
    y,
  );
  y += 6.5;

  // Metadata Box (Structured 3-Column Grid)
  const metaBoxHeight = 38;
  doc.setFillColor(BG_CARD[0], BG_CARD[1], BG_CARD[2]);
  doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
  doc.setLineWidth(0.3);
  doc.rect(margin, y, contentWidth, metaBoxHeight, "FD");

  // Title of Box
  doc.setFont("helvetica", "bold");
  doc.setFontSize(7.5);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("DATASET AUDIT METADATA & INGESTION SUMMARY", margin + 4, y + 5.5);

  const col1X = margin + 4;
  const col2X = margin + 64;
  const col3X = margin + 124;

  doc.setFontSize(7.5);

  // Column 1: Source & Coverage
  let rowY = y + 11;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Dataset File:", col1X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  const dsName =
    analysis.summary.datasetName.length > 28
      ? analysis.summary.datasetName.slice(0, 26) + "…"
      : analysis.summary.datasetName;
  doc.text(dsName, col1X + 20, rowY);

  rowY += 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("File Size:", col1X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text(`${(analysis.summary.fileSizeBytes / 1024).toFixed(1)} KB`, col1X + 20, rowY);

  rowY += 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Data Coverage:", col1X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  const compStr = `${analysis.summary.dataCompletenessPct ?? 100.0}% (${formatNumber(analysis.summary.totalRowsAccepted ?? analysis.summary.totalTransactions, 0)} accepted)`;
  doc.text(compStr, col1X + 20, rowY);

  rowY += 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Pipeline:", col1X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text(
    analysis.backendStatus === "ml_verified"
      ? "Backend Isolation Forest"
      : "Graph heuristics v2.1",
    col1X + 20,
    rowY,
  );

  // Column 2: Volume & Transactions
  rowY = y + 11;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Transactions:", col2X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text(formatNumber(analysis.summary.totalTransactions, 0), col2X + 24, rowY);

  rowY += 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Monitored Vol:", col2X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text(formatCurrency(analysis.summary.totalVolume, currency, 2), col2X + 24, rowY);

  rowY += 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Mean Tx Amt:", col2X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text(formatCurrency(analysis.summary.meanAmount, currency, 2), col2X + 24, rowY);

  rowY += 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Currency:", col2X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text(
    analysis.summary.isMixedCurrency
      ? "MIXED (See Incompatibility Warning)"
      : `${currency} (Uniform)`,
    col2X + 24,
    rowY,
  );

  // Column 3: Accounts & Findings
  rowY = y + 11;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Unique Accounts:", col3X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text(formatNumber(analysis.summary.uniqueAccounts, 0), col3X + 28, rowY);

  rowY += 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Directed Edges:", col3X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text(formatNumber(analysis.summary.uniqueEdges, 0), col3X + 28, rowY);

  rowY += 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Flagged Review:", col3X, rowY);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text(`${formatNumber(analysis.summary.suspiciousAccountCount, 0)} accounts`, col3X + 28, rowY);

  rowY += 5;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text("Rejected Rows:", col3X, rowY);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text(`${analysis.summary.totalRowsRejected ?? 0} rows`, col3X + 28, rowY);

  doc.text('Source records:', col1X, y + 32);
  doc.text(String(analysis.summary.sourceRecords ?? ((analysis.summary.totalRowsAccepted ?? analysis.summary.totalTransactions) + (analysis.summary.totalRowsRejected ?? 0))), col1X + 24, y + 32);
  y += metaBoxHeight + 6;

  // Currency Incompatibility Warning if mixed
  if (analysis.summary.isMixedCurrency) {
    doc.setFillColor(254, 242, 242);
    doc.setDrawColor(RED_PRIMARY[0], RED_PRIMARY[1], RED_PRIMARY[2]);
    doc.rect(margin, y, contentWidth, 9, "FD");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
    doc.text(
      "WARNING: Dataset contains multiple currencies. Aggregated volume amounts combine disparate currency units without FX normalization.",
      margin + 3,
      y + 5.5,
    );
    y += 12;
  }

  // --- SECTION 1: TOPOLOGICAL & STRUCTURAL GRAPH METRICS ---
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9.5);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("1. TOPOLOGICAL & STRUCTURAL GRAPH METRICS", margin, y);
  y += 4.5;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text(
    "Directed funds-flow graph topology models entity accounts as vertices and transactions as directed weighted arcs.",
    margin,
    y,
  );
  y += 5.5;

  // Topology Table (Clean 4-column key-value grid)
  const topoRows = [
    [
      "Network Density",
      analysis.summary.networkDensity.toFixed(6),
      "Max In-Degree",
      formatNumber(analysis.summary.maxInDegree, 0),
    ],
    [
      "Average Degree",
      analysis.summary.avgDegree.toFixed(2),
      "Max Out-Degree",
      formatNumber(analysis.summary.maxOutDegree, 0),
    ],
    [
      "Source-Only Accounts",
      formatNumber(analysis.summary.sourceOnlyAccounts, 0),
      "Sink-Only Accounts",
      formatNumber(analysis.summary.sinkOnlyAccounts, 0),
    ],
    [
      "Intermediary Accounts",
      formatNumber(analysis.summary.intermediaryAccounts, 0),
      "Median Tx Amount",
      formatCurrency(analysis.summary.medianAmount, currency, 2),
    ],
    [
      "Account Volume Mean",
      formatCurrency(analysis.summary.accountVolumeMean ?? 0, currency, 2),
      "Account Vol Outlier Thresh",
      formatCurrency(analysis.summary.accountVolumeThreshold ?? 0, currency, 2),
    ],
  ];

  const colW = contentWidth / 4;
  const cellHeight = 5.5;

  topoRows.forEach((row) => {
    doc.setFillColor(BG_CARD[0], BG_CARD[1], BG_CARD[2]);
    doc.rect(margin, y, colW, cellHeight, "F");
    doc.rect(margin + colW * 2, y, colW, cellHeight, "F");

    doc.setFont("helvetica", "bold");
    doc.setFontSize(7);
    doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
    doc.text(row[0], margin + 2.5, y + 3.8);
    doc.text(row[2], margin + colW * 2 + 2.5, y + 3.8);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
    doc.text(row[1], margin + colW + 2.5, y + 3.8);
    doc.text(row[3], margin + colW * 3 + 2.5, y + 3.8);

    doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
    doc.setLineWidth(0.2);
    doc.rect(margin, y, contentWidth, cellHeight, "S");
    y += cellHeight;
  });

  y += 7;

  // --- SECTION 2: DETECTED AML TYPOLOGIES & STRUCTURAL MOTIFS ---
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9.5);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("2. AML TYPOLOGY DETECTION & STRUCTURAL MOTIFS", margin, y);
  y += 4.5;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text(
    "Structural motifs are investigative indicators of network geometry, not confirmation of illegal activity.",
    margin,
    y,
  );
  y += 5.5;

  const patterns = [
    {
      name: "Fan-Out (Smurfing / Dispersal Hub)",
      count: analysis.summary.patternsDetected.fanOutCount,
      desc: "Account with out-degree > 2.5 sigma from network out-degree distribution and out/in degree ratio >= 2.5.",
    },
    {
      name: "Fan-In (Mule Aggregation Hub)",
      count: analysis.summary.patternsDetected.fanInCount,
      desc: "Account with in-degree > 2.5 sigma from network in-degree distribution and in/out degree ratio >= 2.5.",
    },
    {
      name: "Noteworthy Cycles & Reciprocal Loops",
      count: analysis.summary.patternsDetected.cycleCount,
      desc: "Multi-hop directed routing loops (len >= 3) or repeated reciprocal flow exceeding 5 round-trips.",
    },
    {
      name: "Account-Level Volume Outliers",
      count: analysis.summary.patternsDetected.volumeOutlierCount,
      desc: "Accounts whose total volume exceeds 2.5 sigma from the account-level volume distribution.",
    },
  ];

  patterns.forEach((p) => {
    doc.setFillColor(BG_CARD[0], BG_CARD[1], BG_CARD[2]);
    doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
    doc.setLineWidth(0.2);
    doc.rect(margin, y, contentWidth, 9.5, "FD");

    // Red badge for count
    doc.setFillColor(RED_PRIMARY[0], RED_PRIMARY[1], RED_PRIMARY[2]);
    doc.rect(margin + 2, y + 2, 14, 5.5, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.setTextColor(WHITE[0], WHITE[1], WHITE[2]);
    doc.text(String(p.count), margin + 9, y + 5.8, { align: "center" });

    // Pattern Name & Description
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
    doc.text(p.name, margin + 20, y + 4.2);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(6.8);
    doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
    doc.text(p.desc, margin + 20, y + 7.8);

    y += 11;
  });

  renderFooter(1);

  // ==========================================
  // PAGE 2: SUSPICIOUS ACCOUNT RANKINGS
  // ==========================================
  doc.addPage();
  renderHeader(2);
  y = 23;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(9.5);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("3. ACCOUNT ANOMALY RANKING (NOT ALL ACCOUNTS ARE FLAGGED)", margin, y);
  y += 4.5;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text(
    "Accounts ranked by composite anomaly score derived from account volume extremity, degree divergence, and topological motifs.",
    margin,
    y,
  );
  y += 5.5;

  // Table Layout (8 Columns with generous widths)
  // Total width: 182mm
  // Rank(10), ID(28), Score(16), In/Out(16), Sent(28), Recv(28), Net(22), Typologies(34)
  const colWidths = [10, 28, 16, 16, 28, 28, 22, 34];
  const tableHeaders = [
    "Rank",
    "Account ID",
    "Score",
    "In / Out",
    `Total Sent (${currency})`,
    `Total Recv (${currency})`,
    `Net Flow (${currency})`,
    "Observed Motifs",
  ];

  doc.setFillColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.rect(margin, y, contentWidth, 6, "F");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(6.8);
  doc.setTextColor(WHITE[0], WHITE[1], WHITE[2]);

  let curX = margin;
  tableHeaders.forEach((h, i) => {
    doc.text(h, curX + 2, y + 4.2);
    curX += colWidths[i];
  });
  y += 6;

  // Top accounts list
  const rankedAccounts = (analysis.topAnomalies.length > 0 ? analysis.topAnomalies : analysis.accounts).slice(0, 15);

  rankedAccounts.forEach((acc, idx) => {
    const isEven = idx % 2 === 0;
    doc.setFillColor(isEven ? 255 : 248, isEven ? 255 : 249, isEven ? 255 : 250);
    doc.rect(margin, y, contentWidth, 6.8, "F");
    doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
    doc.setLineWidth(0.15);
    doc.line(margin, y + 6.8, margin + contentWidth, y + 6.8);

    curX = margin;

    // Rank
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7);
    doc.setTextColor(acc.anomalyScore >= 0.7 ? RED_PRIMARY[0] : DARK_TEXT[0], acc.anomalyScore >= 0.7 ? RED_PRIMARY[1] : DARK_TEXT[1], acc.anomalyScore >= 0.7 ? RED_PRIMARY[2] : DARK_TEXT[2]);
    doc.text(`#${idx + 1}`, curX + 2, y + 4.6);
    curX += colWidths[0];

    // Account ID
    doc.setFont("helvetica", "normal");
    doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
    const cleanId = acc.id.length > 15 ? acc.id.slice(0, 13) + "…" : acc.id;
    doc.text(cleanId, curX + 2, y + 4.6);
    curX += colWidths[1];

    // Score
    doc.setFont("helvetica", "bold");
    doc.setTextColor(acc.anomalyScore >= 0.7 ? RED_DARK[0] : DARK_TEXT[0], acc.anomalyScore >= 0.7 ? RED_DARK[1] : DARK_TEXT[1], acc.anomalyScore >= 0.7 ? RED_DARK[2] : DARK_TEXT[2]);
    doc.text(acc.anomalyScore.toFixed(4), curX + 2, y + 4.6);
    curX += colWidths[2];

    // In / Out Degree
    doc.setFont("helvetica", "normal");
    doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
    doc.text(`${acc.inDegree} / ${acc.outDegree}`, curX + 2, y + 4.6);
    curX += colWidths[3];

    // Total Sent
    doc.text(formatNumber(acc.totalSent, 0), curX + 2, y + 4.6);
    curX += colWidths[4];

    // Total Received
    doc.text(formatNumber(acc.totalReceived, 0), curX + 2, y + 4.6);
    curX += colWidths[5];

    // Net Flow
    const netSign = acc.netFlow > 0 ? "+" : "";
    doc.text(`${netSign}${formatNumber(acc.netFlow, 0)}`, curX + 2, y + 4.6);
    curX += colWidths[6];

    // Flagged Typologies (Clean readable abbreviations and 2-line wrapping)
    doc.setFont("helvetica", "bold");
    doc.setFontSize(6.2);
    doc.setTextColor(
      acc.patterns.length > 0 ? RED_DARK[0] : MUTED_TEXT[0],
      acc.patterns.length > 0 ? RED_DARK[1] : MUTED_TEXT[1],
      acc.patterns.length > 0 ? RED_DARK[2] : MUTED_TEXT[2],
    );
    const PATTERN_LABELS: Record<string, string> = {
      VOLUME_OUTLIER: "Vol Outlier",
      FAN_OUT: "Fan-Out",
      FAN_IN: "Fan-In",
      CYCLE: "Cycle Loop",
      FLOW_IMBALANCE: "Flow Imbal",
    };
    const patsStr =
      acc.patterns.length > 0
        ? acc.patterns.map((p) => PATTERN_LABELS[p] || p).join(", ")
        : "Normal";
    const wrappedPats = doc.splitTextToSize(patsStr, colWidths[7] - 3);
    if (wrappedPats.length > 1) {
      doc.text(wrappedPats[0], curX + 2, y + 3.2);
      doc.text(wrappedPats[1], curX + 2, y + 5.8);
    } else {
      doc.text(wrappedPats[0] || "", curX + 2, y + 4.6);
    }

    y += 6.8;
  });

  y += 8;

  // --- SECTION 4: BACKEND ML ISOLATION FOREST RESULTS (If executed) ---
  if (analysis.backendStatus === "ml_verified" && analysis.backendModel) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9.5);
    doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
    doc.text("4. BACKEND ISOLATION FOREST VERIFICATION", margin, y);
    y += 4.5;

    doc.setFillColor(BG_CARD[0], BG_CARD[1], BG_CARD[2]);
    doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
    doc.rect(margin, y, contentWidth, 14, "FD");

    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
    doc.text(`Model: ${analysis.backendModel}`, margin + 4, y + 5);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
    doc.text(
      `Dataset ID: ${analysis.backendDatasetId || "in-memory-session"} | Pipeline: Verified Server-Side Execution on Render`,
      margin + 4,
      y + 9.5,
    );
    y += 18;
  }

  // --- SECTION 5: GROUND-TRUTH BENCHMARK EVALUATION (If labels present) ---
  if (analysis.summary.evaluation) {
    const evalData = analysis.summary.evaluation;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9.5);
    doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
    doc.text("5. SYNTHETIC GROUND-TRUTH BENCHMARK EVALUATION", margin, y);
    y += 4.5;

    const wrappedRule = doc.splitTextToSize(
      evalData.aggregationRule ||
        "Account associated with synthetic anomaly if it participated in >= 1 labeled transaction.",
      contentWidth - 8,
    );
    const wrappedDisc = doc.splitTextToSize(
      evalData.disclaimer ||
        "Synthetic test-label convention for algorithmic benchmarking only; does not confirm illegal fraud.",
      contentWidth - 8,
    );
    const totalBoxHeight = 28 + wrappedRule.length * 3.5 + wrappedDisc.length * 3.5;

    doc.setFillColor(BG_CARD[0], BG_CARD[1], BG_CARD[2]);
    doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
    doc.rect(margin, y, contentWidth, totalBoxHeight, "FD");

    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.2);
    doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
    doc.text("BENCHMARK METRICS (ACCOUNT LEVEL)", margin + 4, y + 5.2);

    // Metric Badges Grid
    const mColW = (contentWidth - 8) / 4;
    const badgeY = y + 8;

    const metrics = [
      { label: "Precision", val: `${(evalData.precision * 100).toFixed(1)}%`, sub: `TP: ${evalData.truePositives} / Flagged: ${evalData.truePositives + evalData.falsePositives}` },
      { label: "Recall (Hubs)", val: `${(evalData.recall * 100).toFixed(1)}%`, sub: `Positives: ${evalData.positives}` },
      { label: "F1 Score", val: evalData.f1Score.toFixed(4), sub: "Harmonic Mean" },
      { label: "PR-AUC (AP)", val: evalData.prAuc ? evalData.prAuc.toFixed(4) : "N/A", sub: "Average Precision" },
    ];

    metrics.forEach((m, idx) => {
      const bX = margin + 4 + idx * mColW;
      doc.setFillColor(WHITE[0], WHITE[1], WHITE[2]);
      doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
      doc.rect(bX, badgeY, mColW - 3, 14, "FD");

      doc.setFont("helvetica", "bold");
      doc.setFontSize(6.8);
      doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
      doc.text(m.label, bX + 2, badgeY + 4);

      doc.setFont("helvetica", "bold");
      doc.setFontSize(10);
      doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
      doc.text(m.val, bX + 2, badgeY + 9.5);

      doc.setFont("helvetica", "normal");
      doc.setFontSize(6);
      doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
      doc.text(m.sub, bX + 2, badgeY + 12.8);
    });

    // Aggregation Rule & Disclaimer
    let textY = y + 26;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(6.8);
    doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
    doc.text("Evaluation Label Aggregation Rule:", margin + 4, textY);
    textY += 3.8;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(6.5);
    doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
    doc.text(wrappedRule, margin + 4, textY);
    textY += wrappedRule.length * 3.5 + 1.5;

    doc.text(wrappedDisc, margin + 4, textY);

    y += totalBoxHeight + 6;
  }

  renderFooter(2);

  // ==========================================
  // PAGE 3: METHODOLOGY, THRESHOLDS & DISCLOSURES
  // ==========================================
  if (totalPages >= 3) {
    doc.addPage();
    renderHeader(3);
    y = 23;
  }

  // Section 6: Methodology & Threshold Definitions
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9.5);
  doc.setTextColor(RED_DARK[0], RED_DARK[1], RED_DARK[2]);
  doc.text("6. METHODOLOGY, VERSIONED THRESHOLDS & EVIDENCE PROVENANCE", margin, y);
  y += 4.5;

  doc.setFillColor(BG_CARD[0], BG_CARD[1], BG_CARD[2]);
  doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
  doc.rect(margin, y, contentWidth, 54, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(7.5);
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text("Analytical Framework & Scoring Semantics:", margin + 4, y + 5);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(6.8);
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text(
    "GraphFin computes continuous anomaly scores as a weighted combination of 4 defensible indicators:",
    margin + 4,
    y + 9,
  );
  doc.text(
    "- Volume Extremity (30%): Standardized Z-score of account-level total volume against account volume distribution.",
    margin + 6,
    y + 13,
  );
  doc.text(
    "- Degree Divergence (25%): Normalized Z-score of entity transaction degree against observed network degree distribution.",
    margin + 6,
    y + 17,
  );
  doc.text(
    "- Net Flow Asymmetry (20%): Volume-moderated absolute difference between total funds received and funds sent.",
    margin + 6,
    y + 21,
  );
  doc.text(
    "- Topological Motifs (25%): Compounding presence of verified Fan-Out hubs, Fan-In collection sinks, and circular loops.",
    margin + 6,
    y + 25,
  );

  doc.setFont("helvetica", "bold");
  doc.setFontSize(7.5);
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text("Configured & Versioned Thresholds:", margin + 4, y + 32);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(6.8);
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  const thresh = analysis.summary.thresholdConfig || {
    volumeZThreshold: 2.5,
    degreeZThreshold: 2.5,
    fanOutRatio: 2.5,
    fanInRatio: 2.5,
    suspiciousScoreThreshold: 0.60,
    version: "GraphFin-Analytical-v2.1",
  };
  doc.text(
    `Algorithm Version: ${thresh.version} | Volume Threshold: Z >= ${thresh.volumeZThreshold} SD | Degree Threshold: Z >= ${thresh.degreeZThreshold} SD`,
    margin + 4,
    y + 36,
  );
  doc.text(
    `Fan-Out Dispersal Ratio: >= ${thresh.fanOutRatio}x | Fan-In Aggregation Ratio: >= ${thresh.fanInRatio}x | Flagged Review Threshold: Score >= ${thresh.suspiciousScoreThreshold}`,
    margin + 4,
    y + 40,
  );
  doc.text(
    "Distinctions: Motifs indicate structural geometry; high scores indicate statistical extremity; flagged indicates compliance review priority.",
    margin + 4,
    y + 44,
  );
  doc.text(
    `Engine Executed: ${engine}`,
    margin + 4,
    y + 49,
  );

  y += 60;

  // Legal & Regulatory Compliance Disclaimer
  doc.setFillColor(BG_CARD[0], BG_CARD[1], BG_CARD[2]);
  doc.setDrawColor(BORDER_LIGHT[0], BORDER_LIGHT[1], BORDER_LIGHT[2]);
  doc.rect(margin, y, contentWidth, 34, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(7.5);
  doc.setTextColor(DARK_TEXT[0], DARK_TEXT[1], DARK_TEXT[2]);
  doc.text("Legal & Regulatory Audit Disclosures:", margin + 4, y + 5);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(6.6);
  doc.setTextColor(MUTED_TEXT[0], MUTED_TEXT[1], MUTED_TEXT[2]);
  doc.text(
    "Anomaly scores generated by this system represent structural and mathematical divergence from observed transaction network",
    margin + 4,
    y + 9,
  );
  doc.text(
    "distributions. Flagged accounts warrant compliance inquiry under applicable AML/CFT risk-based frameworks; they do not constitute",
    margin + 4,
    y + 13,
  );
  doc.text(
    "autonomous evidence of illegal activity, fraud, or guilt without independent factual corroboration.",
    margin + 4,
    y + 17,
  );
  doc.text(
    "Privacy Assurance: This audit report was compiled using ephemeral client-side memory. No visitor transaction data is permanently",
    margin + 4,
    y + 22,
  );
  doc.text(
    "persisted or transferred to external servers without explicit user authorization.",
    margin + 4,
    y + 26,
  );

  if (totalPages >= 3) {
    renderFooter(3);
  }

  // Trigger download if running in browser
  if (download && typeof window !== "undefined") {
    const filename = `GraphFin_Audit_Report_${analysis.summary.datasetName.replace(/[^a-zA-Z0-9_-]/g, "_")}.pdf`;
    doc.save(filename);
  }

  return doc;
}
