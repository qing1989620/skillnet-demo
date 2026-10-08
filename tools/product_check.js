/* Test shared product evidence against actual persisted records and hostile text. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Product = require('../web/assets/product.js');
const run = {run_id:'demo',status:'COMPLETED',skills:['csv'],ranking:[{name:'csv'}],retrieval:{selected:['csv']},
  steps:[{idx:0,skill:'csv',action:'read',status:'done',depends_on:[2],checks:[{passed:true}],verifications:[{item:'image',passed:false}]},
    {idx:2,skill:'plot',action:'root',status:'done',depends_on:[],n_attempts:2}],
  staged:{learning_gate:{eligible:false,skip_reason:'semantic blocked'}},artifacts:[]};
assert.deepEqual(Product.dag(run).edges,[{from:2,to:0}]);
assert.ok(Product.dag(run).nodes.find(s=>s.idx===2).x<Product.dag(run).nodes.find(s=>s.idx===0).x);
assert.equal(Product.metrics(run).confirmed,0);
assert.equal(Product.metrics(run).repairs,1);
assert.equal(Product.metrics(run).gate.reason,'semantic blocked');
assert.match(Product.evidenceHTML(run),/学习准入已拦截/);
assert.doesNotMatch(Product.evidenceHTML({...run,skills:['<script>'],steps:[{idx:0,action:'<img src=x onerror=x>',depends_on:[]}]}),/<img src=x/);
assert.ok(Product.dag({steps:[{idx:9,depends_on:[2]},{idx:2,depends_on:[9]}]}).nodes.length===2);
assert.deepEqual(Product.parseCSV('a,b\r\n"line\ntext","a,b"\r\n"escaped""quote",<script>'),[['a','b'],['line\ntext','a,b'],['escaped"quote','<script>']]);
const experiments=Object.fromEntries(fs.readdirSync(path.join(__dirname,'../out')).filter(name=>/^exp[123]_.*\.json$/.test(name)).map(name=>[name.slice(0,-5),JSON.parse(fs.readFileSync(path.join(__dirname,'../out',name),'utf8'))]));
const report=Product.experimentsHTML(experiments,{total:111,edges:248});
assert.match(report,/exp1_retrieval_heldout/);
assert.match(report,/exp1_retrieval_dev/);
assert.match(report,/86\.1%/);
assert.match(report,/8\.861/);
assert.match(report,/indistinguishable/);
assert.match(report,/任务划分须复核/);
assert.match(report,/逐轮奖励/);
assert.doesNotMatch(Product.experimentsHTML({exp1_bad:{timestamp:'<script>',summary:{'<img>':{skill_recall:1}}}}),/<script>|<img>/);
for(const name of ['briefing','chat','app','run','graph','index']){
  const html=fs.readFileSync(path.join(__dirname,'../web',name+'.html'),'utf8');
  assert.ok(html.includes('/static/assets/product.js'),name+' uses shared evidence');
  const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  scripts.forEach(m=>new Function(m[1]));
}
console.log('Product: true dependencies, noncontiguous steps, learning gate, partial verification, repairs, safe text and all six page scripts passed.');
