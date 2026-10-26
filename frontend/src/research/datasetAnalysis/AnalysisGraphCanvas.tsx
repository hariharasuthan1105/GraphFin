import { useEffect, useRef, useState } from "react";
import type { AccountNode, TransferEdge } from "./types";

interface Props {
  accounts: AccountNode[];
  edges: TransferEdge[];
  selectedNode: string | null;
  onSelectNode: (id: string) => void;
  maxRenderNodes?: number;
}

interface SimNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  score: number;
  isHighRisk: boolean;
  patterns: string[];
}

interface SimEdge {
  source: string;
  target: string;
  amount: number;
  isReciprocal?: boolean;
}

export function AnalysisGraphCanvas({
  accounts,
  edges,
  selectedNode,
  onSelectNode,
  maxRenderNodes = 60,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [links, setLinks] = useState<SimEdge[]>([]);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [zoom, setZoom] = useState(1.0);

  // Filter top most active / anomalous nodes to ensure crisp performance
  useEffect(() => {
    const activeNodes = accounts.slice(0, maxRenderNodes);
    const activeIds = new Set(activeNodes.map((a) => a.id));

    // Width and height of virtual canvas
    const W = 800;
    const H = 550;
    const cx = W / 2;
    const cy = H / 2;

    const simNodes: SimNode[] = activeNodes.map((acc, idx) => {
      // Initialize in concentric ring based on anomaly score
      const angle = (idx / activeNodes.length) * 2 * Math.PI;
      const dist = (1 - acc.anomalyScore * 0.6) * 180 + 30;
      return {
        id: acc.id,
        x: cx + Math.cos(angle) * dist + (Math.random() - 0.5) * 20,
        y: cy + Math.sin(angle) * dist + (Math.random() - 0.5) * 20,
        vx: 0,
        vy: 0,
        radius: Math.max(5, Math.min(14, 5 + Math.log10(Math.max(1, acc.totalDegree)) * 4)),
        score: acc.anomalyScore,
        isHighRisk: acc.anomalyScore >= 0.45 || acc.patterns.length > 0,
        patterns: acc.patterns,
      };
    });

    const activeEdges = edges
      .filter((e) => activeIds.has(e.source) && activeIds.has(e.target))
      .slice(0, 150);

    // Run simple spring relaxation
    const nodeMap = new Map(simNodes.map((n) => [n.id, n]));
    for (let step = 0; step < 60; step++) {
      // Edge spring pull
      for (const e of activeEdges) {
        const u = nodeMap.get(e.source);
        const v = nodeMap.get(e.target);
        if (u && v) {
          const dx = v.x - u.x;
          const dy = v.y - u.y;
          const dist = Math.max(1, Math.hypot(dx, dy));
          const force = (dist - 80) * 0.02;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          u.x += fx;
          u.y += fy;
          v.x -= fx;
          v.y -= fy;
        }
      }

      // Node electrostatic repulsion
      for (let i = 0; i < simNodes.length; i++) {
        for (let j = i + 1; j < simNodes.length; j++) {
          const u = simNodes[i];
          const v = simNodes[j];
          const dx = v.x - u.x;
          const dy = v.y - u.y;
          const distSq = dx * dx + dy * dy || 1;
          if (distSq < 15000) {
            const force = 300 / distSq;
            const dist = Math.sqrt(distSq);
            u.x -= (dx / dist) * force;
            u.y -= (dy / dist) * force;
            v.x += (dx / dist) * force;
            v.y += (dy / dist) * force;
          }
        }
      }

      // Center gravity
      for (const n of simNodes) {
        n.x += (cx - n.x) * 0.015;
        n.y += (cy - n.y) * 0.015;
      }
    }

    setNodes(simNodes);
    setLinks(activeEdges);
  }, [accounts, edges, maxRenderNodes]);

  return (
    <div className="analysis-graph-container" ref={containerRef} style={{ position: "relative" }}>
      <div className="graph-controls-bar">
        <span className="eyebrow technical">
          INTERACTIVE TOPOLOGY LENS ({nodes.length} ACCOUNTS / {links.length} TRANSFERS)
        </span>
        <div className="graph-zoom-actions">
          <button
            type="button"
            className="zoom-btn"
            onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))}
            title="Zoom out"
          >
            -
          </button>
          <span className="zoom-value">{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            className="zoom-btn"
            onClick={() => setZoom((z) => Math.min(2.0, z + 0.2))}
            title="Zoom in"
          >
            +
          </button>
          <button
            type="button"
            className="zoom-btn reset"
            onClick={() => setZoom(1.0)}
            title="Reset zoom"
          >
            RESET
          </button>
        </div>
      </div>

      <svg
        viewBox="0 0 800 550"
        className="analysis-graph-svg"
        style={{
          width: "100%",
          height: "480px",
          background: "#080809",
          border: "1px solid #303034",
          display: "block",
        }}
      >
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="18"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#55555c" />
          </marker>
          <marker
            id="arrow-risk"
            viewBox="0 0 10 10"
            refX="18"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#c04b52" />
          </marker>
        </defs>

        <g transform={`translate(${400 * (1 - zoom)}, ${275 * (1 - zoom)}) scale(${zoom})`}>
          {/* Edges */}
          {links.map((link, idx) => {
            const u = nodes.find((n) => n.id === link.source);
            const v = nodes.find((n) => n.id === link.target);
            if (!u || !v) return null;
            const isHighRisk = u.isHighRisk || v.isHighRisk || link.isReciprocal;
            const isSelected = selectedNode === u.id || selectedNode === v.id;

            return (
              <line
                key={`${link.source}-${link.target}-${idx}`}
                x1={u.x}
                y1={u.y}
                x2={v.x}
                y2={v.y}
                stroke={
                  isSelected
                    ? "#ffffff"
                    : isHighRisk
                    ? link.isReciprocal
                      ? "#e05252"
                      : "#842d35"
                    : "#303034"
                }
                strokeWidth={isSelected ? 2 : link.isReciprocal ? 1.8 : 1}
                strokeDasharray={link.isReciprocal ? "3,3" : undefined}
                markerEnd={isHighRisk ? "url(#arrow-risk)" : "url(#arrow)"}
                opacity={0.75}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((n) => {
            const isSelected = selectedNode === n.id;
            const isHovered = hoveredNode?.id === n.id;

            let fillColor = "#77777d";
            if (n.isHighRisk) {
              fillColor = n.score >= 0.7 ? "#e05252" : "#b44a50";
            } else if (n.score < 0.2) {
              fillColor = "#2a2a2e";
            }

            return (
              <g
                key={n.id}
                transform={`translate(${n.x}, ${n.y})`}
                onClick={() => onSelectNode(n.id)}
                onMouseEnter={() => setHoveredNode(n)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: "pointer" }}
              >
                {/* Glow ring for selected or high risk */}
                {(isSelected || n.isHighRisk) && (
                  <circle
                    r={n.radius + (isSelected ? 6 : 4)}
                    fill="none"
                    stroke={isSelected ? "#ffffff" : "#c04b52"}
                    strokeWidth={isSelected ? 2 : 1}
                    opacity={isSelected ? 0.9 : 0.4}
                  />
                )}

                <circle
                  r={n.radius}
                  fill={fillColor}
                  stroke={isSelected ? "#ffffff" : n.isHighRisk ? "#e05252" : "#45454a"}
                  strokeWidth={isSelected ? 2 : 1}
                />

                {/* Account label on high risk or selected */}
                {(isSelected || isHovered || n.isHighRisk) && (
                  <text
                    x={n.radius + 6}
                    y={4}
                    fill={isSelected ? "#ffffff" : n.isHighRisk ? "#f5f5f5" : "#a6a6a6"}
                    fontSize={10}
                    fontFamily="IBM Plex Mono, monospace"
                  >
                    {n.id.length > 14 ? n.id.slice(0, 12) + "…" : n.id}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Floating Hover Tooltip */}
      {hoveredNode && (
        <div
          style={{
            position: "absolute",
            bottom: 16,
            left: 16,
            background: "#171719",
            border: "1px solid #303034",
            padding: "8px 12px",
            borderRadius: 2,
            fontFamily: "IBM Plex Mono, monospace",
            fontSize: 11,
            pointerEvents: "none",
            zIndex: 10,
          }}
        >
          <div style={{ color: hoveredNode.isHighRisk ? "#e05252" : "#f5f5f5", fontWeight: 600 }}>
            Account: {hoveredNode.id}
          </div>
          <div style={{ color: "#a6a6a6" }}>
            Anomaly Score: <span style={{ color: "#fff" }}>{hoveredNode.score.toFixed(3)}</span>
          </div>
          {hoveredNode.patterns.length > 0 && (
            <div style={{ color: "#b44a50", marginTop: 4 }}>
              Patterns: {hoveredNode.patterns.join(", ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
