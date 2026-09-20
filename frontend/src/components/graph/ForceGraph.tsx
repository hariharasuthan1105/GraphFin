import React, { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3-force";
import { NetworkEdge, NetworkNode } from "../../types/api";

interface ForceGraphProps {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  selectedNodeId?: string | null;
  onNodeClick?: (nodeId: string) => void;
  className?: string;
}

interface SimulationNode extends d3.SimulationNodeDatum {
  id: string;
  degree: number;
  status: "suspicious" | "normal" | "unscored";
  risk_score?: number;
  in_degree?: number;
  out_degree?: number;
}

interface SimulationLink extends d3.SimulationLinkDatum<SimulationNode> {
  source: string | SimulationNode;
  target: string | SimulationNode;
  amount: number;
  count: number;
}

export const ForceGraph: React.FC<ForceGraphProps> = ({
  nodes,
  edges,
  selectedNodeId,
  onNodeClick,
  className = "",
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const [hoveredNode, setHoveredNode] = useState<SimulationNode | null>(null);
  const [simNodes, setSimNodes] = useState<SimulationNode[]>([]);
  const [simLinks, setSimLinks] = useState<SimulationLink[]>([]);

  // Pan and zoom transform
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  // Update container dimensions on resize
  useEffect(() => {
    if (!containerRef.current) return;
    const updateSize = () => {
      if (containerRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        setDimensions({
          width: clientWidth || 800,
          height: clientHeight || 500,
        });
      }
    };
    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Compute max amount and max degree for scaling
  const { maxAmount, maxDegree } = useMemo(() => {
    let maxA = 1;
    edges.forEach((e) => {
      if (e.amount > maxA) maxA = e.amount;
    });

    let maxD = 1;
    nodes.forEach((n) => {
      const d = n.degree || 1;
      if (d > maxD) maxD = d;
    });

    return { maxAmount: maxA, maxDegree: maxD };
  }, [nodes, edges]);

  // Run d3-force physics simulation on data/dimension change
  useEffect(() => {
    if (nodes.length === 0) {
      setSimNodes([]);
      setSimLinks([]);
      return;
    }

    const { width, height } = dimensions;

    // Create shallow copies for simulation
    const simulationNodes: SimulationNode[] = nodes.map((n) => ({
      ...n,
      degree: n.degree || 1,
      status: n.status || "unscored",
      x: n.x ?? width / 2 + (Math.random() - 0.5) * 160,
      y: n.y ?? height / 2 + (Math.random() - 0.5) * 160,
    }));

    const nodeMap = new Map(simulationNodes.map((n) => [n.id, n]));

    // Filter valid edges whose endpoints exist
    const simulationLinks: SimulationLink[] = edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        amount: e.amount,
        count: e.count,
      }));

    const simulation = d3
      .forceSimulation<SimulationNode>(simulationNodes)
      .force(
        "link",
        d3
          .forceLink<SimulationNode, SimulationLink>(simulationLinks)
          .id((d) => d.id)
          .distance(75)
      )
      .force("charge", d3.forceManyBody().strength(-180))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collide",
        d3.forceCollide<SimulationNode>().radius((d) => {
          const r = 6 + (Math.sqrt(d.degree) / Math.sqrt(maxDegree)) * 12;
          return r + 8;
        })
      )
    // Alpha decay for deliberate, smooth settling
    simulation.alphaDecay(0.03);

    // Throttle React state updates during force layout simulation
    // Eliminates ~300 full tree reconciliations during settling
    let animFrameId: number | null = null;
    let lastRenderTime = 0;
    const MIN_FRAME_INTERVAL_MS = 33; // ~30 fps cap for layout animation

    const commitState = () => {
      setSimNodes([...simulationNodes]);
      setSimLinks([...simulationLinks]);
      animFrameId = null;
    };

    simulation.on("tick", () => {
      const now = performance.now();
      if (now - lastRenderTime >= MIN_FRAME_INTERVAL_MS) {
        lastRenderTime = now;
        if (!animFrameId) {
          animFrameId = requestAnimationFrame(commitState);
        }
      }
    });

    simulation.on("end", () => {
      if (animFrameId) {
        cancelAnimationFrame(animFrameId);
        animFrameId = null;
      }
      commitState();
    });

    return () => {
      simulation.stop();
      if (animFrameId) {
        cancelAnimationFrame(animFrameId);
      }
    };
  }, [nodes, edges, dimensions, maxDegree]);

  // Mouse pan and zoom handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    isDraggingRef.current = true;
    dragStartRef.current = {
      x: e.clientX - transform.x,
      y: e.clientY - transform.y,
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current) return;
    setTransform((prev) => ({
      ...prev,
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y,
    }));
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setTransform((prev) => {
      const newScale = Math.min(Math.max(0.3, prev.scale * zoomFactor), 4);
      return { ...prev, scale: newScale };
    });
  };

  const handleResetZoom = () => {
    setTransform({ x: 0, y: 0, scale: 1 });
  };

  // Node radius helper
  const getNodeRadius = (degree: number) => {
    return 6 + (Math.sqrt(degree) / Math.sqrt(maxDegree)) * 10;
  };

  // Node color helper based on design tokens
  const getNodeFill = (status: string, isSelected: boolean) => {
    if (isSelected) return "#78A9FF"; // --accent-graph highlight
    if (status === "suspicious") return "#FA4D56"; // --status-suspicious
    if (status === "normal") return "#42BE65"; // --status-normal
    return "#5A6672"; // --text-tertiary for unscored
  };

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full bg-canvas overflow-hidden select-none cursor-grab active:cursor-grabbing border-0 ${className}`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Zoom controls overlay */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 glass-panel p-1 rounded">
        <button
          onClick={() => setTransform((t) => ({ ...t, scale: Math.min(4, t.scale * 1.2) }))}
          className="px-2 py-1 text-xs font-mono text-text-secondary hover:text-text-primary hover:bg-surface-raised rounded transition-colors"
          title="Zoom in"
        >
          +
        </button>
        <button
          onClick={() => setTransform((t) => ({ ...t, scale: Math.max(0.3, t.scale * 0.8) }))}
          className="px-2 py-1 text-xs font-mono text-text-secondary hover:text-text-primary hover:bg-surface-raised rounded transition-colors"
          title="Zoom out"
        >
          −
        </button>
        <button
          onClick={handleResetZoom}
          className="px-2 py-1 text-xs font-mono text-text-secondary hover:text-text-primary hover:bg-surface-raised rounded transition-colors"
          title="Reset pan & zoom"
        >
          Reset
        </button>
      </div>

      {/* SVG Canvas */}
      <svg
        width={dimensions.width}
        height={dimensions.height}
        className="w-full h-full block"
      >
        <defs>
          {/* Directed edge arrowhead */}
          <marker
            id="edge-arrow"
            viewBox="0 -5 10 10"
            refX="16"
            refY="0"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M0,-4L8,0L0,4" fill="#232B33" />
          </marker>
          <marker
            id="edge-arrow-highlight"
            viewBox="0 -5 10 10"
            refX="16"
            refY="0"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M0,-4L8,0L0,4" fill="#4589FF" />
          </marker>

          {/* Radial soft glow for suspicious nodes (data-encoding depth device) */}
          <filter id="suspicious-glow" x="-60%" y="-60%" width="220%" height="220%">
            <feDropShadow dx="0" dy="0" stdDeviation="4.5" floodColor="#FA4D56" floodOpacity="0.55" />
          </filter>
        </defs>

        <g
          transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}
        >
          {/* Edges */}
          {simLinks.map((link, idx) => {
            const sourceNode = typeof link.source === "object" ? link.source : null;
            const targetNode = typeof link.target === "object" ? link.target : null;

            if (!sourceNode || !targetNode || sourceNode.x === undefined || targetNode.x === undefined) {
              return null;
            }

            const isIncident =
              sourceNode.id === selectedNodeId || targetNode.id === selectedNodeId;

            // Stroke thickness proportional to amount
            const strokeWidth = Math.min(
              5,
              Math.max(1, (link.amount / (maxAmount || 1)) * 4 + 1)
            );

            return (
              <line
                key={`edge-${idx}`}
                x1={sourceNode.x}
                y1={sourceNode.y}
                x2={targetNode.x}
                y2={targetNode.y}
                stroke={isIncident ? "#4589FF" : "#232B33"}
                strokeWidth={isIncident ? strokeWidth + 1 : strokeWidth}
                strokeOpacity={isIncident ? 0.9 : 0.6}
                markerEnd={isIncident ? "url(#edge-arrow-highlight)" : "url(#edge-arrow)"}
              />
            );
          })}

          {/* Nodes */}
          {simNodes.map((node) => {
            if (node.x === undefined || node.y === undefined) return null;
            const isSelected = node.id === selectedNodeId;
            const radius = getNodeRadius(node.degree);
            const fill = getNodeFill(node.status, isSelected);

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                className="cursor-pointer group"
                onClick={(e) => {
                  e.stopPropagation();
                  onNodeClick && onNodeClick(node.id);
                }}
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
              >
                {/* Highlight ring if selected */}
                {isSelected && (
                  <circle
                    r={radius + 5}
                    fill="none"
                    stroke="#4589FF"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                    className="animate-spin-slow"
                  />
                )}

                {/* Node body with soft radial glow for suspicious status */}
                <circle
                  r={radius}
                  fill={fill}
                  stroke="#12181F"
                  strokeWidth="2"
                  filter={node.status === "suspicious" ? "url(#suspicious-glow)" : undefined}
                  style={{
                    filter:
                      node.status === "suspicious"
                        ? "drop-shadow(0 0 8px rgba(250, 77, 86, 0.45))"
                        : undefined,
                  }}
                  className="transition-transform duration-100 group-hover:scale-125"
                />

                {/* Node ID label */}
                <text
                  dy={radius + 12}
                  textAnchor="middle"
                  className="text-[10px] font-mono fill-text-secondary select-none pointer-events-none tracking-tight"
                >
                  {node.id}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Hover tooltip */}
      {hoveredNode && (
        <div
          className="absolute pointer-events-none z-20 glass-panel p-2.5 rounded text-left shadow-lg text-xs font-sans max-w-xs"
          style={{ bottom: "16px", left: "16px" }}
        >
          <div className="font-mono font-medium text-text-primary text-xs mb-1">
            {hoveredNode.id}
          </div>
          <div className="space-y-0.5 text-text-secondary text-[11px]">
            <div className="flex justify-between gap-4">
              <span>Status:</span>
              <span
                className={`font-mono font-medium ${
                  hoveredNode.status === "suspicious"
                    ? "text-status-suspicious"
                    : hoveredNode.status === "normal"
                    ? "text-status-normal"
                    : "text-text-tertiary"
                }`}
              >
                {hoveredNode.status}
              </span>
            </div>
            {hoveredNode.risk_score !== undefined && (
              <div className="flex justify-between gap-4">
                <span>Risk score:</span>
                <span className="font-mono text-text-primary">
                  {hoveredNode.risk_score.toFixed(1)}
                </span>
              </div>
            )}
            <div className="flex justify-between gap-4">
              <span>Degree:</span>
              <span className="font-mono text-text-primary">
                {hoveredNode.degree}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Legend overlay */}
      <div className="absolute bottom-3 right-3 z-10 glass-panel px-3 py-2 rounded text-[11px] font-sans text-text-secondary flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-status-suspicious" />
          <span>Suspicious</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-status-normal" />
          <span>Normal</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-text-tertiary" />
          <span>Unscored</span>
        </div>
      </div>
    </div>
  );
};
