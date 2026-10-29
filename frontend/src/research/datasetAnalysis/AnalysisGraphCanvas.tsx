import { useMemo, useRef, useState } from "react";
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
  preset?: string;
  maxRenderNodes?: number;
  modeBadge?: string;
}

interface SimNode extends SimulationNodeDatum {
  id: string;
  x: number;
  y: number;
  radius: number;
  score: number;
  uniqueInDegree?: number;
  uniqueOutDegree?: number;
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
  preset,
  maxRenderNodes = 60,
  modeBadge,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef({ x: 0, y: 0 });

  // Compute collision-aware layout with structured preset geometries and automatic fit-to-view
  const {nodes, links} = useMemo(() => {
    const activeNodes = accounts.slice(0, maxRenderNodes);
    const activeIds = new Set(activeNodes.map((a) => a.id));

    const W = 900;
    const H = 580;
    const cx = W / 2;
    const cy = H / 2;

    // Structured geometric initial positions based on AML preset
    const simNodes: SimNode[] = activeNodes.map((acc, idx) => {
      let initX = cx;
      let initY = cy;

      if (preset === "mule-ring") {
        if (idx === 0) {
          // Source origin on left
          initX = cx - 220;
          initY = cy;
        } else if (idx <= 8) {
          // Ring of mule intermediaries in center
          const angle = ((idx - 1) / 8) * 2 * Math.PI;
          initX = cx - 20 + Math.cos(angle) * 120;
          initY = cy + Math.sin(angle) * 120;
        } else if (idx <= 10) {
          // Offshore collection sinks on right
          initX = cx + 220;
          initY = cy + (idx === 9 ? -70 : 70);
        } else {
          // Background counterparties on periphery
          const angle = (idx / activeNodes.length) * 2 * Math.PI;
          initX = cx + Math.cos(angle) * 220;
          initY = cy + Math.sin(angle) * 170;
        }
      } else if (preset === "ponzi-cycle") {
        if (acc.patterns.includes("CYCLE") || idx < 4) {
          // Central directed cycle ring
          const angle = (idx / 4) * 2 * Math.PI;
          initX = cx + Math.cos(angle) * 100;
          initY = cy + Math.sin(angle) * 100;
        } else {
          // Peripheral wash traders radiating outward
          const angle = (idx / activeNodes.length) * 2 * Math.PI;
          initX = cx + Math.cos(angle) * 210;
          initY = cy + Math.sin(angle) * 180;
        }
      } else if (preset === "smurfing-fanout") {
        if (idx === 0) {
          // Central Treasury Hub
          initX = cx;
          initY = cy;
        } else {
          // Structured radial fan-out
          const angle = ((idx - 1) / (activeNodes.length - 1)) * 2 * Math.PI;
          initX = cx + Math.cos(angle) * 180;
          initY = cy + Math.sin(angle) * 180;
        }
      } else if (preset === "fanin-aggregation") {
        if (idx === 0) {
          // Central Aggregator / Exit
          initX = cx;
          initY = cy;
        } else if (idx <= 5) {
          // Layer 1 collection
          const angle = ((idx - 1) / 5) * 2 * Math.PI;
          initX = cx + Math.cos(angle) * 110;
          initY = cy + Math.sin(angle) * 110;
        } else {
          // Outer feeder ring
          const angle = ((idx - 6) / (activeNodes.length - 6)) * 2 * Math.PI;
          initX = cx + Math.cos(angle) * 210;
          initY = cy + Math.sin(angle) * 200;
        }
      } else {
        // General uploaded graph: balanced radial dispersion
        const angle = (idx / activeNodes.length) * 2 * Math.PI;
        const dist = 140 + (1 - acc.anomalyScore * 0.4) * 80;
        initX = cx + Math.cos(angle) * dist;
        initY = cy + Math.sin(angle) * dist;
      }

      return {
        id: acc.id,
        x: initX,
        y: initY,
        radius: Math.max(7, Math.min(18, 7 + Math.log10(Math.max(1, acc.totalDegree)) * 4.5)),
        score: acc.anomalyScore,
        uniqueInDegree: acc.uniqueInDegree,
        uniqueOutDegree: acc.uniqueOutDegree,
        inDegree: acc.inDegree,
        outDegree: acc.outDegree,
        totalDegree: acc.totalDegree,
        isHighRisk: acc.isFlaggedForReview ?? acc.anomalyScore >= 0.6,
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

    // Run d3-force with strong collision avoidance (+32px buffer) and repulsion
    const simulation = forceSimulation<SimNode>(simNodes)
      .force(
        "link",
        forceLink<SimNode, SimEdge>(activeEdges)
          .id((d) => d.id)
          .distance(preset ? 110 : 130),
      )
      .force("charge", forceManyBody().strength(preset ? -320 : -420).distanceMax(650))
      .force(
        "collide",
        forceCollide<SimNode>().radius((d) => d.radius + 32),
      )
      .force("center", forceCenter(cx, cy))
      .stop();

    // Run 280 iterations for stable node placement
    for (let i = 0; i < 280; ++i) simulation.tick();

    // Automatic fit-to-view bounding calculation
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

    return {nodes: simNodes, links: activeEdges};
  }, [accounts, edges, preset, maxRenderNodes]);

  const [previousLayout, setPreviousLayout] = useState(nodes);
  if (previousLayout !== nodes) {
    setPreviousLayout(nodes);
    setZoom(1);
    setPan({x: 0, y: 0});
    setHoveredNode(null);
  }

  // Handle Pan Drag
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

  // Original GraphFin Semantic Colors (Black / White / Red)
  const getNodeColor = (n: SimNode) => {
    if (n.isHighRisk && n.score >= 0.7) {
      return { fill: "#ef4444", stroke: "#b91c1c", label: "Critical Anomaly" };
    }
    if (n.isHighRisk) {
      return { fill: "#b44a50", stroke: "#842d35", label: "Flagged for review (heuristic)" };
    }
    return { fill: "#e5e7eb", stroke: "#9ca3af", label: "Standard Account" };
  };

  // Top 3 anomalies to optionally show badges for when unselected
  const topAnomalyIds = new Set(
    [...nodes]
      .filter((n) => n.isHighRisk)
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map((n) => n.id),
  );

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
        background: "radial-gradient(ellipse at 50% 45%, #191724, #06090f 72%)",
        border: "1px solid #303034",
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
                background: "#171719",
                border: "1px solid #303034",
                color: "#f5f5f5",
              }}
            >
              <b style={{ color: "#c04b52" }}>●</b> {modeBadge}
            </span>
          )}
          <span
            style={{
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: "11px",
              color: "#77777d",
            }}
          >
            {nodes.length} / {accounts.length} accounts · {links.length} displayed edges
          </span>
        </div>

        {/* Zoom & Reset Toolbar */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "3px",
            background: "#101012",
            border: "1px solid #303034",
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
              color: "#a6a6a6",
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
              color: "#f5f5f5",
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
              color: "#a6a6a6",
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
              background: "#171719",
              border: "1px solid #303034",
              color: "#ffffff",
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

      {accounts.length > nodes.length && <span className="graph-scope">Bounded view: first {maxRenderNodes} matching accounts. Scores use the full accepted graph.</span>}
      {/* SVG Canvas */}
      <svg
        viewBox="0 0 900 580"
        style={{ width: "100%", height: "100%", display: "block" }}
      >
        <defs>
          <radialGradient id="node-neutral" cx="30%" cy="25%"><stop offset="0" stopColor="#ffffff"/><stop offset=".45" stopColor="#aabacb"/><stop offset="1" stopColor="#263446"/></radialGradient>
          <radialGradient id="node-alert" cx="30%" cy="25%"><stop offset="0" stopColor="#ffb6bc"/><stop offset=".45" stopColor="#ff334d"/><stop offset="1" stopColor="#720f28"/></radialGradient>
          {/* Subtle grid pattern */}
          <pattern id="graph-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#141416" strokeWidth="0.8" />
          </pattern>

          {/* Directional arrowheads */}
          <marker
            id="arrow-gray"
            viewBox="0 0 10 10"
            refX="17"
            refY="5"
            markerWidth="4.5"
            markerHeight="4.5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#4a4a52" />
          </marker>
          <marker
            id="arrow-red"
            viewBox="0 0 10 10"
            refX="18"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#842d35" />
          </marker>
          <marker
            id="arrow-alert"
            viewBox="0 0 10 10"
            refX="19"
            refY="5"
            markerWidth="5.5"
            markerHeight="5.5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#ef4444" />
          </marker>
        </defs>

        {/* Background Grid */}
        <rect width="100%" height="100%" fill="url(#graph-grid)" />

        {/* Pan & Zoom Transform Container */}
        <g className="graph-camera"
          transform={`translate(${pan.x + 450 * (1 - zoom)}, ${
            pan.y + 290 * (1 - zoom)
          }) scale(${zoom})`}
        >
          {/* Directed Edges */}
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

            const isConnectedToSelected = selectedNode === u.id || selectedNode === v.id;
            const isSuspiciousEdge = u.isHighRisk || v.isHighRisk;
            const isCriticalEdge = u.score >= 0.7 && v.score >= 0.7;

            let strokeColor = "#383840";
            let marker = "url(#arrow-gray)";
            let strokeWidth = 1.2;
            let opacity = 0.55;

            if (selectedNode) {
              if (isConnectedToSelected) {
                strokeColor = "#ef4444";
                marker = "url(#arrow-alert)";
                strokeWidth = 2.2;
                opacity = 1.0;
              } else {
                opacity = 0.15; // Dim non-connected edges to focus on selected account's counterparties
              }
            } else if (isCriticalEdge) {
              strokeColor = "#ef4444";
              marker = "url(#arrow-alert)";
              strokeWidth = 1.8;
              opacity = 0.9;
            } else if (isSuspiciousEdge) {
              strokeColor = "#842d35";
              marker = "url(#arrow-red)";
              strokeWidth = 1.5;
              opacity = 0.75;
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
                markerEnd={marker}
                opacity={opacity}
              />
            );
          })}

          {/* Account Nodes */}
          {nodes.map((n) => {
            const isSelected = selectedNode === n.id;
            const isHovered = hoveredNode?.id === n.id;
            const style = getNodeColor(n);
            const showBadge = isSelected || isHovered || (!selectedNode && topAnomalyIds.has(n.id));

            return (
              <g
                key={`node-${n.id}`}
                transform={`translate(${n.x}, ${n.y})`}
                role="button" tabIndex={0} aria-label={'Inspect account ' + n.id} aria-pressed={isSelected}
                onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelectNode(n.id); } }}
                onClick={() => onSelectNode(n.id)}
                onMouseEnter={() => setHoveredNode(n)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: "pointer" }}
              >
                {/* Selection Rings */}
                {isSelected && (
                  <>
                    <circle
                      r={n.radius + 10}
                      fill="none"
                      stroke="#c04b52"
                      strokeWidth={1.5}
                      strokeDasharray="4,4"
                      opacity={0.8}
                    />
                    <circle
                      r={n.radius + 4}
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth={2.2}
                      opacity={0.95}
                    />
                  </>
                )}

                {/* Warning Pulse for High Risk Anomalies */}
                {!isSelected && n.score >= 0.7 && (
                  <circle
                    r={n.radius + 5}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth={1}
                    opacity={0.45}
                  />
                )}

                {/* Core Node Circle */}
                <circle
                  r={n.radius}
                  fill={n.isHighRisk ? "url(#node-alert)" : "url(#node-neutral)"}
                  stroke={isSelected ? "#ffffff" : style.stroke}
                  strokeWidth={isSelected ? 2.5 : 1.2}
                  opacity={0.95}
                />

                {/* Clean Label: Only for Hovered, Selected, or Top 3 Anomalies */}
                {showBadge && (
                  <g transform={`translate(${n.radius + 8}, -11)`}>
                    <rect
                      x={-4}
                      y={-2}
                      width={Math.max(65, n.id.length * 7.2 + 14)}
                      height={22}
                      fill="#101012"
                      stroke={isSelected ? "#ffffff" : n.score >= 0.7 ? "#ef4444" : "#303034"}
                      strokeWidth={1}
                      rx={3}
                      opacity={0.96}
                    />
                    <text
                      x={4}
                      y={13}
                      fill={isSelected ? "#ffffff" : n.score >= 0.7 ? "#fca5a5" : "#e5e7eb"}
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
            background: "rgba(16, 16, 18, 0.96)",
            border: "1px solid #b44a50",
            borderRadius: "6px",
            padding: "10px 14px",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.7)",
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
              color: "#ffffff",
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
              color: "#a6a6a6",
              marginBottom: "3px",
            }}
          >
            <span>Anomaly Risk:</span>
            <span
              style={{
                fontFamily: "IBM Plex Mono, monospace",
                fontWeight: 600,
                color: hoveredNode.score >= 0.7 ? "#ef4444" : hoveredNode.score >= 0.45 ? "#b44a50" : "#f5f5f5",
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
              color: "#a6a6a6",
              marginBottom: "4px",
            }}
          >
            <span>Transactions:</span>
            <span style={{ fontFamily: "IBM Plex Mono, monospace", color: "#f5f5f5" }}>
              {hoveredNode.inDegree} in / {hoveredNode.outDegree} out; unique neighbors {hoveredNode.uniqueInDegree ?? "N/A"} in / {hoveredNode.uniqueOutDegree ?? "N/A"} out
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
                    background: "rgba(180, 74, 80, 0.2)",
                    color: "#fca5a5",
                    border: "1px solid #b44a50",
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
          background: "rgba(16, 16, 18, 0.92)",
          padding: "5px 10px",
          borderRadius: "4px",
          border: "1px solid #303034",
          fontSize: "10px",
          fontFamily: "IBM Plex Mono, monospace",
          color: "#a6a6a6",
          zIndex: 10,
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <span
            style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#e5e7eb", border: "1px solid #9ca3af" }}
          />
          Standard
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <span
            style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#b44a50", border: "1px solid #842d35" }}
          />
          Suspicious
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <span
            style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#ef4444", border: "1px solid #b91c1c" }}
          />
          Critical Anomaly
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <span
            style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#ef4444", border: "2px solid #ffffff" }}
          />
          Selected
        </span>
      </div>
    </div>
  );
}

export default AnalysisGraphCanvas;
