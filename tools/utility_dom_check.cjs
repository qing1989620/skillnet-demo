/* Real page logic with recorded evidence; DOM checks are not pixel acceptance. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {JSDOM}=require(process.env.SKILLNET_JSDOM_DIR||'jsdom');const root=path.resolve(__dirname,'..');
const dom=new JSDOM(fs.readFileSync(path.join(root,'web/utility.html'),'utf8'),{url:'http://127.0.0.1/utility',runScripts:'outside-only'});
const w=dom.window,d=w.document,clone=x=>JSON.parse(JSON.stringify(x));const get=(v,n)=>JSON.parse(fs.readFileSync(path.join(root,'assets/conditional-utility',v,n),'utf8'));
let failed=false;const calls=[];const v1=get('v1','report.json'),v2=get('v2','report.json'),llm=get('v1','llm-report.json');
const observe={mask:0,conditions:{no_projected_test_rows:0,any_projected_group_without_number:1,bad_projected_number:0}};
const prediction1={mask:0,abstain:false,proposed_mask:0,predicted_quality:1,predicted_execution_failure:0,marginal:[{skill:'deduplicate',predicted_marginal_gain:-.5}],reason:'within_finite_training_support'};
const prediction2={abstain:true,observed:observe,failure_score:.51,threshold:.5,reason:'learned_failure_boundary'};
w.UI={productNav:()=>'<nav><a href="/utility">实验</a></nav>',json:async(url,opts={})=>{calls.push({url,body:opts.body?JSON.parse(opts.body):null});if(failed){failed=false;throw new Error('temporary network failure');}
 if(url==='/api/frontier/utility')return clone({summary:v1.summary,artifact_audit:get('v1','artifact-audit.json'),strong_baselines:get('v1','strong-baselines.json').metrics,admission:get('v1','admission.json'),llm:llm.summary,usage:llm.usage});
 if(url==='/api/frontier/utility/boundary')return clone(v2);
 if(url.endsWith('/cases'))return {cases:[{id:url.includes('/boundary/')?'iris-sealed-20':'sealed-boundary-new-empty-group'}]};
 if(url.endsWith('/predict'))return {case:{intent:{deduplicate:false,exclude_cross_split:false,drop_missing:false,goal:'group_mean'}},input_csv:'<img src=x onerror="window.pwned=1">',prediction:clone(url.includes('/boundary/')?prediction2:prediction1)};
 if(url.endsWith('/execute'))return {results:{baseline:{state:'rejected',oracle:{deliverable:false,reason:'group has no numeric values'},artifacts:{'output.csv':{sha256:'0123456789abcdef',text:'<script>window.pwned=1</script>'}}},candidate:{state:'abstained',oracle:{deliverable:false},artifacts:{}}}};
 throw new Error('unknown API '+url);
},toast(){},fetch:async()=>{throw new Error('not used');}};
const tick=()=>new Promise(r=>setTimeout(r,20));
(async()=>{w.eval(fs.readFileSync(path.join(root,'web/assets/utility.js'),'utf8'));await tick();await tick();
 assert.equal(d.querySelectorAll('#strategies tr').length,5);assert.equal(d.querySelectorAll('#gates details').length,12);
 assert.match(d.getElementById('llm-result').textContent,/没有观察到额外质量提升/);assert.equal(d.querySelectorAll('img,script:not([src])').length,0);assert.equal(w.pwned,undefined);
 assert.equal(d.getElementById('execute').disabled,false);d.getElementById('execute').click();await tick();assert.equal(d.querySelectorAll('.execution-card').length,2);assert.match(d.getElementById('execution-results').textContent,/执行前停止/);assert.equal(w.pwned,undefined);
 d.getElementById('version').value='v2';d.getElementById('version').dispatchEvent(new w.Event('change'));await tick();await tick();assert.match(d.getElementById('prediction').textContent,/分组/);assert.match(d.getElementById('prediction').textContent,/停止执行/);
 failed=true;d.getElementById('execute').click();await tick();assert.match(d.getElementById('run-status').textContent,/temporary network failure/);assert.equal(d.getElementById('execute').disabled,false);assert.equal(d.getElementById('case').disabled,false);
 d.getElementById('execute').click();await tick();assert.match(d.getElementById('run-status').textContent,/配对完成/);
 assert(calls.some(c=>c.url==='/api/frontier/utility/boundary/execute'&&c.body.case_id==='iris-sealed-20'));
 console.log('Utility DOM: full baselines, actual API comparison, twelve AND gates, version switching, safe artifact text and failure recovery passed.');w.close();
})().catch(e=>{console.error(e);w.close();process.exitCode=1;});
