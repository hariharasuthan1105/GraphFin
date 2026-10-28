import { useState } from 'react';
import { useSession } from './sessionContext';
import { Panel, Table, Hash } from './ui';

const tabs = ['Preview', 'Statistics', 'Schema', 'Data quality', 'Column mapping'] as const;
export default function SessionDataset() {
  const { activeSession } = useSession();
  const [tab, setTab] = useState<typeof tabs[number]>('Preview');
  if (!activeSession) return null;
  const s = activeSession.summary;
  const facts: [string, string | number][] = [
    ['Source records', s.sourceRecords ?? s.totalTransactions],
    ['Accepted records', s.totalRowsAccepted ?? s.totalTransactions],
    ['Rejected records', s.totalRowsRejected ?? 'Not recorded'],
    ['Transactions labelled normal', s.transactionLabels?.normal ?? 'Not recorded'],
    ['Transactions labelled anomalous', s.transactionLabels?.anomalous ?? 'Not recorded'],
    ['Transactions without known labels', s.transactionLabels?.unknown ?? 'Not recorded'],
    ['Accounts flagged for review (heuristic)', s.suspiciousAccountCount],
    ['Accounts', s.uniqueAccounts], ['Directed edges', s.uniqueEdges],
    ['File size', `${s.fileSizeBytes.toLocaleString()} bytes`],
    ['Currency', s.isMixedCurrency ? 'Mixed units — no FX normalization' : s.currency || 'Unknown'],
    ['Coverage', 'All accepted records; no silent sampling'],
  ];
  return <Panel title="Dataset inspection" tag="ACTIVE SESSION">
    <div className="panel-body">
      <div className="session-tabs" role="tablist" aria-label="Dataset inspection">
        {tabs.map(label => <button key={label} role="tab" aria-selected={tab === label} id={`dataset-tab-${label.replaceAll(' ', '-')}`} aria-controls="dataset-inspection" onClick={() => setTab(label)}>{label}</button>)}
      </div>
      <div id="dataset-inspection" role="tabpanel" aria-labelledby={`dataset-tab-${tab.replaceAll(' ', '-')}`}>
        {tab === 'Preview' && (activeSession.datasetPreview ? <Table caption="First 20 source records, before validation. All accepted records contribute to analysis." headers={activeSession.datasetPreview.headers} rows={activeSession.datasetPreview.rows} /> : <p>Source preview is unavailable for this session. Upload a file to inspect its original columns.</p>)}
        {tab === 'Statistics' && <dl className="session-facts">{facts.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{typeof value === 'number' ? value.toLocaleString() : value}</dd></div>)}</dl>}
        {tab === 'Schema' && <Table caption="Original source columns" headers={['Column', 'Interpretation']} rows={(s.sourceColumns ?? []).map(column => [column, Object.entries(s.columnMapping ?? {}).find(([, value]) => value === column)?.[0] ?? 'Unmapped'])} />}
        {tab === 'Data quality' && <><dl className="session-facts">{facts.slice(0, 3).map(([key,value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl><p>Missing source/destination or non-positive/non-finite amounts are rejected. No corrections are inferred. Currency and timestamp semantics depend on the input. Preview remains local to this browser session.</p><Hash value={s.inputChecksum} /></>}
        {tab === 'Column mapping' && <><Table caption="Mapping used for the completed analysis" headers={['Field', 'Source column']} rows={Object.entries(s.columnMapping ?? {}).map(([key, value]) => [key, value || 'Not mapped'])} /><a className="action-link" href="#/analyze">Open Interactive Analysis to replace the dataset →</a></>}
      </div>
    </div>
  </Panel>;
}
