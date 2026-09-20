import React, { createContext, useContext, useState, useEffect } from "react";
import { NetworkEdge, UserAnomalyResult } from "../types/api";
import { api } from "../api/client";
import { parseTransactionCsv } from "../utils/csvParser";
import { SAMPLE_TRANSACTIONS_CSV } from "../utils/sampleData";

export type NavItem =
  | "overview"
  | "datasets"
  | "graph"
  | "features"
  | "anomalies"
  | "labels_splits"
  | "evaluation"
  | "tax";

export type ResearchTier = "medium_real" | "large_real";

// Locked dataset IDs from final_e0_e4_comparison.json — do not change
export const RESEARCH_TIER_IDS: Record<ResearchTier, string> = {
  medium_real: "ddbaab44-78b6-41be-a8fb-e83dfec66358", // 5,000 accounts
  large_real: "03fb9ab0-4f42-4404-9d76-723fd4d8753e",  // 49,992 accounts
};

export const RESEARCH_TIER_LABELS: Record<ResearchTier, string> = {
  medium_real: "Research — 5,000 accounts (IBM AML HI-Small subsample)",
  large_real: "Research — 49,992 accounts (IBM AML HI-Small subsample)",
};

export const isOfficialResearchDataset = (id: string): boolean => {
  return id === RESEARCH_TIER_IDS.medium_real || id === RESEARCH_TIER_IDS.large_real;
};

export interface DatasetHistoryItem {
  id: string;
  name: string;
  timestamp: string;
  transactions?: number;
  users?: number;
}

interface AppContextType {
  datasetId: string;
  setDatasetId: (id: string) => void;
  experimentLabel: string;
  setExperimentLabel: (label: string) => void;
  splitLabel: string | null;
  setSplitLabel: (label: string | null) => void;
  activeNav: NavItem;
  setActiveNav: (nav: NavItem) => void;
  datasetHistory: DatasetHistoryItem[];
  addDatasetToHistory: (item: DatasetHistoryItem) => void;
  cachedEdges: NetworkEdge[];
  setCachedEdges: (edges: NetworkEdge[]) => void;
  selectedNodeId: string | null;
  setSelectedNodeId: (id: string | null) => void;
  anomalyResults: Record<string, UserAnomalyResult>;
  setAnomalyResults: (results: Record<string, UserAnomalyResult>) => void;
  isBackendConnected: boolean | null;
  backendError: string | null;
  checkBackendHealth: () => Promise<boolean>;
  // Research mode
  researchTier: ResearchTier;
  setResearchTier: (tier: ResearchTier) => void;
  isOfficialResearch: boolean;
  // Active dataset currency (ISO 4217). Auto-fetched on datasetId change.
  datasetCurrency: string;
  setDatasetCurrency: (code: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const LOCAL_STORAGE_DATASET_KEY = "graphfin_dataset_id";
const LOCAL_STORAGE_HISTORY_KEY = "graphfin_dataset_history";
const LOCAL_STORAGE_EXP_KEY = "graphfin_experiment_label";
const LOCAL_STORAGE_SPLIT_KEY = "graphfin_split_label";
const LOCAL_STORAGE_TIER_KEY = "graphfin_research_tier";

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Research tier — persisted. Default: large_real (50K)
  const [researchTier, setResearchTierState] = useState<ResearchTier>(() => {
    const stored = localStorage.getItem(LOCAL_STORAGE_TIER_KEY);
    return (stored === "medium_real" || stored === "large_real") ? stored : "large_real";
  });

  // datasetId: on first load or refresh, default to stored dataset or active research tier ID
  const [datasetId, setDatasetIdState] = useState<string>(() => {
    const storedTier = localStorage.getItem(LOCAL_STORAGE_TIER_KEY) as ResearchTier | null;
    const activeTier = (storedTier === "medium_real" || storedTier === "large_real") ? storedTier : "large_real";
    const stored = localStorage.getItem(LOCAL_STORAGE_DATASET_KEY);
    if (stored) {
      return stored;
    }
    return RESEARCH_TIER_IDS[activeTier];
  });

  const [experimentLabel, setExperimentLabelState] = useState<string>(() => {
    return localStorage.getItem(LOCAL_STORAGE_EXP_KEY) || "default";
  });

  const [splitLabel, setSplitLabelState] = useState<string | null>(() => {
    return localStorage.getItem(LOCAL_STORAGE_SPLIT_KEY) || null;
  });

  const [activeNav, setActiveNav] = useState<NavItem>("overview");

  const [datasetHistory, setDatasetHistory] = useState<DatasetHistoryItem[]>(() => {
    try {
      const stored = localStorage.getItem(LOCAL_STORAGE_HISTORY_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [cachedEdges, setCachedEdges] = useState<NetworkEdge[]>(() => {
    // Pre-parse bundled sample edges as default fallback
    const { edges } = parseTransactionCsv(SAMPLE_TRANSACTIONS_CSV);
    return edges;
  });

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [anomalyResults, setAnomalyResults] = useState<Record<string, UserAnomalyResult>>({});
  const [isBackendConnected, setIsBackendConnected] = useState<boolean | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  // Active dataset currency — auto-updated whenever datasetId changes
  const [datasetCurrency, setDatasetCurrency] = useState<string>("USD");

  // Persist initial large_real datasetId if nothing was stored
  useEffect(() => {
    if (!localStorage.getItem(LOCAL_STORAGE_DATASET_KEY)) {
      localStorage.setItem(LOCAL_STORAGE_DATASET_KEY, RESEARCH_TIER_IDS.large_real);
    }
  }, []);

  // Auto-fetch currency whenever datasetId changes.
  // Research tier datasets (IBM AML) are USD.
  useEffect(() => {
    if (!datasetId) {
      setDatasetCurrency("USD");
      return;
    }
    api
      .getTransactionSummary(datasetId)
      .then((summary) => {
        setDatasetCurrency((summary as any).currency ?? "USD");
      })
      .catch(() => {
        setDatasetCurrency("USD");
      });
  }, [datasetId]);

  const setDatasetId = (id: string) => {
    setDatasetIdState(id);
    localStorage.setItem(LOCAL_STORAGE_DATASET_KEY, id);
    if (id === RESEARCH_TIER_IDS.medium_real) {
      setResearchTierState("medium_real");
      localStorage.setItem(LOCAL_STORAGE_TIER_KEY, "medium_real");
    } else if (id === RESEARCH_TIER_IDS.large_real) {
      setResearchTierState("large_real");
      localStorage.setItem(LOCAL_STORAGE_TIER_KEY, "large_real");
    }
    // Reset anomalies when switching dataset
    setAnomalyResults({});
    setSelectedNodeId(null);
  };

  /** Switch research tier: atomically updates both tier + datasetId */
  const setResearchTier = (tier: ResearchTier) => {
    setResearchTierState(tier);
    localStorage.setItem(LOCAL_STORAGE_TIER_KEY, tier);
    setDatasetId(RESEARCH_TIER_IDS[tier]);
  };

  const setExperimentLabel = (label: string) => {
    setExperimentLabelState(label);
    localStorage.setItem(LOCAL_STORAGE_EXP_KEY, label);
  };

  const setSplitLabel = (label: string | null) => {
    setSplitLabelState(label);
    if (label) {
      localStorage.setItem(LOCAL_STORAGE_SPLIT_KEY, label);
    } else {
      localStorage.removeItem(LOCAL_STORAGE_SPLIT_KEY);
    }
  };

  const addDatasetToHistory = (item: DatasetHistoryItem) => {
    setDatasetHistory((prev) => {
      const filtered = prev.filter((d) => d.id !== item.id);
      const updated = [item, ...filtered];
      localStorage.setItem(LOCAL_STORAGE_HISTORY_KEY, JSON.stringify(updated.slice(0, 20)));
      return updated;
    });
  };

  const checkBackendHealth = async (): Promise<boolean> => {
    try {
      await api.checkHealth();
      setIsBackendConnected(true);
      setBackendError(null);
      return true;
    } catch (err: any) {
      setIsBackendConnected(false);
      setBackendError(err?.message || "Cannot connect to FastAPI backend at port 8000.");
      return false;
    }
  };

  // Check health on mount
  useEffect(() => {
    checkBackendHealth();
  }, []);

  return (
    <AppContext.Provider
      value={{
        datasetId,
        setDatasetId,
        experimentLabel,
        setExperimentLabel,
        splitLabel,
        setSplitLabel,
        activeNav,
        setActiveNav,
        datasetHistory,
        addDatasetToHistory,
        cachedEdges,
        setCachedEdges,
        selectedNodeId,
        setSelectedNodeId,
        anomalyResults,
        setAnomalyResults,
        isBackendConnected,
        backendError,
        checkBackendHealth,
        researchTier,
        setResearchTier,
        isOfficialResearch: isOfficialResearchDataset(datasetId),
        datasetCurrency,
        setDatasetCurrency,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return ctx;
};
