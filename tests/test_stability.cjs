const fs = require('fs');
const assert = require('assert/strict');
const ts = require('../frontend/node_modules/typescript');
require.extensions['.ts'] = (module, filename) => module._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,filename);
const {analyzeTransactionGraph: analyze} = require('../frontend/src/research/datasetAnalysis/engine.ts');
const {prepareSavedAnalysis} = require('../frontend/src/research/localSession.ts');
const {verifyMLResponse, CANONICAL_FEATURES} = require('../frontend/src/research/mlVerification.ts');
const {boundedJsonFetch} = require('../frontend/src/research/boundedFetch.ts');
const tx = (source,destination,amount,label) => ({transaction_id:'test',source,destination,amount,currency:'INR',label});
const result = analyze([tx('A','B',10,0),tx('B','A',20,0)]);
assert.equal(result.accounts.find(a=>a.id==='A').totalSent,10);
assert.equal(result.accounts.find(a=>a.id==='A').totalReceived,20);
assert.equal(result.accounts.find(a=>a.id==='A').netFlow,10);
assert.ok(result.edges.every(e=>e.isReciprocal));
assert.equal(result.summary.patternsDetected.cycleCount,0);
assert.equal(result.topAnomalies.length,0);
assert.equal(analyze([tx('A','A',10,0)]).summary.patternsDetected.cycleCount,0);
assert.equal(analyze([tx('A->B','C',10),tx('A','B->C',20)]).edges.length,2);
assert.equal(analyze([tx('A','B',10,1),tx('B','C',10)]).summary.evaluation,undefined);
const tied=[tx('A','B',10,1),tx('C','D',10,0)];
assert.equal(analyze(tied).summary.evaluation.prAuc,0.5);
assert.equal(analyze(tied.reverse()).summary.evaluation.prAuc,0.5);
result.summary.rawCsvContent='private transactions';
result.datasetPreview={headers:['secret'],rows:[['secret']]};
const saved=prepareSavedAnalysis({session:result,graphMode:'uploaded',simulatedPreset:'mule-ring',selectedGraphAccount:'A'});
assert.ok(!('rawCsvContent' in saved.session.summary));
assert.ok(!('datasetPreview' in saved.session));
assert.equal(result.summary.rawCsvContent,'private transactions');
assert.equal(saved.selectedGraphAccount,'A');
assert.ok(saved.expiresAt>Date.now());
const training={status:'success',dataset_id:'test',model_metadata:{dataset_id:'test',model_type:'IsolationForest',feature_count:19,n_estimators:100,entity_count:2,feature_names:CANONICAL_FEATURES}};
const response={dataset_id:'test',experiment_label:'isolation_forest',total_users:2,users:['A','B'].map(user_id=>({user_id,raw_score:0.1,risk_score:20,status:'normal',prediction:1}))};
assert.equal(verifyMLResponse(result,'test',training,response).size,2);
for(const mutate of [r=>r.users.pop(),r=>r.users[1].user_id='A',r=>r.users[1].user_id='foreign',r=>r.users[0].raw_score=NaN,r=>r.users[0].status='suspicious',r=>r.dataset_id='other']) {
 const invalid=structuredClone(response);mutate(invalid);assert.throws(()=>verifyMLResponse(result,'test',training,invalid));
}
assert.throws(()=>verifyMLResponse(result,'test',{...training,model_metadata:{...training.model_metadata,feature_names:CANONICAL_FEATURES.slice().reverse()}},response));
(async()=>{
 const original=global.fetch;
 try {
  global.fetch=async()=>({ok:false,status:403});
  await assert.rejects(()=>boundedJsonFetch('/test'),/403/);
  global.fetch=async(_url,{signal})=>({ok:true,json:()=>new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(new DOMException('Timed out','AbortError'))))});
  await assert.rejects(()=>boundedJsonFetch('/test',{},10),e=>e.name==='AbortError');
 } finally {global.fetch=original;}
 console.log('PASS: account aggregation, reciprocal/self-loop semantics, edge identity, empty flags, partial labels, tied AP, private snapshots, complete ML mapping, metadata, HTTP failures and body timeout.');
})().catch(e=>{console.error(e);process.exitCode=1;});
