/** Rendering geometry only. Endpoints, multiplicity and amounts stay in the canonical graph. */
export interface EdgePoint { x: number; y: number; radius: number }
export function edgeGeometry(source: EdgePoint, target: EdgePoint, reciprocal: boolean, screenScale: number, self = source === target) {
  const gap = 3 / Math.max(0.05, screenScale);
  if (self) {
    const r = source.radius + gap;
    const reach = r + 35;
    const start = { x: source.x - r * 0.8, y: source.y - r * 0.6 };
    const end = { x: source.x + r * 0.8, y: source.y - r * 0.6 };
    return { path: `M ${start.x} ${start.y} C ${source.x - reach} ${source.y - reach * 1.8}, ${source.x + reach} ${source.y - reach * 1.8}, ${end.x} ${end.y}`, start, end, kind: 'self' };
  }
  const dx = target.x - source.x, dy = target.y - source.y;
  const distance = Math.max(0.001, Math.hypot(dx, dy));
  const bend = reciprocal ? Math.min(58, Math.max(25, distance * 0.18)) : 0;
  // Opposite endpoints naturally flip the perpendicular, separating the two directions.
  const control = { x: (source.x + target.x) / 2 - dy / distance * bend, y: (source.y + target.y) / 2 + dx / distance * bend };
  const fromLength = Math.max(0.001, Math.hypot(control.x - source.x, control.y - source.y));
  const toLength = Math.max(0.001, Math.hypot(control.x - target.x, control.y - target.y));
  const trimSource = Math.min(source.radius + gap, fromLength * 0.8);
  const trimTarget = Math.min(target.radius + gap, toLength * 0.8);
  const start = { x: source.x + (control.x - source.x) / fromLength * trimSource, y: source.y + (control.y - source.y) / fromLength * trimSource };
  const end = { x: target.x + (control.x - target.x) / toLength * trimTarget, y: target.y + (control.y - target.y) / toLength * trimTarget };
  return { path: reciprocal ? `M ${start.x} ${start.y} Q ${control.x} ${control.y}, ${end.x} ${end.y}` : `M ${start.x} ${start.y} L ${end.x} ${end.y}`, start, end, kind: reciprocal ? 'reciprocal' : 'straight' };
}
