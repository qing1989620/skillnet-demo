/* Shared, factual presentation of execution evidence across the product. */
(function (root) {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const terminal = ['COMPLETED','PARTIAL','FAILED','CANCELLED','INTERRUPTED','BUDGET_EXCEEDED'];
  const labels = {CREATED:'已创建',RETRIEVING:'检索中',ORCHESTRATING:'编排中',EXECUTING:'执行中',VERIFYING:'验收中',EVOLVING:'沉淀中',COMPLETED:'执行完成',PARTIAL:'部分完成',FAILED:'执行失败',CANCELLED:'已取消',INTERRUPTED:'已中断',BUDGET_EXCEEDED:'预算已到上限'};
  function metrics(run) {
    const steps = run.steps || [], checks = steps.flatMap(s => s.checks || []).filter(c=>c.required!==false), semantic = steps.flatMap(s => s.verifications || []);
    return {done:steps.filter(s=>s.status==='done').length,total:steps.length,
      checks:checks.length,passed:checks.filter(c=>c.passed===true).length,
      semantic:semantic.length,confirmed:semantic.filter(c=>c.passed===true).length,
      unconfirmed:semantic.filter(c=>c.passed!==true),repairs:steps.filter(s=>s.status==='done'&&(s.n_attempts||s.attempts?.length||0)>1).length,
      gate:{...(run.staged?.learning_gate||{}),reason:run.staged?.learning_gate?.reason||run.staged?.learning_gate?.skip_reason||''}, impact:run.staged?.skill_impact || {}, terminal:terminal.includes(run.status)};
  }
  function dag(run) {
    const steps = run.steps || [], byId = new Map(steps.map(s=>[s.idx,s])), levels = new Map();
    function depth(id, visiting = new Set()) {
      if(levels.has(id))return levels.get(id); if(visiting.has(id))return 0;
      const next = new Set(visiting);next.add(id);
      const deps=(byId.get(id)?.depends_on||[]).filter(d=>byId.has(d));
      const value=deps.length?1+Math.max(...deps.map(d=>depth(d,next))):0;levels.set(id,value);return value;
    }
    steps.forEach(s=>depth(s.idx));
    const counts = new Map(), nodes = steps.map(s=>{const level=levels.get(s.idx), row=counts.get(level)||0;counts.set(level,row+1);return {...s,x:24+level*286,y:24+row*124};});
    const edges=nodes.flatMap(s=>(s.depends_on||[]).filter(d=>byId.has(d)).map(from=>({from,to:s.idx})));
    return {nodes,edges,width:Math.max(220,...nodes.map(s=>s.x+250)),height:Math.max(110,...nodes.map(s=>s.y+112))};
  }
  function dagHTML(run) {
    const g=dag(run),by=new Map(g.nodes.map(s=>[s.idx,s]));
    if(!g.nodes.length)return '<div class="product-empty">执行图将在方案生成后出现。</div>';
    return `<div class="kernel-dag-caption"><span>真实文件依赖 · 点击节点聚焦动作、契约与证据</span><span>${g.nodes.length} 个步骤 / ${g.edges.length} 条依赖</span></div><div class="kernel-dag"><svg width="${g.width}" height="${g.height}" viewBox="0 0 ${g.width} ${g.height}" aria-label="真实执行依赖图">${g.edges.map(e=>{const a=by.get(e.from),b=by.get(e.to);return `<path d="M${a.x+244} ${a.y+46} C${a.x+268} ${a.y+46},${b.x-24} ${b.y+46},${b.x} ${b.y+46}" fill="none" stroke="#49a78e" stroke-width="2"/>`;}).join('')}${g.nodes.map(n=>`<g role="button" tabindex="0" data-kernel-step="${n.idx}" data-run="${esc(run.run_id||'')}" aria-label="步骤 ${n.idx+1}：${esc(n.action)}"><title>${esc(n.action)} · ${esc(n.dependency_reason||'顺序依赖')}</title><rect x="${n.x}" y="${n.y}" width="244" height="98" rx="12" fill="${n.status==='done'?'#edf8f3':n.status==='failed'?'#fff0e8':'#f2f5f9'}" stroke="#bddbd0"/><text x="${n.x+14}" y="${n.y+22}" fill="#267968" font-size="13" font-weight="600">STEP ${n.idx+1} · ${esc(n.status)}</text><foreignObject x="${n.x+14}" y="${n.y+32}" width="216" height="62"><div xmlns="http://www.w3.org/1999/xhtml" style="font:13px/1.6 Microsoft YaHei,sans-serif;color:#20414f;overflow-wrap:anywhere">${esc(n.action||n.skill)}</div></foreignObject></g>`).join('')}</svg></div>`;
  }
  function selectionHTML(run){
    const retrieval=run.retrieval?.fabric||run.retrieval||{},selected=new Set(run.skills||[]),ranking=run.ranking||[];
    const rows=(retrieval.candidates||[]).slice(0,10),orchestration=run.staged?.orchestration||{},used=new Set((run.steps||[]).map(s=>s.skill));
    if(!rows.length)return '';
    return `<details class="contract-section"><summary>为什么采用这些技能 · 查看采用与未采用的候选</summary><div class="experiment-table"><table><thead><tr><th>候选技能</th><th>采用情况</th><th>检索来源</th><th>相关排序分</th><th>收益预测 / 探索项</th></tr></thead><tbody>${rows.map(c=>{const r=ranking.find(r=>r.name===c.name),reason=(orchestration.decisions||[]).find(d=>d.name===c.name)?.reason;return `<tr><td>${esc(c.name)}</td><td>${used.has(c.name)?'进入实际执行步骤':selected.has(c.name)?'编排采用；实际步骤未使用':'本次编排未采用'}${reason?'<br>'+esc(reason):''}</td><td>${esc((c.channels||[]).join(' / '))}</td><td>${Number(c.score||0).toFixed(3)}</td><td>${r?esc(r.exploit)+' / '+esc(r.explore):'未进入策略排序'}</td></tr>`;}).join('')}</tbody></table></div><p>总体编排依据：${esc(orchestration.reason||'此历史记录未保存理由，不能补写模型当时的判断')}。<br>本次编码器：${esc(retrieval.encoder?.kind||"历史记录未保存")} ${esc(retrieval.encoder?.model||"")}；融合权重（关键词 / 语义 / 结构）：${esc((retrieval.weights||[]).join(" / ")||"未记录")}。<br>检索分用于本次排序，收益预测和探索项来自历史反馈；它们不是成功概率。编排采用依据以编排理由和实际步骤为准。</p></details>`;
  }
  function outcomeHTML(run){
    const m=metrics(run);if(!m.terminal)return '';
    const verdict=run.staged?.acceptance,state=verdict?.state,scope=run.staged?.execution_scope;
    return `<div class="kernel-outcome"><div><h4>${esc(labels[run.status]||run.status)} · <strong>${state?({passed:'验收通过',failed:'验收未通过',unknown:'有待确认'}[state]||state):'逐项核对验收'}</strong></h4><p>${m.done}/${m.total} 步执行完成 · ${(run.artifacts||[]).filter(a=>a.kind!=='跨轮输入').length} 个交付文件 · ${m.repairs} 步经过修复。${m.gate.eligible===false?'学习被拦截：'+esc(m.gate.reason):run.evolution?.candidate?'新经验已生成候选，等待冻结任务验证':run.evolution?.accepted?'已产生准入记录':'本次没有新增技能'}</p></div><a href="/run?id=${encodeURIComponent(run.run_id)}">检查结果与证据 ↗</a></div>${filesHTML(run)}${scope?`<div class="kernel-scope">规划 ${scope.planned} 步，预算允许 ${scope.max_steps} 步，实际执行 ${scope.executed} 步。${(scope.omitted||[]).length?'尚未执行：'+esc(scope.omitted.map(s=>s.action).join('；')):'已覆盖本次全部规划。'}</div>`:''}`;
  }
  function evidenceHTML(run, compact=false) {
    const m=metrics(run), used=(run.skills||[]).length, impact=m.impact;
    const phases=[['检索','找到可用能力',`${used} 个技能进入本次任务`,!!Object.keys(run.retrieval||{}).length],
      ['选择','按任务挑选技能',`${(run.ranking||[]).length} 项策略排序记录`,!!(run.ranking||[]).length],
      ['编排','把能力连成工作流',`${m.total} 步 · ${(run.steps||[]).reduce((n,s)=>n+(s.depends_on||[]).length,0)} 条依赖`,!!m.total],
      ['执行','让方案变成产物',`${m.done}/${m.total} 步完成 · ${m.repairs} 步自动修复`,m.done>0],
      ['验收','核对交付证据',`${m.passed}/${m.checks} 程序检查 · ${m.confirmed}/${m.semantic} 语义确认`,m.checks>0&&m.passed===m.checks&&m.unconfirmed.length===0],
      ['反馈','记录成功与失败',`${impact.summary?.updated_n||0} 个技能执行账本更新`,!!impact.summary],
      ['沉淀','有证据才学习',m.gate.eligible===false?'学习准入已拦截':run.evolution?.candidate?'候选待冻结任务验证':run.evolution?.accepted?'新技能已准入':m.gate.eligible===true?'已满足学习条件':'未记录准入结论',m.gate.eligible===true]];
    return `<section class="kernel-evidence ${compact?'compact':''}" aria-label="本次任务内核证据"><div class="kernel-heading"><div><span class="product-eyebrow">ENGINE / EVIDENCE</span><h3>这个问题，框架实际做了什么</h3></div><a href="/run?id=${encodeURIComponent(run.run_id||'')}">打开完整轨迹 ↗</a><a href="/graph?run=${encodeURIComponent(run.run_id||'')}">本次技能子图 ↗</a></div>${outcomeHTML(run)}<div class="kernel-phases">${phases.map(([name,value,fact,done],i)=>`<div class="kernel-phase ${done?'done':i===4&&m.terminal?'attention':'pending'} ${!m.terminal&&i===phases.findIndex(p=>!p[3])?'current':''}"><small>0${i+1} / ${name}</small><b>${value}</b><span>${esc(fact)}</span></div>`).join('')}</div>${!compact?dagHTML(run):''}<div class="kernel-verdict ${m.unconfirmed.length||m.gate.eligible===false?'attention':''}"><b>${m.checks?m.passed===m.checks?'程序检查全部通过':'存在未通过的程序检查':'尚无程序验收证据'}</b><span>${m.unconfirmed.length?`${m.unconfirmed.length} 项语义要求尚未确认：${esc(m.unconfirmed.slice(0,3).map(v=>v.item).join('；'))}`:m.semantic?'产物语义复核已完成':'尚无产物语义复核记录'}${m.gate.reason?' · '+esc(m.gate.reason):''}</span></div>${selectionHTML(run)}</section>`;
  }
  function filesHTML(run) {
    return `<div class="product-files">${(run.artifacts||[]).map(a=>`<button type="button" data-artifact-preview data-run="${esc(run.run_id)}" data-file="${esc(a.name)}" data-sha="${esc(a.sha256||'')}"><span class="file-glyph">${esc((a.name.split('.').pop()||'FILE').toUpperCase())}</span><span><b>${esc(a.name)}</b><small>${a.kind==='跨轮输入'?'历史输入版本 · ':'本次交付 · '}${(Number(a.bytes||0)/1024).toFixed(1)} KB · 点击核对</small></span><span>↗</span></button>`).join('')}</div>`;
  }
  function parseCSV(text) {
    const rows=[];let row=[],cell='',quoted=false;
    for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if((c==='\n'||c==='\r')&&!quoted){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);rows.push(row);row=[];cell='';}else cell+=c;}
    if(cell||row.length){row.push(cell);rows.push(row);}return rows;
  }
  function experimentsHTML(results, stats={}) {
    const entries=Object.entries(results||{}).filter(([name,data])=>/^exp[123]_/.test(name)&&data&&typeof data==='object').sort(([a],[b])=>Number(b.endsWith('_heldout'))-Number(a.endsWith('_heldout'))||a.localeCompare(b));
    if(!Object.keys(results||{}).length)return '<p class="empty">尚无实验记录。</p>';
    const number=(v,d=3)=>v!=null&&Number.isFinite(Number(v))?Number(v).toFixed(d):'—';
    const percent=v=>v!=null&&Number.isFinite(Number(v))?number(Number(v)*100,1)+'%':'—';
    const modes={bm25:'BM25 关键词',hybrid:'混合检索',fabric:'完整方案',bare:'无技能',cards:'仅技能卡',linucb:'LinUCB 选择',random:'随机选择'};
    const table=(heads,rows)=>`<div class="experiment-table"><table><thead><tr>${heads.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(cell=>`<td>${esc(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    const meter=(value,label)=>{const n=Math.max(0,Math.min(100,Number(value)*100||0));return `<div class="experiment-meter"><span>${esc(label)}</span><div role="meter" aria-label="${esc(label)}" aria-valuenow="${n.toFixed(1)}" aria-valuemin="0" aria-valuemax="100"><i style="width:${n}%"></i></div><b>${percent(value)}</b></div>`;};
    let html=`<div class="product-block experiment-note"><span class="product-eyebrow">BENCHMARK / FROZEN RECORDS</span><h3>先核对实验口径，再判断能力增益</h3><p>${stats.total!=null?`当前资产 ${esc(stats.total)} 个技能 / ${esc(stats.edges)} 条关系。`:''}历史方案实验与本轮真实执行分别展示；记录对应各自运行时的技能版本。方案盲评、程序验收和科研效果分别核对。</p><a href="/api/results" target="_blank">核对全部原始实验 JSON ↗</a></div>`;
    const executed=Object.entries(results||{}).filter(([,data])=>data?.evaluation_kind==='paired-real-execution');
    for(const [name,data] of executed){
      const paired=Boolean(data.candidate_sha256),pairs=data.pairs||[];
      const delta=pairs.length?pairs.reduce((sum,p)=>sum+Number(p.after)-Number(p.before),0)/pairs.length:null;
      const regressed=pairs.some(p=>Number(p.after)<Number(p.before));
      const frozenTasks=new Set(pairs.map(p=>p.task_sha256)).size;
      const rejected=paired&&(delta==null||delta<=0||regressed||pairs.length<4||frozenTasks<2);
      html+=`<section class="product-block experiment-card"><span class="product-eyebrow">REAL EXECUTION / INDEPENDENT ORACLE · ${esc(name)}</span><h3>${paired?'候选技能的学习前后评测':'真实产物的同题对照'}</h3><p>${esc(data.oracle_scope||'')}。${paired?`${frozenTasks} 道冻结任务 / ${pairs.length} 组配对，逐次实际调用模型并执行代码；候选内容由 SHA-256 绑定。`:'三组采用相同数据、执行图与验收口径；每组实际调用模型并执行代码。'}</p>${paired?`<div class="experiment-warning"><b>${rejected?'未满足晋级条件 · 保持候选':'报告满足分数门槛 · 晋级仍须核验物理证据'}</b><p>平均得分差 ${number(delta,4)}${regressed?'，存在回退':''}。${delta===0?'本轮没有测出质量增益，不能声称学习后更好。':'这组样本不代表总体能力或报告洞察质量。'}</p><p>候选指纹 ${esc(data.candidate_sha256)}</p></div>`:''}${table(['供给方式','任务','数值与产物检查','实际成本','运行证据'],(data.cases||[]).map(row=>[{none:'无技能知识',prompt:'背景技能',contract:'契约技能',before:'学习前',after:'候选技能'}[row.mode]||row.mode,row.id,percent(row.score),'¥'+number(row.cost_yuan,4),row.run_id]))}${paired?'':'<p>本次各组都通过时，仅说明这组任务未区分出质量增益；不能据此声称契约技能全面优于其它方式。</p>'}<p>${(data.cases||[]).map(row=>`<a href="/run?id=${encodeURIComponent(row.run_id)}">${esc(row.mode)} 完整轨迹 ↗</a>`).join(' · ')}</p></section>`;
    }
    for(const [name,data] of entries){
      const kind=name.slice(0,4),held=name.endsWith('_heldout');
      const mismatch=held&&(data.split&&data.split!=='heldout'||String(data.dataset||'').includes('dev'));
      html+=`<section class="product-block experiment-card"><span class="product-eyebrow">${held?'HOLD-OUT 命名记录':'DEV / 开发实验'} · ${esc(name)}</span><h3>${{exp1:'技能检索与依赖编排',exp2:'研究方案与盲评对照',exp3:'选择与进化闭环'}[kind]}</h3><p class="experiment-meta">${esc(data.timestamp||'未记录时间')} · ${esc(data.n_tasks??'—')} 个任务${data.k!=null?' · K='+esc(data.k):''}${data.repeats!=null?' · '+esc(data.repeats)+' 次重复':''}${data.rounds!=null?' · '+esc(data.rounds)+' 轮':''}</p>`;
      if(mismatch)html+='<p class="experiment-warning">原始 split / dataset 字段与 heldout 文件名不一致；这里保留原始数值，任务划分须复核后才能作为独立测试集结论。</p>';
      if(kind==='exp1'){
        const rows=Object.entries(data.summary||{});
        html+=`<p>技能召回核对金标准技能集；编排完整度核对金标准依赖边。相关度与召回不能证明产物正确。</p><div class="experiment-meters">${rows.map(([mode,row])=>meter(row.skill_recall,modes[mode]||mode)).join('')}</div>`;
        html+=table(['检索策略','技能召回','完全覆盖','编排完整度'],rows.map(([mode,row])=>[modes[mode]||mode,percent(row.skill_recall),percent(row.full_coverage_rate),percent(row.orchestration_completeness)]));
      }else if(kind==='exp2'){
        const rows=Object.entries(data.summary||{});
        html+='<p>模型盲评评价研究方案，要点覆盖率核对方案中的陷阱与验证清单；这些分数不代表代码已经执行。</p>';
        html+=table(['技能供给','方案盲评 / 10','要点覆盖率','相对基线','平均成本'],rows.map(([mode,row])=>[modes[mode]||mode,number(row.avg_score,3),percent(row.avg_coverage),mode==='bare'?'基线':number(row.gain_pct,1)+'%','¥'+number(row.avg_cost_yuan,4)]));
        html+=`<details class="contract-section"><summary>查看各评审维度</summary>${table(['供给方式','评审维度均分'],rows.map(([mode,row])=>[modes[mode]||mode,Object.entries(row.dim_avg||{}).map(([key,value])=>key+': '+number(value,2)).join(' · ')]))}</details>`;
      }else{
        const rows=Object.entries(data.results||{}),stat=data.statistics||{};
        html+='<p>历史方案评价奖励参与选择器更新和技能蒸馏。是否优于随机选择，应以统计检验为依据。</p>';
        html+=table(['选择策略','平均奖励 ± 标准差','库规模','新技能','成本'],rows.map(([mode,row])=>[modes[mode]||mode,number(row.mean_reward,4)+' ± '+number(row.std,4),row.library_size??'—',(row.evolved_skills||[]).length,'¥'+number(row.cost_yuan,4)]));
        html+=`<div class="experiment-curves">${rows.map(([mode,row])=>`<div><b>${esc(modes[mode]||mode)} · 逐轮奖励</b><div class="experiment-curve">${(row.curve||[]).map(point=>`<div title="${esc('第 '+point.round+' 轮 · '+point.chosen+' · 奖励 '+point.reward)}" style="height:${Math.max(4,Math.min(100,Number(point.reward)*100||0))}%;background:${point.evolved?'#bc644d':'#67ad98'}"><small>${esc(point.round)}</small></div>`).join('')}</div><p>朱红柱标记该轮产生的新技能。</p></div>`).join('')}</div>`;
        html+=`<div class="experiment-warning"><b>统计结论 · ${esc(stat.verdict||'未记录')}</b><p>${esc(stat.conclusion||'尚无统计检验，不能据此声称选择策略优于随机。')}</p>${stat.ci95?`<p>配对 bootstrap · n=${esc(stat.n)} · 均值差 ${number(stat.mean_diff,4)} · 95% 区间 [${stat.ci95.map(v=>number(v,4)).join(', ')}]</p>`:''}</div>`;
      }
      html+=`<details class="contract-section"><summary>查看原始口径</summary><pre>${esc(JSON.stringify({file:name+'.json',dataset:data.dataset??null,split:data.split??null,timestamp:data.timestamp,k:data.k,repeats:data.repeats,rounds:data.rounds,alpha:data.alpha},null,2))}</pre></details></section>`;
    }
    return `<div class="product-experiments">${html}</div>`;
  }
  const core={esc,terminal,labels,metrics,dag,dagHTML,evidenceHTML,outcomeHTML,selectionHTML,filesHTML,parseCSV,experimentsHTML};
  if(typeof module!=='undefined'&&module.exports)module.exports=core;
  if(!root?.document)return;
  root.Product=core;
  async function preview(button) {
    const run=button.dataset.run,file=button.dataset.file,sha=button.dataset.sha||'';
    const url=`/api/runs/${encodeURIComponent(run)}/artifacts/${encodeURIComponent(file)}`;
    let dialog=document.getElementById('product-preview');
    if(!dialog){dialog=document.createElement('dialog');dialog.id='product-preview';dialog.className='product-preview';document.body.appendChild(dialog);}
    dialog.innerHTML=`<header><div><small>DELIVERABLE / ${esc(run)}</small><h3>${esc(file)}</h3></div><form method="dialog"><button>关闭</button></form></header><div class="preview-content" role="status">正在读取产物…</div><footer><span>${sha?'SHA-256 · '+esc(sha):'此历史产物未记录指纹'}</span><a href="${url}" download>下载文件 ↗</a></footer>`;
    dialog.showModal();const host=dialog.querySelector('.preview-content');
    if(/\.(png|jpe?g|webp|gif|svg)$/i.test(file)){const img=document.createElement('img');img.alt=file;img.src=url;img.onerror=()=>{host.innerHTML=root.UI.errorHTML('产物无法读取');};host.replaceChildren(img);return;}
    if(/\.pdf$/i.test(file)){host.innerHTML=`<object data="${url}" type="application/pdf" width="100%" height="500"><p>当前浏览器无法嵌入 PDF，可下载完整文件查看。</p></object>`;return;}
    if(!/\.(csv|tsv|txt|md|py|json|html|svg|log)$/i.test(file)){host.innerHTML='<p>此文件格式请下载后查看，完整文件指纹见下方。</p>';return;}
    try{const res=await root.UI.fetch(url);if(!res.ok)throw new Error('产物读取失败（HTTP '+res.status+'）');
      // Bound previews independently of the download size. Never interpret artifact HTML.
      const reader=res.body.getReader();let bytes=0,parts=[];
      try{while(bytes<65536){const {value,done}=await reader.read();if(done)break;parts.push(value.slice(0,65536-bytes));bytes+=value.length;}}finally{await reader.cancel().catch(()=>{});}
      const joined=new Uint8Array(parts.reduce((n,p)=>n+p.length,0));let offset=0;
      for(const part of parts){joined.set(part,offset);offset+=part.length;}
      const text=new TextDecoder().decode(joined);
      if(!dialog.open||dialog.querySelector('h3').textContent!==file)return;
      if(/\.csv$/i.test(file)){
        const rows=parseCSV(text.replace(/^\ufeff/,''));
        host.innerHTML=`<table><thead><tr>${(rows[0]||[]).slice(0,12).map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${rows.slice(1,41).map(row=>`<tr>${row.slice(0,12).map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table><p class="preview-note">已读取 ${rows.length-1} 行数据 · 预览最多 40 行 / 12 列 / 64 KB</p>`;
      }else host.innerHTML=`<pre>${esc(text)}</pre>`;
      if(bytes>=65536)host.insertAdjacentHTML('beforeend','<p>预览最多显示 64 KB，完整内容可下载核对。</p>');
    }catch(e){if(dialog.open)host.innerHTML=root.UI.errorHTML(e);}
  }
  function boot(){
    const path=location.pathname, page=path==='/chat'?'chat':path==='/graph'?'graph':path==='/run'?'run':path==='/runs'?'center':path==='/dashboard'?'lab':'briefing';
    document.documentElement.dataset.product=page;
    if(page==='briefing'||page==='chat')root.UI.json('/api/scenarios').then(data=>{const first=data.items?.[0],input=document.getElementById('task')||document.getElementById('q'),host=document.getElementById('show-composer-slot')||document.querySelector('.chips');if(!first||!input||!host)return;const button=document.createElement('button');button.type='button';button.className='chip';button.textContent=first.title;button.onclick=()=>{input.value=first.task;input.focus();input.dispatchEvent(new Event('input',{bubbles:true}));};const row=document.createElement('div');row.className='scenario-preset';row.append(button);host.prepend(row);}).catch(()=>{});
    if(page!=='briefing'){
      const shell=document.createElement('div');shell.className='product-shell';shell.innerHTML=`<a class="product-brand" href="/">${root.UI.mark}<span>SkillNet<small>S1 · 能力运维层</small></span></a>${root.UI.productNav(page==='center'||page==='run'?'dashboard':page==='lab'?'technical':page)}<span class="product-live" id="product-live" role="status">连接中…</span>`;
      document.body.prepend(shell);
      root.UI.json('/api/health').then(h=>{document.getElementById('product-live').textContent=h.ok?(h.api_key_configured?'引擎已连接':'引擎在线 · 待配置模型'):'服务异常';}).catch(()=>{document.getElementById('product-live').textContent='连接失败';});
    }
    document.addEventListener('click',event=>{const button=event.target.closest('[data-artifact-preview]');if(button)preview(button);const node=event.target.closest('[data-kernel-step]');if(node)focusStep(node);});
    document.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&event.target.matches('[data-kernel-step]')){event.preventDefault();focusStep(event.target);}});
    async function focusStep(node){
      const id=node.dataset.run,idx=Number(node.dataset.kernelStep);if(!id)return;
      if(location.pathname==='/run'){document.dispatchEvent(new CustomEvent('kernel-step-focus',{detail:{idx}}));return;}
      try{const run=await root.UI.json('/api/runs/'+encodeURIComponent(id)),step=(run.steps||[]).find(s=>s.idx===idx);if(!step)return;let dialog=document.getElementById('kernel-step-dialog');if(!dialog){dialog=document.createElement('dialog');dialog.id='kernel-step-dialog';dialog.className='product-preview';document.body.append(dialog);}
      dialog.innerHTML=`<header><h3>STEP ${idx+1} · ${esc(step.action)}</h3><button type="button" data-close-step>关闭</button></header><div class="preview-content"><div class="kernel-scope">${esc(step.dependency_reason||'历史记录未保存依赖说明')}<br>技能：${esc(step.skill||'通用执行')}<br>实际输入：${esc((step.inputs||[]).join(' / ')||'无前序文件')}</div><pre>${esc(JSON.stringify(step.contract||{},null,2))}</pre><details><summary>完整代码与修复</summary><pre>${esc(step.code||'尚无代码')}</pre>${(step.attempts||[]).filter(a=>a.code_diff).map(a=>`<p>尝试 ${a.n} · ${esc(a.repair_reason)}</p><pre class="repair-diff">${esc(a.code_diff)}</pre>`).join('')}</details>${filesHTML({...run,artifacts:step.artifacts||[]})}</div>`;dialog.querySelector('[data-close-step]').onclick=()=>dialog.close();dialog.showModal();}catch(error){root.UI.toast(error.message);}
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})(typeof window==='undefined'?null:window);
