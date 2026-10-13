/* Real rendering/request functions under controlled state; no network or LLM. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const Product=require('../web/assets/product.js');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const between=(source,start,end)=>{const first=source.indexOf(start),last=source.indexOf(end,first);assert.ok(first>=0&&last>first,start);return source.slice(first,last);};
const sha='a'.repeat(64),payload='<img src=x onerror="owned()"><script>owned()</script>';
for(const bad of ['javascript:alert(1)','data:text/html,<script>','file:///secret','//evil.example/x',
  'https://user:password@example.com/','https://example.com:8000/','https://example.com\n/',
  'http://localhost/','http://127.1/','http://2130706433/','http://169.254.169.254/','http://[::1]/'])assert.equal(Product.webURL(bad),'',bad);
assert.equal(Product.webURL('https://example.com/p?a=1&b=2'),'https://example.com/p?a=1&b=2');
assert.equal(Product.webResearchHTML({staged:{}}),'','history must not acquire invented network evidence');
const source={source_id:'web-01',title:'Actual source',url:'https://example.com/p?a=1&b=2',provider:'tavily',
  retrieval_mode:'direct_fetch',state:'fetched',status_code:200,sha256:sha,retrieved_at:'2026-10-13T00:00:00Z',text_file:'web_snapshot_01.txt'};
const run={run_id:'run /?<"',steps:[],artifacts:[],staged:{web_research:{version:'web-test',mode:'on',state:'available',needed:true,
  queries:['public query'],sources:[source,{...source,source_id:'web-02',state:'extracted',retrieval_mode:'provider_extract',status_code:null},
    {...source,source_id:'web-03',state:'blocked',status_code:null,sha256:'',reason:'private destination'}],
  citation_audit:{state:'unknown',rows:2,verified:0,unknown:1,failed:1,items:[{file:'ledger.csv',row:2,state:'unknown',reason:'insufficient identity evidence'}]},
  discovery:{state:'quarantined',candidates:[{name:'skill-x',repo:'owner/repo',source_url:'https://github.com/owner/repo/blob/fixed/SKILL.md',stars:400,commit:'b'.repeat(40),sha256:sha,license:'MIT',state:'quarantined'}]},boundary:'Limited source support'}}};
const html=Product.webResearchHTML(run);
assert.match(html,/原站 HTTP 200/);assert.match(html,/提供方摘录 · 原站未确认/);assert.match(html,/private destination/);
assert.match(html,/1 未确认 \/ 1 未通过/);assert.match(html,/人物已完全消歧/);assert.match(html,/不会自动执行下载脚本/);
assert.match(html,/href="https:\/\/example.com\/p\?a=1&amp;b=2" target="_blank" rel="noopener noreferrer"/);
assert.match(html,/data-run="run \/\?&lt;&quot;" data-file="web_snapshot_01.txt" data-sha="a{64}"/);
assert.match(Product.evidenceHTML(run),/本次任务的网络来源与核验/,'final chat must include the shared view');
const hostile=structuredClone(run);Object.assign(hostile.staged.web_research,{reason:payload,queries:[payload],attempts:[{error:payload}],boundary:payload});
Object.assign(hostile.staged.web_research.sources[0],{title:payload,url:'javascript:'+payload,provider:payload,source_id:payload,text_file:'../../outside.txt',reason:payload,retrieved_at:payload});
hostile.staged.web_research.citation_audit.items=[{file:payload,row:payload,reason:payload,claim:payload,quote:payload,url:'data:text/html,'+payload,state:'unknown'}];
hostile.staged.web_research.discovery.candidates=[{name:payload,repo:payload,source_url:'javascript:alert(1)',stars:Infinity,commit:payload,license:payload,state:payload}];
const safe=Product.webResearchHTML(hostile);
assert.doesNotMatch(safe,/<img|<script|href="javascript:|href="data:|data-file="\.\./);
assert.match(safe,/&lt;img/);assert.match(safe,/地址不可直接打开/);
const unknown=Product.webResearchHTML({run_id:'x',staged:{web_research:{state:'unknown',sources:[{...source,status_code:500}],citation_audit:{}}}});
assert.doesNotMatch(unknown,/原站已打开/);assert.match(unknown,/原站状态未确认/);assert.match(unknown,/尚未检查/);
assert.match(Product.webResearchHTML({staged:{web_research:{state:'disabled',mode:'off'}}}),/本次未发起新采集/);
assert.match(Product.webCapabilitiesText({enabled:true,keyless:true}),/匿名额度/);
assert.match(Product.webCapabilitiesText({enabled:true,keyless:true}),/每次请求中核验/);
assert.match(Product.webCapabilitiesText({enabled:false}),/已停用/);
assert.doesNotMatch(Product.webCapabilitiesText({enabled:true,availability:'unprobed'}),/已连接|已联网|可用$/);
let live=Product.reduceWebEvent(null,'web.search.started',{query:payload},'on');assert.equal(live.state,'searching');
live=Product.reduceWebEvent(live,'web.search.completed',{state:'ok',candidates:2,attempts:[{provider:'tavily'}]});assert.equal(live.state,'checking');
live=Product.reduceWebEvent(live,'web.source.checked',source);live=Product.reduceWebEvent(live,'web.source.checked',{...source,state:'failed'});
assert.equal(live.sources.length,1);assert.equal(live.sources[0].state,'failed');assert.equal(live.mode,'on');
live=Product.reduceWebEvent(live,'web.citations.checked',{state:'unknown',verified:0,unknown:1,failed:0});assert.equal(live.citation_audit.state,'unknown');
assert.doesNotMatch(Product.webResearchHTML({web_research:live}),/<img|<script/);
assert.match(Product.webEventText('web.search.completed',{candidates:2}),/候选仍需打开核验/);
assert.match(Product.webEventText('web.source.checked',{state:'extracted',retrieval_mode:'provider_extract'}),/提供方摘录/);
const referenceOnly=Product.reduceWebEvent(null,'web.skills.discovered',{reference_only:true,needed:false,reason:'仅补充隔离方法参考',candidates:[]});
assert.equal(referenceOnly.needed,false);assert.equal(referenceOnly.reference_only,true);assert.equal(referenceOnly.state,'not_needed');
assert.match(Product.webResearchHTML({web_research:referenceOnly}),/仅补充隔离方法参考/);
assert.doesNotMatch(Product.webResearchHTML({web_research:referenceOnly}),/原站已打开|正在核验来源/);

async function dialogOwnership(){
  const sourceCode=read('web/assets/product.js'),code=between(sourceCode,'async function inspectWebEvidence(button){','async function inspectValue(button){');
  let generation=0;const pending=[],dialog={innerHTML:''},errors=[];
  const context={root:{UI:{json:url=>new Promise((resolve,reject)=>pending.push({url,resolve,reject}))}},
    beginPanel(){const mine=++generation;return {dialog,current:()=>mine===generation,fail:error=>{if(mine===generation){errors.push(String(error));dialog.innerHTML=Product.esc(String(error));}}};},
    contextText:value=>typeof value==='string'?value:'',esc:Product.esc,webResearchHTML:Product.webResearchHTML,encodeURIComponent};
  vm.createContext(context);vm.runInContext(code+';globalThis.inspect=inspectWebEvidence;',context);
  const buttonA={dataset:{run:'run-A'},disabled:false},buttonB={dataset:{run:'run-B'},disabled:false};
  const a=context.inspect(buttonA),b=context.inspect(buttonB);
  assert.equal(buttonA.disabled,true);assert.equal(buttonB.disabled,true);
  pending[1].resolve({...run,run_id:'run-B'});await b;const latest=dialog.innerHTML;
  pending[0].resolve({...run,run_id:'run-A',staged:{web_research:{state:'failed',reason:'stale result must not appear'}}});await a;
  assert.equal(dialog.innerHTML,latest);assert.equal(buttonA.disabled,false);assert.equal(buttonB.disabled,false);
  const mismatch=context.inspect(buttonA);pending[2].resolve({...run,run_id:'different-run'});await mismatch;
  assert.match(dialog.innerHTML,/运行身份不匹配/);assert.doesNotMatch(dialog.innerHTML,/Actual source/);
  const unavailable=context.inspect(buttonA);pending[3].reject(new Error('injected unavailable'));await unavailable;
  assert.match(dialog.innerHTML,/injected unavailable/);assert.equal(buttonA.disabled,false);
  assert.equal(pending[0].url,'/api/runs/run-A');
  const closed=context.inspect(buttonA);generation++;pending[4].resolve({...run,run_id:'run-A'});await closed;
  assert.match(dialog.innerHTML,/injected unavailable/,'closed dialog must not receive a late source view');
}
async function requestModes(){
  const chat=read('web/chat.html'),submit=between(chat,'async function submitQ(){','async function stream(');
  for(const mode of ['auto','on','off']){
    const elements=new Map(),session={title:'',turns:[]},requests=[];
    const element=id=>{if(!elements.has(id))elements.set(id,{value:'',style:{},textContent:'',disabled:false,scrollHeight:30});return elements.get(id);};
    element('q').value='Public research question';element('web-mode').value=mode;
    const context={API:'',busy:false,activeRun:null,cur:()=>session,newSession:()=>assert.fail('unexpected new session'),
      document:{getElementById:id=>/^acard-/.test(id)?null:element(id),querySelector:()=>element('newbtn')},
      saveSessions(){},renderSidebar(){},renderMain(){},UI:{errorHTML:error=>Product.esc(error.message),
        async fetch(url,options){assert.equal(element('web-mode').disabled,true);requests.push({url,...options});return {ok:false,status:503,json:async()=>({detail:'injected unavailable'})};}},
      Date,JSON,Error,Number,encodeURIComponent};
    vm.createContext(context);vm.runInContext(submit+';globalThis.submit=submitQ;',context);await context.submit();
    assert.equal(requests.length,1);assert.equal(requests[0].url,'/api/runs');assert.equal(JSON.parse(requests[0].body).web_mode,mode);
    assert.equal(session.turns[0].web_mode,mode);assert.equal(element('web-mode').disabled,false);assert.equal(element('send').disabled,false);
    assert.equal(session.turns[0].status,'error','unavailable service must not create a completed result');
  }
  assert.match(chat,/option value="auto"/);assert.match(chat,/option value="on"/);assert.match(chat,/option value="off"/);
  assert.match(chat,/jget\('\/api\/web\/capabilities',8000\)/);assert.match(chat,/Product.webResearchHTML\(model/);
  const runPage=read('web/run.html');assert.match(runPage,/Product.webResearchHTML\(RUN/);assert.match(runPage,/data-web-evidence/);
  assert.match(runPage,/Product.reduceWebEvent\(LIVE_WEB_REPORT/);assert.match(runPage,/case 'web.citations.checked'/);
  assert.match(read('web/assets/product.js'),/run.run_id!==id/,'network evidence modal must validate run identity');
}
Promise.all([requestModes(),dialogOwnership()]).then(()=>{console.log('Web research UI: 3 real request modes, source vs provider extract, unknown vs pass, exact run snapshot links, source/SSE escaping, malicious URL rejection, historical absence and evidence dialog identity/stale/error ownership passed (controlled state; no browser rendering claim).');}).catch(error=>{console.error(error);process.exitCode=1;});
