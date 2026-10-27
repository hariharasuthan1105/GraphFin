import React, { createContext, useContext, useEffect, useState } from "react";
import type { AnalysisResult } from "./datasetAnalysis/types";
import { SAMPLE_CSV_DATA } from "./datasetAnalysis/sampleData";
import { parseDelimitedText } from "./datasetAnalysis/parser";
import { analyzeTransactionGraph } from "./datasetAnalysis/engine";

export type AppMode = "research" | "interactive";
export type GraphViewMode = "uploaded" | "simulated" | "research";
export type SimulatedPresetKey =
  | "mule-ring"
  | "ponzi-cycle"
  | "smurfing-fanout"
  | "fanin-aggregation";

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
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [appMode, setAppMode] = useState<AppMode>("interactive");
  const [activeSession, setActiveSession] = useState<AnalysisResult | null>(null);
  const [graphMode, setGraphMode] = useState<GraphViewMode>("simulated");
  const [simulatedPreset, setSimulatedPreset] =
    useState<SimulatedPresetKey>("mule-ring");

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
      setActiveSession(result);
      setAppMode("interactive");
      setGraphMode("uploaded");
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
