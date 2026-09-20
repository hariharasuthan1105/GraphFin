import React, { useEffect, useState } from "react";
import { api } from "../../api/client";
import { NodeMetrics, UserFeatures } from "../../types/api";
import { formatNumber, formatCurrency } from "../../utils/formatters";
import { Badge } from "../ui/Badge";
import { useApp } from "../../context/AppContext";

interface NodeInspectorProps {
  userId: string;
  onClose: () => void;
}

export const NodeInspector: React.FC<NodeInspectorProps> = ({ userId, onClose }) => {
  const { datasetId, anomalyResults, datasetCurrency } = useApp();
  const [metrics, setMetrics] = useState<NodeMetrics | null>(null);
  const [features, setFeatures] = useState<UserFeatures | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const anomaly = anomalyResults[userId];
  const [isMountedAnim, setIsMountedAnim] = useState(false);

  useEffect(() => {
    setIsMountedAnim(false);
    const frame = requestAnimationFrame(() => {
      setIsMountedAnim(true);
    });
    return () => cancelAnimationFrame(frame);
  }, [userId]);

  useEffect(() => {
    if (!datasetId || !userId) return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    Promise.all([
      api.getNodeMetrics(datasetId, userId).catch((err) => {
        console.warn("Could not load node metrics:", err);
        return null;
      }),
      api.getSingleUserFeatures(datasetId, userId).catch((err) => {
        console.warn("Could not load full user features:", err);
        return null;
      }),
    ])
      .then(([m, f]) => {
        if (!isMounted) return;
        setMetrics(m);
        setFeatures(f);
        setIsLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || "Failed to inspect node.");
        setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [datasetId, userId]);

  return (
    <div
      className={`w-80 glass-panel border-l border-glass h-full flex flex-col justify-between overflow-y-auto z-10 transition-all duration-140 ease-out transform shadow-2xl ${
        isMountedAnim ? "opacity-100 translate-x-0" : "opacity-0 translate-x-2"
      }`}
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between pb-3 border-b border-hairline mb-4">
          <div className="text-left">
            <span className="text-xs font-sans text-text-tertiary block">
              Node inspector
            </span>
            <h3 className="text-sm font-mono font-medium text-text-primary break-all mt-0.5">
              {userId}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-text-tertiary hover:text-text-primary p-1 transition-colors"
            title="Close inspector"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Anomaly model status if available */}
        {anomaly && (
          <div className="mb-4 pb-4 border-b border-hairline text-left">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-sans text-text-secondary">Model status</span>
              <Badge
                variant={
                  anomaly.status === "suspicious"
                    ? "suspicious"
                    : anomaly.status === "normal"
                    ? "normal"
                    : "neutral"
                }
              >
                {anomaly.status}
              </Badge>
            </div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-sans text-text-tertiary">Risk score</span>
              <span className="text-xs font-mono text-text-primary">
                {anomaly.risk_score.toFixed(1)} / 100
              </span>
            </div>
            {/* Risk score bar */}
            <div className="w-full bg-surface h-1.5 rounded overflow-hidden">
              <div
                className={`h-full ${
                  anomaly.status === "suspicious"
                    ? "bg-status-suspicious"
                    : "bg-status-normal"
                }`}
                style={{ width: `${Math.min(100, Math.max(0, anomaly.risk_score))}%` }}
              />
            </div>
            {anomaly.reasons && anomaly.reasons.length > 0 && (
              <div className="mt-3">
                <span className="text-xs font-sans text-text-tertiary block mb-1">
                  Explanations
                </span>
                <div className="flex flex-wrap gap-1">
                  {anomaly.reasons.map((r, idx) => (
                    <span
                      key={idx}
                      className="text-[11px] font-mono bg-surface px-1.5 py-0.5 rounded border border-hairline text-text-secondary"
                    >
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {isLoading ? (
          <div className="py-8 text-center text-xs font-sans text-text-tertiary">
            Loading node structural metrics...
          </div>
        ) : error ? (
          <div className="text-xs font-sans text-status-suspicious p-3 bg-[#2D1619]/40 border border-[#521A1F] rounded">
            {error}
          </div>
        ) : metrics ? (
          <div className="space-y-4 text-left">
            {/* Degree centrality metrics */}
            <div>
              <span className="text-xs font-medium font-sans text-text-secondary block mb-2">
                Structural centrality
              </span>
              <div className="space-y-1.5 text-xs font-sans">
                <div className="flex justify-between py-1 border-b border-hairline/50">
                  <span className="text-text-tertiary">Total degree</span>
                  <span className="font-mono text-text-primary">
                    {metrics.total_degree}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-hairline/50">
                  <span className="text-text-tertiary">In-degree</span>
                  <span className="font-mono text-text-primary">
                    {metrics.in_degree}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-hairline/50">
                  <span className="text-text-tertiary">Out-degree</span>
                  <span className="font-mono text-text-primary">
                    {metrics.out_degree}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-hairline/50">
                  <span className="text-text-tertiary">Betweenness</span>
                  <span className="font-mono text-text-primary">
                    {metrics.betweenness_centrality.toFixed(6)}
                  </span>
                </div>
              </div>
            </div>

            {/* Transaction volumes */}
            <div>
              <span className="text-xs font-medium font-sans text-text-secondary block mb-2">
                Monetary flow
              </span>
              <div className="space-y-1.5 text-xs font-sans">
                <div className="flex justify-between py-1 border-b border-hairline/50">
                  <span className="text-text-tertiary">Weighted in-flow</span>
                  <span className="font-mono text-text-primary">
                    {formatCurrency(metrics.weighted_in_degree, datasetCurrency)}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-hairline/50">
                  <span className="text-text-tertiary">Weighted out-flow</span>
                  <span className="font-mono text-text-primary">
                    {formatCurrency(metrics.weighted_out_degree, datasetCurrency)}
                  </span>
                </div>
                {features && (
                  <>
                    <div className="flex justify-between py-1 border-b border-hairline/50">
                      <span className="text-text-tertiary">Net flow</span>
                      <span
                        className={`font-mono ${
                          features.net_flow >= 0
                            ? "text-status-normal"
                            : "text-status-suspicious"
                        }`}
                      >
                        {formatCurrency(features.net_flow, datasetCurrency)}
                      </span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-hairline/50">
                      <span className="text-text-tertiary">Avg tx amount</span>
                      <span className="font-mono text-text-primary">
                        {formatCurrency(features.average_transaction_amount, datasetCurrency)}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Behavioral stats if available */}
            {features && (
              <div>
                <span className="text-xs font-medium font-sans text-text-secondary block mb-2">
                  Behavioral profile
                </span>
                <div className="space-y-1.5 text-xs font-sans">
                  <div className="flex justify-between py-1 border-b border-hairline/50">
                    <span className="text-text-tertiary">Total tx count</span>
                    <span className="font-mono text-text-primary">
                      {features.transaction_count}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-hairline/50">
                    <span className="text-text-tertiary">Tx / day</span>
                    <span className="font-mono text-text-primary">
                      {formatNumber(features.transactions_per_day, 2)}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-hairline/50">
                    <span className="text-text-tertiary">Unique counterparties</span>
                    <span className="font-mono text-text-primary">
                      {features.unique_senders + features.unique_receivers}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>

      <div className="p-4 border-t border-glass bg-transparent text-xs font-mono text-text-tertiary text-center">
        GET /graph/{datasetId}/nodes/{userId}
      </div>
    </div>
  );
};
