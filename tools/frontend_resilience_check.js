/* Controlled faults against the real UI functions; no browser or model calls. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const extract = (source, start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const deferred = () => {let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const tick = () => new Promise(resolve=>setImmediate(resolve));

function uiHarness() {
  const elements=new Map(), handlers=new Map();
  function el(id) {if(!elements.has(id))elements.set(id,{id,style:{},disabled:false,value:'',textContent:'',
    addEventListener(type,fn){handlers.set(id+':'+type,fn);},querySelector:selector=>el(selector.slice(1)),
    setAttribute(){},showModal(){this.open=true;},close(){this.open=false;handlers.get(id+':close')?.();},
    getBoundingClientRect:()=>({left:0,right:100,top:0,bottom:100})});return elements.get(id);}
  const store=new Map(),pending=[],events=[];
  const document={readyState:'loading',addEventListener(){},getElementById:id=>elements.get(id),
    createElement(){return el('ui-connection-dialog');},body:{appendChild(){}}};
  const context={document,location:{origin:'https://skillnet.test',href:'https://skillnet.test/'},Request,Headers,URL,AbortController,Event,TextDecoder,
    localStorage:{getItem:key=>store.get('local:'+key)||null},sessionStorage:{getItem:key=>store.get(key)||null,setItem:(key,value)=>store.set(key,value),removeItem:key=>store.delete(key)},
    window:{fetch:(input,options)=>{const d=deferred();pending.push({input,options,...d});return d.promise;},dispatchEvent:event=>events.push(event.type)},setTimeout,clearTimeout};
  vm.runInNewContext(read('web/assets/ui.js'),context);
  return {UI:context.window.UI,elements,handlers,store,pending,events};
}

async function tokenRace() {
  const h=uiHarness();h.UI.setToken('original');h.UI.connectionSettings();
  h.elements.get('ui-token').value='candidate';
  const save=h.handlers.get('ui-token-save:click')({currentTarget:h.elements.get('ui-token-save')});
  assert.equal(h.UI.getToken(),'original','unverified candidate must not become the active token');
  assert.equal(h.pending[0].options.headers.get('X-SkillNet-Token'),'candidate');
  h.handlers.get('ui-token-clear:click')();
  h.pending[0].reject(new Error('late network failure'));await save;
  assert.equal(h.UI.getToken(),'','late validation failure must not restore a cleared token');
  assert.match(h.elements.get('ui-token-status').textContent,/已清除/);
  assert.ok(h.pending[0].options.signal.aborted);
  h.elements.get('ui-token').value='accepted';
  const second=h.handlers.get('ui-token-save:click')({currentTarget:h.elements.get('ui-token-save')});
  h.pending[1].resolve({ok:true,json:async()=>({token_required:true})});await tick();
  assert.equal(h.pending[2].options.headers.get('X-SkillNet-Token'),'accepted');
  h.pending[2].resolve({ok:true,json:async()=>({ok:true})});await second;
  assert.equal(h.UI.getToken(),'accepted');
  assert.ok(h.events.includes('skillnet:connection-changed'));
  h.elements.get('ui-token').value='closed';
  const third=h.handlers.get('ui-token-save:click')({currentTarget:h.elements.get('ui-token-save')});
  h.elements.get('ui-connection-dialog').close();h.pending[3].resolve({ok:true,json:async()=>({token_required:false})});await third;
  assert.equal(h.UI.getToken(),'accepted','closing validation must not mutate the connection later');
}

function storedHistory() {
  const h=uiHarness(),bad='x\' onclick=\'alert(1)';
  h.store.set('local:history',JSON.stringify([null,{id:5,turns:[]},{id:bad,title:'<img onerror=x>',turns:[null,{q:4},{q:'Keep this question',run_id:'run-1',body:'<script>x</script>',_html:'<script>x</script>',_fin:{secret:true},reply_digest:'previous'}]}]));
  const sessions=h.UI.readSessions('history');assert.equal(sessions.length,1);
  assert.equal(sessions[0].turns.length,1);assert.equal(sessions[0].turns[0].run_id,'run-1');
  assert.equal(sessions[0].turns[0].body,'');assert.equal(sessions[0].turns[0]._html,undefined);assert.equal(sessions[0].turns[0]._fin,undefined);
  const html=read('web/briefing.html'),host={innerHTML:'',querySelectorAll:()=>[]};
  new Function('WS_SESSIONS','WS_CUR','$','esc',extract(html,'function wsRenderList(){','function wsPhaseBar(')+'\nwsRenderList();')(sessions,bad,()=>host,h.UI.esc);
  assert.ok(host.innerHTML.includes('<button type="button"'));assert.ok(!/onclick=["']/.test(host.innerHTML));
  assert.ok(host.innerHTML.includes('data-session="x&#39; onclick=&#39;alert(1)"'));
  h.store.set('local:history','{}');assert.equal(h.UI.readSessions('history').length,0);
}

function skillsHarness() {
  const ids=new Map(),pending=[];
  const el=id=>{if(!ids.has(id))ids.set(id,{value:'',options:[{}],innerHTML:'',textContent:'',
    insertAdjacentHTML(){this.options.push({});},after(){},querySelectorAll:()=>[]});return ids.get(id);};
  el('skill-domain').value='';el('skill-source').value='';
  const code=extract(read('web/app.html'),'let SKILLS = [],skillOffset=0,skillGeneration=0;','function labelCells(');
  const api=new Function('$','API','UI','esc','document','labelCells',code+'\nreturn {loadSkills};')(
    el,'https://skillnet.test',{json:url=>{const d=deferred();pending.push({url,...d});return d.promise;},errorHTML:e=>'ERROR '+e.message,toast(){}},
    String,{createElement:()=>({}),getElementById:el},()=>{});
  return {...api,el,pending};
}
const page=(name,total)=>({items:[{name,description:name,domain:'test',quality:{},stats:{},source:'seed'}],total});
async function skillsRace() {
  const h=skillsHarness();const a=h.loadSkills();h.pending[0].resolve(page('older',1));await tick(); // A waits for domain metadata.
  h.el('q').value='current';const b=h.loadSkills();h.pending[2].resolve(page('current',2));await tick();
  h.pending[3].resolve({domain_distribution:{test:2}});await b;
  const current=h.el('skills-body').innerHTML;assert.ok(current.includes('current'));
  h.pending[1].resolve({domain_distribution:{old:1}});await a;
  assert.equal(h.el('skills-body').innerHTML,current,'late domain metadata must not restore the previous result');
  const c=h.loadSkills(),d=h.loadSkills();h.pending[5].resolve(page('newest',3));await d;
  h.pending[4].reject(new Error('old request failed'));await c;
  assert.ok(h.el('skills-body').innerHTML.includes('newest'));assert.ok(!h.el('skills-body').innerHTML.includes('old request failed'));
  const isolated=skillsHarness();const e=isolated.loadSkills();isolated.pending[0].resolve(page('still-visible',1));await tick();
  isolated.pending[1].reject(new Error('stats offline'));await e;
  assert.ok(isolated.el('skills-body').innerHTML.includes('still-visible'),'optional metadata failure must not erase independently loaded skills');
}

async function blockedStorage() {
  const html=read('web/app.html'),button={textContent:'Run',disabled:false},location={href:''};
  const elements={task:{value:'demo question'},run:button};
  const code=extract(html,'async function startRun(){','/* ---------- Latest Run');
  let calls=0;
  const fn=new Function('$','fetch','API','localStorage','location','UI',code+'\nreturn startRun;')(
    id=>elements[id],async()=>{calls++;return {ok:true,json:async()=>({run_id:'created-run'})};},'',
    {setItem(){throw new Error('storage disabled');}},location,{toast(){throw new Error('must not misreport a confirmed creation');}});
  await fn();assert.equal(calls,1);assert.equal(location.href,'/run?id=created-run');
  const run=read('web/run.html'),declaration=extract(run,'const RUN_ID =','// 截图/审计模式');
  const id=new Function('QS','localStorage',declaration+'\nreturn RUN_ID;')(new URLSearchParams(),{getItem(){throw new Error('storage disabled');}});
  assert.equal(id,'','storage-disabled run detail still reaches its empty state');
}

function honestScoreAndAttempts() {
  const html=read('web/index.html');
  const declarations=html.split('\n').filter(line=>/^const judge(Score|Dimensions) =/.test(line)).join('\n');
  const {judgeScore,judgeDimensions}=new Function('num',declarations+'\nreturn {judgeScore,judgeDimensions};')((n,d)=>n.toFixed(d));
  for(const judge of [{},{weighted:null},{weighted:Infinity},{weighted:9,score_valid:false}])assert.equal(judgeScore(judge),'不可用');
  assert.equal(judgeScore({weighted:0}),'0.00/10','an actual numeric zero remains a valid reference score');
  assert.equal(judgeDimensions({score_valid:false,scores:{quality:9}}).length,0);
  assert.deepEqual(judgeDimensions({scores:{quality:9,bad:Infinity,missing:null}}),[['quality',9]]);
  const chat=read('web/chat.html'),step=extract(chat,'function stepCardHTML(s, fin, i){','/* Agent 回复');
  const render=new Function('esc','fmtMs','API',step+'\nreturn stepCardHTML;')(String,String,'');
  const card=render({idx:0,status:'skipped',n_attempts:0,action:'blocked admission'}, {steps:[]},0);
  assert.match(card,/共 0 次尝试/,'a blocked precondition cannot pretend to have run one attempt');
}

async function centreRequestOwnership() {
  const html=read('web/app.html'),elements=new Map(),pending=[];
  const el=id=>{if(!elements.has(id))elements.set(id,{style:{},innerHTML:'',textContent:''});return elements.get(id);};
  const source='let HEALTH=null,healthGeneration=0,latestGeneration=0,evalGeneration=0,systemGeneration=0;\n'+
    extract(html,'async function loadHealth(){','/* ---------- 示例任务')+
    extract(html,'async function loadLatest(){','let runOffset=')+
    extract(html,'async function loadEval(){','/* ---------- System')+
    extract(html,'async function loadSystem(){','/* ---------- boot');
  const functions=new Function('$','API','UI','esc','Product','fmtMs','fmtTime','kpis',source+'\nreturn {loadHealth,loadLatest,loadEval,loadSystem};')(
    el,'',{json:url=>{const d=deferred();pending.push({url,...d});return d.promise;},errorHTML:e=>'ERROR '+e.message},String,
    {labels:{COMPLETED:'done'},evidenceHTML:r=>'EVIDENCE '+r.task,experimentsHTML:r=>'EXPERIMENT '+r.name},String,String,()=>'<kpi>');
  let offset=pending.length;
  const healthA=functions.loadHealth(),healthB=functions.loadHealth();
  pending[offset+1].resolve({ok:true,model:'current-model'});await healthB;
  pending[offset].reject(new Error('old health failure'));await healthA;
  assert.match(el('sys').innerHTML,/current-model/);
  offset=pending.length;const latestA=functions.loadLatest();
  pending[offset].resolve({summary:{},runs:[{run_id:'old',status:'COMPLETED'}]});await tick();
  const latestB=functions.loadLatest();pending[offset+2].resolve({summary:{},runs:[{run_id:'current',status:'COMPLETED'}]});await tick();
  pending[offset+3].resolve({task:'current task'});await latestB;
  pending[offset+1].reject(new Error('old detail failure'));await latestA;
  assert.match(el('latest-body').innerHTML,/current task/);assert.doesNotMatch(el('latest-body').innerHTML,/old detail failure/);
  offset=pending.length;const evalA=functions.loadEval(),evalB=functions.loadEval();
  pending[offset+2].resolve({name:'current report'});pending[offset+3].resolve({});await evalB;
  pending[offset].reject(new Error('old report failure'));pending[offset+1].resolve({});await evalA;
  assert.equal(el('eval-body').innerHTML,'EXPERIMENT current report');
  offset=pending.length;const systemA=functions.loadSystem(),systemB=functions.loadSystem();
  pending[offset+3].resolve({});pending[offset+4].resolve({total:1,evolved:0});pending[offset+5].resolve({model:'current system',runtime:{deployment:'queue-worker'}});await systemB;
  pending[offset].reject(new Error('old system failure'));pending[offset+1].resolve({});pending[offset+2].resolve({});await systemA;
  assert.match(el('sys-body').innerHTML,/current system/);assert.doesNotMatch(el('sys-body').innerHTML,/old system failure/);
}

(async()=>{await tokenRace();storedHistory();await skillsRace();await blockedStorage();honestScoreAndAttempts();await centreRequestOwnership();
  console.log('Frontend resilience: token clear/close races, untrusted stored history, chained search ordering, metadata failure, storage-disabled runs, unavailable judge scores, blocked zero-attempt steps and centre request ownership passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
