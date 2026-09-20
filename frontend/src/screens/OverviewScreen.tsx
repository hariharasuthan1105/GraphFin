import React, { useEffect, useState, useRef, useMemo } from "react";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { ForceGraph } from "../components/graph/ForceGraph";
import { AnimatedNumber } from "../utils/useCountUp";
import { formatCurrency, truncateId } from "../utils/formatters";
import {
  TransactionSummaryResponse,
  GraphSummaryResponse,
  AnomalySummaryResponse,
  UserAnomalyResult,
  NetworkNode,
} from "../types/api";

export const OverviewScreen: React.FC = () => {
  const {
    datasetId,
    experimentLabel,
    cachedEdges,
    setActiveNav,
    setSelectedNodeId,
    setDatasetId,
    datasetHistory,
    datasetCurrency,
  } = useApp();

  const [txSummary, setTxSummary] = useState<TransactionSummaryResponse | null>(null);
  const [graphSummary, setGraphSummary] = useState<GraphSummaryResponse | null>(null);
  const [anomalySummary, setAnomalySummary] = useState<AnomalySummaryResponse | null>(null);
  const [topAnomalies, setTopAnomalies] = useState<UserAnomalyResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Parallax offset state for hero section
  const [mouseParallax, setMouseParallax] = useState({ x: 0, y: 0 });
  const heroRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!datasetId) return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    Promise.all([
      api.getTransactionSummary(datasetId).catch(() => null),
      api.getGraphSummary(datasetId).catch(() => null),
      api.getAnomalySummary(datasetId, experimentLabel).catch(() => null),
      api
        .getUserAnomalies(datasetId, {
          experimentLabel,
          limit: 10,
          suspiciousOnly: false,
        })
        .catch(() => null),
    ])
      .then(([txResp, graphResp, anomResp, userResp]) => {
        if (!isMounted) return;
        setTxSummary(txResp);
        setGraphSummary(graphResp);
        setAnomalySummary(anomResp);

        if (userResp?.users && userResp.users.length > 0) {
          // Sort descending by real risk_score (0-100 percentile rank)
          const sorted = [...userResp.users].sort(
            (a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0)
          );
          setTopAnomalies(sorted.slice(0, 5));
        } else {
          setTopAnomalies([]);
        }
        setIsLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || "Failed to load overview data.");
        setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [datasetId, experimentLabel]);

  // Subtle mouse-based parallax tracker for hero
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!heroRef.current) return;
    const rect = heroRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setMouseParallax({ x: x * 14, y: y * 14 });
  };

  // Construct a quiet preview node list for the background graph hero
  const previewNodes: NetworkNode[] = useMemo(() => {
    const nodeMap = new Map<string, NetworkNode>();
    cachedEdges.slice(0, 80).forEach((e) => {
      if (!nodeMap.has(e.source)) {
        nodeMap.set(e.source, {
          id: e.source,
          degree: 1,
          status: "normal",
        });
      }
      if (!nodeMap.has(e.target)) {
        nodeMap.set(e.target, {
          id: e.target,
          degree: 1,
          status: "normal",
        });
      }
    });
    return Array.from(nodeMap.values());
  }, [cachedEdges]);

  if (!datasetId) {
    return (
      <div className="max-w-[960px] mx-auto py-12 text-left space-y-8">
        {/* Editorial Display Headline (EB Garamond) */}
        <div className="space-y-3">
          <h1 className="text-3xl md:text-4xl font-display font-normal text-text-primary tracking-tight">
            Financial integrity, measured.
          </h1>
          <p className="text-sm font-sans text-text-secondary max-w-xl leading-relaxed">
            Research-grade graph topology and unsupervised machine learning for financial
            transaction networks. Select an active dataset or upload a new transaction CSV
            to begin analysis.
          </p>
        </div>

        {/* Empty State Onboarding Card */}
        <div className="p-8 border border-hairline bg-surface rounded-lg space-y-6">
          <div className="space-y-1">
            <h2 className="text-base font-sans font-medium text-text-primary">
              No dataset currently active
            </h2>
            <p className="text-xs font-sans text-text-tertiary">
              Choose a recently ingested dataset or navigate to Datasets to upload a new transaction stream.
            </p>
          </div>

          {datasetHistory.length > 0 ? (
            <div className="space-y-2">
              <span className="text-xs font-sans text-text-secondary block">
                Available in session cache:
              </span>
              <div className="grid grid-cols-2 gap-3">
                {datasetHistory.slice(0, 4).map((d) => (
                  <button
                    key={d.id}
                    onClick={() => setDatasetId(d.id)}
                    className="p-3 bg-surface-raised border border-hairline hover:border-accent-primary rounded text-left transition-colors"
                  >
                    <span className="text-xs font-sans text-text-primary font-medium block">
                      {d.name}
                    </span>
                    <span className="text-[11px] font-mono text-text-tertiary block mt-0.5">
                      {truncateId(d.id, 10, 6)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="pt-2 flex items-center gap-3">
            <Button variant="primary" onClick={() => setActiveNav("datasets")}>
              Upload transactions CSV
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const isModelTrained = Boolean(
    anomalySummary &&
      (anomalySummary.suspicious_count !== undefined || anomalySummary.model_metadata)
  );

  return (
    <div className="space-y-8 max-w-[1040px] mx-auto text-left">
      {/* Editorial Display Headline (EB Garamond) */}
      <div className="space-y-2">
        <h1 className="text-3xl md:text-4xl font-display font-normal text-text-primary tracking-tight">
          Financial integrity, measured.
        </h1>
        <p className="text-sm font-sans text-text-secondary max-w-2xl leading-relaxed">
          {graphSummary && txSummary ? (
            <>
              Analyzing{" "}
              <span className="font-mono text-text-primary">
                {graphSummary.nodes.toLocaleString()}
              </span>{" "}
              accounts across{" "}
              <span className="font-mono text-text-primary">
                {txSummary.transactions.toLocaleString()}
              </span>{" "}
              directed transaction flows under empirical class balance.
            </>
          ) : (
            "Research-grade graph topology and unsupervised machine learning for financial transaction networks."
          )}
        </p>
      </div>

      {error && (
        <div className="p-3 bg-[#2D1619] border border-[#521A1F] rounded text-xs font-sans text-status-suspicious">
          {error}
        </div>
      )}

      {/* Hero Parallax Area: Background Quiet Graph Preview behind Public Sans Summary Stats */}
      <div
        ref={heroRef}
        onMouseMove={handleMouseMove}
        className="relative rounded-lg overflow-hidden border border-hairline bg-surface min-h-[360px] flex flex-col justify-between"
      >
        {/* Quiet Background Graph Preview with slow drift & parallax */}
        <div
          onClick={() => setActiveNav("graph")}
          className="absolute inset-0 cursor-pointer overflow-hidden transition-transform duration-200 ease-out"
          style={{
            transform: `translate3d(${mouseParallax.x * -0.5}px, ${mouseParallax.y * -0.5}px, 0)`,
            opacity: 0.28,
          }}
          title="Click to open interactive graph hero"
        >
          <ForceGraph
            nodes={previewNodes}
            edges={cachedEdges.slice(0, 80)}
            className="w-full h-full pointer-events-none"
          />
          {/* Subtle gradient vignette over background graph */}
          <div className="absolute inset-0 bg-gradient-to-t from-surface via-surface/40 to-transparent pointer-events-none" />
        </div>

        {/* Foreground Header Bar on Parallax Layer */}
        <div
          className="relative z-10 p-6 flex items-center justify-between pointer-events-auto transition-transform duration-200 ease-out"
          style={{
            transform: `translate3d(${mouseParallax.x * 0.2}px, ${mouseParallax.y * 0.2}px, 0)`,
          }}
        >
          <div>
            <span className="text-xs font-sans text-text-tertiary block">
              Active dataset overview
            </span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="font-mono text-xs text-text-primary">
                {truncateId(datasetId, 12, 8)}
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-status-normal" />
            </div>
          </div>

          <button
            onClick={() => setActiveNav("graph")}
            className="text-xs font-sans text-accent-primary hover:text-accent-graph hover:underline flex items-center gap-1 transition-colors"
          >
            <span>Explore full network graph</span>
            <span className="font-mono">→</span>
          </button>
        </div>

        {/* Four Public Sans Large-Numeral Stats floating over graph */}
        <div
          className="relative z-10 p-6 grid grid-cols-2 md:grid-cols-4 gap-4 transition-transform duration-200 ease-out"
          style={{
            transform: `translate3d(${mouseParallax.x * 0.3}px, ${mouseParallax.y * 0.3}px, 0)`,
          }}
        >
          {/* Stat 1: Entity Count */}
          <div className="glass-panel p-4 rounded text-left">
            <span className="text-xs font-sans text-text-secondary block">
              Node entities
            </span>
            <div className="font-stat text-2xl md:text-3xl font-semibold text-text-primary mt-1 tracking-tight">
              {graphSummary ? (
                <AnimatedNumber value={graphSummary.nodes} />
              ) : isLoading ? (
                "..."
              ) : (
                "—"
              )}
            </div>
            <span className="text-[11px] font-sans text-text-tertiary mt-1 block">
              Unique graph accounts
            </span>
          </div>

          {/* Stat 2: Transaction Count */}
          <div className="glass-panel p-4 rounded text-left">
            <span className="text-xs font-sans text-text-secondary block">
              Transactions
            </span>
            <div className="font-stat text-2xl md:text-3xl font-semibold text-text-primary mt-1 tracking-tight">
              {txSummary ? (
                <AnimatedNumber value={txSummary.transactions} />
              ) : isLoading ? (
                "..."
              ) : (
                "—"
              )}
            </div>
            <span className="text-[11px] font-sans text-text-tertiary mt-1 block">
              Directed monetary flows
            </span>
          </div>

          {/* Stat 3: Entities Flagged Suspicious (only if model trained; otherwise "Not yet scored") */}
          <div className="glass-panel p-4 rounded text-left">
            <span className="text-xs font-sans text-text-secondary block">
              Flagged entities
            </span>
            <div className="mt-1">
              {isModelTrained && anomalySummary ? (
                <div className="font-stat text-2xl md:text-3xl font-semibold text-status-suspicious tracking-tight">
                  <AnimatedNumber value={anomalySummary.suspicious_count} />
                </div>
              ) : (
                <div className="font-stat text-lg md:text-xl font-semibold text-text-tertiary mt-1">
                  Not yet scored
                </div>
              )}
            </div>
            <span className="text-[11px] font-sans text-text-tertiary mt-1 block">
              {isModelTrained ? (
                <span className="font-mono">
                  {anomalySummary?.contamination_rate
                    ? `${(anomalySummary.contamination_rate * 100).toFixed(2)}% rate`
                    : "Top outlier tier"}
                </span>
              ) : (
                "Requires trained model"
              )}
            </span>
          </div>

          {/* Stat 4: Total Volume (Static current total, NO trend arrow) */}
          <div className="glass-panel p-4 rounded text-left">
            <span className="text-xs font-sans text-text-secondary block">
              Total transaction volume
            </span>
            <div className="font-stat text-2xl md:text-3xl font-semibold text-text-primary mt-1 tracking-tight truncate">
              {txSummary ? formatCurrency(txSummary.total_amount, datasetCurrency) : isLoading ? "..." : "—"}
            </div>
            <span className="text-[11px] font-sans text-text-tertiary mt-1 block">
              Point-in-time snapshot
            </span>
          </div>
        </div>
      </div>

      {/* Lower Dashboard Grid: Real Highest-Risk Entities + Structural Component Clusters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Highest-Risk Entities (Real Live-Sorted List from /anomalies/users) */}
        <div className="border border-hairline bg-surface p-5 rounded-lg space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-hairline">
            <div>
              <h2 className="text-sm font-sans font-medium text-text-primary">
                Highest-risk entities
              </h2>
              <span className="text-xs font-sans text-text-tertiary">
                Top entities ordered by empirical risk percentile (0–100)
              </span>
            </div>
            {isModelTrained && (
              <Button size="sm" variant="ghost" onClick={() => setActiveNav("anomalies")}>
                View all
              </Button>
            )}
          </div>

          {isModelTrained && topAnomalies.length > 0 ? (
            <div className="space-y-2">
              {topAnomalies.map((entity) => (
                <div
                  key={entity.user_id}
                  onClick={() => {
                    setSelectedNodeId(entity.user_id);
                    setActiveNav("graph");
                  }}
                  className="p-3 bg-surface-raised/60 hover:bg-surface-raised border border-hairline rounded flex items-center justify-between cursor-pointer transition-colors"
                >
                  <div className="space-y-0.5 text-left">
                    <span className="font-mono text-xs text-text-primary hover:text-accent-primary">
                      {entity.user_id}
                    </span>
                    {entity.reasons && entity.reasons.length > 0 && (
                      <span className="text-[11px] font-sans text-text-tertiary block">
                        {entity.reasons[0]}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="font-mono text-xs text-text-primary block">
                        {entity.risk_score.toFixed(1)}
                      </span>
                      <span className="text-[10px] font-sans text-text-tertiary">
                        Risk score
                      </span>
                    </div>
                    <Badge
                      variant={
                        entity.status === "suspicious"
                          ? "suspicious"
                          : entity.status === "normal"
                          ? "normal"
                          : "neutral"
                      }
                    >
                      {entity.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center space-y-3">
              <p className="text-xs font-sans text-text-tertiary max-w-xs mx-auto">
                No anomaly model trained yet for this dataset. Train an Isolation Forest
                ensemble or compute a statistical baseline to calculate entity risk scores.
              </p>
              <Button size="sm" variant="secondary" onClick={() => setActiveNav("anomalies")}>
                Configure anomaly models
              </Button>
            </div>
          )}
        </div>

        {/* Structural Clusters / Weakly Connected Components (Real Topology instead of fake maps) */}
        <div className="border border-hairline bg-surface p-5 rounded-lg space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-hairline">
            <div>
              <h2 className="text-sm font-sans font-medium text-text-primary">
                Structural anomaly clusters
              </h2>
              <span className="text-xs font-sans text-text-tertiary">
                Topological partition by weakly-connected components
              </span>
            </div>
            <Button size="sm" variant="ghost" onClick={() => setActiveNav("graph")}>
              Inspect
            </Button>
          </div>

          <div className="space-y-3 text-left">
            <div className="grid grid-cols-2 gap-3 text-xs font-sans">
              <div className="p-3 bg-surface-raised/60 border border-hairline rounded">
                <span className="text-text-tertiary block">Connected components</span>
                <span className="text-lg font-mono text-text-primary mt-0.5 block">
                  {graphSummary ? graphSummary.weakly_connected_components : "—"}
                </span>
                <span className="text-[10px] font-sans text-text-tertiary mt-1 block">
                  Disjoint subgraphs
                </span>
              </div>

              <div className="p-3 bg-surface-raised/60 border border-hairline rounded">
                <span className="text-text-tertiary block">Network density</span>
                <span className="text-lg font-mono text-text-primary mt-0.5 block">
                  {graphSummary ? graphSummary.density.toFixed(5) : "—"}
                </span>
                <span className="text-[10px] font-sans text-text-tertiary mt-1 block">
                  Edge connectivity ratio
                </span>
              </div>
            </div>

            {/* Top Structural Centrality Hubs */}
            {graphSummary?.top_out_degree_nodes && graphSummary.top_out_degree_nodes.length > 0 && (
              <div className="pt-2 space-y-1.5">
                <span className="text-xs font-sans text-text-secondary block">
                  Top structural outflow hubs:
                </span>
                <div className="space-y-1">
                  {graphSummary.top_out_degree_nodes.slice(0, 3).map((node) => (
                    <div
                      key={node.user_id}
                      onClick={() => {
                        setSelectedNodeId(node.user_id);
                        setActiveNav("graph");
                      }}
                      className="px-2.5 py-1.5 bg-surface-raised/40 hover:bg-surface-raised border border-hairline rounded flex items-center justify-between text-xs cursor-pointer transition-colors"
                    >
                      <span className="font-mono text-text-primary hover:text-accent-primary">
                        {node.user_id}
                      </span>
                      <span className="font-mono text-text-secondary text-[11px]">
                        Out-deg: {node.out_degree} · {formatCurrency(node.weighted_out_degree, datasetCurrency)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="p-2.5 bg-surface-raised/30 border border-hairline/60 rounded text-[11px] font-sans text-text-tertiary leading-relaxed">
              Entities are organized by topological component reachability rather than geographic
              regions. Flagged nodes cluster within interconnected transaction subgraphs.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
