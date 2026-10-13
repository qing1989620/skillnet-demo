/* Exercise real graph event handlers in a controlled DOM; visual QA remains a browser check. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const core=require('../web/assets/graph-sphere.js'),product=require('../web/assets/product.js');
const source=fs.readFileSync(path.resolve(__dirname,'../web/assets/graph-sphere.js'),'utf8');
const relations=new Set(['depend_on','compose_with','similar_to']);
const nodes=[{id:'alpha',domain:'D1'},{id:'beta',domain:'D2'},{id:'gamma',domain:'D1',generation:1},{id:'orphan',domain:'D1'}];
const edges=[{source:'alpha',target:'beta',type:'depend_on'},{source:'gamma',target:'alpha',type:'depend_on'},
  {source:'beta',target:'alpha',type:'compose_with'},{source:'alpha',target:'gamma',type:'similar_to'},
  {source:'alpha',target:'beta',type:'depend_on'},{source:'alpha',target:'alpha',type:'similar_to'}];
const rows=core.relationRows('alpha',edges,relations);
assert.deepEqual(rows.map(r=>r.label),['依赖 beta','被 gamma 依赖','与 beta 组合','相似候选 · gamma']);
assert.deepEqual(core.relationRows('beta',edges,relations).map(r=>r.label),['被 alpha 依赖','与 alpha 组合']);
assert.deepEqual(core.relationRows('alpha',edges,new Set(['similar_to']),new Set(['alpha','beta'])),[]);
assert.deepEqual(core.relationRows('orphan',edges,relations),[]);
const filter={domain:'D1',taskOnly:true,task:new Set(['alpha','beta']),relations,neighbors:true};
assert.deepEqual(nodes.filter(n=>core.nodeVisible(n,filter,nodes[0],edges,false)).map(n=>n.id),['alpha']);
filter.domain='';assert.deepEqual(nodes.filter(n=>core.nodeVisible(n,filter,nodes[0],edges,false)).map(n=>n.id),['alpha','beta']);
filter.taskOnly=false;assert.deepEqual(nodes.filter(n=>core.nodeVisible(n,filter,nodes[0],edges,true)).map(n=>n.id),['gamma']);
const visits=core.history();assert.equal(visits.back(),null);visits.visit('alpha');visits.visit('alpha');visits.visit('beta');visits.visit('gamma');
assert.equal(visits.back(),'beta');visits.visit('orphan');assert.equal(visits.back(),'beta');assert.equal(visits.back(),'alpha');assert.equal(visits.back(),null);
const attack='<img src=x onerror="attack()">';
const run={run_id:'RUN & frozen',skills:['alpha','retired-skill'],artifacts:[{name:'history_123_input.csv',logical_name:'raw.csv',sha256:'a'.repeat(64),source_run_id:'SOURCE-RUN'}],
  staged:{state_policy:{frozen:{'2':{sha256:'frozen-2'}}},state_composition:{frontier:[{step_idx:2,file:'raw.csv',detail:attack},{step_idx:8,file:'other.csv',detail:'OTHER_FRONTIER'}]},
    quality_assessment:{observations:[{idx:2,independent_checks:[{name:'independent.exact',passed:false,detail:attack}]}]}},
  steps:[{idx:2,skill:'alpha',status:'done',action:attack,contract:{input_files:['raw.csv'],output_files:['clean.csv']},
    input_artifacts:[{logical_name:'raw.csv',name:'history_123_input.csv',sha256:'a'.repeat(64)}],
    artifacts:[{name:'step3_clean.csv',logical_name:'clean.csv',bytes:10,sha256:'b'.repeat(64),from_step:2}],
    checks:[{name:'required.one',passed:true,required:true},{name:'optional.skip',passed:false,required:false}],
    state_evidence:{pre:{state:'passed',admitted:true,checks:[]},post:{state:'unknown',checks:[]}}},
  {idx:8,skill:'manual',status:'pending',action:'MANUAL_ACTION',contract:{output_files:['expected-not-produced.csv']}},
  {idx:12,skill:'retired-skill',status:'failed',action:'RETIRED_ACTION'},
  {idx:20,skill:'beta',status:'done',action:'BETA_ACTION'}]};
assert.equal(core.taskView(run,'step:8').step.idx,8);assert.deepEqual(core.taskView(run,'step:8').names,[]);
assert.equal(core.taskView(run,'step:12').names[0],'retired-skill');assert.equal(core.taskView(run,'step:0').key,'all');
const detail=core.taskDetailHTML(run,core.taskView(run,'step:2'),product);
assert.ok(detail.includes('data-kernel-step="2"')&&!detail.includes('data-kernel-step="0"'));
assert.ok(detail.includes('data-run="RUN &amp; frozen"')&&detail.includes('data-file="history_123_input.csv"'));
assert.ok(detail.includes('来自运行 SOURCE-RUN')&&!detail.includes('data-run="SOURCE-RUN"'),'copied cross-run inputs are read by their current-run registered name; source_run_id is provenance only');
assert.ok(detail.includes('必要检查 1/1 · 独立结果检查 0/1')&&!detail.includes('optional.skip'));
assert.ok(detail.includes('产物效果</b> 无法核实')&&detail.includes('frozen-2'));
assert.ok(detail.includes('&lt;img')&&!detail.includes('<img')&&!detail.includes('OTHER_FRONTIER'));
const manual=core.taskDetailHTML({...run,staged:{}},core.taskView(run,'step:8'),product);
assert.ok(manual.includes('通用执行 · 未绑定技能')&&manual.includes('前后条件实测：未知'));
assert.ok(manual.includes('未登记实际产物')&&manual.includes('expected-not-produced.csv'));
const all=core.taskDetailHTML(run,core.taskView(run),product);
assert.ok(all.includes('data-graph-step="step:20"')&&all.includes('Step 21')&&all.includes('Step 9'));

const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function settled(){await tick();await tick();}
function harness(query='?run=RUN%20%26%20frozen&step=8'){
  const pending=[],listeners=new Map(),windowListeners=new Map(),elements=new Map();let document;
  const decode=s=>s.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
  class Element{
    constructor(id=''){this.id=id;this.children=[];this.parent=null;this.dataset={};this.disabled=false;this.hidden=false;this.checked=true;this.style={};this.value='';this._html='';this._text='';this.attributes={};const names=new Set();this.classList={add:n=>names.add(n),remove:n=>names.delete(n),toggle:(n,on)=>{on?names.add(n):names.delete(n);},contains:n=>names.has(n)};}
    set innerHTML(value){this._html=String(value);this._text='';this.children=[];for(const match of this._html.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)){const button=new Element();for(const attr of match[1].matchAll(/([\w-]+)="([^"]*)"/g)){button.attributes[attr[1]]=decode(attr[2]);if(attr[1].startsWith('data-'))button.dataset[attr[1].slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=decode(attr[2]);}button._html=match[2];this.append(button);}}
    get innerHTML(){return this._html;}
    set textContent(value){this._text=String(value);this._html='';this.children=[];}
    get textContent(){return this._text||this._html.replace(/<[^>]*>/g,'');}
    append(child){child.parent=this;this.children.push(child);}
    contains(node){return node===this||this.children.some(c=>c.contains(node));}
    get isConnected(){return this===document.body||!!this.parent?.isConnected;}
    focus(){document.activeElement=this;}
    setAttribute(name,value){this.attributes[name]=String(value);}
    insertAdjacentHTML(_,value){this._html+=String(value);}
    querySelectorAll(selector){const found=[];const visit=node=>{for(const c of node.children){if(selector.startsWith('[')&&c.attributes[selector.slice(1,-1)]!==undefined)found.push(c);visit(c);}};visit(this);return found;}
    querySelector(selector){if(selector==='.close')return this.children.find(c=>c.id==='close');return this.querySelectorAll(selector)[0]||null;}
    closest(){return null;}
    click(){if(!this.disabled)this.onclick?.({target:this});}
  }
  const body=new Element('body');
  document={body,activeElement:body,getElementById:id=>elements.get(id),querySelectorAll:selector=>selector==='[data-relation]'?relationInputs:[],addEventListener(type,fn){listeners.set(type,fn);}};
  const html=fs.readFileSync(path.resolve(__dirname,'../web/graph.html'),'utf8');
  for(const match of html.matchAll(/\bid="([^"]+)"/g)){const element=new Element(match[1]);elements.set(element.id,element);body.append(element);}
  const card=elements.get('card'),close=new Element('close');card.append(close);
  elements.get('graph-task-only').checked=false;elements.get('graph-neighbors').checked=false;
  for(const id of ['cName','cDom','cKv','cRel','cContract','cContractLink','graph-back','graph-card-context','graph-selected-note'])card.append(elements.get(id));
  const relationInputs=['depend_on','compose_with','similar_to'].map(type=>{const e=new Element();e.dataset.relation=type;return e;});
  const scene={highlighted:[],statuses:[],focuses:[],zoomed:[],selected:null,paused:true,
    setData(g){this.data=g;},setFilter(fn,types){this.visible=nodes.filter(fn).map(n=>n.id);this.relations=[...types];},
    highlight(names){this.highlighted=[...names];},states(states){this.statuses=[...states];},select(id){this.selected=id;},focus(id){this.focuses.push(id);},
    zoom(value){this.zoomed.push(value);},reset(){this.resetCalled=true;},pause(){this.paused=!this.paused;this.options.onPause(this.paused);},labels(value){this.showLabels=value;},
    snapshot(){return {paused:this.paused};}};
  const location={href:'http://localhost/graph'+query,search:query};
  const window={document,history:{replaceState(_,__,value){const url=new URL(value);location.href=url.href;location.search=url.search;}},
    addEventListener(type,fn){windowListeners.set(type,fn);}};
  const context={window,document,URL,URLSearchParams,location,AbortController,Product:product,Set,Map,innerWidth:1440,innerHeight:900,
    UI:{esc:core.esc,json(url,options={}){const d=deferred();pending.push({url,options,...d});return d.promise;},toast(message){window.toast=message;}},
    SkillSphere:{create(canvas,options){scene.options=options;return scene;}},matchMedia:()=>({matches:true})};
  vm.runInNewContext(source,context,{filename:'graph-sphere.js'});
  return {elements,pending,relationInputs,scene,location,window,listeners,document};
}
function request(h,url){const item=h.pending.findLast(p=>p.url===url);assert.ok(item,'expected '+url);return item;}
async function ready(h){request(h,'/api/graph').resolve({nodes,edges});await settled();request(h,'/api/runs/RUN%20%26%20frozen').resolve(run);await settled();}
function choose(h,key){const select=h.elements.get('graph-step');select.value=key;select.onchange({target:select});}
function change(h,id,value){const element=h.elements.get(id);if(typeof value==='boolean')element.checked=value;else element.value=value;element.onchange({target:element});}
async function handlers(){
  const h=harness();await ready(h);
  assert.deepEqual(h.scene.highlighted,[],'query step=8 selects a manual step, not array index 8');
  assert.match(h.elements.get('graph-task-note').textContent,/Step 9.*通用执行/);
  assert.match(h.elements.get('graph-step').innerHTML,/value="step:20">Step 21/);
  choose(h,'step:2');assert.deepEqual(h.scene.highlighted,['alpha']);assert.ok(h.elements.get('graph-task-detail').innerHTML.includes('data-kernel-step="2"'));
  assert.equal(new URL(h.location.href).searchParams.get('run'),run.run_id);assert.equal(new URL(h.location.href).searchParams.get('step'),'2');
  choose(h,'step:12');assert.deepEqual(h.scene.highlighted,['retired-skill']);assert.match(h.elements.get('graph-task-note').textContent,/retired-skill 不在当前库/);
  choose(h,'all');assert.equal(new URL(h.location.href).searchParams.has('step'),false);change(h,'graph-task-only',true);
  assert.deepEqual(h.scene.visible,['alpha','beta']);
  h.elements.get('graph-q').focus();h.scene.options.onSelect(nodes[0]);const first=request(h,'/api/skill/alpha');
  assert.match(h.elements.get('cRel').innerHTML,/当前筛选下 2 条关系/);assert.ok(!h.elements.get('cRel').innerHTML.includes('被 gamma'));
  h.relationInputs[0].checked=false;h.relationInputs[0].onchange();assert.match(h.elements.get('cRel').innerHTML,/当前筛选下 1 条关系/);
  change(h,'graph-domain','D1');assert.match(h.elements.get('cRel').textContent,/没有可见关系/);assert.match(h.elements.get('graph-task-note').textContent,/1 项被当前筛选隐藏/);
  change(h,'graph-domain','');h.relationInputs[0].checked=true;h.relationInputs[0].onchange();change(h,'graph-task-only',false);change(h,'graph-neighbors',true);
  assert.deepEqual(h.scene.visible,['alpha','beta','gamma']);assert.match(h.elements.get('cRel').textContent,/被 gamma 依赖/);
  const beta=h.elements.get('cRel').querySelectorAll('[data-related]').find(b=>b.dataset.related==='beta');beta.click();
  const second=request(h,'/api/skill/beta');assert.ok(first.options.signal.aborted);
  second.resolve({skill:{description:'CURRENT_BETA'},passport:{}});await settled();
  first.resolve({skill:{description:'STALE_ALPHA'},passport:{}});await settled();assert.ok(h.elements.get('cContract').innerHTML.includes('CURRENT_BETA')&&!h.elements.get('cContract').innerHTML.includes('STALE_ALPHA'));
  assert.match(h.elements.get('cRel').textContent,/被 alpha 依赖/);
  h.elements.get('graph-back').click();assert.equal(h.elements.get('cName').textContent,'alpha');
  assert.ok(h.elements.get('graph-card-context').textContent.includes(run.run_id));assert.equal(h.elements.get('graph-step').value,'all');
  assert.equal(new URL(h.location.href).searchParams.get('run'),run.run_id);assert.equal(h.elements.get('graph-back').disabled,true);
  const returning=request(h,'/api/skill/alpha');h.elements.get('card').querySelector('.close').click();const snapshot=h.elements.get('cContract').innerHTML;
  assert.ok(returning.options.signal.aborted);returning.resolve({skill:{description:'CLOSED_RESPONSE'}});await settled();assert.equal(h.elements.get('cContract').innerHTML,snapshot);
  assert.equal(h.document.activeElement,h.elements.get('graph-q'));
  h.scene.options.onSelect(nodes[3]);assert.match(h.elements.get('cRel').textContent,/尚未登记此类关系/);
  h.elements.get('btnZoomIn').click();h.elements.get('btnZoomOut').click();assert.deepEqual(h.scene.zoomed,[1.2,1/1.2]);
  h.elements.get('btnPause').click();assert.equal(h.scene.paused,false);h.elements.get('btnLabel').click();assert.equal(h.scene.showLabels,false);
  const ignoredEvent={key:'Escape',defaultPrevented:true,target:h.elements.get('cName')};h.listeners.get('keydown')(ignoredEvent);assert.equal(h.scene.selected,'orphan');
  const q=h.elements.get('graph-q');q.value='beta';q.oninput({target:q});let prevented=false;q.onkeydown({key:'Enter',preventDefault(){prevented=true;}});
  assert.equal(prevented,true);assert.equal(h.scene.selected,'beta');assert.equal(h.elements.get('graph-domain').value,'');
  choose(h,'step:8');assert.deepEqual(h.scene.highlighted,[]);assert.ok(h.elements.get('graph-card-context').textContent.includes('Step 9'));
  const latest=request(h,'/api/skill/beta');
  h.window && h.listeners.get('keydown')({key:'Escape',defaultPrevented:false,target:q});assert.ok(latest.options.signal.aborted);
  assert.deepEqual(h.scene.highlighted,[],'closing a skill keeps the manual task overlay');
  h.elements.get('btnReset').click();assert.equal(h.scene.resetCalled,true);assert.equal(h.elements.get('graph-step').value,'step:8');
  const noRun=harness('');request(noRun,'/api/graph').resolve({nodes,edges:[]});await settled();assert.equal(noRun.elements.get('load').hidden,true);
  noRun.scene.options.onSelect(nodes[0]);assert.match(noRun.elements.get('cRel').textContent,/尚未登记此类关系/);assert.equal(noRun.elements.get('graph-card-context').textContent,'探索当前目录');
}
handlers().then(()=>console.log('Graph explorer: directed declarations, live filters, history, stale passport isolation, original step indices, manual/missing skills, actual evidence, URL context and retained globe controls passed.')).catch(error=>{console.error(error);process.exitCode=1;});
