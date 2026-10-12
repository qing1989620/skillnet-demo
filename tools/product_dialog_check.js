/* Fault injection against the complete, real Product controller in a controlled
 * DOM. This verifies application code and async ownership, not browser rendering,
 * accessibility-tree behavior or native dialog layout. No network is used. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto, createHash} = require('node:crypto');
const source = fs.readFileSync(path.resolve(__dirname, '../web/assets/product.js'), 'utf8');
const core = require('../web/assets/product.js');
const defer = () => {let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const tick = () => new Promise(resolve=>setImmediate(resolve));
async function settled(){await tick();await tick();}
async function until(test,label){for(let n=0;n<200;n++){if(test())return;await tick();}assert.fail(label);}

function harness(){
  const ids=new Map(),listeners=new Map(),windowListeners=new Map(),pending=[];
  class Element {
    constructor(tag){this.tag=tag;this.dataset={};this.open=false;this.disabled=false;this._html='';this._children=new Map();this.handlers=new Map();this.writes=0;}
    set innerHTML(value){this._html=String(value);this._children=new Map();this.writes++;}
    get innerHTML(){return this._html;}
    querySelector(selector){
      const exists=selector==='.preview-content'?this._html.includes('class="preview-content"'):
        selector.startsWith('[')?this._html.includes(selector.slice(1,-1)):false;
      if(!exists)return null;
      if(!this._children.has(selector))this._children.set(selector,new Element(selector));
      return this._children.get(selector);
    }
    querySelectorAll(){return [];}
    addEventListener(type,handler){const list=this.handlers.get(type)||[];list.push(handler);this.handlers.set(type,list);}
    dispatch(type){for(const handler of this.handlers.get(type)||[])handler({target:this});}
    showModal(){assert.equal(this.open,false);this.open=true;}
    close(){this.open=false;this.dispatch('close');}
    replaceChildren(...children){this._children=new Map(children.map((child,i)=>[String(i),child]));this._html='';this.writes++;}
    insertAdjacentHTML(_position,html){this._html+=html;this.writes++;}
    closest(selector){const key=selector.slice(6,-1).replace(/-([a-z])/g,(_,c)=>c.toUpperCase());return Object.hasOwn(this.dataset,key)?this:null;}
    matches(selector){return Boolean(this.closest(selector));}
    append(...elements){for(const element of elements)if(element.id)ids.set(element.id,element);}
    prepend(...elements){this.append(...elements);}
    click(){}
    snapshot(){
      let view=this._html;const extra=[];
      for(const [key,node] of this._children){
        if(key==='.preview-content'&&node.writes)
          view=view.replace(/(<div class="preview-content"[^>]*>)[\s\S]*?(<\/div>)/,
            (_,start,end)=>start+node.snapshot()+end);
        else if(key!=='.preview-content')extra.push(key+':'+node.snapshot());
      }
      return view+'\n'+extra.join('\n');
    }
  }
  const body=new Element('body');
  const document={readyState:'loading',documentElement:{dataset:{}},body,
    createElement:tag=>new Element(tag),getElementById:id=>ids.get(id)||null,querySelector:()=>null,
    addEventListener(type,handler){const list=listeners.get(type)||[];list.push(handler);listeners.set(type,list);},
    dispatchEvent(){}};
  const UI={mark:'',productNav:()=>'',errorHTML:error=>'<p class="error">'+core.esc(error?.message||error)+'</p>',
    json(url){if(url==='/api/scenarios')return Promise.resolve({items:[]});const d=defer();pending.push({kind:'json',url,...d});return d.promise;},
    fetch(url){const d=defer();pending.push({kind:'fetch',url,...d});return d.promise;}};
  const window={document,UI,addEventListener(type,handler){const list=windowListeners.get(type)||[];list.push(handler);windowListeners.set(type,list);}};
  vm.runInNewContext(source,{window,document,location:{pathname:'/'},crypto:webcrypto,TextDecoder,Uint8Array,Blob,URL,
    setTimeout,clearTimeout,Event,CustomEvent:class{}},{filename:'web/assets/product.js'});
  for(const handler of listeners.get('DOMContentLoaded')||[])handler();
  return {pending,document,ids,window,
    button(dataset){return Object.assign(new Element('button'),{dataset});},
    click(button){for(const handler of listeners.get('click')||[])handler({target:button});},
    key(button,key){let prevented=false;for(const handler of listeners.get('keydown')||[])handler({target:button,key,preventDefault(){prevented=true;}});return prevented;},
    pagehide(){for(const handler of windowListeners.get('pagehide')||[])handler();}};
}

const resourceText=marker=>Buffer.from(marker+'\n<script>resource_payload()</script>','utf8');
const resourceHash=marker=>createHash('sha256').update(resourceText(marker)).digest('hex');
const resourceResponse=marker=>{const raw=resourceText(marker);return {ok:true,arrayBuffer:async()=>raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength)};};
const descriptors=[
  {name:'resource manifest',id:'resources-dialog',dataset:marker=>({skillResources:marker}),
    payload:marker=>({name:marker,repository:'owner/repo',license:'MIT',commit:'a'.repeat(40),files:[]})},
  {name:'verified resource file',id:'resource-file-dialog',dataset:marker=>({resourceRead:'',skill:marker,path:marker+'.md',sha:resourceHash(marker)}),
    response:resourceResponse},
  {name:'evidence export',id:'evidence-dialog',dataset:marker=>({evidenceExport:'',run:marker}),
    payload:marker=>({run_id:marker,capsule_sha256:marker,files:[],status:'COMPLETED',version:'evidence-v1'})},
  {name:'run value',id:'value-dialog',dataset:marker=>({runValue:'',run:marker}),
    payload:marker=>({run_id:marker,status:'COMPLETED',steps:[],artifacts:[],staged:{quality_assessment:{scope:marker}}})},
  {name:'capability report',id:'capabilities-dialog',dataset:marker=>({capabilityReport:'',run:marker}),
    payload:marker=>({run_id:marker,summary:{steps:1},steps:[{idx:0,action:marker}],scope:marker,version:'transitions-v1'})},
  {name:'skill passport',id:'passport-dialog',dataset:marker=>({capabilitySkill:marker}),
    payload:marker=>({passport:{name:marker,capability:marker,activation:[],inputs:[],effects:[]}})},
  {name:'step details',id:'kernel-step-dialog',dataset:marker=>({kernelStep:'0',run:marker}),
    payload:marker=>({run_id:marker,steps:[{idx:0,action:marker,inputs:[],attempts:[],artifacts:[]}]})},
];

async function dialogOwnership(descriptor){
  const h=harness();
  const request=marker=>{const button=h.button(descriptor.dataset(marker));h.click(button);const pending=h.pending.at(-1);return {button,pending};};
  const resolve=(request,marker)=>request.pending.resolve(descriptor.response?descriptor.response(marker):descriptor.payload(marker));
  const finish=async request=>{
    if(['verified resource file','evidence export','capability report','skill passport'].includes(descriptor.name))
      await until(()=>request.button.disabled===false,descriptor.name+' async finally did not complete');
    else await settled();
  };
  const a=request('OLD_A'),b=request('LATEST_B');
  assert.equal(h.pending.length,2,descriptor.name+' must call its real request function');
  resolve(b,'LATEST_B');
  const dialog=h.ids.get(descriptor.id);
  await until(()=>dialog.snapshot().includes('LATEST_B')&&!dialog.snapshot().includes('正在读取'),descriptor.name+' B did not render');
  const latest=dialog.snapshot();
  resolve(a,'OLD_A');await finish(a);
  assert.equal(dialog.snapshot(),latest,descriptor.name+' stale success overwrote B');

  const c=request('OLD_C'),d=request('LATEST_D');resolve(d,'LATEST_D');
  await until(()=>dialog.snapshot().includes('LATEST_D')&&!dialog.snapshot().includes('正在读取'),descriptor.name+' D did not render');
  const current=dialog.snapshot();c.pending.reject(new Error('STALE_C_FAILURE'));await finish(c);
  assert.equal(dialog.snapshot(),current,descriptor.name+' stale catch overwrote D');

  const closed=request('CLOSED_E');dialog.close();const atClose=dialog.snapshot();resolve(closed,'CLOSED_E');await finish(closed);
  assert.equal(dialog.open,false);assert.equal(dialog.snapshot(),atClose,descriptor.name+' closed dialog changed after late success');
  const cancelled=request('CANCELLED_F');dialog.dispatch('cancel');const atCancel=dialog.snapshot();resolve(cancelled,'CANCELLED_F');await finish(cancelled);
  assert.equal(dialog.snapshot(),atCancel,descriptor.name+' cancelled request still rendered');
  const leaving=request('PAGEHIDE_G');h.pagehide();const atLeave=dialog.snapshot();leaving.pending.reject(new Error('PAGEHIDE_FAILURE'));await finish(leaving);
  assert.equal(dialog.snapshot(),atLeave,descriptor.name+' pagehide catch changed the view');
  if(descriptor.name==='verified resource file'||descriptor.name==='evidence export'||descriptor.name==='capability report'||descriptor.name==='skill passport')
    assert.equal(leaving.button.disabled,false,descriptor.name+' did not restore trigger state');
  const active=request('ACTIVE_FAILURE');active.pending.reject(new Error('<script>active_failure()</script>'));await finish(active);
  assert.ok(dialog.snapshot().includes('&lt;script&gt;active_failure()&lt;/script&gt;'),descriptor.name+' active failure must be visible and escaped');
}

function textResponse(text,{lateRead=false}={}){
  const raw=new TextEncoder().encode(text),first=defer();let readCount=0,cancelCount=0;
  const response={ok:true,body:{getReader(){return {read(){readCount++;return readCount===1?(lateRead?first.promise:Promise.resolve({value:raw,done:false})):Promise.resolve({done:true});},async cancel(){cancelCount++;}};}}};
  return {response,first,get readCount(){return readCount;},get cancelCount(){return cancelCount;}};
}

async function artifactOwnership(){
  const h=harness(),button=run=>h.button({artifactPreview:'',run,file:'same.csv',sha:'a'.repeat(64)});
  h.click(button('OLD_RUN'));const a=h.pending.at(-1);h.click(button('LATEST_RUN'));const b=h.pending.at(-1);
  assert.equal(a.url,'/api/runs/OLD_RUN/artifacts/same.csv');assert.equal(b.url,'/api/runs/LATEST_RUN/artifacts/same.csv');
  const old=textResponse('value\nOLD_RESULT',{lateRead:true}),latest=textResponse('value\nLATEST_RESULT');
  a.resolve(old.response);await until(()=>old.readCount===1,'old reader did not start');
  b.resolve(latest.response);const dialog=h.ids.get('product-preview');
  await until(()=>dialog.snapshot().includes('LATEST_RESULT'),'latest run artifact did not render');const snapshot=dialog.snapshot();
  old.first.resolve({value:new TextEncoder().encode('value\nOLD_RESULT'),done:false});await settled();
  assert.equal(dialog.snapshot(),snapshot,'same filename across runs must retain latest request ownership');
  assert.equal(old.cancelCount,1);assert.equal(latest.cancelCount,1);
  assert.match(dialog.snapshot(),/LATEST_RUN/);assert.ok(!dialog.snapshot().includes('OLD_RESULT'));

  h.click(button('OLD_ERROR'));const c=h.pending.at(-1);h.click(button('NEW_RESULT'));const d=h.pending.at(-1);
  d.resolve(textResponse('value\nNEW_GOOD').response);await until(()=>dialog.snapshot().includes('NEW_GOOD'),'new preview did not render');
  const current=dialog.snapshot();c.reject(new Error('STALE_ARTIFACT_FAILURE'));await settled();assert.equal(dialog.snapshot(),current);
  h.click(button('CLOSE_RUN'));const e=h.pending.at(-1);dialog.close();const atClose=dialog.snapshot();e.resolve(textResponse('value\nLATE_CLOSED').response);await settled();
  assert.equal(dialog.snapshot(),atClose);assert.equal(dialog.open,false);

  // The image error callback must also belong to its own request generation.
  h.click(h.button({artifactPreview:'',run:'IMAGE_A',file:'same.svg'}));
  const oldImage=dialog.querySelector('.preview-content')._children.get('0');
  h.click(h.button({artifactPreview:'',run:'IMAGE_B',file:'same.svg'}));
  const imageSnapshot=dialog.snapshot();oldImage.onerror();assert.equal(dialog.snapshot(),imageSnapshot);
  const newImage=dialog.querySelector('.preview-content')._children.get('0');assert.equal(newImage.src,'/api/runs/IMAGE_B/artifacts/same.svg');
  dialog.close();const closedImage=dialog.snapshot();newImage.onerror();assert.equal(dialog.snapshot(),closedImage);

  h.click(h.button({artifactPreview:'',run:'HTML_RUN',file:'answer.html'}));
  h.pending.at(-1).resolve(textResponse('<script>artifact_payload()</script>').response);
  await until(()=>dialog.snapshot().includes('&lt;script&gt;artifact_payload()&lt;/script&gt;'),'artifact HTML must render as escaped source');
  assert.ok(!dialog.snapshot().includes('<script>'));
  h.click(h.button({artifactPreview:'',run:'LARGE_RUN',file:'large.txt'}));
  const large=textResponse('x'.repeat(70000)+'TAIL_MUST_NOT_RENDER');h.pending.at(-1).resolve(large.response);
  await until(()=>dialog.snapshot().includes('预览最多显示 64 KB'),'large preview did not settle');
  assert.ok(!dialog.snapshot().includes('TAIL_MUST_NOT_RENDER'));assert.equal(large.cancelCount,1);
}

async function resourceIntegrity(){
  for(const [name,response,message] of [
    ['mismatch',resourceResponse('wrong bytes'),'资源与清单指纹不一致'],
    ['changed',{ok:false,status:409},'资源指纹已改变'],
    ['oversized',{ok:true,arrayBuffer:async()=>new ArrayBuffer(2000001)},'资源超过读取上限'],
  ]){
    const h=harness(),button=h.button({resourceRead:'',skill:'trusted',path:'SKILL.md',sha:'0'.repeat(64)});
    h.click(button);h.pending[0].resolve(response);
    await until(()=>button.disabled===false,name+' resource did not finish');
    const dialog=h.ids.get('resource-file-dialog');assert.ok(dialog.snapshot().includes(message));
    assert.ok(!dialog.snapshot().includes('data-save-resource'),'unverified resource must not receive a verified download action');
  }
}

async function hostileContent(){
  const attack='<img src=x onerror=payload()>"\' & <script>payload()</script>';
  const escaped=core.esc(attack);
  const run={run_id:attack,staged:{state_policy:{host_reference:true,frozen:{0:{sha256:attack}}},state_composition:{state:'unknown',frontier:[{step_idx:0,file:attack,detail:attack}]}},
    steps:[{idx:0,skill:attack,action:attack,state_evidence:{pre:{state:'unknown',admitted:false,checks:[{state:'unknown',predicate:{kind:attack,file:attack},detail:attack,evidence:{sha256:attack}}]},
      post:{state:'failed',checks:[{state:'failed',predicate:{kind:'csv_schema',file:attack},detail:attack}]}}}]};
  const state=core.stateKernelHTML(run);assert.ok(state.includes(escaped));assert.ok(!state.includes('<script>'));assert.ok(!state.includes('<img src=x'));
  const capsule={...run,staged:undefined,state_kernel:{policy:run.staged.state_policy,declared_composition:run.staged.state_composition}};
  assert.equal(core.stateKernelHTML(capsule),state,'run and capability-capsule paths must expose the same condition semantics');
  assert.match(state,/执行准入<\/b> 无法核实/);assert.match(state,/产物效果<\/b> 条件不满足/);
  assert.match(state,/已阻断代码生成/);assert.match(state,/不代表系统全局不会/);
  assert.ok(state.includes('<b>无法核实</b>'));assert.ok(state.includes('<b>条件不满足</b>'));
  const resources=core.resourcesHTML({name:attack,repository:attack,license:attack,commit:attack,files:[{path:attack,sha256:attack,bytes:12}]});
  assert.ok(resources.includes(escaped));assert.ok(!resources.includes('<img src=x'));assert.ok(!resources.includes('<script>'));

  const h=harness();h.click(h.button({kernelStep:'0',run:'unsafe-step'}));h.pending[0].resolve({run_id:'unsafe-step',steps:[{idx:0,action:attack,dependency_reason:attack,skill:attack,inputs:[attack],code:attack,
    contract:{note:attack},attempts:[{n:attack,repair_reason:attack,code_diff:attack}],artifacts:[]}]});
  const dialog=h.ids.get('kernel-step-dialog');await until(()=>dialog.snapshot().includes(escaped),'step evidence did not render escaped payload');
  assert.ok(!dialog.snapshot().includes('<script>'));assert.ok(!dialog.snapshot().includes('<img src=x'));

  const resource=harness();resource.click(resource.button({resourceRead:'',skill:'trusted',path:'SKILL.md',sha:resourceHash('MALICIOUS_TEXT')}));
  resource.pending[0].resolve(resourceResponse('MALICIOUS_TEXT'));
  await until(()=>resource.ids.get('resource-file-dialog').snapshot().includes('&lt;script&gt;'),'resource text was not escaped');
  assert.ok(!resource.ids.get('resource-file-dialog').snapshot().includes('<script>'));

}

function capabilityCounterEscaping(){
  const attack='<img src=x onerror=payload()><script>payload()</script>';
  const report=core.capabilityReportHTML({summary:{steps:attack,observed_in_scope:attack,file_links:attack,verified_file_links:attack,evidence_gaps:attack},
    steps:[{idx:0,action:attack,checks:{passed:attack,total:attack},independent_checks:{passed:attack,total:attack}}],scope:attack,boundary:attack});
  assert.ok(!report.includes('<img src=x'),'capability summary counts must not interpret API strings as HTML');
}

async function missingStepAndKeyboard(){
  const h=harness(),button=h.button({kernelStep:'99',run:'run-no-step'});
  assert.equal(h.key(button,'Enter'),true,'keyboard step activation must reach the real controller');
  assert.equal(h.pending.length,1);h.pending[0].resolve({run_id:'run-no-step',steps:[]});await settled();
  const dialog=h.ids.get('kernel-step-dialog');
  assert.ok(!dialog.snapshot().includes('正在读取与核对'),'missing step must settle into an explicit empty/error state');
}

(async()=>{
  const failures=[];
  const checks=[...descriptors.map(d=>[d.name,()=>dialogOwnership(d)]),
    ['artifact ownership and bounded source preview',artifactOwnership],['resource integrity',resourceIntegrity],
    ['hostile content and state semantics',hostileContent],['capability counter escaping',capabilityCounterEscaping],
    ['missing step and keyboard activation',missingStepAndKeyboard]];
  for(const [name,check] of checks){try{await check();}catch(error){failures.push(new Error(name+': '+error.message,{cause:error}));}}
  if(failures.length)throw new AggregateError(failures,'Product dialog failures: '+failures.length);
  console.log('Product dialog controller: 7 dialog classes, stale success/catch, close/cancel/pagehide, same-file cross-run streams/images, resource/step/state XSS, unknown vs failed, missing step and keyboard activation passed (controlled DOM; no browser rendering claim).');
})().catch(error=>{console.error(error);process.exitCode=1;});
