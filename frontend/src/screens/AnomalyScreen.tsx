import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Checkbox } from "../components/ui/Checkbox";
import { Card } from "../components/ui/Card";
import { Table, Column } from "../components/ui/Table";
import { Badge } from "../components/ui/Badge";
import { ModelMetadata, UserAnomalyResult } from "../types/api";

export const AnomalyScreen: React.FC = () => {
  const {
    datasetId,
    experimentLabel,
    setExperimentLabel,
    splitLabel,
    setAnomalyResults,
    setActiveNav,
    setSelectedNodeId,
  } = useApp();

  // Training form state
  const [formExpLabel, setFormExpLabel] = useState(experimentLabel || "default");
  const [formSplitLabel, setFormSplitLabel] = useState(splitLabel || "");
  const [includeGraph, setIncludeGraph] = useState(true);
  const [includeBehavioral, setIncludeBehavioral] = useState(true);
  const [includeTemporal, setIncludeTemporal] = useState(true);

  // Advanced hyperparameters
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [nEstimators, setNEstimators] = useState(100);
  const [contamination, setContamination] = useState(0.1);
  const [maxSamples, setMaxSamples] = useState("auto");
  const [randomState, setRandomState] = useState(42);

  // Execution and results state
  const [isTraining, setIsTraining] = useState(false);
  const [trainMessage, setTrainMessage] = useState<string | null>(null);
  const [trainError, setTrainError] = useState<string | null>(null);

  const [experiments, setExperiments] = useState<ModelMetadata[]>([]);
  const [userAnomalies, setUserAnomalies] = useState<UserAnomalyResult[]>([]);
  const [suspiciousOnly, setSuspiciousOnly] = useState(false);
  const [isLoadingResults, setIsLoadingResults] = useState(false);

  // Server-side pagination state
  const [page, setPage] = useState<number>(0);
  const pageSize = 50;
  const [totalCount, setTotalCount] = useState<number>(0);

  // Fetch trained experiments for current dataset
  const loadExperiments = async () => {
    if (!datasetId) return;
    try {
      const resp = await api.listExperiments(datasetId);
      setExperiments(resp.experiments || []);
    } catch (err: any) {
      console.warn("Could not list experiments:", err);
    }
  };

  // Fetch user anomaly predictions for current experiment with server-side pagination
  const loadUserAnomalies = async (exp: string, suspOnly = suspiciousOnly, pageNum = page) => {
    if (!datasetId) return;
    setIsLoadingResults(true);
    try {
      const resp = await api.getUserAnomalies(datasetId, {
        experimentLabel: exp,
        limit: pageSize,
        offset: pageNum * pageSize,
        suspiciousOnly: suspOnly,
        splitLabel: splitLabel || undefined,
      });
      setUserAnomalies(resp.users || []);
      setTotalCount(suspOnly ? (resp.suspicious_count || 0) : (resp.total_users || 0));

      // Also cache to AppContext to update graph hero node colors
      const map: Record<string, UserAnomalyResult> = {};
      (resp.users || []).forEach((u) => {
        map[u.user_id] = u;
      });
      setAnomalyResults(map);
    } catch (err: any) {
      console.warn("Could not fetch user anomalies:", err);
    } finally {
      setIsLoadingResults(false);
    }
  };

  useEffect(() => {
    if (datasetId) {
      loadExperiments();
      loadUserAnomalies(experimentLabel, suspiciousOnly, page);
    }
  }, [datasetId, experimentLabel, suspiciousOnly, page]);

  const handleTrainModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetId) return;

    setIsTraining(true);
    setTrainError(null);
    setTrainMessage(null);

    const featureGroups: string[] = [];
    if (includeGraph) featureGroups.push("graph");
    if (includeBehavioral) featureGroups.push("behavioral");
    if (includeTemporal) featureGroups.push("temporal");

    if (featureGroups.length === 0) {
      setTrainError("Select at least one feature group to train.");
      setIsTraining(false);
      return;
    }

    try {
      const payload = {
        experiment_label: formExpLabel.trim() || "default",
        feature_groups: featureGroups,
        n_estimators: nEstimators,
        contamination: contamination,
        max_samples: maxSamples === "auto" ? "auto" : parseFloat(maxSamples) || 100,
        random_state: randomState,
        split_label: formSplitLabel.trim() || null,
      };

      const resp = await api.trainAnomalyModel(
        datasetId,
        payload,
        payload.experiment_label,
        payload.split_label || undefined
      );

      setTrainMessage(`Model trained · ${resp.model_metadata.entity_count} entities scored`);
      setTimeout(() => setTrainMessage(null), 4000);
      setExperimentLabel(payload.experiment_label);
      await loadExperiments();
      await loadUserAnomalies(payload.experiment_label, suspiciousOnly);
    } catch (err: any) {
      setTrainError(err.message || "Model training failed.");
    } finally {
      setIsTraining(false);
    }
  };

  const handleTrainBenchmarkSuite = async () => {
    if (!datasetId) return;
    setIsTraining(true);
    setTrainError(null);
    setTrainMessage("Training benchmark suite (E0–E4)...");

    const activeSplit = formSplitLabel.trim() || splitLabel || "default";

    try {
      // 1. E0: statistical baseline with graph features only
      await api.trainBaseline(datasetId, {
        experiment_label: "E0_graph_baseline",
        z_threshold: 2.0,
        feature_groups: ["graph"],
        split_label: activeSplit,
      });

      // 2. E1: Graph + Isolation Forest
      await api.trainAnomalyModel(datasetId, {
        experiment_label: "E1_graph_ml",
        feature_groups: ["graph"],
        random_state: 42,
        split_label: activeSplit,
      });

      // 3. E2: Graph + Behavioral + Isolation Forest
      await api.trainAnomalyModel(datasetId, {
        experiment_label: "E2_graph_behavioral_ml",
        feature_groups: ["graph", "behavioral"],
        random_state: 42,
        split_label: activeSplit,
      });

      // 4. E3: Graph + Temporal + Isolation Forest
      await api.trainAnomalyModel(datasetId, {
        experiment_label: "E3_graph_temporal_ml",
        feature_groups: ["graph", "temporal"],
        random_state: 42,
        split_label: activeSplit,
      });

      // 5. E4: Full GraphFin
      await api.trainAnomalyModel(datasetId, {
        experiment_label: "E4_full_graphfin",
        feature_groups: ["graph", "behavioral", "temporal"],
        random_state: 42,
        split_label: activeSplit,
      });

      setTrainMessage("Benchmark suite (E0–E4) trained successfully.");
      setTimeout(() => setTrainMessage(null), 4000);
      setExperimentLabel("E4_full_graphfin");
      await loadExperiments();
      await loadUserAnomalies("E4_full_graphfin", suspiciousOnly);
    } catch (err: any) {
      setTrainError(err.message || "Failed to train benchmark suite.");
    } finally {
      setIsTraining(false);
    }
  };

  const handleTrainBaseline = async () => {
    if (!datasetId) return;
    setIsTraining(true);
    setTrainError(null);
    setTrainMessage(null);

    try {
      const resp = await api.trainBaseline(datasetId, {
        experiment_label: "baseline_statistical",
        z_threshold: 2.0,
        features: ["weighted_out_degree", "betweenness_centrality", "total_degree"],
        split_label: formSplitLabel.trim() || null,
      });

      setTrainMessage(`Statistical baseline fitted · ${resp.model_metadata.entity_count} entities scored`);
      setTimeout(() => setTrainMessage(null), 4000);
      setExperimentLabel("baseline_statistical");
      await loadExperiments();
      await loadUserAnomalies("baseline_statistical", suspiciousOnly);
    } catch (err: any) {
      setTrainError(err.message || "Failed to fit statistical baseline.");
    } finally {
      setIsTraining(false);
    }
  };

  const handleSelectExperiment = (exp: string) => {
    setExperimentLabel(exp);
    setFormExpLabel(exp);
    setPage(0);
    loadUserAnomalies(exp, suspiciousOnly, 0);
  };

  if (!datasetId) {
    return (
      <div className="h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-center space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-sans font-medium text-text-primary">
            No dataset selected
          </h2>
          <p className="text-sm font-sans text-text-secondary max-w-sm">
            Select or upload a dataset before training anomaly models or calculating baselines.
          </p>
        </div>
        <Button variant="primary" onClick={() => setActiveNav("datasets")}>
          Select or upload dataset
        </Button>
      </div>
    );
  }

  const resultColumns: Column<UserAnomalyResult>[] = [
    {
      key: "user_id",
      header: "Entity ID",
      mono: true,
      render: (row) => (
        <button
          onClick={() => {
            setSelectedNodeId(row.user_id);
            setActiveNav("graph");
          }}
          className="font-mono text-text-primary hover:text-accent-primary hover:underline text-left"
          title="Inspect node in graph"
        >
          {row.user_id}
        </button>
      ),
    },
    {
      key: "status",
      header: "Classification",
      render: (row) => (
        <Badge
          variant={
            row.status === "suspicious"
              ? "suspicious"
              : row.status === "normal"
              ? "normal"
              : "neutral"
          }
        >
          {row.status}
        </Badge>
      ),
    },
    {
      key: "risk_score",
      header: "Presentation risk score (0-100)",
      render: (row) => (
        <div className="flex items-center gap-3 w-48">
          <div className="flex-1 bg-surface h-1.5 rounded overflow-hidden">
            <div
              className={`h-full ${
                row.status === "suspicious"
                  ? "bg-status-suspicious"
                  : "bg-status-normal"
              }`}
              style={{ width: `${Math.min(100, Math.max(0, row.risk_score))}%` }}
            />
          </div>
          <span className="font-mono text-xs text-text-primary w-10 text-right">
            {row.risk_score.toFixed(1)}
          </span>
        </div>
      ),
    },
    {
      key: "raw_score",
      header: "Raw score",
      align: "right",
      mono: true,
      render: (row) => row.raw_score.toFixed(5),
    },
    {
      key: "reasons",
      header: "Explainability reasons",
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          {row.reasons && row.reasons.length > 0 ? (
            row.reasons.map((r, i) => (
              <span
                key={i}
                className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-surface border border-hairline text-text-secondary"
              >
                {r}
              </span>
            ))
          ) : (
            <span className="text-text-tertiary text-xs font-mono">—</span>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8 max-w-[960px] mx-auto text-left">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-sans font-medium text-text-primary">
          Anomaly Models
        </h1>
        <p className="text-sm font-sans text-text-secondary mt-1">
          Configure unsupervised Isolation Forest ensembles or statistical baselines on graph-fused feature vectors.
        </p>
      </div>

      {/* Train Model Form */}
      <Card variant="surface" className="space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-hairline">
          <h2 className="text-sm font-sans font-medium text-text-primary">
            Train anomaly model
          </h2>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={handleTrainBenchmarkSuite}
              disabled={isTraining}
            >
              Train Benchmark Suite (E0–E4)
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleTrainBaseline}
              disabled={isTraining}
            >
              Fit statistical baseline (z-score)
            </Button>
          </div>
        </div>

        <form onSubmit={handleTrainModel} className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Experiment label"
              value={formExpLabel}
              onChange={(e) => setFormExpLabel(e.target.value)}
              placeholder="e.g. default, exp_graph_only"
              mono
            />
            <Input
              label="Split label (optional)"
              value={formSplitLabel}
              onChange={(e) => setFormSplitLabel(e.target.value)}
              placeholder="Leave empty for full population in-sample"
              mono
            />
          </div>

          {/* Feature Groups Checkboxes */}
          <div>
            <span className="text-xs font-sans text-text-secondary block mb-2">
              Feature groups
            </span>
            <div className="grid grid-cols-3 gap-3">
              <Checkbox
                label="Graph topology"
                description="In/out degree, weighted volume, betweenness"
                checked={includeGraph}
                onChange={(e) => setIncludeGraph(e.target.checked)}
              />
              <Checkbox
                label="Behavioral flow"
                description="Transaction counts, amounts, net flow"
                checked={includeBehavioral}
                onChange={(e) => setIncludeBehavioral(e.target.checked)}
              />
              <Checkbox
                label="Temporal intervals"
                description="Tx frequency per day/week, inter-tx time"
                checked={includeTemporal}
                onChange={(e) => setIncludeTemporal(e.target.checked)}
              />
            </div>
          </div>

          {/* Advanced Collapsible Section */}
          <div className="border-t border-hairline pt-3">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs font-sans text-accent-primary hover:underline flex items-center gap-1"
            >
              <span>{showAdvanced ? "Hide hyperparameters" : "Show advanced hyperparameters"}</span>
              <span className="font-mono text-[10px]">{showAdvanced ? "▲" : "▼"}</span>
            </button>

            {showAdvanced && (
              <div className="grid grid-cols-4 gap-4 mt-3 pt-3 border-t border-hairline/50">
                <Input
                  label="n_estimators"
                  type="number"
                  min={10}
                  max={1000}
                  value={nEstimators}
                  onChange={(e) => setNEstimators(parseInt(e.target.value) || 100)}
                  mono
                />
                <Input
                  label="contamination"
                  type="number"
                  step="0.01"
                  min={0.01}
                  max={0.5}
                  value={contamination}
                  onChange={(e) => setContamination(parseFloat(e.target.value) || 0.1)}
                  mono
                />
                <Input
                  label="max_samples"
                  value={maxSamples}
                  onChange={(e) => setMaxSamples(e.target.value)}
                  mono
                />
                <Input
                  label="random_state"
                  type="number"
                  value={randomState}
                  onChange={(e) => setRandomState(parseInt(e.target.value) || 42)}
                  mono
                />
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-hairline">
            <span className="text-xs font-sans text-text-tertiary">
              Model trains on user feature matrix with {includeGraph ? 6 : 0} + {includeBehavioral ? 8 : 0} + {includeTemporal ? 5 : 0} features
            </span>
            <div className="flex items-center gap-3">
              {trainMessage && (
                <span className="text-xs font-sans text-status-normal transition-opacity duration-150">
                  {trainMessage}
                </span>
              )}
              <Button type="submit" variant="primary" isLoading={isTraining}>
                Train model
              </Button>
            </div>
          </div>
        </form>

        {trainError && (
          <div className="p-3 bg-[#2D1619] border border-[#521A1F] rounded text-xs font-sans text-status-suspicious">
            {trainError}
          </div>
        )}
      </Card>

      {/* Trained Experiments for Dataset */}
      {experiments.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-sans font-medium text-text-primary">
            Trained experiments ({experiments.length})
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {experiments.map((exp) => {
              const isSelected = exp.experiment_label === experimentLabel;
              return (
                <div
                  key={exp.experiment_label}
                  onClick={() => handleSelectExperiment(exp.experiment_label)}
                  className={`p-3 rounded border text-left cursor-pointer transition-colors ${
                    isSelected
                      ? "border-accent-primary bg-surface-raised"
                      : "border-hairline bg-surface hover:border-text-tertiary"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono font-medium text-text-primary">
                      {exp.experiment_label}
                    </span>
                    <Badge variant={isSelected ? "accent" : "neutral"}>
                      {exp.model_type}
                    </Badge>
                  </div>
                  <div className="text-[11px] font-sans text-text-secondary space-y-0.5">
                    <div>Features: {exp.feature_groups.join(", ")} ({exp.feature_count})</div>
                    <div>Entities: {exp.entity_count}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Predictions Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-sans font-medium text-text-primary">
              Prediction results for <span className="font-mono text-accent-primary">{experimentLabel}</span>
            </h2>
            <span className="text-xs font-sans text-text-tertiary">
              Showing page {page + 1} ({userAnomalies.length} of {totalCount} {suspiciousOnly ? "suspicious" : "scored"} entities)
            </span>
          </div>

          <div className="flex items-center gap-4">
            <Checkbox
              label="Suspicious entities only"
              checked={suspiciousOnly}
              onChange={(e) => {
                setSuspiciousOnly(e.target.checked);
                setPage(0);
              }}
            />
            <Button
              size="sm"
              variant="ghost"
              onClick={() => loadUserAnomalies(experimentLabel, suspiciousOnly, page)}
            >
              Refresh
            </Button>
          </div>
        </div>

        <Table
          columns={resultColumns}
          data={userAnomalies}
          isLoading={isLoadingResults}
          stickyFirstColumn={true}
          emptyMessage="No predictions found for this experiment. Train a model to see scores."
        />

        {/* Server-Side Pagination Bar */}
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs font-mono text-text-tertiary">
            Showing {totalCount === 0 ? 0 : page * pageSize + 1}–
            {Math.min((page + 1) * pageSize, totalCount)} of {totalCount} {suspiciousOnly ? "suspicious" : "scored"} entities
          </span>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              disabled={page === 0 || isLoadingResults}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Previous
            </Button>
            <span className="text-xs font-mono text-text-secondary px-2">
              Page {page + 1} of {Math.ceil(totalCount / pageSize) || 1}
            </span>
            <Button
              size="sm"
              variant="ghost"
              disabled={(page + 1) * pageSize >= totalCount || isLoadingResults}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
