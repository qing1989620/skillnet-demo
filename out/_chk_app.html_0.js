
/* Mission Control —— 先让用户做事，再让系统证明自己。
   数据全部来自真实 API；不伪造任何状态；术语严格区分
   VERIFIED（确定性校验）/ SEMANTIC REVIEW（模型复核）/ 不声称 RESULT CORRECT。 */
const API = location.port ? location.origin : "http://127.0.0.1:8848";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmtMs = ms => ms == null ? "—" : (ms >= 1000 ? (ms/1000).toFixed(1)+"s" : Math.round(ms)+"ms");
const fmtTime = ms => ms ? new Date(ms).toLocaleString("zh-CN", {hour12:false}) : "—";
const VIEWS = ["runs","skills","eval","system"];
const NAMES = {runs:"运行记录", skills:"技能库", eval:"评估与实验", system:"系统状态"};

/* ---------- 路由 ---------- */
function route(){
  const v = (location.hash.replace("#/","") || "mission");
  const cur = VIEWS.includes(v) ? v : "runs";
  VIEWS.forEach(x => $(`v-${x}`).classList.toggle("on", x === cur));
  $("nav").innerHTML = VIEWS.map(x =>
    `<a href="#/${x}" class="${x===cur?"on":""}">${NAMES[x]}</a>`).join("");
  if (cur === "runs") loadRuns();
  if (cur === "skills") loadSkills();
  if (cur === "eval") loadEval();
  if (cur === "system") loadSystem();
  if (cur === "mission") loadLatest();
}
window.addEventListener("hashchange", route);

/* ---------- 系统状态 ---------- */
let HEALTH = null;
async function loadHealth(){
  try {
    HEALTH = await (await fetch(API + "/api/health")).json();
    $("sys").innerHTML =
      `<span><span class="dot ${HEALTH.ok?"on":"off"}"></span>${HEALTH.ok?"online":"down"}</span>`
      + `<span>model ${esc(HEALTH.model||"—")}</span>`
      + `<span>${HEALTH.api_key_configured?"":"<span style='color:var(--warn)'>no key</span>"}</span>`
      + `<span>skills ${HEALTH.skills}</span>`
      + `<span>evolved ${HEALTH.evolved}</span>`;
  } catch { $("sys").innerHTML = '<span><span class="dot off"></span>offline</span>'; }
}

/* ---------- 示例任务 ---------- */
const EXAMPLES = [
  "分析一批不同剂量下的细胞存活率数据，做清洗、剂量-反应建模与可视化",
  "对两组实验数据做统计检验，报告效应量与置信区间",
  "分析一份含缺失值的表格数据，建立基线预测模型并做误差分析",
  "评估某化合物的成药性风险，给出筛选建议与依据",
];
const exEl = $("ex");
if (exEl) {                                      // 该容器仅在产品首页存在；运行中心页跳过
  exEl.innerHTML = EXAMPLES.map(t => `<span class="ex">${esc(t.slice(0,26))}…</span>`).join("");
  document.querySelectorAll(".ex").forEach((el, i) => el.onclick = () => { const ta = $("task"); if (ta) ta.value = EXAMPLES[i]; });
}

/* ---------- 启动 Run ---------- */
async function startRun(){
  const ta = $("task");
  const task = ta ? ta.value.trim() : "";
  if (!task){ if (ta) ta.focus(); return; }
  const btn = $("run"); if (btn) { btn.disabled = true; }
  const old = btn ? btn.textContent : "";
  if (btn) btn.textContent = "Creating run…";
  try {
    const r = await fetch(API + "/api/runs", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({task, max_steps:+($("maxsteps")?.value)||2,
                            max_cost_yuan:+($("maxcost")?.value)||0.8,
                            max_seconds:+($("maxsec")?.value)||240})
    });
    if (!r.ok){ const d = await r.json().catch(()=>({})); throw new Error(d.detail || r.status); }
    const d = await r.json();
    localStorage.setItem("last_run", d.run_id);
    location.href = `/run?id=${encodeURIComponent(d.run_id)}`;   // 立即跳 Live Run
  } catch (e) {
    alert("创建 Run 失败：" + (e.message || e));
    if (btn) { btn.disabled = false; btn.textContent = old; }
  }
}

/* ---------- Latest Run（首屏关键：让用户看到系统在做事） ---------- */
async function loadLatest(){
  let runs = [];
  try { runs = (await (await fetch(API + "/api/runs?limit=1")).json()).runs || []; } catch {}
  const card = $("latest");
  if (!runs.length){ card.style.display = "none"; return; }
  const r = runs[0];
  let full = null;
  try { full = await (await fetch(API + `/api/runs/${encodeURIComponent(r.run_id)}`)).json(); } catch {}
  card.style.display = "block";
  $("latest-title").innerHTML = `Latest run <span class="badge st-${r.status}" style="margin-left:8px">${r.status}</span>`
    + (r.status === "INTERRUPTED" ? '<span style="font-size:11.5px;color:var(--warn);margin-left:10px">服务重启导致中断，请重新运行</span>' : "");
  $("latest-meta").innerHTML = `<a href="/run?id=${encodeURIComponent(r.run_id)}">打开 Live Run →</a>`;
  const steps = (full && full.steps) || [];
  const done = (full?.step_stats?.done) || 0, total = (full?.step_stats?.total) || 0;
  const pct = total ? Math.round(done/total*100) : 0;
  $("latest-body").innerHTML = `
    <div style="font-size:13px;margin-bottom:6px">${esc(r.task)}</div>
    <div style="font:11.5px var(--mono);color:var(--ink3)">
      ${esc(r.run_id)} · ${fmtTime(r.started_at_ms)} · 时长 ${fmtMs(r.duration_ms)} ·
      成本 ¥${Number(r.cost_yuan||0).toFixed(4)} · 步骤 ${done}/${total} · 产物 ${r.artifacts||0}
    </div>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <div class="steps">${steps.map(s => `
      <div class="srow s-${s.status==="done"?"done":s.status}">
        <span class="sdot"></span>
        <span class="nm">S${s.idx+1} ${esc(s.action||"")}</span>
        <span>${esc(s.skill||"—")}</span>
        <span>${fmtMs(s.duration_ms)}${s.n_attempts>1?` ·×${s.n_attempts}`:""}</span>
      </div>`).join("") || '<div class="empty">步骤信息加载中…</div>'}</div>`;
}

/* ---------- Runs 列表 ---------- */
async function loadRuns(){
  let runs = [];
  try { runs = (await (await fetch(API + "/api/runs?limit=60")).json()).runs || []; } catch {}
  $("runs-meta").textContent = `${runs.length} runs · 同一任务共享 task fingerprint 但 run_id 不覆盖`;
  if (!runs.length){ $("runs-body").innerHTML = '<div class="empty">还没有 Run。到 Mission Control 启动一个。</div>'; return; }
  $("runs-body").innerHTML = `<table>
    <tr><th>Status</th><th>Task</th><th>Started</th><th>Duration</th><th>Steps</th><th>Artifacts</th><th>Cost</th><th>Fingerprint</th></tr>
    ${runs.map(r => `<tr onclick="location.href='/run?id=${encodeURIComponent(r.run_id)}'" style="cursor:pointer">
      <td><span class="badge st-${r.status}">${r.status}</span></td>
      <td style="color:var(--ink)">${esc((r.task||"").slice(0,60))}</td>
      <td>${fmtTime(r.started_at_ms)}</td>
      <td>${fmtMs(r.duration_ms)}</td>
      <td>${r.steps_done||0}/${r.steps||0}${r.steps_failed?` · <span style="color:var(--bad)">${r.steps_failed} failed</span>`:""}</td>
      <td>${r.artifacts||0}</td>
      <td>¥${Number(r.cost_yuan||0).toFixed(4)}</td>
      <td>${esc(r.task_fp||"")}</td>
    </tr>`).join("")}</table>`;
}

/* ---------- Skills ---------- */
let SKILLS = [];
async function loadSkills(){
  if (!SKILLS.length){
    try { SKILLS = (await (await fetch(API + "/api/skills")).json()).skills || []; } catch {}
  }
  const q = ($("q").value || "").toLowerCase();
  const rows = SKILLS.filter(s => !q || (s.name+s.domain+(s.capability||"")).toLowerCase().includes(q));
  $("skills-meta").textContent = `${rows.length} / ${SKILLS.length} skills · 来源 seed/evolved · 执行统计来自真实运行`;
  $("skills-body").innerHTML = rows.length ? `<table>
    <tr><th>Skill</th><th>Domain</th><th>Source</th><th>Exec</th><th>Reward</th><th>Quality</th></tr>
    ${rows.slice(0, 400).map(s => {
      const st = s.stats || {};
      const tot = st.exec_total || 0, ok = st.exec_ok || 0;
      return `<tr><td style="color:var(--ink)">${esc(s.name)}</td><td>${esc(s.domain)}</td>
        <td>${s.source === "seed" ? "seed" : `<span style="color:var(--warn)">evolved G${s.generation||1}</span>`}</td>
        <td>${tot ? `${ok}/${tot}${st.exec_fix?` · fix ${st.exec_fix}`:""}${st.exec_fail?` · <span style="color:var(--bad)">fail ${st.exec_fail}</span>`:""}` : "—"}</td>
        <td>${(s.stats?.mean_reward ?? 0).toFixed ? (s.stats.mean_reward||0).toFixed(3) : "—"}</td>
        <td style="color:var(--ink3)">${esc(Object.entries(s.quality||{}).map(([k,v])=>`${k.slice(0,4)}:${v}`).join(" "))}</td></tr>`;
    }).join("")}</table>` : '<div class="empty">无匹配技能</div>';
}
$("q").addEventListener("input", loadSkills);

/* ---------- Evaluations ---------- */
async function loadEval(){
  let d = null;
  try { d = await (await fetch(API + "/api/results")).json(); } catch {}
  const ho = d && (d.splits?.heldout || null);
  const dev = d && (d.splits?.dev || null);
  const block = (name, label, s) => {
    if (!s) return `<div class="empty">${label}：暂无数据</div>`;
    const e1 = s.exp1, e2 = s.exp2, e3 = s.exp3;
    return `<div style="margin-bottom:16px">
      <div style="font:600 12.5px inherit;margin-bottom:6px">${label}</div>
      <table>
        <tr><th>实验</th><th>指标</th><th>数值</th></tr>
        ${e1?`<tr><td>检索与编排</td><td>召回 / 编排完整度</td><td>${(e1.rows||[]).map(r=>`${r.mode}: ${r.recall}% / ${r.orchestration}%`).join(" · ")}</td></tr>`:""}
        ${e2?`<tr><td>执行质量</td><td>盲评均分</td><td>${(e2.rows||[]).map(r=>`${r.arm}: ${r.score}`).join(" · ")}</td></tr>`:""}
        ${e3?`<tr><td>选择策略</td><td>mean_reward</td><td>${Object.entries(e3.arms||{}).map(([k,v])=>`${k}: ${v.mean_reward}±${v.std??"—"}`).join(" · ")}</td></tr>
             <tr><td>统计结论</td><td>配对 bootstrap</td><td>${esc((e3.statistics||{}).verdict || "—")}</td></tr>`:""}
      </table></div>`;
  };
  $("eval-body").innerHTML =
    `<div class="empty" style="padding-bottom:10px">当前技能库规模已变（90+ 技能 / 162+ 边），实验数据为更早条件（51 技能 / 62 边）的产物 —— <b>尚未重跑</b>，文档已显式标注，不以此声称当前性能。</div>`
    + block("heldout", "HELD-OUT（冻结测试集 · 最终结论只引这里）", ho)
    + block("dev", "DEV（调参集）", dev)
    + `<div style="margin-top:14px;font-size:12px"><a href="/static/briefing.html" target="_blank">查看完整六幕复盘页（历史材料）</a> · <a href="/dashboard" target="_blank">完整面板</a> · <a href="/graph" target="_blank">技能拓扑</a></div>`;
}

/* ---------- System ---------- */
async function loadSystem(){
  let cfg = null, stats = null;
  try { cfg = await (await fetch(API + "/api/config")).json(); } catch {}
  try { stats = await (await fetch(API + "/api/stats")).json(); } catch {}
  $("sys-meta").textContent = HEALTH ? `ui ${HEALTH.ui_version||"—"} · skills ${HEALTH.skills}` : "";
  $("sys-body").innerHTML = `
    <div class="grid2">
      <div><div style="font:600 12px inherit;margin-bottom:8px">Runtime</div>
        <table>
          <tr><td>模型</td><td>${esc(HEALTH?.model||"—")}</td></tr>
          <tr><td>密钥</td><td>${HEALTH?.api_key_configured ? "已配置" : "<span style='color:var(--warn)'>未配置（LLM 端点返回 503）</span>"}</td></tr>
          <tr><td>技能库</td><td>${HEALTH?.skills ?? "—"} 技能 · ${HEALTH?.evolved ?? 0} 演化</td></tr>
          <tr><td>令牌保护</td><td>${HEALTH?.token_required ? "已启用" : "未启用（默认）"}</td></tr>
        </table></div>
      <div><div style="font:600 12px inherit;margin-bottom:8px">自检（可本地复跑）</div>
        <table>
          <tr><td><code>python verify.py</code></td><td>31 项组件自检</td></tr>
          <tr><td><code>python -m pytest tests/</code></td><td>单元测试</td></tr>
          <tr><td><code>python tools/selfcheck.py</code></td><td>18 项交付自检（含数字一致性）</td></tr>
          <tr><td><code>python tools/profile_baseline.py</code></td><td>端到端耗时/成本采样</td></tr>
        </table></div>
    </div>
    <div style="margin-top:14px"><div style="font:600 12px inherit;margin-bottom:8px">API（${cfg ? Object.keys(cfg).length : 0} 项配置字段）</div>
      <table><tr><td><code>POST /api/runs</code></td><td>创建并后台执行 → run_id</td></tr>
      <tr><td><code>GET /api/runs/&#123;id&#125;/stream</code></td><td>SSE 实时事件流</td></tr>
      <tr><td><code>GET /api/runs</code></td><td>运行历史（不覆盖）</td></tr>
      <tr><td><code>POST /api/runs/&#123;id&#125;/cancel</code></td><td>取消（检查点退出）</td></tr></table></div>`;
}

/* ---------- boot ---------- */
(async function(){ await loadHealth(); route(); setInterval(loadHealth, 15000); })();

/* 自检项（仅 selftest 模式读取） */
window.__SELFTEST__ = function(){ return {
  "主容器存在": document.querySelectorAll("section, div.wrap, .card").length > 0,
  "有数据表或卡片": document.querySelectorAll("table, .card, .kpi").length > 0
}; };
