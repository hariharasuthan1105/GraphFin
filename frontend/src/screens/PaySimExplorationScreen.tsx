import React, { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";

// ─── Types ──────────────────────────────────────────────────────────────────

interface TransactionStats {
  count: number;
  total_amount: number;
  mean_amount: number;
  median_amount: number;
  min_amount: number;
  max_amount: number;
}

interface AccountStats {
  count: number;
  fraud_involved: number;
  normal: number;
}

interface NetworkStats {
  nodes: number;
  edges: number;
  density: number;
  weakly_connected_components: number;
}

interface TemporalStats {
  min_step: number | null;
  max_step: number | null;
  unique_steps: number | null;
}

interface AmountBucket {
  bucket: string;
  count: number;
}

interface StepCount {
  step: number;
  count: number;
}

interface FraudVsNormal {
  label: string;
  count: number;
}

interface TopAccount {
  account_id: string;
  transaction_count: number;
  total_amount: number;
}

interface FeatureStat {
  feature_name: string;
  group: string;
  mean: number;
  std: number;
  min: number;
  max: number;
  pct_missing: number;
}

interface ExplorationData {
  dataset_id: string;
  scope: string;
  status: string;
  transactions: TransactionStats;
  accounts: AccountStats;
  network: NetworkStats;
  temporal: TemporalStats;
  amount_distribution: AmountBucket[];
  transactions_by_step: StepCount[];
  fraud_vs_normal: FraudVsNormal[];
  top_senders: TopAccount[];
  top_receivers: TopAccount[];
  feature_summary: FeatureStat[];
}

// ─── Small helpers ───────────────────────────────────────────────────────────

function fmt(n: number, decimals = 2): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: decimals });
}

function fmtUSD(n: number): string {
  return "$" + fmt(n, 0);
}

// ─── Sub-components ──────────────────────────────────────────────────────────

const StatCard: React.FC<{
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}> = ({ label, value, sub, accent }) => (
  <div className={`rounded-lg border p-4 flex flex-col gap-1 ${accent
    ? "bg-[#1a1f2e] border-[#3b4a6b]"
    : "bg-surface border-hairline"}`}>
    <span className="text-xs font-sans text-text-tertiary uppercase tracking-wider">{label}</span>
    <span className={`text-xl font-medium font-sans ${accent ? "text-[#6ca4ff]" : "text-text-primary"}`}>{value}</span>
    {sub && <span className="text-xs font-sans text-text-tertiary">{sub}</span>}
  </div>
);

const SectionHeader: React.FC<{ title: string; sub?: string }> = ({ title, sub }) => (
  <div className="mt-8 mb-3">
    <h2 className="text-sm font-semibold font-sans text-text-primary uppercase tracking-widest">{title}</h2>
    {sub && <p className="text-xs font-sans text-text-tertiary mt-0.5">{sub}</p>}
  </div>
);

/** Inline bar chart (CSS only, no canvas/recharts dependency) */
const BarChart: React.FC<{
  data: { label: string; value: number }[];
  maxValue: number;
  colorClass?: string;
}> = ({ data, maxValue, colorClass = "bg-[#3b6fd4]" }) => (
  <div className="space-y-1.5">
    {data.map((d) => (
      <div key={d.label} className="flex items-center gap-3 text-xs font-sans">
        <span className="w-24 text-right text-text-tertiary truncate shrink-0">{d.label}</span>
        <div className="flex-1 bg-surface-raised rounded-full h-2.5 overflow-hidden">
          <div
            className={`${colorClass} h-full rounded-full transition-all duration-500`}
            style={{ width: maxValue > 0 ? `${Math.min(100, (d.value / maxValue) * 100)}%` : "0%" }}
          />
        </div>
        <span className="w-16 text-text-secondary font-mono">{d.value.toLocaleString()}</span>
      </div>
    ))}
  </div>
);

const FeatureGroupBadge: React.FC<{ group: string }> = ({ group }) => {
  const styles: Record<string, string> = {
    graph: "bg-[#1e3a5f] text-[#6ca4ff] border-[#2d5491]",
    behavioral: "bg-[#1a3d2b] text-[#4ade80] border-[#2d5c3f]",
    temporal: "bg-[#3d2a1a] text-[#fb923c] border-[#5c3f2d]",
    other: "bg-surface text-text-tertiary border-hairline",
  };
  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${styles[group] || styles.other}`}>
      {group}
    </span>
  );
};

// ─── Main Screen ─────────────────────────────────────────────────────────────

export const PaySimExplorationScreen: React.FC = () => {
  const { isBackendConnected } = useApp();
  const [data, setData] = useState<ExplorationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notLoaded, setNotLoaded] = useState(false);

  const fetchExploration = useCallback(() => {
    setLoading(true);
    setError(null);
    setNotLoaded(false);

    api
      .getPaySimExploration()
      .then((resp: any) => {
        if (resp.status === "not_loaded" || resp.status === "error") {
          setNotLoaded(true);
        } else {
          setData(resp as ExplorationData);
        }
        setLoading(false);
      })
      .catch((err: any) => {
        setError(err.message || "Failed to load PaySim exploration data.");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchExploration();
  }, [fetchExploration]);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <div className="w-6 h-6 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
        <span className="text-xs font-sans text-text-tertiary">Loading PaySim exploration…</span>
      </div>
    );
  }

  // ── Not loaded ─────────────────────────────────────────────────────────────
  if (notLoaded || !data) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <div className="rounded-lg border border-hairline bg-surface p-8 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-surface-raised flex items-center justify-center mx-auto">
            <span className="text-2xl">📊</span>
          </div>
          <h2 className="text-base font-medium font-sans text-text-primary">PaySim Dataset Not Loaded</h2>
          <p className="text-sm font-sans text-text-secondary">
            The PaySim production slice is not currently available. The backend loads it automatically on startup.
          </p>
          {!isBackendConnected && (
            <p className="text-xs font-sans text-status-suspicious">Backend is currently unreachable.</p>
          )}
          <button
            id="paysim-exploration-retry-btn"
            onClick={fetchExploration}
            className="mt-2 px-4 py-2 rounded bg-accent-primary text-white text-sm font-sans hover:opacity-90 transition-opacity"
          >
            Retry
          </button>
          {error && <p className="text-xs font-sans text-status-suspicious">{error}</p>}
        </div>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="rounded-lg border border-[#521A1F] bg-[#2D1619] p-6 text-sm font-sans text-status-suspicious">
        {error}
        <button onClick={fetchExploration} className="ml-4 underline text-xs">Retry</button>
      </div>
    );
  }

  // ── Prepare chart data ─────────────────────────────────────────────────────
  const amountMaxCount = Math.max(...data.amount_distribution.map((b) => b.count), 1);
  const stepMaxCount = Math.max(...data.transactions_by_step.map((s) => s.count), 1);
  const fraudPct = data.accounts.count > 0
    ? ((data.accounts.fraud_involved / data.accounts.count) * 100).toFixed(2)
    : "0.00";

  const featuresByGroup: Record<string, FeatureStat[]> = {};
  for (const f of data.feature_summary) {
    if (!featuresByGroup[f.group]) featuresByGroup[f.group] = [];
    featuresByGroup[f.group].push(f);
  }
  const groupOrder = ["graph", "behavioral", "temporal"];

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div id="paysim-exploration-screen" className="max-w-5xl mx-auto space-y-0 pb-16">

      {/* Page header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-lg font-semibold font-sans text-text-primary">
            PaySim Exploration
          </h1>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1e3a5f] text-[#6ca4ff] border border-[#2d5491]">
            Production 10K Slice
          </span>
        </div>
        <p className="text-sm font-sans text-text-tertiary">
          Descriptive exploration of the deployed PaySim slice. This view is separate from the research benchmark and cross-dataset evaluation.
        </p>
      </div>

      {/* ── Summary cards ────────────────────────────────────────────────────── */}
      <SectionHeader title="Transaction Overview" />
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Transactions" value={fmt(data.transactions.count, 0)} accent />
        <StatCard label="Accounts" value={fmt(data.accounts.count, 0)} />
        <StatCard label="Fraud-Involved" value={fmt(data.accounts.fraud_involved, 0)} sub={`${fraudPct}% prevalence`} />
        <StatCard label="Normal" value={fmt(data.accounts.normal, 0)} />
        <StatCard label="Total Value" value={fmtUSD(data.transactions.total_amount)} />
        <StatCard label="Mean Tx Amount" value={fmtUSD(data.transactions.mean_amount)} sub={`Median: ${fmtUSD(data.transactions.median_amount)}`} />
      </div>

      {/* ── Network summary ───────────────────────────────────────────────────── */}
      <SectionHeader title="Network Topology" sub="Reuses cached graph metrics — no recomputation on request." />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Nodes" value={fmt(data.network.nodes, 0)} />
        <StatCard label="Edges" value={fmt(data.network.edges, 0)} />
        <StatCard label="Density" value={data.network.density.toFixed(6)} />
        <StatCard label="Weakly Connected Components" value={fmt(data.network.weakly_connected_components, 0)} />
      </div>

      {/* ── Temporal ──────────────────────────────────────────────────────────── */}
      {data.temporal.min_step !== null && (
        <>
          <SectionHeader title="Temporal (Simulated Steps)" sub="PaySim uses hourly simulated time steps." />
          <div className="grid grid-cols-3 gap-3">
            <StatCard label="Min Step" value={String(data.temporal.min_step)} />
            <StatCard label="Max Step" value={String(data.temporal.max_step)} />
            <StatCard label="Unique Steps" value={String(data.temporal.unique_steps)} />
          </div>
        </>
      )}

      {/* ── Amount distribution ───────────────────────────────────────────────── */}
      <SectionHeader title="Transaction Amount Distribution" />
      <div className="rounded-lg border border-hairline bg-surface p-5">
        <BarChart
          data={data.amount_distribution.map((b) => ({ label: b.bucket, value: b.count }))}
          maxValue={amountMaxCount}
          colorClass="bg-[#3b6fd4]"
        />
      </div>

      {/* ── Transactions over simulated time ─────────────────────────────────── */}
      {data.transactions_by_step.length > 0 && (
        <>
          <SectionHeader title="Transactions Over Simulated Time" sub="Step = simulated hourly time unit in PaySim." />
          <div className="rounded-lg border border-hairline bg-surface p-5">
            <BarChart
              data={data.transactions_by_step.map((s) => ({ label: `Step ${s.step}`, value: s.count }))}
              maxValue={stepMaxCount}
              colorClass="bg-[#6366f1]"
            />
          </div>
        </>
      )}

      {/* ── Fraud vs Normal ───────────────────────────────────────────────────── */}
      <SectionHeader title="Fraud-Involved vs Normal Accounts" sub="Based on account-level ground-truth labels from paysim_account_labels.csv." />
      <div className="rounded-lg border border-hairline bg-surface p-5">
        <BarChart
          data={data.fraud_vs_normal.map((f) => ({ label: f.label, value: f.count }))}
          maxValue={data.accounts.count}
          colorClass="bg-[#ef4444]"
        />
      </div>

      {/* ── Top senders / receivers ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <SectionHeader title="Top Senders" sub="By outgoing transaction count." />
          <div className="rounded-lg border border-hairline bg-surface overflow-hidden">
            <table className="w-full text-xs font-sans">
              <thead className="bg-surface-raised">
                <tr>
                  <th className="text-left px-4 py-2 text-text-tertiary font-medium">Account</th>
                  <th className="text-right px-4 py-2 text-text-tertiary font-medium">Tx Count</th>
                  <th className="text-right px-4 py-2 text-text-tertiary font-medium">Total Sent</th>
                </tr>
              </thead>
              <tbody>
                {data.top_senders.map((a, i) => (
                  <tr key={a.account_id} className={i % 2 === 0 ? "bg-surface" : "bg-surface-raised/30"}>
                    <td className="px-4 py-1.5 font-mono text-text-primary truncate max-w-[120px]" title={a.account_id}>
                      {a.account_id}
                    </td>
                    <td className="px-4 py-1.5 text-right text-text-secondary">{a.transaction_count}</td>
                    <td className="px-4 py-1.5 text-right text-text-secondary">{fmtUSD(a.total_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <SectionHeader title="Top Receivers" sub="By incoming transaction count." />
          <div className="rounded-lg border border-hairline bg-surface overflow-hidden">
            <table className="w-full text-xs font-sans">
              <thead className="bg-surface-raised">
                <tr>
                  <th className="text-left px-4 py-2 text-text-tertiary font-medium">Account</th>
                  <th className="text-right px-4 py-2 text-text-tertiary font-medium">Tx Count</th>
                  <th className="text-right px-4 py-2 text-text-tertiary font-medium">Total Recv.</th>
                </tr>
              </thead>
              <tbody>
                {data.top_receivers.map((a, i) => (
                  <tr key={a.account_id} className={i % 2 === 0 ? "bg-surface" : "bg-surface-raised/30"}>
                    <td className="px-4 py-1.5 font-mono text-text-primary truncate max-w-[120px]" title={a.account_id}>
                      {a.account_id}
                    </td>
                    <td className="px-4 py-1.5 text-right text-text-secondary">{a.transaction_count}</td>
                    <td className="px-4 py-1.5 text-right text-text-secondary">{fmtUSD(a.total_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Feature summary ───────────────────────────────────────────────────── */}
      <SectionHeader
        title="GraphFin 19-Feature Summary"
        sub="Descriptive statistics for the canonical feature schema across all accounts in the production slice."
      />
      {groupOrder.map((group) => {
        const features = featuresByGroup[group];
        if (!features || features.length === 0) return null;
        return (
          <div key={group} className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <FeatureGroupBadge group={group} />
              <span className="text-xs font-sans text-text-tertiary capitalize">{group} features</span>
            </div>
            <div className="rounded-lg border border-hairline bg-surface overflow-x-auto">
              <table className="w-full text-xs font-sans">
                <thead className="bg-surface-raised">
                  <tr>
                    <th className="text-left px-4 py-2 text-text-tertiary font-medium">Feature</th>
                    <th className="text-right px-4 py-2 text-text-tertiary font-medium">Mean</th>
                    <th className="text-right px-4 py-2 text-text-tertiary font-medium">Std</th>
                    <th className="text-right px-4 py-2 text-text-tertiary font-medium">Min</th>
                    <th className="text-right px-4 py-2 text-text-tertiary font-medium">Max</th>
                    <th className="text-right px-4 py-2 text-text-tertiary font-medium">Missing %</th>
                  </tr>
                </thead>
                <tbody>
                  {features.map((f, i) => (
                    <tr key={f.feature_name} className={i % 2 === 0 ? "bg-surface" : "bg-surface-raised/30"}>
                      <td className="px-4 py-1.5 font-mono text-text-primary">{f.feature_name}</td>
                      <td className="px-4 py-1.5 text-right text-text-secondary font-mono">{fmt(f.mean, 4)}</td>
                      <td className="px-4 py-1.5 text-right text-text-secondary font-mono">{fmt(f.std, 4)}</td>
                      <td className="px-4 py-1.5 text-right text-text-secondary font-mono">{fmt(f.min, 4)}</td>
                      <td className="px-4 py-1.5 text-right text-text-secondary font-mono">{fmt(f.max, 4)}</td>
                      <td className="px-4 py-1.5 text-right font-mono">
                        <span className={f.pct_missing > 5 ? "text-status-suspicious" : "text-text-secondary"}>
                          {f.pct_missing.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}

      {/* Scope footer */}
      <div className="mt-8 rounded-lg border border-hairline bg-surface-raised/30 p-4 text-xs font-sans text-text-tertiary">
        <strong className="text-text-secondary">Scope:</strong> PaySim Exploration — Production 10K Slice ·{" "}
        <strong className="text-text-secondary">Dataset ID:</strong> paysim ·{" "}
        <strong className="text-text-secondary">Transactions:</strong> {fmt(data.transactions.count, 0)} ·{" "}
        <strong className="text-text-secondary">Accounts:</strong> {fmt(data.accounts.count, 0)} ·{" "}
        Exploration data is cached on the backend after first request.
      </div>
    </div>
  );
};
