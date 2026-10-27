import React, { createContext, useContext, useEffect, useState } from "react";
import type { AnalysisResult, AccountNode, BackendMLStatus } from "./datasetAnalysis/types";
import { SAMPLE_CSV_DATA } from "./datasetAnalysis/sampleData";
import { parseDelimitedText } from "./datasetAnalysis/parser";
import { analyzeTransactionGraph } from "./datasetAnalysis/engine";
import {
  checkBackendHealth,
  uploadTransactionsCsv,
  trainIsolationForest,
  fetchUserAnomalies,
} from "./client";

export type AppMode = "research" | "interactive";
export type GraphViewMode = "uploaded" | "simulated" | "research";
export type SimulatedPresetKey =
  | "mule-ring"
  | "ponzi-cycle"
  | "smurfing-fanout"
  | "fanin-aggregation";

export type BackendSyncStatus = BackendMLStatus;

interface SessionContextType {
  appMode: AppMode;
  setAppMode: (mode: AppMode) => void;
  activeSession: AnalysisResult | null;
  setActiveSession: (session: AnalysisResult | null) => void;
  graphMode: GraphViewMode;
  setGraphMode: (mode: GraphViewMode) => void;
  simulatedPreset: SimulatedPresetKey;
  setSimulatedPreset: (preset: SimulatedPresetKey) => void;
  loadBenchmarkSample: () => void;
  clearSession: () => void;
  backendStatus: BackendSyncStatus;
  backendDatasetId: string | null;
  backendModel: string;
  backendMessage: string;
  isBackendOnline: boolean;
  syncSessionToBackend: (
    session: AnalysisResult,
    rawCsv?: string,
    userConsent?: boolean,
  ) => Promise<boolean>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [appMode, setAppMode] = useState<AppMode>("interactive");
  const [activeSession, setActiveSession] = useState<AnalysisResult | null>(null);
  const [graphMode, setGraphMode] = useState<GraphViewMode>("simulated");
  const [simulatedPreset, setSimulatedPreset] =
    useState<SimulatedPresetKey>("mule-ring");

  const [backendStatus, setBackendStatus] = useState<BackendSyncStatus>("idle");
  const [backendDatasetId, setBackendDatasetId] = useState<string | null>(null);
  const [backendModel, setBackendModel] = useState<string>("Client-Side Graph Heuristics v2.1");
  const [backendMessage, setBackendMessage] = useState<string>("Client-side heuristic analysis completed.");
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(false);

  // Probe backend health on mount (non-intrusive health ping)
  useEffect(() => {
    let mounted = true;
    checkBackendHealth().then((res) => {
      if (mounted) {
        setIsBackendOnline(res.online);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  // Securely trigger backend ML pipeline with EXPLICIT user consent and bounds enforcement
  const syncSessionToBackend = async (
    session: AnalysisResult,
    rawCsv?: string,
    userConsent = false,
  ): Promise<boolean> => {
    // 1. Enforce Privacy Requirement: explicit consent is mandatory
    if (!userConsent) {
      console.warn("Backend ML sync blocked: Explicit user consent is required before transmitting financial data.");
      return false;
    }

    // 2. Enforce Resource and Safety Limits for Render Free Tier (512MB RAM budget)
    const MAX_SAFE_TRANSACTIONS = 15000;
    const MAX_SAFE_FILE_BYTES = 10 * 1024 * 1024; // 10 MB

    if (session.summary.totalTransactions > MAX_SAFE_TRANSACTIONS) {
      setBackendStatus("ml_unavailable");
      setBackendMessage(
        `Backend ML unavailable: Dataset exceeds 15,000 transaction limit for public Render Free tier (${session.summary.totalTransactions.toLocaleString()} rows). Local heuristics remain active.`
      );
      return false;
    }

    if (session.summary.fileSizeBytes > MAX_SAFE_FILE_BYTES) {
      setBackendStatus("ml_unavailable");
      setBackendMessage(
        `Backend ML unavailable: Dataset exceeds 10 MB safety limit for public Render tier. Local heuristics remain active.`
      );
      return false;
    }

    try {
      setBackendStatus("ml_pending");
      setBackendMessage("Backend ML pending: Transmitting dataset and fitting Isolation Forest (100 Trees, 19 Features)...");

      // Build canonical CSV content if raw text is not already available
      let csvData = rawCsv;
      if (!csvData) {
        const rows = session.edges.map((e, idx) =>
          `TX_${String(idx + 1).padStart(5, "0")},${e.source},${e.target},${e.amount},2026-10-27T10:00:00Z`
        );
        csvData = "transaction_id,sender_id,receiver_id,amount,timestamp\n" + rows.join("\n");
      }

      // Step A: Upload to backend
      const uploadRes = await uploadTransactionsCsv(
        csvData,
        session.summary.datasetName,
        session.summary.currency || "USD"
      );
      const dsId = uploadRes.dataset_id;
      setBackendDatasetId(dsId);

      // Step B: Train Isolation Forest model (100 trees, 0.05 contamination, 19 canonical features)
      setBackendMessage("Backend ML pending: Fitting Isolation Forest anomaly model on backend...");
      await trainIsolationForest(dsId, "isolation_forest");

      // Step C: Fetch computed per-user anomaly scores
      setBackendMessage("Backend ML pending: Retrieving multidimensional anomaly scores...");
      const userRes = await fetchUserAnomalies(dsId, "isolation_forest", 1000);

      if (userRes && Array.isArray(userRes.users) && userRes.users.length > 0) {
        const userMap = new Map<string, any>();
        userRes.users.forEach((u: any) => {
          if (u.user_id) {
            userMap.set(u.user_id, u);
          }
        });

        // Associate Isolation Forest output with each account node
        // Semantics: preserve deterministic heuristic score as heuristicScore / anomalyScore,
        // and attach verified ML continuous score, risk score, and status.
        const updatedAccounts: AccountNode[] = session.accounts.map((acc) => {
          const mlData = userMap.get(acc.id);
          if (mlData) {
            const rawScore = typeof mlData.raw_score === "number" ? mlData.raw_score : 0;
            const riskScore = typeof mlData.risk_score === "number" ? mlData.risk_score : 0;
            const mlStatus = mlData.status || (mlData.prediction === -1 ? "anomaly" : "normal");
            // Normalize decision score to [0, 1] range: lower raw_score means more anomalous
            const normMlScore = Number(Math.max(0, Math.min(1, (0.5 - rawScore))).toFixed(4));

            return {
              ...acc,
              heuristicScore: acc.anomalyScore,
              mlScore: normMlScore,
              mlRiskScore: riskScore,
              mlStatus: mlStatus,
            };
          }
          return acc;
        });

        const updatedSession: AnalysisResult = {
          ...session,
          accounts: updatedAccounts,
          backendDatasetId: dsId,
          backendStatus: "ml_verified",
          backendModel: "Isolation Forest (100 Trees, 19 Features)",
        };

        setActiveSession(updatedSession);
        setBackendStatus("ml_verified");
        setBackendModel("Isolation Forest (100 Trees, 19 Features)");
        setBackendMessage("Backend ML completed and verified: Isolation Forest active");
        return true;
      }

      setBackendStatus("ml_failed");
      setBackendMessage("Backend ML failed: Response did not return valid user anomaly records.");
      return false;
    } catch (err: any) {
      console.warn("Backend ML execution failed; preserving client heuristics:", err);
      const isRestricted = err?.message?.includes("405") || err?.message?.includes("GATEWAY_READ_ONLY");
      const isTimeout = err?.name === "AbortError" || err?.message?.includes("timeout");

      const failStatus: BackendMLStatus = isRestricted || isTimeout ? "ml_unavailable" : "ml_failed";
      setBackendStatus(failStatus);
      setBackendMessage(
        isRestricted
          ? "Backend ML unavailable: Remote gateway is configured for read-only safety. Client heuristics active."
          : isTimeout
          ? "Backend ML unavailable: Remote server timed out or spinning up. Client heuristics active."
          : `Backend ML failed: ${err?.message || "Execution error"}. Client heuristics active.`
      );
      return false;
    }
  };

  // Load benchmark sample immediately or on demand (CLIENT-SIDE ONLY, NO AUTO-TRANSMISSION)
  const loadBenchmarkSample = () => {
    try {
      const parsed = parseDelimitedText(SAMPLE_CSV_DATA);
      const records = parsed.rows.map((r, idx) => ({
        transaction_id: `TX_SAMPLE_${String(idx + 1).padStart(4, "0")}`,
        source: r[3] || `SRC_${idx}`,
        destination: r[4] || `DST_${idx}`,
        amount: parseFloat(r[2]) || 100,
        type: r[1] || "TRANSFER",
        label: r[5] === "1" ? 1 : 0,
      }));
      const result = analyzeTransactionGraph(
        records,
        "synthetic_financial_benchmark.csv",
        SAMPLE_CSV_DATA.length,
      );
      result.summary.rawCsvContent = SAMPLE_CSV_DATA;
      result.backendStatus = "client_completed";
      result.backendModel = "Client-Side Graph Heuristics v2.1";
      setActiveSession(result);
      setAppMode("interactive");
      setGraphMode("uploaded");
      setBackendStatus("client_completed");
      setBackendModel("Client-Side Graph Heuristics v2.1");
      setBackendMessage("Client-side heuristic analysis completed.");
    } catch (err) {
      console.error("Failed to load benchmark sample", err);
    }
  };

  // Pre-load benchmark sample on mount so app feels immediately rich and interactive
  useEffect(() => {
    if (!activeSession) {
      loadBenchmarkSample();
    }
  }, []);

  const clearSession = () => {
    setActiveSession(null);
    setGraphMode("simulated");
    setBackendDatasetId(null);
    setBackendStatus("idle");
    setBackendModel("Client-Side Graph Heuristics v2.1");
    setBackendMessage("Client-side heuristic analysis completed.");
  };

  return (
    <SessionContext.Provider
      value={{
        appMode,
        setAppMode,
        activeSession,
        setActiveSession,
        graphMode,
        setGraphMode,
        simulatedPreset,
        setSimulatedPreset,
        loadBenchmarkSample,
        clearSession,
        backendStatus,
        backendDatasetId,
        backendModel,
        backendMessage,
        isBackendOnline,
        syncSessionToBackend,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
}
