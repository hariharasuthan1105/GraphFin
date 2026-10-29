import type { AnalysisSummary } from './datasetAnalysis/types';

export default function NetworkMetricSummary({summary:s}: {summary:AnalysisSummary}) {
  const c=s.cycleDiagnostics;
  return <p className="panel-body">
    Average unique-neighbor total degree: <strong>{s.averageUniqueTotalDegree?.toFixed(2) ?? 'Not recorded'}</strong>.
    {' '}Average transaction incidences: <strong>{(s.averageTransactionIncidences??s.avgDegree).toFixed(2)}</strong> (used in heuristic scoring).
    {' '}Directed three-account cycles observed: <strong>{c?.directedThreeCycles ?? 'Not recorded'}</strong>.
    {' '}Loops meeting noteworthy criteria: <strong>{c?.noteworthyLoops ?? 'Not recorded'}</strong>.
    {c&&(!c.threeCycleScanComplete||!c.fourCycleScanComplete)&&' Cycle scan reached its operation limit: counts are lower bounds and cycle-driven scores may be incomplete.'}
  </p>;
}
