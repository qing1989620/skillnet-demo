/* Finite capability research: server observations stay distinct from claims.
 * No executable code, model key, or reward policy is accepted from this UI. */
(function (root) {
  'use strict';
  if (!root || !root.document) return;
  const doc = root.document;
  const labels = {
    reachable_declared:'声明模型找到组合', reachable:'模型中可达',
    observed_success:'本次实测通过', completed:'执行完成', passed:'通过',
    failed:'未通过', unknown:'证据不足', evidence_insufficient:'证据不足',
    retrieval_miss:'检索候选遗漏', unreachable_closed_world:'有限模型内不可达',
    unreachable:'有限模型未找到路径', search_truncated:'搜索预算截断',
    model_mismatch:'观测推翻当前假设', blocked:'条件阻断', skipped:'未执行',
    plan_found:'声明模型找到组合', rejected_by_oracle:'独立复核拒绝错误结果',
    execution_failed:'实际执行失败', budget_exhausted:'实测预算已用尽',
    search_unknown:'声明搜索尚无结论', evidence_changed:'证据发生变化',
    quarantined:'本次实验隔离该版本', invalid_input:'输入不符合约束'
  };
  const factNames={'data.file':'输入文件存在','data.schema':'列结构符合要求','data.nonempty':'数据非空','data.binary':'标签仅含 0 / 1','data.unique':'样本键唯一','data.disjoint':'跨集合实体无泄漏','data.complete':'评分字段完整','data.range':'评分位于合法范围','metrics.file':'已生成指标文件'};
  const operatorNames={deduplicate:'去除重复样本',exclude_cross_split:'排除跨集合泄漏',drop_missing_score:'清除缺失评分',metrics_decimal:'复算科研指标',metrics_strict_bug:'检验错误阈值版本'};
  const operatorActions={deduplicate:'按冻结策略保留首个样本，重新检查唯一键。',exclude_cross_split:'移除跨训练与测试集合重复出现的实体，重新核验泄漏。',drop_missing_score:'去除缺失评分行，并重新观测完整性与数值范围。',metrics_decimal:'在测试集合按冻结阈值计算指标，再交由独立 oracle 复核。',metrics_strict_bug:'用边界输入检验比较符偏差，不将结构通过当作算法正确。'};
  const experimentNotes={retrieval:'候选集没有路径时继续检查完整试验登记集，避免把检索遗漏误判为不会。',coverage:'对缺失条件定向实测后重新读取状态，比较有限任务覆盖与真实调用代价。',provider:'在相同输入上补入登记提供者，再由独立结果判据检验目标是否恢复。',counterexample:'阈值边界反例用于揭示结构条件全部通过时仍存在的算法错误。',unmodeled:'保留当前模型没有描述的真实失败，避免只报告成功案例。',finite_basis:'穷举冻结任务集合上的登记子集，并实测候选覆盖；结论仅限这些目标。'};
  let dialog, trigger, labHost, scenarioHost, resultHost, live, select, execute;
  let generation = 0, sequences = {}, requests = new Map(), returnFocus;
  const arr = value => Array.isArray(value) ? value : [];
  const obj = value => value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const text = value => value == null ? '未提供' : typeof value === 'string' ? value : JSON.stringify(value);
  const status = value => labels[String(value)] || (value == null ? '尚未判定' : '服务端状态：'+text(value));
  function el(tag, className, value) {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = text(value);
    return node;
  }
  function button(label, action, className) {
    const node = el('button', className || 'frontier-button', label);
    node.type = 'button'; node.addEventListener('click', action); return node;
  }
  function paragraph(host, value, className) { host.append(el('p',className || '',value)); }
  function raw(host, title, value) {
    const details = el('details','frontier-details'), summary = el('summary','',title);
    const encoded = JSON.stringify(value,null,2) ?? '未提供';
    details.append(summary,el('pre','',encoded.slice(0,80000)));
    if (encoded.length > 80000) paragraph(details,'屏幕预览已截断到 80,000 字符。');
    host.append(details);
  }
  function entries(host, value) {
    const data = obj(value), list = el('dl','frontier-data');
    for (const [key,item] of Object.entries(data).slice(0,40)) {
      if (item !== null && typeof item === 'object') continue;
      list.append(el('dt','',key),el('dd','',item));
    }
    if (list.children.length) host.append(list);
    else if (value == null) paragraph(host,'服务端未提供本项证据。','frontier-muted');
    else if (typeof value !== 'object') paragraph(host,value);
  }
  function factList(host, facts, label) {
    const block = el('section','frontier-facts'); block.append(el('h5','',label));
    if (Array.isArray(facts)) {
      const list = el('div','frontier-fact-tags');
      facts.slice(0,80).forEach(item=>{const tag=el('span','',factNames[item]||item);tag.title=text(item);list.append(tag);});
      block.append(list);
      if (!facts.length) paragraph(block,'没有登记事实。','frontier-muted');
    } else if (facts && typeof facts === 'object') entries(block,facts);
    else paragraph(block,facts == null ? '没有登记事实。' : facts,'frontier-muted');
    host.append(block);
  }
  function checks(host, value, label) {
    const items = Array.isArray(value) ? value : arr(value?.checks); if (!items.length) return;
    const details = el('details','frontier-details'); details.append(el('summary','',label+' · '+items.length+' 项'));
    const list = el('ul','frontier-checks');
    items.slice(0,100).forEach(check=>{
      const item = el('li'), record = obj(check);
      const verdict = record.state ?? (record.passed === true ? 'passed' : record.passed === false ? 'failed' : 'unknown');
      item.append(el('b','',status(verdict)),el('span','', ' · '+text(record.detail ?? record.name ?? record.id ?? record.predicate ?? check)));
      list.append(item);
    });
    details.append(list); host.append(details);
  }
  function section(host,title,kicker) {
    const node = el('section','frontier-section');
    if (kicker) node.append(el('small','frontier-kicker',kicker));
    node.append(el('h3','',title));host.append(node);return node;
  }
  function strategyTable(host,summary) {
    const names={flat:'平面候选直接执行',plan_only:'仅依赖声明规划',active:'状态规划 + 主动探针'};
    const strategies=obj(summary?.strategies),wrap=el('div','frontier-table-wrap'),table=el('table','frontier-table');
    const head=el('thead'),headRow=el('tr');
    ['执行策略','有效任务独立验收','实际代码调用','未通过复核仍生成指标','错误放行'].forEach(label=>headRow.append(el('th','',label)));
    head.append(headRow);table.append(head);const body=el('tbody');
    for (const [key,label] of Object.entries(names)) {
      const record=obj(strategies[key]),row=el('tr');if(key==='active')row.className='frontier-strategy-active';
      row.append(el('th','',label),el('td','',text(record.valid_verified)+' / '+text(summary?.valid_tasks)),el('td','',record.code_calls),el('td','',record.unverified_metric_outputs),el('td','',record.false_accepts));body.append(row);
    }
    table.append(body);wrap.append(table);host.append(wrap);
    paragraph(host,'三组都保留独立 oracle。未复核指标是中间产物，不等于错误交付；负例正确阻断也不计入有效任务成功率。表格同时报告覆盖与调用，主动实测增加调用，不能据此宣称省成本。','frontier-muted');
  }
  function probeFlow(host,probe) {
    const flow=el('ol','frontier-probe-flow');flow.setAttribute('aria-label','主动实验的证据链');
    const parts=[['输入','冻结任务与当前假设'],['缺口','区分未观测效果与缺少提供者'],['定向探针',probe?.selected_probe ?? '未选择'],['新观测',probe?.observation ?? '未提供'],['独立复核','用真实输出检验假设，保留反例']];
    parts.forEach(([title,value])=>{const item=el('li');item.append(el('b','',title),el('span','',value));flow.append(item);});host.append(flow);
    const calls=obj(probe?.first_counterexample_calls),row=el('dl','frontier-data');
    for(const [label,value] of [['固定顺序首次反例调用',calls.fixed],['主动选择首次反例调用',calls.active],['随机基线平均调用',probe?.random_mean]])
      row.append(el('dt','',label),el('dd','',value));host.append(row);
  }
  function errorView(host,error,retry) {
    host.replaceChildren(); const message = el('p','frontier-error',error?.message || error || '请求失败。');
    message.setAttribute('role','alert'); host.append(message);
    if (retry) host.append(button('重试读取',retry));
  }
  function stopRequests() {
    generation++;
    requests.forEach(record=>{clearTimeout(record.timer);record.controller.abort();});
    requests.clear();sequences={};
  }
  async function request(kind,url,options,success,failure) {
    const old = requests.get(kind); if (old) { clearTimeout(old.timer);old.controller.abort(); }
    const session = generation, serial = (sequences[kind] || 0)+1; sequences[kind]=serial;
    const controller = new AbortController(), record = {controller,timer:null,timedOut:false};
    const current = () => dialog?.open && generation===session && sequences[kind]===serial;
    record.timer = setTimeout(()=>{record.timedOut=true;controller.abort();},45000);
    requests.set(kind,record);
    try {
      if (!root.UI?.json) throw new Error('共享连接模块尚未就绪，请刷新页面后重试。');
      const data = await root.UI.json(url,{...(options || {}),signal:controller.signal});
      if (current()) success(data);
    } catch (error) {
      if (current()) failure(record.timedOut ? new Error('等待已超过 45 秒，请检查服务后重试。') : error);
    } finally {
      clearTimeout(record.timer);
      if (requests.get(kind)===record) requests.delete(kind);
    }
  }
  function renderLab(data) {
    if (!data || typeof data !== 'object' || typeof data.version !== 'string') throw new Error('实验报告格式不完整，未作为成功结果展示。');
    labHost.replaceChildren();
    paragraph(labHost,data.scope || '有限公开模拟任务；具体范围见原始协议。','frontier-lead');
    const summary = section(labHost,'冻结实验的观测','EXPERIMENT / OBSERVATION');
    const info=obj(data.summary);
    paragraph(summary,'预注册任务 '+text(info.task_count)+' · 有效任务 '+text(info.valid_tasks)+' · 无效输入任务 '+text(info.invalid_tasks)+' · 协议义务 '+(info.all_obligations_passed===true?'全部通过':info.all_obligations_passed===false?'存在未通过项':'尚未确认'));
    strategyTable(summary,info);raw(summary,'核对实验汇总原始字段',data.summary);
    const experiments = Array.isArray(data.experiments) ? data.experiments.map((value,index)=>[String(index+1),value]) : Object.entries(obj(data.experiments));
    const grid = el('div','frontier-experiments');
    for (const [key,value] of experiments.slice(0,12)) {
      const experiment = obj(value), card = el('article','frontier-experiment');
      card.append(el('small','frontier-kicker',experiment.id || key),el('h4','',experiment.title || experiment.name || experiment.label || key));
      if (experiment.hypothesis) paragraph(card,experiment.hypothesis);
      card.append(el('strong','frontier-verdict',experiment.passed===true?'预注册义务通过':experiment.passed===false?'预注册义务未通过':'义务判定未提供'));
      paragraph(card,experimentNotes[experiment.id] || '按冻结协议与实际输出核对本项义务；完整对照和失败证据可展开查看。');
      raw(card,'对照、结果与失败记录',value);grid.append(card);
    }
    if (experiments.length) summary.append(grid);
    else paragraph(summary,'尚无冻结实验记录。','frontier-muted');
    const probe = section(labHost,'主动探针：优先寻找能区分假设的输入','ACTIVE / COUNTEREXAMPLE');
    paragraph(probe,'预测分歧用于安排实验；实际输出与独立判据决定哪些假设需要撤回。未知结果不当作反例，也不当作通过。');
    probeFlow(probe,data.active_probe);raw(probe,'探针次序、假设与实测反例',data.active_probe);
    const basis = section(labHost,'能力基：限定目标上的组合覆盖','BASIS / FINITE SCOPE');
    paragraph(basis,'此处只讨论冻结目标与登记算子；有限探针一致不能证明普遍等价，有限集合压缩不能证明通用最小能力基。');
    const base=obj(data.basis),baseStats=el('div','frontier-basis-stats');
    for(const [label,value] of [['登记算子',base.registry_size],['有限目标最小子集',base.minimum_size],['穷举子集',base.enumerated_subsets]]) {
      const cell=el('div');cell.append(el('b','',value),el('span','',label));baseStats.append(cell);
    }
    basis.append(baseStats);paragraph(basis,base.scope ?? '具体目标范围未提供。','frontier-muted');
    raw(basis,'核对能力基的目标、方法与实测覆盖',data.basis);
    const evidence = section(labHost,'协议、报告与结论边界','EVIDENCE / SHA-256');
    const list=el('dl','frontier-data');
    for (const [label,value] of [['报告版本',data.version],['协议 SHA-256',data.protocol_sha256],['完整冻结报告指纹',data.source_report_sha256],['当前投影指纹',data.report_sha256]])
      list.append(el('dt','',label),el('dd','frontier-hash',value));
    evidence.append(list);
    if(data.evidence_url==='/api/frontier/evidence') {
      const link=el('a','frontier-evidence-link','下载完整冻结报告 JSON ↗');
      link.href='/api/frontier/evidence';
      const feedback=el('p','frontier-muted');feedback.setAttribute('role','status');
      let downloading=false;
      link.addEventListener('click',event=>{
        event.preventDefault();if(downloading)return;downloading=true;link.setAttribute('aria-disabled','true');feedback.textContent='正在通过当前连接读取完整报告…';
        request('evidence','/api/frontier/evidence',null,report=>{
          downloading=false;link.removeAttribute('aria-disabled');
          const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
          const download=el('a');download.href=url;download.download='skillnet-frontier-evidence.json';download.click();
          setTimeout(()=>URL.revokeObjectURL(url),1000);feedback.textContent='完整报告已读取，已发起 JSON 下载。请与上方完整冻结报告指纹核对。';
        },error=>{downloading=false;link.removeAttribute('aria-disabled');feedback.textContent=error?.message || '完整报告读取失败；可点击再次读取。';});
      });
      evidence.append(link,feedback);
    } else if(data.evidence_url != null) paragraph(evidence,'完整报告地址未通过固定同源路径核对。','frontier-muted');
    paragraph(evidence,text(data.boundary),'frontier-boundary');
  }
  function loadLab() {
    labHost.replaceChildren(el('p','frontier-muted','正在读取冻结协议与真实实验记录…'));
    request('lab','/api/frontier/lab',null,data=>{
      try { renderLab(data); } catch(error) { errorView(labHost,error,loadLab); }
    },error=>errorView(labHost,error,loadLab));
  }
  function loadScenarios() {
    select=null;execute=null;
    scenarioHost.replaceChildren(el('p','frontier-muted','正在读取可实测的公开情景…'));
    request('scenarios','/api/frontier/scenarios',null,data=>{
      const items=arr(data?.scenarios).filter(s=>s && typeof s.id==='string' && typeof s.label==='string');
      scenarioHost.replaceChildren();
      if (!items.length) {errorView(scenarioHost,'当前没有可实测情景。',loadScenarios);return;}
      const label=el('label','frontier-label','选择公开模拟情景'); label.htmlFor='frontier-scenario';
      select=el('select');select.id='frontier-scenario';
      items.forEach(item=>{const option=el('option','',item.label);option.value=item.id;select.append(option);});
      const description=el('p','frontier-muted',items[0].description || '');
      select.addEventListener('change',()=>{description.textContent=items.find(s=>s.id===select.value)?.description || '';});
      execute=button('实测当前能力边界',runScenario,'frontier-button frontier-primary');
      const controls=el('div','frontier-controls'); controls.append(select,execute);
      scenarioHost.append(label,controls,description);
      if (data.boundary != null) paragraph(scenarioHost,text(data.boundary),'frontier-boundary');
    },error=>errorView(scenarioHost,error,loadScenarios));
  }
  function renderRun(data,scenarioId) {
    if (!data || typeof data !== 'object' || typeof data.version!=='string' || typeof data.status!=='string' || !Array.isArray(data.trace))
      throw new Error('实测响应不完整，不能据此判定能力已提升。');
    resultHost.replaceChildren();
    const heading=section(resultHost,status(data.status),'LIVE / INDEPENDENT OBSERVATION');
    paragraph(heading,'情景 '+scenarioId+' · '+data.version,'frontier-muted');
    paragraph(heading,'找到声明路径只代表计划可尝试；下方真实执行与独立判据才支持本次结果。');
    factList(heading,data.goal,'本次目标');
    const diagnosis=section(resultHost,'先辨别：缺能力，还是缺证据','DIAGNOSIS');
    const decision=obj(data.diagnosis);diagnosis.append(el('strong','frontier-verdict',status(decision.state)));
    const plans=el('div','frontier-state-pair');
    for(const [label,value] of [['当前检索候选的声明规划',decision.candidate],['完整试验登记集的声明规划',decision.registry]]) {
      const record=obj(value),card=el('div','frontier-facts');card.append(el('h5','',label));
      paragraph(card,status(record.status));paragraph(card,arr(record.plan).length?'声明路径：'+record.plan.join(' → '):'没有记录声明路径。','frontier-muted');plans.append(card);
    }
    diagnosis.append(plans);const gaps=arr(decision.gaps).filter(gap=>gap&&typeof gap==='object');
    if(gaps.length) {
      const list=el('ul','frontier-checks');
      gaps.slice(0,80).forEach(gap=>{const item=el('li');
        item.append(el('b','',gap.fact),el('span','',arr(gap.providers).length?' · 试验提供者：'+gap.providers.join(' / '):' · 试验登记集暂无提供者'));
        list.append(item);
      });diagnosis.append(list);
    }
    paragraph(diagnosis,'这些是本次输入与固定登记程序的有限诊断；没有提供者不等于整个技能库不会。','frontier-muted');
    raw(diagnosis,'搜索范围、缺失条件与判定依据',data.diagnosis);
    const initial=section(resultHost,'执行前的实际状态','INITIAL / OBSERVED');
    factList(initial,data.initial?.facts,'输入事实');checks(initial,data.initial?.checks,'原始输入核验');
    const trace=section(resultHost,'逐步执行与状态变化','STATE / TRANSITION');
    if (!data.trace.length) paragraph(trace,'本次没有执行算子；请核对诊断中的缺口、未知或阻断原因。','frontier-muted');
    data.trace.slice(0,80).forEach((step,index)=>{
      const card=el('article','frontier-step');card.append(el('small','frontier-kicker','STEP '+(index+1)+' / '+(step.kind==='targeted_execution_probe'?'定向执行探针':step.kind==='declared_plan'?'执行声明计划':text(step.kind))),el('h4','',operatorNames[step.operator_id]||step.operator_id));
      paragraph(card,operatorActions[step.operator_id] || '运行登记程序，并重新读取产物核验状态变化。');
      const measure=obj(step.execution?.execution_summary);
      if(measure.input_rows != null && measure.output_rows != null) paragraph(card,'实际数据：'+text(measure.input_rows)+' → '+text(measure.output_rows)+' 行','frontier-row-count');
      else if(measure.evaluation_rows != null) paragraph(card,'实际输入 '+text(measure.input_rows)+' 行 · 指标计算使用 '+text(measure.evaluation_rows)+' 行','frontier-row-count');
      else paragraph(card,'本步未提供可核对的行数统计。','frontier-muted');
      const beforeFacts=arr(step.before?.facts ?? step.before),afterFacts=arr(step.after?.facts ?? step.after),knownBefore=new Set(beforeFacts);
      const newFacts=afterFacts.filter(fact=>!knownBefore.has(fact));
      paragraph(card,newFacts.length?'本步新确认：'+newFacts.map(fact=>factNames[fact]||text(fact)).join(' / '):'本步未新增可确认事实。','frontier-new-facts');
      const states=el('div','frontier-state-pair');
      factList(states,step.before?.facts ?? step.before,'之前');factList(states,step.after?.facts ?? step.after,'之后');card.append(states);
      checks(card,step.before?.checks,'执行前条件');checks(card,step.after?.checks,'执行后条件');
      if(step.oracle == null)paragraph(card,'本步未提供独立结果判据；请继续核对最终 oracle，条件通过不证明算法正确。','frontier-muted');
      else checks(card,step.oracle?.checks,'本步独立结果判据');
      raw(card,'核对本步的执行、文件与 oracle',step);trace.append(card);
    });
    const final=section(resultHost,'执行后的观测与结果复核','FINAL / VERIFIED SCOPE');
    factList(final,data.final?.facts,'输出事实');checks(final,data.final?.checks,'最终条件');
    const oracleChecks=arr(data.oracle?.checks),oraclePassed=oracleChecks.filter(check=>check?.passed===true).length;
    const oracleVerdict=status(data.oracle?.state ?? (data.oracle?.passed===true?'passed':data.oracle?.passed===false?'failed':'unknown'));
    final.append(el('strong','frontier-verdict','独立 oracle：'+oracleVerdict+(oracleChecks.length?' · '+oraclePassed+'/'+oracleChecks.length+' 项':' · 没有提供逐项检查')));
    checks(final,data.oracle?.checks,'独立结果判据');
    paragraph(final,'实际代码调用 '+text(data.summary?.code_calls)+' 次 · 主动探针 '+text(data.summary?.active_probes)+' 次','frontier-muted');
    paragraph(final,text(data.boundary),'frontier-boundary');
    raw(final,'完整本次实测记录',data);
    live.textContent='实测返回：'+status(data.status)+'。结论仅限报告中的范围；正式排序与奖励未改变。';
  }
  function runScenario() {
    if (!select || !execute || execute.disabled) return;
    const scenarioId=select.value, runButton=execute, runSelect=select;
    runButton.disabled=true;runSelect.disabled=true;
    resultHost.replaceChildren(el('p','frontier-muted','正在运行登记的有限程序，并读取真实输出复核…'));
    live.textContent='本地实测进行中。不调用 LLM，不更新正式技能策略。';
    request('run','/api/frontier/execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario_id:scenarioId})},data=>{
      runButton.disabled=false;runSelect.disabled=false;
      try {renderRun(data,scenarioId);} catch(error) {errorView(resultHost,error);live.textContent='实测记录格式不完整，请重新实测。';}
      if(doc.activeElement===doc.body || !dialog.contains(doc.activeElement))runButton.focus();
    },error=>{
      runButton.disabled=false;runSelect.disabled=false;errorView(resultHost,error);
      live.textContent='未取得可核对的实测结果。可以检查连接后再次点击实测。';
      if(doc.activeElement===doc.body || !dialog.contains(doc.activeElement))runButton.focus();
    });
  }
  function focusables() {
    return Array.from(dialog.querySelectorAll('button,[href],select,input,textarea,summary,[tabindex]'))
      .filter(node=>!node.disabled && node.tabIndex!==-1 && !node.hidden && !node.closest('[hidden]') && node.getClientRects().length>0);
  }
  function restore() {
    const node=returnFocus;returnFocus=null;
    if (node?.isConnected && !node.disabled) node.focus();
  }
  function close() {
    stopRequests();
    if (dialog?.open) dialog.close();
    restore();
  }
  function ensureDialog() {
    if (dialog) return;
    dialog=el('dialog','frontier-dialog');dialog.id='frontier-dialog';
    dialog.setAttribute('aria-labelledby','frontier-title');dialog.setAttribute('aria-describedby','frontier-description');
    const header=el('header','frontier-header'), title=el('div');title.append(el('small','frontier-kicker','CAPABILITY SCIENCE / EXPERIMENT'));
    const h=el('h2','','能力边界实验');h.id='frontier-title';title.append(h);
    const closer=button('关闭',close,'frontier-button frontier-close');header.append(title,closer);
    const body=el('div','frontier-body'), intro=el('p','frontier-lead','从“没找到技能”继续追问：当前组合是否可达，缺什么证据，哪个实验能推翻假设。');intro.id='frontier-description';body.append(intro);
    const runtime=section(body,'选择一个情景，观察真实能力变化','TRY / EXECUTE / VERIFY');
    paragraph(runtime,'固定程序运行公开模拟数据；不调用大模型，不修改正式技能库，也不自动给予提升奖励。');
    scenarioHost=el('div');resultHost=el('div','frontier-result');live=el('p','frontier-live','请选择情景开始实测。');live.setAttribute('role','status');live.setAttribute('aria-live','polite');
    runtime.append(scenarioHost,live,resultHost);
    const lab=section(body,'研究证据：方法是否真的有效','FROZEN / REPRODUCIBLE');
    labHost=el('div');lab.append(labHost);
    const footer=el('footer','frontier-footer','有限任务、有限模型、真实产物。关闭停止等待，已开始的服务端实测可能继续；结果不能外推为全库能力证明。');
    dialog.append(header,body,footer);doc.body.append(dialog);
    dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
    dialog.addEventListener('close',()=>{stopRequests();restore();});
    dialog.addEventListener('keydown',event=>{
      if (event.key==='Escape') {event.preventDefault();close();return;}
      if (event.key!=='Tab') return;
      const nodes=focusables(),first=nodes[0],last=nodes[nodes.length-1];
      if (!first) {event.preventDefault();dialog.focus();return;}
      if (event.shiftKey && (doc.activeElement===first || !dialog.contains(doc.activeElement))) {event.preventDefault();last.focus();}
      else if (!event.shiftKey && (doc.activeElement===last || !dialog.contains(doc.activeElement))) {event.preventDefault();first.focus();}
    });
    dialog._frontierClose=closer;
  }
  function open(opener) {
    ensureDialog();if (dialog.open) return;
    stopRequests();returnFocus=opener?.currentTarget?.focus ? opener.currentTarget : opener?.focus ? opener : doc.activeElement;
    live.textContent='请选择情景开始实测。';resultHost.replaceChildren();
    try {dialog.showModal();} catch (_) {root.UI?.toast?.('当前浏览器不能打开实验对话框，请使用新版浏览器。');restore();return;}
    dialog._frontierClose.focus();loadLab();loadScenarios();
  }
  function boot() {
    if (doc.getElementById('frontier-launch')) return;
    const host=doc.querySelector('.product-shell .ui-product-nav') || doc.querySelector('.topbar .wrap') || doc.querySelector('nav') || doc.querySelector('main') || doc.body;
    trigger=button('能力边界实验',open,'frontier-launch');trigger.id='frontier-launch';
    trigger.setAttribute('aria-haspopup','dialog');trigger.setAttribute('aria-controls','frontier-dialog');host.append(trigger);
    doc.addEventListener('click',event=>{const opener=event.target.closest?.('[data-frontier-open]');if(opener)open(opener);});
    root.addEventListener('pagehide',()=>{returnFocus=null;stopRequests();if(dialog?.open)dialog.close();});
  }
  if (doc.readyState==='loading') doc.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})(typeof window==='undefined'?null:window);
