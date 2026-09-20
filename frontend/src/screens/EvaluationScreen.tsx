/**
 * EvaluationScreen
 *
 * Supports two strictly separated evaluation modes:
 *
 * 1. "Official Research Results" — static, locked, loaded from frozen JSON
 *    (/data/final_e0_e4_comparison.json), IBM AML 5K/50K tiers only.
 *    Completely untouched and undisturbed.
 *
 * 2. "Custom Evaluation" — live evaluation on user-uploaded datasets,
 *    using live backend endpoints (labels -> split -> train -> evaluate/compare).
 *    Never touches or modifies locked benchmark artifacts.
 */
import React, { useEffect, useState, useMemo, useRef } from "react";
import {
  useApp,
  RESEARCH_TIER_IDS,
  isOfficialResearchDataset,
} from "../context/AppContext";
import { Table, Column } from "../components/ui/Table";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Checkbox } from "../components/ui/Checkbox";
import { ExportDropdown } from "../components/ui/ExportDropdown";
import {
  ResearchChartsSection,
  LockedExperiment,
} from "../components/ui/ResearchChartsSection";
import { api } from "../api/client";
import {
  DatasetLabelsSummaryResponse,
  EvaluationComparisonResponse,
  ExperimentEvaluationMetrics,
  SplitSummaryResponse,
} from "../types/api";
import { formatPercent, truncateId } from "../utils/formatters";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  LineChart,
  Line,
} from "recharts";
import { TERMINOLOGY } from "../constants/terminology";

// ─────────────────────────────────────────────────────────────────────────────
// OFFICIAL RESEARCH VIEW CONSTANTS & TYPES
// ─────────────────────────────────────────────────────────────────────────────
const FINDING_STATEMENT: string | null = null;

const TIER_5K_ID = "ddbaab44-78b6-41be-a8fb-e83dfec66358";
const TIER_50K_ID = "03fb9ab0-4f42-4404-9d76-723fd4d8753e";

const EXP_DISPLAY: Record<string, string> = {
  E0_graph_baseline: "E0 — Graph / Statistical Baseline",
  E1_graph_ml: "E1 — Graph + Isolation Forest",
  E2_graph_behavioral_ml: "E2 — Graph + Behavioral + IF",
  E3_graph_temporal_ml: "E3 — Graph + Temporal + IF",
  E4_full_graphfin: "E4 — Graph + Behavioral + Temporal + IF",
};

const getExperimentDisplayName = (label: string): string =>
  EXP_DISPLAY[label] ?? label;

const getFeatureConfigDisplay = (groups: string[], count: number): string => {
  const gList = groups.map((g) => g.charAt(0).toUpperCase() + g.slice(1)).join(" + ");
  return `${gList || "Custom"} (${count} features)`;
};

const ORDERED_EXP = [
  "E0_graph_baseline",
  "E1_graph_ml",
  "E2_graph_behavioral_ml",
  "E3_graph_temporal_ml",
  "E4_full_graphfin",
];

// ─────────────────────────────────────────────────────────────────────────────
// 1. OFFICIAL RESEARCH RESULTS VIEW (LOCKED BENCHMARK)
// ─────────────────────────────────────────────────────────────────────────────
const OfficialResearchView: React.FC = () => {
  const { researchTier, setResearchTier } = useApp();

  const [allExperiments, setAllExperiments] = useState<LockedExperiment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedExpLabel, setSelectedExpLabel] = useState<string>("E0_graph_baseline");

  // Fetch the static locked JSON once on mount
  useEffect(() => {
    setIsLoading(true);
    setLoadError(null);
    fetch(`${import.meta.env.BASE_URL}data/final_e0_e4_comparison.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load locked results (HTTP ${r.status})`);
        return r.json();
      })
      .then((data) => {
        setAllExperiments(data.experiments ?? []);
        setIsLoading(false);
      })
      .catch((err) => {
        setLoadError(err.message ?? "Could not load final_e0_e4_comparison.json");
        setIsLoading(false);
      });
  }, []);

  // Filter to active tier's 5 experiments, ordered
  const tierExperiments = useMemo<LockedExperiment[]>(() => {
    const activeTierId = researchTier === "medium_real" ? TIER_5K_ID : TIER_50K_ID;
    const filtered = allExperiments.filter((e) => e.dataset_id === activeTierId);
    return ORDERED_EXP.map((label) => filtered.find((e) => e.experiment_label === label)!).filter(Boolean);
  }, [allExperiments, researchTier]);

  const activeTierDatasetId = researchTier === "medium_real" ? TIER_5K_ID : TIER_50K_ID;
  const tierLabel = researchTier === "medium_real" ? "5,000 accounts" : "49,992 accounts";
  const tierShort = researchTier === "medium_real" ? "5K" : "50K";

  // Dense results table columns
  const columns: Column<LockedExperiment>[] = [
    {
      key: "experiment_label",
      header: "Experiment",
      render: (row) => (
        <div>
          <span className="font-sans text-text-primary font-medium block text-xs">
            {getExperimentDisplayName(row.experiment_label)}
          </span>
          <span className="font-mono text-[10px] text-text-tertiary">{row.experiment_label}</span>
        </div>
      ),
    },
    {
      key: "feature_count",
      header: "Feature Config",
      render: (row) => (
        <span className="text-text-secondary text-xs">
          {getFeatureConfigDisplay(row.feature_groups, row.feature_count)}
        </span>
      ),
    },
    {
      key: "pr_auc",
      header: "PR-AUC",
      align: "right",
      mono: true,
      render: (row) => <span className="font-mono text-text-primary font-medium">{row.pr_auc.toFixed(4)}</span>,
    },
    {
      key: "roc_auc",
      header: "ROC-AUC",
      align: "right",
      mono: true,
      render: (row) => row.roc_auc.toFixed(4),
    },
    {
      key: "f1_score",
      header: "F1",
      align: "right",
      mono: true,
      render: (row) => row.f1_score.toFixed(4),
    },
    {
      key: "precision",
      header: "Precision",
      align: "right",
      mono: true,
      render: (row) => row.precision.toFixed(4),
    },
    {
      key: "recall",
      header: "Recall",
      align: "right",
      mono: true,
      render: (row) => row.recall.toFixed(4),
    },
    {
      key: "tp",
      header: "TP",
      align: "right",
      mono: true,
      render: (row) => <span className="text-status-normal font-mono">{row.tp}</span>,
    },
    {
      key: "fp",
      header: "FP",
      align: "right",
      mono: true,
      render: (row) => <span className="text-status-warning font-mono">{row.fp}</span>,
    },
    {
      key: "tn",
      header: "TN",
      align: "right",
      mono: true,
      render: (row) => row.tn.toLocaleString(),
    },
    {
      key: "fn",
      header: "FN",
      align: "right",
      mono: true,
      render: (row) => <span className="text-status-suspicious font-mono">{row.fn}</span>,
    },
    {
      key: "evaluation_mode",
      header: "Eval Mode",
      render: (row) => (
        <div>
          <Badge variant="normal">{row.evaluation_mode}</Badge>
          <span className="text-[10px] font-mono text-text-tertiary block mt-0.5">
            {row.test_positive}+ / {row.test_negative.toLocaleString()}−
          </span>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8 max-w-[1040px] mx-auto text-left">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-sans font-medium text-text-primary flex items-center gap-2">
            <span>Research Evaluation</span>
            <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/25 rounded text-[11px] font-mono uppercase tracking-wider font-semibold">
              Official Locked Benchmark
            </span>
          </h1>
          <p className="text-sm font-sans text-text-secondary mt-1">
            Finalized benchmark results — IBM AML HI-Small subsamples, E0–E4 experiments,
            held-out evaluation. Loaded from locked static output.
          </p>
        </div>

        {/* Multi-format export dropdown */}
        <ExportDropdown source="official" />
      </div>

      {/* ── Research Tier Selector (5K vs 50K) ── */}
      <div className="flex items-center justify-between p-3 bg-surface border border-hairline rounded">
        <div className="flex items-center gap-3">
          <span className="text-xs font-sans text-text-secondary font-medium">
            Active Research Benchmark Tier:
          </span>
          <div className="flex items-center bg-surface-raised border border-hairline rounded p-0.5">
            <button
              type="button"
              onClick={() => setResearchTier("medium_real")}
              className={`px-3 py-1.5 text-xs font-sans rounded transition-colors flex items-center gap-1.5 ${
                researchTier === "medium_real"
                  ? "bg-accent-primary text-white font-medium shadow-sm"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface"
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-blue-300" />
              <span>5,000 accounts (5K)</span>
            </button>
            <button
              type="button"
              onClick={() => setResearchTier("large_real")}
              className={`px-3 py-1.5 text-xs font-sans rounded transition-colors flex items-center gap-1.5 ${
                researchTier === "large_real"
                  ? "bg-accent-primary text-white font-medium shadow-sm"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface"
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-blue-300" />
              <span>49,992 accounts (50K)</span>
            </button>
          </div>
        </div>
        <div className="text-[11px] font-mono text-text-tertiary">
          Dataset ID: <span className="text-text-secondary font-mono">{activeTierDatasetId}</span>
        </div>
      </div>

      {/* ── Research Summary Card ── */}
      <div className="p-5 bg-surface border border-hairline rounded space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-sans uppercase tracking-wider text-text-tertiary font-medium">
            Research Summary
          </span>
          <Badge variant="normal">Held-out evaluation</Badge>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-8 gap-y-3 text-xs font-sans">
          <div>
            <span className="text-text-tertiary block">Dataset</span>
            <span className="text-text-primary">IBM AML HI-Small (Kaggle, IBM AMLSim / AMLworld-generated)</span>
          </div>
          <div>
            <span className="text-text-tertiary block">Evaluation tiers</span>
            <span className="text-text-primary">5,000 accounts / 49,992 accounts (stratified subsamples)</span>
          </div>
          <div>
            <span className="text-text-tertiary block">Ground-truth labels</span>
            <span className="text-text-primary">Real Is-Laundering ground truth aggregated to account level (any involvement rule)</span>
          </div>
          <div>
            <span className="text-text-tertiary block">Experiments</span>
            <span className="text-text-primary">E0 (graph / statistical baseline) through E4 (full GraphFin)</span>
          </div>
          <div>
            <span className="text-text-tertiary block">Evaluation protocol</span>
            <span className="text-text-primary">70/30 stratified entity-level held-out split</span>
          </div>
          <div>
            <span className="text-text-tertiary block">Primary metric</span>
            <span className="text-text-primary">
              PR-AUC — chosen due to severe class imbalance
              (~0.4–0.5% positive prevalence at both tiers)
            </span>
          </div>
        </div>

        {/* Robustness placeholder note */}
        <div className="pt-3 border-t border-hairline">
          <p className="text-xs font-sans text-text-secondary leading-relaxed">
            <span className="font-medium text-text-primary">Note: </span>
            Cross-scale feature-group comparison based on a single stratified split
            (random_state=42). A multi-seed robustness check is in progress to confirm
            whether observed differences between feature groups are stable or attributable
            to the small number of positive test cases at these scales. Provisional
            single-split PR-AUC/ROC-AUC values are shown below; do not treat differences
            between experiments as conclusive until that check is complete.
          </p>
          {FINDING_STATEMENT !== null && (
            <p className="text-xs font-sans text-text-primary font-medium mt-2 pt-2 border-t border-hairline">
              <span className="text-text-tertiary">Finding: </span>
              {FINDING_STATEMENT}
            </p>
          )}
        </div>
      </div>

      {/* ── Small-Sample Caution Card ── */}
      <div className="p-4 bg-surface border-l-4 border-amber-500/80 rounded-r space-y-1.5 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold tracking-wider bg-amber-500/15 text-amber-400 rounded border border-amber-500/30">
            SAMPLE SIZE CAUTION
          </span>
          <span className="text-xs font-sans font-medium text-text-primary">
            Real Ground-Truth Labels · Small Positive Sample Size in Held-Out Test Partition
          </span>
        </div>
        <p className="text-xs font-sans text-text-secondary leading-relaxed">
          Ground-truth labels are real <span className="font-mono text-text-primary">Is-Laundering</span>-derived
          classifications aggregated to the account level via the documented &ldquo;any involvement&rdquo; rule (not synthetic labels).
          Due to extreme real-world class imbalance (~0.4–0.5% positive prevalence), the held-out test partition contains
          a small absolute number of positive cases: 6 positives at 5,000 accounts and 75 positives at 49,992 accounts.
        </p>
        <p className="text-[11px] font-sans text-text-tertiary leading-relaxed">
          The caution concerns sample size (single-split evaluation, pending multi-seed verification), not label authenticity.
          Observed performance differences between feature groups should not be considered conclusive until multi-seed
          robustness checks confirm cross-split stability.
        </p>
      </div>

      {/* ── Research Question ── */}
      <div className="p-4 bg-surface border border-hairline rounded space-y-1.5">
        <span className="text-xs font-sans uppercase tracking-wider text-text-tertiary font-medium block">
          Research Question
        </span>
        <p className="text-sm font-sans text-text-primary font-normal italic">
          &ldquo;Does enriching graph-based transaction representations with behavioral and temporal
          information improve anomaly detection compared with the existing graph/statistical approach?&rdquo;
        </p>
        <p className="text-[11px] font-sans text-text-secondary">
          Empirical measurements below provide evaluation evidence without preconceived winner designations.
        </p>
      </div>

      {/* ── Methodology Pipeline ── */}
      <div className="p-4 bg-surface border border-hairline rounded space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-sans uppercase tracking-wider text-text-tertiary font-medium">
            Pipeline Methodology Flow
          </span>
          <span className="text-[11px] font-mono text-text-tertiary">
            E0: Statistical Baseline · E1–E4: Isolation Forest ML
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono">
          {[
            { label: "Raw Transactions", cls: "text-text-primary border-hairline" },
            { label: "Preprocessing", cls: "text-text-primary border-hairline" },
            { label: "Directed Weighted Graph", cls: "text-text-primary border-hairline" },
            { label: "Graph Features (6)", cls: "text-blue-400 border-blue-500/30" },
            { label: "Behavioral Features (8)", cls: "text-emerald-400 border-emerald-500/30" },
            { label: "Temporal Features (5)", cls: "text-purple-400 border-purple-500/30" },
            { label: "Isolation Forest", cls: "text-amber-400 border-amber-500/30 font-semibold" },
            { label: "Anomaly Score", cls: "text-text-primary border-hairline" },
            { label: "Held-Out Evaluation", cls: "text-text-primary border-hairline" },
            { label: "Research Metrics", cls: "text-text-primary border-hairline" },
          ].map((step, i, arr) => (
            <React.Fragment key={step.label}>
              <span className={`px-2 py-1 rounded bg-surface-raised border ${step.cls}`}>
                {step.label}
              </span>
              {i < arr.length - 1 && <span className="text-text-tertiary">↓</span>}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Loading / error states */}
      {isLoading && (
        <div className="py-10 text-center text-sm font-sans text-text-tertiary">
          Loading locked research results…
        </div>
      )}
      {loadError && (
        <div className="p-3 bg-[#2D1619] border border-[#521A1F] rounded text-xs font-sans text-status-suspicious">
          {loadError}
        </div>
      )}

      {!isLoading && !loadError && tierExperiments.length > 0 && (
        <>
          {/* ── Charts ── */}
          <ResearchChartsSection
            experiments={allExperiments}
            activeTierDatasetId={activeTierDatasetId}
            selectedExpLabel={selectedExpLabel}
            onSelectExp={setSelectedExpLabel}
          />

          {/* ── Dense results table ── */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-sans font-medium text-text-primary flex items-center gap-2">
                <span>Held-out Evaluation Results</span>
                <Badge variant="normal">Publication grade</Badge>
              </h2>
              <span className="text-xs font-sans text-text-tertiary">
                {tierShort} tier · {tierLabel} · random_state=42
              </span>
            </div>
            <Table
              columns={columns}
              data={tierExperiments}
              emptyMessage="No results found for this tier."
            />
            <p className="text-[11px] font-sans text-text-tertiary leading-relaxed">
              Results are read from the locked static file{" "}
              <span className="font-mono">final_e0_e4_comparison.json</span> and do not
              reflect any live backend state. TP/FP/TN/FN counts are at the
              contamination-rate threshold; AUC metrics are threshold-independent.
            </p>
          </div>
        </>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// 2. CUSTOM EVALUATION VIEW (LIVE USER-UPLOADED DATASET)
// ─────────────────────────────────────────────────────────────────────────────
const CustomEvaluationView: React.FC = () => {
  const { datasetId, splitLabel, setActiveNav } = useApp();

  // Data state
  const [labelsSummary, setLabelsSummary] = useState<DatasetLabelsSummaryResponse | null>(null);
  const [splits, setSplits] = useState<SplitSummaryResponse[]>([]);
  const [txCount, setTxCount] = useState<number>(0);
  const [comparison, setComparison] = useState<EvaluationComparisonResponse | null>(null);
  const [selectedExp, setSelectedExp] = useState<ExperimentEvaluationMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Quick Inline Label Upload state
  const [isUploadingLabels, setIsUploadingLabels] = useState(false);
  const [labelUploadError, setLabelUploadError] = useState<string | null>(null);
  const labelFileRef = useRef<HTMLInputElement>(null);

  // Quick Model Training state
  const [isTraining, setIsTraining] = useState(false);
  const [trainError, setTrainError] = useState<string | null>(null);
  const [expName, setExpName] = useState("custom_if_model");
  const [includeGraph, setIncludeGraph] = useState(true);
  const [includeBehavioral, setIncludeBehavioral] = useState(true);
  const [includeTemporal, setIncludeTemporal] = useState(true);

  // Load custom dataset evaluation state
  const loadCustomData = async () => {
    if (!datasetId) return;
    setIsLoading(true);
    setError(null);

    try {
      // 1. Transaction stats
      try {
        const txSummary = await api.getTransactionSummary(datasetId);
        setTxCount(txSummary.transactions);
      } catch {
        setTxCount(0);
      }

      // 2. Labels summary
      let lblSummary: DatasetLabelsSummaryResponse | null = null;
      try {
        lblSummary = await api.getLabelsSummary(datasetId);
        setLabelsSummary(lblSummary);
      } catch {
        setLabelsSummary(null);
      }

      // 3. Splits
      try {
        const splitList = await api.listSplits(datasetId);
        setSplits(splitList);
      } catch {
        setSplits([]);
      }

      // 4. Comparison of trained experiments (only if labels exist)
      if (lblSummary && lblSummary.matched_count > 0) {
        try {
          const comp = await api.compareExperiments(datasetId, true, splitLabel || undefined);
          setComparison(comp);
          if (comp.experiments && comp.experiments.length > 0) {
            setSelectedExp(comp.experiments[0]);
          } else {
            setSelectedExp(null);
          }
        } catch {
          setComparison(null);
          setSelectedExp(null);
        }
      } else {
        setComparison(null);
        setSelectedExp(null);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load live evaluation data.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCustomData();
  }, [datasetId, splitLabel]);

  // Handle Quick Label Upload
  const handleUploadLabels = async (file: File) => {
    if (!datasetId) return;
    setIsUploadingLabels(true);
    setLabelUploadError(null);
    try {
      const summary = await api.uploadLabels(datasetId, file, {
        userIdCol: "user_id",
        labelCol: "label",
        strict: false,
      });
      setLabelsSummary(summary);
      await loadCustomData();
    } catch (err: any) {
      setLabelUploadError(err.message || "Label upload failed.");
    } finally {
      setIsUploadingLabels(false);
    }
  };

  // Handle Quick Model Train
  const handleQuickTrain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetId) return;

    const featureGroups: string[] = [];
    if (includeGraph) featureGroups.push("graph");
    if (includeBehavioral) featureGroups.push("behavioral");
    if (includeTemporal) featureGroups.push("temporal");

    if (featureGroups.length === 0) {
      setTrainError("Select at least one feature group.");
      return;
    }

    setIsTraining(true);
    setTrainError(null);

    try {
      await api.trainAnomalyModel(
        datasetId,
        {
          experiment_label: expName.trim() || "custom_if_model",
          feature_groups: featureGroups,
          n_estimators: 100,
          contamination: 0.1,
          random_state: 42,
          split_label: splitLabel || null,
        },
        expName.trim() || "custom_if_model",
        splitLabel || undefined
      );
      await loadCustomData();
    } catch (err: any) {
      setTrainError(err.message || "Training failed.");
    } finally {
      setIsTraining(false);
    }
  };

  // Custom table columns
  const customColumns: Column<ExperimentEvaluationMetrics>[] = [
    {
      key: "experiment_label",
      header: "Experiment",
      render: (row) => (
        <div>
          <span className="font-sans text-text-primary font-medium block text-xs">
            {row.experiment_label}
          </span>
          <span className="font-mono text-[10px] text-text-tertiary">
            {row.method || row.model_type || "Isolation Forest"}
          </span>
        </div>
      ),
    },
    {
      key: "feature_groups",
      header: "Features",
      render: (row) => (
        <span className="text-text-secondary text-xs">
          {row.feature_groups && row.feature_groups.length > 0
            ? row.feature_groups.join(" + ")
            : "Default"}{" "}
          ({row.feature_count ?? row.feature_names?.length ?? 0})
        </span>
      ),
    },
    {
      key: "pr_auc",
      header: "PR-AUC",
      align: "right",
      mono: true,
      render: (row) => (
        <span className="font-mono text-text-primary font-semibold">
          {row.pr_auc !== null && row.pr_auc !== undefined ? row.pr_auc.toFixed(4) : "—"}
        </span>
      ),
    },
    {
      key: "roc_auc",
      header: "ROC-AUC",
      align: "right",
      mono: true,
      render: (row) =>
        row.roc_auc !== null && row.roc_auc !== undefined ? row.roc_auc.toFixed(4) : "—",
    },
    {
      key: "f1_score",
      header: "F1",
      align: "right",
      mono: true,
      render: (row) =>
        row.f1_score !== null && row.f1_score !== undefined ? row.f1_score.toFixed(4) : "—",
    },
    {
      key: "precision",
      header: "Precision",
      align: "right",
      mono: true,
      render: (row) =>
        row.precision !== null && row.precision !== undefined ? row.precision.toFixed(4) : "—",
    },
    {
      key: "recall",
      header: "Recall",
      align: "right",
      mono: true,
      render: (row) =>
        row.recall !== null && row.recall !== undefined ? row.recall.toFixed(4) : "—",
    },
    {
      key: "accuracy",
      header: "Accuracy",
      align: "right",
      mono: true,
      render: (row) =>
        row.accuracy !== null && row.accuracy !== undefined ? row.accuracy.toFixed(4) : "—",
    },
    {
      key: "evaluation_mode",
      header: "Eval Mode",
      render: (row) => (
        <div>
          <Badge variant={row.evaluation_mode === "held_out" ? "normal" : "neutral"}>
            {row.evaluation_mode || "in_sample"}
          </Badge>
          <span className="text-[10px] font-mono text-text-tertiary block mt-0.5">
            {row.positive_count ?? 0}+ / {(row.negative_count ?? 0).toLocaleString()}−
          </span>
        </div>
      ),
    },
  ];

  const experimentsList = comparison?.experiments?.filter((e) => e.status === "success") || [];

  return (
    <div className="space-y-8 max-w-[1040px] mx-auto text-left">
      {/* Page header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-sans font-medium text-text-primary flex items-center gap-2">
            <span>Custom Evaluation</span>
            <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 rounded text-[11px] font-mono uppercase tracking-wider font-semibold">
              Live Custom Mode
            </span>
          </h1>
          <p className="text-sm font-sans text-text-secondary mt-1">
            Custom Evaluation — live results on your uploaded data. Not part of the official locked research benchmark.
          </p>
        </div>

        {/* Multi-format export dropdown for custom results */}
        <ExportDropdown source="custom" datasetId={datasetId} splitLabel={splitLabel} />
      </div>

      {/* ── Dataset Stats & Metadata Card ── */}
      <div className="p-5 bg-surface border border-hairline rounded space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-sans uppercase tracking-wider text-text-tertiary font-medium">
            Active Dataset Overview
          </span>
          <span className="font-mono text-xs text-text-tertiary">
            ID: {truncateId(datasetId, 12, 6)}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-sans pt-1">
          <div className="p-3 bg-surface-raised/40 rounded border border-hairline">
            <span className="text-text-tertiary block text-[11px]">Transactions</span>
            <span className="text-base font-medium font-mono text-text-primary">
              {txCount.toLocaleString()}
            </span>
          </div>

          <div className="p-3 bg-surface-raised/40 rounded border border-hairline">
            <span className="text-text-tertiary block text-[11px]">Ground-Truth Labels</span>
            <span className="text-base font-medium font-mono text-text-primary">
              {labelsSummary ? `${labelsSummary.matched_count.toLocaleString()} accounts` : "None"}
            </span>
          </div>

          <div className="p-3 bg-surface-raised/40 rounded border border-hairline">
            <span className="text-text-tertiary block text-[11px]">{TERMINOLOGY.POSITIVE_PREVALENCE}</span>
            <span className="text-base font-medium font-mono text-text-primary">
              {labelsSummary && labelsSummary.matched_count > 0
                ? `${formatPercent(labelsSummary.prevalence_rate, 2)} (${labelsSummary.positive_count} ${TERMINOLOGY.POSITIVE.toLowerCase()})`
                : "—"}
            </span>
          </div>

          <div className="p-3 bg-surface-raised/40 rounded border border-hairline">
            <span className="text-text-tertiary block text-[11px]">Evaluation Partition</span>
            <span className="text-base font-medium font-sans text-text-primary">
              {splitLabel ? `Split: ${splitLabel}` : "In-Sample"}
            </span>
          </div>
        </div>
      </div>

      {/* ── Small-Sample Caution (if positive labels < 30) ── */}
      {labelsSummary && labelsSummary.positive_count < 30 && (
        <div className="p-4 bg-surface border-l-4 border-amber-500/80 rounded-r space-y-1.5 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold tracking-wider bg-amber-500/15 text-amber-400 rounded border border-amber-500/30">
              SAMPLE SIZE CAUTION
            </span>
            <span className="text-xs font-sans font-medium text-text-primary">
              Low Positive Label Count ({labelsSummary.positive_count} cases)
            </span>
          </div>
          <p className="text-xs font-sans text-text-secondary leading-relaxed">
            This uploaded dataset has only <span className="font-mono text-text-primary">{labelsSummary.positive_count}</span> positive labels.
            Metric estimates (especially Precision, Recall, and PR-AUC) have wider uncertainty bounds under small sample sizes.
          </p>
        </div>
      )}

      {/* ── State 1: No Labels Uploaded ── */}
      {(!labelsSummary || labelsSummary.matched_count === 0) && (
        <div className="p-6 bg-surface border border-hairline rounded space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-sans font-medium text-text-primary flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-status-warning" />
              <span>Step 1: Upload Ground-Truth Labels</span>
            </h3>
            <Button size="sm" variant="ghost" onClick={() => setActiveNav("labels_splits")}>
              Go to Labels & Splits Screen →
            </Button>
          </div>

          <p className="text-xs font-sans text-text-secondary leading-relaxed">
            Classification metrics (Precision, Recall, F1, ROC-AUC, and PR-AUC) require ground-truth labels to evaluate predictions.
            Upload a CSV containing <code className="text-text-primary">user_id</code> and <code className="text-text-primary">label</code> columns to enable live evaluation.
          </p>

          <div className="flex items-center gap-4 pt-2">
            <input
              type="file"
              ref={labelFileRef}
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleUploadLabels(e.target.files[0]);
                }
              }}
            />
            <Button
              size="sm"
              variant="primary"
              disabled={isUploadingLabels}
              onClick={() => labelFileRef.current?.click()}
            >
              {isUploadingLabels ? "Uploading Labels..." : "Select Labels CSV File"}
            </Button>
            <span className="text-xs text-text-tertiary font-mono">
              Accepted headers: user_id, label (1/0, true/false)
            </span>
          </div>

          {labelUploadError && (
            <div className="p-2.5 bg-red-950/80 border border-red-800 text-xs text-red-200 rounded">
              {labelUploadError}
            </div>
          )}
        </div>
      )}

      {/* ── State 2: Labels exist, but No Models Trained ── */}
      {labelsSummary && labelsSummary.matched_count > 0 && experimentsList.length === 0 && !isLoading && (
        <div className="p-6 bg-surface border border-hairline rounded space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-sans font-medium text-text-primary flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-400" />
              <span>Step 2: Train Anomaly Models for Evaluation</span>
            </h3>
            <Button size="sm" variant="ghost" onClick={() => setActiveNav("anomalies")}>
              Open Full Anomaly Models Screen →
            </Button>
          </div>

          <p className="text-xs font-sans text-text-secondary leading-relaxed">
            Ground-truth labels are ready ({labelsSummary.matched_count} accounts). Train one or more model variants
            to compute performance metrics and generate the evaluation report.
          </p>

          <form onSubmit={handleQuickTrain} className="space-y-4 pt-2">
            <div className="flex flex-wrap items-center gap-4">
              <div className="w-56">
                <Input
                  label="Experiment Name"
                  value={expName}
                  onChange={(e) => setExpName(e.target.value)}
                  placeholder="e.g. e4_custom"
                />
              </div>

              <div className="flex items-center gap-4 pt-5">
                <Checkbox
                  label="Graph Features (6)"
                  checked={includeGraph}
                  onChange={(e) => setIncludeGraph(e.target.checked)}
                />
                <Checkbox
                  label="Behavioral Features (8)"
                  checked={includeBehavioral}
                  onChange={(e) => setIncludeBehavioral(e.target.checked)}
                />
                <Checkbox
                  label="Temporal Features (5)"
                  checked={includeTemporal}
                  onChange={(e) => setIncludeTemporal(e.target.checked)}
                />
              </div>

              <div className="pt-5">
                <Button size="sm" variant="primary" type="submit" disabled={isTraining}>
                  {isTraining ? "Training Model..." : "Train & Evaluate"}
                </Button>
              </div>
            </div>

            {trainError && (
              <div className="p-2.5 bg-red-950/80 border border-red-800 text-xs text-red-200 rounded">
                {trainError}
              </div>
            )}
          </form>
        </div>
      )}

      {/* ── State 3: Experiments Trained -> Results Table & Charts ── */}
      {experimentsList.length > 0 && (
        <>
          {/* Quick Train Another Model Header */}
          <div className="p-4 bg-surface border border-hairline rounded flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-xs font-sans text-text-secondary">
                <strong className="text-text-primary">{experimentsList.length}</strong> model variant(s) evaluated live against stored labels.
              </span>
            </div>
            <Button size="sm" variant="secondary" onClick={() => setActiveNav("anomalies")}>
              Train More Model Variants →
            </Button>
          </div>

          {/* Comparison Bar Chart */}
          <div className="p-5 bg-surface border border-hairline rounded space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-sans uppercase tracking-wider text-text-tertiary font-medium">
                Comparative PR-AUC Performance
              </h3>
              <span className="text-[11px] font-mono text-text-tertiary">
                Ranked descending by PR-AUC
              </span>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={experimentsList.map((e) => ({
                    name: e.experiment_label,
                    pr_auc: e.pr_auc || 0,
                    roc_auc: e.roc_auc || 0,
                  }))}
                  margin={{ top: 10, right: 20, left: -10, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 1]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", fontSize: "11px" }}
                  />
                  <Bar dataKey="pr_auc" name="PR-AUC" fill="#34d399" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="roc_auc" name="ROC-AUC" fill="#60a5fa" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Detailed Dense Results Table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-sans font-medium text-text-primary flex items-center gap-2">
                <span>Live Evaluation Comparison Table</span>
                <Badge variant="neutral">Custom Upload</Badge>
              </h2>
              <span className="text-xs font-sans text-text-tertiary">
                Click a row to inspect curves & confusion matrix
              </span>
            </div>

            <Table
              columns={customColumns}
              data={experimentsList}
              onRowClick={(row) => setSelectedExp(row)}
              emptyMessage="No evaluation results available."
            />
          </div>

          {/* Selected Experiment Deep-Dive: Curves & Confusion Matrix */}
          {selectedExp && (
            <div className="p-5 bg-surface border border-hairline rounded space-y-4">
              <div className="flex items-center justify-between border-b border-hairline pb-3">
                <div>
                  <h3 className="text-sm font-sans font-medium text-text-primary flex items-center gap-2">
                    <span>Experiment Deep-Dive: {selectedExp.experiment_label}</span>
                    <Badge variant="normal">
                      {selectedExp.method || selectedExp.model_type || "Isolation Forest"}
                    </Badge>
                  </h3>
                  <span className="text-xs font-sans text-text-secondary mt-0.5 block">
                    Mode: <span className="font-mono text-text-primary">{selectedExp.evaluation_mode}</span> · Split:{" "}
                    <span className="font-mono text-text-primary">{selectedExp.split_label || "None"}</span>
                  </span>
                </div>

                <div className="text-right font-mono text-xs">
                  <span className="text-text-tertiary">PR-AUC: </span>
                  <span className="text-emerald-400 font-bold text-sm">
                    {selectedExp.pr_auc ? selectedExp.pr_auc.toFixed(4) : "—"}
                  </span>
                  <span className="text-text-tertiary ml-3">ROC-AUC: </span>
                  <span className="text-blue-400 font-bold text-sm">
                    {selectedExp.roc_auc ? selectedExp.roc_auc.toFixed(4) : "—"}
                  </span>
                </div>
              </div>

              {/* Confusion Matrix Breakdown */}
              {selectedExp.confusion_matrix && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                  <div className="p-3 bg-surface-raised/60 rounded border border-hairline">
                    <span className="text-[10px] uppercase font-mono text-text-tertiary block">
                      True Positives ({TERMINOLOGY.TP})
                    </span>
                    <span className="text-lg font-bold font-mono text-status-normal">
                      {selectedExp.confusion_matrix.tp}
                    </span>
                    <span className="text-[10px] text-text-tertiary block">{TERMINOLOGY.ANOMALIES_DETECTED}</span>
                  </div>

                  <div className="p-3 bg-surface-raised/60 rounded border border-hairline">
                    <span className="text-[10px] uppercase font-mono text-text-tertiary block">
                      False Positives ({TERMINOLOGY.FP})
                    </span>
                    <span className="text-lg font-bold font-mono text-status-warning">
                      {selectedExp.confusion_matrix.fp}
                    </span>
                    <span className="text-[10px] text-text-tertiary block">{TERMINOLOGY.FALSE_ALARMS}</span>
                  </div>

                  <div className="p-3 bg-surface-raised/60 rounded border border-hairline">
                    <span className="text-[10px] uppercase font-mono text-text-tertiary block">
                      True Negatives ({TERMINOLOGY.TN})
                    </span>
                    <span className="text-lg font-bold font-mono text-text-primary">
                      {selectedExp.confusion_matrix.tn.toLocaleString()}
                    </span>
                    <span className="text-[10px] text-text-tertiary block">{TERMINOLOGY.NORMAL_CLEARED}</span>
                  </div>

                  <div className="p-3 bg-surface-raised/60 rounded border border-hairline">
                    <span className="text-[10px] uppercase font-mono text-text-tertiary block">
                      False Negatives ({TERMINOLOGY.FN})
                    </span>
                    <span className="text-lg font-bold font-mono text-status-suspicious">
                      {selectedExp.confusion_matrix.fn}
                    </span>
                    <span className="text-[10px] text-text-tertiary block">{TERMINOLOGY.ANOMALIES_MISSED}</span>
                  </div>
                </div>
              )}

              {/* ROC & PR Curve Charts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                {/* Precision-Recall Curve */}
                <div className="p-3 bg-surface-raised/30 rounded border border-hairline">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-sans font-medium text-text-primary">
                      Precision-Recall Curve
                    </span>
                    <span className="text-[11px] font-mono text-emerald-400">
                      PR-AUC = {selectedExp.pr_auc?.toFixed(4) || "—"}
                    </span>
                  </div>
                  {selectedExp.precision_recall_curve && selectedExp.precision_recall_curve.recall.length > 0 ? (
                    <div className="h-44 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={selectedExp.precision_recall_curve.recall.map((r: number, i: number) => ({
                            recall: r,
                            precision: selectedExp.precision_recall_curve!.precision[i],
                          }))}
                          margin={{ top: 5, right: 10, left: -20, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                          <XAxis dataKey="recall" stroke="#94a3b8" fontSize={10} domain={[0, 1]} />
                          <YAxis stroke="#94a3b8" fontSize={10} domain={[0, 1]} />
                          <Tooltip contentStyle={{ backgroundColor: "#0f172a", fontSize: "10px" }} />
                          <Line type="monotone" dataKey="precision" stroke="#34d399" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-44 flex items-center justify-center text-xs text-text-tertiary">
                      Curve points not available for this run.
                    </div>
                  )}
                </div>

                {/* ROC Curve */}
                <div className="p-3 bg-surface-raised/30 rounded border border-hairline">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-sans font-medium text-text-primary">
                      ROC Curve
                    </span>
                    <span className="text-[11px] font-mono text-blue-400">
                      ROC-AUC = {selectedExp.roc_auc?.toFixed(4) || "—"}
                    </span>
                  </div>
                  {selectedExp.roc_curve && selectedExp.roc_curve.fpr.length > 0 ? (
                    <div className="h-44 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={selectedExp.roc_curve.fpr.map((f: number, i: number) => ({
                            fpr: f,
                            tpr: selectedExp.roc_curve!.tpr[i],
                          }))}
                          margin={{ top: 5, right: 10, left: -20, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                          <XAxis dataKey="fpr" stroke="#94a3b8" fontSize={10} domain={[0, 1]} />
                          <YAxis stroke="#94a3b8" fontSize={10} domain={[0, 1]} />
                          <Tooltip contentStyle={{ backgroundColor: "#0f172a", fontSize: "10px" }} />
                          <Line type="monotone" dataKey="tpr" stroke="#60a5fa" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-44 flex items-center justify-center text-xs text-text-tertiary">
                      Curve points not available for this run.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <p className="text-[11px] font-sans text-text-tertiary leading-relaxed">
            Live evaluation runs exclusively in user space against uploaded dataset{" "}
            <span className="font-mono">{datasetId}</span>. Locked official research artifacts
            are never accessed or modified by custom evaluations.
          </p>
        </>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN UNIFIED EVALUATION SCREEN ROUTER
// ─────────────────────────────────────────────────────────────────────────────
export const EvaluationScreen: React.FC = () => {
  const {
    isOfficialResearch,
    datasetId,
    setDatasetId,
    researchTier,
    datasetHistory,
  } = useApp();

  const handleSwitchToOfficial = () => {
    const tierId = RESEARCH_TIER_IDS[researchTier] || RESEARCH_TIER_IDS.large_real;
    setDatasetId(tierId);
  };

  const handleSwitchToCustom = () => {
    // If current is official research, switch to the most recent custom dataset if available
    const custom = datasetHistory.find((d) => !isOfficialResearchDataset(d.id));
    if (custom) {
      setDatasetId(custom.id);
    } else {
      // If no custom dataset uploaded yet, set a custom session placeholder
      setDatasetId("custom-session");
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Evaluation Mode Switcher Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-3 bg-surface border border-hairline rounded-lg">
        <div className="flex items-center gap-2">
          <span className="text-xs font-sans text-text-tertiary font-medium mr-1">
            Evaluation Mode:
          </span>

          <div className="flex items-center bg-surface-raised p-1 rounded border border-hairline">
            <button
              type="button"
              onClick={handleSwitchToOfficial}
              className={`px-3.5 py-1.5 rounded text-xs font-sans font-medium transition-all flex items-center gap-2 ${
                isOfficialResearch
                  ? "bg-accent-primary text-white shadow-sm"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface"
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isOfficialResearch ? "bg-white" : "bg-blue-400"}`} />
              <span>Official Research Results</span>
              <span
                className={`px-1.5 py-0.2 rounded text-[10px] font-mono uppercase tracking-wider ${
                  isOfficialResearch ? "bg-white/20 text-white" : "bg-blue-500/10 text-blue-400"
                }`}
              >
                Locked
              </span>
            </button>

            <button
              type="button"
              onClick={handleSwitchToCustom}
              className={`px-3.5 py-1.5 rounded text-xs font-sans font-medium transition-all flex items-center gap-2 ${
                !isOfficialResearch
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface"
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${!isOfficialResearch ? "bg-white" : "bg-emerald-400"}`} />
              <span>Custom Evaluation</span>
              <span
                className={`px-1.5 py-0.2 rounded text-[10px] font-mono uppercase tracking-wider ${
                  !isOfficialResearch ? "bg-white/20 text-white" : "bg-emerald-500/10 text-emerald-400"
                }`}
              >
                Live
              </span>
            </button>
          </div>
        </div>

        <div className="text-xs font-mono text-text-tertiary flex items-center gap-2">
          {isOfficialResearch ? (
            <span>Benchmark: {researchTier === "medium_real" ? "5,000" : "49,992"} accounts (Frozen)</span>
          ) : (
            <span>Dataset: {truncateId(datasetId, 8, 6)}</span>
          )}
        </div>
      </div>

      {isOfficialResearch ? <OfficialResearchView /> : <CustomEvaluationView />}
    </div>
  );
};
