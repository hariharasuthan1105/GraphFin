import type { AnalysisResult } from './types';

/** Single report model. Legacy recovered sessions disclose unavailable new metrics. */
export function buildReportData(analysis: AnalysisResult, generatedAt = new Date().toISOString()) {
  const s = analysis.summary;
  const flags = analysis.accounts.filter(a => a.isFlaggedForReview === true)
    .sort((a,b) => b.anomalyScore - a.anomalyScore || a.id.localeCompare(b.id));
  return {
    summary: s,
    generatedAt,
    reportId: `GF-${s.inputChecksum?.slice(0,8) || 'LOCAL'}-${generatedAt.replace(/\D/g,'')}`,
    sourceRecords: s.sourceRecords ?? s.totalTransactions + (s.totalRowsRejected ?? 0),
    acceptedRecords: s.totalRowsAccepted ?? s.totalTransactions,
    rejectedRecords: s.totalRowsRejected,
    flags,
    rankings: flags.slice(0,15),
    currency: s.isMixedCurrency ? 'MIXED' : s.currency || 'Unknown',
    origin: s.datasetOrigin === 'synthetic' ? 'Synthetic demonstration data' : 'User upload; origin not independently verified',
    engine: s.analysisEngine || 'Client-side graph heuristics',
    algorithmVersion: s.algorithmVersion || 'Not recorded',
    mlStatus: analysis.backendStatus === 'ml_verified'
      ? `Validated backend model/score response: ${analysis.backendModel || 'model name unavailable'}. Rankings in this report remain heuristic.`
      : 'Client-side graph analysis available; backend ML inference not verified.',
    evaluation: s.evaluation,
    cycles: s.cycleDiagnostics,
    integrityWarning: flags.length !== s.suspiciousAccountCount ? 'Saved summary and account flags disagree. Re-run analysis before relying on this report.' : null,
  };
}
