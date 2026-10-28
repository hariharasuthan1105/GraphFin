import { createContext, useContext } from "react";
import type { AnalysisResult, BackendMLStatus } from "./datasetAnalysis/types";
export type AppMode = "research" | "interactive";
export type GraphViewMode = "uploaded" | "simulated" | "research";
export type SimulatedPresetKey =
  | "mule-ring"
  | "ponzi-cycle"
  | "smurfing-fanout"
  | "fanin-aggregation";

export type BackendSyncStatus = BackendMLStatus;

export interface SessionContextType {
  selectedGraphAccount: string | null;
  setSelectedGraphAccount: (id: string | null) => void;
  saveAnalysisLocally: () => Promise<void>;
  clearSavedSession: () => Promise<void>;
  storageMessage: string;
  storageBusy: boolean;
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

export const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
}
