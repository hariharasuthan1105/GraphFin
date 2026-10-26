export type LayoutInput = { nodes: { node_ref: string; in_degree: number; out_degree: number }[]; edges: { source_ref: string; target_ref: string }[] };
export type Point = { id: string; radius: number; x: number; y: number };
export type LayoutOutput = { nodes: Point[]; layoutMs: number };
const ref = /^node_[a-f0-9]{32}$/;
export function validInput(value: unknown): value is LayoutInput {
 if (!value || typeof value !== "object") return false;
 const v = value as LayoutInput;
 if (!Array.isArray(v.nodes) || !Array.isArray(v.edges) || v.nodes.length > 250 || v.edges.length > 500) return false;
 if (!v.nodes.every(n => n && ref.test(n.node_ref) && Number.isSafeInteger(n.in_degree) && n.in_degree >= 0 && Number.isSafeInteger(n.out_degree) && n.out_degree >= 0)) return false;
 const ids = new Set(v.nodes.map(n => n.node_ref));
 return ids.size === v.nodes.length && v.edges.every(e => e && ids.has(e.source_ref) && ids.has(e.target_ref));
}
export function validOutput(value: unknown, input: LayoutInput): value is LayoutOutput {
 if (!value || typeof value !== "object") return false;
 const v = value as LayoutOutput;
 return Number.isFinite(v.layoutMs) && v.layoutMs >= 0 && Array.isArray(v.nodes) && v.nodes.length === input.nodes.length && v.nodes.every((n, i) => n && n.id === input.nodes[i].node_ref && Number.isFinite(n.x) && Number.isFinite(n.y) && Number.isFinite(n.radius) && n.radius >= 4 && n.radius <= 13);
}
