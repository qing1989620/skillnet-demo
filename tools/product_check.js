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
const paired=JSON.parse(fs.readFileSync(path.join(__dirname,'../out/execution-benchmark-1791453374.json'),'utf8'));
const learningReport=Product.experimentsHTML({paired});
assert.match(learningReport,/2 道冻结任务 \/ 4 组配对/);
assert.match(learningReport,/未满足晋级条件 · 保持候选/);
assert.match(learningReport,/本轮没有测出质量增益/);
assert.match(learningReport,new RegExp(paired.candidate_sha256));
assert.doesNotMatch(learningReport,/三组采用相同数据/);
assert.match(Product.assessmentHTML(run),/历史评价记录/);
const assessed={...run,staged:{learning_gate:{mode:'shadow',eligible:false},
  quality_assessment:{version:'outcome-evidence-v1',scope_verdict:'unknown',overall_verdict:'unconfirmed',
    goal_contract:{source:'user_task_without_independent_reference'},unverified:['用户满意度'],
    observations:[{idx:0,skill:'<script>',observed_score:null,reason:'没有独立判据',necessary_passed:3,necessary_total:3}],
    integrity:[],network:{applied:false,reason:'保留观察'},task_sha256:'task',evidence_sha256:'proof'},
  shadow_feedback:{rows:[{name:'<img>',exploit_before:.5,exploit_after:.5,shadow_delta:null,weight:0}]}}};
const assessment=Product.assessmentHTML(assessed);
assert.match(assessment,/结果判据不足/);
assert.match(assessment,/整体任务质量与用户满意度：尚未确认/);
assert.match(assessment,/未确认 · 不分配奖励/);
assert.match(assessment,/0\.5000 → 0\.5000/);
assert.match(assessment,/影子策略预演/);
assert.match(Product.evidenceHTML(assessed),/正式网络未更新/);
assert.doesNotMatch(assessment,/<script>|<img>/);
const evidenceManifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../docs/evidence/outcome-evidence-files.json'),'utf8'));
for(const record of evidenceManifest){
  const raw=fs.readFileSync(path.join(__dirname,'..',record.path));
  assert.equal(require('node:crypto').createHash('sha256').update(raw).digest('hex'),record.sha256);
}
const measuredRun=JSON.parse(fs.readFileSync(path.join(__dirname,'../out/runs/b5492bb7-20261009-232823-34fe.json'),'utf8'));
const unmeasuredRun=JSON.parse(fs.readFileSync(path.join(__dirname,'../out/runs/1624c869-20261009-232919-0fe0.json'),'utf8'));
assert.equal(measuredRun.judge.weighted,unmeasuredRun.judge.weighted);
assert.match(Product.assessmentHTML(measuredRun),/已测范围通过/);
assert.match(Product.assessmentHTML(unmeasuredRun),/结果判据不足/);
assert.equal(measuredRun.staged.shadow_feedback.policy_state_sha256,unmeasuredRun.staged.shadow_feedback.policy_state_sha256);
for(const name of ['briefing','chat','app','run','graph','index']){
  const html=fs.readFileSync(path.join(__dirname,'../web',name+'.html'),'utf8');
  assert.ok(html.includes('/static/assets/product.js'),name+' uses shared evidence');
  const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  scripts.forEach(m=>new Function(m[1]));
}
console.log('Product: true dependencies, noncontiguous steps, learning gate, partial verification, repairs, safe text and all six page scripts passed.');
