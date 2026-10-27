import React, { createContext, useContext, useEffect, useState } from "react";
import type { AnalysisResult, AccountNode } from "./datasetAnalysis/types";
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

export type BackendSyncStatus = "idle" | "syncing" | "synced" | "offline";

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
  syncSessionToBackend: (session: AnalysisResult, rawCsv?: string) => Promise<void>;
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
  const [backendModel, setBackendModel] = useState<string>("Client-Side Graph Heuristics");
  const [backendMessage, setBackendMessage] = useState<string>("Checking backend API...");
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(false);

  // Probe backend health on mount
  useEffect(() => {
    let mounted = true;
    checkBackendHealth().then((res) => {
      if (mounted) {
        setIsBackendOnline(res.online);
        setBackendMessage(res.message);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  // Sync session to backend ML pipeline
  const syncSessionToBackend = async (session: AnalysisResult, rawCsv?: string) => {
    try {
      setBackendStatus("syncing");
      setBackendMessage("Syncing dataset with backend ML pipeline...");

      // Prepare canonical CSV content
      let csvData = rawCsv;
      if (!csvData) {
        // Build canonical CSV from account / edge relationships
        const rows = session.edges.map((e, idx) =>
          `TX_${String(idx + 1).padStart(5, "0")},${e.source},${e.target},${e.amount},2026-10-27T10:00:00Z`
        );
        csvData = "transaction_id,sender_id,receiver_id,amount,timestamp\n" + rows.join("\n");
      }

      // 1. Upload to backend
      const uploadRes = await uploadTransactionsCsv(csvData, session.summary.datasetName);
      const dsId = uploadRes.dataset_id;
      setBackendDatasetId(dsId);

      // 2. Train Isolation Forest model
      setBackendMessage("Training Isolation Forest anomaly model on backend...");
      await trainIsolationForest(dsId, "isolation_forest");

      // 3. Fetch computed per-user anomaly scores
      setBackendMessage("Retrieving multidimensional anomaly scores...");
      const userRes = await fetchUserAnomalies(dsId, "isolation_forest", 500);

      if (userRes && Array.isArray(userRes.users) && userRes.users.length > 0) {
        const scoreMap = new Map<string, number>();
        userRes.users.forEach((u: any) => {
          if (u.user_id && typeof u.continuous_anomaly_score === "number") {
            // Map isolation forest score (ranges ~-0.5 to 0.5) to normalized 0.0 - 1.0 range
            const normScore = Math.max(0, Math.min(1, (u.continuous_anomaly_score + 0.5)));
            scoreMap.set(u.user_id, normScore);
          }
        });

        // Merge scores into accounts
        const updatedAccounts: AccountNode[] = session.accounts.map((acc) => {
          const mlScore = scoreMap.get(acc.id);
          if (mlScore !== undefined) {
            // Blend ML isolation depth with graph structural anomaly score
            const blended = Number(((acc.anomalyScore * 0.4) + (mlScore * 0.6)).toFixed(4));
            return {
              ...acc,
              anomalyScore: blended,
            };
          }
          return acc;
        });

        updatedAccounts.sort((a, b) => b.anomalyScore - a.anomalyScore);
        const topAnomalies = updatedAccounts.filter((a) => a.anomalyScore >= 0.6);

        const updatedSession: AnalysisResult = {
          ...session,
          accounts: updatedAccounts,
          topAnomalies: topAnomalies.length > 0 ? topAnomalies : updatedAccounts.slice(0, 5),
          backendDatasetId: dsId,
          backendStatus: "synced",
          backendModel: "Isolation Forest (100 Trees, 19 Features)",
        };

        setActiveSession(updatedSession);
        setBackendStatus("synced");
        setBackendModel("Isolation Forest (100 Trees, 19 Features)");
        setBackendMessage("Synced & Trained: Isolation Forest active");
        return;
      }

      setBackendStatus("synced");
      setBackendModel("Graph Engine (NetworkX)");
      setBackendMessage("Synced: Dataset active on backend");
    } catch (err: any) {
      console.warn("Backend sync failed; client heuristics remain active:", err);
      setBackendStatus("offline");
      setBackendMessage(
        err?.message?.includes("AbortError")
          ? "Backend waking up (client heuristics active)"
          : "Local heuristics active (backend offline)"
      );
    }
  };

  // Load benchmark sample immediately or on demand
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
      setActiveSession(result);
      setAppMode("interactive");
      setGraphMode("uploaded");

      // Auto-sync sample to backend in background
      syncSessionToBackend(result, SAMPLE_CSV_DATA).catch(() => {});
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
    setBackendModel("Client-Side Graph Heuristics");
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
