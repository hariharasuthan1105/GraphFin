import { useEffect, useRef, useState } from "react";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";
import type { AccountNode, TransferEdge } from "./types";

interface Props {
  accounts: AccountNode[];
  edges: TransferEdge[];
  selectedNode: string | null;
  onSelectNode: (id: string) => void;
  maxRenderNodes?: number;
}

interface SimNode extends SimulationNodeDatum {
  id: string;
  x: number;
  y: number;
  radius: number;
  score: number;
  inDegree: number;
  outDegree: number;
  isHighRisk: boolean;
  patterns: string[];
}

interface SimEdge extends SimulationLinkDatum<SimNode> {
  source: string | SimNode;
  target: string | SimNode;
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

  // Compute collision-aware d3-force layout with automatic fit-to-view bounding
  useEffect(() => {
    const activeNodes = accounts.slice(0, maxRenderNodes);
    const activeIds = new Set(activeNodes.map((a) => a.id));

    // Width and height of canvas viewport
    const W = 800;
    const H = 550;
    const cx = W / 2;
    const cy = H / 2;

    const simNodes: SimNode[] = activeNodes.map((acc, idx) => {
      const angle = (idx / activeNodes.length) * 2 * Math.PI;
      const dist = 140 + (1 - acc.anomalyScore * 0.5) * 80;
      return {
        id: acc.id,
        x: cx + Math.cos(angle) * dist,
        y: cy + Math.sin(angle) * dist,
        radius: Math.max(6, Math.min(16, 6 + Math.log10(Math.max(1, acc.totalDegree)) * 4)),
        score: acc.anomalyScore,
        inDegree: acc.inDegree,
        outDegree: acc.outDegree,
        isHighRisk: acc.anomalyScore >= 0.45 || acc.patterns.length > 0,
        patterns: acc.patterns,
      };
    });

    const activeEdges: SimEdge[] = edges
      .filter((e) => activeIds.has(e.source) && activeIds.has(e.target))
      .slice(0, 150)
      .map((e) => ({
        source: e.source,
        target: e.target,
        amount: e.amount,
        isReciprocal: e.isReciprocal,
      }));

    // Run d3-force simulation with strong collision avoidance (+24px buffer)
    const simulation = forceSimulation<SimNode>(simNodes)
      .force(
        "link",
        forceLink<SimNode, SimEdge>(activeEdges)
          .id((d) => d.id)
          .distance(120),
      )
      .force("charge", forceManyBody().strength(-350).distanceMax(550))
      .force(
        "collide",
        forceCollide<SimNode>()
          .radius((d) => d.radius + 24)
          .iterations(3),
      )
      .force("center", forceCenter(cx, cy))
      .stop();

    // Advance 180 ticks synchronously for a stable, collision-free layout
    for (let i = 0; i < 180; ++i) {
      simulation.tick();
    }

    // Auto-fit to view: calculate bounding box and center within 800x550
    if (simNodes.length > 0) {
      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity;
      let maxY = -Infinity;

      for (const n of simNodes) {
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      }

      const padding = 50;
      const spanX = Math.max(100, maxX - minX);
      const spanY = Math.max(100, maxY - minY);
      const scaleX = (W - padding * 2) / spanX;
      const scaleY = (H - padding * 2) / spanY;
      const fitScale = Math.min(1.0, Math.min(scaleX, scaleY));

      const midX = (minX + maxX) / 2;
      const midY = (minY + maxY) / 2;

      for (const n of simNodes) {
        n.x = cx + (n.x - midX) * fitScale;
        n.y = cy + (n.y - midY) * fitScale;
      }
    }

    setNodes(simNodes);
    setLinks(activeEdges);
    setZoom(1.0); // Reset to crisp 100% initial zoom
  }, [accounts, edges, maxRenderNodes]);

  return (
    <div className="analysis-graph-container" ref={containerRef} style={{ position: "relative" }}>
      {/* Horizontal Graph Controls Bar */}
      <div className="graph-controls-bar">
        <span className="eyebrow technical">
          INTERACTIVE TOPOLOGY LENS ({nodes.length} ACCOUNTS / {links.length} TRANSFERS)
        </span>
        <div className="graph-zoom-actions">
          <button
            type="button"
            className="zoom-btn"
            onClick={() => setZoom((z) => Math.max(0.6, Math.round((z - 0.2) * 10) / 10))}
            title="Zoom out"
          >
            -
          </button>
          <span className="zoom-value">{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            className="zoom-btn"
            onClick={() => setZoom((z) => Math.min(2.0, Math.round((z + 0.2) * 10) / 10))}
            title="Zoom in"
          >
            +
          </button>
          <button
            type="button"
            className="zoom-btn reset"
            onClick={() => setZoom(1.0)}
            title="Reset to 100% zoom"
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
            const u = typeof link.source === "object" ? link.source : nodes.find((n) => n.id === link.source);
            const v = typeof link.target === "object" ? link.target : nodes.find((n) => n.id === link.target);
            if (!u || !v) return null;
            const isHighRisk = u.isHighRisk || v.isHighRisk || link.isReciprocal;
            const isSelected = selectedNode === u.id || selectedNode === v.id;

            return (
              <line
                key={`link-${u.id}-${v.id}-${idx}`}
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
                    : "#2a2a2e"
                }
                strokeWidth={isSelected ? 2 : link.isReciprocal ? 1.8 : 1}
                strokeDasharray={link.isReciprocal ? "4,4" : undefined}
                markerEnd={isHighRisk ? "url(#arrow-risk)" : "url(#arrow)"}
                opacity={isSelected ? 1.0 : isHighRisk ? 0.75 : 0.45}
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
              fillColor = "#26262a";
            }

            return (
              <g
                key={`node-${n.id}`}
                transform={`translate(${n.x}, ${n.y})`}
                onClick={() => onSelectNode(n.id)}
                onMouseEnter={() => setHoveredNode(n)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: "pointer" }}
              >
                {/* Outer Glow Ring for Selected Node */}
                {isSelected && (
                  <>
                    <circle
                      r={n.radius + 9}
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth={1.5}
                      strokeDasharray="4,4"
                      opacity={0.85}
                    />
                    <circle
                      r={n.radius + 5}
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth={2}
                      opacity={0.95}
                    />
                  </>
                )}

                {/* Subtle Warning Halo for High-Risk (when not selected) */}
                {!isSelected && n.isHighRisk && (
                  <circle
                    r={n.radius + 4}
                    fill="none"
                    stroke="#c04b52"
                    strokeWidth={1}
                    opacity={0.5}
                  />
                )}

                {/* Main Node Body */}
                <circle
                  r={n.radius}
                  fill={fillColor}
                  stroke={isSelected ? "#ffffff" : n.isHighRisk ? "#e05252" : "#45454a"}
                  strokeWidth={isSelected ? 2.5 : 1}
                />

                {/* Legible Badge Label: ONLY rendered on Selected or Hovered nodes */}
                {(isSelected || isHovered) && (
                  <g transform={`translate(${n.radius + 8}, -11)`}>
                    <rect
                      x={-4}
                      y={-2}
                      width={Math.max(65, n.id.length * 7.2 + 12)}
                      height={22}
                      fill="#101012"
                      stroke={isSelected ? "#ffffff" : "#b44a50"}
                      strokeWidth={1}
                      rx={2}
                      opacity={0.95}
                    />
                    <text
                      x={3}
                      y={13}
                      fill="#ffffff"
                      fontSize={10}
                      fontFamily="IBM Plex Mono, monospace"
                      fontWeight={600}
                    >
                      {n.id}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Floating Hover Tooltip HUD */}
      {hoveredNode && (
        <div className="graph-hud-tooltip">
          <div className="graph-hud-title">ACCOUNT: {hoveredNode.id}</div>
          <div className="graph-hud-row">
            <span>Anomaly Score:</span>
            <span style={{ color: hoveredNode.isHighRisk ? "#e05252" : "#4ade80" }}>
              {hoveredNode.score.toFixed(3)}
            </span>
          </div>
          <div className="graph-hud-row">
            <span>Connections:</span>
            <span>{hoveredNode.inDegree} in / {hoveredNode.outDegree} out</span>
          </div>
          {hoveredNode.patterns.length > 0 && (
            <div className="graph-hud-patterns">
              Patterns: {hoveredNode.patterns.join(", ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
