import type { AnalysisResult } from './datasetAnalysis/types';

export const CANONICAL_FEATURES = ['in_degree','out_degree','total_degree','weighted_in_degree','weighted_out_degree','betweenness_centrality','transaction_count','total_sent','total_received','net_flow','average_transaction_amount','maximum_transaction_amount','unique_receivers','unique_senders','transactions_per_day','transactions_per_week','average_time_between_transactions','minimum_time_between_transactions','maximum_time_between_transactions'];

export function verifyMLResponse(session: AnalysisResult, datasetId: string, training: any, response: any) {
  const m = training?.model_metadata;
  if (training?.status !== 'success' || training?.dataset_id !== datasetId || m?.dataset_id !== datasetId ||
      m?.model_type !== 'IsolationForest' || m?.feature_count !== 19 || m?.n_estimators !== 100 ||
      m?.entity_count !== session.accounts.length ||
      JSON.stringify(m?.feature_names) !== JSON.stringify(CANONICAL_FEATURES)) {
    throw new Error('ML execution metadata does not match the intended 19-feature Isolation Forest pipeline.');
  }
  if (response?.dataset_id !== datasetId || response?.experiment_label !== 'isolation_forest' ||
      response?.total_users !== session.accounts.length || !Array.isArray(response.users) || response.users.length !== session.accounts.length) {
    throw new Error('Incomplete or mismatched account score response. ML inference is not verified.');
  }
  const ids = new Set(session.accounts.map(a => a.id));
  const users = new Map<string, {raw_score:number; risk_score:number; status:string; prediction:number}>();
  for (const u of response.users) {
    if (!ids.has(u.user_id) || users.has(u.user_id) || !Number.isFinite(u.raw_score) ||
        !Number.isFinite(u.risk_score) || u.risk_score < 0 || u.risk_score > 100 ||
        ![-1,1].includes(u.prediction) || u.status !== (u.prediction === -1 ? 'suspicious' : 'normal')) {
      throw new Error('Invalid, duplicate or unmapped ML account scores. ML inference is not verified.');
    }
    users.set(u.user_id, u);
  }
  return users;
}
