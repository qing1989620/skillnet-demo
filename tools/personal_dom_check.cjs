/* DOM behaviour tests, not a browser screenshot or CSS visual acceptance. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {JSDOM}=require(process.env.SKILLNET_JSDOM_DIR||'jsdom');
const root=path.resolve(__dirname,'..');
const dom=new JSDOM(fs.readFileSync(path.join(root,'web/personal.html'),'utf8'),{url:'http://127.0.0.1/personal',runScripts:'outside-only',pretendToBeVisual:true});
const w=dom.window,d=w.document,requests=[];let fail=false,outOfScope=false;let sphereOptions;const history=new Map();
const profile={version:0,identity:{tenant:'lab',user:'alice',project:'research'},enabled:true,pinned:[],disabled:[],custom_skills:[],edges:[],active_personal_model:null,observations:{},distinct_queries:0};
const model={available:true,model_id:'network-fixture',trainable_parameters:110596,scope:'relatedness only',reason:'shadow only'};
const research=JSON.parse(fs.readFileSync(path.join(root,'docs/evidence/network-training-v1.json'),'utf8'));let candidates=[];
const continuation=JSON.parse(fs.readFileSync(path.join(root,'docs/evidence/network-training-v2.json'),'utf8'));
const clone=x=>JSON.parse(JSON.stringify(x));
const graph=()=>({nodes:[{id:'data-cleaning',domain:'data',private:false},{id:'xlsx',domain:'documents',private:false},...profile.custom_skills.map(s=>({id:s.name,domain:'private',description:s.description,private:true}))].map(n=>({...n,pinned:profile.pinned.includes(n.id),disabled:profile.disabled.includes(n.id)})),edges:profile.edges});
w.matchMedia=()=>({matches:false});w.HTMLElement.prototype.scrollIntoView=()=>{};
w.SkillSphere={create:(_canvas,options)=>{sphereOptions=options;if(process.env.SKILLNET_TEST_CANVAS_FAILURE)throw new Error('canvas unavailable');return {setData(){},highlight(){},setFilter(){},select(){},focus(){},pause(){},reset(){},destroy(){}};}};
w.UI={productNav:()=>'<nav><a href="/personal">我的网络</a></nav>',json:async(url,options={})=>{
  const body=options.body?JSON.parse(options.body):null;requests.push({url,body,method:options.method});if(fail){fail=false;throw new Error('temporary network failure');}
  if(url==='/api/personal')return clone({profile,model,research,candidates,personal_training_version:'private-preference-training-v2',history_versions:[...history.keys()].sort((a,b)=>b-a),model_candidates:{v1:model,v2:model},research_candidates:{v1:research,v2:continuation}});
  if(url==='/api/personal/graph')return clone(graph());
  if(url==='/api/personal/profile'){assert.equal(body.expected_version,profile.version);history.set(profile.version,clone(profile));Object.assign(profile,body.patch);profile.version++;return clone(profile);}
  if(url==='/api/personal/rollback'){assert.equal(body.expected_version,profile.version);const next=profile.version+1,snapshot=history.get(body.target_version);assert(snapshot);history.set(profile.version,clone(profile));Object.assign(profile,clone(snapshot));profile.version=next;return clone(profile);}
  if(url.startsWith('/api/personal/skill/'))return clone(profile.custom_skills.find(s=>s.name===decodeURIComponent(url.split('/').at(-1))));
  if(url.startsWith('/api/skill/'))return {description:'actual skill description'};
  if(url==='/api/personal/search'){profile.distinct_queries++;profile.observations.query=(profile.observations.query||0)+1;return {selected:[{name:'data-cleaning',score:.8}],private_candidates:[{name:profile.custom_skills[0].name,score:.5}],candidate:{ranking:[{name:'xlsx',score:.7}]},personal_candidate:outOfScope?{available:true,within_support:false,max_support_similarity:.71,scope_min_cosine:.88,ranking:[{name:'data-cleaning',score:.8}]}:null,observation:{recorded:true},manual_personal_model_applied:false};}
  if(url==='/api/personal/feedback'){profile.observations.preference_pair=(profile.observations.preference_pair||0)+1;return {recorded:true};}
  if(url==='/api/personal/train'){const c={model_id:'personal-1234567890abcdef1234',protocol:{version:'private-preference-training-v2'},trained:true,train_queries:4,holdout_queries:2,loss_before:1,loss_after:.2};candidates=[c];return c;}
  throw new Error('Unhandled API '+url);
}};
const tick=()=>new Promise(r=>setTimeout(r,15));
function submit(id){const f=d.getElementById(id);f.dispatchEvent(new w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:f.querySelector('[type=submit]')}));}
(async()=>{
  w.eval(fs.readFileSync(path.join(root,'web/assets/personal.js'),'utf8'));await tick();
  assert.doesNotMatch(d.getElementById('graph-count').textContent,/读取/);
  assert.match(d.getElementById('owner').textContent,/alice \/ research/);assert.match(d.getElementById('admission-title').textContent,/7 \/ 12/);
  assert.equal(d.getElementById('candidate-version').value,'v2');assert.equal(d.getElementById('continuation-section').hidden,false);assert.match(d.getElementById('continuation-policy').textContent,/保留实验基线/);
  d.getElementById('custom-name').value='personal-safe';d.getElementById('custom-description').value='<img src=x onerror="window.pwned=1">';d.getElementById('custom-instructions').value='Read actual files; do not invent results.';submit('custom-form');await tick();
  assert.equal(profile.custom_skills.length,1);assert.equal(d.querySelectorAll('img').length,0);assert.equal(w.pwned,undefined);
  sphereOptions.onSelect({id:'personal-safe'});await tick();assert.match(d.getElementById('selected-description').textContent,/<img/);assert.equal(d.querySelectorAll('img').length,0);
  d.getElementById('question').value='清理重复与泄漏';submit('search-form');await tick();
  assert.equal(d.querySelectorAll('.rank-column').length,3);assert.equal(d.querySelectorAll('.rank-row').length,3);assert.equal(d.getElementById('search-button').disabled,false);
  assert.equal(requests.find(r=>r.url==='/api/personal/search').body.query,'清理重复与泄漏');
  assert.equal(requests.find(r=>r.url==='/api/personal/search').body.candidate_version,'v2');
  d.getElementById('preferred').value='data-cleaning';d.getElementById('rejected').value='xlsx';submit('preference-form');await tick();
  const feedback=requests.find(r=>r.url==='/api/personal/feedback').body;assert.deepEqual(Object.keys(feedback).sort(),['preferred','query','rejected']);
  d.getElementById('train-personal').click();await tick();assert.equal(d.getElementById('use-personal-model').disabled,false);
  d.getElementById('use-personal-model').click();await tick();assert.equal(profile.active_personal_model,'personal-1234567890abcdef1234');
  d.getElementById('stop-personal-model').click();await tick();assert.equal(profile.active_personal_model,null);
  outOfScope=true;submit('search-form');await tick();assert.equal(d.getElementById('scope-message').hidden,false);assert.match(d.getElementById('scope-message').textContent,/0.710/);assert.match(d.querySelectorAll('.rank-column')[2].textContent,/保持原检索/);outOfScope=false;
  fail=true;submit('search-form');await tick();assert.match(d.getElementById('status').textContent,/temporary network failure/);assert.equal(d.getElementById('search-button').disabled,false);
  assert.equal(d.querySelectorAll('svg[role=img]').length,1);
  d.getElementById('rollback-version').value='0';d.getElementById('rollback-profile').click();await tick();assert.equal(profile.custom_skills.length,0);assert.equal(d.getElementById('pin').disabled,true);
  console.log('Personal DOM: owned scope, real evidence rendering, three ranking views, XSS-safe private text, preference labels, train/select/rollback and failed-request recovery passed.');
  w.close();
})().catch(e=>{console.error(e);w.close();process.exitCode=1;});
