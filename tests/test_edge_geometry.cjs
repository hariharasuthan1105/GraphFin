const fs=require('fs'),assert=require('assert/strict'),ts=require('../frontend/node_modules/typescript');
require.extensions['.ts']=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const {edgeGeometry}=require('../frontend/src/research/datasetAnalysis/edgeGeometry.ts');
const a={x:100,y:100,radius:10},b={x:300,y:100,radius:15};
for(const scale of [0.15,0.5,1,2.5]){
 const straight=edgeGeometry(a,b,false,scale);
 assert.ok(Math.abs(Math.hypot(straight.start.x-a.x,straight.start.y-a.y)-(a.radius+3/scale))<1e-8);
 assert.ok(Math.abs(Math.hypot(straight.end.x-b.x,straight.end.y-b.y)-(b.radius+3/scale))<1e-8);
 assert.ok(straight.start.x<straight.end.x);assert.equal(straight.kind,'straight');
 const ab=edgeGeometry(a,b,true,scale),ba=edgeGeometry(b,a,true,scale);
 assert.ok(ab.start.y>100&&ba.start.y<100,'Reciprocal arrows must occupy opposite curves');
 assert.notEqual(ab.path,ba.path);assert.ok(ab.path.includes(' Q '));
 const self=edgeGeometry(a,a,false,scale);assert.equal(self.kind,'self');assert.ok(self.path.includes(' C '));
 assert.ok(Math.abs(Math.hypot(self.end.x-a.x,self.end.y-a.y)-(a.radius+3/scale))<1e-8);
}
assert.ok(!edgeGeometry(a,{...a},false,1).path.includes('NaN'));
console.log('PASS: directed boundary trimming at four zoom scales; reciprocal curves; self loops; degenerate positions.');
