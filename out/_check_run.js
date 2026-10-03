
/* ============================================================================
   Live Run —— 全部内容由 SSE 真实事件驱动；**无 fake animation、无 staged delay**。
   设计约束（来自 Round 2 指令）：
   - 事件到达即渲染，禁止人为节奏；
   - 术语严格：L1 通过 = VERIFIED（确定性校验）；L2 = ASSERTIONS；L3 = SEMANTIC REVIEW；
     **绝不出现 "RESULT CORRECT"**（无 ground truth 时不允许声称结果正确）；
   - 产物依赖必须可见（点击边看 lineage：SHA256/大小/来源步骤）。
   ============================================================================ */
const API = location.port ? location.origin : "http://127.0.0.1:8848";
const QS = new URLSearchParams(location.search);
const RUN_ID = QS.get("id") || localStorage.getItem("last_run") || "";
// 截图/审计模式：不建立 SSE 长连接（否则无头浏览器的虚拟时钟无法结束，
// 与 graph.html 的 ?frames=N 是同一类问题），只回放已落盘事件。
const STATIC_MODE = QS.get("static") === "1";
// 指标测量（真实测量，非估计）：
//   TTFE = 首个运行事件到达（服务端）
//   TTFM = 首个"有意义"事件（候选技能/编排方案，即检索或编排完成）
//   TTFV = UI 首次渲染出有决策价值的信息（本页 = Execution Graph 首次绘制完成）
const PERF = { t0: Date.now(), ttfe: null, ttfm: null, ttfv: null };
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmtMs = ms => ms >= 1000 ? (ms/1000).toFixed(1) + "s" : Math.max(0, Math.round(ms)) + "ms";
const fmtTs = ms => { const d = new Date(ms); return d.toTimeString().slice(0,8) + "." + String(d.getMilliseconds()).padStart(3,"0"); };

let RUN = null;          // 最近一次 /api/runs/{id}
let EVENTS = [];         // 收到的全部事件
let SELECTED = null;     // {kind:"step"|"artifact"|"attempt", idx?, name?}
const T0 = Date.now();

/* ---------- SSE ---------- */
function subscribe(){
  const es = new EventSource(`${API}/api/runs/${encodeURIComponent(RUN_ID)}/stream`);
  es.onmessage = e => {
    let ev; try { ev = JSON.parse(e.data); } catch { return; }
    if (ev.type === "end" || ev.type === "run.finished") {
      setTimeout(() => { es.close(); refresh(); }, 120);
    }
    if (ev.type) {
      if (PERF.ttfe == null) PERF.ttfe = Date.now() - PERF.t0;
      if (PERF.ttfm == null && (ev.type === "retrieval.completed" || ev.type === "orchestration.completed"))
        PERF.ttfm = Date.now() - PERF.t0;
      EVENTS.push(ev); appendEvent(ev); reactTo(ev);
    }
  };
  es.addEventListener("end", () => { es.close(); refresh(); });
  es.onerror = () => { es.close(); setTimeout(refresh, 400); };
}

/* ---------- Header ---------- */
async function refresh(){
  try { RUN = await (await fetch(`${API}/api/runs/${encodeURIComponent(RUN_ID)}`)).json(); } catch { return; }
  if (RUN.detail) return;
  $("status").textContent = ({"COMPLETED":"已完成","PARTIAL":"部分完成","FAILED":"失败","RUNNING":"运行中",
        "EXECUTING":"执行中","RETRIEVING":"检索中","ORCHESTRATING":"编排中","VERIFYING":"验收中","EVOLVING":"进化中",
        "CANCELLED":"已取消","INTERRUPTED":"已中断","CREATED":"已创建","BUDGET_EXCEEDED":"超出预算"}[RUN.status] || RUN.status);
  $("status").className = "badge st-" + RUN.status;
  $("task").textContent = RUN.task || "";
  $("rid").textContent = RUN.run_id || "";
  $("stepstat").textContent = `${(RUN.step_stats||{}).done||0}/${(RUN.step_stats||{}).total||0}`;
  $("budget").textContent = "¥" + (RUN.budget?.max_cost_yuan ?? 0.2).toFixed(2);
  renderGraph(); renderTimelineMeta();
  if (SELECTED) renderInspector();
  const done = ["COMPLETED","FAILED","PARTIAL","CANCELLED","INTERRUPTED","BUDGET_EXCEEDED"].includes(RUN.status);
  $("cancel").disabled = done;
}
function tickHeader(){
  if (!RUN) return;
  const ended = RUN.ended_at_ms || (RUN.status === "COMPLETED" ? RUN.started_at_ms : 0);
  const ms = ended ? (RUN.ended_at_ms - RUN.started_at_ms) : (Date.now() - (RUN.started_at_ms || Date.now()));
  $("elapsed").textContent = fmtMs(ms);
  if (RUN.cost_yuan != null){
    $("cost").textContent = "¥" + Number(RUN.cost_yuan).toFixed(3);
    const cap = RUN.budget?.max_cost_yuan || 1;
    const pct = Math.min(100, RUN.cost_yuan / cap * 100);
    $("costbar").querySelector("i").style.width = pct + "%";
    $("costbar").className = "bar" + (pct > 75 ? " warn" : "");
  }
}
if (!(new URLSearchParams(location.search).get("static") === "1")) setInterval(tickHeader, 200);

/* ---------- Graph ---------- */
const STEP_STATE = s => {
  if (s.status === "done") {
    const failedChk = (s.checks_total || 0) > 0 && (s.checks_passed || 0) === 0;
    return failedChk ? "verifying" : "passed";
  }
  if (s.status === "failed") return s.n_attempts > 1 ? "failed" : "failed";
  if (s.status === "skipped") return "skipped";
  if (s.status === "running") return s.n_attempts > 1 ? "retrying" : "running";
  return "waiting";
};
function renderGraph(){
  const host = $("graph");
  if (!RUN || !RUN.steps) return;
  if (!RUN.steps.length){ host.innerHTML = '<div class="empty">尚无步骤（等方案生成）</div>'; return; }
  const parts = [];
  RUN.steps.forEach((s, i) => {
    const st = STEP_STATE(s);
    const sel = SELECTED && SELECTED.kind === "step" && SELECTED.idx === s.idx ? " sel" : "";
    parts.push(`<div class="gnode s-${st}${sel}" data-step="${s.idx}">
      <div class="grow1"><span class="dot"></span><span class="gname">S${s.idx+1} ${esc(s.action || "（未命名步骤）").slice(0,42)}</span></div>
      <div class="gmeta">${st.toUpperCase()} · ${fmtMs(s.duration_ms||0)}${s.n_attempts>1?` · <span class="gretry">×${s.n_attempts} 尝试</span>`:""}
        ${s.checks_total?` · 检查 ${s.checks_passed}/${s.checks_total}`:""}
        ${s.verification_total?` · 语义 ${s.verification_passed}/${s.verification_total}`:""}</div>
      ${s.skill?`<span class="gskill">${esc(s.skill)}</span>`:""}
    </div>`);
    // 依赖边：真实 artifact（下游 inputs）
    const next = RUN.steps[i+1];
    if (next) {
      const carried = (next.inputs || []);
      parts.push(`<div class="gedge"><div class="ln"></div>
        ${carried.length ? carried.map(a => `<span class="art" data-art="${esc(a)}" data-from="${s.idx}">${esc(a)}</span>`).join("")
                         : '<span class="art" style="color:var(--ink3);border-color:var(--line)">（无显式产物传递）</span>'}
        <div class="ln"></div></div>`);
    }
  });
  host.innerHTML = parts.join("");
  if (PERF.ttfv == null && RUN.steps.length) {
    PERF.ttfv = Date.now() - PERF.t0;
    // 上报（落盘到 Run，供审计）：一次 per page load
    fetch(`${API}/api/runs/${encodeURIComponent(RUN_ID)}`, {method:"GET"}).then(()=>{});
    try {
      const ev = {ts_ms: Date.now(), type: "perf.ttfv", data: {ttfe: PERF.ttfe, ttfm: PERF.ttfm, ttfv: PERF.ttfv}};
      fetch(`${API}/api/runs/${encodeURIComponent(RUN_ID)}/perf`, {
        method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(ev)
      }).catch(()=>{});
    } catch {}
  }
  host.querySelectorAll(".gnode").forEach(el => el.onclick = () => {
    SELECTED = { kind: "step", idx: +el.dataset.step }; renderGraph(); renderInspector();
  });
  host.querySelectorAll(".art").forEach(el => el.onclick = ev => {
    ev.stopPropagation();
    SELECTED = { kind: "artifact", name: el.dataset.art, from: +el.dataset.from };
    renderGraph(); renderInspector();
  });
  $("gcount").textContent = `${RUN.steps.length} steps`;
}

/* ---------- Timeline ---------- */
const EV_STYLE = t => t.startsWith("run.completed") || t === "execution.finished" ? "mile"
  : t === "run.finished" ? "mile"
  : t.includes("error") || t.includes("failed") ? "bad"
  : t === "step.retry" ? "warn"
  : t === "artifact.created" || t === "check.result" || t === "step.completed" ? "ok" : "";
const EV_TEXT = (ev) => {
  const d = ev.data || {};
  switch (ev.type) {
    case "run.started": return `Run started — <b>${esc((d.task||"").slice(0,90))}</b>`;
    case "retrieval.completed": return `Retrieved <b>${(d.selected||[]).length}</b> candidates · decision <b>${esc(d.decision||"")}</b> · ${fmtMs(d.duration_ms||0)}`;
    case "ranking.completed": return `Ranking ready — top: <b>${esc(d.top||"—")}</b>`;
    case "orchestration.completed": return `Workflow ready — <b>${(d.skills||[]).length}</b> skills · ${(d.workflow||0)} edges · ${fmtMs(d.duration_ms||0)}`;
    case "plan.created": return `研究方案 — <b>${d.steps}</b> 个步骤 · ${fmtMs(d.duration_ms||0)}`;
    case "run.executing": return `开始执行 <b>${d.steps}</b> 个步骤`;
    case "step.started": return `Step ${ev.step+1} 开始 — ${esc((d.action||"").slice(0,80))}${d.skill?` · <b>${esc(d.skill)}</b>`:""}`;
    case "step.inputs": return `Step ${ev.step+1} 输入 ← <b>${(d.files||[]).join(", ")}</b>`;
    case "code.generating": return `Step ${ev.step+1}: 生成代码（第 ${d.attempt} 次尝试）`;
    case "step.attempt": return `Step ${ev.step+1} 尝试 #${d.attempt} <b>${d.ok?"成功":"失败"}</b>${d.error_kind?` · ${esc(d.error_kind)}`:""} · ${fmtMs(d.duration_ms||0)}`;
    case "step.retry": return `Step ${ev.step+1}: 请求修复 — ${esc(d.reason||"")}`;
    case "artifact.created": return `✓ <b>${esc(d.name)}</b> 已创建 (${(d.bytes/1024).toFixed(1)} KB)`;
    case "check.result": return `${d.passed?"✓":"✗"} ${esc(d.name)}${d.passed?"":` — ${esc((d.detail||"").slice(0,70))}`}`;
    case "step.completed": return `Step ${ev.step+1} 完成 — ${d.status} · 产物 ${d.artifacts} · 验收 ${d.checks} · ${fmtMs(d.duration_ms||0)}`;
    case "step.error": return `Step ${ev.step+1} 异常 — ${esc((d.error||"").slice(0,90))}`;
    case "steps.skipped": return `步骤 ${JSON.stringify(d.steps)} 被跳过 — ${esc(d.reason||"")}`;
    case "execution.finished": return `执行结束 — 成功 <b>${d.done}</b> · 失败 <b>${d.failed}</b> · ${fmtMs(d.duration_ms||0)}`;
    case "judge.completed": return `语义评审 — 加权 <b>${d.weighted}</b>${d.coverage!=null?` · 覆盖 ${d.coverage}`:""}`;
    case "evolution.proposed": return `技能蒸馏 — ${d.accepted?`已准入 <b>${esc(d.name)}</b>`:"未准入"} · 库规模 ${d.library_size}`;
    case "run.reply": renderReply(d.text || ""); return `Agent 最终回复已生成（${(d.text||"").length} 字）`;
    case "run.finished": return `<b>运行结束 ${d.status}</b> · ${fmtMs(d.duration_ms||0)} · ¥${Number(d.cost||0).toFixed(3)}`;
    default: return `${esc(ev.type)} ${esc(JSON.stringify(d).slice(0,90))}`;
  }
};
/* 同类 check 结果聚合成一行：避免几十条 "✓ 文件存在" 淹没真正的里程碑事件。
   聚合行可点击展开明细（明细仍在数据里，未丢失信息）。 */
const CHECK_AGGR = new Map();   // stepIdx -> {el, n, ok, bad:[]}
function appendEvent(ev){
  const host = $("timeline");
  if (host.querySelector(".empty")) host.innerHTML = "";
  if (ev.type === "check.result" && ev.step != null) {
    const key = ev.step;
    let g = CHECK_AGGR.get(key);
    if (!g) {
      const div = document.createElement("div");
      div.className = "ev ok new";
      div.innerHTML = `<span class="ts">${fmtTs(ev.ts_ms)}</span><span class="msg"></span>`;
      div.onclick = () => { SELECTED = {kind:"step", idx:key}; renderGraph(); renderInspector(); };
      host.appendChild(div);
      g = { el: div, n: 0, ok: 0, bad: [] };
      CHECK_AGGR.set(key, g);
    }
    g.n++; if (ev.data && ev.data.passed) g.ok++; else g.bad.push((ev.data||{}).name || "");
    const cls = g.bad.length ? "warn" : "ok";
    g.el.className = "ev " + cls;
    g.el.querySelector(".msg").innerHTML =
      `Step ${key+1}: 确定性检查 <b>${g.ok}/${g.n}</b> 通过`
      + (g.bad.length ? ` — 未过：${esc(g.bad.slice(0,3).join("; "))}` : "")
      + ` <span style="color:var(--ink3)">（点击查看明细）</span>`;
    host.scrollTop = host.scrollHeight; updateEvCount(); return;
  }
  const div = document.createElement("div");
  div.className = "ev " + EV_STYLE(ev.type) + " new";
  div.innerHTML = `<span class="ts">${fmtTs(ev.ts_ms)}</span><span class="msg">${EV_TEXT(ev)}</span>`;
  div.onclick = () => { if (ev.step != null) { SELECTED = {kind:"step", idx:ev.step}; renderGraph(); renderInspector(); } };
  host.appendChild(div);
  host.scrollTop = host.scrollHeight;
  updateEvCount();
}
function renderTimelineMeta(){ $("evcount").textContent = EVENTS.length + " events"; }
function updateEvCount(){ $("evcount").textContent = EVENTS.length + " events"; }
function reactTo(ev){
  if (ev.type === "step.started" || ev.type === "step.completed" || ev.type === "artifact.created"
      || ev.type === "check.result" || ev.type === "step.attempt") {
    fetch(`${API}/api/runs/${encodeURIComponent(RUN_ID)}`).then(r=>r.json()).then(d=>{
      RUN = d; renderGraph(); tickHeader(); if (SELECTED) renderInspector();
    }).catch(()=>{});
  }
  if (ev.type === "run.finished") refresh();
}

/* ---------- Inspector ---------- */
function renderInspector(){
  const host = $("inspector");
  if (!RUN || !SELECTED){ host.innerHTML = '<div class="empty">点击左侧节点、产物边或时间线事件查看详情。</div>'; $("inswhat").textContent="—"; return; }
  if (SELECTED.kind === "step"){ const s = RUN.steps[SELECTED.idx]; if(!s) return; $("inswhat").textContent = `step ${s.idx+1}`; host.innerHTML = stepHtml(s); }
  else if (SELECTED.kind === "artifact"){ $("inswhat").textContent = "artifact"; host.innerHTML = artifactHtml(SELECTED); }
  else host.innerHTML = '<div class="empty">—</div>';
}
function stepHtml(s){
  const st = STEP_STATE(s);
  const q = RUN.retrieval && RUN.retrieval.selected ? RUN.retrieval.selected.indexOf(s.skill) : -1;
  const rk = (RUN.ranking||[]).find(r => r.name === s.skill);
  const attempts = (s.attempts||[]).map(a => `
    <div class="layer ${a.ok?"l1":"l3"}">
      <div class="lh"><span>Attempt #${a.n} ${a.ok?"PASSED":"FAILED"}</span><span>${fmtMs(a.duration_ms||0)}${a.error_kind?` · ${esc(a.error_kind)}`:""}</span></div>
      ${a.stderr?`<pre style="max-height:130px">${esc(a.stderr.slice(-700))}</pre>`:""}
      ${a.stdout?`<pre style="max-height:130px">${esc(a.stdout.slice(0,700))}</pre>`:""}
    </div>`).join("") || '<div class="empty">尚无尝试</div>';
  const l1 = (s.checks||[]).filter(c => !String(c.name).startsWith("[技能断言]"));
  const l2 = (s.checks||[]).filter(c => String(c.name).startsWith("[技能断言]"));
  const l3 = s.verifications||[];
  const chk = arr => arr.map(c => `<div class="chk ${c.passed?"":"bad"}"><span class="m">${c.passed?"✓":"✗"}</span>
      <span>${esc(c.name)}${c.detail?` <span style="color:var(--ink3)">— ${esc(c.detail)}</span>`:""}
      ${c.evidence?` <span style="color:var(--ink3)">— ${esc(c.evidence)}</span>`:""}</span></div>`).join("") || '<div class="empty">（无）</div>';
  const stageRows = Object.entries(s.stages||{}).sort((a,b)=>b[1]-a[1]).map(([k,v]) =>
      `<div class="row"><span>${esc(k)}</span><b>${k.endsWith("_ms")?fmtMs(v):v}</b></div>`).join("") || '<div class="empty">（无细分数据）</div>';
  const arts = (s.artifacts||[]).map(a => `<div class="row"><a href="${API}/api/runs/${RUN.run_id}/artifacts/${encodeURIComponent(a.name)}" target="_blank">${esc(a.name)}</a><b>${(a.bytes/1024).toFixed(1)} KB</b></div>`).join("") || '<div class="empty">（无）</div>';
  return `
  <div class="ins-sec">
    <div class="ins-k">步骤 ${s.idx+1} · ${st.toUpperCase()}</div>
    <div class="row"><span>动作</span><b style="text-align:right;max-width:260px">${esc(s.action)}</b></div>
    <div class="row"><span>技能</span><b>${esc(s.skill||"—")}</b></div>
    <div class="row"><span>耗时</span><b>${fmtMs(s.duration_ms||0)}</b></div>
    <div class="row"><span>尝试次数</span><b>${s.n_attempts}${s.fixed?"（修复后成功）":""}${s.exhausted?"（尝试耗尽）":""}</b></div>
  </div>
  ${(q>=0||rk)?`<div class="ins-sec"><div class="ins-k">为什么选这个技能（检索 + 策略，可解释）</div>
    ${q>=0?`<div class="row"><span>检索排名</span><b>#${q+1} / ${(RUN.retrieval.selected||[]).length}</b></div>`:""}
    ${q>=0?`<div class="row"><span>检索置信度分流</span><b>${esc(RUN.retrieval.decision||"")} (${RUN.retrieval.confidence??"—"})</b></div>`:""}
    ${rk?`<div class="row"><span>策略预测收益</span><b>${rk.exploit}</b></div>
         <div class="row"><span>探索奖励</span><b>${rk.explore}</b></div>
         <div class="row"><span>优先级</span><b>${rk.priority}</b></div>`:""}
    <div class="note">排序来自历史反馈（预测）+ 探索奖励；当前样本下策略收益未在 heldout 上证实。</div>
  </div>`:""}
  <div class="ins-sec"><div class="ins-k">阶段细分（这段时间花在哪）</div>${stageRows}</div>
  <div class="ins-sec"><div class="ins-k">执行尝试</div>${attempts}</div>
  <div class="ins-sec"><div class="ins-k">产物验收（分层）</div>
    <div class="layer l1"><div class="lh"><span>L1 · 确定性检查 — VERIFIED</span><span>${l1.filter(c=>c.passed).length}/${l1.length}</span></div>
      <div class="note" style="border-style:solid;margin:0 0 6px">机器可验证约束（文件/表头/行数/数值范围/可编译）。<b>不等价于结果正确。</b></div>${chk(l1)}</div>
    <div class="layer l2"><div class="lh"><span>L2 · 技能断言 — ASSERTIONS</span><span>${l2.filter(c=>c.passed).length}/${l2.length}</span></div>${chk(l2)}</div>
    <div class="layer l3"><div class="lh"><span>L3 · 语义评审 — SEMANTIC REVIEW</span><span>${l3.filter(c=>c.passed).length}/${l3.length}</span></div>
      <div class="note" style="border-style:solid;margin:0 0 6px">由模型判定，且<b>与被评者是同一模型</b>——只作参考，不构成独立证据。</div>${chk(l3)}</div>
    ${s.verify_skip_reason?`<div class="note">${esc(s.verify_skip_reason)}</div>`:""}
  </div>
  <div class="ins-sec"><div class="ins-k">产物文件</div>${arts}</div>
  <div class="ins-sec"><div class="ins-k">生成的代码</div>
    <pre style="max-height:300px">${esc((s.code||"（无）").slice(0,6000))}</pre></div>`;
}
function artifactHtml(sel){
  const a = (RUN.steps||[]).flatMap(s=>s.artifacts||[]).find(x=>x.name===sel.name) || {};
  const consumers = (RUN.steps||[]).filter(s => (s.inputs||[]).includes(sel.name)).map(s=>s.idx+1);
  return `<div class="ins-sec"><div class="ins-k">产物血缘（从哪来、被谁用）</div>
    <div class="row"><span>文件名</span><b>${esc(sel.name)}</b></div>
    <div class="row"><span>来源步骤</span><b>Step ${(sel.from??a.from_step??0)+1}</b></div>
    <div class="row"><span>被用于</span><b>${consumers.length?consumers.map(i=>"Step "+i).join(", "):"（暂无下游）"}</b></div>
    <div class="row"><span>大小</span><b>${a.bytes?((a.bytes/1024).toFixed(1)+" KB"):"—"}</b></div>
    <div class="row"><span>SHA256（前 16）</span><b>${esc(a.sha256||"—")}</b></div>
    <div style="margin-top:8px"><a href="${API}/api/runs/${RUN.run_id}/artifacts/${encodeURIComponent(sel.name)}" target="_blank">打开 / 预览</a>
    　<a href="${API}/api/runs/${RUN.run_id}/artifacts/${encodeURIComponent(sel.name)}?download=1">下载</a></div>
  </div>
  <div class="ins-sec"><div class="ins-k">说明</div>
    <div class="note">这条边表示：<b>Step ${(sel.from??0)+1} 的产物作为 Step ${consumers.length?consumers[0]:"?"} 的输入</b>（文件系统级传递，非提示词占位）。</div>
  </div>`;
}

/* ---------- Cancel ---------- */
$("cancel").onclick = async () => {
  if (!confirm("请求取消该 Run？将在当前步骤检查点退出（不会硬杀沙箱进程）。")) return;
  $("cancel").disabled = true;
  await fetch(`${API}/api/runs/${encodeURIComponent(RUN_ID)}/cancel`, {method:"POST"});
  setTimeout(refresh, 600);
};
/* ---------- Tabs（移动端） ---------- */
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#tabs button").forEach(x=>x.classList.remove("on"));
  b.classList.add("on");
  document.querySelectorAll(".col").forEach(c => c.classList.toggle("on", c.dataset.tab === b.dataset.t));
});

/* ---------- Agent 最终回复（Markdown 轻渲染，先 esc 再处理标记） ---------- */
const mdToHtml = md => {
  const inline = s => s.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
                        .replace(/`([^`]+)`/g, "<code>$1</code>");
  const src = (typeof esc === "function" ? esc(String(md || "")) : String(md || ""))
    .replace(/```(\w*)\n?([\s\S]*?)```/g,
      (_m, _l, code) => "\u0000PRE" + btoa(unescape(encodeURIComponent(code))) + "\u0000");
  return src.split(/\n{2,}/).map(b => {
    const x = b.trim(); if (!x) return "";
    const pre = x.match(/^\u0000PRE([A-Za-z0-9+/=]*)\u0000$/);
    if (pre) return "<pre>" + decodeURIComponent(escape(atob(pre[1]))) + "</pre>";
    if (/^#{1,4}\s/.test(x)) return "<h5>" + inline(x.replace(/^#{1,4}\s/, "")) + "</h5>";
    if (x.split("\n").every(l => !l.trim() || /^\s*[-*]\s/.test(l)))
      return "<ul>" + x.split("\n").filter(l => l.trim())
        .map(l => "<li>" + inline(l.replace(/^\s*[-*]\s/, "")) + "</li>").join("") + "</ul>";
    if (x.split("\n").every(l => !l.trim() || /^\s*\d+[.、)]\s/.test(l)))
      return "<ol>" + x.split("\n").filter(l => l.trim())
        .map(l => "<li>" + inline(l.replace(/^\s*\d+[.、)]\s/, "")) + "</li>").join("") + "</ol>";
    return "<p>" + inline(x).replace(/\n/g, "<br>") + "</p>";
  }).filter(Boolean).join("");
};
function renderReply(text){
  const old = document.getElementById("ai-reply"); if (old) old.remove();
  if (!text) return;
  const host = document.getElementById("inspector") || document.body;
  const d = document.createElement("div");
  d.id = "ai-reply"; d.className = "ai-reply";
  d.innerHTML = '<div class="rp-head"><i></i>Agent 最终回复' +
    '<span class="rp-meta">基于本次真实执行数据生成</span></div>' +
    '<div class="rp-body">' + mdToHtml(text) + '</div>';
  host.parentNode.insertBefore(d, host.nextSibling);   // 紧跟时间线/检查器区块之后
}

/* ---------- boot ---------- */
(async function boot(){
  if (!RUN_ID){ document.body.innerHTML = '<div style="padding:24px;font:13px monospace;color:#9aa8b8">缺少 run id —— 请从 Mission Control 启动一次 Run。</div>'; return; }
  await refresh();
  // 先回放已发生的事件（刷新页面后时间线不空）
  try {
    const evs = (RUN.events || []);
    CHECK_AGGR.clear(); $("timeline").innerHTML = "";
    evs.forEach(appendEvent);
    updateEvCount();
  } catch {}
  if (!STATIC_MODE) subscribe();
  else { $("cancel").disabled = true; }
  tickHeader();
  // 历史 run 复查：回复已落盘则直接渲染
  try { if (RUN.staged && RUN.staged.final_reply) renderReply(RUN.staged.final_reply); } catch {}
})();
