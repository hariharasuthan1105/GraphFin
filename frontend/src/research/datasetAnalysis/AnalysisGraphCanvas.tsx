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
  modeBadge?: string;
}

interface SimNode extends SimulationNodeDatum {
  id: string;
  x: number;
  y: number;
  radius: number;
  score: number;
  inDegree: number;
  outDegree: number;
  totalDegree: number;
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
  modeBadge,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [links, setLinks] = useState<SimEdge[]>([]);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef({ x: 0, y: 0 });

  // Compute collision-aware d3-force layout with automatic fit-to-view bounding
  useEffect(() => {
    const activeNodes = accounts.slice(0, maxRenderNodes);
    const activeIds = new Set(activeNodes.map((a) => a.id));

    const W = 900;
    const H = 580;
    const cx = W / 2;
    const cy = H / 2;

    const simNodes: SimNode[] = activeNodes.map((acc, idx) => {
      const angle = (idx / activeNodes.length) * 2 * Math.PI;
      const dist = 160 + (1 - acc.anomalyScore * 0.5) * 80;
      return {
        id: acc.id,
        x: cx + Math.cos(angle) * dist,
        y: cy + Math.sin(angle) * dist,
        radius: Math.max(7, Math.min(18, 7 + Math.log10(Math.max(1, acc.totalDegree)) * 4.5)),
        score: acc.anomalyScore,
        inDegree: acc.inDegree,
        outDegree: acc.outDegree,
        totalDegree: acc.totalDegree,
        isHighRisk: acc.anomalyScore >= 0.45 || acc.patterns.length > 0,
        patterns: acc.patterns,
      };
    });

    const activeEdges: SimEdge[] = edges
      .filter((e) => activeIds.has(e.source) && activeIds.has(e.target))
      .slice(0, 180)
      .map((e) => ({
        source: e.source,
        target: e.target,
        amount: e.amount,
        isReciprocal: e.isReciprocal,
      }));

    // Run d3-force simulation with generous collision avoidance (+28px buffer)
    const simulation = forceSimulation<SimNode>(simNodes)
      .force(
        "link",
        forceLink<SimNode, SimEdge>(activeEdges)
          .id((d) => d.id)
          .distance(130),
      )
      .force("charge", forceManyBody().strength(-380).distanceMax(600))
      .force(
        "collide",
        forceCollide<SimNode>().radius((d) => d.radius + 28),
      )
      .force("center", forceCenter(cx, cy))
      .stop();

    // Run 260 iterations synchronously for instant stable placement
    for (let i = 0; i < 260; ++i) simulation.tick();

    // Fit-to-view calculation
    if (simNodes.length > 0) {
      let minX = Infinity,
        maxX = -Infinity,
        minY = Infinity,
        maxY = -Infinity;
      for (const n of simNodes) {
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      }
      const padding = 70;
      const graphW = Math.max(1, maxX - minX + padding * 2);
      const graphH = Math.max(1, maxY - minY + padding * 2);
      const midX = (minX + maxX) / 2;
      const midY = (minY + maxY) / 2;

      const scale = Math.min(1.0, W / graphW, H / graphH);
      for (const n of simNodes) {
        n.x = cx + (n.x - midX) * scale;
        n.y = cy + (n.y - midY) * scale;
      }
    }

    setNodes(simNodes);
    setLinks(activeEdges);
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  }, [accounts, edges, maxRenderNodes]);

  // Handle Pan Interaction
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).tagName === "svg" || (e.target as HTMLElement).tagName === "rect") {
      setIsPanning(true);
      panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      });
    }
  };

  const handleMouseUp = () => setIsPanning(false);

  // Semantic color selector
  const getNodeColor = (n: SimNode) => {
    if (n.score >= 0.7) return { fill: "#f43f5e", stroke: "#e11d48", label: "Critical Anomaly" };
    if (n.patterns.includes("CYCLE")) return { fill: "#a855f7", stroke: "#9333ea", label: "Cycle Node" };
    if (n.patterns.includes("FAN_OUT") || n.patterns.includes("FAN_IN"))
      return { fill: "#f59e0b", stroke: "#d97706", label: "Mule / Hub" };
    if (n.score >= 0.45) return { fill: "#fb923c", stroke: "#ea580c", label: "Suspicious" };
    return { fill: "#38bdf8", stroke: "#0284c7", label: "Standard Account" };
  };

  return (
    <div
      className="graph-canvas-container"
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{
        position: "relative",
        background: "#08090d",
        border: "1px solid #1a1e28",
        borderRadius: "6px",
        overflow: "hidden",
        width: "100%",
        height: "560px",
        cursor: isPanning ? "grabbing" : "default",
      }}
    >
      {/* Top Bar: Controls + Scope Tag */}
      <div
        style={{
          position: "absolute",
          top: "12px",
          left: "14px",
          right: "14px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 10,
          pointerEvents: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {modeBadge && (
            <span
              style={{
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: "10px",
                letterSpacing: "0.08em",
                fontWeight: 600,
                padding: "3px 8px",
                borderRadius: "3px",
                background: "#12151e",
                border: "1px solid #283144",
                color: "#38bdf8",
              }}
            >
              {modeBadge}
            </span>
          )}
          <span
            style={{
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: "11px",
              color: "#64748b",
            }}
          >
            {nodes.length} accounts · {links.length} transfers
          </span>
        </div>

        {/* Zoom & Reset Toolbar */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            background: "#0e111a",
            border: "1px solid #1e2434",
            borderRadius: "4px",
            padding: "2px",
            pointerEvents: "auto",
          }}
        >
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.4, Number((z - 0.15).toFixed(2))))}
            aria-label="Zoom out"
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              padding: "4px 8px",
              fontSize: "12px",
              fontFamily: "monospace",
              borderRadius: "3px",
            }}
          >
            -
          </button>
          <span
            style={{
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: "10px",
              color: "#e2e8f0",
              minWidth: "42px",
              textAlign: "center",
            }}
          >
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(2.5, Number((z + 0.15).toFixed(2))))}
            aria-label="Zoom in"
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              padding: "4px 8px",
              fontSize: "12px",
              fontFamily: "monospace",
              borderRadius: "3px",
            }}
          >
            +
          </button>
          <button
            type="button"
            onClick={() => {
              setZoom(1.0);
              setPan({ x: 0, y: 0 });
            }}
            aria-label="Reset zoom and pan"
            style={{
              background: "#161b26",
              border: "1px solid #252e42",
              color: "#38bdf8",
              cursor: "pointer",
              padding: "3px 8px",
              fontSize: "10px",
              fontFamily: "IBM Plex Mono, monospace",
              borderRadius: "3px",
              marginLeft: "4px",
            }}
          >
            RESET
          </button>
        </div>
      </div>

      {/* SVG Canvas */}
      <svg
        viewBox="0 0 900 580"
        style={{ width: "100%", height: "100%", display: "block" }}
      >
        <defs>
          <marker
            id="arrow-norm"
            viewBox="0 0 10 10"
            refX="17"
            refY="5"
            markerWidth="4.5"
            markerHeight="4.5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#334155" />
          </marker>
          <marker
            id="arrow-amber"
            viewBox="0 0 10 10"
            refX="18"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#f59e0b" />
          </marker>
          <marker
            id="arrow-violet"
            viewBox="0 0 10 10"
            refX="18"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#a855f7" />
          </marker>
          <marker
            id="arrow-risk"
            viewBox="0 0 10 10"
            refX="19"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#f43f5e" />
          </marker>
        </defs>

        {/* Pan & Zoom Transform Container */}
        <g
          transform={`translate(${pan.x + 450 * (1 - zoom)}, ${
            pan.y + 290 * (1 - zoom)
          }) scale(${zoom})`}
        >
          {/* Edges */}
          {links.map((link, idx) => {
            const u =
              typeof link.source === "object"
                ? link.source
                : nodes.find((n) => n.id === link.source);
            const v =
              typeof link.target === "object"
                ? link.target
                : nodes.find((n) => n.id === link.target);
            if (!u || !v) return null;

            const isSelected = selectedNode === u.id || selectedNode === v.id;
            const isHighRisk = u.isHighRisk && v.isHighRisk;
            const isReciprocal = link.isReciprocal;

            let strokeColor = "#1e293b";
            let marker = "url(#arrow-norm)";
            let strokeWidth = 1.2;

            if (isSelected) {
              strokeColor = "#38bdf8";
              marker = "url(#arrow-norm)";
              strokeWidth = 2.2;
            } else if (isHighRisk) {
              strokeColor = "#f43f5e";
              marker = "url(#arrow-risk)";
              strokeWidth = 1.8;
            } else if (isReciprocal) {
              strokeColor = "#a855f7";
              marker = "url(#arrow-violet)";
              strokeWidth = 1.6;
            } else if (u.patterns.length > 0 || v.patterns.length > 0) {
              strokeColor = "#f59e0b";
              marker = "url(#arrow-amber)";
              strokeWidth = 1.4;
            }

            return (
              <line
                key={`link-${u.id}-${v.id}-${idx}`}
                x1={u.x}
                y1={u.y}
                x2={v.x}
                y2={v.y}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
                strokeDasharray={isReciprocal ? "4,4" : undefined}
                markerEnd={marker}
                opacity={isSelected ? 1.0 : isHighRisk ? 0.85 : 0.55}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((n) => {
            const isSelected = selectedNode === n.id;
            const isHovered = hoveredNode?.id === n.id;
            const style = getNodeColor(n);

            return (
              <g
                key={`node-${n.id}`}
                transform={`translate(${n.x}, ${n.y})`}
                onClick={() => onSelectNode(n.id)}
                onMouseEnter={() => setHoveredNode(n)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: "pointer" }}
              >
                {/* Glow Ring for Selected Node */}
                {isSelected && (
                  <>
                    <circle
                      r={n.radius + 10}
                      fill="none"
                      stroke="#00f0ff"
                      strokeWidth={1.5}
                      strokeDasharray="4,4"
                      opacity={0.8}
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

                {/* Warning Pulse for High Risk */}
                {!isSelected && n.isHighRisk && (
                  <circle
                    r={n.radius + 4}
                    fill="none"
                    stroke={style.fill}
                    strokeWidth={1}
                    opacity={0.4}
                  />
                )}

                {/* Node Circle */}
                <circle
                  r={n.radius}
                  fill={style.fill}
                  stroke={isSelected ? "#ffffff" : style.stroke}
                  strokeWidth={isSelected ? 2.5 : 1.2}
                  opacity={0.95}
                />

                {/* Badge Label: only for Selected or Hovered nodes */}
                {(isSelected || isHovered) && (
                  <g transform={`translate(${n.radius + 8}, -11)`}>
                    <rect
                      x={-4}
                      y={-2}
                      width={Math.max(70, n.id.length * 7.5 + 16)}
                      height={24}
                      fill="#0d1017"
                      stroke={isSelected ? "#00f0ff" : style.stroke}
                      strokeWidth={1}
                      rx={3}
                      opacity={0.95}
                    />
                    <text
                      x={4}
                      y={14}
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
        <div
          style={{
            position: "absolute",
            bottom: "16px",
            right: "16px",
            background: "rgba(10, 13, 20, 0.95)",
            border: "1px solid #1f2738",
            borderRadius: "6px",
            padding: "10px 14px",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
            pointerEvents: "none",
            zIndex: 20,
            maxWidth: "260px",
          }}
        >
          <div
            style={{
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: "11px",
              fontWeight: 700,
              color: "#38bdf8",
              marginBottom: "6px",
            }}
          >
            ACCOUNT: {hoveredNode.id}
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "11px",
              color: "#94a3b8",
              marginBottom: "3px",
            }}
          >
            <span>Anomaly Risk:</span>
            <span
              style={{
                fontFamily: "IBM Plex Mono, monospace",
                fontWeight: 600,
                color: hoveredNode.isHighRisk ? "#f43f5e" : "#10b981",
              }}
            >
              {(hoveredNode.score * 100).toFixed(1)}%
            </span>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "11px",
              color: "#94a3b8",
              marginBottom: "4px",
            }}
          >
            <span>Topology Degree:</span>
            <span style={{ fontFamily: "IBM Plex Mono, monospace", color: "#e2e8f0" }}>
              {hoveredNode.inDegree} in / {hoveredNode.outDegree} out
            </span>
          </div>
          {hoveredNode.patterns.length > 0 && (
            <div style={{ marginTop: "4px", display: "flex", gap: "4px", flexWrap: "wrap" }}>
              {hoveredNode.patterns.map((p) => (
                <span
                  key={p}
                  style={{
                    fontSize: "9px",
                    fontFamily: "IBM Plex Mono, monospace",
                    padding: "2px 5px",
                    background: "#2a151b",
                    color: "#f43f5e",
                    border: "1px solid #4c1d24",
                    borderRadius: "2px",
                  }}
                >
                  {p}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Semantic Legend Bar (Bottom Left) */}
      <div
        style={{
          position: "absolute",
          bottom: "12px",
          left: "14px",
          display: "flex",
          gap: "12px",
          alignItems: "center",
          background: "rgba(10, 13, 20, 0.85)",
          padding: "5px 10px",
          borderRadius: "4px",
          border: "1px solid #1a202c",
          fontSize: "10px",
          fontFamily: "IBM Plex Mono, monospace",
          color: "#94a3b8",
          zIndex: 10,
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <span
            style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#38bdf8" }}
          />
          Standard
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <span
            style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#f59e0b" }}
          />
          Mule / Hub
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <span
            style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#a855f7" }}
          />
          Cycle
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <span
            style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#f43f5e" }}
          />
          Anomaly
        </span>
      </div>
    </div>
  );
}

export default AnalysisGraphCanvas;
