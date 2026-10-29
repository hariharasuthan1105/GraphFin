import type { TransferEdge } from './types';

export interface CycleDiagnostics {
  directedThreeCycles: number;
  directedFourCycles: number;
  reciprocalPairs: number;
  repeatedReciprocalPairs: number;
  qualifyingThreeCycles: number;
  qualifyingFourCycles: number;
  noteworthyLoops: number;
  threeCycleScanComplete: boolean;
  fourCycleScanComplete: boolean;
  operationLimit: number;
  minimumLoopAmount: number;
}

/** Distinct vertices, directed edges, rotational deduplication; reverse orientations remain distinct. */
export function inspectNetworkCycles(edges: TransferEdge[], accountVolumeMean: number, operationLimit = 2_000_000) {
  const outgoing = new Map<string, Map<string, TransferEdge>>();
  for (const edge of edges) {
    if (edge.source === edge.target) continue;
    if (!outgoing.has(edge.source)) outgoing.set(edge.source, new Map());
    outgoing.get(edge.source)!.set(edge.target, edge);
  }
  const accounts = new Set<string>();
  const d: CycleDiagnostics = {
    directedThreeCycles: 0, directedFourCycles: 0, reciprocalPairs: 0, repeatedReciprocalPairs: 0,
    qualifyingThreeCycles: 0, qualifyingFourCycles: 0, noteworthyLoops: 0,
    threeCycleScanComplete: true, fourCycleScanComplete: true, operationLimit,
    minimumLoopAmount: accountVolumeMean * 0.15,
  };
  for (const [u, next] of outgoing) for (const [v, uv] of next) {
    if (u >= v) continue;
    const vu = outgoing.get(v)?.get(u);
    if (!vu) continue;
    d.reciprocalPairs++;
    if (uv.count >= 5 && vu.count >= 5) {
      d.repeatedReciprocalPairs++;
      accounts.add(u); accounts.add(v);
    }
  }
  let operations = 0;
  triangles: for (const [u, next] of outgoing) for (const [v, uv] of next) {
    if (v <= u) continue;
    for (const [w, vw] of outgoing.get(v) ?? []) {
      if (++operations > operationLimit) { d.threeCycleScanComplete = false; break triangles; }
      if (w <= u || w === v) continue;
      const wu = outgoing.get(w)?.get(u);
      if (!wu) continue;
      d.directedThreeCycles++;
      if (Math.min(uv.amount, vw.amount, wu.amount) > d.minimumLoopAmount || accountVolumeMean === 0) {
        d.qualifyingThreeCycles++; [u,v,w].forEach(id => accounts.add(id));
      }
    }
  }
  operations = 0;
  squares: for (const [u, next] of outgoing) for (const [v, uv] of next) {
    if (v <= u) continue;
    for (const [w, vw] of outgoing.get(v) ?? []) {
      if (++operations > operationLimit) { d.fourCycleScanComplete = false; break squares; }
      if (w <= u || w === v) continue;
      for (const [x, wx] of outgoing.get(w) ?? []) {
        if (++operations > operationLimit) { d.fourCycleScanComplete = false; break squares; }
        if (x <= u || x === v || x === w) continue;
        const xu = outgoing.get(x)?.get(u);
        if (!xu) continue;
        d.directedFourCycles++;
        if (Math.min(uv.amount,vw.amount,wx.amount,xu.amount) > d.minimumLoopAmount || accountVolumeMean === 0) {
          d.qualifyingFourCycles++; [u,v,w,x].forEach(id => accounts.add(id));
        }
      }
    }
  }
  d.noteworthyLoops = d.repeatedReciprocalPairs + d.qualifyingThreeCycles + d.qualifyingFourCycles;
  return {diagnostics:d, noteworthyAccounts:accounts};
}
