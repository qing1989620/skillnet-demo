/* Actual page code + frozen public evidence. This is DOM, not pixel QA. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {JSDOM}=require(process.env.SKILLNET_JSDOM_DIR||'jsdom'),root=path.resolve(__dirname,'..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const report=read('assets/semantic-routing/v1/report.json'),selection=read('assets/semantic-routing/v1/selection.json');
const cases=read('assets/semantic-routing/v1/cases.json').filter(c=>c.split==='sealed_test');
const guard=read('assets/semantic-routing/guard-v1/report.json');
const dom=new JSDOM(fs.readFileSync(path.join(root,'web/utility.html'),'utf8'),{url:'http://127.0.0.1/utility',runScripts:'outside-only'});
const w=dom.window,d=w.document;let fail=false;const calls=[];
w.UI={json:async(url,opts={})=>{calls.push({url,body:opts.body?JSON.parse(opts.body):null});
 if(fail){fail=false;throw new Error('temporary offline');}
 if(url.endsWith('/semantic'))return {report,selection,cases,guard_validation:guard};
 if(url.endsWith('/replay'))return {input_csv:'<img src=x onerror="window.pwned=1">',new_api_calls:0,
   results:{plain:{state:'rejected',recorded_action:{mask:0,reject:false},artifacts:{'output.csv':{sha256:'abcde123456789',text:'<script>window.pwned=1</script>'}}},
    retrieved_examples:{state:'recorded_refusal',recorded_action:{mask:null,reject:true}},trained_hint:{state:'invalid_recorded_action',recorded_action:null},
    guarded_plain:{state:'preflight_rejected',recorded_action:{mask:0,reject:false},preflight:{allowed:false,reasons:['any_projected_group_without_number']}}}};
 throw new Error('unexpected URL');},fetch:async()=>{throw new Error('download not used');}};
const tick=()=>new Promise(resolve=>setTimeout(resolve,25));
(async()=>{w.eval(fs.readFileSync(path.join(root,'web/assets/semantic-study.js'),'utf8'));await tick();
 assert.equal(d.querySelectorAll('#semantic-metrics tr').length,3);assert.equal(d.getElementById('semantic-case').options.length,24);
 assert.match(d.getElementById('semantic-status').textContent,/0 胜 \/ 2 负 \/ 30 平/);assert.match(d.getElementById('semantic-generalization').textContent,/0 \/ 16/);
 assert.match(d.getElementById('semantic-admission').textContent,/5 \/ 12/);assert.match(d.getElementById('semantic-guard').textContent,/44/);
 d.getElementById('semantic-repeat').value='1';d.getElementById('semantic-case').value='wine-boundary-2';d.getElementById('semantic-case').dispatchEvent(new w.Event('change'));
 d.getElementById('semantic-replay').click();assert.equal(d.getElementById('semantic-repeat').disabled,true);await tick();
 assert.equal(d.querySelectorAll('#semantic-results .execution-card').length,4);assert.match(d.getElementById('semantic-results').textContent,/格式无效/);
 assert.equal(w.pwned,undefined);assert.equal(d.querySelectorAll('#semantic-results img,#semantic-results script').length,0);
 assert(calls.some(c=>c.body?.repeat===1&&c.body.case_id==='wine-boundary-2'));
 fail=true;d.getElementById('semantic-replay').click();await tick();assert.match(d.getElementById('semantic-replay-status').textContent,/temporary offline/);
 assert.equal(d.getElementById('semantic-replay').disabled,false);d.getElementById('semantic-replay').click();await tick();assert.match(d.getElementById('semantic-replay-status').textContent,/新增 API 调用 0/);
 console.log('Semantic study DOM: complete negative results, gates, source validation, batch selection, safe CSV text, busy lock and failure recovery passed.');w.close();
})().catch(e=>{console.error(e);w.close();process.exitCode=1;});
