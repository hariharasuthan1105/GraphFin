import type { AnalysisSummary } from './datasetAnalysis/types';

/** Raw input stays in memory for explicit backend consent, never in metadata exports. */
export function safeSummary(summary: AnalysisSummary) {
  const { rawCsvContent: _raw, ...metadata } = summary;
  return metadata;
}
