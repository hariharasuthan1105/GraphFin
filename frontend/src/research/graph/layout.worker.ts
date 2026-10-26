import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from "d3-force";

import { validInput, type LayoutInput, type Point } from "./layout-contract";
const endpoint = self as unknown as {
  onmessage: ((event: MessageEvent<LayoutInput>) => void) | null;
  postMessage: (
    value: { nodes: Point[]; layoutMs: number } | { error: string },
  ) => void;
};
endpoint.onmessage = (event) => {
  try {
    const input = event.data;
    if (!validInput(input))
      throw new Error("Layout bounds");
    const start = performance.now();
    let random = 42;
    const rng = () =>
      (random = (Math.imul(1664525, random) + 1013904223) >>> 0) / 4294967296;
    type N = SimulationNodeDatum & Point;
    type L = SimulationLinkDatum<N>;
    const nodes: N[] = input.nodes.map((n, i) => ({
      id: n.node_ref,
      radius: Math.min(13, 4 + 2 * Math.log1p(n.in_degree + n.out_degree)),
      x: 500 + 180 * Math.cos(i * 2.399963),
      y: 310 + 180 * Math.sin(i * 2.399963),
    }));
    const links: L[] = input.edges.map((e) => ({
      source: e.source_ref,
      target: e.target_ref,
    }));
    const simulation = forceSimulation(nodes)
      .randomSource(rng)
      .stop()
      .force(
        "link",
        forceLink<N, L>(links)
          .id((n) => n.id)
          .distance(72),
      )
      .force("charge", forceManyBody().strength(-100))
      .force("center", forceCenter(500, 310))
      .force(
        "collide",
        forceCollide<N>().radius((n) => n.radius + 6),
      );
    simulation.tick(100);
    simulation.stop();
    endpoint.postMessage({
      nodes: nodes.map(({ id, radius, x, y }) => ({ id, radius, x, y })),
      layoutMs: performance.now() - start,
    });
  } catch {
    endpoint.postMessage({
      error:
        "The bounded graph layout could not be displayed. Account and relationship lists remain available.",
    });
  }
};
