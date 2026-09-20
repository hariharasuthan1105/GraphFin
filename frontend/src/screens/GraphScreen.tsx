import React, { useEffect, useState, useMemo, useRef } from "react";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";
import { ForceGraph } from "../components/graph/ForceGraph";
import { NodeInspector } from "../components/graph/NodeInspector";
import {
  GraphSummaryResponse,
  NetworkNode,
  NetworkEdge,
  StreamStateResponse,
  StreamScoredEntity,
} from "../types/api";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

export const GraphScreen: React.FC = () => {
  const {
    datasetId,
    cachedEdges,
    selectedNodeId,
    setSelectedNodeId,
    anomalyResults,
    setAnomalyResults,
    experimentLabel,
    setActiveNav,
  } = useApp();

  // Mode: "static" (batch network view) vs "simulation" (live streaming replay)
  const [viewMode, setViewMode] = useState<"static" | "simulation">("static");

  // Static mode state
  const [summary, setSummary] = useState<GraphSummaryResponse | null>(null);
  const [userList, setUserList] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [staticError, setStaticError] = useState<string | null>(null);

  // Live simulation mode state
  const [simState, setSimState] = useState<StreamStateResponse | null>(null);
  const [isSimLoading, setIsSimLoading] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);

  // Config fields
  const [txPerTick, setTxPerTick] = useState<number>(50);
  const [tickInterval, setTickInterval] = useState<number>(2.0);
  const [rescoreTicks, setRescoreTicks] = useState<number>(5);
  const [selectedExp, setSelectedExp] = useState<string>(
    experimentLabel || "E4_full_graphfin"
  );

  // Active tab in simulation side drawer: "new" (newly flagged) vs "all_suspicious"
  const [flaggedTab, setFlaggedTab] = useState<"new" | "all">("new");

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Synchronize selectedExp when global experimentLabel changes
  useEffect(() => {
    if (experimentLabel) {
      setSelectedExp(experimentLabel);
    }
  }, [experimentLabel]);

  // Fetch static graph data when in static mode
  useEffect(() => {
    if (!datasetId || viewMode !== "static") return;

    let isMounted = true;
    setIsLoading(true);
    setStaticError(null);

    Promise.all([
      api.getGraphSummary(datasetId),
      api.getUserAnalytics(datasetId, { limit: 300 }).catch(() => null),
      api.getUserAnomalies(datasetId, { experimentLabel, limit: 300 }).catch(() => null),
    ])
      .then(([sumResp, userResp, anomResp]) => {
        if (!isMounted) return;
        setSummary(sumResp);
        if (userResp?.users) {
          setUserList(userResp.users);
        }
        if (anomResp?.users) {
          const map: Record<string, any> = {};
          anomResp.users.forEach((u) => {
            map[u.user_id] = u;
          });
          setAnomalyResults(map);
        }
        setIsLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setStaticError(err.message || "Failed to fetch graph summary.");
        setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [datasetId, experimentLabel, viewMode]);

  // Fetch initial stream state when switching to simulation mode
  useEffect(() => {
    if (!datasetId || viewMode !== "simulation") return;

    api
      .getStreamState(datasetId)
      .then((state) => {
        setSimState(state);
        if (state.transactions_per_tick) setTxPerTick(state.transactions_per_tick);
        if (state.tick_interval_seconds) setTickInterval(state.tick_interval_seconds);
        if (state.rescoring_interval_ticks) setRescoreTicks(state.rescoring_interval_ticks);
        if (state.experiment_label && state.experiment_label !== "default") {
          setSelectedExp(state.experiment_label);
        }
      })
      .catch(() => {
        // Not started yet
      });
  }, [datasetId, viewMode]);

  // Polling loop for active simulation
  useEffect(() => {
    if (!datasetId || viewMode !== "simulation") {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      return;
    }

    const isRunning = simState?.status === "running";

    if (isRunning) {
      const pollFreqMs = Math.max(400, Math.round(tickInterval * 800));
      pollIntervalRef.current = setInterval(() => {
        api
          .getStreamState(datasetId)
          .then((state) => {
            setSimState(state);
            if (state.status !== "running" && pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
          })
          .catch((err) => {
            console.error("Stream polling error:", err);
          });
      }, pollFreqMs);
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [datasetId, viewMode, simState?.status, tickInterval]);

  // Handler: Start simulation
  const handleStartSimulation = async () => {
    if (!datasetId) return;
    setIsSimLoading(true);
    setSimError(null);

    try {
      const state = await api.startStream(datasetId, {
        experiment_label: selectedExp,
        transactions_per_tick: txPerTick,
        tick_interval_seconds: tickInterval,
        rescoring_interval_ticks: rescoreTicks,
      });
      setSimState(state);
    } catch (err: any) {
      setSimError(err.message || "Failed to start live simulation.");
    } finally {
      setIsSimLoading(false);
    }
  };

  // Handler: Stop simulation
  const handleStopSimulation = async () => {
    if (!datasetId) return;
    setIsSimLoading(true);
    setSimError(null);

    try {
      const state = await api.stopStream(datasetId);
      setSimState(state);
    } catch (err: any) {
      setSimError(err.message || "Failed to stop simulation.");
    } finally {
      setIsSimLoading(false);
    }
  };

  // Static investigation limits
  const [nodeLimit, setNodeLimit] = useState<number>(100);
  const [expandNeighbors, setExpandNeighbors] = useState<boolean>(true);
  const edgeLimit = 300;

  // Static mode network nodes & edges with investigation limits
  const staticNetworkData = useMemo(() => {
    const nodeMap = new Map<string, NetworkNode>();

    userList.forEach((u) => {
      const anom = anomalyResults[u.user_id];
      const status: "suspicious" | "normal" | "unscored" =
        anom?.status === "suspicious"
          ? "suspicious"
          : anom?.status === "normal"
          ? "normal"
          : "unscored";

      nodeMap.set(u.user_id, {
        id: u.user_id,
        degree: u.total_degree || 1,
        in_degree: u.in_degree,
        out_degree: u.out_degree,
        betweenness: u.betweenness_centrality,
        status,
        risk_score: anom?.risk_score,
        reasons: anom?.reasons,
      });
    });

    cachedEdges.forEach((e) => {
      if (!nodeMap.has(e.source)) {
        const anom = anomalyResults[e.source];
        const status: "suspicious" | "normal" | "unscored" =
          anom?.status === "suspicious"
            ? "suspicious"
            : anom?.status === "normal"
            ? "normal"
            : "unscored";
        nodeMap.set(e.source, {
          id: e.source,
          degree: 1,
          status,
          risk_score: anom?.risk_score,
        });
      }
      if (!nodeMap.has(e.target)) {
        const anom = anomalyResults[e.target];
        const status: "suspicious" | "normal" | "unscored" =
          anom?.status === "suspicious"
            ? "suspicious"
            : anom?.status === "normal"
            ? "normal"
            : "unscored";
        nodeMap.set(e.target, {
          id: e.target,
          degree: 1,
          status,
          risk_score: anom?.risk_score,
        });
      }
    });

    const allNodesList = Array.from(nodeMap.values());
    if (allNodesList.length <= nodeLimit) {
      const nodeSet = new Set(allNodesList.map((n) => n.id));
      const edges = cachedEdges
        .filter((e) => nodeSet.has(e.source) && nodeSet.has(e.target))
        .slice(0, edgeLimit);
      return { nodes: allNodesList, edges, totalCount: allNodesList.length };
    }

    // Prioritized selection for large graphs:
    // 1. Selected node + its 1-hop neighbors
    // 2. Suspicious entities sorted by risk_score descending
    // 3. High degree structural hubs up to nodeLimit
    const prioritizedNodeIds = new Set<string>();

    if (selectedNodeId && nodeMap.has(selectedNodeId)) {
      prioritizedNodeIds.add(selectedNodeId);
      if (expandNeighbors) {
        cachedEdges.forEach((e) => {
          if (e.source === selectedNodeId) prioritizedNodeIds.add(e.target);
          if (e.target === selectedNodeId) prioritizedNodeIds.add(e.source);
        });
      }
    }

    const suspiciousNodes = allNodesList
      .filter((n) => n.status === "suspicious")
      .sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));

    for (const s of suspiciousNodes) {
      if (prioritizedNodeIds.size >= nodeLimit) break;
      prioritizedNodeIds.add(s.id);
    }

    if (prioritizedNodeIds.size < nodeLimit) {
      const remainingNodes = allNodesList
        .filter((n) => !prioritizedNodeIds.has(n.id))
        .sort((a, b) => (b.degree || 0) - (a.degree || 0));

      for (const r of remainingNodes) {
        if (prioritizedNodeIds.size >= nodeLimit) break;
        prioritizedNodeIds.add(r.id);
      }
    }

    const filteredNodes = Array.from(prioritizedNodeIds)
      .map((id) => nodeMap.get(id))
      .filter(Boolean) as NetworkNode[];

    const nodeSet = new Set(prioritizedNodeIds);
    const filteredEdges = cachedEdges
      .filter((e) => nodeSet.has(e.source) && nodeSet.has(e.target))
      .sort((a, b) => {
        const aInc = a.source === selectedNodeId || a.target === selectedNodeId ? 1 : 0;
        const bInc = b.source === selectedNodeId || b.target === selectedNodeId ? 1 : 0;
        if (aInc !== bInc) return bInc - aInc;
        return (b.amount || 0) - (a.amount || 0);
      })
      .slice(0, edgeLimit);

    return { nodes: filteredNodes, edges: filteredEdges, totalCount: allNodesList.length };
  }, [userList, cachedEdges, anomalyResults, selectedNodeId, nodeLimit, expandNeighbors]);

  // Simulation mode network nodes & edges
  const simNetworkNodes: NetworkNode[] = useMemo(() => {
    if (!simState || !simState.graph_nodes) return [];
    return simState.graph_nodes.map((n) => ({
      id: n.id,
      degree: n.degree,
      status:
        n.status === "suspicious"
          ? "suspicious"
          : n.status === "normal"
          ? "normal"
          : "unscored",
      risk_score: n.risk_score,
    }));
  }, [simState]);

  const simNetworkEdges: NetworkEdge[] = useMemo(() => {
    if (!simState || !simState.graph_edges) return [];
    return simState.graph_edges.map((e) => ({
      source: e.source,
      target: e.target,
      amount: e.amount,
      count: e.transactions,
    }));
  }, [simState]);

  // Active display nodes & edges based on mode
  const activeNodes = viewMode === "simulation" ? simNetworkNodes : staticNetworkData.nodes;
  const activeEdges = viewMode === "simulation" ? simNetworkEdges : staticNetworkData.edges;

  // Simulation progress helpers
  const simPercent = useMemo(() => {
    if (!simState || simState.total_transactions === 0) return 0;
    return Math.min(
      100,
      Math.round((simState.transactions_revealed / simState.total_transactions) * 100)
    );
  }, [simState]);

  // Filtered lists for recently flagged drawer
  const newlyFlagged = simState?.newly_flagged_entities || [];
  const allSuspicious = useMemo(() => {
    if (!simState?.scoring_results?.users) return [];
    return simState.scoring_results.users.filter((u) => u.status === "suspicious");
  }, [simState]);

  if (!datasetId) {
    return (
      <div className="h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-center space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-sans font-medium text-text-primary">
            No dataset selected
          </h2>
          <p className="text-sm font-sans text-text-secondary max-w-sm">
            Upload a transaction CSV to visualize the directed network graph and analyze structural hubs.
          </p>
        </div>
        <Button variant="primary" onClick={() => setActiveNav("datasets")}>
          Upload a dataset to begin
        </Button>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-56px)] flex flex-col justify-between overflow-hidden bg-canvas">
      {/* View Mode Switcher Header */}
      <div className="bg-surface border-b border-hairline px-6 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center space-x-2">
          <span className="text-xs uppercase tracking-wider text-text-tertiary font-mono mr-2">
            View Mode:
          </span>
          <button
            onClick={() => setViewMode("static")}
            className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
              viewMode === "static"
                ? "bg-accent text-canvas font-medium shadow-sm"
                : "bg-surface-raised text-text-secondary hover:text-text-primary hover:bg-surface-overlay"
            }`}
          >
            Static Network View
          </button>
          <button
            onClick={() => setViewMode("simulation")}
            className={`px-3 py-1 text-xs font-mono rounded transition-colors flex items-center gap-1.5 ${
              viewMode === "simulation"
                ? "bg-accent text-canvas font-medium shadow-sm"
                : "bg-surface-raised text-text-secondary hover:text-text-primary hover:bg-surface-overlay"
            }`}
          >
            {simState?.status === "running" && (
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            )}
            Live Streaming Simulation
          </button>
        </div>

        {/* Mode-specific status summary */}
        <div className="flex items-center space-x-3 text-xs font-mono text-text-secondary">
          {viewMode === "static" ? (
            <span>
              {summary ? `${summary.nodes} entities | ${summary.edges} edges` : "Loading..."}
            </span>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-text-tertiary">Status:</span>
              <span
                className={`font-semibold uppercase tracking-wider ${
                  simState?.status === "running"
                    ? "text-emerald-400"
                    : simState?.status === "complete"
                    ? "text-blue-400"
                    : simState?.status === "stopped"
                    ? "text-amber-400"
                    : "text-text-tertiary"
                }`}
              >
                {simState?.status || "Idle"}
              </span>
              {simState && (
                <span className="text-text-primary ml-2">
                  Tick #{simState.current_tick} | {simState.transactions_revealed} / {simState.total_transactions} txs ({simPercent}%)
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Static Investigation Limits Toolbar */}
      {viewMode === "static" && (
        <div className="bg-surface-raised border-b border-hairline px-6 py-2 flex items-center justify-between gap-4 flex-shrink-0 text-xs font-mono flex-wrap">
          <div className="flex items-center gap-3">
            <span className="text-text-tertiary">Node Limit:</span>
            <div className="flex items-center gap-1 bg-surface border border-hairline rounded p-0.5">
              {[50, 100, 250, 500].map((limit) => (
                <button
                  key={limit}
                  onClick={() => setNodeLimit(limit)}
                  className={`px-2 py-0.5 rounded text-[11px] transition-colors ${
                    nodeLimit === limit
                      ? "bg-accent-primary text-canvas font-semibold"
                      : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {limit}
                </button>
              ))}
            </div>
            <span className="text-text-tertiary text-[11px]">
              Showing {staticNetworkData.nodes.length} nodes & {staticNetworkData.edges.length} edges (top suspicious entities + 1-hop neighbors)
            </span>
          </div>

          <div className="flex items-center gap-3">
            {selectedNodeId && (
              <div className="flex items-center gap-2">
                <span className="text-text-secondary text-[11px]">
                  Selected: <strong className="text-accent-primary font-mono">{selectedNodeId}</strong>
                </span>
                <button
                  onClick={() => setExpandNeighbors(!expandNeighbors)}
                  className={`px-2 py-0.5 rounded text-[11px] border transition-colors ${
                    expandNeighbors
                      ? "bg-accent-primary/20 border-accent-primary text-accent-primary"
                      : "bg-surface border-hairline text-text-secondary hover:text-text-primary"
                  }`}
                  title="Include all 1-hop transactional neighbors of the selected entity"
                >
                  {expandNeighbors ? "✓ 1-Hop Neighbors" : "+ 1-Hop Neighbors"}
                </button>
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="px-1.5 py-0.5 rounded text-[11px] text-text-tertiary hover:text-text-primary"
                >
                  Clear
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Honesty & Disclaimer Banner for Live Simulation */}
      {viewMode === "simulation" && (
        <div className="bg-[#121A24] border-b border-[#1E3246] px-6 py-2 flex items-center justify-between text-xs font-sans text-[#78A9FF] select-none flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold uppercase tracking-wider text-[11px] bg-[#1A2E44] px-1.5 py-0.5 rounded text-[#8AB4F8] border border-[#244266]">
              Controlled Replay
            </span>
            <span>
              Live simulation — replaying real transaction data from an already-trained model. Not a live production feed.
            </span>
          </div>
          <span className="text-text-tertiary text-[11px]">
            Fixed offline model inference; locked benchmark results in Evaluation remain unchanged.
          </span>
        </div>
      )}

      {/* Simulation Controls Toolbar (when in simulation mode) */}
      {viewMode === "simulation" && (
        <div className="bg-surface-raised border-b border-hairline px-6 py-3 flex items-center justify-between gap-4 flex-shrink-0 flex-wrap">
          {/* Inputs */}
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span className="text-text-tertiary">Tx/Tick:</span>
              <input
                type="number"
                min={1}
                max={500}
                value={txPerTick}
                disabled={simState?.status === "running"}
                onChange={(e) => setTxPerTick(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-16 px-2 py-1 bg-surface border border-hairline rounded text-text-primary text-xs font-mono focus:outline-none focus:border-accent disabled:opacity-50"
              />
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-text-tertiary">Interval (s):</span>
              <input
                type="number"
                min={0.1}
                step={0.5}
                max={10.0}
                value={tickInterval}
                disabled={simState?.status === "running"}
                onChange={(e) => setTickInterval(Math.max(0.1, parseFloat(e.target.value) || 0.5))}
                className="w-16 px-2 py-1 bg-surface border border-hairline rounded text-text-primary text-xs font-mono focus:outline-none focus:border-accent disabled:opacity-50"
              />
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-text-tertiary">Rescore every:</span>
              <input
                type="number"
                min={1}
                max={50}
                value={rescoreTicks}
                disabled={simState?.status === "running"}
                onChange={(e) => setRescoreTicks(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-14 px-2 py-1 bg-surface border border-hairline rounded text-text-primary text-xs font-mono focus:outline-none focus:border-accent disabled:opacity-50"
              />
              <span className="text-text-tertiary">ticks</span>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-text-tertiary">Model Exp:</span>
              <input
                type="text"
                value={selectedExp}
                disabled={simState?.status === "running"}
                onChange={(e) => setSelectedExp(e.target.value)}
                placeholder="E4_full_graphfin"
                className="w-36 px-2 py-1 bg-surface border border-hairline rounded text-text-primary text-xs font-mono focus:outline-none focus:border-accent disabled:opacity-50"
              />
            </div>
          </div>

          {/* Action Buttons & Progress Bar */}
          <div className="flex items-center gap-3">
            {/* Progress bar */}
            <div className="w-36 bg-surface rounded-full h-2 overflow-hidden border border-hairline hidden md:block">
              <div
                className="bg-accent h-full transition-all duration-300"
                style={{ width: `${simPercent}%` }}
              />
            </div>

            {simState?.status === "running" ? (
              <Button
                size="sm"
                variant="danger"
                onClick={handleStopSimulation}
                disabled={isSimLoading}
              >
                Stop Replay
              </Button>
            ) : (
              <Button
                size="sm"
                variant="primary"
                onClick={handleStartSimulation}
                disabled={isSimLoading}
              >
                {simState?.status === "stopped" ? "Resume Replay" : "Start Replay"}
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Error Banners */}
      {(staticError || simError) && (
        <div className="px-6 py-2 bg-[#2D1619] border-b border-[#521A1F] text-xs font-sans text-status-suspicious text-left flex justify-between items-center flex-shrink-0">
          <span>{staticError || simError}</span>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setStaticError(null);
              setSimError(null);
            }}
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Simulation Complete Alert */}
      {viewMode === "simulation" && simState?.status === "complete" && (
        <div className="bg-[#12231A] border-b border-[#1E462E] px-6 py-2 text-xs font-sans text-emerald-400 flex justify-between items-center flex-shrink-0">
          <span>
            ✓ Simulation complete — All {simState.total_transactions} transactions have been revealed and rescored against '{simState.experiment_label}'.
          </span>
          <Button size="sm" variant="ghost" onClick={handleStartSimulation}>
            Restart Simulation
          </Button>
        </div>
      )}

      {/* Main Canvas Area + Live Drawers */}
      <div className="flex-1 relative flex overflow-hidden">
        {/* Force-directed graph canvas */}
        <div className="flex-1 h-full relative">
          <ForceGraph
            nodes={activeNodes}
            edges={activeEdges}
            selectedNodeId={selectedNodeId}
            onNodeClick={(id) => setSelectedNodeId(id)}
          />

          {/* Floating Live Simulation Overlay Badge (Graph corner) */}
          {viewMode === "simulation" && (
            <div className="absolute top-4 left-4 bg-surface/90 backdrop-blur border border-hairline rounded-lg p-3 shadow-lg pointer-events-auto select-none space-y-1 z-10 text-left">
              <div className="flex items-center gap-2">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    simState?.status === "running"
                      ? "bg-emerald-400 animate-pulse"
                      : simState?.status === "complete"
                      ? "bg-blue-400"
                      : "bg-text-tertiary"
                  }`}
                />
                <span className="text-xs font-mono font-medium text-text-primary">
                  {simState?.status === "running"
                    ? "Live Replay In Progress"
                    : simState?.status === "complete"
                    ? "Simulation Finished"
                    : "Simulation Ready"}
                </span>
              </div>
              <div className="text-[11px] font-mono text-text-secondary">
                Revealed: {simState ? simState.transactions_revealed : 0} / {simState ? simState.total_transactions : 0} txs
              </div>
              <div className="text-[11px] font-mono text-text-secondary">
                Active Nodes: {activeNodes.length} | Edges: {activeEdges.length}
              </div>
              {simState?.last_rescoring_tick !== undefined && simState.last_rescoring_tick !== null && (
                <div className="text-[11px] font-mono text-accent">
                  Last Rescored: Tick #{simState.last_rescoring_tick}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Live Simulation "Most Recently Flagged" Sidebar Panel */}
        {viewMode === "simulation" && (
          <div className="w-80 border-l border-hairline bg-surface/95 backdrop-blur flex flex-col h-full z-10 overflow-hidden flex-shrink-0">
            {/* Header / Tab switcher */}
            <div className="p-3 border-b border-hairline flex items-center justify-between">
              <div className="flex gap-2">
                <button
                  onClick={() => setFlaggedTab("new")}
                  className={`text-xs font-mono px-2 py-1 rounded transition-colors ${
                    flaggedTab === "new"
                      ? "bg-surface-raised text-text-primary border border-hairline font-medium"
                      : "text-text-tertiary hover:text-text-secondary"
                  }`}
                >
                  Newly Flagged ({newlyFlagged.length})
                </button>
                <button
                  onClick={() => setFlaggedTab("all")}
                  className={`text-xs font-mono px-2 py-1 rounded transition-colors ${
                    flaggedTab === "all"
                      ? "bg-surface-raised text-text-primary border border-hairline font-medium"
                      : "text-text-tertiary hover:text-text-secondary"
                  }`}
                >
                  All Suspicious ({allSuspicious.length})
                </button>
              </div>
            </div>

            {/* List Content */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {flaggedTab === "new" ? (
                newlyFlagged.length === 0 ? (
                  <div className="h-48 flex flex-col items-center justify-center text-center p-4 text-xs font-mono text-text-tertiary">
                    {simState?.status === "running" ? (
                      <>
                        <span className="inline-block w-2 h-2 rounded-full bg-accent animate-ping mb-2" />
                        <span>Monitoring stream...</span>
                        <span className="text-[10px] mt-1 text-text-tertiary">
                          Rescores every {rescoreTicks} ticks. Entities newly flagged since last rescore will appear here.
                        </span>
                      </>
                    ) : (
                      <span>No entities newly flagged in the current interval.</span>
                    )}
                  </div>
                ) : (
                  newlyFlagged.map((entity: StreamScoredEntity) => (
                    <div
                      key={entity.user_id}
                      onClick={() => setSelectedNodeId(entity.user_id)}
                      className={`p-2.5 rounded border transition-all cursor-pointer text-left ${
                        selectedNodeId === entity.user_id
                          ? "bg-[#3A181C] border-status-suspicious shadow"
                          : "bg-surface-raised hover:bg-surface-overlay border-hairline"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono font-medium text-text-primary truncate max-w-[140px]">
                          {entity.user_id}
                        </span>
                        <Badge variant="suspicious">
                          Risk: {entity.risk_score.toFixed(3)}
                        </Badge>
                      </div>
                      {entity.reasons && entity.reasons.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {entity.reasons.slice(0, 2).map((r, i) => (
                            <span
                              key={i}
                              className="text-[10px] font-mono px-1 py-0.5 rounded bg-surface border border-hairline text-text-secondary"
                            >
                              {r}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )
              ) : allSuspicious.length === 0 ? (
                <div className="h-48 flex items-center justify-center text-center p-4 text-xs font-mono text-text-tertiary">
                  <span>No suspicious entities identified yet.</span>
                </div>
              ) : (
                allSuspicious.map((entity: StreamScoredEntity) => (
                  <div
                    key={entity.user_id}
                    onClick={() => setSelectedNodeId(entity.user_id)}
                    className={`p-2.5 rounded border transition-all cursor-pointer text-left ${
                      selectedNodeId === entity.user_id
                        ? "bg-[#3A181C] border-status-suspicious shadow"
                        : "bg-surface-raised hover:bg-surface-overlay border-hairline"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono font-medium text-text-primary truncate max-w-[140px]">
                        {entity.user_id}
                      </span>
                      <Badge variant="suspicious">
                        Risk: {entity.risk_score.toFixed(3)}
                      </Badge>
                    </div>
                    {entity.reasons && entity.reasons.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {entity.reasons.slice(0, 2).map((r, i) => (
                          <span
                            key={i}
                            className="text-[10px] font-mono px-1 py-0.5 rounded bg-surface border border-hairline text-text-secondary"
                          >
                            {r}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Footer summary */}
            <div className="p-2 border-t border-hairline bg-surface text-[10px] font-mono text-text-tertiary text-center">
              Click any entity to focus & inspect graph features
            </div>
          </div>
        )}

        {/* Node Inspector Drawer */}
        {selectedNodeId && (
          <NodeInspector
            userId={selectedNodeId}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </div>

      {/* Hero Topological Invariants Strip */}
      <div className="bg-surface border-t border-hairline px-6 py-4 flex-shrink-0 select-none">
        <div className="flex items-baseline gap-12 text-left">
          <div>
            <div className="text-2xl font-mono font-medium text-text-primary">
              {viewMode === "simulation"
                ? activeNodes.length
                : summary
                ? summary.nodes
                : isLoading
                ? "..."
                : "—"}
            </div>
            <div className="text-xs font-sans text-text-secondary mt-0.5">
              {viewMode === "simulation" ? "Revealed Entities" : "Node entities"}
            </div>
          </div>

          <div>
            <div className="text-2xl font-mono font-medium text-text-primary">
              {viewMode === "simulation"
                ? activeEdges.length
                : summary
                ? summary.edges
                : isLoading
                ? "..."
                : "—"}
            </div>
            <div className="text-xs font-sans text-text-secondary mt-0.5">
              {viewMode === "simulation" ? "Revealed Edges" : "Directed edges"}
            </div>
          </div>

          <div>
            <div className="text-2xl font-mono font-medium text-text-primary">
              {viewMode === "simulation"
                ? `${simState ? simState.transactions_revealed : 0} / ${simState ? simState.total_transactions : 0}`
                : summary
                ? summary.density.toFixed(5)
                : isLoading
                ? "..."
                : "—"}
            </div>
            <div className="text-xs font-sans text-text-secondary mt-0.5">
              {viewMode === "simulation" ? "Transactions Revealed" : "Network density"}
            </div>
          </div>

          <div>
            <div className="text-2xl font-mono font-medium text-text-primary">
              {viewMode === "simulation"
                ? `${newlyFlagged.length} new (${allSuspicious.length} total)`
                : summary
                ? summary.weakly_connected_components
                : isLoading
                ? "..."
                : "—"}
            </div>
            <div className="text-xs font-sans text-text-secondary mt-0.5">
              {viewMode === "simulation"
                ? "Suspicious Entities"
                : "Weakly connected components"}
            </div>
          </div>

          <div>
            <div className="text-2xl font-mono font-medium text-text-primary">
              {viewMode === "simulation"
                ? simState?.last_rescoring_tick !== null && simState?.last_rescoring_tick !== undefined
                  ? `Tick #${simState.last_rescoring_tick}`
                  : "Pending"
                : summary?.is_directed
                ? "Directed"
                : "Undirected"}
            </div>
            <div className="text-xs font-sans text-text-secondary mt-0.5">
              {viewMode === "simulation" ? "Last Rescore" : "Graph topology"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
