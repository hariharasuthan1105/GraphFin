import React, { useState, useRef, useEffect } from "react";
import { api } from "../api/client";
import {
  useApp,
} from "../context/AppContext";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Checkbox } from "../components/ui/Checkbox";
import { Select } from "../components/ui/Select";
import { Card } from "../components/ui/Card";
import { Table, Column } from "../components/ui/Table";
import { parseTransactionCsv } from "../utils/csvParser";
import { TransactionUploadResponse } from "../types/api";
import { truncateId } from "../utils/formatters";

export const DatasetsScreen: React.FC = () => {
  const {
    datasetId,
    setDatasetId,
    researchTier,
    setResearchTier,
    datasetHistory,
    addDatasetToHistory,
    setCachedEdges,
    setActiveNav,
    setDatasetCurrency,
  } = useApp();

  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadConfirmation, setUploadConfirmation] = useState<string | null>(null);
  const [strictMode, setStrictMode] = useState(false);
  const [uploadReport, setUploadReport] = useState<TransactionUploadResponse | null>(null);
  const [manualIdInput, setManualIdInput] = useState("");
  const [selectedCurrency, setSelectedCurrency] = useState("USD");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Locked datasets: fetched dynamically from backend so we can show an honest
  // empty state on fresh checkouts where the research CSVs haven't been loaded.
  const [lockedDatasets, setLockedDatasets] = useState<Array<{
    dataset_id: string;
    tier: string;
    label: string;
    transactions: number;
    users: number;
    currency: string;
  }> | null>(null); // null = still loading, [] = empty (no datasets available)
  const [lockedDatasetsError, setLockedDatasetsError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getLockedDatasets()
      .then((data) => setLockedDatasets(data))
      .catch(() => {
        setLockedDatasets([]);
        setLockedDatasetsError("Could not reach backend to check research dataset availability.");
      });
  }, []);

  const handleFileUpload = async (file: File, currencyOverride?: string) => {
    setIsUploading(true);
    setUploadError(null);
    setUploadConfirmation(null);
    setUploadReport(null);

    const currency = currencyOverride ?? selectedCurrency;

    try {
      // Also parse client-side to retain transaction edges for the graph hero
      const text = await file.text();
      const parsed = parseTransactionCsv(text);
      setCachedEdges(parsed.edges);

      const resp = await api.uploadTransactions(file, strictMode, currency);
      setUploadReport(resp);
      setDatasetId(resp.dataset_id);
      // Immediately update currency context — don't wait for the summary re-fetch
      setDatasetCurrency(resp.currency ?? currency);
      addDatasetToHistory({
        id: resp.dataset_id,
        name: file.name,
        timestamp: new Date().toISOString(),
        transactions: resp.valid_transactions,
        users: resp.summary.users,
      });

      setUploadConfirmation(
        `Dataset uploaded · ${resp.valid_transactions} valid transactions (${resp.summary.users} entities) · ${resp.currency ?? currency}`
      );
      setTimeout(() => setUploadConfirmation(null), 4000);
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload transactions CSV.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleSelectHistoryDataset = (id: string) => {
    setDatasetId(id);
    setActiveNav("graph");
  };

  const handleManualIdSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = manualIdInput.trim();
    if (clean) {
      setDatasetId(clean);
      addDatasetToHistory({
        id: clean,
        name: `Manual (${truncateId(clean, 6, 4)})`,
        timestamp: new Date().toISOString(),
      });
      setManualIdInput("");
      setActiveNav("graph");
    }
  };

  const historyColumns: Column<any>[] = [
    {
      key: "id",
      header: "Dataset ID",
      mono: true,
      render: (row) => (
        <span className="font-mono text-text-primary">
          {truncateId(row.id, 10, 6)}
        </span>
      ),
    },
    {
      key: "name",
      header: "Name / Source",
      render: (row) => <span className="text-text-secondary">{row.name}</span>,
    },
    {
      key: "transactions",
      header: "Transactions",
      align: "right",
      mono: true,
      render: (row) => row.transactions ?? "—",
    },
    {
      key: "users",
      header: "Entities",
      align: "right",
      mono: true,
      render: (row) => row.users ?? "—",
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (row) => (
        <Button
          size="sm"
          variant={row.id === datasetId ? "secondary" : "ghost"}
          onClick={() => handleSelectHistoryDataset(row.id)}
        >
          {row.id === datasetId ? "Active" : "Load"}
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-8 max-w-[960px] mx-auto text-left">
      {/* Header section */}
      <div>
        <h1 className="text-xl font-sans font-medium text-text-primary">
          Datasets
        </h1>
        <p className="text-sm font-sans text-text-secondary mt-1">
          Upload and manage transaction datasets for topological graph analysis and anomaly modeling.
        </p>
      </div>

      {/* Upload Zone */}
      <Card variant="surface" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-sans font-medium text-text-primary">
            Upload transaction CSV
          </h2>
        </div>

        {/* Currency selector */}
        <div className="flex items-center gap-4 py-2 border-b border-hairline">
          <label className="text-xs font-sans text-text-secondary font-medium whitespace-nowrap">
            Dataset currency
          </label>
          <Select
            value={selectedCurrency}
            onChange={(e) => setSelectedCurrency(e.target.value)}
            options={[
              { value: "USD", label: "USD — US Dollar ($)" },
              { value: "INR", label: "INR — Indian Rupee (₹)" },
              { value: "EUR", label: "EUR — Euro (€)" },
              { value: "GBP", label: "GBP — British Pound (£)" },
            ]}
            className="w-56 text-xs"
          />
          <span className="text-xs font-sans text-text-tertiary">
            All amounts in this dataset are treated as{" "}
            <span className="font-mono text-text-secondary">{selectedCurrency}</span>.
            No conversion is applied — this only affects how amounts are displayed.
          </span>
        </div>

        {/* Drag and Drop Box */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
          onClick={() => fileInputRef.current?.click()}
          className="border border-dashed border-hairline hover:border-accent-primary/60 bg-canvas/40 p-8 rounded text-center cursor-pointer transition-colors"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.txt"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
              }
            }}
          />
          <div className="space-y-1">
            <p className="text-sm font-sans text-text-primary">
              Drop transactions CSV here, or click to browse
            </p>
            <p className="text-xs font-sans text-text-tertiary">
              Canonical columns: transaction_id, sender_id, receiver_id,{" "}
              <span className="font-mono">amount (numeric, in {selectedCurrency})</span>,
              timestamp
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          <Checkbox
            label="Strict mode"
            description="If checked, any single invalid row aborts the entire dataset upload"
            checked={strictMode}
            onChange={(e) => setStrictMode(e.target.checked)}
          />

          <div className="flex items-center gap-3">
            {uploadConfirmation && (
              <span className="text-xs font-sans text-status-normal transition-opacity duration-150">
                {uploadConfirmation}
              </span>
            )}
            <Button
              variant="primary"
              size="md"
              onClick={() => fileInputRef.current?.click()}
              isLoading={isUploading}
            >
              Select file
            </Button>
          </div>
        </div>

        {/* Upload error display inline */}
        {uploadError && (
          <div className="p-3 bg-[#2D1619] border border-[#521A1F] rounded text-xs font-sans text-status-suspicious">
            {uploadError}
          </div>
        )}
      </Card>

      {/* Validation Report (Exact API output) */}
      {uploadReport && (
        <Card variant="surface-raised" className="space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-hairline">
            <div>
              <span className="text-xs font-sans text-text-tertiary">Upload result</span>
              <h3 className="text-sm font-sans font-medium text-text-primary">
                Dataset created: <span className="font-mono">{uploadReport.dataset_id}</span>
              </h3>
            </div>
            <Button
              size="sm"
              variant="primary"
              onClick={() => setActiveNav("graph")}
            >
              Open graph hero
            </Button>
          </div>

          <div className="grid grid-cols-4 gap-4 text-xs font-sans py-1">
            <div className="border border-hairline p-3 bg-surface rounded">
              <span className="text-text-tertiary block">Total parsed</span>
              <span className="text-lg font-mono text-text-primary">
                {uploadReport.total_rows_parsed}
              </span>
            </div>
            <div className="border border-hairline p-3 bg-surface rounded">
              <span className="text-text-tertiary block">Valid transactions</span>
              <span className="text-lg font-mono text-status-normal">
                {uploadReport.valid_transactions}
              </span>
            </div>
            <div className="border border-hairline p-3 bg-surface rounded">
              <span className="text-text-tertiary block">Invalid rows</span>
              <span className={`text-lg font-mono ${uploadReport.invalid_rows_count > 0 ? "text-status-suspicious" : "text-text-primary"}`}>
                {uploadReport.invalid_rows_count}
              </span>
            </div>
            <div className="border border-hairline p-3 bg-surface rounded">
              <span className="text-text-tertiary block">Unique entities</span>
              <span className="text-lg font-mono text-text-primary">
                {uploadReport.summary.users}
              </span>
            </div>
          </div>

          {/* Validation errors verbatim */}
          {uploadReport.validation_errors && uploadReport.validation_errors.length > 0 && (
            <div className="space-y-1.5 pt-2">
              <span className="text-xs font-sans font-medium text-status-suspicious block">
                Validation errors from server ({uploadReport.validation_errors.length}):
              </span>
              <div className="bg-canvas border border-[#521A1F] p-3 rounded text-xs font-mono text-status-suspicious max-h-40 overflow-y-auto space-y-1">
                {uploadReport.validation_errors.map((err, idx) => (
                  <div key={idx}>{err}</div>
                ))}
              </div>
            </div>
          )}

          {/* Duplicate warnings verbatim */}
          {uploadReport.duplicate_warnings && uploadReport.duplicate_warnings.length > 0 && (
            <div className="space-y-1.5 pt-2">
              <span className="text-xs font-sans font-medium text-status-warning block">
                Duplicate warnings ({uploadReport.duplicate_warnings.length}):
              </span>
              <div className="bg-canvas border border-[#4F3F12] p-3 rounded text-xs font-mono text-status-warning max-h-32 overflow-y-auto space-y-1">
                {uploadReport.duplicate_warnings.map((warn, idx) => (
                  <div key={idx}>{warn}</div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Official Research Benchmarks (Locked) */}
      <Card variant="surface" className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-sans font-medium text-text-primary flex items-center gap-2">
              <span>Official Research Benchmarks</span>
              <span className="px-1.5 py-0.2 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-[10px] font-mono uppercase tracking-wider">
                Locked
              </span>
            </h2>
            <p className="text-xs font-sans text-text-secondary mt-0.5">
              Frozen benchmark datasets from IBM AML HI-Small used for baseline and topological research evaluation.
            </p>
          </div>
        </div>

        {/* Loading state */}
        {lockedDatasets === null && (
          <div className="py-4 text-center text-xs font-sans text-text-tertiary">
            Checking research dataset availability…
          </div>
        )}

        {/* Error reaching backend */}
        {lockedDatasetsError && (
          <div className="py-2 text-xs font-sans text-amber-400">
            {lockedDatasetsError}
          </div>
        )}

        {/* Empty state — datasets not loaded on this backend instance */}
        {lockedDatasets !== null && lockedDatasets.length === 0 && !lockedDatasetsError && (
          <div className="border border-hairline rounded p-4 text-center space-y-1">
            <p className="text-xs font-sans font-medium text-text-secondary">
              No locked research datasets currently available
            </p>
            <p className="text-[11px] font-sans text-text-tertiary">
              The IBM AML HI-Small benchmark fixtures have not been loaded on this backend instance.
              Run <span className="font-mono">backend/scripts/run_final_research_evaluation.py</span> with
              the source dataset to make them available.
            </p>
          </div>
        )}

        {/* Dynamically available locked datasets */}
        {lockedDatasets !== null && lockedDatasets.length > 0 && (
          <div className="divide-y divide-hairline border border-hairline rounded overflow-hidden">
            {lockedDatasets.map((ds) => (
              <div key={ds.dataset_id} className="p-3 bg-surface-raised/40 flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-400" />
                    <span className="text-xs font-sans font-medium text-text-primary">
                      {ds.label}
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-text-tertiary">
                    ID: {ds.dataset_id} · {ds.transactions.toLocaleString()} txs · {ds.users.toLocaleString()} entities · {ds.currency}
                  </div>
                </div>
                <Button
                  size="sm"
                  variant={datasetId === ds.dataset_id ? "secondary" : "ghost"}
                  onClick={() => {
                    setResearchTier(ds.tier as any);
                    setActiveNav("evaluation");
                  }}
                >
                  {datasetId === ds.dataset_id ? "Active Benchmark" : "Load Benchmark"}
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Manual Dataset ID Input */}
      <Card variant="surface" className="space-y-3">
        <h2 className="text-sm font-sans font-medium text-text-primary">
          Connect to existing dataset ID
        </h2>
        <form onSubmit={handleManualIdSubmit} className="flex items-end gap-3">
          <div className="flex-1">
            <Input
              label="Dataset UUID"
              placeholder="e.g. 1d25c967-dce7-4453-abf1-358c00e114b7"
              value={manualIdInput}
              onChange={(e) => setManualIdInput(e.target.value)}
              mono
            />
          </div>
          <Button type="submit" variant="secondary">
            Set active dataset
          </Button>
        </form>
      </Card>

      {/* Client-side Dataset History */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-sans font-medium text-text-primary">
            Dataset history
          </h2>
          <span className="text-xs font-sans text-text-tertiary">
            Cached in client storage (backend maintains in-memory registry per session)
          </span>
        </div>

        <Table
          columns={historyColumns}
          data={datasetHistory}
          emptyMessage="No datasets uploaded in this browser session. Upload a CSV to begin."
        />
      </div>
    </div>
  );
};
