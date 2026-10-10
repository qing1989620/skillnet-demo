/* A question drives one real Run. The stage projects its persisted events, never simulations. */
(function (root) {
  'use strict';
  const PHASES = [
    {name:'检索能力',tag:'BM25 · HYBRID · FABRIC',title:'先找到适合这道题的能力',doing:'关键词、语义与关系图围绕同一问题检索。候选技能和实际启用的检索组件会在这里出现。',benefit:'把能力定位变成可追溯的选择过程，便于发现漏选和误选。'},
    {name:'策略选择',tag:'SHARED LINUCB / SHADOW',title:'先提出可检验的选择假设',doing:'共享 LinUCB 分解收益预测与探索项；当前正式权重从零开始，收益预测可能为零，它们不是成功概率。新增经验只做影子预演，尚未部署学习后的排序参数。',benefit:'保留可追溯的选择依据，避免一次偶然结果污染整个网络。'},
    {name:'关系编排',tag:'WIKI · DEPENDENCIES',title:'把单项能力组织成协作',doing:'路由器读取技能关系与依赖，确定采用的技能和编排边。降级路径也会明确展示。',benefit:'先明确谁依赖谁，减少任务顺序与输入输出脱节。'},
    {name:'方案与 DAG',tag:'PLAN → EXECUTION GRAPH',title:'把研究方案变成执行路径',doing:'规划器生成动作，执行引擎再解析真实步骤依赖。图中的每个节点都对应一个可查证的运行步骤。',benefit:'计划可以被逐步执行和追踪，前序文件能进入后序步骤。'},
    {name:'执行与修复',tag:'PYTHON · RETRY · ARTIFACTS',title:'让能力真正产出结果',doing:'生成代码、语法预检、运行 Python；失败后携带错误信息与技能陷阱进行修复，每步最多尝试三次。',benefit:'交付可下载的真实文件，保留失败原因与修复轨迹。'},
    {name:'分层验收',tag:'FROZEN REFERENCE / ARTIFACT HASH',title:'先展示判据，再判断结果',doing:'服务端重新读取文件并验证指纹；有独立参考的结果逐项重算。模型评分仅供参考，没有结果判据就保留未知。',benefit:'区分技术执行成功、目标结果正确和用户认可，判断边界可以核对。'},
    {name:'反馈与进化',tag:'OBSERVATION → SHADOW → HOLD-OUT',title:'一条经验，先成为待验证的假设',doing:'单次经验只进入影子观察。合格轨迹可隔离为候选；至少五道留出任务、每题两组同预算对照，并满足无回退与统计门槛后才有资格晋级。',benefit:'不把参数变化当成网络提升；只在已测范围内陈述增益，保留未知和失败。'}
  ];
  const esc = x => String(x == null ? '' : x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const arr = x => Array.isArray(x) ? x : [];
  const number = (x, fallback=0) => Number.isFinite(Number(x)) ? Number(x) : fallback;
  const statusName = s => ({COMPLETED:'已完成',PARTIAL:'部分完成',FAILED:'失败',CANCELLED:'已取消',BUDGET_EXCEEDED:'预算已达上限',INTERRUPTED:'运行中断'}[s] || s || '待启动');
  const stepName = s => ({pending:'待执行',running:'执行中',done:'已完成',failed:'失败',skipped:'已跳过'}[s] || '待执行');
  const PUBLIC_REPLAY_ID='f11ad204-20261010-110841-6d42';
  function createState(task='',mode='idle') {
    return {task,mode,id:null,seq:0,phase:0,view:null,phases:PHASES.map(()=> 'pending'),nodes:[],selected:[],ranking:[],retrieval:{},orchestration:{},checks:[],artifacts:[],feedback:[],judge:null,evolution:null,logs:[],started:0,elapsed:0,finished:false,error:'',snapshot:null};
  }
  function reduceEvent(s,ev) {
    if (!ev || typeof ev.type !== 'string') return false;
    const seq = number(ev.seq);
    if (seq > 0 && seq <= s.seq) return false;
    if (seq > 0) s.seq = seq;
    const d = ev.data || {}, t = ev.type;
    const idx = Number.isInteger(ev.step) ? ev.step : d.step;
    const node = () => s.nodes.find(n=>n.idx===idx);
    const complete = i => {s.phases[i]='done'; if(i<6) {s.phase=Math.max(s.phase,i+1);if(s.phases[i+1]==='pending')s.phases[i+1]='running';}};
    if (!s.started && ev.ts_ms) s.started = ev.ts_ms;
    if (ev.ts_ms && s.started) s.elapsed = Math.max(0,ev.ts_ms-s.started);
    let log='';
    if(t==='run.started') {s.phases[0]='running';log='问题已进入框架，开始检索技能';}
    else if(t==='retrieval.completed') {s.selected=arr(d.selected);s.retrieval=d;complete(0);log=`检索完成 · 推荐 ${s.selected.length} 个技能，供后续编排核对`;}
    else if(t==='ranking.completed') {s.ranking=arr(d.entries);complete(1);log=`策略排序完成 · 首位 ${d.top || '无候选'}`;}
    else if(t==='orchestration.completed') {s.orchestration=d;s.selected=arr(d.order || d.skills);complete(2);log=`编排采用 ${s.selected.length} 项技能 · ${arr(d.edges).length} 条关系`;}
    else if(t==='plan.created') {s.approach=d.approach || '';s.planSteps=number(d.steps);complete(3);log=`方案已生成 · ${s.planSteps} 个规划动作`;}
    else if(t==='dag.ready') {s.nodes=arr(d.nodes).filter(n=>Number.isInteger(n.idx)).map(n=>({...n,status:'pending'}));log=`执行 DAG 就绪 · ${s.nodes.length} 步 · 依赖来自 ${d.workflow_source || '执行引擎'}`;}
    else if(t==='step.inputs') {if(node())node().inputs=arr(d.files);log=`Step ${number(idx)+1} 收到 ${arr(d.files).length} 个前序文件`;}
    else if(t==='step.started') {if(node())node().status='running';log=`Step ${number(idx)+1} 开始 · ${d.skill || '通用动作'}`;}
    else if(t==='code.generating') {if(node()){node().attempt=number(d.attempt);node().stage='generating';}log=`Step ${number(idx)+1} · ${number(d.attempt)>1?'根据错误修复代码':'模型生成可运行代码'}`;}
    else if(t==='code.generated') {if(node()){node().code=d.code || '';node().stage='syntax';}log=`Step ${number(idx)+1} · 代码生成完成，进入语法预检`;}
    else if(t==='sandbox.started') {if(node())node().stage='sandbox';log=`Step ${number(idx)+1} · Python 正在实际运行`;}
    else if(t==='step.attempt') {if(node()){node().attempt=number(d.attempt);node().stdout=d.stdout || '';node().stderr=d.stderr || '';} log=`Step ${number(idx)+1} · 第 ${d.attempt} 次运行${d.ok?'成功':'失败 · '+(d.error_kind || '见运行记录')}`;}
    else if(t==='step.retry') log=`Step ${number(idx)+1} · 自动修复：${d.reason || '执行错误'}`;
    else if(t==='artifact.created') {if(!s.artifacts.some(a=>a.name===d.name))s.artifacts.push({...d,from_step:idx});log=`真实文件已登记 · ${d.name}`;}
    else if(t==='verification.started') {if(node())node().stage='verify';log=`Step ${number(idx)+1} · 进入文件检查与技能验收`;}
    else if(t==='check.result') {if(d.required!==false)s.checks.push({...d,step:idx});log=`${d.passed?'通过':'未通过'} · Step ${number(idx)+1} · ${d.name}`;}
    else if(t==='verification.result') log=`${d.passed?'通过':'未通过'} · 语义验收 · ${d.item || ''}`;
    else if(t==='step.completed') {if(node()){node().status=d.status;node().stage='done';node().checks=d.checks;node().duration_ms=d.duration_ms;node().attempt=number(d.n_attempts);}log=`Step ${number(idx)+1} ${stepName(d.status)} · 程序检查 ${d.checks || '—'}`;}
    else if(t==='steps.skipped') {arr(d.steps).forEach(i=>{const n=s.nodes.find(x=>x.idx===i);if(n)n.status='skipped';});log='依赖失败，跳过受影响的下游步骤';}
    else if(t==='execution.finished') {complete(4);log=`执行结束 · ${number(d.done)} 步完成 / ${number(d.failed)} 步失败`;}
    else if(t==='evaluation.completed') {s.assessment=d.assessment;s.shadow=d.shadow;s.rewardGates=d.reward_gates;log=d.reward_gates?`奖励门禁 ${d.reward_gates.passed}/${d.reward_gates.total} 通过 · 缺证据不发奖`:'独立结果核验完成 · 正式网络保持不变';}
    else if(t==='evaluation.gates_updated') {s.rewardGates=d.reward_gates;log=`最终奖励门禁 ${d.reward_gates.passed}/${d.reward_gates.total} 通过 · ${d.reward_gates.eligible?'具备领奖资格':'本次不发奖'}`;}
    else if(t==='judge.completed') {s.judge=d;complete(5);log=d.score_valid===false?'评审不可用 · 跳过反馈学习':`方案评审完成 · ${d.weighted == null?'分数不可用':d.weighted+'/10'}`;}
    else if(t==='evolution.proposed') {s.evolution=d;s.feedback=arr(d.feedback);s.phases[6]='done';s.phase=6;log=d.candidate?'新经验进入候选区 · 等待冻结任务验证':d.accepted?`新增能力已准入 · ${d.name}`:(d.skipped?(d.skip_reason||'未满足学习门槛，未进行技能准入'):'本次未新增技能 · 保留现有能力');}
    else if(t==='run.reply') {s.reply=d.text || '';log='基于真实执行事实生成最终回答';}
    else if(t==='run.cancel_requested') log='取消请求已提交 · 等待当前操作结束';
    else if(['run.error','run.failed','run.cancelled','run.budget_exceeded'].includes(t)) {s.error=d.reason || d.error || '运行未完成';s.phases[s.phase]='failed';log=s.error;}
    else if(t==='run.finished') {s.finished=true;s.status=d.status;s.elapsed=number(d.duration_ms,s.elapsed);log=`${statusName(d.status)} · 运行记录已保存`;}
    if(log) s.logs.push({time:s.elapsed,text:log});
    s.logs=s.logs.slice(-80);
    return true;
  }
  function dagLayout(nodes,narrow=false) {
    const by=new Map(nodes.map(n=>[n.idx,n]));const depths=new Map();
    function depth(i,path=new Set()) {if(depths.has(i))return depths.get(i);if(path.has(i))return 0;const next=new Set(path);next.add(i);const deps=arr(by.get(i)?.depends_on).filter(d=>by.has(d)&&d!==i);const d=deps.length?1+Math.max(...deps.map(x=>depth(x,next))):0;depths.set(i,d);return d;}
    nodes.forEach(n=>depth(n.idx));
    const max=Math.max(0,...depths.values()),groups=new Map();
    nodes.forEach(n=>{const d=depths.get(n.idx);if(!groups.has(d))groups.set(d,[]);groups.get(d).push(n.idx);});
    const widest=Math.max(1,...[...groups.values()].map(g=>g.length));
    const width=narrow?Math.max(360,widest*90+40):640, height=narrow?Math.max(124,(max+1)*94+26):Math.max(250,...[...groups.values()].map(g=>g.length*94+30));
    const boxW=narrow?Math.min(270,(width-40-12*(widest-1))/widest):Math.min(186,570/(max+1));
    const points=new Map();groups.forEach((group,d)=>group.forEach((id,i)=>points.set(id,narrow?{x:(width-group.length*boxW-(group.length-1)*12)/2+i*(boxW+12),y:20+d*94,w:boxW,h:76}:{x:22+(width-44-boxW)*(max?d/max:.5),y:height/(group.length+1)*(i+1)-38,w:boxW,h:76})));
    return {width,height,points};
  }
  // Quote-aware parser for evidence previews, including newlines inside quoted cells.
  function parseCSV(text) {
    const rows=[];let row=[],cell='',quoted=false;
    for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);rows.push(row);row=[];cell='';}else cell+=c;}
    if(cell||row.length){row.push(cell);rows.push(row);}return rows;
  }
  function stepEvidenceHTML(n) {
    const required=arr(n.checks).filter(c=>c.required!==false),sem=arr(n.verifications);
    const checks=[...arr(n.checks)].sort((a,b)=>Number(b.required!==false)-Number(a.required!==false)||Number(a.passed)-Number(b.passed)||Number(/原值|输入版本/.test(b.name))-Number(/原值|输入版本/.test(a.name)));
    const rows=checks.map(c=>`<li class="${c.passed?'pass':'fail'}"><b>${c.passed?'通过':'未通过'} · ${esc(c.name)}${c.required===false?' · 辅助检查':''}</b><p>${esc(c.detail)}</p></li>`).join('');
    const inputs=arr(n.input_artifacts).map(a=>`<li><b>${esc(a.logical_name||a.name)}</b><p>登记版本 ${esc(a.name)}<br>SHA-256 <code>${esc(a.sha256||'未记录')}</code></p></li>`).join('');
    const semantics=sem.map(v=>`<li class="${v.passed?'pass':v.state==='unknown'?'unknown':'fail'}"><b>${v.passed?'通过':v.state==='unknown'?'未确认':'未通过'} · ${esc(v.item)}</b><p>${esc(v.evidence)}</p></li>`).join('');
    return `<article class="show-step-evidence"><p>${esc(n.action||'')}</p><div class="show-step-summary"><span>${esc(stepName(n.status))}</span><span>必要检查 ${required.filter(c=>c.passed).length}/${required.length}</span><span>语义复核 ${sem.filter(v=>v.passed).length}/${sem.length}</span><span>${number(n.n_attempts)} 次尝试</span></div><section><h3>实际输入与文件版本</h3>${inputs?`<ul>${inputs}</ul>`:`<p>${esc(arr(n.inputs).join(' / ')||'本步骤未携带前序文件')}</p>`}</section><section><h3>服务端检查 · 直接核对产物</h3>${rows?`<ul>${rows}</ul>`:'<p>尚无检查结果。</p>'}</section>${semantics?`<details><summary>模型语义复核 · 逐条证据</summary><ul>${semantics}</ul></details>`:''}${n.error?`<section><h3>执行错误</h3><pre>${esc(n.error)}</pre></section>`:''}${n.code?`<details><summary>查看实际执行代码</summary><pre>${esc(n.code)}</pre></details>`:''}${arr(n.attempts).map(a=>`<details><summary>第 ${number(a.n)} 次尝试 · ${a.ok?'代码运行成功':'代码运行失败'}</summary>${a.repair_reason?`<p>修复原因：${esc(a.repair_reason)}</p>`:''}<pre>${esc(a.stdout||'')}${a.stderr?'\n'+esc(a.stderr):''}</pre>${a.code_diff?`<h3>修复差异</h3><pre>${esc(a.code_diff)}</pre>`:''}</details>`).join('')}${!n.attempts&&n.stdout?`<details><summary>运行输出</summary><pre>${esc(n.stdout)}</pre></details>`:''}</article>`;
  }
  const Core={PHASES,createState,reduceEvent,dagLayout,parseCSV,stepEvidenceHTML,esc};
  if(typeof module!=='undefined'&&module.exports)module.exports=Core;
  if(!root.document)return;
  const $=id=>document.getElementById(id);
  let state=createState(),network={nodes:[],edges:[]},timer=null,poller=null,requestGeneration=0,replay=null,presentationFocus=null,previewGeneration=0;
  const safeGet=(url,options={})=>root.UI.json(url,options);
  function stopPlayback(){if(timer)clearTimeout(timer);timer=null;replay=null;}
  function stopPolling(){if(poller)clearInterval(poller);poller=null;requestGeneration++;}
  function fact(title,detail=''){return `<div class="show-fact"><b>${esc(title)}</b>${detail?`<small>${esc(detail)}</small>`:''}</div>`;}
  function done(i){return state.phases[i]==='done';}
  function renderNetwork() {
    const host=$('show-network'), narrow=host.clientWidth<430;
    host.dataset.dag=String(state.nodes.length>0);
    if(state.nodes.length){
      const layout=dagLayout(state.nodes,narrow);const edge=[],nodes=[];
      state.nodes.forEach(n=>{const p=layout.points.get(n.idx);arr(n.depends_on).forEach(dep=>{const a=layout.points.get(dep);if(!a)return;const active=n.status==='running';const path=narrow?`M ${a.x+a.w/2},${a.y+a.h} C ${a.x+a.w/2},${a.y+a.h+9} ${p.x+p.w/2},${p.y-9} ${p.x+p.w/2},${p.y}`:`M ${a.x+a.w},${a.y+38} C ${a.x+a.w+20},${a.y+38} ${p.x-20},${p.y+38} ${p.x},${p.y+38}`;edge.push(`<path d="${path}" class="sc-dag-edge ${active?'active':''}" marker-end="url(#sc-arrow)"/>`);});
        const action=String(n.action||'通用执行').slice(0,Math.floor((p.w-24)/12)),name=String(n.skill||'通用执行').slice(0,Math.floor((p.w-24)/5.2));
        nodes.push(`<g data-show-step="${n.idx}" role="button" tabindex="0" aria-label="查看第 ${n.idx+1} 步：${esc(n.action)}"><title>${esc(n.action)} · ${esc(n.skill)}</title><rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="8" class="sc-dag-node ${esc(n.status)}"/><text x="${p.x+12}" y="${p.y+18}" fill="#9ab6c7" font-size="10">STEP ${String(n.idx+1).padStart(2,'0')} · ${esc(stepName(n.status))}</text><text x="${p.x+12}" y="${p.y+39}" fill="#e8f7fa" font-size="12">${esc(action)}…</text><text x="${p.x+12}" y="${p.y+55}" fill="#9ab6c7" font-size="9">${esc(name)}</text><text x="${p.x+12}" y="${p.y+68}" fill="#88bcad" font-size="9">${n.checks?'检查 '+esc(n.checks):'点击查看动作与代码'}</text></g>`);
      });
      host.innerHTML=`<svg viewBox="0 0 ${layout.width} ${layout.height}" aria-label="本次问题的真实执行依赖图"><defs><marker id="sc-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10" fill="#82b4bb"/></marker></defs>${edge.join('')}${nodes.join('')}</svg>`;
      $('show-graph-label').textContent='EXECUTION DAG · 实际步骤依赖';
      $('show-graph-note').textContent=`${state.nodes.length} 个步骤 · ${state.nodes.filter(n=>n.status==='done').length} 已完成`;
      return;
    }
    const selected=new Set(state.selected),width=640,height=278,pts=new Map();
    const counts={};const visible=network.nodes.filter(n=>{const i=counts[n.domain]||0;counts[n.domain]=i+1;return selected.has(n.id)||n.source!=='github'||i<12;});
    visible.forEach((n,i)=>{const angle=i*2.399963;const r=Math.sqrt((i+.5)/Math.max(1,visible.length));pts.set(n.id,{x:320+Math.cos(angle)*r*276,y:135+Math.sin(angle)*r*110});});
    const links=network.edges.map(e=>{const a=pts.get(e.source),b=pts.get(e.target);return a&&b?`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" class="sc-link"/>`:'';}).join('');
    const nodes=visible.map(n=>{const p=pts.get(n.id),hot=selected.has(n.id);return `<g><title>${esc(n.id)} · ${esc(n.domain)}</title><circle cx="${p.x}" cy="${p.y}" r="${hot?5:2.3}" class="sc-node ${hot?'hot':''}"/>${hot?`<text x="${p.x}" y="${p.y-10}" text-anchor="middle" font-size="10" fill="#c5f6e6">${esc(String(n.id).slice(0,30))}</text>`:''}</g>`;}).join('');
    host.innerHTML=`<svg viewBox="0 0 ${width} ${height}" aria-label="来自真实技能库的能力网络"><ellipse cx="320" cy="135" rx="276" ry="110" class="sc-orbit"/><ellipse cx="320" cy="135" rx="195" ry="78" class="sc-orbit"/>${links}${nodes}${!network.nodes.length?'<text x="320" y="140" text-anchor="middle" fill="#9cb6c9" font-size="14">正在读取技能网络…</text>':''}<text x="320" y="265" text-anchor="middle" fill="#819eb5" font-size="10">${selected.size?'亮点 = 本次选中的技能':'提出问题，能力网络将收束为可执行路径'}</text></svg>`;
    $('show-graph-label').textContent='LIVE SKILL NETWORK · 实时资产';
    $('show-graph-note').textContent=network.nodes.length?`${network.nodes.length} 项能力 / ${network.edges.length} 条关系`:'读取中';
  }
  function phaseFacts(i) {
    const snap=state.snapshot||{},staged=snap.staged||{};
    if(!done(i)&&!(i===4&&state.nodes.length)&&!(i===5&&state.checks.length))return fact('等待本阶段的真实结果','运行后展示实际值，未执行阶段不填充演示数字。');
    if(i===0){const modes=state.retrieval.modes||snap.retrieval||{};const f=modes.fabric||state.retrieval;const components=Object.entries(f.components||{}).filter(([,v])=>v).map(([k])=>({bm25:'关键词',vector:'向量',structural:'结构',graph_expansion:'关系扩展',llm_rerank:'必要性筛选'}[k]||k));return fact(`推荐 ${arr(f.selected).length} 项 · ${f.selection?.library_size==null?'库规模未记录':f.selection.library_size+' 项技能中检索'}`,f.selection?.rule||'历史记录未保存必要性筛选规则。')+arr(f.selected).slice(0,4).map(n=>{const c=arr(f.candidates).find(c=>c.name===n)||{};return fact(n,c.note||c.capability||'具体采用理由在编排阶段核对。');}).join('')+['bm25','hybrid','fabric'].map(m=>fact(m.toUpperCase()+` · ${arr(modes[m]?.selected).length} 项`,arr(modes[m]?.selected).slice(0,3).join(' / ')||'没有推荐项或未记录')).join('')+fact('实际组件 · '+(components.join(' / ')||'见原始记录'),f.degraded?'降级：'+(f.degraded_reason||'存在组件未启用'):(f.decision_reason||'相关度为启发式指标，不代表成功概率'));}
    if(i===1){const rows=state.ranking.length?state.ranking:arr(snap.ranking);const max=Math.max(1,...rows.map(r=>number(r.priority)));return `<div class="show-ranking">${rows.slice(0,5).map(r=>`<div class="show-rank" title="收益 ${esc(r.exploit)} · 探索 ${esc(r.explore)}"><span>${esc(r.name)}</span><b>${number(r.priority).toFixed(3)}</b><i style="--pct:${Math.max(0,Math.min(100,number(r.priority)/max*100))}%"></i></div>`).join('')}</div>`+fact('优先级 = 收益预测 + 探索项','悬停查看分项；编排不保证采用排序首位。');}
    if(i===2){const o=Object.keys(state.orchestration).length?state.orchestration:staged.orchestration||{};return fact(`${arr(o.order||o.skills).length} 项能力共同完成任务`,arr(o.order||o.skills).join(' / '))+arr(o.decisions).filter(d=>arr(o.order||o.skills).includes(d.name)).slice(0,4).map(d=>fact('采用 · '+d.name,d.reason||'未记录具体理由')).join('')+fact(`${arr(o.edges||o.workflow).length} 条编排关系`,'执行引擎会进一步解析到实际步骤依赖。')+fact('来源 · '+(o.source||staged.orchestration?.source||'历史记录未标注'),(o.degraded??staged.orchestration?.degraded)?'本次使用了降级路径，仍保留可查证的依赖。':'本次未标注降级。');}
    if(i===3&&snap.staged?.execution_scope){const scope=snap.staged.execution_scope;return fact(`规划 ${scope.planned} 步 / 本轮执行 ${scope.executed} 步`, `步骤预算 ${scope.max_steps}，保留所有执行节点的前置依赖。`)+fact('未执行的范围',scope.omitted.map(s=>s.action+'：'+s.reason).join('；')||'本次规划已全部执行');}
    if(i===3)return fact(`${state.nodes.length || state.planSteps || 0} 个执行节点`,state.approach||snap.plan?.approach||'动作与验收约束已进入执行引擎。')+fact('按实际依赖执行，编号来自规划','编号不代表开始顺序；点击步骤查看动作、输入、代码与输出。');
    if(i===4)return fact(`${state.nodes.filter(n=>n.status==='done').length}/${state.nodes.length} 步完成`,`${state.nodes.filter(n=>number(n.attempt)>1&&n.status==='done').length} 步修复后完成 · ${state.nodes.filter(n=>n.status==='failed').length} 步失败`)+fact(`${state.artifacts.length} 个文件已登记`,state.artifacts.slice(-3).map(a=>a.name).join(' / '))+fact('文件在步骤间实际传递',state.nodes.filter(n=>arr(n.inputs).length).map(n=>`Step ${n.idx+1} ← ${arr(n.inputs).length} 文件`).join(' / ')||'本次尚未记录跨步文件传递。');
    if(i===5){const checks=state.checks;const j=state.judge||(done(5)?snap.judge:null)||{};const sem=state.mode==='replay'&&!done(5)?[]:arr(snap.steps).flatMap(n=>arr(n.verifications));return fact(`程序检查 ${checks.filter(c=>c.passed).length}/${checks.length} 通过`,checks.filter(c=>!c.passed).slice(0,2).map(c=>c.name).join(' / ')||'当前已记录的检查未出现失败。')+fact('方案评审 · '+(j.score_valid!==false&&j.weighted!=null?number(j.weighted).toFixed(1)+'/10':done(5)?'不可用':'等待评审'),'方案评分与文件检查分开计算，不相互替代。')+fact(`语义验收 ${sem.filter(v=>v.passed).length}/${sem.length} 通过`,sem.length?'详细证据可在逐步记录中查看。':'尚无语义验收记录；不可解释为全部通过。')+sem.filter(v=>!v.passed).slice(0,2).map(v=>fact('未确认 · '+v.evidence,v.item)).join('');}
    const e={...(snap.evolution||{}),...(state.evolution||{})},a=state.assessment||staged.quality_assessment;
    if(a){const gates=state.rewardGates||staged.reward_gates;return (gates?fact(`奖励门禁 ${gates.passed}/${gates.total} 通过`,gates.eligible?'十二道门全部通过，具备限定范围的领奖资格。':'存在未通过或待证据的门，本次不发放提升积分。'):'')+fact('正式网络未更新','单次运行没有证明技能因果贡献或跨任务增益。')+fact(`${arr(a.observations).filter(r=>r.observed_score!=null).length} 步有可重算的限定范围结果`,a.scope)+fact(e.candidate?'新经验已隔离为候选':'本次仅保留观察',e.candidate?'留出评测前不准入，不自动部署排序参数。':e.skip_reason||'没有足够的独立结果证据。');}
    const feedback=state.feedback.length?state.feedback:arr(snap.feedback);return fact(e.candidate?'历史候选记录':e.accepted?'历史准入 · '+e.name:'本次未新增能力',e.skip_reason||'见原始记录')+fact('历史记录未采用当前独立评价协议','旧参数变化不能作为网络整体提升的证据。')+fact(`${feedback.filter(f=>f.nudged).length} 项历史反馈`,feedback.slice(0,2).map(f=>`${f.name} · Δ ${number(f.delta).toFixed(4)}`).join(' / '));
  }
  function render() {
    if(!$('show-stage'))return;
    const focused=document.activeElement;
    const restoreFocus=focused?.closest?.('[data-show-phase],[data-show-step]');
    const focusKey=restoreFocus?.hasAttribute('data-show-phase')?'data-show-phase':restoreFocus?'data-show-step':null;
    const focusValue=focusKey?restoreFocus.getAttribute(focusKey):null;
    const selected=state.view??state.phase,phase=PHASES[selected];
    $('show-stage').dataset.running=String(state.mode==='live'&&!state.finished);
    $('show-rail').innerHTML=PHASES.map((p,i)=>`<button type="button" class="show-phase" data-show-phase="${i}" data-state="${state.phases[i]}" aria-pressed="${selected===i}"><i>${state.phases[i]==='done'?'✓':String(i+1).padStart(2,'0')}</i><span>${p.name}<small>${state.phases[i]==='running'?'进行中':state.phases[i]==='done'?'已有真实证据':state.phases[i]==='failed'?'异常':'等待执行'}</small></span></button>`).join('');
    $('show-status').textContent=state.mode==='replay'?`真实记录回放${state.finished?' · 完成':''}`:state.finished?statusName(state.status):state.mode==='live'?'真实运行 · '+PHASES[state.phase].name:'框架待命';
    $('show-question-text').textContent=state.task||'你的问题将驱动整个框架；过程、证据与结果在这里同步展开。';
    $('show-question-text').title=state.task||'';
    $('show-question-toggle').hidden=!state.task;
    $('show-run-link').hidden=!state.id;
    if(state.id){$('show-run-link').href='/run?id='+encodeURIComponent(state.id);$('show-run-link').textContent='RUN '+state.id.slice(-13)+' ↗';}
    $('show-phase-tag').textContent=phase.tag;
    $('show-phase-title').textContent=phase.title;
    $('show-phase-doing').textContent=phase.doing;
    $('show-phase-benefit').textContent=phase.benefit;
    $('show-facts').innerHTML=phaseFacts(selected);
    $('show-activity').innerHTML=state.logs.length?state.logs.slice(-3).map(l=>`<div><time>${(l.time/1000).toFixed(1)}s</time><span>${esc(l.text)}</span></div>`).join(''):'<div><time>READY</time><span>真实技能库在线 · 一次问题，贯穿完整能力生命周期</span></div>';
    $('show-follow').hidden=state.view===null;
    $('show-cancel').hidden=state.mode!=='live'||state.finished||!state.id;
    $('show-cancel').disabled=false;
    $('show-replay-controls').hidden=state.mode!=='replay';
    $('show-replay').disabled=state.mode==='live'&&!state.finished;
    if(replay){$('show-pause').textContent=replay.paused?'继续回放':'暂停回放';$('show-seek').value=String(replay.cursor);$('show-seek').max=String(replay.events.length);}
    const snap=state.snapshot||{};
    $('show-elapsed').textContent=(state.elapsed/1000).toFixed(1)+'s';
    $('show-cost').textContent=state.mode==='idle'?'—':(state.mode==='replay'&&!state.finished?'历史记录':'¥'+number(snap.cost_yuan).toFixed(3));
    $('show-calls').textContent=state.mode==='idle'?'—':(state.mode==='replay'&&!state.finished?'回放不调用模型':`${number(snap.llm_calls)} 次 · ${number(snap.tokens).toLocaleString()} tokens`);
    $('show-record-note').textContent=state.mode==='replay'?'回放真实事件 · 无新增模型费用':state.mode==='live'?'预算 ¥1.00 / 420s · 记录可追溯':'S1 接入契约已就绪 · 生产联调待验证';
    renderNetwork();
    renderOperation();
    if(focusKey)$('show-stage').querySelector(`[${focusKey}="${focusValue}"]`)?.focus({preventScroll:true});
    if(matchMedia('(max-width:900px)').matches){const rail=$('show-rail'),button=rail.querySelector(`[data-show-phase="${selected}"]`);if(button){const left=button.offsetLeft-rail.offsetLeft;if(left<rail.scrollLeft||left+button.offsetWidth>rail.scrollLeft+rail.clientWidth)rail.scrollLeft=Math.max(0,left-10);}}
  }
  function renderOperation(){const host=$('show-operation');const n=state.nodes.find(n=>n.status==='running')||state.nodes.filter(n=>n.status==='done').at(-1);host.hidden=!n;if(!n)return;
    const attempt=arr(n.attempts).at(-1),stdout=n.stdout||attempt?.stdout||'',code=n.code||'';
    const status={generating:'模型正在生成 / 修复代码',syntax:'生成完成 · 语法预检',sandbox:'Python 正在运行',verify:'检查文件与技能验收',done:'步骤已完成'}[n.stage]||stepName(n.status);
    const excerpt=stdout?stdout.slice(-700):code?code.split('\n').filter(l=>l.trim()&&!l.trim().startsWith('#')).slice(0,8).join('\n').slice(0,700):'正在等待本步骤的实际代码；生成后可查看，运行输出将实时替换这里。';
    host.innerHTML=`<div><span>STEP ${String(n.idx+1).padStart(2,'0')} · ${esc(status)}</span><button type="button" data-show-step="${n.idx}">完整证据 ↗</button></div><pre>${esc(excerpt)}</pre><small>${stdout?'真实 Python 输出片段':code?'本次实际生成代码片段':'模型等待阶段 · 此处不填充示例代码'}</small>`;
  }
  function start(task,history=[]) {
    stopPlayback();stopPolling();state=createState(task,'live');state.started=Date.now();state.phases[0]='running';state.history=history;
    $('show-output').hidden=true;$('show-results').hidden=true;render();
    $('s3').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'instant':'smooth',block:'start'});
  }
  function event(ev){if(state.mode!=='live')return;if(reduceEvent(state,ev))render();}
  function created(id){state.id=id;const generation=requestGeneration;let reading=false;render();
    poller=setInterval(async()=>{if(reading||state.finished||state.mode!=='live')return;reading=true;try{const snap=await safeGet('/api/runs/'+encodeURIComponent(id));if(generation!==requestGeneration||state.id!==id)return;state.snapshot=snap;state.elapsed=number(snap.duration_ms,state.elapsed);arr(snap.events).forEach(ev=>reduceEvent(state,ev));render();}catch(e){if(generation===requestGeneration)$('show-record-note').textContent='状态读取暂不可用 · 继续接收实时事件';}finally{reading=false;}},2500);
  }
  function renderOutput(fin) {
    $('show-results').hidden=false;$('show-output').hidden=false;
    const stats=fin.step_stats||{},checks=arr(fin.steps).flatMap(n=>arr(n.checks)).filter(c=>c.required!==false);
    $('show-results').innerHTML=[factMetric(`${number(stats.done)}/${number(stats.total)}`,'实际完成步骤'),factMetric(`${checks.filter(c=>c.passed).length}/${checks.length}`,'程序检查通过 · 不等于步骤完成'),factMetric(String(arr(fin.artifacts).length),'可下载的真实文件'),factMetric(fin.evolution?.accepted?'+1':'0','本次新增技能 · 准入结果')].join('');
    const answer=fin.staged?.final_reply || fin.error || '本次没有生成最终文本，请查看步骤和文件证据。';
    const verdict=fin.staged?.acceptance;
    const value=fin.evolution?.candidate?'新经验已进入候选区，等待冻结任务的真实执行验证；当前技能库尚未新增。':fin.evolution?.accepted?`本次经验已沉淀为 ${fin.evolution.name}，可进入后续任务复用。`:fin.staged?.learning_gate?.eligible===false?`本次经验暂不写入技能库：${fin.staged.learning_gate.skip_reason}。结果与证据保留供核对，避免学习未经确认的经验。`:fin.evolution?.skip_reason||'本次未新增技能；已有运行、验收和反馈记录保留供后续复盘。';
    $('show-routing').innerHTML=root.Product?.selectionHTML(fin)||'';
    $('show-answer-body').innerHTML=`${root.Product?.valueHTML(fin)||''}${root.Product?.assessmentDetailsHTML(fin)||''}<div class="show-value">${esc(statusName(fin.status))} · 验收${verdict?({passed:'通过',failed:'未通过',unknown:'有待确认'}[verdict.state]||verdict.state):'见逐项证据'} · ${esc(value)}</div><div class="rp-body">${typeof root.mdToHtml==='function'?root.mdToHtml(answer):esc(answer).replace(/\n/g,'<br>')}</div>`;
    $('show-files-body').innerHTML=arr(fin.artifacts).slice().sort((a,b)=>number(b.from_step)-number(a.from_step)).map(a=>{const url='/api/runs/'+encodeURIComponent(fin.run_id)+'/artifacts/'+encodeURIComponent(a.name);return `<div class="show-file"><b>${esc(a.name)}</b><p>${esc(a.kind||'真实运行产物')}${a.from_step!=null?' · Step '+(number(a.from_step)+1)+' 产出':''} · ${(number(a.bytes)/1024).toFixed(1)} KB · SHA-256 ${esc(String(a.sha256||'未记录').slice(0,16))}${a.sha256?'…':''}</p><button type="button" data-show-artifact="${esc(a.name)}">查看文件</button><a href="${url}" download="${esc(a.name)}">下载</a>${/\.(png|jpg|jpeg|webp|svg)$/i.test(a.name)?`<img src="${url}" alt="本次实际运行生成的 ${esc(a.name)}" loading="lazy">`:''}</div>`;}).join('')||'<p style="font-size:12px;color:#7a909e">本次没有登记可下载文件。</p>';
    $('show-evidence-link').href='/run?id='+encodeURIComponent(fin.run_id);
    const modes=fin.retrieval||{},feedback=arr(fin.feedback),orchestration=fin.staged?.orchestration||{};
    const evidence=[
      ['三档检索', ['bm25','hybrid','fabric'].map(m=>m.toUpperCase()+' '+(modes[m]?arr(modes[m].selected).length:'—')).join(' / '),'同题对照，检索来源可查'],
      ['经验参与选择',arr(fin.ranking).length+' 项实际排序','收益与探索项分别可见'],
      ['能力协作',arr(fin.skills).length+' 项技能 / '+arr(orchestration.workflow).length+' 条编排边','依赖继续解析为执行步骤'],
      ['可执行方案',number(stats.total)+' 步 / '+(fin.staged?.scheduler||'见执行记录'),'DAG 对应真实运行路径'],
      ['执行与修复',number(stats.retried)+' 步重试 / '+arr(fin.artifacts).length+' 个文件','保留实际输出与尝试记录'],
      ['独立验收',checks.filter(c=>c.passed).length+'/'+checks.length+' 程序检查通过','失败结果保留，完成与合格分开'],
      ['经验观察',fin.staged?.quality_assessment?'影子观察 / 正式更新 0 次':feedback.filter(f=>f.nudged).length+' 项历史反馈','任务结果、技能贡献与网络增益分开核验']
    ];
    $('show-impact').innerHTML=evidence.map(([title,value,why],i)=>`<button type="button" data-show-phase="${i}"><small>${String(i+1).padStart(2,'0')} · ${esc(title)}</small><b>${esc(value)}</b><span>${esc(why)}</span></button>`).join('');
  }
  function factMetric(value,label){return `<div class="show-result"><b>${esc(value)}</b><span>${esc(label)}</span></div>`;}
  function finish(fin){stopPolling();state.snapshot=fin;arr(fin.events).forEach(ev=>reduceEvent(state,ev));state.finished=true;state.status=fin.status;state.error=fin.error||'';state.elapsed=number(fin.duration_ms);state.artifacts=arr(fin.artifacts);state.checks=arr(fin.steps).flatMap(n=>arr(n.checks).filter(c=>c.required!==false).map(c=>({...c,step:n.idx})));state.nodes=arr(fin.steps).map(n=>({...n,stage:n.status==='done'?'done':n.status,attempt:n.n_attempts,checks:arr(n.checks).length?`${n.checks.filter(c=>c.required!==false&&c.passed).length}/${n.checks.filter(c=>c.required!==false).length}`:`${number(n.checks_passed)}/${number(n.checks_total)}`}));render();renderOutput(fin);
    if(state.mode==='live')safeGet('/api/graph').then(g=>{network={nodes:arr(g.nodes),edges:arr(g.edges)};const fields={'hm-skills':network.nodes.length,'hm-edges':network.edges.length,'hm-domains':new Set(network.nodes.map(n=>n.domain)).size,'hm-evolved':network.nodes.filter(n=>(n.generation||0)>0).length};Object.entries(fields).forEach(([id,v])=>{if($(id))$(id).textContent=v;});$('lib-n').textContent=network.nodes.length+' 个技能';}).catch(()=>{});
  }
  function fail(message){stopPolling();state.finished=true;state.status='FAILED';state.error=String(message);state.phases[state.phase]='failed';state.logs.push({time:state.elapsed,text:state.error});render();}
  async function loadRecord(id,animate=false) {
    if((state.mode==='live'&&!state.finished)||$('task').disabled)return;
    stopPlayback();stopPolling();const generation=requestGeneration;
    $('show-replay').disabled=true;
    try{const fin=await safeGet('/api/runs/'+encodeURIComponent(id));if(generation!==requestGeneration)return;
      if(!animate){state=createState(fin.task,'record');state.id=id;finish(fin);$('s3').scrollIntoView({behavior:'smooth',block:'start'});return;}
      const events=arr(fin.events).filter(e=>e.type!=='perf.frontend');
      state=createState(fin.task,'replay');state.id=id;state.snapshot=fin;
      replay={events,fin,cursor:0,paused:false,speed:number($('show-speed').value,4)};
      $('show-results').hidden=true;$('show-output').hidden=true;render();$('s3').scrollIntoView({behavior:'smooth',block:'start'});nextReplay();
    }catch(e){fail('无法读取真实记录：'+(e.message||e));}finally{$('show-replay').disabled=false;}
  }
  function nextReplay(){if(!replay||replay.paused)return;const playback=replay;
    if(playback.cursor>=playback.events.length){finish(playback.fin);return;}
    const ev=playback.events[playback.cursor++];reduceEvent(state,ev);render();
    const next=playback.events[playback.cursor];const delay=next?Math.max(40,Math.min(1800,(number(next.ts_ms)-number(ev.ts_ms))/playback.speed)):50;
    timer=setTimeout(()=>{timer=null;if(replay===playback)nextReplay();},delay);
  }
  function seek(cursor){if(!replay)return;clearTimeout(timer);timer=null;const playback=replay;state=createState(playback.fin.task,'replay');state.id=playback.fin.run_id;state.snapshot=playback.fin;playback.cursor=Math.max(0,Math.min(playback.events.length,number(cursor)));playback.events.slice(0,playback.cursor).forEach(ev=>reduceEvent(state,ev));$('show-output').hidden=true;$('show-results').hidden=true;if(playback.cursor===playback.events.length)finish(playback.fin);else {render();if(!playback.paused){const ev=playback.events[playback.cursor],prev=playback.events[playback.cursor-1];timer=setTimeout(nextReplay,prev?Math.max(40,Math.min(1800,(number(ev.ts_ms)-number(prev.ts_ms))/playback.speed)):40);}}}
  async function preview(name) {
    if(!state.id)return;const art=state.artifacts.find(a=>a.name===name);if(!art)return;
    const dialog=$('show-preview'),body=$('show-preview-body'),generation=++previewGeneration;
    $('show-preview-title').textContent=name;body.textContent='正在读取本次真实文件…';dialog.showModal();
    const url='/api/runs/'+encodeURIComponent(state.id)+'/artifacts/'+encodeURIComponent(name);
    try{if(number(art.bytes)>2*1024*1024){body.textContent='文件较大，请通过下载按钮查看原文件。';return;}
      const response=await root.UI.fetch(url);if(!response.ok)throw new Error('HTTP '+response.status);const bytes=await response.arrayBuffer();if(generation!==previewGeneration||!dialog.open)return;
      if(/\.(png|jpg|jpeg|webp|svg)$/i.test(name)){const imageURL=URL.createObjectURL(new Blob([bytes],{type:response.headers.get('content-type')||'image/png'}));body.innerHTML=`<img src="${imageURL}" alt="${esc(name)}">`;dialog.addEventListener('close',()=>URL.revokeObjectURL(imageURL),{once:true});}
      else if(/\.(csv|tsv|txt|md|py|json|html|svg)$/i.test(name)){const text=new TextDecoder().decode(bytes);if(/\.csv$/i.test(name)){const rows=parseCSV(text.replace(/^\ufeff/,''));body.innerHTML=`<table><thead><tr>${arr(rows[0]).slice(0,12).map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${rows.slice(1,41).map(r=>`<tr>${r.slice(0,12).map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table><p style="font-size:10px;margin-top:10px">原文件 ${rows.length-1} 行数据 · 预览最多 40 行 / 12 列</p>`;}else body.innerHTML='<pre>'+esc(text)+'</pre>';}
      else body.textContent='此格式请下载原文件后查看。';
    }catch(e){if(generation===previewGeneration)body.textContent='文件读取失败：'+(e.message||e);}
  }
  async function inspectStep(idx){let n=state.nodes.find(s=>s.idx===idx);if(!n)return;const id=state.id;const dialog=$('show-preview');$('show-preview-title').textContent=`Step ${idx+1} · ${n.skill||'通用动作'}`;$('show-preview-body').innerHTML='<pre>'+esc(n.action)+'</pre>';dialog.showModal();const generation=++previewGeneration;
    try{if(id&&state.mode!=='replay'){const snap=await safeGet('/api/runs/'+encodeURIComponent(id));if(generation!==previewGeneration||!dialog.open)return;n=arr(snap.steps).find(s=>s.idx===idx)||n;}else if(state.mode==='replay'){const stored=arr(state.snapshot?.steps).find(s=>s.idx===idx);if(n.status==='done'||n.status==='failed')n=stored||n;}
      $('show-preview-body').innerHTML=stepEvidenceHTML(n);
    }catch(e){$('show-preview-body').textContent='步骤记录读取失败：'+(e.message||e);}
  }
  function present(){const entering=!document.body.classList.contains('showcase-presenting');if(entering)presentationFocus=document.activeElement;document.body.classList.toggle('showcase-presenting',entering);$('show-present').textContent=entering?'退出汇报模式':'汇报模式';if(!entering&&presentationFocus)presentationFocus.focus();renderNetwork();}
  function reset(){if(state.mode==='live'&&!state.finished)return;stopPlayback();stopPolling();state=createState();$('show-output').hidden=true;$('show-results').hidden=true;render();}
  function beforeLegacy(){reset();$('show-status').textContent='七阶段演示 · 过程在下方展开';$('show-replay').disabled=true;}
  async function cancel(){if(!state.id||state.finished||state.mode!=='live')return;const id=state.id;$('show-cancel').disabled=true;try{await safeGet('/api/runs/'+encodeURIComponent(id)+'/cancel',{method:'POST'});if(state.id===id){state.logs.push({time:state.elapsed,text:'已请求取消 · 等待服务端安全结束'});render();$('show-cancel').disabled=true;}}catch(e){if(state.id===id){state.logs.push({time:state.elapsed,text:'取消失败：'+e.message});render();}}}
  const prompts={stats:'仅使用公开演示数据，不联网：A组[1,2,3,4,5]，B组[2,3,4,5,6]。完成3步真实执行：①计算n、均值、样本标准差(ddof=1)，统一保留4位小数，写入summary.csv；②回读校验表头group,n,mean,std_sample、2组、无空值，核对数值时使用绝对容差0.0001，不把舍入误差当错误；③直接读取同一CSV绘制均值对比图figure.png，误差条注明样本标准差，纵轴从0开始。所有步骤采用相同的舍入规则，只做描述统计，不进行推断。',plan:'我想用纯成分特征预测无机化合物的形成能。请制定可执行的小样本机器学习方案，明确数据泄漏风险、基线、验证方法与交付物。',follow:'结合上一轮结果，解释每个验收检查为什么有必要，哪些结果仍不能支持业务结论，并列出下一步改进。'};
  function init(){
    if(!$('show-stage'))return;
    $('show-replay').addEventListener('click',()=>loadRecord(PUBLIC_REPLAY_ID,true));
    $('show-present').addEventListener('click',present);$('show-follow').addEventListener('click',()=>{state.view=null;render();});$('show-cancel').addEventListener('click',cancel);
    $('show-question-toggle').addEventListener('click',e=>{const expanded=e.currentTarget.getAttribute('aria-expanded')!=='true';e.currentTarget.setAttribute('aria-expanded',String(expanded));e.currentTarget.textContent=expanded?'收起问题':'展开问题';$('show-question').classList.toggle('is-expanded',expanded);});
    $('show-pause').addEventListener('click',()=>{if(!replay)return;replay.paused=!replay.paused;clearTimeout(timer);timer=null;render();if(!replay.paused)nextReplay();});
    $('show-speed').addEventListener('change',()=>{if(replay)replay.speed=number($('show-speed').value,4);});$('show-seek').addEventListener('input',e=>seek(e.target.value));
    document.addEventListener('click',e=>{const phase=e.target.closest('[data-show-phase]');if(phase){state.view=number(phase.dataset.showPhase);render();return;}const step=e.target.closest('[data-show-step]');if(step){inspectStep(number(step.dataset.showStep));return;}const artifact=e.target.closest('[data-show-artifact]');if(artifact){preview(artifact.dataset.showArtifact);return;}const record=e.target.closest('[data-show-run]');if(record){loadRecord(record.dataset.showRun);return;}const prompt=e.target.closest('[data-show-prompt]');if(prompt){$('task').value=prompts[prompt.dataset.showPrompt]||'';$('task').focus();}});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.body.classList.contains('showcase-presenting')&&!$('show-preview').open){present();}const step=e.target.closest?.('[data-show-step]');if(step&&(e.key==='Enter'||e.key===' ')){e.preventDefault();inspectStep(number(step.dataset.showStep));}});
    $('show-preview-close').addEventListener('click',()=>{previewGeneration++;$('show-preview').close();});$('show-preview').addEventListener('close',()=>{previewGeneration++;});
    new ResizeObserver(()=>renderNetwork()).observe($('show-network'));
    safeGet('/api/graph').then(g=>{network={nodes:arr(g.nodes),edges:arr(g.edges)};renderNetwork();}).catch(()=>{$('show-graph-note').textContent='技能网络读取失败，可在连接设置中检查服务';});
    render();
  }
  root.Showcase={start,created,event,finish,fail,present,loadRecord,reset,beforeLegacy,replay:()=>loadRecord(PUBLIC_REPLAY_ID,true)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})(typeof window==='undefined'?globalThis:window);
