import React, { useEffect, useState, useRef } from "react";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Checkbox } from "../components/ui/Checkbox";
import { Card } from "../components/ui/Card";
import { Table, Column } from "../components/ui/Table";
import { DatasetLabelsSummaryResponse, SplitSummaryResponse } from "../types/api";
import { formatPercent } from "../utils/formatters";

export const LabelsSplitScreen: React.FC = () => {
  const { datasetId, splitLabel, setSplitLabel, setActiveNav } = useApp();

  // Label upload state
  const [userIdCol, setUserIdCol] = useState("user_id");
  const [labelCol, setLabelCol] = useState("label");
  const [strictLabels, setStrictLabels] = useState(false);
  const [isUploadingLabels, setIsUploadingLabels] = useState(false);
  const [labelsSummary, setLabelsSummary] = useState<DatasetLabelsSummaryResponse | null>(null);
  const [labelError, setLabelError] = useState<string | null>(null);
  const [labelConfirmation, setLabelConfirmation] = useState<string | null>(null);
  const labelFileRef = useRef<HTMLInputElement>(null);

  // Split state
  const [splitLabelInput, setSplitLabelInput] = useState(splitLabel || "default");
  const [testSize, setTestSize] = useState(0.3);
  const [randomState, setRandomState] = useState(42);
  const [stratify, setStratify] = useState(true);
  const [isCreatingSplit, setIsCreatingSplit] = useState(false);
  const [splitResult, setSplitResult] = useState<SplitSummaryResponse | null>(null);
  const [splitError, setSplitError] = useState<string | null>(null);
  const [splitConfirmation, setSplitConfirmation] = useState<string | null>(null);
  const [splitsList, setSplitsList] = useState<SplitSummaryResponse[]>([]);

  // Load existing labels summary and splits
  const loadData = async () => {
    if (!datasetId) return;

    try {
      const summary = await api.getLabelsSummary(datasetId);
      setLabelsSummary(summary);
    } catch {
      // Labels not uploaded yet, quiet fallback
      setLabelsSummary(null);
    }

    try {
      const splits = await api.listSplits(datasetId);
      setSplitsList(splits);
      if (splits.length > 0 && !splitResult) {
        setSplitResult(splits[0]);
      }
    } catch {
      setSplitsList([]);
    }
  };

  useEffect(() => {
    if (datasetId) {
      loadData();
    }
  }, [datasetId]);

  const handleUploadLabelsFile = async (file: File) => {
    if (!datasetId) return;
    setIsUploadingLabels(true);
    setLabelError(null);
    setLabelConfirmation(null);

    try {
      const resp = await api.uploadLabels(datasetId, file, {
        userIdCol: userIdCol.trim() || "user_id",
        labelCol: labelCol.trim() || "label",
        strict: strictLabels,
      });
      setLabelsSummary(resp);
      setLabelConfirmation(
        `Labels uploaded · ${resp.matched_count} entities matched (${resp.positive_count} positive)`
      );
      setTimeout(() => setLabelConfirmation(null), 4000);
    } catch (err: any) {
      setLabelError(err.message || "Failed to upload ground-truth labels.");
    } finally {
      setIsUploadingLabels(false);
    }
  };

  const handleCreateSplit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetId) return;

    setIsCreatingSplit(true);
    setSplitError(null);
    setSplitConfirmation(null);

    try {
      const resp = await api.createSplit(datasetId, {
        split_label: splitLabelInput.trim() || "default",
        test_size: testSize,
        random_state: randomState,
        stratify_by_label: stratify,
      });

      setSplitResult(resp);
      setSplitLabel(resp.split_label);
      setSplitConfirmation(
        `Split created · ${resp.train_count} train / ${resp.test_count} test (${(resp.test_size * 100).toFixed(0)}% test)`
      );
      setTimeout(() => setSplitConfirmation(null), 4000);
      await loadData();
    } catch (err: any) {
      setSplitError(err.message || "Failed to create dataset split.");
    } finally {
      setIsCreatingSplit(false);
    }
  };

  if (!datasetId) {
    return (
      <div className="h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-center space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-sans font-medium text-text-primary">
            No dataset selected
          </h2>
          <p className="text-sm font-sans text-text-secondary max-w-sm">
            Select or upload a dataset before managing ground-truth labels and train/test splits.
          </p>
        </div>
        <Button variant="primary" onClick={() => setActiveNav("datasets")}>
          Upload a dataset to begin
        </Button>
      </div>
    );
  }

  const isSplitGated = !labelsSummary || labelsSummary.matched_count === 0;

  const splitColumns: Column<SplitSummaryResponse>[] = [
    {
      key: "split_label",
      header: "Split label",
      mono: true,
      render: (row) => (
        <span className="font-mono text-text-primary">{row.split_label}</span>
      ),
    },
    {
      key: "train_count",
      header: "Train entities",
      align: "right",
      mono: true,
      render: (row) => `${row.train_count} (${formatPercent(row.train_prevalence)} prev)`,
    },
    {
      key: "test_count",
      header: "Test entities",
      align: "right",
      mono: true,
      render: (row) => `${row.test_count} (${formatPercent(row.test_prevalence)} prev)`,
    },
    {
      key: "stratified",
      header: "Stratified",
      align: "center",
      render: (row) => (row.stratified ? "Yes" : "No"),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (row) => (
        <Button
          size="sm"
          variant={row.split_label === splitLabel ? "secondary" : "ghost"}
          onClick={() => {
            setSplitLabel(row.split_label);
            setSplitResult(row);
          }}
        >
          {row.split_label === splitLabel ? "Active" : "Select"}
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-8 max-w-[960px] mx-auto text-left">
      {/* Header */}
      <div>
        <h1 className="text-xl font-sans font-medium text-text-primary">
          Labels & Splits
        </h1>
        <p className="text-sm font-sans text-text-secondary mt-1">
          Ingest entity ground-truth labels and partition data into deterministic train/test splits for held-out evaluation.
        </p>
      </div>

      {/* Upload Labels Section */}
      <Card variant="surface" className="space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-hairline">
          <h2 className="text-sm font-sans font-medium text-text-primary">
            Upload ground-truth labels CSV
          </h2>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="User ID column name"
            value={userIdCol}
            onChange={(e) => setUserIdCol(e.target.value)}
            placeholder="user_id"
            mono
          />
          <Input
            label="Label column name"
            value={labelCol}
            onChange={(e) => setLabelCol(e.target.value)}
            placeholder="label"
            mono
          />
        </div>

        <div className="flex items-center justify-between pt-2">
          <Checkbox
            label="Strict validation"
            description="Abort if any user ID in labels CSV does not exist in dataset feature matrix"
            checked={strictLabels}
            onChange={(e) => setStrictLabels(e.target.checked)}
          />

          <input
            ref={labelFileRef}
            type="file"
            accept=".csv,.txt"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleUploadLabelsFile(e.target.files[0]);
              }
            }}
          />

          <div className="flex items-center gap-3">
            {labelConfirmation && (
              <span className="text-xs font-sans text-status-normal transition-opacity duration-150">
                {labelConfirmation}
              </span>
            )}
            <Button
              variant="primary"
              onClick={() => labelFileRef.current?.click()}
              isLoading={isUploadingLabels}
            >
              Upload labels
            </Button>
          </div>
        </div>

        {labelError && (
          <div className="p-3 bg-[#2D1619] border border-[#521A1F] rounded text-xs font-sans text-status-suspicious">
            {labelError}
          </div>
        )}
      </Card>

      {/* Stored Labels Summary */}
      {labelsSummary && (
        <Card variant="surface-raised" className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-sans text-text-tertiary">
              Stored ground-truth labels
            </span>
            <span className="text-xs font-mono text-status-normal">
              {labelsSummary.matched_count} matched entities
            </span>
          </div>

          <div className="grid grid-cols-4 gap-4 text-xs font-sans py-1">
            <div className="border border-hairline p-3 bg-surface rounded">
              <span className="text-text-tertiary block">Total uploaded</span>
              <span className="text-lg font-mono text-text-primary">
                {labelsSummary.total_labels_uploaded}
              </span>
            </div>
            <div className="border border-hairline p-3 bg-surface rounded">
              <span className="text-text-tertiary block">Positive labels</span>
              <span className="text-lg font-mono text-status-suspicious">
                {labelsSummary.positive_count}
              </span>
            </div>
            <div className="border border-hairline p-3 bg-surface rounded">
              <span className="text-text-tertiary block">Normal negatives</span>
              <span className="text-lg font-mono text-status-normal">
                {labelsSummary.negative_count}
              </span>
            </div>
            <div className="border border-hairline p-3 bg-surface rounded">
              <span className="text-text-tertiary block">Prevalence rate</span>
              <span className="text-lg font-mono text-text-primary">
                {formatPercent(labelsSummary.prevalence_rate)}
              </span>
            </div>
          </div>

          {labelsSummary.rejected_errors && labelsSummary.rejected_errors.length > 0 && (
            <div className="space-y-1 pt-2">
              <span className="text-xs font-sans text-status-warning block">
                Unmatched label rows ({labelsSummary.unmatched_count}):
              </span>
              <div className="bg-canvas border border-[#4F3F12] p-2.5 rounded text-xs font-mono text-status-warning max-h-24 overflow-y-auto">
                {labelsSummary.rejected_errors.map((e, idx) => (
                  <div key={idx}>{e}</div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Create Train/Test Split Section (GATED if no labels) */}
      <Card
        variant="surface"
        className={`space-y-4 transition-opacity duration-150 ${
          isSplitGated ? "opacity-50" : "opacity-100"
        }`}
      >
        {isSplitGated && (
          <div className="text-xs font-sans text-status-warning pb-1">
            Upload labels above to enable splitting.
          </div>
        )}

        <div className="pb-3 border-b border-hairline">
          <h2 className="text-sm font-sans font-medium text-text-primary">
            Create entity-level train/test split
          </h2>
          <p className="text-xs font-sans text-text-secondary mt-0.5">
            Requires ground-truth labels. Stratifies by label to preserve rare class balance across train and test partitions.
          </p>
        </div>

        <form onSubmit={handleCreateSplit} className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <Input
              label="Split label"
              value={splitLabelInput}
              onChange={(e) => setSplitLabelInput(e.target.value)}
              placeholder="e.g. default, split_80_20"
              disabled={isSplitGated}
              mono
            />
            <Input
              label="Test size fraction (0.1 - 0.9)"
              type="number"
              step="0.05"
              min="0.05"
              max="0.95"
              value={testSize}
              onChange={(e) => setTestSize(parseFloat(e.target.value) || 0.3)}
              disabled={isSplitGated}
              mono
            />
            <Input
              label="Random state seed"
              type="number"
              value={randomState}
              onChange={(e) => setRandomState(parseInt(e.target.value) || 42)}
              disabled={isSplitGated}
              mono
            />
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-hairline">
            <Checkbox
              label="Stratify by ground-truth label"
              description="Preserve exact positive prevalence in train and test partitions"
              checked={stratify}
              onChange={(e) => setStratify(e.target.checked)}
              disabled={isSplitGated}
            />

            <div className="flex items-center gap-3">
              {splitConfirmation && (
                <span className="text-xs font-sans text-status-normal transition-opacity duration-150">
                  {splitConfirmation}
                </span>
              )}
              <Button
                type="submit"
                variant="primary"
                isLoading={isCreatingSplit}
                disabled={isSplitGated}
              >
                Create split
              </Button>
            </div>
          </div>
        </form>

        {splitError && (
          <div className="p-3 bg-[#2D1619] border border-[#521A1F] rounded text-xs font-sans text-status-suspicious">
            {splitError}
          </div>
        )}
      </Card>

      {/* Split Result Details */}
      {splitResult && (
        <Card variant="surface-raised" className="space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-hairline">
            <span className="text-xs font-sans text-text-tertiary">
              Active split assignment
            </span>
            <span className="text-xs font-mono text-accent-primary">
              {splitResult.split_label}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs font-sans">
            {/* Training partition */}
            <div className="border border-hairline p-3 bg-surface rounded space-y-1">
              <span className="text-text-tertiary block font-medium">
                Training partition (Fit population)
              </span>
              <div className="text-base font-mono text-text-primary">
                {splitResult.train_count} entities
              </div>
              <div className="text-text-secondary text-[11px]">
                {splitResult.train_positive_count} positive / {splitResult.train_negative_count} normal (
                <span className="font-mono">{formatPercent(splitResult.train_prevalence)}</span> prevalence)
              </div>
            </div>

            {/* Test partition */}
            <div className="border border-hairline p-3 bg-surface rounded space-y-1">
              <span className="text-text-tertiary block font-medium">
                Held-out test partition (Evaluation target)
              </span>
              <div className="text-base font-mono text-text-primary">
                {splitResult.test_count} entities
              </div>
              <div className="text-text-secondary text-[11px]">
                {splitResult.test_positive_count} positive / {splitResult.test_negative_count} normal (
                <span className="font-mono">{formatPercent(splitResult.test_prevalence)}</span> prevalence)
              </div>
            </div>
          </div>

          {splitResult.warning && (
            <div className="p-2.5 bg-[#2B230B] border border-[#4F3F12] rounded text-xs font-sans text-status-warning">
              {splitResult.warning}
            </div>
          )}
        </Card>
      )}

      {/* List of Configured Splits */}
      {splitsList.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-sans font-medium text-text-primary">
            Configured partitions ({splitsList.length})
          </h2>
          <Table
            columns={splitColumns}
            data={splitsList}
            emptyMessage="No splits configured yet."
          />
        </div>
      )}
    </div>
  );
};
