import type { AnalysisResult } from './datasetAnalysis/types';

const DB = 'graphfin-local-analysis-v1';
const MAX_BYTES = 12 * 1024 * 1024;
export interface SavedAnalysis {
  version: 1;
  expiresAt: number;
  session: AnalysisResult;
  graphMode: 'uploaded' | 'simulated' | 'research';
  simulatedPreset: 'mule-ring' | 'ponzi-cycle' | 'smurfing-fanout' | 'fanin-aggregation';
  selectedGraphAccount: string | null;
}

// Only an explicitly requested snapshot is saved. Source rows and CSV text never enter storage.
export function prepareSavedAnalysis(value: Omit<SavedAnalysis, 'version' | 'expiresAt'>): SavedAnalysis {
  const session = structuredClone(value.session);
  delete session.summary.rawCsvContent;
  delete session.datasetPreview;
  const snapshot: SavedAnalysis = {...value, session, version: 1, expiresAt: Date.now() + 7 * 86400000};
  if (new Blob([JSON.stringify(snapshot)]).size > MAX_BYTES) throw new Error('Analysis exceeds the 12 MB local-saving limit. This session remains in memory.');
  return snapshot;
}

async function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('session');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error('Browser storage is unavailable or restricted.'));
    request.onblocked = () => reject(new Error('Close other GraphFin tabs to update local storage.'));
  });
}

// Serialize writes/deletes so a quick replacement or clear cannot resurrect an older snapshot.
let pending: Promise<unknown> = Promise.resolve();
function write(value?: SavedAnalysis): Promise<void> {
  const task = pending.catch(() => undefined).then(async () => {
    const db = await database();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('session', 'readwrite');
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onabort = tx.onerror = () => { db.close(); reject(new Error('Could not change saved session: browser quota or storage restriction.')); };
      try {
        if (value) tx.objectStore('session').put(value, 'active');
        else tx.objectStore('session').delete('active');
      } catch (error) { db.close(); reject(error); }
    });
  });
  pending = task;
  return task;
}
export const saveLocalAnalysis = (snapshot: SavedAnalysis) => write(snapshot);
export const clearLocalAnalysis = () => write();
export async function readLocalAnalysis(): Promise<SavedAnalysis | null> {
  const db = await database();
  const value = await new Promise<SavedAnalysis | undefined>((resolve, reject) => {
    const tx = db.transaction('session', 'readonly');
    const request = tx.objectStore('session').get('active');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error('Could not read saved analysis.'));
    tx.oncomplete = () => db.close();
  });
  if (!value) return null;
  if (value.version !== 1 || !Number.isFinite(value.expiresAt) || value.expiresAt <= Date.now() ||
      !value.session?.summary || !Array.isArray(value.session.accounts) || !Array.isArray(value.session.edges) ||
      !['uploaded', 'simulated', 'research'].includes(value.graphMode)) {
    await clearLocalAnalysis();
    return null;
  }
  // Defensive privacy check for any obsolete or locally edited snapshot.
  delete value.session.summary.rawCsvContent;
  delete value.session.datasetPreview;
  return value;
}
