/* Execute the real hero module against a controlled DOM. This checks event and
 * request ownership; actual layout and native keyboard behavior need a browser. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../web/assets/hero-explorer.js'),'utf8');
const exported=require('../web/assets/hero-explorer.js');
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const settle=()=>new Promise(resolve=>setImmediate(resolve));
function harness(){
  let document,id=0,listenerCount=0;
  class Element{
    constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.parentNode=null;this.className='';this.id='';this.hidden=false;this.disabled=false;this.value='';this.style={};this.dataset={};this.attributes=new Map();this.handlers=new Map();this._text='';}
    set textContent(value){this._text=String(value);this.replaceChildren();}
    get textContent(){return this._text+this.children.map(c=>c.textContent).join(' ');}
    set innerHTML(_){assert.fail('Catalogue data must never be interpreted as HTML');}
    get isConnected(){return this===document.body||!!this.parentNode?.isConnected;}
    append(...items){for(const item of items){if(item.parentNode)item.parentNode.children=item.parentNode.children.filter(c=>c!==item);this.children.push(item);item.parentNode=this;}}
    prepend(...items){for(const item of items.reverse()){this.children.unshift(item);item.parentNode=this;}}
    replaceChildren(...items){for(const child of this.children)child.parentNode=null;this.children=[];this.append(...items);}
    setAttribute(name,value){this.attributes.set(name,String(value));}
    getAttribute(name){return this.attributes.get(name)??null;}
    contains(item){return item===this||this.children.some(c=>c.contains(item));}
    matches(selector){if(selector.startsWith('#'))return this.id===selector.slice(1);if(selector.startsWith('.'))return this.className.split(' ').includes(selector.slice(1));if(selector.startsWith('['))return this.attributes.has(selector.slice(1,-1));return this.tagName.toLowerCase()===selector;}
    closest(selector){return this.matches(selector)?this:this.parentNode?.closest(selector)||null;}
    querySelectorAll(selector){const found=[];for(const child of this.children){if(child.matches(selector))found.push(child);found.push(...child.querySelectorAll(selector));}return found;}
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
    addEventListener(type,fn){const list=this.handlers.get(type)||[];list.push(fn);this.handlers.set(type,list);listenerCount++;}
    removeEventListener(type,fn){const list=this.handlers.get(type)||[];if(list.includes(fn)){this.handlers.set(type,list.filter(f=>f!==fn));listenerCount--;}}
    dispatch(type,extra={}){let prevented=false;const event={target:this,currentTarget:this,defaultPrevented:false,preventDefault(){this.defaultPrevented=true;prevented=true;},...extra};for(let current=this;current;current=current.parentNode){event.currentTarget=current;for(const fn of current.handlers.get(type)||[])fn(event);}return prevented;}
    click(){if(!this.disabled)this.dispatch('click');}
    focus(){document.activeElement=this;}
  }
  const body=new Element('body'),host=new Element('div'),link=new Element('a');body.append(host,link);
  document={body,activeElement:body,createElement:tag=>new Element(tag),getElementById:id=>body.querySelector('#'+id)};
  const pending=[],timers=new Map(),sphere={selected:null,domainFilter:()=>true,highlighted:[],focused:null,setFilter(fn){this.domainFilter=fn;},highlight(ids){this.highlighted=ids;},select(id){this.selected=id;},focus(id){this.focused=id;this.selected=id;},reset(){this.focused=null;this.selected=null;}};
  const window=new Element('window');window.document=document;window.SkillSphere={color:()=> '#98e6cf'};
  window.setTimeout=fn=>{timers.set(++id,fn);return id;};window.clearTimeout=id=>timers.delete(id);
  window.UI={json(url,options){const d=deferred();pending.push({url,options,...d});return d.promise;}};
  vm.runInNewContext(source,{window,URLSearchParams,AbortController},{filename:'hero-explorer.js'});
  let catalogueRetries=0;const api=window.HeroExplorer.mount({host,graphLink:link,sphere,reload:async()=>{catalogueRetries++;api.setData(graph);}});
  return {api,host,link,document,sphere,pending,timers,window,node:selector=>host.querySelector(selector),nodes:selector=>host.querySelectorAll(selector),listeners:()=>listenerCount,catalogueRetries:()=>catalogueRetries};
}
const graph={nodes:[{id:'pdf<extract>',domain:'研究',source:'github'},{id:'pdf-clean',domain:'研究',generation:1},{id:'stats',domain:'分析'},{id:'plot',domain:'分析'}],edges:[{source:'pdf<extract>',target:'pdf-clean',type:'depend_on'},{source:'pdf-clean',target:'stats',type:'compose_with'},{source:'plot',target:'pdf<extract>',type:'similar_to'},{source:'missing',target:'plot',type:'depend_on'}]};
const detail=(id,purpose)=>({skill:{name:id,description:purpose},passport:{name:id,capability:purpose}});
async function main(){
  const parsed=exported.catalogue({nodes:[...graph.nodes,graph.nodes[0],{id:null}],edges:graph.edges});
  assert.equal(parsed.nodes.length,4);assert.equal(parsed.edges.length,3);assert.equal([...parsed.domains].reduce((n,[,v])=>n+v,0),4);
  const url=new URL(exported.graphURL('a/b?&<x>','中文 & 域'),'https://example.test');assert.equal(url.searchParams.get('skill'),'a/b?&<x>');assert.equal(url.searchParams.get('domain'),'中文 & 域');
  const big=exported.catalogue({nodes:Array.from({length:1881},(_,i)=>({id:'skill-'+i,domain:'领域'+i%57})),edges:[]});assert.equal(big.nodes.length,1881);assert.equal(big.domains.length,57);
  const h=harness();h.api.setData(graph);
  assert.match(h.node('#hero-explorer-scope').textContent,/4 个真实技能/);assert.equal(h.nodes('[data-hero-domain]').length,3);
  const domainButton=()=>h.nodes('[data-hero-domain]').find(b=>b.getAttribute('data-hero-domain')==='研究');
  domainButton().focus();domainButton().click();
  assert.equal(h.api.snapshot().domain,'研究');assert.equal(h.api.snapshot().selected,null);assert.equal(graph.nodes.filter(h.sphere.domainFilter).length,2);assert.equal(h.sphere.selected,null);
  assert.equal(h.document.activeElement.getAttribute('data-hero-domain'),'研究','rebuilding domain choices must preserve keyboard focus');
  assert.equal(new URL(h.link.href,'https://example.test').searchParams.get('domain'),'研究');
  const input=h.node('#hero-skill-search');h.node('.hero-search-panel').open=true;input.value='pdf';input.dispatch('input');assert.equal(h.nodes('[data-hero-skill]').length,2);
  input.focus();assert.equal(input.dispatch('keydown',{key:'ArrowDown'}),true);assert.equal(h.document.activeElement.getAttribute('data-hero-skill'),'pdf<extract>');
  h.document.activeElement.click();assert.equal(h.pending.length,1);assert.equal(h.node('#hero-skill-name').textContent,'pdf<extract>');assert.match(h.node('.hero-skill-source').textContent,/社区导入/);assert.match(h.node('.hero-skill-relations').textContent,/2 条登记关系/);
  assert.equal(h.node('[data-capability-skill]').getAttribute('data-capability-skill'),'pdf<extract>');assert.equal(h.document.activeElement.id,'hero-skill-name');
  const selectedURL=new URL(h.link.href,'https://example.test');assert.equal(selectedURL.searchParams.get('skill'),'pdf<extract>');assert.equal(selectedURL.searchParams.get('domain'),'研究');
  h.pending[0].resolve(detail('pdf<extract>','<script>声明文本</script>'));await settle();
  assert.equal(h.node('.hero-skill-purpose').textContent,'<script>声明文本</script>');assert.equal(h.timers.size,0);
  h.node('.hero-skill-close').focus();h.node('.hero-skill-close').click();assert.equal(h.api.snapshot().selected,null);assert.equal(h.document.activeElement,input,'removed search result returns to stable search input');
  // Switching, toggling or closing invalidates asynchronous successes and errors.
  h.api.select('pdf<extract>');const a=h.pending.at(-1);h.api.select('pdf-clean');const b=h.pending.at(-1);assert.equal(a.options.signal.aborted,true);
  b.resolve(detail('pdf-clean','B用途'));await settle();a.resolve(detail('pdf<extract>','过时用途'));await settle();assert.equal(h.node('.hero-skill-purpose').textContent,'B用途');
  h.api.select('pdf-clean',true);assert.equal(h.api.snapshot().selected,null);
  h.api.select('stats');const closed=h.pending.at(-1);h.node('.hero-skill-close').click();closed.reject(new Error('late error'));await settle();assert.equal(h.node('.hero-skill-card').hidden,true);assert.equal(closed.options.signal.aborted,true);
  // Wrong response identity is visible and retryable; it never rewrites purpose.
  h.api.select('stats');h.pending.at(-1).resolve(detail('other','wrong'));await settle();assert.match(h.node('.hero-skill-purpose').textContent,/不一致/);
  const retry=h.nodes('button').find(b=>b.textContent==='重试读取用途');assert.equal(retry.hidden,false);retry.click();h.pending.at(-1).resolve(detail('stats','统计分析'));await settle();assert.equal(h.node('.hero-skill-purpose').textContent,'统计分析');assert.equal(retry.hidden,true);
  // A request which ignores abort cannot write over timeout/retry ownership.
  h.api.select('plot');const timeout=h.pending.at(-1);assert.equal(h.timers.size,1);[...h.timers.values()][0]();assert.equal(timeout.options.signal.aborted,true);assert.match(h.node('.hero-skill-purpose').textContent,/超时/);assert.equal(h.timers.size,0);
  retry.click();const afterTimeout=h.pending.at(-1);timeout.resolve(detail('plot','timed out'));await settle();assert.notEqual(h.node('.hero-skill-purpose').textContent,'timed out');afterTimeout.resolve(detail('plot','绘图'));await settle();assert.equal(h.node('.hero-skill-purpose').textContent,'绘图');
  // Starting the original DAG hides this dock and prevents hidden selections.
  h.api.select('stats');const duringDAG=h.pending.at(-1),requestCount=h.pending.length;h.api.suspend(true);assert.equal(h.host.hidden,true);assert.equal(duringDAG.options.signal.aborted,true);h.api.select('plot');assert.equal(h.pending.length,requestCount);duringDAG.resolve(detail('stats','late DAG'));await settle();h.api.suspend(false);assert.equal(h.host.hidden,false);assert.equal(h.api.snapshot().selected,null);
  // Repeated live choices use two delegated containers, not accumulating nodes.
  const stableListeners=h.listeners();for(let i=0;i<120;i++){domainButton().click();input.value='pdf';input.dispatch('input');input.value='';input.dispatch('input');}assert.equal(h.listeners(),stableListeners);
  input.value='not-in-library';input.dispatch('input');assert.equal(h.node('#hero-skill-results').hidden,true);assert.match(h.node('.hero-search-status').textContent,/没有匹配/);
  h.api.failed(new Error('<img onerror=alert(1)>'));assert.match(h.node('#hero-explorer-scope').textContent,/<img/);assert.equal(input.disabled,true);h.node('.hero-catalogue-retry').click();await settle();assert.equal(h.catalogueRetries(),1);assert.equal(h.node('.hero-catalogue-retry').hidden,true);assert.equal(input.disabled,false);
  h.api.select('stats');const paused=h.pending.at(-1);h.window.dispatch('pagehide');assert.equal(paused.options.signal.aborted,true);assert.match(h.node('.hero-skill-purpose').textContent,/已暂停/);assert.equal(retry.hidden,false);paused.resolve(detail('stats','late pagehide'));await settle();assert.notEqual(h.node('.hero-skill-purpose').textContent,'late pagehide');
  h.api.setData({nodes:[],edges:[]});assert.equal(input.disabled,true);assert.match(h.node('#hero-explorer-scope').textContent,/0 个真实技能/);
  h.api.setData(graph);assert.equal(input.disabled,false);h.api.select('stats');const destroyed=h.pending.at(-1);h.api.destroy();assert.equal(h.listeners(),0);assert.equal(h.timers.size,0);assert.equal(destroyed.options.signal.aborted,true);destroyed.resolve(detail('stats','destroyed'));await settle();assert.notEqual(h.node('.hero-skill-purpose').textContent,'destroyed');
  const html=fs.readFileSync(path.join(__dirname,'../web/briefing.html'),'utf8');
  assert.ok(html.includes('id="heroNet"')&&html.includes('id="netcv"')&&html.includes('id="demo-seven"')&&html.includes('id="hero-rotate"'));
  assert.ok(html.includes('explorer.suspend(true)')&&html.includes('explorer.suspend(false)'));
  console.log('Hero explorer: true catalogue counts, keyboard entry/focus, domain scope, safe source declarations, exact selection links, request identity/staleness, timeout/retry, close/DAG ownership, 120 filter cycles and teardown passed.');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
