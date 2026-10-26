import { useCallback, useEffect, useRef, useState } from "react";
import type { GraphNeighborhood } from "./contract";
import { validOutput, type Point, type LayoutInput } from "./layout-contract";
type Geometry = { nodes: Map<string, Point>; layoutMs: number; workerReadyMs: number };
type Props = {
  data: GraphNeighborhood;
  selected: string;
  onNode: (ref: string) => void;
  onEdge: (ref: string) => void;
};
export default function GraphCanvas(props: Props) {
  const [layout, setLayout] = useState<{
    data: GraphNeighborhood;
    geometry?: Geometry;
    error?: string;
  }>();
  useEffect(() => {
    const started = performance.now();
    const input: LayoutInput = {
      nodes: props.data.nodes.map(({ node_ref, in_degree, out_degree }) => ({ node_ref, in_degree, out_degree })),
      edges: props.data.edges.map(({ source_ref, target_ref }) => ({ source_ref, target_ref })),
    };
    const worker = new Worker(new URL("./layout.worker.ts", import.meta.url), {
      type: "module",
    });
    let active = true;
    worker.onmessage = (
      event: MessageEvent<{
        nodes?: Point[];
        layoutMs?: number;
        error?: string;
      }>,
    ) => {
      if (active) {
        const value = event.data;
        setLayout(
          !validOutput(value, input)
            ? { data: props.data, error: "Graph layout unavailable. Use the account and relationship lists below." }
            : {
                data: props.data,
                geometry: {
                  nodes: new Map(value.nodes!.map((n) => [n.id, n])),
                  layoutMs: value.layoutMs!,
                  workerReadyMs: performance.now() - started,
                },
              },
        );
      }
      worker.terminate();
    };
    worker.onerror = () => {
      if (active)
        setLayout({
          data: props.data,
          error:
            "Graph layout unavailable. Use the account and relationship lists below.",
        });
      worker.terminate();
    };
    worker.postMessage(input);
    return () => {
      active = false;
      worker.terminate();
    };
  }, [props.data]);
  if (!layout || layout.data !== props.data)
    return (
      <div className="graph-layout-loading" role="status">
        Preparing the bounded network layout…
      </div>
    );
  if (!layout.geometry)
    return (
      <div className="graph-empty" role="alert">
        {layout.error}
      </div>
    );
  return <PositionedGraph {...props} geometry={layout.geometry} />;
}
function PositionedGraph({
  data,
  selected,
  onNode,
  onEdge,
  geometry,
}: Props & { geometry: Geometry }) {
  const svg = useRef<SVGSVGElement>(null);
  const group = useRef<SVGGElement>(null);
  const view = useRef({ x: 0, y: 0, k: 1 });
  const drag = useRef<{ x: number; y: number; vx: number; vy: number } | null>(
    null,
  );
  const frame = useRef<number | undefined>(undefined);
  const zoomText = useRef<HTMLSpanElement>(null);
  const setZoom = useCallback((value: number) => {
    if (zoomText.current) zoomText.current.textContent = value + "%";
  }, []);
  const paint = useCallback(() => {
    group.current?.setAttribute(
      "transform",
      `translate(${view.current.x} ${view.current.y}) scale(${view.current.k})`,
    );
  }, []);
  function schedule() {
    if (frame.current === undefined)
      frame.current = requestAnimationFrame(() => {
        paint();
        frame.current = undefined;
      });
  }
  const scale = useCallback(
    (factor: number) => {
      const v = view.current;
      const next = Math.min(5, Math.max(0.2, v.k * factor));
      v.x = 500 - ((500 - v.x) * next) / v.k;
      v.y = 310 - ((310 - v.y) * next) / v.k;
      v.k = next;
      paint();
      setZoom(Math.round(v.k * 100));
    },
    [paint, setZoom],
  );
  function reset() {
    view.current = { x: 0, y: 0, k: 1 };
    paint();
    setZoom(100);
  }
  const fit = useCallback(() => {
    const nodes = [...geometry.nodes.values()];
    if (!nodes.length) return;
    const minX = Math.min(...nodes.map((n) => n.x!)) - 35,
      maxX = Math.max(...nodes.map((n) => n.x!)) + 35,
      minY = Math.min(...nodes.map((n) => n.y!)) - 35,
      maxY = Math.max(...nodes.map((n) => n.y!)) + 35;
    const k = Math.min(2.5, 900 / (maxX - minX), 540 / (maxY - minY));
    view.current = {
      x: 500 - ((minX + maxX) * k) / 2,
      y: 310 - ((minY + maxY) * k) / 2,
      k,
    };
    paint();
    setZoom(Math.round(k * 100));
  }, [geometry, paint, setZoom]);
  useEffect(() => {
    fit();
  }, [fit]);
  useEffect(() => {
    const element = svg.current;
    if (!element) return;
    const wheel = (event: WheelEvent) => {
      event.preventDefault();
      scale(event.deltaY < 0 ? 1.1 : 1 / 1.1);
    };
    element.addEventListener("wheel", wheel, { passive: false });
    return () => {
      element.removeEventListener("wheel", wheel);
      if (frame.current !== undefined) cancelAnimationFrame(frame.current);
    };
  }, [scale]);
  function edgePath(source: string, target: string, reciprocal: boolean) {
    const a = geometry.nodes.get(source)!,
      b = geometry.nodes.get(target)!;
    const dx = b.x! - a.x!,
      dy = b.y! - a.y!,
      length = Math.hypot(dx, dy) || 1;
    const sx = a.x! + (dx / length) * (a.radius + 2),
      sy = a.y! + (dy / length) * (a.radius + 2),
      tx = b.x! - (dx / length) * (b.radius + 9),
      ty = b.y! - (dy / length) * (b.radius + 9);
    return reciprocal
      ? `M${sx},${sy} Q${(sx + tx) / 2 - dy * 0.15},${(sy + ty) / 2 + dx * 0.15} ${tx},${ty}`
      : `M${sx},${sy} L${tx},${ty}`;
  }
  return (
    <div className="graph-stage" data-layout-ms={geometry.layoutMs.toFixed(3)} data-worker-ready-ms={geometry.workerReadyMs.toFixed(3)}>
      <div className="graph-view-controls" aria-label="Graph view controls">
        <button onClick={() => scale(1.25)} aria-label="Zoom in">
          +
        </button>
        <button onClick={() => scale(0.8)} aria-label="Zoom out">
          −
        </button>
        <span ref={zoomText}>100%</span>
        <button onClick={fit}>Fit</button>
        <button onClick={reset}>Reset view</button>
      </div>
      <svg
        ref={svg}
        viewBox="0 0 1000 620"
        role="img"
        tabIndex={0}
        aria-describedby="graph-keyboard-help"
        onKeyDown={(e) => {
          if (
            [
              "ArrowLeft",
              "ArrowRight",
              "ArrowUp",
              "ArrowDown",
              "+",
              "=",
              "-",
              "Home",
            ].includes(e.key)
          )
            e.preventDefault();
          if (e.key === "ArrowLeft") view.current.x -= 40;
          if (e.key === "ArrowRight") view.current.x += 40;
          if (e.key === "ArrowUp") view.current.y -= 40;
          if (e.key === "ArrowDown") view.current.y += 40;
          if (e.key === "+" || e.key === "=") scale(1.2);
          if (e.key === "-") scale(1 / 1.2);
          if (e.key === "Home") fit();
          paint();
        }}
        aria-label="Directed transaction neighborhood. Use the account and relationship lists below for keyboard inspection."
        onPointerDown={(e) => {
          if ((e.target as Element).closest("[data-graph-object]")) return;
          const matrix = svg.current?.getScreenCTM();
          if (!matrix) return;
          const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(
            matrix.inverse(),
          );
          drag.current = {
            x: point.x,
            y: point.y,
            vx: view.current.x,
            vy: view.current.y,
          };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (!drag.current || !svg.current) return;
          const matrix = svg.current.getScreenCTM();
          if (!matrix) return;
          const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(
            matrix.inverse(),
          );
          view.current.x = drag.current.vx + point.x - drag.current.x;
          view.current.y = drag.current.vy + point.y - drag.current.y;
          schedule();
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
      >
        <defs>
          <marker
            id="graph-arrow"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="4"
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path d="M0,0 L8,4 L0,8 Z" fill="#a6a6a6" />
          </marker>
        </defs>
        <g ref={group} transform="translate(0 0) scale(1)">
          {data.edges.map((e) => {
            const path = edgePath(
              e.source_ref,
              e.target_ref,
              e.reciprocal_in_snapshot,
            );
            const active = e.edge_ref === selected;
            return (
              <g
                key={e.edge_ref}
                data-graph-object="edge"
                data-edge-ref={e.edge_ref}
                onClick={() => onEdge(e.edge_ref)}
              >
                <path
                  d={path}
                  fill="none"
                  stroke="transparent"
                  strokeWidth="14"
                  pointerEvents="stroke"
                />
                <path
                  className={active ? "selected-edge" : ""}
                  d={path}
                  fill="none"
                  stroke={active ? "#fff" : "#77777d"}
                  strokeWidth={
                    active
                      ? 2.5
                      : Math.min(4, 0.7 + Math.log10(1 + e.transaction_count))
                  }
                  strokeDasharray={
                    e.target_ref === data.focus_ref ? "5 3" : undefined
                  }
                  markerEnd="url(#graph-arrow)"
                />
                <title>
                  {e.transaction_count} recorded transactions, sender to
                  receiver
                </title>
              </g>
            );
          })}
          {data.nodes.map((n) => {
            const p = geometry.nodes.get(n.node_ref)!;
            const focus = n.node_ref === data.focus_ref,
              active = n.node_ref === selected;
            return (
              <g
                key={n.node_ref}
                data-graph-object="node"
                data-node-ref={n.node_ref}
                transform={`translate(${p.x} ${p.y})`}
                onClick={() => onNode(n.node_ref)}
              >
                <circle
                  r={p.radius + 7}
                  fill="transparent"
                  stroke={active ? "#fff" : focus ? "#b44a50" : "transparent"}
                  strokeWidth={active ? 2 : 1}
                />
                <circle
                  r={p.radius}
                  fill={focus ? "#fff" : "#a6a6a6"}
                  stroke="#080809"
                  strokeWidth="2"
                />
                {focus && (
                  <text
                    y={-p.radius - 14}
                    textAnchor="middle"
                    fill="#f5f5f5"
                    fontSize="13"
                  >
                    FOCUS
                  </text>
                )}
                <title>
                  {n.display_id}, account, incoming degree {n.in_degree},
                  outgoing degree {n.out_degree}
                </title>
              </g>
            );
          })}
        </g>
      </svg>
      <div className="graph-legend">
        Arrow: sender → receiver · radius: capped log of full-snapshot degree ·
        width: capped log of transaction count · dashed: incoming to focus ·
        curved pairs: reciprocal in source snapshot
      </div>
      <p className="graph-layout-note" id="graph-keyboard-help">
        Static deterministic layout / {geometry.layoutMs.toFixed(1)} ms. Drag
        background to pan; use wheel or buttons to zoom. Positions are visual,
        not a financial measure. Keyboard: arrows pan, +/− zoom, Home fits.
      </p>
    </div>
  );
}
