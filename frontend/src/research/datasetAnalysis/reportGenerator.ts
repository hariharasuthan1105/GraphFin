import type { AnalysisResult } from './types';
import { AuditLayout } from './pdfLayout';
import { buildReportData } from './reportData';

const TITLE = 'Machine Learning Enhanced Graph-Based Anomaly Detection for Financial Transactions';
const n = (v: number | undefined, d=0) => v === undefined || !Number.isFinite(v) ? 'Not recorded' : v.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
const patterns: Record<string,string> = {FAN_IN:'Fan-in',FAN_OUT:'Fan-out',VOLUME_OUTLIER:'Volume outlier',FLOW_IMBALANCE:'Flow imbalance',CYCLE:'Qualifying loop'};

/** Searchable, locally generated report driven by one canonical report model. */
export function generateDatasetPdfReport(analysis: AnalysisResult, _executionEngine?: string, download=true) {
  const r=buildReportData(analysis),s=r.summary,c=r.cycles,e=r.evaluation,p=new AuditLayout(r.reportId);
  const money=(v:number,d=2)=>`${r.currency} ${n(v,d)}`;
  const incomplete=!!c&&(!c.threeCycleScanComplete||!c.fourCycleScanComplete);
  let section=1;
  p.text('TRANSACTION NETWORK',16,34,24,true);p.text('ANALYSIS REPORT',16,45,24,true);
  p.y=55;p.paragraph(TITLE,11);
  p.text('CLIENT-SIDE GRAPH HEURISTIC ANALYSIS',16,p.y+2,9,true,'#A52C3B');p.y+=12;
  p.paragraph(`Dataset: ${s.datasetName}`,10);
  p.paragraph(`Generated: ${r.generatedAt} | Report: ${r.reportId}`,8.5);
  p.paragraph(`Origin: ${r.origin}. Algorithm: ${r.algorithmVersion}.`,8.5);
  p.cards([
    {label:'ACCEPTED TRANSACTIONS',value:n(r.acceptedRecords)},
    {label:'UNIQUE ACCOUNTS',value:n(s.uniqueAccounts)},
    {label:'DIRECTED ACCOUNT PAIRS',value:n(s.uniqueEdges)},
    {label:'ACCOUNTS FOR REVIEW',value:n(r.flags.length),detail:'Heuristic flags; not confirmed fraud'},
    {label:'TRANSACTION VOLUME',value:money(s.totalVolume),detail:s.isMixedCurrency?'Mixed units; no FX normalization':`${r.currency} reported currency`},
    {label:'REJECTED / SOURCE ROWS',value:`${n(r.rejectedRecords)} / ${n(r.sourceRecords)}`,detail:`${n(s.dataCompletenessPct,1)}% accepted`},
  ]);
  p.section(section++,'Executive summary');
  p.paragraph(`${n(r.acceptedRecords)} accepted transfers connect ${n(s.uniqueAccounts)} accounts through ${n(s.uniqueEdges)} directed account pairs. The heuristic selected ${n(r.flags.length)} accounts for review. Scores combine account-volume extremity, transaction-count divergence, flow asymmetry and structural indicators; they are not fraud probabilities.`);
  p.note('KEY FINDINGS',`${n(s.patternsDetected.volumeOutlierCount)} account-volume outliers, ${n(s.patternsDetected.fanInCount)} fan-in and ${n(s.patternsDetected.fanOutCount)} fan-out indicators were observed. Indicators overlap and do not sum to unique suspicious accounts. ${c?`${n(c.directedThreeCycles)} directed three-account cycles were observed${c.threeCycleScanComplete?'':' (lower bound)'}; ${n(c.noteworthyLoops)} loops meet noteworthy criteria${incomplete?' (lower bound)':''}.`:'Cycle census was not recorded in this saved session.'}`);
  if(r.integrityWarning)p.note('INTEGRITY WARNING',r.integrityWarning);
  if(s.isMixedCurrency)p.note('CURRENCY LIMITATION','Amounts combine different currency units. The total is an unconverted arithmetic sum, not a monetary valuation. Volume rankings are not comparable across currencies.');

  p.nextPage();p.section(section++,'Dataset & network profile','Transaction counts and simple-graph degrees describe different properties.');
  const t=s.timestampCoverage;
  p.table(['Dataset profile','Recorded value'],[
    ['Source file',s.datasetName],['Source / accepted / rejected',`${n(r.sourceRecords)} / ${n(r.acceptedRecords)} / ${n(r.rejectedRecords)}`],
    ['Unique accounts / currency',`${n(s.uniqueAccounts)} / ${r.currency}${s.isMixedCurrency?' (unconverted)':''}`],
    ['Timestamp coverage',t?`${n(t.present)} present; ${n(t.parseable)} parseable ISO calendar values`:'Not recorded'],
    ['Calendar range',t?.earliest&&t.latest?`${t.earliest} to ${t.latest} (source timezone semantics)`:'Unavailable; step counters are not calendar dates'],
    ['Total / median amount',`${money(s.totalVolume)} / ${money(s.medianAmount)}`],
  ],[60,118],9);
  p.table(['Network statistic','Value'],[
    ['Unique directed edges / self-loop edges',`${n(s.uniqueEdges)} / ${n(s.selfLoopEdges)}`],
    ['Simple directed edges (excluding self-loops)',n(s.simpleDirectedEdges)],
    ['Density: simple edges / N(N-1)',n(s.networkDensity,6)],
    ['Average incoming / outgoing transactions',`${n(s.averageIncomingTransactions,2)} / ${n(s.averageOutgoingTransactions,2)}`],
    ['Average transaction incidences: 2T / N',n(s.averageTransactionIncidences??s.avgDegree,2)],
    ['Average unique-neighbor total degree: 2E / N',n(s.averageUniqueTotalDegree,2)],
    ['Maximum unique in-degree / out-degree',`${n(s.maxUniqueInDegree)} / ${n(s.maxUniqueOutDegree)}`],
    ['Maximum incoming / outgoing transactions',`${n(s.maxInDegree)} / ${n(s.maxOutDegree)}`],
    ['Source-only / sink-only / intermediary accounts',`${n(s.sourceOnlyAccounts)} / ${n(s.sinkOnlyAccounts)} / ${n(s.intermediaryAccounts)}`],
    ['Repeated directed pairs / additional transfers',`${n(s.repeatedDirectedPairs)} / ${n(s.extraRepeatedTransactions)}`],
    ['Self-transfers (included in transaction totals)',n(s.selfTransferTransactions)],
  ],[121,57],9);
  p.note('METRIC DEFINITIONS','Unique neighbors exclude self. A reciprocal neighbor contributes once to each directional degree, but once to the counterparty union. Repeated transfers increase transaction counts and amounts without adding an edge. Self-transfers count once incoming and once outgoing; they add no simple-graph neighbors.');

  p.nextPage();p.section(section++,'Patterns & account findings','Account indicators overlap. Cycle counts are deduplicated loops, not accounts.');
  p.bars([
    {label:'Fan-in indicators',value:s.patternsDetected.fanInCount,unit:'accounts'},
    {label:'Fan-out indicators',value:s.patternsDetected.fanOutCount,unit:'accounts'},
    {label:'Volume outliers',value:s.patternsDetected.volumeOutlierCount,unit:'accounts'},
    ...(c?[{label:'Directed three-account cycles',value:c.directedThreeCycles,unit:'cycles'},{label:'Qualifying noteworthy loops',value:c.noteworthyLoops,unit:'loops'}]:[]),
    {label:'Flagged for review',value:r.flags.length,unit:'accounts'},
  ]);
  p.paragraph(c?`Cycle census: ${n(c.directedThreeCycles)} directed 3-account cycles; ${n(c.directedFourCycles)} directed 4-account cycles; ${n(c.reciprocalPairs)} reciprocal pairs. Qualifying: ${n(c.qualifyingThreeCycles)} three-cycles, ${n(c.qualifyingFourCycles)} four-cycles and ${n(c.repeatedReciprocalPairs)} repeated reciprocal pairs. ${n(s.patternsDetected.cycleCount)} accounts participate in qualifying loops.`:'Cycle census unavailable for this saved session; re-run analysis.',9);
  if(incomplete)p.note('BOUNDED SCAN - LOWER BOUNDS',`The scan reached its ${n(c?.operationLimit)}-operation budget. Cycle counts and cycle-driven scores may be incomplete. Benchmark evaluation is withheld.`);
  p.paragraph(`Showing ${r.rankings.length} of ${r.flags.length} flagged accounts, ordered by heuristic score (ties by ID). Tx in/out are transaction counts; Cp is the distinct counterparty union excluding self. Amounts use ${r.currency}, rounded to whole units in this table.`,9);
  if(r.rankings.length)p.table(['Rank','Account ID','Score','Tx in / out','Cp','Sent','Received','Net flow','Indicators'],r.rankings.map((a,i)=>[
    String(i+1),a.id,a.anomalyScore.toFixed(4),`${n(a.incomingTransactionCount??a.inDegree)} / ${n(a.outgoingTransactionCount??a.outDegree)}`,n(a.uniqueCounterpartyCount),n(a.totalSent),n(a.totalReceived),`${a.netFlow>0?'+':''}${n(a.netFlow)}`,a.patterns.map(v=>patterns[v]||v).join(', ')||'None',
  ]),[11,23,15,14,11,23,23,23,35],8);
  else p.note('NO ACCOUNTS FLAGGED','No account met the review rule. This does not establish that every transaction is normal or that all anomalous behavior was detected.');
  p.paragraph('Review: configured score threshold, OR at least two indicators with score >= 0.40, OR account-volume Z >= 3.0. Full definitions follow in Methodology.',9);

  if(e){
    p.nextPage();p.section(section++,'Benchmark evaluation','Synthetic test-label convention; not validated real-world fraud detection performance.');
    p.cards([{label:'PRECISION',value:`${n(e.precision*100,1)}%`},{label:'RECALL',value:`${n(e.recall*100,2)}%`},{label:'F1 SCORE',value:n(e.f1Score,4)},{label:'AVERAGE PRECISION',value:n(e.prAuc,4)}],2);
    p.table(['Unit of analysis','Count / meaning'],[
      ['Transaction labels',`${n(s.transactionLabels?.anomalous)} positive; ${n(s.transactionLabels?.normal)} normal; ${n(s.transactionLabels?.unknown)} unknown`],
      ['Account label association',`${n(e.positives)} accounts in at least one positive transaction`],
      ['Heuristic review flags',`${n(r.flags.length)} accounts selected by the review rule`],
    ],[65,113],10);
    p.table(['Account confusion matrix','Label-associated positive','Label-associated negative'],[
      ['Flagged for review',`TP: ${n(e.truePositives)}`,`FP: ${n(e.falsePositives)}`],
      ['Not flagged',`FN: ${n(e.falseNegatives)}`,`TN: ${n(e.trueNegatives)}`],
    ],[70,54,54],10);
    p.note('INTERPRETATION',`${n(e.truePositives)} of ${n(e.positives)} label-associated accounts were selected; ${n(e.falseNegatives)} were not. Precision of ${n(e.precision*100,1)}% on ${n(r.flags.length)} flags does not imply broad detection coverage. Recall is ${n(e.recall*100,2)}%. Average precision uses all continuous account scores, grouping ties at each threshold.`);
    p.paragraph(e.aggregationRule);p.paragraph(e.disclaimer);
    p.paragraph('Labels and pattern-type annotations are excluded from scoring. Precision, recall and F1 use account review decisions; average precision uses the full ranking. All four metrics use the same account label-association convention.');
  }

  p.nextPage();p.section(section++,'Methodology & provenance');
  p.paragraph(`Engine: ${r.engine}. Algorithm: ${r.algorithmVersion}. Renderer: GraphFin Audit PDF v3 / jsPDF. Analysis time: ${s.processedAt}.`,9.5);
  p.table(['Component','Weight','Definition'],[
    ['Volume extremity','30%','clamp(account-volume Z / 3.5, 0, 1); volume = sent + received.'],
    ['Transaction-count divergence','25%','clamp(transaction-incidence Z / 3.5, 0, 1); not unique-neighbor degree.'],
    ['Flow asymmetry','20%','Mean of count and amount asymmetry, multiplied by min(1, account volume / mean account volume).'],
    ['Structural indicators','25%','min(1, 0.25 x number of indicators). Indicators can overlap.'],
  ],[47,17,114],9);
  const th=s.thresholdConfig;
  p.paragraph(`The weighted sum is rounded to four decimals and bounded to [0.01, 1]. Volume outlier: volume > account mean + ${th?.volumeZThreshold??'unrecorded'} population SD (threshold ${s.accountVolumeThreshold===undefined?'not recorded':money(s.accountVolumeThreshold)}). Fan-in/out: directional transaction count > directional mean + ${th?.degreeZThreshold??'unrecorded'} x max(1, directional SD), with count ratio >= ${th?.fanInRatio??'unrecorded'} (in) / ${th?.fanOutRatio??'unrecorded'} (out). Flow imbalance requires volume above the account median and |net flow| / volume > 0.85.`,9.5);
  p.paragraph(`Review: score >= ${th?.suspiciousScoreThreshold??'unrecorded'}, OR at least 2 indicators and score >= 0.40, OR volume Z >= 3.0. Scoring retains transaction-occurrence semantics; unique-neighbor metrics are descriptive.`,9.5);
  p.paragraph(`Cycles qualify with >= 5 transfers in each direction of a reciprocal pair, OR a directed loop of 3/4 distinct accounts whose minimum aggregated edge amount exceeds 15% of mean account volume${c?` (${money(c.minimumLoopAmount)})`:''}. Rotations are deduplicated; opposite directions are distinct. Self-loops are excluded. Each 3/4-cycle scan has a ${n(c?.operationLimit)}-operation budget; truncated counts are lower bounds. Longer cycles are not enumerated.`,9.5);
  p.note('BACKEND EXECUTION STATUS',r.mlStatus);
  if(!e)p.paragraph(`Benchmark metrics unavailable: labels may be missing, incomplete, contain no positive accounts, or the cycle scan may be incomplete. Labels: ${n(s.transactionLabels?.anomalous)} positive / ${n(s.transactionLabels?.normal)} normal / ${n(s.transactionLabels?.unknown)} unknown. Unknown labels are not treated as normal.`,9.5);
  p.note('INTERPRETATION & LIMITATIONS','Scores support review prioritization. They are not calibrated fraud probabilities, proof of fraud or causal explanations. Synthetic performance does not establish real-world generalization. Mixed currency totals have no FX normalization. Zero noteworthy loops does not mean no directed cycles exist.');
  p.paragraph(`Coverage: ${n(r.acceptedRecords)} accepted of ${n(r.sourceRecords)} source records; ${n(r.rejectedRecords)} rejected. Input SHA-256: ${s.inputChecksum||'not recorded'}. A hash identifies content, not independently verified forensic provenance.`,9);
  p.paragraph('Privacy: generated locally from the active analysis. No raw transaction rows are included or transmitted for this PDF. Optional saved sessions retain aggregates after consent. This report contains sensitive account identifiers and financial aggregates.',9);
  const doc=p.finish();doc.setProperties({title:`GraphFin - ${s.datasetName}`,subject:TITLE,author:'GraphFin',creator:'GraphFin Audit PDF v3'});
  if(download&&typeof window!=='undefined')doc.save(`GraphFin_Audit_Report_${s.datasetName.replace(/[^a-zA-Z0-9_-]/g,'_')}.pdf`);
  return doc;
}
