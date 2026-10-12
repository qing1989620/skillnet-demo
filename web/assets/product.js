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
    const retrieval=run.retrieval?.fabric||run.retrieval||{},recommended=new Set(retrieval.selected||[]),selected=new Set(run.skills||[]),ranking=run.ranking||[];
    const rows=retrieval.candidates||[],orchestration=run.staged?.orchestration||{},steps=run.steps||[],used=new Set(steps.map(s=>s.skill).filter(n=>n&&n!=='manual')),selection=retrieval.selection||{};
    const names=[...new Set([...selected,...used,...recommended])];
    if(!rows.length&&!names.length&&!selection.method)return '';
    const channels=xs=>(xs||[]).map(x=>({bm25:'关键词',vector:'向量',structural:'领域标签',graph:'关系扩展',fused:'融合'}[x]||x)).join(' / ');
    const state=n=>used.has(n)?'已进入执行步骤':selected.has(n)?'编排采用 · 本轮未执行':recommended.has(n)?'检索推荐 · 编排未采用':'本轮未采用';
    return `<section class="skill-route" aria-label="问题驱动的技能自检索"><div class="route-heading"><div><small>QUESTION → USEFUL SKILLS</small><h3>为这道题，找到有用的几个 Skill</h3></div><button type="button" data-capability-report data-run="${esc(run.run_id||'')}">状态变化与证据缺口 ↗</button><a href="/graph?run=${encodeURIComponent(run.run_id||'')}">能力球体 ↗</a></div><div class="route-funnel"><span><b>${selection.library_size==null?'—':esc(selection.library_size)}</b> 本轮技能库</span><i>→</i><span><b>${rows.length}</b> 检索候选</span><i>→</i><span><b>${recommended.size}</b> 检索推荐</span><i>→</i><span><b>${selected.size}</b> 编排采用 / <b>${used.size}</b> 进入执行</span></div><p class="route-method">${esc(selection.rule||'该历史记录未保存必要性筛选规则，以下只展示当时记录的候选、采用理由和实际步骤。')}${retrieval.degraded?' · 检索降级：'+esc(retrieval.degraded_reason||'见组件明细'):''}</p><div class="route-cards">${names.map((n,i)=>{const c=rows.find(c=>c.name===n)||{},reason=(orchestration.decisions||[]).find(d=>d.name===n)?.reason,actions=steps.filter(s=>s.skill===n);return `<article class="route-card ${used.has(n)?'used':'suggested'}"><div class="route-card-top"><small>${String(i+1).padStart(2,'0')} / ${esc(state(n))}</small><span>${esc(channels(c.channels)||'历史召回来源未记录')}</span></div><h4>${esc(n)}</h4><p class="route-capability">${esc(c.capability||'历史记录未保存能力摘要，以实际动作和原始技能版本为准。')}</p><p><b>${reason?'编排采用依据':c.note?'检索筛选依据':'采用依据'}</b>${esc(reason||c.note||'该记录没有保存具体理由，不能事后补写。')}</p>${c.outputs?.length?`<p><b>技能声明的交付物</b>${esc(c.outputs.join(' / '))}</p>`:''}<div class="route-actual"><b>实际参与</b>${esc(actions.map(s=>`Step ${Number(s.idx)+1} · ${s.action||s.skill} · ${labels[s.status]||({done:'完成',failed:'失败',running:'执行中',pending:'待执行',skipped:'跳过'}[s.status])||s.status}`).join('；')||'尚未进入执行步骤；推荐不等于已发挥作用。')}</div><button type="button" data-capability-skill="${esc(n)}">查看适用条件与失效边界 ↗</button></article>`;}).join('')||'<p class="route-empty">没有推荐适用技能；保留候选供核查，不为数量凑技能。</p>'}</div><p class="route-boundary">${steps.filter(s=>!s.skill||s.skill==='manual').length} 个步骤采用通用执行。检索推荐供编排参考，编排可从候选池补齐协作能力。采用理由是待检验的选择依据；进入执行也不等于证明贡献。实际结果看产物验收，提升奖励仍须通过十二道门。</p><details class="contract-section"><summary>查看全部候选与未采用理由 · ${rows.length} 项</summary><div class="experiment-table"><table><thead><tr><th>候选技能</th><th>采用情况与理由</th><th>召回来源</th><th>相关排序分</th><th>收益预测 / 探索项</th></tr></thead><tbody>${rows.map(c=>{const r=ranking.find(r=>r.name===c.name),reason=(orchestration.decisions||[]).find(d=>d.name===c.name)?.reason||c.note;return `<tr><td>${esc(c.name)}</td><td>${esc(state(c.name))}${reason?'<br>'+esc(reason):'<br>未记录具体理由'}</td><td>${esc(channels(c.channels))}</td><td>${Number(c.score||0).toFixed(3)}</td><td>${r?esc(r.exploit)+' / '+esc(r.explore):'未进入策略排序'}</td></tr>`;}).join('')}</tbody></table></div><p>总体编排依据：${esc(orchestration.reason||'历史记录未保存')}。编码器：${esc(retrieval.encoder?.kind||'历史记录未保存')} ${esc(retrieval.encoder?.model||'')}；融合权重：${esc((retrieval.weights||[]).join(' / ')||'未记录')}。分数用于排序，不是成功概率。当前展示 ${used.size} 项能力进入执行；没有据此声称已选出全库最优组合。</p></details></section>`;
  }
  function transitionsHTML(run){
    const steps=run.steps||[],observations=run.staged?.quality_assessment?.observations||[];
    if(!steps.length)return '';
    const measured=observations.filter(o=>(o.independent_checks||[]).length),generic=steps.filter(s=>!s.skill||s.skill==='manual'),unmeasured=steps.length-measured.length;
    return `<section class="transition-overview" aria-label="能力的实际状态变化"><header><div><small>INPUT STATE → OBSERVED EFFECT → EVIDENCE</small><h3>能力有没有发挥作用，沿实际产物检查</h3></div><button type="button" data-capability-report data-run="${esc(run.run_id)}">重新核对文件与证据 ↗</button></header><div class="transition-overview-grid">${steps.map(s=>{const o=observations.find(o=>o.idx===s.idx),checks=o?.independent_checks||[];return `<article><small>STEP ${Number(s.idx)+1} · ${esc(s.skill&&s.skill!=='manual'?s.skill:'通用执行')}</small><h4>${esc(s.action)}</h4><p><b>实际输入</b> ${esc((s.input_artifacts||[]).map(f=>f.logical_name||f.name).join(' / ')||'本次任务输入')}</p><i>↓</i><p><b>登记产物</b> ${esc((s.artifacts||[]).map(f=>f.logical_name||f.name).join(' / ')||'尚无登记产物')}</p><strong>${checks.length?'执行时独立结果检查 '+checks.filter(c=>c.passed===true).length+'/'+checks.length:'独立结果判据待补齐'}</strong></article>`;}).join('')}</div><p>${generic.length} 个通用步骤尚未绑定技能 · ${unmeasured} 个步骤缺少独立结果判据。以上是执行时记录；点击核对可重新检查物理文件。单次变化仍不证明技能因果贡献。</p></section>`;
  }
  function frontierSnapshotHTML(run){
    const f=run.staged?.capability_frontier||run.capability_frontier;
    if(!f||typeof f!=='object'||typeof f.version!=='string')return '';
    const observation=f.observation||{},diagnosis=f.diagnosis||{},rawChecks=Array.isArray(observation.checks)?observation.checks:observation.checks?.checks;
    const checks=Array.isArray(rawChecks)?rawChecks.filter(c=>c&&typeof c==='object'):[];
    const facts=Array.isArray(observation.facts)?observation.facts:[],gaps=Array.isArray(diagnosis.gaps)?diagnosis.gaps.filter(g=>g&&typeof g==='object'):[];
    const state={reachable_declared:'声明模型找到组合',retrieval_miss:'候选检索遗漏',unreachable_closed_world:'声明模型内不可达',evidence_insufficient:'证据不足',search_truncated:'搜索预算截断',unknown:'证据不足'};
    const providerNames=[...new Set(gaps.flatMap(g=>Array.isArray(g.providers)?g.providers:[]))];
    return `<section class="frontier-snapshot" aria-label="本次任务的有限能力边界观察"><header><div><small>OBSERVE → LOCATE GAP → TEST</small><h3>这个问题，还缺哪些条件与能力证据</h3></div><button type="button" class="frontier-button" data-frontier-open aria-haspopup="dialog">打开能力边界实验 ↗</button></header><p>${esc(state[diagnosis.state]||'尚未形成可确认结论')} · ${f.read_only===true?'只读诊断':'声明快照'}。${esc(f.scope||'仅本次输入和有限试验登记程序。')}</p><div class="frontier-snapshot-grid"><article><small>01 / 实际观测</small><b>${facts.length} 项已观测事实</b><p>${esc(facts.join(' / ')||'未登记可确认事实')}</p><span>${checks.filter(c=>c.state==='passed'||c.passed===true).length}/${checks.length} 项输入条件通过</span></article><article><small>02 / 未满足条件</small><b>${gaps.length} 项待补齐</b><ul>${gaps.map(g=>`<li><code>${esc(g.fact)}</code> · ${esc(g.kind==='no_registered_provider'?'试验登记集没有提供者':g.kind==='observed_or_provider_needed'?'需要观测或提供者':'待补证据')}</li>`).join('')||'<li>没有登记此类缺口；仍不证明实际效果。</li>'}</ul></article><article><small>03 / 试验登记提供者</small><b>${providerNames.length} 个候选程序</b><p>${esc(providerNames.join(' / ')||'暂无登记提供者')}</p><span>仅用于提出可复验假设，不自动执行或写回技能网络。</span></article></div><details><summary>输入指纹与原始诊断</summary><p>输入 SHA-256 <code>${esc(f.input_sha256||'未记录')}</code><br>版本 ${esc(f.version)}</p><pre>${esc(JSON.stringify(diagnosis,null,2))}</pre></details><p class="frontier-snapshot-boundary">${esc(f.boundary||'此处是有限模型的只读观察。声明路径不证明真实可达；缺少试验提供者也不代表整个技能库不会。')} 原有技能自检索继续生效，实验按钮只打开证据与公开情景，不会自动开始实测。</p></section>`;
  }
  function stateKernelHTML(run){
    const kernel=run.state_kernel||{},policy=run.staged?.state_policy||kernel.policy;
    if(!policy)return '';
    const composition=run.staged?.state_composition||kernel.declared_composition||{},steps=run.steps||[];
    const labels={passed:'已核实',failed:'条件不满足',unknown:'无法核实',not_declared:'未声明条件'};
    const meanings={file_exists:'文件存在',csv_schema:'列结构',csv_nonempty:'非空数据',csv_no_missing:'必填字段',csv_unique:'唯一键',csv_numeric_range:'数值范围',csv_values_in:'允许值',csv_disjoint_groups:'组间无实体泄漏',input_integrity:'输入版本完整性',frozen_contract:'冻结契约'};
    const checks=report=>(report?.checks||[]).map(c=>`<li><b>${esc(labels[c.state]||'未知')}</b> · ${esc(meanings[c.predicate?.kind]||c.predicate?.kind)} / <code>${esc(c.predicate?.file||'契约')}</code><br>${esc(c.detail)}${c.evidence?.sha256?`<small> · SHA ${esc(c.evidence.sha256.slice(0,12))}</small>`:''}</li>`).join('');
    return `<section class="transition-overview state-kernel" aria-label="可执行状态契约"><header><div><small>DECLARE → ADMIT → EXECUTE → VERIFY</small><h3>先证明能接着做，再执行；做完核实真实效果</h3></div></header><p>在代码生成之前读取真实输入，核对冻结条件与版本。条件失败或未知时阻断自动执行；不把阻断算成技能负贡献。${policy.host_reference?'本场景还叠加服务端独立定义的条件，模型不能删掉。':'模型提出的条件是待验证声明，不是完整质量标准。'}</p><div class="transition-overview-grid">${steps.map(s=>{const pre=s.state_evidence?.pre,post=s.state_evidence?.post;return `<article><small>STEP ${Number(s.idx)+1} · ${esc(s.skill||'通用执行')}</small><h4>${esc(s.action)}</h4><p><b>执行准入</b> ${esc(labels[pre?.state]||'尚未检查')} ${pre?.admitted===false?'· 已阻断代码生成':''}</p><p><b>产物效果</b> ${esc(labels[post?.state]||'尚未检查')}</p><details><summary>逐项核对条件、字节与判定</summary><h5>执行前</h5><ul>${checks(pre)||'<li>尚无检查记录</li>'}</ul><h5>执行后</h5><ul>${checks(post)||'<li>尚无检查记录</li>'}</ul><p>冻结指纹 <code>${esc(policy.frozen?.[String(s.idx)]?.sha256||'未记录')}</code></p></details></article>`;}).join('')}</div><details><summary>声明组合与当前缺口 · ${(composition.frontier||[]).length} 项待满足条件</summary><p>组合判定：${esc(({declared_compatible:'上游效果声明覆盖下游要求',contradicted:'存在相互矛盾的声明',unknown:'声明不足或有歧义'}[composition.state])||'未记录')}。声明可以用于规划，实际执行仍重新读取文件；这只是本次有限执行图的条件缺口，不代表系统全局不会。</p><ul>${(composition.frontier||[]).map(g=>`<li>STEP ${Number(g.step_idx)+1} · ${esc(g.file)} · ${esc(g.detail)}</li>`).join('')||'<li>未发现此类声明缺口；仍需运行时核验。</li>'}</ul></details><p>结构门禁不保证算法正确；数值结果继续接受独立复算。通过这些条件不会自动给任何技能加分。</p></section>`;
  }
  function outcomeHTML(run){
    const m=metrics(run);if(!m.terminal)return '';
    const verdict=run.staged?.acceptance,state=verdict?.state,scope=run.staged?.execution_scope;
    const learning=m.gate.mode==='shadow'?'正式网络未更新；保留影子观察。'+(run.evolution?.candidate?'新经验已隔离为候选，待独立验证。':''):m.gate.eligible===false?'学习被拦截：'+esc(m.gate.reason):run.evolution?.candidate?'新经验已生成候选，等待冻结任务验证':run.evolution?.accepted?'已产生准入记录':'本次没有新增技能';
    return `<div class="kernel-outcome"><div><h4>${esc(labels[run.status]||run.status)} · <strong>${state?({passed:'验收通过',failed:'验收未通过',unknown:'有待确认'}[state]||state):'逐项核对验收'}</strong></h4><p>${m.done}/${m.total} 步执行完成 · ${(run.artifacts||[]).filter(a=>!['跨轮输入','任务输入'].includes(a.kind)).length} 个交付文件 · ${m.repairs} 步经过修复。${learning}</p></div><a href="/run?id=${encodeURIComponent(run.run_id)}">检查结果与证据 ↗</a></div>${filesHTML(run)}${scope?`<div class="kernel-scope">规划 ${scope.planned} 步，预算允许 ${scope.max_steps} 步，实际执行 ${scope.executed} 步。${(scope.omitted||[]).length?'尚未执行：'+esc(scope.omitted.map(s=>s.action).join('；')):'已覆盖本次全部规划。'}</div>`:''}`;
  }
  function rewardReceiptHTML(skill){
    const receipt=skill.stats?.verified_improvement_receipt;
    if(!receipt)return '<p class="reward-history">该技能尚无通过十二道门的提升积分凭证。</p>';
    return `<details class="quality-details"><summary>已核验提升积分 +${Number(receipt.points||0).toFixed(2)} · 仅此版本</summary><p>${esc(receipt.scope)}。对照平均增益 ${Number(receipt.measured_mean_gain||0).toFixed(4)}。<br>版本 <code>${esc(receipt.candidate_sha256)}</code><br>评测计划 <code>${esc(receipt.evaluation_plan_sha256)}</code><br>奖励凭证 <code>${esc(receipt.id)}</code><br>没有向其他技能分配积分；正式排序参数未自动部署。</p></details>`;
  }
  function valueHTML(run){
    if(!terminal.includes(run.status))return '';
    const a=run.staged?.quality_assessment||{},g=run.staged?.reward_gates||{},outputs=(run.artifacts||[]).filter(f=>!['跨轮输入','任务输入'].includes(f.kind));
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
    return `<section class="kernel-evidence ${compact?'compact':''}" aria-label="本次任务内核证据"><div class="kernel-heading"><div><span class="product-eyebrow">ENGINE / EVIDENCE</span><h3>这个问题，框架实际做了什么</h3></div><a href="/run?id=${encodeURIComponent(run.run_id||'')}">打开完整轨迹 ↗</a><a href="/graph?run=${encodeURIComponent(run.run_id||'')}">本次技能子图 ↗</a></div>${selectionHTML(run)}${frontierSnapshotHTML(run)}${transitionsHTML(run)}${stateKernelHTML(run)}${valueHTML(run)}${outcomeHTML(run)}<div class="kernel-phases">${phases.map(([name,value,fact,done],i)=>`<div class="kernel-phase ${done?'done':i===4&&m.terminal?'attention':'pending'} ${!m.terminal&&i===phases.findIndex(p=>!p[3])?'current':''}"><small>0${i+1} / ${name}</small><b>${value}</b><span>${esc(fact)}</span></div>`).join('')}</div>${!compact?dagHTML(run):''}<div class="kernel-verdict ${m.unconfirmed.length||m.gate.eligible===false?'attention':''}"><b>${m.checks?m.passed===m.checks?'程序检查全部通过':'存在未通过的程序检查':'尚无程序验收证据'}</b><span>${m.unconfirmed.length?`${m.unconfirmed.length} 项语义要求尚未确认：${esc(m.unconfirmed.slice(0,3).map(v=>v.item).join('；'))}`:m.semantic?'产物语义复核已完成':'尚无产物语义复核记录'}${m.gate.reason?' · '+esc(m.gate.reason):''}</span></div>${assessmentDetailsHTML(run)}</section>`;
  }
  function filesHTML(run) {
    return `<div class="product-files">${(run.artifacts||[]).map(a=>`<button type="button" data-artifact-preview data-run="${esc(run.run_id)}" data-file="${esc(a.name)}" data-sha="${esc(a.sha256||'')}"><span class="file-glyph">${esc((a.name.split('.').pop()||'FILE').toUpperCase())}</span><span><b>${esc(a.name)}</b><small>${a.kind==='跨轮输入'?'历史输入版本 · ':a.kind==='任务输入'?'冻结任务输入 · ':'本次交付 · '}${(Number(a.bytes||0)/1024).toFixed(1)} KB · 点击核对</small></span><span>↗</span></button>`).join('')}</div>`;
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
    for(const data of Object.values(results||{}).filter(r=>r?.version==='capability-probe-lab-v1')){
      const strategies=data.summary||{},baseline=strategies.unconditional||{},gate=strategies.contract_gate||{};
      html+=`<section class="product-block experiment-card"><span class="product-eyebrow">CAPABILITY LAB / REAL PYTHON PROBES</span><h3>用反例测量能力边界，而不是只看技能说明</h3><p>${esc((data.admissions||[]).length)} 类公开模拟输入 × 3 个固定实现。两个正确实现采用不同代码；第三个只把 ≥ 写成 >。两种策略使用相同代码，输入、代码指纹与独立算术参考先冻结，实际启动 ${esc(Number(baseline.code_calls||0)+Number(gate.code_calls||0))} 次 Python 子进程，无模型评分参与判定。</p>${table(['实测指标','不设准入','真实条件准入'],[
        ['实际代码调用',baseline.code_calls,gate.code_calls],['违规输入仍执行',baseline.invalid_inputs_executed,gate.invalid_inputs_executed],
        ['违规输入仍生成指标',baseline.invalid_input_outputs,gate.invalid_input_outputs],['有效任务误阻断',baseline.valid_false_blocks,gate.valid_false_blocks],
        ['有效输出独立正确',`${baseline.independent_passes}/${baseline.valid_tasks}`,`${gate.independent_passes}/${gate.valid_tasks}`]])}
        <div class="experiment-warning"><b>保留失败：结构条件通过，算法仍可能错误</b><p>≥ 写成 > 的实现通过结构检查，却在阈值恰为 0.5 时被独立复算拒绝。门禁避免不适用输入的执行，不能把算法 bug 修好。unknown 也阻断，本实验没有修改正式技能库或发奖。</p></div>
        ${table(['公开探针','预注册准入','实际准入'],(data.admissions||[]).map(a=>[a.probe,a.expected,a.result?.state]))}
        <details><summary>行为签名与反例 · 有限观测，不自动合并技能</summary>${table(['实现对','共同观测探针','结论与反例'],(data.behavioral_comparisons||[]).map(c=>[c.left+' / '+c.right,(c.observed_probes||[]).join(', '),c.status==='finite_probe_agreement'?'仅本组探针一致':'反例区分：'+(c.counterexamples||[]).join(', ')]))}<p>两个实现未执行同一探针，不能据此认为行为一致。有限探针一致不证明普遍行为等价。</p></details><p>冻结协议 <code>${esc(data.protocol_sha256)}</code><br>报告 <code>${esc(data.report_sha256)}</code>。本页是留存实验记录；完整逐次输入、输出和代码见原始 JSON。</p></section>`;
    }
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
  function requestEpoch(){let epoch=0;return {begin(){const mine=++epoch;return ()=>epoch===mine;},invalidate(){epoch++;}};}
  const core={esc,terminal,labels,metrics,dag,dagHTML,evidenceHTML,outcomeHTML,valueHTML,resourcesHTML,resourcesButtonHTML,assessmentDetailsHTML,assessmentHTML,rewardGatesHTML,rewardReceiptHTML,selectionHTML,transitionsHTML,frontierSnapshotHTML,stateKernelHTML,capabilityReportHTML,filesHTML,parseCSV,experimentsHTML,requestEpoch};
  if(typeof module!=='undefined'&&module.exports)module.exports=core;
  if(!root?.document)return;
  root.Product=core;
  function beginPanel(id,title){
    let dialog=document.getElementById(id);
    if(!dialog){dialog=document.createElement('dialog');dialog.id=id;dialog.className='product-preview';document.body.append(dialog);}
    if(!dialog._requests){dialog._requests=requestEpoch();dialog.addEventListener('close',()=>dialog._requests.invalidate());dialog.addEventListener('cancel',()=>dialog._requests.invalidate());root.addEventListener('pagehide',()=>dialog._requests.invalidate());}
    const latest=dialog._requests.begin(),current=()=>latest()&&dialog.open;
    dialog.innerHTML=`<header><h3>${esc(title)}</h3><form method="dialog"><button>关闭</button></form></header><div class="preview-content" role="status">正在读取与核对…</div>`;
    if(!dialog.open)dialog.showModal();
    return {dialog,current,fail(error){if(current())dialog.querySelector('.preview-content').innerHTML=root.UI.errorHTML(error);}};
  }
  async function inspectResources(button){
    const panel=beginPanel('resources-dialog','完整技能资源'),dialog=panel.dialog;
    try{const data=await root.UI.json('/api/skill/'+encodeURIComponent(button.dataset.skillResources)+'/package');
      if(!panel.current())return;dialog.innerHTML=`<header><h3>${esc(data.name)} · 完整资源</h3><form method="dialog"><button>关闭</button></form></header><div class="preview-content">${resourcesHTML(data)}</div>`;
    }catch(error){panel.fail(error);}
  }
  async function readResource(button){
    const panel=beginPanel('resource-file-dialog','读取技能文件'),dialog=panel.dialog;
    button.disabled=true;
    try{
      const response=await root.UI.fetch('/api/skill/'+encodeURIComponent(button.dataset.skill)+'/resource?path='+encodeURIComponent(button.dataset.path));
      if(!response.ok)throw new Error(response.status===409?'资源指纹已改变，服务已停止交付。':'资源读取失败（HTTP '+response.status+'）');
      const raw=await response.arrayBuffer();if(raw.byteLength>2000000)throw new Error('资源超过读取上限');
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw))).map(b=>b.toString(16).padStart(2,'0')).join('');
      if(hash!==button.dataset.sha)throw new Error('资源与清单指纹不一致');
      let text='';try{text=new TextDecoder('utf-8',{fatal:true}).decode(raw);}catch(_){}
      const readable=text&&!text.includes('\u0000');
      if(!panel.current())return;dialog.innerHTML=`<header><h3>${esc(button.dataset.path)}</h3><form method="dialog"><button>关闭</button></form></header><div class="preview-content"><p>文件指纹已核对。资源是参考数据；此页面没有执行脚本。</p>${readable?`<pre>${esc(text.slice(0,65536))}</pre>${text.length>65536?'<p>预览最多 64 KB，完整内容可下载。</p>':''}`:'<p>二进制资源可下载后使用。</p>'}</div><footer><span>SHA-256 ${esc(hash)}</span><button type="button" data-save-resource>下载已核对资源 ↗</button></footer>`;
      const filename=button.dataset.path.split('/').pop();dialog.querySelector('[data-save-resource]').onclick=()=>{const url=URL.createObjectURL(new Blob([raw],{type:'application/octet-stream'}));const link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
    }catch(error){panel.fail(error);}finally{button.disabled=false;}
  }
  async function handoff(button){
    const panel=beginPanel('evidence-dialog','执行证据交付'),dialog=panel.dialog;
    const id=button.dataset.run;button.disabled=true;
    try{
      const data=await root.UI.json('/api/runs/'+encodeURIComponent(id)+'/evidence');
      if(!panel.current())return;dialog.innerHTML=`<header><div><small>S1 / EVIDENCE HANDOFF</small><h3>把这次执行带回项目</h3></div><form method="dialog"><button>关闭</button></form></header><div class="preview-content"><p>${data.handoff_ready?'登记文件已重新计算指纹，可作为项目附件的交付依据。':'当前记录未满足完整文件交付条件，请先检查下方文件与执行状态。'}</p><p>执行状态 ${esc(labels[data.status]||data.status)} · ${data.scope_verified?'执行时的已测范围得到支持':'结果仍需按范围核验'} · S1 线上联调待验证</p><table><thead><tr><th>登记文件</th><th>实时指纹核对</th><th>来源</th></tr></thead><tbody>${(data.files||[]).map(f=>`<tr><td>${esc(f.name)}</td><td>${f.integrity==='passed'?'一致':'缺失或不一致'}</td><td>${f.producer_step==null?'外部输入':'STEP '+(Number(f.producer_step)+1)}</td></tr>`).join('')}</tbody></table><p>证据包指纹 <code>${esc(data.capsule_sha256)}</code></p><p>导出包含文件清单、技能版本、输入输出关系、验收范围、成本和候选状态。文件本体由 S1 后端逐项下载并核验 SHA-256。</p><details><summary>完整接入数据</summary><pre>${esc(JSON.stringify(data,null,2))}</pre></details></div><footer><span>${esc(data.version)}</span><button type="button" data-save-capsule>下载证据包 JSON ↗</button></footer>`;
      dialog.querySelector('[data-save-capsule]').onclick=()=>{
        const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
        const link=document.createElement('a');link.href=url;link.download='skillnet-evidence-'+String(id).replace(/[^a-zA-Z0-9_-]/g,'')+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      };
    }catch(error){panel.fail(error);}finally{button.disabled=false;}
  }
  async function inspectValue(button){
    const panel=beginPanel('value-dialog','任务交付、核验与复用'),dialog=panel.dialog;
    try{const run=await root.UI.json('/api/runs/'+encodeURIComponent(button.dataset.run));
      if(!panel.current())return;dialog.innerHTML=`<header><h3>任务交付、核验与复用</h3><form method="dialog"><button>关闭</button></form></header><div class="preview-content">${valueHTML(run)}${assessmentDetailsHTML(run)}</div>`;
    }catch(error){panel.fail(error);}
  }
  function capabilityReportHTML(data){
    const m=data.summary||{},observation={violated_in_scope:'限定范围结果未通过',observed_in_scope:'本次限定范围得到支持',not_confirmed:'结果证据待补齐',execution_failed:'执行失败',artifact_integrity_failed:'文件完整性核对失败'};
    const files=xs=>(xs||[]).map(f=>`<p><code>${esc(f.name)}</code><br>${f.integrity==='passed'?'文件指纹一致':'指纹未确认或不一致'} · ${esc((f.sha256||'').slice(0,12))}</p>`).join('')||'<p>未登记文件</p>';
    return `<div class="capability-report"><p>从本次输入到真实产物，逐步核对发生了什么变化。文件已在读取时重新计算指纹。此报告不会重新评分或发奖。</p><div class="capability-summary"><div><b>${esc(m.observed_in_scope||0)} / ${esc(m.steps||0)}</b>步骤有独立范围证据</div><div><b>${esc(m.verified_file_links||0)} / ${esc(m.file_links||0)}</b>文件交接指纹一致</div><div><b>${esc(m.evidence_gaps||0)}</b>证据缺口</div></div><p>验收范围：${esc(data.scope||'历史记录未声明独立验收范围')}</p>${stateKernelHTML(data)}${frontierSnapshotHTML(data)}<div class="capability-transitions">${(data.steps||[]).map(s=>`<article class="capability-transition" data-observation="${esc(s.observation)}"><small>STEP ${Number(s.idx)+1} · ${esc(observation[s.observation]||'未知')}</small><h4>${esc(s.action)}</h4><p>技能：${esc(s.skill||'通用执行 · 未绑定技能')}<br>技能版本：<code>${esc(s.skill_sha256||'未记录')}</code></p><div class="capability-io"><div><b>实际输入状态</b>${files(s.inputs)}</div><i>→</i><div><b>已登记的产物状态</b>${files(s.effects)}</div></div><p>程序检查 ${esc(s.checks?.passed||0)}/${esc(s.checks?.total||0)} · 独立结果检查 ${esc(s.independent_checks?.passed||0)}/${esc(s.independent_checks?.total||0)}。适用条件与因果贡献尚未实测。</p></article>`).join('')}</div><details><summary>核对真实文件组合 · ${(data.composition||[]).length} 条交接</summary>${(data.composition||[]).map(e=>`<p>${e.source_run_id&&e.source_run_id!==data.run_id?'历史运行 '+esc(e.source_run_id)+' / ':''}STEP ${Number(e.source)+1} → STEP ${Number(e.target)+1} · ${esc(e.file)} · ${e.integrity==='passed'?'指纹一致':'待核验'}</p>`).join('')||'<p>没有记录跨步文件消费。</p>'}<p>依赖图表示执行顺序；这里仅展示确实被消费、且已登记版本的文件。文件交接仍不能证明技能语义兼容。</p></details><div class="capability-gaps"><h4>下一步该补什么证据</h4>${(data.evidence_gaps||[]).length?`<ul>${data.evidence_gaps.map(g=>`<li>${g.step==null?'规划':'STEP '+(Number(g.step)+1)} · ${esc(g.reason)}</li>`).join('')}</ul>`:'<p>本次未发现这些类型的记录缺口；不代表跨环境能力已经得到验证。</p>'}</div><p>${esc(data.boundary)}</p><details><summary>完整审计数据与指纹</summary><pre>${esc(JSON.stringify(data,null,2))}</pre></details></div>`;
  }
  async function inspectCapabilities(button){
    const panel=beginPanel('capabilities-dialog','能力状态与证据'),dialog=panel.dialog;
    button.disabled=true;
    try{const data=await root.UI.json('/api/runs/'+encodeURIComponent(button.dataset.run)+'/capabilities');
      if(!panel.current())return;dialog.innerHTML=`<header><div><small>CAPABILITY / OBSERVED TRANSITIONS</small><h3>这次运行，能力产生了什么变化</h3></div><form method="dialog"><button>关闭</button></form></header><div class="preview-content">${capabilityReportHTML(data)}</div><footer><span>${esc(data.version)}</span><button type="button" data-save-transitions>下载能力证据报告 ↗</button></footer>`;
      dialog.querySelector('[data-save-transitions]').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='skillnet-capabilities-'+data.run_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
    }catch(e){panel.fail(e);}finally{button.disabled=false;}
  }
  async function inspectPassport(button){
    const panel=beginPanel('passport-dialog','技能适用边界'),dialog=panel.dialog;
    button.disabled=true;try{const data=await root.UI.json('/api/skill/'+encodeURIComponent(button.dataset.capabilitySkill)),p=data.passport||{};
      const list=xs=>(xs||[]).length?'<ul>'+xs.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>':'<p>尚未声明</p>';
      if(!panel.current())return;dialog.innerHTML=`<header><h3>${esc(p.name)} · 能力边界</h3><form method="dialog"><button>关闭</button></form></header><div class="preview-content"><p>${esc(p.capability)}</p><h4>何时启用</h4>${list(p.activation)}<h4>输入 → 预期产物</h4>${list(p.inputs)}${list(p.effects)}<h4>失效边界与注意事项</h4>${list(p.failure_boundary)}<h4>如何验收</h4>${list(p.verification)}<p>${esc(p.boundary)}</p><p>当前版本 SHA-256 <code>${esc(p.skill_sha256)}</code>。当前声明不能代替执行时技能版本。</p><a href="/graph?skill=${encodeURIComponent(p.name)}">在球体中定位 ↗</a></div>`;
    }catch(e){panel.fail(e);}finally{button.disabled=false;}
  }
  async function preview(button) {
    const run=button.dataset.run,file=button.dataset.file,sha=button.dataset.sha||'';
    const url=`/api/runs/${encodeURIComponent(run)}/artifacts/${encodeURIComponent(file)}`;
    const panel=beginPanel('product-preview',file),dialog=panel.dialog;
    dialog.innerHTML=`<header><div><small>DELIVERABLE / ${esc(run)}</small><h3>${esc(file)}</h3></div><form method="dialog"><button>关闭</button></form></header><div class="preview-content" role="status">正在读取产物…</div><footer><span>${sha?'SHA-256 · '+esc(sha):'此历史产物未记录指纹'}</span><a href="${url}" download>下载文件 ↗</a></footer>`;
    const host=dialog.querySelector('.preview-content');
    if(/\.(png|jpe?g|webp|gif|svg)$/i.test(file)){const img=document.createElement('img');img.alt=file;img.src=url;img.onerror=()=>{if(panel.current())host.innerHTML=root.UI.errorHTML('产物无法读取');};host.replaceChildren(img);return;}
    if(/\.pdf$/i.test(file)){host.innerHTML=`<object data="${url}" type="application/pdf" width="100%" height="500"><p>当前浏览器无法嵌入 PDF，可下载完整文件查看。</p></object>`;return;}
    if(!/\.(csv|tsv|txt|md|py|json|html|svg|log)$/i.test(file)){host.innerHTML='<p>此文件格式请下载后查看，完整文件指纹见下方。</p>';return;}
    try{const res=await root.UI.fetch(url);if(!res.ok)throw new Error('产物读取失败（HTTP '+res.status+'）');
      // Bound previews independently of the download size. Never interpret artifact HTML.
      const reader=res.body.getReader();let bytes=0,parts=[];
      try{while(bytes<65536){const {value,done}=await reader.read();if(done)break;parts.push(value.slice(0,65536-bytes));bytes+=value.length;}}finally{await reader.cancel().catch(()=>{});}
      const joined=new Uint8Array(parts.reduce((n,p)=>n+p.length,0));let offset=0;
      for(const part of parts){joined.set(part,offset);offset+=part.length;}
      const text=new TextDecoder().decode(joined);
      if(!panel.current())return;
      if(/\.csv$/i.test(file)){
        const rows=parseCSV(text.replace(/^\ufeff/,''));
        host.innerHTML=`<table><thead><tr>${(rows[0]||[]).slice(0,12).map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${rows.slice(1,41).map(row=>`<tr>${row.slice(0,12).map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table><p class="preview-note">已读取 ${rows.length-1} 行数据 · 预览最多 40 行 / 12 列 / 64 KB</p>`;
      }else host.innerHTML=`<pre>${esc(text)}</pre>`;
      if(bytes>=65536)host.insertAdjacentHTML('beforeend','<p>预览最多显示 64 KB，完整内容可下载核对。</p>');
    }catch(e){if(panel.current())host.innerHTML=root.UI.errorHTML(e);}
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
    document.addEventListener('click',event=>{const cap=event.target.closest('[data-capability-report]');if(cap)inspectCapabilities(cap);const passport=event.target.closest('[data-capability-skill]');if(passport)inspectPassport(passport);const button=event.target.closest('[data-artifact-preview]');if(button)preview(button);const node=event.target.closest('[data-kernel-step]');if(node)focusStep(node);const exportButton=event.target.closest('[data-evidence-export]');if(exportButton)handoff(exportButton);const valueButton=event.target.closest('[data-run-value]');if(valueButton)inspectValue(valueButton);const resourcesButton=event.target.closest('[data-skill-resources]');if(resourcesButton)inspectResources(resourcesButton);const resourceButton=event.target.closest('[data-resource-read]');if(resourceButton)readResource(resourceButton);});
    document.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&event.target.matches('[data-kernel-step]')){event.preventDefault();focusStep(event.target);}});
    async function focusStep(node){
      const id=node.dataset.run,idx=Number(node.dataset.kernelStep);if(!id)return;
      if(location.pathname==='/run'){document.dispatchEvent(new CustomEvent('kernel-step-focus',{detail:{idx}}));return;}
      const panel=beginPanel('kernel-step-dialog','步骤执行证据'),dialog=panel.dialog;try{const run=await root.UI.json('/api/runs/'+encodeURIComponent(id)),step=(run.steps||[]).find(s=>s.idx===idx);if(!step){panel.fail('该运行没有这个步骤，请重新选择。');return;}
      if(!panel.current())return;dialog.innerHTML=`<header><h3>STEP ${idx+1} · ${esc(step.action)}</h3><button type="button" data-close-step>关闭</button></header><div class="preview-content"><div class="kernel-scope">${esc(step.dependency_reason||'历史记录未保存依赖说明')}<br>技能：${esc(step.skill||'通用执行')}<br>实际输入：${esc((step.inputs||[]).join(' / ')||'无前序文件')}</div><pre>${esc(JSON.stringify(step.contract||{},null,2))}</pre><details><summary>完整代码与修复</summary><pre>${esc(step.code||'尚无代码')}</pre>${(step.attempts||[]).filter(a=>a.code_diff).map(a=>`<p>尝试 ${esc(a.n)} · ${esc(a.repair_reason)}</p><pre class="repair-diff">${esc(a.code_diff)}</pre>`).join('')}</details>${filesHTML({...run,artifacts:step.artifacts||[]})}${run.staged?.skill_versions?.[step.skill]?.source==='github'?`<button type="button" data-skill-resources="${esc(step.skill)}">查看技能资源（社区技能） ↗</button>`:''}</div>`;dialog.querySelector('[data-close-step]').onclick=()=>dialog.close();}catch(error){panel.fail(error);}
    }
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})(typeof window==='undefined'?null:window);
