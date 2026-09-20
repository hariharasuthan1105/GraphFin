/**
 * ResearchChartsSection
 *
 * Renders 4 charts from the locked final_e0_e4_comparison.json data:
 *  1. PR-AUC grouped bar — 5K vs 50K side-by-side, 5 experiment groups
 *  2. ROC-AUC grouped bar — same layout
 *  3. Precision / Recall / F1 grouped bar — per selected tier
 *  4. Single-experiment focused view with confusion matrix
 *
 * VISUAL RULES (per research spec):
 * - All experiments render with EQUAL visual weight — no winner badge, no highlight
 * - Colors are consistent per experiment across all charts (series-keyed, not rank-keyed)
 * - No gradient fills, no gaming-UI treatment
 */
import React, { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { TERMINOLOGY } from "../../constants/terminology";

export interface LockedExperiment {
  scale: string;
  dataset_id: string;
  experiment_label: string;
  seed: number;
  method: string;
  feature_groups: string[];
  feature_count: number;
  contamination: number | null;
  evaluation_mode: string;
  split_label: string;
  test_total: number;
  test_positive: number;
  test_negative: number;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
  precision: number;
  recall: number;
  f1_score: number;
  accuracy: number;
  roc_auc: number;
  pr_auc: number;
}

interface Props {
  experiments: LockedExperiment[]; // all 10 rows (both tiers)
  activeTierDatasetId: string;     // the currently selected tier's dataset_id
  selectedExpLabel: string;
  onSelectExp: (label: string) => void;
}

// Consistent per-experiment color — no ranking implied
const EXP_COLORS: Record<string, string> = {
  E0_graph_baseline:       "#60a5fa", // blue-400
  E1_graph_ml:             "#34d399", // emerald-400
  E2_graph_behavioral_ml:  "#c084fc", // purple-400
  E3_graph_temporal_ml:    "#fbbf24", // amber-400
  E4_full_graphfin:        "#94a3b8", // slate-400
};

const TIER_COLORS: Record<string, string> = {
  medium_real: "#60a5fa",  // blue-400 for 5K
  large_real:  "#c084fc",  // purple-400 for 50K
};

const EXP_SHORT_LABELS: Record<string, string> = {
  E0_graph_baseline:      "E0",
  E1_graph_ml:            "E1",
  E2_graph_behavioral_ml: "E2",
  E3_graph_temporal_ml:   "E3",
  E4_full_graphfin:       "E4",
};

const EXP_DISPLAY: Record<string, string> = {
  E0_graph_baseline:      "E0 — Graph / Statistical Baseline",
  E1_graph_ml:            "E1 — Graph + Isolation Forest",
  E2_graph_behavioral_ml: "E2 — Graph + Behavioral + IF",
  E3_graph_temporal_ml:   "E3 — Graph + Temporal + IF",
  E4_full_graphfin:       "E4 — Graph + Behavioral + Temporal + IF",
};

const ORDERED_LABELS = [
  "E0_graph_baseline",
  "E1_graph_ml",
  "E2_graph_behavioral_ml",
  "E3_graph_temporal_ml",
  "E4_full_graphfin",
];

const CHART_STYLE = {
  backgroundColor: "#1A222B",
  borderColor: "#232B33",
  borderRadius: "4px",
  fontFamily: "IBM Plex Mono, monospace",
  fontSize: "11px",
  color: "#EDEFF2",
};

const AXIS_TICK = { fill: "#8B96A3", fontSize: 11, fontFamily: "IBM Plex Mono, monospace" };
const GRID_STROKE = "#232B33";

/** Build grouped-bar data: one row per experiment, two values (5K and 50K) */
function buildGroupedData(
  experiments: LockedExperiment[],
  metricKey: keyof LockedExperiment
): { label: string; "5K": number; "50K": number }[] {
  const medium = experiments.filter((e) => e.dataset_id === "ddbaab44-78b6-41be-a8fb-e83dfec66358");
  const large  = experiments.filter((e) => e.dataset_id === "03fb9ab0-4f42-4404-9d76-723fd4d8753e");
  return ORDERED_LABELS.map((label) => {
    const m = medium.find((e) => e.experiment_label === label);
    const l = large.find((e) => e.experiment_label === label);
    return {
      label: EXP_SHORT_LABELS[label] ?? label,
      "5K":  m ? parseFloat((m[metricKey] as number).toFixed(4)) : 0,
      "50K": l ? parseFloat((l[metricKey] as number).toFixed(4)) : 0,
    };
  });
}

/** Build single-tier data for Prec/Rec/F1 chart */
function buildSingleTierData(
  experiments: LockedExperiment[],
  datasetId: string
): { label: string; Precision: number; Recall: number; F1: number }[] {
  const tier = experiments.filter((e) => e.dataset_id === datasetId);
  return ORDERED_LABELS.map((label) => {
    const e = tier.find((ex) => ex.experiment_label === label);
    return {
      label:     EXP_SHORT_LABELS[label] ?? label,
      Precision: e ? parseFloat(e.precision.toFixed(4)) : 0,
      Recall:    e ? parseFloat(e.recall.toFixed(4)) : 0,
      F1:        e ? parseFloat(e.f1_score.toFixed(4)) : 0,
    };
  });
}

// Custom tooltip that shows 4 decimal places
const MetricTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={CHART_STYLE}
      className="px-3 py-2 border text-xs space-y-1"
    >
      <div className="font-medium text-text-primary mb-1">{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: p.color }}>
          {p.name}: <span className="font-mono">{p.value.toFixed(4)}</span>
        </div>
      ))}
    </div>
  );
};

export const ResearchChartsSection: React.FC<Props> = ({
  experiments,
  activeTierDatasetId,
  selectedExpLabel,
  onSelectExp,
}) => {
  const [confView, setConfView] = useState<"selected" | "all">("selected");

  const prAucData   = buildGroupedData(experiments, "pr_auc");
  const rocAucData  = buildGroupedData(experiments, "roc_auc");
  const precRecData = buildSingleTierData(experiments, activeTierDatasetId);

  const selectedExp = experiments.find(
    (e) => e.experiment_label === selectedExpLabel && e.dataset_id === activeTierDatasetId
  );

  const tierLabel = activeTierDatasetId === "ddbaab44-78b6-41be-a8fb-e83dfec66358"
    ? "5K" : "50K";

  return (
    <div className="space-y-8">
      {/* ── Chart 1: PR-AUC grouped bar, 5K vs 50K ── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-sans font-medium text-text-primary">
            PR-AUC by Experiment
          </h3>
          <span className="text-xs font-sans text-text-tertiary">
            Primary metric — area under precision-recall curve
          </span>
        </div>
        <div className="p-4 bg-surface border border-hairline rounded">
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={prAucData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }} barGap={2} barCategoryGap="30%">
                <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} />
                <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} domain={[0, "auto"]} tickFormatter={(v) => v.toFixed(2)} />
                <Tooltip content={<MetricTooltip />} />
                <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#8B96A3" }} />
                <Bar dataKey="5K"  name="5K accounts"  fill={TIER_COLORS.medium_real} radius={[2, 2, 0, 0]} maxBarSize={28} />
                <Bar dataKey="50K" name="50K accounts" fill={TIER_COLORS.large_real}  radius={[2, 2, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Chart 2: ROC-AUC grouped bar, 5K vs 50K ── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-sans font-medium text-text-primary">
            ROC-AUC by Experiment
          </h3>
          <span className="text-xs font-sans text-text-tertiary">
            Ranking discrimination — area under ROC curve
          </span>
        </div>
        <div className="p-4 bg-surface border border-hairline rounded">
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rocAucData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }} barGap={2} barCategoryGap="30%">
                <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} />
                <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} domain={[0, 1]} tickFormatter={(v) => v.toFixed(2)} />
                <Tooltip content={<MetricTooltip />} />
                <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#8B96A3" }} />
                <Bar dataKey="5K"  name="5K accounts"  fill={TIER_COLORS.medium_real} radius={[2, 2, 0, 0]} maxBarSize={28} />
                <Bar dataKey="50K" name="50K accounts" fill={TIER_COLORS.large_real}  radius={[2, 2, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Chart 3: Precision / Recall / F1 per active tier ── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-sans font-medium text-text-primary">
            Precision / Recall / F1 — {tierLabel} tier
          </h3>
          <span className="text-xs font-sans text-text-tertiary">
            Threshold-dependent at contamination-rate decision boundary
          </span>
        </div>
        <div className="p-4 bg-surface border border-hairline rounded">
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={precRecData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }} barGap={2} barCategoryGap="28%">
                <CartesianGrid stroke={GRID_STROKE} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} />
                <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} domain={[0, "auto"]} tickFormatter={(v) => v.toFixed(2)} />
                <Tooltip content={<MetricTooltip />} />
                <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "IBM Plex Mono, monospace", color: "#8B96A3" }} />
                <Bar dataKey="Precision" fill="#60a5fa" radius={[2, 2, 0, 0]} maxBarSize={20} />
                <Bar dataKey="Recall"    fill="#34d399" radius={[2, 2, 0, 0]} maxBarSize={20} />
                <Bar dataKey="F1"        fill="#c084fc" radius={[2, 2, 0, 0]} maxBarSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Chart 4: Single-experiment confusion matrix ── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-sans font-medium text-text-primary">
            Confusion Matrix — focused experiment
          </h3>
          <span className="text-xs font-sans text-text-tertiary">
            {tierLabel} tier · click an experiment row in the table to focus
          </span>
        </div>

        {/* Experiment selector mini-bar */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {ORDERED_LABELS.map((label) => (
            <button
              key={label}
              onClick={() => onSelectExp(label)}
              className={`px-2 py-1 text-xs font-mono rounded border transition-colors ${
                label === selectedExpLabel
                  ? "border-accent-primary bg-surface-raised text-text-primary"
                  : "border-hairline text-text-tertiary hover:text-text-secondary hover:border-text-tertiary"
              }`}
            >
              {EXP_SHORT_LABELS[label]}
            </button>
          ))}
        </div>

        {selectedExp ? (
          <div className="p-4 bg-surface border border-hairline rounded">
            <div className="flex items-start gap-8 flex-wrap">
              {/* 2×2 confusion matrix */}
              <div>
                <span className="text-[11px] font-sans text-text-tertiary block mb-2">
                  {EXP_DISPLAY[selectedExp.experiment_label] ?? selectedExp.experiment_label}
                </span>
                <div className="inline-grid gap-1" style={{ gridTemplateColumns: "7rem 6rem 6rem" }}>
                  {/* Header row */}
                  <div />
                  <div className="text-center text-xs font-sans text-text-secondary pb-1 font-medium">{TERMINOLOGY.PREDICTED_POSITIVE}</div>
                  <div className="text-center text-xs font-sans text-text-secondary pb-1 font-medium">{TERMINOLOGY.PREDICTED_NEGATIVE}</div>
                  {/* Actual Positive row */}
                  <div className="text-xs font-sans text-text-secondary pr-2 flex items-center font-medium">
                    {TERMINOLOGY.ACTUAL_POSITIVE}
                  </div>
                  <div className="p-3 bg-surface-raised border border-hairline text-center rounded">
                    <span className="text-[10px] font-sans text-text-tertiary block">{TERMINOLOGY.TP}</span>
                    <span className="text-xl font-mono font-medium text-status-normal">{selectedExp.tp}</span>
                  </div>
                  <div className="p-3 bg-surface-raised border border-hairline text-center rounded">
                    <span className="text-[10px] font-sans text-text-tertiary block">{TERMINOLOGY.FN}</span>
                    <span className="text-xl font-mono font-medium text-status-suspicious">{selectedExp.fn}</span>
                  </div>
                  {/* Actual Negative row */}
                  <div className="text-xs font-sans text-text-secondary pr-2 flex items-center font-medium">
                    {TERMINOLOGY.ACTUAL_NEGATIVE}
                  </div>
                  <div className="p-3 bg-surface-raised border border-hairline text-center rounded">
                    <span className="text-[10px] font-sans text-text-tertiary block">{TERMINOLOGY.FP}</span>
                    <span className="text-xl font-mono font-medium text-status-warning">{selectedExp.fp}</span>
                  </div>
                  <div className="p-3 bg-surface-raised border border-hairline text-center rounded">
                    <span className="text-[10px] font-sans text-text-tertiary block">{TERMINOLOGY.TN}</span>
                    <span className="text-xl font-mono font-medium text-text-primary">{selectedExp.tn}</span>
                  </div>
                </div>
              </div>

              {/* Metrics sidebar */}
              <div className="space-y-2 text-xs font-sans">
                <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                  {[
                    { label: "PR-AUC",    value: selectedExp.pr_auc },
                    { label: "ROC-AUC",   value: selectedExp.roc_auc },
                    { label: "Precision", value: selectedExp.precision },
                    { label: "Recall",    value: selectedExp.recall },
                    { label: "F1 Score",  value: selectedExp.f1_score },
                    { label: "Accuracy",  value: selectedExp.accuracy },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <span className="text-text-tertiary block">{label}</span>
                      <span className="font-mono text-text-primary">{value.toFixed(4)}</span>
                    </div>
                  ))}
                </div>
                <div className="pt-2 border-t border-hairline text-[11px] text-text-tertiary space-y-0.5">
                  <div>Test set: <span className="font-mono text-text-secondary">{selectedExp.test_total.toLocaleString()} entities</span></div>
                  <div>
                    <span className="text-status-suspicious font-mono">{selectedExp.test_positive}</span> labeled positive ·{" "}
                    <span className="font-mono">{selectedExp.test_negative.toLocaleString()}</span> labeled negative
                  </div>
                  <div>Method: <span className="font-mono text-text-secondary">{selectedExp.method}</span></div>
                  <div>Features: <span className="font-mono text-text-secondary">{selectedExp.feature_groups.join(" + ")} ({selectedExp.feature_count})</span></div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 bg-surface border border-hairline rounded text-xs font-sans text-text-tertiary">
            Select an experiment above to view its confusion matrix.
          </div>
        )}
      </div>
    </div>
  );
};
