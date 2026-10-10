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
    const learning=m.gate.mode==='shadow'?'正式网络未更新；保留影子观察。'+(run.evolution?.candidate?'新经验已隔离为候选，待独立验证。':''):m.gate.eligible===false?'学习被拦截：'+esc(m.gate.reason):run.evolution?.candidate?'新经验已生成候选，等待冻结任务验证':run.evolution?.accepted?'已产生准入记录':'本次没有新增技能';
    return `<div class="kernel-outcome"><div><h4>${esc(labels[run.status]||run.status)} · <strong>${state?({passed:'验收通过',failed:'验收未通过',unknown:'有待确认'}[state]||state):'逐项核对验收'}</strong></h4><p>${m.done}/${m.total} 步执行完成 · ${(run.artifacts||[]).filter(a=>a.kind!=='跨轮输入').length} 个交付文件 · ${m.repairs} 步经过修复。${learning}</p></div><a href="/run?id=${encodeURIComponent(run.run_id)}">检查结果与证据 ↗</a></div>${filesHTML(run)}${scope?`<div class="kernel-scope">规划 ${scope.planned} 步，预算允许 ${scope.max_steps} 步，实际执行 ${scope.executed} 步。${(scope.omitted||[]).length?'尚未执行：'+esc(scope.omitted.map(s=>s.action).join('；')):'已覆盖本次全部规划。'}</div>`:''}`;
  }
  function rewardReceiptHTML(skill){
    const receipt=skill.stats?.verified_improvement_receipt;
    if(!receipt)return '<p class="reward-history">该技能尚无通过十二道门的提升积分凭证。</p>';
    return `<details class="quality-details"><summary>已核验提升积分 +${Number(receipt.points||0).toFixed(2)} · 仅此版本</summary><p>${esc(receipt.scope)}。对照平均增益 ${Number(receipt.measured_mean_gain||0).toFixed(4)}。<br>版本 <code>${esc(receipt.candidate_sha256)}</code><br>评测计划 <code>${esc(receipt.evaluation_plan_sha256)}</code><br>奖励凭证 <code>${esc(receipt.id)}</code><br>没有向其他技能分配积分；正式排序参数未自动部署。</p></details>`;
  }
  function valueHTML(run){
    if(!terminal.includes(run.status))return '';
    const a=run.staged?.quality_assessment||{},g=run.staged?.reward_gates||{},outputs=(run.artifacts||[]).filter(f=>f.kind!=='跨轮输入');
    const measured=(a.independent_reference?.checks||[]),passed=measured.filter(c=>c.passed===true).length;
    const scoped=a.scope_verdict==='passed',done=(run.steps||[]).filter(s=>s.status==='done').length;
    return `<section class="value-capsule" aria-label="任务交付与 S1 复用"><div class="value-heading"><div><small>DELIVERY → EVIDENCE → REUSE</small><h3>这次运行，留下了什么</h3></div><span>${esc(labels[run.status]||run.status)}</span></div><div class="value-cells"><div><small>01 / 交付</small><b>${outputs.length} 个真实文件</b><p>${done}/${(run.steps||[]).length} 步完成 · 模型费用 ¥${Number(run.cost_yuan||0).toFixed(4)}</p></div><div><small>02 / 核验</small><b>${scoped?'已测范围得到支持':a.scope_verdict==='failed'?'已测范围发现问题':'结果判据有待补齐'}</b><p>${measured.length?`${passed}/${measured.length} 项独立参考检查`:'没有独立参考分数'} · 可追查检查与原始文件</p></div><div><small>03 / 积累</small><b>${run.evolution?.candidate?'已形成隔离候选':'保留可复盘的轨迹'}</b><p>${Number(g.passed||0)}/${Number(g.total||12)} 道奖励门通过 · 正式排序未自动更新</p></div></div><div class="value-scope"><b>当前可以支持的结论</b><p>${esc(a.scope||'保留执行事实；此历史记录没有独立结果评价。')}</p></div><div class="value-handoff"><div><b>接入 S1 的落点</b><p>项目会话接收执行时间线，项目附件接收产物，能力库接收待验证经验。</p><small>服务契约可用 · S1 线上联调待验证</small></div><button type="button" data-evidence-export data-run="${esc(run.run_id)}">核对并导出证据包 ↗</button></div></section>`;
  }
  function resourcesButtonHTML(skill){
    return skill?.source==='github'?`<button type="button" data-skill-resources="${esc(skill.name)}">原文、脚本与参考资源 ↗</button>`:'';
  }
  function resourcesHTML(data){
    return `<p>来源 ${esc(data.repository)} · 许可 ${esc(data.license)}<br>固定提交 <code>${esc(data.commit)}</code></p><p>资源已登记指纹；导入尚未经过执行认证。脚本作为参考文件读取，不自动运行。</p><table><thead><tr><th>资源</th><th>大小</th><th>按需读取</th></tr></thead><tbody>${(data.files||[]).map(f=>`<tr><td>${esc(f.path)}</td><td>${(Number(f.bytes)/1024).toFixed(1)} KB</td><td><button type="button" data-resource-read data-skill="${esc(data.name)}" data-path="${esc(f.path)}" data-sha="${esc(f.sha256)}">核对与读取 ↗</button></td></tr>`).join('')}</tbody></table>`;
  }
  function assessmentDetailsHTML(run){
    return `<details class="assessment-expand"><summary>展开独立评价、技能观察与十二道奖励门</summary>${assessmentHTML(run)}</details>`;
  }
  function rewardGatesHTML(decision){
    if(!decision)return '<div class="reward-history">本记录早于十二门奖励协议，未回填新的放行结论。</div>';
    const gates=decision.gates||[],passed=gates.filter(g=>g.status==='passed').length;
    const eligible=gates.length===12&&passed===12&&decision.eligible===true;
    const failed=gates.filter(g=>g.status==='failed').length,unknown=gates.length-passed-failed;
    const status={passed:'通过',failed:'未通过',unknown:'待证据'};
    return `<section class="reward-panel" aria-label="十二道奖励门禁"><div class="reward-heading"><div><span>REWARD ADMISSION / ALL CONSTRAINTS</span><h3>真正提升，才能领奖</h3></div><div class="reward-count"><b>${passed}<small> / ${gates.length}</small></b><span>道门已核验通过</span></div></div><p class="reward-intro">十二道门采用 <strong>AND</strong> 规则：每一道都通过，才获得提升积分。任一道失败或缺少证据，都不会发奖。模型评分只供参考。</p><div class="reward-progress" aria-label="${passed} 通过，${failed} 未通过，${unknown} 待证据">${gates.map(g=>`<i class="${['passed','failed'].includes(g.status)?g.status:'unknown'}" title="${esc(g.title)}：${status[g.status]||'待证据'}"></i>`).join('')}</div><ol class="reward-grid">${gates.map((g,i)=>`<li class="reward-gate ${['passed','failed'].includes(g.status)?g.status:'unknown'}"><div><small>${String(i+1).padStart(2,'0')}</small><span>${status[g.status]||'待证据'}</span></div><h4>${esc(g.title)}</h4><p>${esc(g.reason)}</p><details><summary>约束与证据</summary><p>${esc(g.rule)}</p><pre>${esc(JSON.stringify(g.evidence||{},null,2))}</pre></details></li>`).join('')}</ol><div class="reward-decision"><b>${decision.reward_applied===true&&eligible?'已写入版本提升积分':eligible?'全部通过 · 具备领奖资格':'奖励暂不发放'}</b><span>${eligible?'只奖励通过对照验证的技能版本；其他参与技能不分享奖励。':`${failed} 道未通过 · ${unknown} 道待证据。合格产物保留为经验，等待独立对照补齐提升证据。`}</span></div><p class="reward-boundary">${esc(decision.reward_scope||'积分仅适用于已验证的技能版本和评测范围')}。积分上限 25 分；同版本只奖一次。正式排序参数需要单独的部署验证。</p><details class="reward-fingerprint"><summary>核对奖励规则与审计指纹</summary><p>协议 <code>${esc(decision.version)}</code><br>规则 <code>${esc(decision.policy_sha256)}</code><br>审计 <code>${esc(decision.audit_sha256)}</code></p></details></section>`;
  }
  function assessmentHTML(run){
    const a=run.staged?.quality_assessment;
    if(!a)return terminal.includes(run.status)?'<div class="quality-history">历史评价记录 · 此记录未采用当前独立评价协议。旧参数变化不能作为网络提升的证据，系统没有事后补写评价结果。</div>':'';
    const contract=a.goal_contract||{},rows=a.observations||[],shadow=run.staged?.shadow_feedback||{};
    const verdict={passed:'已测范围通过',failed:'已测范围存在失败',unknown:'结果判据不足'}[a.scope_verdict]||'待核验';
    const measured=rows.filter(r=>r.observed_score!=null),checks=[...new Map([...(a.independent_reference?.checks||[]),...rows.flatMap(r=>r.independent_checks||[])].map(c=>[JSON.stringify(c),c])).values()];
    const source=contract.source==='frozen_research_reference'?'执行前冻结的科研样本与指标参考':contract.source==='frozen_business_reference'?'执行前冻结的独立业务算术参考':'用户任务未提供独立标准答案';
    const fmt=v=>v==null?'未分配':Number(v).toFixed(4);
    return `<article class="quality-panel" aria-label="结果判断依据"><div class="quality-title"><div><span>OUTCOME / EVIDENCE / RESTRAINT</span><h3>凭什么判断这次结果？</h3></div><b class="quality-badge ${esc(a.scope_verdict)}">${verdict}</b></div><p class="quality-lead">回答完成，只代表产生了一次经验。<strong>结果正确、技能有贡献、网络变好，是三个不同的命题。</strong></p><div class="quality-grid"><div><small>01 / 判断来源</small><b>${source}</b><p>${esc(a.scope)}</p><em>${a.reference_anchored_before_execution?'评价契约已在执行前锁定':'缺少冻结契约，不接受事后标准答案'}</em></div><div><small>02 / 证据强度</small><b>${measured.length} / ${rows.length} 步有可重算的结果观察</b><p>文件 SHA-256 核验 ${(a.integrity||[]).filter(c=>c.passed).length}/${(a.integrity||[]).length}；方案模型评分只供参考。步骤契约通过只说明符合该契约，不能代替用户目标。</p><em>整体任务质量与用户满意度：尚未确认</em></div><div><small>03 / 是否改变网络</small><b>正式策略更新 0 次</b><p>${esc(a.network?.reason||'保留观察，等待独立验证')}。</p><em>${run.evolution?.candidate?'候选已隔离保存 · 尚未晋级':'当前仅保留观察记录'}</em></div></div>${rewardGatesHTML(run.staged?.reward_gates)}<details class="quality-details" open><summary>逐步归因 · 只评价实际测到的部分</summary><div class="quality-scroll"><table><thead><tr><th>执行步骤 / 技能</th><th>结果依据</th><th>限定范围的观察</th><th>正式参数变化</th></tr></thead><tbody>${rows.map(r=>`<tr><td>STEP ${Number(r.idx)+1}<br><code>${esc(r.skill||'通用执行')}</code></td><td>${esc(r.reason)}<br><small>${(r.independent_checks||[]).length} 项独立重算 · ${r.necessary_passed}/${r.necessary_total} 必要执行检查</small></td><td>${r.observed_score==null?(r.verdict==='blocked'?'上游阻断 · 不归罪本步':'未确认 · 不分配奖励'):fmt(r.observed_score)+' / 1，仅限已测部分'}</td><td>0.0000<br><small>正式网络未更新</small></td></tr>`).join('')}</tbody></table></div></details><details class="quality-details"><summary>核对独立判据、实际值与文件指纹</summary><ul>${checks.map(c=>`<li><b>${c.passed?'通过':'未通过'} · ${esc(c.name)}</b>${c.expected!=null?`<span>参考 ${esc(c.expected)} / 实际 ${esc(c.actual??'缺失')}</span>`:`<span>${esc(c.detail||'只支持此项检查，不外推整体质量')}</span>`}</li>`).join('')||'<li>没有独立结果检查；执行成功和模型赞同都不能补足标准答案。</li>'}${(a.integrity||[]).map(c=>`<li><b>${c.passed?'指纹一致':'证据异常'} · ${esc(c.name)}</b><code>${esc(c.sha256)}</code></li>`).join('')}</ul><p>评价证据 SHA-256 <code>${esc(a.evidence_sha256)}</code><br>任务 SHA-256 <code>${esc(a.task_sha256)}</code><br>协议 ${esc(a.version)}</p></details><details class="quality-details"><summary>影子策略预演 · 关联变化不是实测增益</summary><p>在参数副本上预演一次更新，单次轨迹总权重最多 0.25。它没有写回正式策略，也没有证明因果贡献。没有结果判据的步骤不参与预演。</p><div class="quality-scroll"><table><thead><tr><th>技能</th><th>正式收益预测</th><th>副本变化量</th><th>预演权重</th></tr></thead><tbody>${(shadow.rows||[]).map(r=>`<tr><td>${esc(r.name)}</td><td>${fmt(r.exploit_before)} → ${fmt(r.exploit_after)}</td><td>${fmt(r.shadow_delta)}</td><td>${fmt(r.weight)}</td></tr>`).join('')||'<tr><td colspan="4">没有可用于预演的结果证据。</td></tr>'}</tbody></table></div></details><div class="quality-release"><b>什么时候才有资格晋级？</b><p>至少 5 道未用于生成候选的留出任务，每题至少 2 组同预算真实对照；物理产物重新验算，无任务回退，任务平均增益至少 0.02，按不同任务统计的单侧符号检验 p ≤ 0.05。重复运行不会冒充更多独立任务。以上是发布门槛，通过也只支持该评测范围；晋级候选不会自动部署新的排序参数。</p><small>仍未证明：${esc((a.unverified||[]).join(' / '))}。</small>${(a.issues||[]).map(s=>`<p>${esc(s)}</p>`).join('')}</div></article>`;
  }
  function evidenceHTML(run, compact=false) {
    const m=metrics(run), used=(run.skills||[]).length, impact=m.impact;
    const phases=[['检索','找到可用能力',`${used} 个技能进入本次任务`,!!Object.keys(run.retrieval||{}).length],
      ['选择','按任务挑选技能',`${(run.ranking||[]).length} 项策略排序记录`,!!(run.ranking||[]).length],
      ['编排','把能力连成工作流',`${m.total} 步 · ${(run.steps||[]).reduce((n,s)=>n+(s.depends_on||[]).length,0)} 条依赖`,!!m.total],
      ['执行','让方案变成产物',`${m.done}/${m.total} 步完成 · ${m.repairs} 步自动修复`,m.done>0],
      ['验收','核对交付证据',`${m.passed}/${m.checks} 程序检查 · ${m.confirmed}/${m.semantic} 语义确认`,m.checks>0&&m.passed===m.checks&&m.unconfirmed.length===0],
      ['反馈','记录成功与失败',`${impact.summary?.updated_n||0} 个技能执行账本更新`,!!impact.summary],
      ['沉淀','有证据才学习',m.gate.mode==='shadow'?'影子观察 · 正式网络未更新':m.gate.eligible===false?'学习准入已拦截':run.evolution?.candidate?'候选待冻结任务验证':run.evolution?.accepted?'新技能已准入':m.gate.eligible===true?'已满足学习条件':'未记录准入结论',m.gate.eligible===true]];
    return `<section class="kernel-evidence ${compact?'compact':''}" aria-label="本次任务内核证据"><div class="kernel-heading"><div><span class="product-eyebrow">ENGINE / EVIDENCE</span><h3>这个问题，框架实际做了什么</h3></div><a href="/run?id=${encodeURIComponent(run.run_id||'')}">打开完整轨迹 ↗</a><a href="/graph?run=${encodeURIComponent(run.run_id||'')}">本次技能子图 ↗</a></div>${valueHTML(run)}${outcomeHTML(run)}<div class="kernel-phases">${phases.map(([name,value,fact,done],i)=>`<div class="kernel-phase ${done?'done':i===4&&m.terminal?'attention':'pending'} ${!m.terminal&&i===phases.findIndex(p=>!p[3])?'current':''}"><small>0${i+1} / ${name}</small><b>${value}</b><span>${esc(fact)}</span></div>`).join('')}</div>${!compact?dagHTML(run):''}<div class="kernel-verdict ${m.unconfirmed.length||m.gate.eligible===false?'attention':''}"><b>${m.checks?m.passed===m.checks?'程序检查全部通过':'存在未通过的程序检查':'尚无程序验收证据'}</b><span>${m.unconfirmed.length?`${m.unconfirmed.length} 项语义要求尚未确认：${esc(m.unconfirmed.slice(0,3).map(v=>v.item).join('；'))}`:m.semantic?'产物语义复核已完成':'尚无产物语义复核记录'}${m.gate.reason?' · '+esc(m.gate.reason):''}</span></div>${selectionHTML(run)}${assessmentDetailsHTML(run)}</section>`;
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
      const rejected=paired&&(delta==null||delta<.02||regressed||pairs.length<10||frozenTasks<5);
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
  const core={esc,terminal,labels,metrics,dag,dagHTML,evidenceHTML,outcomeHTML,valueHTML,resourcesHTML,resourcesButtonHTML,assessmentDetailsHTML,assessmentHTML,rewardGatesHTML,rewardReceiptHTML,selectionHTML,filesHTML,parseCSV,experimentsHTML};
  if(typeof module!=='undefined'&&module.exports)module.exports=core;
  if(!root?.document)return;
  root.Product=core;
  async function inspectResources(button){
    try{const data=await root.UI.json('/api/skill/'+encodeURIComponent(button.dataset.skillResources)+'/package');
      let dialog=document.getElementById('resources-dialog');if(!dialog){dialog=document.createElement('dialog');dialog.id='resources-dialog';dialog.className='product-preview';document.body.append(dialog);}
      dialog.innerHTML=`<header><h3>${esc(data.name)} · 完整资源</h3><form method="dialog"><button>关闭</button></form></header><div class="preview-content">${resourcesHTML(data)}</div>`;dialog.showModal();
    }catch(error){root.UI.toast(error.message);}
  }
  async function readResource(button){
    button.disabled=true;
    try{
      const response=await root.UI.fetch('/api/skill/'+encodeURIComponent(button.dataset.skill)+'/resource?path='+encodeURIComponent(button.dataset.path));
      if(!response.ok)throw new Error(response.status===409?'资源指纹已改变，服务已停止交付。':'资源读取失败（HTTP '+response.status+'）');
      const raw=await response.arrayBuffer();if(raw.byteLength>2000000)throw new Error('资源超过读取上限');
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw))).map(b=>b.toString(16).padStart(2,'0')).join('');
      if(hash!==button.dataset.sha)throw new Error('资源与清单指纹不一致');
      let text='';try{text=new TextDecoder('utf-8',{fatal:true}).decode(raw);}catch(_){}
      const readable=text&&!text.includes('\u0000');
      let dialog=document.getElementById('resource-file-dialog');if(!dialog){dialog=document.createElement('dialog');dialog.id='resource-file-dialog';dialog.className='product-preview';document.body.append(dialog);}
      dialog.innerHTML=`<header><h3>${esc(button.dataset.path)}</h3><form method="dialog"><button>关闭</button></form></header><div class="preview-content"><p>文件指纹已核对。资源是参考数据；此页面没有执行脚本。</p>${readable?`<pre>${esc(text.slice(0,65536))}</pre>${text.length>65536?'<p>预览最多 64 KB，完整内容可下载。</p>':''}`:'<p>二进制资源可下载后使用。</p>'}</div><footer><span>SHA-256 ${esc(hash)}</span><button type="button" data-save-resource>下载已核对资源 ↗</button></footer>`;
      const filename=button.dataset.path.split('/').pop();dialog.querySelector('[data-save-resource]').onclick=()=>{const url=URL.createObjectURL(new Blob([raw],{type:'application/octet-stream'}));const link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};dialog.showModal();
    }catch(error){root.UI.toast(error.message);}finally{button.disabled=false;}
  }
  async function handoff(button){
    const id=button.dataset.run;button.disabled=true;
    try{
      const data=await root.UI.json('/api/runs/'+encodeURIComponent(id)+'/evidence');
      let dialog=document.getElementById('evidence-dialog');
      if(!dialog){dialog=document.createElement('dialog');dialog.id='evidence-dialog';dialog.className='product-preview';document.body.append(dialog);}
      dialog.innerHTML=`<header><div><small>S1 / EVIDENCE HANDOFF</small><h3>把这次执行带回项目</h3></div><form method="dialog"><button>关闭</button></form></header><div class="preview-content"><p>${data.handoff_ready?'登记文件已重新计算指纹，可作为项目附件的交付依据。':'当前记录未满足完整文件交付条件，请先检查下方文件与执行状态。'}</p><p>执行状态 ${esc(labels[data.status]||data.status)} · ${data.scope_verified?'执行时的已测范围得到支持':'结果仍需按范围核验'} · S1 线上联调待验证</p><table><thead><tr><th>登记文件</th><th>实时指纹核对</th><th>来源</th></tr></thead><tbody>${(data.files||[]).map(f=>`<tr><td>${esc(f.name)}</td><td>${f.integrity==='passed'?'一致':'缺失或不一致'}</td><td>${f.producer_step==null?'外部输入':'STEP '+(Number(f.producer_step)+1)}</td></tr>`).join('')}</tbody></table><p>证据包指纹 <code>${esc(data.capsule_sha256)}</code></p><p>导出包含文件清单、技能版本、输入输出关系、验收范围、成本和候选状态。文件本体由 S1 后端逐项下载并核验 SHA-256。</p><details><summary>完整接入数据</summary><pre>${esc(JSON.stringify(data,null,2))}</pre></details></div><footer><span>${esc(data.version)}</span><button type="button" data-save-capsule>下载证据包 JSON ↗</button></footer>`;
      dialog.querySelector('[data-save-capsule]').onclick=()=>{
        const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
        const link=document.createElement('a');link.href=url;link.download='skillnet-evidence-'+String(id).replace(/[^a-zA-Z0-9_-]/g,'')+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      };dialog.showModal();
    }catch(error){root.UI.toast(error.message);}finally{button.disabled=false;}
  }
  async function inspectValue(button){
    try{const run=await root.UI.json('/api/runs/'+encodeURIComponent(button.dataset.run));
      let dialog=document.getElementById('value-dialog');if(!dialog){dialog=document.createElement('dialog');dialog.id='value-dialog';dialog.className='product-preview';document.body.append(dialog);}
      dialog.innerHTML=`<header><h3>任务交付、核验与复用</h3><form method="dialog"><button>关闭</button></form></header><div class="preview-content">${valueHTML(run)}${assessmentDetailsHTML(run)}</div>`;dialog.showModal();
    }catch(error){root.UI.toast(error.message);}
  }
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
    if(page==='briefing'||page==='chat')root.UI.json('/api/scenarios').then(data=>{const presets=(data.items||[]).slice(0,2),input=document.getElementById('task')||document.getElementById('q'),host=document.getElementById('show-composer-slot')||document.querySelector('.chips');if(!presets.length||!input||!host)return;const row=document.createElement('div');row.className='scenario-preset';for(const first of presets){const button=document.createElement('button');button.type='button';button.className='chip';button.textContent=first.title;button.onclick=()=>{input.value=first.task;input.focus();input.dispatchEvent(new Event('input',{bubbles:true}));};row.append(button);}host.prepend(row);}).catch(()=>{});
    if(page!=='briefing'){
      const shell=document.createElement('div');shell.className='product-shell';shell.innerHTML=`<a class="product-brand" href="/">${root.UI.mark}<span>SkillNet<small>S1 · 能力运维层</small></span></a>${root.UI.productNav(page==='center'||page==='run'?'dashboard':page==='lab'?'technical':page)}<span class="product-live" id="product-live" role="status">连接中…</span>`;
      document.body.prepend(shell);
      root.UI.json('/api/health').then(h=>{document.getElementById('product-live').textContent=h.ok?(h.api_key_configured?'引擎已连接':'引擎在线 · 待配置模型'):'服务异常';}).catch(()=>{document.getElementById('product-live').textContent='连接失败';});
    }
    document.addEventListener('click',event=>{const button=event.target.closest('[data-artifact-preview]');if(button)preview(button);const node=event.target.closest('[data-kernel-step]');if(node)focusStep(node);const exportButton=event.target.closest('[data-evidence-export]');if(exportButton)handoff(exportButton);const valueButton=event.target.closest('[data-run-value]');if(valueButton)inspectValue(valueButton);const resourcesButton=event.target.closest('[data-skill-resources]');if(resourcesButton)inspectResources(resourcesButton);const resourceButton=event.target.closest('[data-resource-read]');if(resourceButton)readResource(resourceButton);});
    document.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&event.target.matches('[data-kernel-step]')){event.preventDefault();focusStep(event.target);}});
    async function focusStep(node){
      const id=node.dataset.run,idx=Number(node.dataset.kernelStep);if(!id)return;
      if(location.pathname==='/run'){document.dispatchEvent(new CustomEvent('kernel-step-focus',{detail:{idx}}));return;}
      try{const run=await root.UI.json('/api/runs/'+encodeURIComponent(id)),step=(run.steps||[]).find(s=>s.idx===idx);if(!step)return;let dialog=document.getElementById('kernel-step-dialog');if(!dialog){dialog=document.createElement('dialog');dialog.id='kernel-step-dialog';dialog.className='product-preview';document.body.append(dialog);}
      dialog.innerHTML=`<header><h3>STEP ${idx+1} · ${esc(step.action)}</h3><button type="button" data-close-step>关闭</button></header><div class="preview-content"><div class="kernel-scope">${esc(step.dependency_reason||'历史记录未保存依赖说明')}<br>技能：${esc(step.skill||'通用执行')}<br>实际输入：${esc((step.inputs||[]).join(' / ')||'无前序文件')}</div><pre>${esc(JSON.stringify(step.contract||{},null,2))}</pre><details><summary>完整代码与修复</summary><pre>${esc(step.code||'尚无代码')}</pre>${(step.attempts||[]).filter(a=>a.code_diff).map(a=>`<p>尝试 ${a.n} · ${esc(a.repair_reason)}</p><pre class="repair-diff">${esc(a.code_diff)}</pre>`).join('')}</details>${filesHTML({...run,artifacts:step.artifacts||[]})}${run.staged?.skill_versions?.[step.skill]?.source==='github'?`<button type="button" data-skill-resources="${esc(step.skill)}">查看技能资源（社区技能） ↗</button>`:''}</div>`;dialog.querySelector('[data-close-step]').onclick=()=>dialog.close();dialog.showModal();}catch(error){root.UI.toast(error.message);}
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})(typeof window==='undefined'?null:window);
