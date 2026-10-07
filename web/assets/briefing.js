/* Real API data only. Preview never invokes Fabric/LLM; execution is explicit. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g,
    c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const samples = {
    data: '检查实验数据的缺失值与异常值，完成探索性分析，输出可复现的统计图表和数据质量报告。',
    literature: '围绕单细胞 RNA 测序的肿瘤微环境研究，设计文献检索与筛选流程，比较研究方法并梳理证据缺口。',
    materials: '使用化学成分特征预测无机材料的形成能，规划数据清洗、特征工程、交叉验证和模型解释流程。'
  };
  const statuses = {CREATED:'已创建',RETRIEVING:'检索技能',ORCHESTRATING:'编排任务',
    EXECUTING:'执行中',VERIFYING:'验收中',EVOLVING:'沉淀经验',COMPLETED:'已完成',
    PARTIAL:'部分完成',FAILED:'执行失败',CANCELLED:'已取消',INTERRUPTED:'运行中断',
    BUDGET_EXCEEDED:'达到预算上限'};
  const terminal = new Set(['COMPLETED','PARTIAL','FAILED','CANCELLED','INTERRUPTED','BUDGET_EXCEEDED']);
  let mode = 'preview', busy = false, health = null, activeRun = null, pollTimer = null;
  let skillRequest = 0, previousFocus = null;
  function storeRun(id) {
    try { if (id) sessionStorage.setItem('skillnet_overview_run', id); else sessionStorage.removeItem('skillnet_overview_run'); }
    catch (_) { /* Storage can be disabled; the current page still works. */ }
  }
  async function api(path, options) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(path, Object.assign({}, options, {signal:controller.signal}));
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : '接口返回 HTTP ' + response.status;
        if (response.status === 401) throw new Error('此操作需要访问令牌，请通过顶部的连接设置配置。');
        if (response.status === 429) throw new Error('服务正在处理其他任务，请稍后重试。');
        throw new Error(detail);
      }
      return data;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('服务响应超时。任务可能仍在后台执行，可到运行记录确认。');
      if (error instanceof TypeError) throw new Error('暂时无法连接服务，请确认服务已启动后重试。');
      throw error;
    } finally { clearTimeout(timeout); }
  }
  const post = (path, body) => api(path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const duration = ms => Number.isFinite(Number(ms)) && Number(ms) > 0 ? (Number(ms)/1000).toFixed(1)+'s' : '—';
  const money = n => '¥' + Number(n || 0).toFixed(3);
  function setMode(next, focus) {
    mode = next;
    ['preview','execute'].forEach(key => {
      const button = $('mode-' + key);
      button.classList.toggle('active', key === next);
      button.setAttribute('aria-selected', String(key === next));
      button.tabIndex = key === next ? 0 : -1;
    });
    $('task-panel').setAttribute('aria-labelledby', 'mode-' + next);
    $('execution-notice').hidden = next !== 'execute';
    $('mode-hint').textContent = next === 'preview' ? '混合检索 · 无模型费用' :
      health && !health.api_key_configured ? '模型未配置 · 可先使用能力预检' : '真实模型 · 步骤与成本可追溯';
    updateSubmit();
    if (focus) $('mode-' + next).focus();
  }
  function updateSubmit() {
    $('task-submit').disabled = busy;
    $('task-submit').innerHTML = busy ? '处理中…' : mode === 'preview' ?
      '匹配技能 <span aria-hidden="true">→</span>' : '启动执行 <span aria-hidden="true">↗</span>';
  }
  function updateHealth(data) {
    health = data;
    $('service-status').className = 'system-status online';
    $('service-status').innerHTML = '<i></i>服务在线';
    setMode(mode, false);
  }
  function renderNetwork(graph) {
    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    const edges = Array.isArray(graph.edges) ? graph.edges : [];
    if (!nodes.length) { $('network-map').innerHTML = '<div class="map-loading">技能库暂无数据</div>'; return; }
    const counts = {};
    nodes.forEach(n => { counts[n.domain] = (counts[n.domain] || 0) + 1; });
    const top = Object.keys(counts).sort((a,b) => counts[b]-counts[a] || a.localeCompare(b)).slice(0,5);
    const groups = top.concat(Object.keys(counts).filter(domain => !top.includes(domain)).sort());
    const positions = {}, members = groups.map(() => []);
    nodes.forEach(n => members[groups.indexOf(n.domain)].push(n));
    let marks = '', labels = '';
    groups.forEach((group, index) => {
      const outer = index < top.length;
      const angle = outer ? -Math.PI/2 + index*2*Math.PI/top.length : (index-top.length)*2.399963;
      // Keep every actual domain separate: rare domains occupy the interior
      // rather than collapsing most of the library into one artificial cluster.
      const radius = outer ? 132 : 13*Math.sqrt(index-top.length+1);
      const cx = 260 + radius*Math.cos(angle), cy = 163 + radius*Math.sin(angle)*.72;
      members[index].sort((a,b) => a.id.localeCompare(b.id)).forEach((node,j) => {
        const a = j*2.399963, r = 6*Math.sqrt(j+1);
        const x = cx+r*Math.cos(a), y = cy+r*Math.sin(a)*.75;
        positions[node.id] = {x,y};
        const evolved = node.source !== 'seed';
        marks += '<g class="map-node" role="button" tabindex="' + (j === 0 ? '0' : '-1') +
          '" aria-label="' + esc(node.id+'，'+node.domain+'，查看技能契约') + '" data-skill="' + esc(node.id) + '">' +
          '<title>' + esc(node.id+' · '+node.domain) + '</title><circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) +
          '" r="10" fill="transparent"/><circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) +
          '" r="' + (evolved ? '3.5' : '3') + '" fill="' + (evolved ? '#c1985d' : '#7d9f8a') + '" stroke="#fff" stroke-width="1.2"/></g>';
      });
      if (outer) {
        const labelX = 260+181*Math.cos(angle), labelY = 164+132*Math.sin(angle);
        labels += '<text x="' + labelX.toFixed(1) + '" y="' + labelY.toFixed(1) +
          '" fill="#81968a" font-size="8.5" text-anchor="middle">' + esc(group.length > 10 ? group.slice(0,9)+'…' : group) + '</text>';
      }
    });
    let lines = '';
    edges.forEach(edge => {
      const a = positions[edge.source], b = positions[edge.target];
      if (!a || !b) return;
      lines += '<line x1="' + a.x.toFixed(1) + '" y1="' + a.y.toFixed(1) + '" x2="' + b.x.toFixed(1) + '" y2="' + b.y.toFixed(1) +
        '" stroke="' + (edge.type === 'depend_on' ? '#608f73' : '#a8c0ae') + '" stroke-width=".7" opacity=".25"/>';
    });
    $('network-map').innerHTML = '<svg viewBox="0 0 520 328" role="group" aria-label="实时技能节点与类型化关系">' +
      '<ellipse cx="260" cy="163" rx="166" ry="118" fill="none" stroke="#edf2ed" stroke-dasharray="2 5"/>' +
      '<ellipse cx="260" cy="163" rx="102" ry="73" fill="none" stroke="#f1f5f0"/>' + lines + marks + labels + '</svg>';
    const values = {skills:nodes.length,domains:Object.keys(counts).length,edges:edges.length,evolved:nodes.filter(n => n.source !== 'seed').length};
    document.querySelectorAll('[data-live]').forEach(el => { const value = values[el.dataset.live]; if (value !== undefined) el.textContent = value; });
    $('domain-list').innerHTML = Object.keys(counts).sort((a,b) => counts[b]-counts[a] || a.localeCompare(b)).slice(0,6).map(domain =>
      '<div class="domain-item"><span><i></i>'+esc(domain)+'</span><b>'+counts[domain]+' 项</b></div>').join('');
  }
  function renderBenchmark(results) {
    const experiment = results.exp1_retrieval_heldout;
    if (!experiment || !experiment.summary) {
      $('benchmark-subtitle').textContent = '暂无冻结评估集记录';
      $('benchmark-chart').innerHTML = '<p class="loading-text">完成实验后，这里会展示原始结果。</p>';
      return;
    }
    $('benchmark-subtitle').textContent = 'Held-out · ' + experiment.n_tasks + ' 个任务 · K=' + experiment.k;
    $('benchmark-chart').innerHTML = ['bm25','hybrid','fabric'].map(mode => {
      const value = Number(experiment.summary[mode] && experiment.summary[mode].skill_recall);
      if (!Number.isFinite(value)) return '';
      const percent = Math.max(0,Math.min(100,value*100));
      return '<div class="benchmark-row '+(mode === 'fabric'?'highlight':'')+'"><span>'+({bm25:'BM25',hybrid:'Hybrid',fabric:'Fabric'}[mode])+
        '</span><div class="benchmark-track" role="meter" aria-label="'+esc(mode+' 技能召回率')+'" aria-valuenow="'+percent.toFixed(1)+
        '" aria-valuemin="0" aria-valuemax="100"><i style="width:'+percent.toFixed(1)+'%"></i></div><b>'+percent.toFixed(1)+'%</b></div>';
    }).join('');
  }
  async function refreshRuns() {
    $('refresh-runs').disabled = true;
    try {
      const data = await api('/api/runs?limit=4');
      const runs = data.runs || [];
      if (!runs.length) { $('recent-runs').innerHTML = '<p class="loading-text">还没有执行记录。完成第一个任务后，可在这里回放。</p>'; return; }
      $('recent-runs').innerHTML = '<div class="run-row header"><span>状态</span><span>任务</span><span style="text-align:right">时长</span><span style="text-align:right">成本</span><span style="text-align:right">产物</span></div>' +
        runs.map(run => '<a class="run-row" href="/run?id='+encodeURIComponent(run.run_id)+'"><span class="run-status '+
          (['FAILED','INTERRUPTED','BUDGET_EXCEEDED'].includes(run.status)?'failed':terminal.has(run.status)?'':'running')+'">'+esc(statuses[run.status]||run.status)+
          '</span><span class="run-task" title="'+esc(run.task)+'">'+esc(run.task)+'</span><span class="run-number">'+duration(run.duration_ms)+
          '</span><span class="run-number">'+money(run.cost_yuan)+'</span><span class="run-number">'+Number(run.artifacts||0)+'</span></a>').join('');
    } catch (error) { $('recent-runs').innerHTML = '<p class="inline-error">'+esc(error.message)+'</p>'; }
    finally { $('refresh-runs').disabled = false; }
  }
  async function showSkill(name) {
    const requestId = ++skillRequest;
    const dialog = $('skill-dialog');
    previousFocus = document.activeElement;
    $('skill-dialog-content').innerHTML = '<p class="loading-text">正在读取技能契约…</p>';
    if (!dialog.open) dialog.showModal();
    try {
      const data = await api('/api/skill/'+encodeURIComponent(name));
      if (requestId !== skillRequest || !dialog.open) return;
      const s = data.skill || {};
      const section = (title,items) => Array.isArray(items) && items.length ?
        '<h3>'+title+'</h3><ul>'+items.map(item => '<li>'+esc(item)+'</li>').join('')+'</ul>' : '';
      $('skill-dialog-content').innerHTML = '<h2>'+esc(s.name)+'</h2><span class="small-tag">'+esc(s.domain)+'</span><p>'+esc(s.capability||s.description)+'</p>' +
        section('输入',s.inputs)+section('输出',s.outputs)+section('执行步骤',s.steps)+section('验收清单',s.verification)+
        '<a href="/api/skill/'+encodeURIComponent(name)+'/raw" target="_blank" rel="noopener">查看完整 SKILL.md ↗</a>';
    } catch (error) { if (requestId === skillRequest) $('skill-dialog-content').innerHTML = '<p class="inline-error">'+esc(error.message)+'</p>'; }
  }
  function renderMatches(data) {
    const result = data.by_mode && data.by_mode.hybrid;
    if (!result) throw new Error('检索返回缺少混合检索结果。');
    const selected = new Set(result.selected || []);
    const skills = (result.detail||[]).filter(s => selected.has(s.name));
    const decision = {auto:'匹配明确',confirm:'建议确认',abstain:'匹配不足'};
    $('task-result').innerHTML = '<div class="result-top"><h3>'+skills.length+' 项技能候选</h3><span class="small-tag">'+esc(decision[result.decision]||'候选预览')+
      '</span></div><p class="result-note">'+esc(result.decision_reason || '预检结果用于选择技能；执行前请确认目标与所需数据。')+'</p>' +
      (skills.length ? skills.map(s => '<button type="button" class="result-skill" data-skill="'+esc(s.name)+'"><span class="result-skill-top"><code>'+esc(s.name)+
        '</code><span>↗</span></span><p>'+esc(s.capability)+'</p><span class="micro-label">'+esc(s.domain)+'</span></button>').join('') :
        '<p class="loading-text">没有找到合适的技能。可以补充领域、输入数据和预期产物后再试。</p>') +
      '<div class="result-trace">混合检索 / BM25 + 语义 + 结构信号<br>本次预检无模型调用 · '+esc((result.trace||[]).slice(-1).join(''))+'</div>';
  }
  function renderRun(run) {
    const done = terminal.has(run.status), steps = run.steps || [];
    const completed = steps.filter(s => s.status === 'done').length;
    const percent = done ? 100 : steps.length ? Math.round(completed/steps.length*100) : 5;
    $('task-result').innerHTML = '<div class="result-top"><h3>'+esc(statuses[run.status]||run.status)+'</h3><span class="small-tag">真实执行</span></div>'+
      '<p class="result-note">'+esc(run.task)+'</p><div class="run-progress" role="progressbar" aria-label="任务进度" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+percent+
      '"><span style="width:'+percent+'%"></span></div>' +
      steps.map(s => '<div class="run-step '+esc(s.status)+'"><i></i><span>'+esc(s.action||s.skill||'步骤 '+(s.idx+1))+'</span></div>').join('') +
      (run.error ? '<p class="inline-error">'+esc(run.error)+'</p>' : '') +
      '<div class="live-run-info"><span>'+completed+' / '+steps.length+' 步完成</span><span>'+money(run.cost_yuan)+'</span><span>'+duration(run.duration_ms)+'</span></div>'+
      '<div class="live-run-actions"><a class="action-primary" href="/run?id='+encodeURIComponent(run.run_id)+'">'+(done?'查看结果与产物':'打开实时运行')+' ↗</a>'+
      (done ? '' : '<button type="button" id="cancel-overview-run" class="text-button">取消任务</button>')+'</div>'+
      '<p class="run-meta">Run '+esc(run.run_id)+'</p>';
    const cancel = $('cancel-overview-run');
    if (cancel) cancel.addEventListener('click', async () => {
      cancel.disabled = true; cancel.textContent = '正在取消…';
      try { await post('/api/runs/'+encodeURIComponent(run.run_id)+'/cancel',{}); cancel.textContent = '已请求取消'; }
      catch (error) { cancel.disabled = false; cancel.textContent = '重试取消'; $('task-result').insertAdjacentHTML('beforeend','<p class="inline-error">'+esc(error.message)+'</p>'); }
    });
  }
  async function pollRun(id, failures) {
    clearTimeout(pollTimer);
    if (activeRun !== id) return;
    try {
      const run = await api('/api/runs/'+encodeURIComponent(id));
      if (activeRun !== id) return;
      renderRun(run);
      if (terminal.has(run.status)) {
        activeRun = null; busy = false; storeRun(null); updateSubmit();
        refreshRuns();
        api('/api/graph').then(renderNetwork).catch(() => {});
        return;
      }
      pollTimer = setTimeout(() => pollRun(id,0),document.hidden?6000:2000);
    } catch (error) {
      if (activeRun !== id) return;
      if (failures < 3) { pollTimer = setTimeout(() => pollRun(id,failures+1),4000); return; }
      $('task-result').innerHTML = '<h3>连接暂时中断</h3><p class="inline-error">'+esc(error.message)+'</p><p class="result-note">后台任务可能仍在运行，恢复连接后可以继续查看。</p>'+
        '<button id="resume-overview-run" class="retry-button" type="button">恢复连接</button> <a class="text-link" href="/run?id='+encodeURIComponent(id)+'">打开运行详情 ↗</a>';
      $('resume-overview-run').addEventListener('click',() => pollRun(id,0));
    }
  }
  async function submit(event) {
    event.preventDefault();
    const task = $('task-input').value.trim();
    if (!task || busy) return;
    if (mode === 'execute' && health && !health.api_key_configured) {
      $('task-result').innerHTML = '<h3>先配置模型连接</h3><p class="result-note">在服务的环境配置中填写模型 API 密钥并重启，即可真实执行。现在也可以切回能力预检体验技能匹配。</p>';
      return;
    }
    busy = true; updateSubmit(); $('task-result').setAttribute('aria-busy','true');
    $('task-result').innerHTML = '<div class="result-placeholder"><div class="loading-indicator"></div><h3>'+(mode === 'preview'?'正在匹配技能':'正在创建运行')+'</h3><p>正在连接真实服务…</p></div>';
    try {
      if (mode === 'preview') {
        renderMatches(await post('/api/search',{query:task,k:4,modes:['bm25','hybrid']}));
      } else {
        const run = await post('/api/runs',{task:task,k:5,max_steps:3,max_cost_yuan:.5,max_seconds:180,max_llm_calls:30});
        if (!run.run_id) throw new Error('服务未返回运行编号，请到运行记录检查任务状态。');
        activeRun = run.run_id; storeRun(activeRun); await pollRun(activeRun,0);
      }
    } catch (error) {
      $('task-result').innerHTML = '<h3>暂时未能完成请求</h3><p class="inline-error">'+esc(error.message)+'</p><a class="text-link" href="/runs">检查运行记录 ↗</a>';
    } finally { busy = !!activeRun; updateSubmit(); $('task-result').setAttribute('aria-busy','false'); }
  }
  function bind() {
    $('task-form').addEventListener('submit',submit);
    $('task-input').addEventListener('input',() => { $('char-count').textContent = $('task-input').value.length+' / 4000'; });
    ['preview','execute'].forEach(key => {
      $('mode-'+key).addEventListener('click',() => setMode(key,false));
      $('mode-'+key).addEventListener('keydown',event => {
        if (['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) {
          event.preventDefault(); setMode(event.key==='Home'?'preview':event.key==='End'?'execute':mode==='preview'?'execute':'preview',true);
        }
      });
    });
    document.querySelectorAll('[data-sample]').forEach(button => button.addEventListener('click',() => {
      $('task-input').value = samples[button.dataset.sample]; $('task-input').dispatchEvent(new Event('input')); $('task-input').focus();
    }));
    document.addEventListener('click',event => { const el = event.target.closest('[data-skill]'); if (el) showSkill(el.dataset.skill); });
    $('network-map').addEventListener('keydown',event => {
      const el = event.target.closest('[data-skill]');
      if (el && (event.key==='Enter'||event.key===' ')) { event.preventDefault(); showSkill(el.dataset.skill); }
    });
    $('close-skill').addEventListener('click',() => $('skill-dialog').close());
    $('skill-dialog').addEventListener('close',() => { ++skillRequest; if (previousFocus) previousFocus.focus(); });
    $('refresh-runs').addEventListener('click',refreshRuns);
    window.addEventListener('skillnet:connection-changed', () => {
      refreshRuns();
      api('/api/health').then(updateHealth).catch(() => {});
      if (activeRun) pollRun(activeRun,0);
    });
    window.addEventListener('pagehide',() => clearTimeout(pollTimer));
  }
  async function boot() {
    bind();
    // Panels load independently: one unavailable endpoint does not blank the page.
    await Promise.allSettled([
      api('/api/health').then(updateHealth).catch(() => {
        $('service-status').className='system-status offline'; $('service-status').innerHTML='<i></i>服务离线';
      }),
      api('/api/graph').then(renderNetwork).catch(error => {
        $('network-map').innerHTML='<div class="map-loading">'+esc(error.message)+'</div>';
        $('domain-list').innerHTML='<p class="inline-error">'+esc(error.message)+'</p>';
      }),
      api('/api/results').then(renderBenchmark).catch(error => {
        $('benchmark-subtitle').textContent='实验记录暂时不可用'; $('benchmark-chart').innerHTML='<p class="inline-error">'+esc(error.message)+'</p>';
      }),
      refreshRuns()
    ]);
    let saved;
    try { saved=sessionStorage.getItem('skillnet_overview_run'); } catch (_) {}
    if (saved && /^[a-zA-Z0-9_-]{1,100}$/.test(saved) && !busy) {
      activeRun=saved; busy=true; setMode('execute',false); pollRun(saved,0);
    }
  }
  boot();
})();
