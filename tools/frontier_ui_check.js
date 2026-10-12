/* Fault-injection checks run the complete real Frontier IIFE in a controlled DOM.
 * This is logic/ownership evidence, not a browser layout or screen-reader audit. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.resolve(__dirname,'../web/assets/frontier.js'),'utf8');
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function settled(){await tick();await tick();}

function harness({hostName='.product-shell .ui-product-nav',readyState='loading'}={}) {
  const listeners=new Map(),windowListeners=new Map(),pending=[],timers=new Map();let timerId=0;
  let document;
  class Element {
    constructor(tag){this.tagName=tag.toUpperCase();this.className='';this.id='';this.children=[];this.parentNode=null;this.attributes=new Map();this.handlers=new Map();this.disabled=false;this.hidden=false;this.open=false;this.tabIndex=0;this._text='';this._value='';}
    set textContent(value){this._text=String(value);this.children=[];}
    get textContent(){return this._text+this.children.map(child=>child.textContent).join('\n');}
    set value(value){this._value=String(value);}
    get value(){return this._value || (this.tagName==='SELECT' ? this.children[0]?.value || '' : '');}
    set href(value){this._href=String(value);this.attributes.set('href',String(value));}
    get href(){return this._href || '';}
    get isConnected(){return this===document.body || Boolean(this.parentNode?.isConnected);}
    set innerHTML(_){assert.fail('Frontier must never interpret dynamic HTML');}
    append(...children){for(const child of children){this.children.push(child);child.parentNode=this;}}
    replaceChildren(...children){for(const child of this.children)child.parentNode=null;this.children=[];this._text='';this.append(...children);}
    setAttribute(name,value){this.attributes.set(name,String(value));}
    removeAttribute(name){this.attributes.delete(name);}
    getAttribute(name){return this.attributes.get(name)??null;}
    addEventListener(type,fn){const handlers=this.handlers.get(type)||[];handlers.push(fn);this.handlers.set(type,handlers);}
    dispatch(type,extra={}){let prevented=false;const event={target:this,currentTarget:this,preventDefault(){prevented=true;},...extra};for(const fn of this.handlers.get(type)||[])fn(event);return prevented;}
    click(){if(!this.disabled)this.dispatch('click');}
    focus(){document.activeElement=this;}
    showModal(){assert.equal(this.open,false);this.open=true;}
    close(){this.open=false;this.dispatch('close');}
    contains(node){return node===this || this.children.some(child=>child.contains(node));}
    matches(selector){
      if(selector.startsWith('#'))return this.id===selector.slice(1);
      if(selector.startsWith('.'))return this.className.split(/\s+/).includes(selector.slice(1));
      if(selector.startsWith('['))return this.attributes.has(selector.slice(1,-1));
      return this.tagName.toLowerCase()===selector;
    }
    closest(selector){return this.matches(selector)?this:this.parentNode?.closest(selector)||null;}
    querySelectorAll(selector){const selectors=selector.split(',');const found=[];const visit=node=>{for(const child of node.children){if(selectors.some(s=>child.matches(s.trim())))found.push(child);visit(child);}};visit(this);return found;}
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
    getClientRects(){return this.hidden?[]:[{}];}
  }
  const body=new Element('body'),host=new Element('nav');body.append(host);
  document={body,readyState,activeElement:body,createElement:tag=>new Element(tag),
    getElementById:id=>body.querySelector('#'+id),querySelector:selector=>selector===hostName?host:null,
    dispatchClick(target){for(const fn of listeners.get('click')||[])fn({target});},
    addEventListener(type,fn){const list=listeners.get(type)||[];list.push(fn);listeners.set(type,list);}};
  const window={document,UI:{json(url,options){const d=deferred();pending.push({url,options,...d});return d.promise;},toast(){}},
    addEventListener(type,fn){const list=windowListeners.get(type)||[];list.push(fn);windowListeners.set(type,list);}};
  const context={window,AbortController,URL,Blob,setTimeout(fn){const id=++timerId;timers.set(id,fn);return id;},clearTimeout(id){timers.delete(id);}};
  vm.runInNewContext(source,context,{filename:'web/assets/frontier.js'});
  if(readyState==='loading')for(const fn of listeners.get('DOMContentLoaded')||[])fn();
  const api={document,body,host,pending,timers,window,
    trigger:()=>document.getElementById('frontier-launch'),dialog:()=>document.getElementById('frontier-dialog'),
    node:selector=>body.querySelector(selector),nodes:selector=>body.querySelectorAll(selector),
    pagehide(){for(const fn of windowListeners.get('pagehide')||[])fn();},
    close(){const dialog=this.dialog();if(dialog?.open)dialog.dispatch('cancel');},
    fireTimeout(){const timer=[...timers.values()][0];assert.ok(timer);timer();},
    reloadScript(){vm.runInNewContext(source,context);for(const fn of listeners.get('DOMContentLoaded')||[])fn();}};
  return api;
}
const lab=(marker='LAB')=>({version:'frontier-lab-v1',scope:marker,summary:{task_count:23,valid_tasks:16,invalid_tasks:7,all_obligations_passed:false,strategies:{flat:{valid_verified:2,code_calls:23,false_accepts:0,unverified_metric_outputs:7},plan_only:{valid_verified:2,code_calls:3,false_accepts:0,unverified_metric_outputs:0},active:{valid_verified:16,code_calls:42,false_accepts:0,unverified_metric_outputs:0}}},
  experiments:[{id:'experiment',label:marker,passed:false,details:{finding:marker}}],active_probe:{selected_probe:marker,first_counterexample_calls:{fixed:7,active:1},random_mean:3.5},basis:{scope:marker,registry_size:5,minimum_size:3,enumerated_subsets:32},protocol_sha256:'a'.repeat(64),source_report_sha256:'c'.repeat(64),report_sha256:'b'.repeat(64),evidence_url:'/api/frontier/evidence',boundary:marker});
const scenarios=(marker='SCENARIO')=>({scenarios:[{id:marker,label:marker,description:marker}],boundary:marker});
const run=(marker='RUN')=>({version:'frontier-runtime-v1',status:'evidence_insufficient',goal:[marker],initial:{facts:[marker],checks:[{name:marker,passed:false}]},diagnosis:{state:'unknown',gap:marker},trace:[{operator_id:marker,kind:marker,before:[marker],after:[],execution:{returncode:0,sha256:marker},oracle:{passed:false,checks:[{name:marker,passed:false}]}}],final:{facts:[],checks:[]},oracle:{passed:false},summary:{marker},boundary:marker});
function request(h,url){const match=h.pending.findLast(item=>item.url===url);assert.ok(match,'missing real request '+url);return match;}
async function openReady(h,marker='READY') {
  h.trigger().focus();h.trigger().click();
  request(h,'/api/frontier/lab').resolve(lab(marker));request(h,'/api/frontier/scenarios').resolve(scenarios(marker));await settled();
}

async function checkNavigationAndKeyboard(){
  for(const hostName of ['.product-shell .ui-product-nav','.topbar .wrap','nav','main','body']) {
    const h=harness({hostName});assert.equal(h.trigger().parentNode,hostName==='body'?h.body:h.host);
    h.reloadScript();assert.equal(h.nodes('#frontier-launch').length,1,'script must be idempotent');
    await openReady(h);const dialog=h.dialog(),close=h.node('.frontier-close');assert.equal(h.document.activeElement,close);
    assert.equal(dialog.getAttribute('aria-labelledby'),'frontier-title');
    const nodes=dialog.querySelectorAll('button,select,summary,[href]');const last=nodes.at(-1);
    close.focus();assert.equal(dialog.dispatch('keydown',{key:'Tab',shiftKey:true}),true);assert.equal(h.document.activeElement,last);
    last.focus();assert.equal(dialog.dispatch('keydown',{key:'Tab',shiftKey:false}),true);assert.equal(h.document.activeElement,close);
    assert.equal(dialog.dispatch('keydown',{key:'Escape'}),true);assert.equal(dialog.open,false);assert.equal(h.document.activeElement,h.trigger());
    assert.equal(h.timers.size,0);
  }
}
async function checkAsyncOwnership(){
  const h=harness();h.trigger().focus();h.trigger().click();const a=h.pending.slice();
  assert.equal(a.length,2,'independent GETs start together');h.close();
  assert.ok(a.every(r=>r.options.signal.aborted),'close aborts both requests');h.trigger().click();const b=h.pending.slice(2);
  b.find(r=>r.url.endsWith('/lab')).resolve(lab('CURRENT_B'));b.find(r=>r.url.endsWith('/scenarios')).resolve(scenarios('CURRENT_B'));await settled();
  const current=h.dialog().textContent;a[0].resolve(lab('STALE_A'));a[1].reject(new Error('STALE_FAILURE'));await settled();
  assert.equal(h.dialog().textContent,current,'late success/error must not overwrite new session');
  h.close();h.trigger().click();const closed=h.pending.slice(4);h.close();const snapshot=h.dialog().textContent;
  closed.forEach(r=>r.resolve(r.url.endsWith('/lab')?lab('CLOSED'):scenarios('CLOSED')));await settled();assert.equal(h.dialog().textContent,snapshot);
  h.trigger().click();const leaving=h.pending.slice(6);h.pagehide();const before=h.dialog().textContent;
  leaving.forEach(r=>r.reject(new Error('PAGEHIDE')));await settled();assert.equal(h.dialog().textContent,before);assert.ok(leaving.every(r=>r.options.signal.aborted));assert.equal(h.dialog().open,false,'bfcache return must not retain an aborted loading dialog');h.close();
}
async function checkErrorsAndRecovery(){
  const h=harness();h.trigger().click();request(h,'/api/frontier/lab').reject(new Error('<script>network_failure()</script>'));request(h,'/api/frontier/scenarios').resolve(scenarios());await settled();
  assert.match(h.dialog().textContent,/network_failure/);assert.equal(h.node('script'),null);
  assert.ok(h.node('.frontier-primary'),'lab error must not disable independent execution');
  h.nodes('button').find(b=>b.textContent==='重试读取').click();request(h,'/api/frontier/lab').resolve(lab('RECOVERED'));await settled();assert.match(h.dialog().textContent,/RECOVERED/);
  h.close();h.trigger().click();request(h,'/api/frontier/lab').resolve({});request(h,'/api/frontier/scenarios').resolve({scenarios:[]});await settled();
  assert.match(h.dialog().textContent,/格式不完整/);assert.match(h.dialog().textContent,/没有可实测情景/);assert.equal(h.node('.frontier-primary'),null);h.close();
  const timed=harness();timed.trigger().click();const first=timed.pending[0];timed.fireTimeout();first.reject(Object.assign(new Error('Aborted'),{name:'AbortError'}));await settled();
  assert.match(timed.dialog().textContent,/45 秒/);timed.close();
}
async function checkRealSubmitAndSafety(){
  const payload='<img src=x onerror="payload()"><script>payload()</script>';
  const h=harness();await openReady(h,payload);
  const execute=h.node('.frontier-primary'),select=h.node('select');execute.click();execute.dispatch('click');
  const post=request(h,'/api/frontier/execute');assert.equal(h.pending.filter(r=>r.url.endsWith('/execute')).length,1,'duplicate submit must not execute twice');
  assert.equal(post.options.method,'POST');assert.equal(post.options.headers['Content-Type'],'application/json');assert.deepEqual(JSON.parse(post.options.body),{scenario_id:payload});
  assert.ok(post.options.signal instanceof AbortSignal);assert.equal(execute.disabled,true);assert.equal(select.disabled,true);
  post.resolve(run(payload));await settled();assert.equal(execute.disabled,false);assert.equal(select.disabled,false);
  assert.match(h.dialog().textContent,/证据不足/);assert.ok(h.dialog().textContent.includes(payload));
  assert.equal(h.node('img'),null);assert.equal(h.node('script'),null,'untrusted data remains text, never markup');
  assert.match(h.dialog().textContent,/预注册义务未通过/);assert.match(h.dialog().textContent,/正式排序与奖励未改变/);
  const strategyRows=h.nodes('tbody')[0].children;
  assert.equal(strategyRows[2].children[1].textContent,'16 / 16');assert.equal(strategyRows[2].children[2].textContent,'42');
  assert.equal(strategyRows[0].children[3].textContent,'7');assert.equal(strategyRows[0].children[4].textContent,'0');
  assert.match(h.dialog().textContent,/三组都保留独立 oracle/);assert.match(h.dialog().textContent,/不能据此宣称省成本/);
  const mean=h.nodes('dt').find(n=>n.textContent==='随机基线平均调用');assert.equal(mean.parentNode.children[mean.parentNode.children.indexOf(mean)+1].textContent,'3.5','random_mean follows the real report schema');
  execute.click();const closed=request(h,'/api/frontier/execute');h.close();assert.ok(closed.options.signal.aborted);const snapshot=h.dialog().textContent;closed.resolve(run('LATE_POST'));await settled();assert.equal(h.dialog().textContent,snapshot);
  await openReady(h);h.node('.frontier-primary').click();request(h,'/api/frontier/execute').reject(new Error('需要访问令牌'));await settled();
  assert.match(h.dialog().textContent,/需要访问令牌/);assert.equal(h.node('.frontier-primary').disabled,false);
  assert.ok(!h.nodes('button').some(b=>b.textContent==='重试读取'),'POST is never auto-retried as a read');
  h.node('.frontier-primary').click();request(h,'/api/frontier/execute').resolve({status:'completed',trace:[]});await settled();
  assert.match(h.dialog().textContent,/实测响应不完整/);assert.equal(h.node('.frontier-primary').disabled,false);h.close();assert.equal(h.timers.size,0);
}
async function checkRuntimeReportsAndSnapshotEntry(){
  const h=harness();const snapshot=h.document.createElement('button');snapshot.setAttribute('data-frontier-open','');h.host.append(snapshot);
  // The real Product cards use this delegated control; opening does not execute.
  snapshot.focus();
  h.document.dispatchClick(snapshot);
  assert.equal(h.pending.length,2);assert.equal(h.pending.filter(r=>r.options.method==='POST').length,0);
  request(h,'/api/frontier/lab').resolve(lab());request(h,'/api/frontier/scenarios').resolve(scenarios());await settled();
  h.node('.frontier-primary').click();const actual=run('ACTUAL_FACT');
  actual.initial.checks={state:'failed',checks:[{predicate:{kind:'csv_unique'},state:'failed',detail:'duplicate key witness'}]};
  actual.trace[0].before={facts:['BEFORE_FACT'],checks:actual.initial.checks};
  actual.trace[0].after={facts:['AFTER_FACT'],checks:{state:'passed',checks:[{state:'passed',detail:'observed output'}]}};
  actual.trace[0].oracle=null;
  request(h,'/api/frontier/execute').resolve(actual);await settled();
  assert.match(h.dialog().textContent,/BEFORE_FACT/);assert.match(h.dialog().textContent,/AFTER_FACT/);
  assert.match(h.dialog().textContent,/duplicate key witness/);assert.match(h.dialog().textContent,/本步未提供独立结果判据/);
  h.close();assert.equal(h.document.activeElement,snapshot);
}
async function checkEvidenceLink(){
  const h=harness();await openReady(h);const link=h.node('.frontier-evidence-link');
  assert.equal(link.href,'/api/frontier/evidence');assert.match(h.dialog().textContent,/完整冻结报告指纹/);assert.match(h.dialog().textContent,/当前投影指纹/);
  link.click();link.click();const read=request(h,'/api/frontier/evidence');assert.equal(h.pending.filter(r=>r.url.endsWith('/evidence')).length,1);
  assert.equal(read.options.method,undefined,'evidence is an authenticated read, not execution');
  read.reject(new Error('报告不可读取'));await settled();assert.match(h.dialog().textContent,/报告不可读取/);assert.equal(link.getAttribute('aria-disabled'),null);
  link.click();const late=request(h,'/api/frontier/evidence');h.close();assert.ok(late.options.signal.aborted);const snapshot=h.dialog().textContent;late.resolve({});await settled();assert.equal(h.dialog().textContent,snapshot);
  h.trigger().click();request(h,'/api/frontier/lab').resolve({...lab(),evidence_url:'https://attacker.invalid/steal'});request(h,'/api/frontier/scenarios').resolve(scenarios());await settled();
  assert.equal(h.node('.frontier-evidence-link'),null,'external evidence links must never be accepted');assert.match(h.dialog().textContent,/固定同源路径核对/);h.close();
}
async function checkSubmitFocusRecoveryAndCompactReport(){
  const h=harness();await openReady(h);let execute=h.node('.frontier-primary');
  execute.click();h.document.activeElement=h.body;
  const sample=run('FOCUS_SUCCESS');sample.status='observed_success';sample.oracle={state:'passed',checks:Array.from({length:11},(_,i)=>({id:'check'+i,passed:true}))};
  sample.trace[0].operator_id='deduplicate';sample.trace[0].execution={execution_summary:{input_rows:9,output_rows:8},code_sha256:'a'.repeat(64)};
  sample.trace[0].before={facts:['data.file'],checks:{checks:[]}};sample.trace[0].after={facts:['data.file','data.unique'],checks:{checks:[]}};
  request(h,'/api/frontier/execute').resolve(sample);await settled();assert.equal(h.document.activeElement,execute,'success restores focus lost by disabling submit');
  assert.match(h.dialog().textContent,/实际数据：9 → 8 行/);assert.match(h.dialog().textContent,/本步新确认：样本键唯一/);assert.match(h.dialog().textContent,/独立 oracle：通过 · 11\/11 项/);
  const step=h.node('.frontier-step');assert.equal(step.querySelector('.frontier-data'),null,'step hashes stay in collapsed original evidence');
  execute.click();const close=h.node('.frontier-close');close.focus();request(h,'/api/frontier/execute').resolve(sample);await settled();assert.equal(h.document.activeElement,close,'success must not steal focus already moved inside dialog');
  execute.click();h.document.activeElement=h.body;request(h,'/api/frontier/execute').reject(new Error('FOCUS_FAILURE'));await settled();assert.equal(h.document.activeElement,execute,'failure restores focus lost by disabling submit');
  h.close();
}
(async()=>{
  await checkNavigationAndKeyboard();await checkAsyncOwnership();await checkErrorsAndRecovery();await checkRealSubmitAndSafety();await checkRuntimeReportsAndSnapshotEntry();await checkEvidenceLink();await checkSubmitFocusRecoveryAndCompactReport();
  console.log('Frontier UI: real IIFE navigation, focus, stale/abort/timeout, recovery, POST dedupe, unsafe-data checks passed (controlled DOM).');
})().catch(error=>{console.error(error);process.exitCode=1;});
