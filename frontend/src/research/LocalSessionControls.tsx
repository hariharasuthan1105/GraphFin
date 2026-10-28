import { useSession } from './sessionContext';

export default function LocalSessionControls() {
  const { activeSession, saveAnalysisLocally, clearSavedSession, storageMessage, storageBusy } = useSession();
  return <details className="panel-body" aria-label="Local session recovery">
    <summary>Local session recovery</summary>
    <p>Optional local recovery: save a snapshot of account identifiers, aggregate amounts, analysis results and graph selection on this device. It expires after 7 days and is deleted when GraphFin next opens. Raw transaction rows and preview are excluded. Shared-device users may access this information. Nothing is sent to a server.</p>
    <button className="action-link" disabled={!activeSession || storageBusy} onClick={saveAnalysisLocally}>Save analysis locally</button>{' '}
    <button className="action-link" disabled={storageBusy} onClick={clearSavedSession}>Clear saved session</button>
    <p role="status">{storageMessage || 'Saving is off by default. Save again to update the snapshot; replacing the dataset removes the previous snapshot. Clearing leaves the current in-memory analysis open.'}</p>
  </details>;
}
