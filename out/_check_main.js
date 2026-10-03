
const PAGE_VER = "2026-10-03h";   // 改版递增：与服务端不一致时自动强制刷新
const API = location.port ? location.origin : "http://127.0.0.1:8848";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmtMs = ms => ms == null ? "—" : (ms >= 1000 ? (ms / 1000).toFixed(1) + "s" : Math.max(0, Math.round(ms)) + "ms");

/* 轻量 Markdown → HTML（Agent 回复用）：标题/列表/代码块/粗体/行内代码。
   先 esc 再处理标记——所有内容都来自 LLM，必须当不可信文本。 */
function mdToHtml(md) {
  const inline = s => s.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
                        .replace(/`([^`]+)`/g, "<code>$1</code>");
  const src = esc(String(md || "")).replace(/```(\w*)\n?([\s\S]*?)```/g,
    (_m, _lang, code) => `\u0000PRE${btoa(unescape(encodeURIComponent(code)))}\u0000`);
  const blocks = src.split(/\n{2,}/).map(b => {
    const t = b.trim(); if (!t) return "";
    const pre = t.match(/^\u0000PRE([A-Za-z0-9+/=]*)\u0000$/);
    if (pre) return `<pre>${decodeURIComponent(escape(atob(pre[1])))}</pre>`;
    if (/^#{1,4}\s/.test(t)) return `<h5>${inline(t.replace(/^#{1,4}\s/, ""))}</h5>`;
    if (t.split("\n").filter(l => l.trim()).length >= 2 &&
        t.split("\n").filter(l => l.trim()).every(l => /^\|.*\|$/.test(l.trim()))) {
      const rows = t.split("\n").filter(l => l.trim())
        .map(l => l.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim()));
      const isSep = r => r.every(c => /^:?-{2,}:?$/.test(c));
      const body = rows.slice(isSep(rows[1] || []) ? 2 : 1);
      return "<table><thead><tr>" + rows[0].map(c => `<th>${inline(c)}</th>`).join("") +
        "</tr></thead><tbody>" + body.map(r => "<tr>" + r.map(c => `<td>${inline(c)}</td>`).join("") + "</tr>").join("") +
        "</tbody></table>";
    }
    if (/^>\s?/m.test(t)) {
      const q = t.split("\n").map(l => l.replace(/^>\s?/, "")).join("<br>");
      return `<blockquote>${inline(q)}</blockquote>`;
    }
    if (t.split("\n").every(l => !l.trim() || /^\s*[-*]\s/.test(l)))
      return "<ul>" + t.split("\n").filter(l => l.trim()).map(l => `<li>${inline(l.replace(/^\s*[-*]\s/, ""))}</li>`).join("") + "</ul>";
    if (t.split("\n").every(l => !l.trim() || /^\s*\d+[.、)]\s/.test(l)))
      return "<ol>" + t.split("\n").filter(l => l.trim()).map(l => `<li>${inline(l.replace(/^\s*\d+[.、)]\s/, ""))}</li>`).join("") + "</ol>";
    return `<p>${inline(t).replace(/\n/g, "<br>")}</p>`;
  });
  return blocks.filter(Boolean).join("");
}

function replyCardHTML(text) {
  return `<div class="ai-reply"><div class="rp-head"><i></i>Agent 最终回复` +
    `<span class="rp-meta">基于本次真实执行数据生成</span></div>` +
    `<div class="rp-body">${mdToHtml(text)}</div></div>`;
}

async function jget(url, t = 8000) {
  const c = new AbortController(); const to = setTimeout(() => c.abort(), t);
  try { const r = await fetch(url, { signal: c.signal }); if (!r.ok) throw new Error(r.status); return await r.json(); }
  finally { clearTimeout(to); }
}

let TASKS = [], CUR_GOLD = [], RUN_ID = 0;
let CAP = null;                       // 能力自证数据（/api/capabilities 缓存）
async function fillLiveNumbers() {
  try {
    const g = await jget(API + "/api/graph", 8000);
    const doms = new Set(g.nodes.map(n => n.domain)).size;
    const evolved = g.nodes.filter(n => n.source !== "seed").length;
    const map = { skills: g.nodes.length, domains: doms, edges: g.edges.length, evolved: evolved };
    try {
      CAP = await jget(API + "/api/capabilities", 8000);
      window.CAP = CAP;                       // 供自检/调试读取
      map.linucb_ratio = (CAP.linucb && CAP.linucb.generalization_ratio) || map.linucb_ratio;
    } catch (e2) { /* 端点不可用时保留静态占位 */ }
    document.querySelectorAll("[data-live]").forEach(el => {
      const v = map[el.dataset.live];
      if (v != null) el.textContent = v;
    });
  } catch (e) { /* 离线时保留占位符，不阻塞页面 */ }
}

/* ---------- 能力证据面板：每项能力的实时值 / 实现位置 / 测试 / 自核命令 ---------- */
function evidenceDetail(key) {
  if (!CAP) return "<div style='color:#8a97a4'>能力数据加载中（或服务未启动）—— 也可直接访问 <code>/api/capabilities</code></div>";
  const L = CAP.library, C = CAP.confidence_gating, K = CAP.linucb, S = CAP.statistics, R = CAP.reproducibility;
  const rows = arr => arr.map(([k, v]) => `<span>${k}</span><span>${v}</span>`).join("");
  const wrap = (title, pairs, cmd) =>
    `<h5>${title}<span class="close" onclick="document.getElementById('evpanel').innerHTML=''">收起 ✕</span></h5>` +
    `<div class="kv">${rows(pairs)}</div>` +
    (cmd ? `<div style="margin-top:8px;color:#8a97a4">自核命令：<code>${cmd}</code></div>` : "");
  switch (key) {
    case "library": return wrap("三层本体 · 技能库构成（实时计算）", [
      ["技能总数", L.skills + " 个"], ["领域数", L.domains + " 个"],
      ["类型化关系边", L.edges + " 条"], ["种子 / 演化", L.seed + " / " + L.evolved + "（演化随运行自动增长）"],
      ["数据来源", "<code>/api/graph</code> 实时返回（本页数字与接口同源）"]],
      "curl -s http://127.0.0.1:8848/api/graph | python -c \"import json,sys; g=json.load(sys.stdin); print(len(g['nodes']), len(g['edges']))\"");
    case "linucb": return wrap("技能选择（Shared LinUCB）· 跨技能泛化实测", [
      ["泛化比（同/异领域）", "<b>" + K.generalization_ratio + "×</b>（现场计算，非历史值）"],
      ["同领域未评估技能 Δ", K.near_delta], ["异领域技能 Δ", K.far_delta],
      ["测量方法", K.method], ["锁定测试", "<code>" + K.tests + "</code>"]],
      "python -m pytest tests/test_bandit.py -q");
    case "gating": return wrap("置信度分流 · 阈值与标定依据", [
      ["自动执行阈值", "BM25 原始分 ≥ " + C.auto_execute_threshold],
      ["人工确认区间", "[" + C.manual_confirm_threshold + ", " + C.auto_execute_threshold + ")"],
      ["无匹配直答", "< " + C.manual_confirm_threshold + "（无关查询实测为 0）"],
      ["标定依据", C.calibration], ["锁定测试", "<code>" + C.tests + "</code>"]],
      "python -m pytest tests/test_retrieval_policy.py -q");
    case "quality": return wrap("技能契约 · 五维质量分（准入闸）", [
      ["质量维度", CAP.quality_dimensions.join(" / ")],
      ["用法", "检索排序先验 + 进化准入判定（代码 <code>skillnet/schema.py::quality_score</code>）"],
      ["契约扩展字段", "陷阱提示 pitfalls · 验证方式 verification · 输入输出 inputs/outputs"]],
      "python -c \"from skillnet.schema import QUALITY_DIMENSIONS as Q; print(Q)\"");
    case "evolver": return wrap("技能进化 · 四算子与准入", [
      ["算子", CAP.evolver_operators.join(" / ")],
      ["闭环", "轨迹蒸馏 → 质量准入（相似度 + 命名 + 步骤数）→ 落盘 → 星图标记"],
      ["实测", "本次会话中库规模随运行从 98 → " + L.skills + "，全部经准入闸"],
      ["代码", "<code>skillnet/evolver.py</code> · 演示入口 <code>POST /api/evolve</code>"]],
      "curl -s -X POST http://127.0.0.1:8848/api/evolve -H 'Content-Type: application/json' -d '{\"task\":\"示例\"}'");
    case "stats": return wrap("评估体系 · 统计检验", [
      ["配对检验", S.paired_bootstrap], ["判定口径", S.note],
      ["数据集治理", "dev（调参）/ held-out（结论）严格隔离，调参集过拟合主动暴露"],
      ["代码", "<code>bench/run_bench.py</code>"]],
      "python bench/run_bench.py --help");
    case "ledger": return wrap("成本核算 · 请求级账本", [
      ["隔离方式", CAP.ledger.scope], ["账本字段", CAP.ledger.fields.join(" / ")],
      ["锁定测试", "<code>" + CAP.ledger.tests + "</code>"],
      ["页面可见", "每次运行结束的 Run Summary 与时间线均显示 ¥ 三位小数"]],
      "python -m pytest tests/test_runtime_pipeline.py -q");
    case "frameworks": return wrap("跨框架互操作 · 导出落点", [
      ...Object.entries(CAP.framework_targets).map(([k, v]) => [k, "<code>" + v + "</code>"]),
      ["代码", "<code>skillnet/adapters.py</code> · 导出为一次写全多落点，避免只认一个目录"]],
      "curl -s -X POST http://127.0.0.1:8848/api/export -H 'Content-Type: application/json' -d '{}'");
    case "repro": return wrap("可复现工程 · 自检与溯源", [
      ["交付自检", R.selfcheck], ["测试", R.tests], ["数字溯源", R.manifest]],
      "python verify.py && python -m pytest tests/ -q");
    default: return "";
  }
}
document.addEventListener("click", e => {
  const b = e.target.closest && e.target.closest(".evtag");
  if (!b) return;
  const host = document.getElementById("evpanel");
  if (!host) return;
  const html = evidenceDetail(b.dataset.ev);
  if (!html) { host.innerHTML = ""; return; }
  host.innerHTML = "<div class='evpanel'>" + html + "</div>";
  host.scrollIntoView({ behavior: "smooth", block: "nearest" });
});


/* ================== 对话工作台（首页内嵌双栏；与 /chat 共用同一会话存储） ==================
   设计：左栏只记问题（可新建/切换会话）；右栏多轮结果流。
   追问：提交时携带本会话最近 3 轮 {q, a}（a=上一轮回复摘要）——检索仍只用当前问题。 */
const WS_KEY = "skillnet_chat_sessions_v1";
let WS_SESSIONS = [], WS_CUR = null, wsBusy = false;
const WS_PHASES = [["retrieval","检索对比"],["ranking","策略选择"],["orchestration","任务编排"],
                   ["dag","DAG 收束"],["plan","研究方案"],["exec","真实执行"],["final","验收与进化"]];

function wsLoad(){ try { WS_SESSIONS = JSON.parse(localStorage.getItem(WS_KEY) || "[]"); } catch { WS_SESSIONS = []; }
  if (!Array.isArray(WS_SESSIONS)) WS_SESSIONS = []; }
function wsSave(){ try { localStorage.setItem(WS_KEY, JSON.stringify(WS_SESSIONS)); } catch {} }
function wsSess(){ return WS_SESSIONS.find(s => s.id === WS_CUR) || null; }
function wsNew(){ if (wsBusy) return;
  const s = { id: "s" + Date.now(), title: "", created: Date.now(), turns: [] };
  WS_SESSIONS.unshift(s); WS_CUR = s.id; wsSave(); wsRenderList(); wsRenderMsgs();
  $("task").focus(); }
function wsOpen(id){ if (wsBusy) return; WS_CUR = id; wsRenderList(); wsRenderMsgs(); }

function wsRenderList(){
  const host = $("ws-list"); if (!host) return;
  if (!WS_SESSIONS.length){
    host.innerHTML = '<div style="padding:12px 6px;font-size:12px;color:#8a97a4;line-height:1.9">还没有对话。<br>点上方「新建对话」开始。</div>';
    return;
  }
  host.innerHTML = WS_SESSIONS.map(s => `
    <div class="ws-item ${s.id === WS_CUR ? "on" : ""}" onclick="wsOpen('${s.id}')">
      <div class="t">${esc(s.title || "（新对话）")}</div>
      <div class="m">${s.turns.length} 问 · ${new Date(s.created).toLocaleString("zh-CN", {month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit"})}</div>
    </div>`).join("");
}

function wsPhaseBar(i){
  return '<div class="phases">' + WS_PHASES.map(([k, label]) =>
    `<span class="ph" id="wsp-${i}-${k}"><i></i>${label}</span>`).join("") + '</div>' +
    `<div class="sub2" id="wss-${i}">Run 创建后实时显示各阶段状态</div>`;
}
function wsSetPhase(i, k, state, ms){
  const el = document.getElementById(`wsp-${i}-${k}`); if (!el) return;
  el.className = "ph " + (state === "run" ? "on" : state === "done" ? "ok" : state === "fail" ? "no" : "");
  if (ms != null) el.insertAdjacentHTML("beforeend", ` <b style="font-weight:400;color:#aab6c1">${(ms/1000).toFixed(1)}s</b>`);
}
function wsSetSub(i, txt){ const el = document.getElementById(`wss-${i}`); if (el) el.textContent = txt; }

function wsTurnHTML(t, i){
  const body = t._loaded
    ? wsResultHTML(t._fin)
    : '<span style="color:#8a97a4">' + (t.body || "已提交，等待结果…") + "</span>";
  return `<div class="ws-turn" id="wst-${i}">
    <div class="ws-q"><div class="who">你</div><div class="txt">${esc(t.q)}</div></div>
    <div class="ws-card" id="wsc-${i}">${body}</div>
  </div>`;
}

function wsRenderMsgs(){
  const host = $("ws-msgs"); if (!host) return;
  const s = wsSess();
  if (!s || !s.turns.length){
    host.innerHTML = '<div class="ws-empty">' +
      '<div style="font-size:13px;color:var(--ink2);margin-bottom:10px">在上面输入问题，调用完整 Agent 框架</div>' +
      '<div class="cap-strip">' +
        '<span><b data-live="skills">—</b>技能资产</span>' +
        '<span><b data-live="domains">—</b>领域</span>' +
        '<span><b data-live="edges">—</b>类型化关系边</span>' +
        '<span><b data-live="evolved">—</b>演化技能</span>' +
        '<span><b>37</b>项自动化测试</span>' +
      '</div>' +
      '<div style="margin-top:12px;font-size:12px">执行完成后这里会给出：Run Summary · 每一步的执行解释 · AI 回复 · 本次任务总结<br>' +
      '同一个对话里可以继续追问，系统会自动带上上下文</div></div>';
    return;
  }
  host.innerHTML = s.turns.map((t, i) => wsTurnHTML(t, i)).join("");
  s.turns.forEach((t, i) => { if (t.run_id && !t._loaded && !t._loading) wsHydrate(i, t.run_id); });
  host.scrollTop = host.scrollHeight;
}

async function wsHydrate(i, runId){
  const s = wsSess(), t = s && s.turns[i]; if (!t) return;
  t._loading = true;
  try {
    const fin = await jget(API + "/api/runs/" + encodeURIComponent(runId), 15000);
    t._loaded = true; t._fin = fin;
    const box = document.getElementById(`wsc-${i}`);
    if (box) box.innerHTML = wsResultHTML(fin);
  } catch (e) {
    const box = document.getElementById(`wsc-${i}`);
    if (box) box.innerHTML = '<span style="color:#8a97a4">无法加载该次运行详情（' + esc(e.message || e) + "）</span>";
  } finally { t._loading = false; }
}

/* 完整结果：Run Summary + 折叠的逐步解释/原始事件 + AI 回复 + 本次任务总结 */
function wsResultHTML(fin){
  if (!fin) return "";
  const steps = fin.steps || [];
  const nDone = steps.filter(s => s.status === "done").length;
  const nFix = steps.filter(s => s.status === "done" && (s.n_attempts || 1) > 1).length;
  const nFail = steps.filter(s => s.status === "failed").length;
  const nSkip = steps.filter(s => s.status === "skipped").length;
  const cp = (fin.staged || {}).critical_path;
  const cpTxt = cp ? `关键路径 ${cp.steps.map(x => "Step " + (x + 1)).join(" → ")}（${(cp.ms/1000).toFixed(1)}s / 总 ${(fin.duration_ms/1000).toFixed(1)}s）` : "";
  const ret = (fin.retrieval || {}).fabric || {};
  const decMap = { auto: ["自动执行", "#2e7d4f"], confirm: ["人工确认", "#b0781a"], direct: ["直接回答", "#8a97a4"] };
  const dec = decMap[ret.decision] || [ret.decision || "—", "#8a97a4"];
  const confVal = typeof ret.confidence === "number" ? (ret.confidence * 100).toFixed(0) + "%" : "—";
  const chkOk = steps.reduce((a, s) => a + (s.checks || []).filter(c => c.passed).length, 0);
  const chkAll = steps.reduce((a, s) => a + (s.checks || []).length, 0);
  const chkPct = chkAll ? Math.round(chkOk / chkAll * 100) : 0;
  const histTurn = (wsSess() || { turns: [] }).turns.find(x => x.run_id === fin.run_id) || {};
  const histN = (histTurn.history || []).length;
  const ctxBox = histN ? ('<div class="ctx"><span onclick="wsToggleCtx(this)">带入上下文 ' + histN + ' 轮（追问依据） ▾</span><div class="ctx-body" style="display:none">' +
      (histTurn.history || []).map((h, i) => '<div><b>第 ' + (i + 1) + ' 轮问题：</b>' + esc(h.q || '') + '</div>' +
        (h.a ? '<div style="color:#8a97a4">其回复摘要：' + esc(String(h.a).slice(0, 160)) + '…</div>' : '')).join("") +
      '</div></div>') : "";
  const confBar = `<div class="conf">` +
    `<span class="ci" title="${esc(ret.decision_reason || "")}"><i style="background:${dec[1]}"></i>检索分流 · ${dec[0]}（相关度 ${confVal} · BM25 ${ret.raw_bm25_top != null ? Number(ret.raw_bm25_top).toFixed(1) : "—"}）</span>` +
    (chkAll ? `<span class="ci"><i style="background:var(--ok)"></i>程序化验收 ${chkOk}/${chkAll}<span class="bar"><b style="width:${chkPct}%"></b></span>${chkPct}%</span>` : "") +
    `</div>`;
  const sum = ctxBox + `<div style="background:var(--soft);border:1px solid var(--line);border-radius:6px;padding:10px 13px">` +
    `<b style="color:var(--brand)">Run Summary</b> · ${fin.status === "COMPLETED" ? "已完成" : fin.status === "PARTIAL" ? "部分完成" : fin.status} · ` +
    `¥${Number(fin.cost_yuan || 0).toFixed(3)} · ${(fin.duration_ms/1000).toFixed(1)}s<br>` +
    `步骤 ${steps.length}：一次通过 <b style="color:var(--ok)">${nDone - nFix}</b> · 修复后成功 <b style="color:#b0781a">${nFix}</b> · 失败 <b style="color:var(--bad)">${nFail}</b> · 跳过 <b>${nSkip}</b>` +
    (cpTxt ? `<br><span style="color:#8a97a4">${cpTxt}</span>` : "") +
    ` · <a href="/run?id=${encodeURIComponent(fin.run_id)}" target="_blank" style="color:var(--brand2)">完整面板 →</a>` +
    confBar + `</div>`;
  const stepsHtml = steps.map(s => stepCardHTML(s, fin)).join("") || '<div style="color:#8a97a4">无步骤</div>';
  const evTypes = ((fin.events || []).map(e => e.type).join(" → ")) || "（无事件记录）";
  const reply = (fin.staged || {}).final_reply;
  return sum +
    `<div style="margin-top:10px;font-size:12px;color:var(--brand2);cursor:pointer" onclick="wsToggle(this)">查看执行详情（${steps.length} 步 · 逐步解释与产物） ▾</div>
     <div style="display:none;margin-top:10px;border-top:1px dashed var(--line);padding-top:10px">
       ${stepsHtml}
       <div style="margin-top:10px"><div style="font-size:11px;letter-spacing:2px;color:#8a97a4">── 原始事件序列 ──</div>
       <pre style="white-space:pre-wrap;font:11px/1.6 Consolas,monospace;background:var(--soft);padding:9px 11px;border-radius:4px;margin-top:5px">${esc(evTypes)}</pre></div>
     </div>` +
    (reply ? linkifyArtifacts(replyCardHTML(reply), fin) : "") +
    taskSummaryHTML(fin);
}
function linkifyArtifacts(html, fin){
  const arts = fin.artifacts || [];
  if (!arts.length) return html;
  let out = html;
  for (const a of arts) {
    const bare = a.name.replace(/^step\d+_/, "");
    const chip = `<a class="cite" href="${API}/api/runs/${encodeURIComponent(fin.run_id)}/artifacts/${encodeURIComponent(a.name)}" target="_blank" title="打开产物">${esc(bare)}</a>`;
    out = out.split("`" + bare + "`").join(chip);
    out = out.split("`" + a.name + "`").join(chip);
  }
  return out;
}
function wsToggleCtx(el){
  const d = el.nextElementSibling;
  const open = d.style.display !== "none";
  d.style.display = open ? "none" : "grid";
  el.textContent = el.textContent.replace(open ? "▾" : "▴", open ? "▴" : "▾");
}
function wsToggle(el){
  const d = el.nextElementSibling;
  const open = d.style.display !== "none";
  d.style.display = open ? "none" : "block";
  el.textContent = el.textContent.replace(open ? "▾" : "▴", open ? "▴" : "▾");
}

async function wsSubmit(){
  if (wsBusy) return;
  const input = $("task"); const q = input.value.trim();
  if (!q){ input.focus(); return; }
  if (!wsSess()) wsNew();
  const s = wsSess();
  wsBusy = true;
  const btn = $("run"); const oldTxt = btn.textContent;
  btn.disabled = true; btn.textContent = "运行中…";
  $("err").style.display = "none";

  const history = s.turns.map(t => ({ q: t.q, a: t.reply_digest || "" })).slice(-3);
  const turn = { q, run_id: null, ts: Date.now(), status: "running", history,
                 body: wsPhaseBar(s.turns.length) +
                       '<div class="sk-wrap"><div class="sk-line w85"></div><div class="sk-line w60"></div><div class="sk-line w40"></div></div>' };
  s.turns.push(turn);
  if (!s.title) s.title = q.slice(0, 34);
  wsSave(); wsRenderList(); wsRenderMsgs();
  const i = s.turns.length - 1;
  const host = $("ws-msgs"); host.scrollTop = host.scrollHeight;
  input.value = "";

  try {
    const r = await fetch(API + "/api/runs", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: q, k: 5, max_steps: 3, max_cost_yuan: 1.0,
                             max_seconds: 420, history })
    });
    if (!r.ok){ const d = await r.json().catch(() => ({}));
      throw new Error(typeof d.detail === "string" ? d.detail : ("HTTP " + r.status)); }
    const { run_id } = await r.json();
    turn.run_id = run_id; wsSave();
    wsSetSub(i, "Run 已创建：" + run_id);
    await wsStream(i, run_id);
    const fin = await jget(API + "/api/runs/" + encodeURIComponent(run_id), 15000);
    turn._loaded = true; turn._fin = fin; turn.status = fin.status;
    const reply = (fin.staged || {}).final_reply || "";
    turn.reply_digest = reply.replace(/[#*`>\-]/g, "").slice(0, 400);
    const box = document.getElementById(`wsc-${i}`);
    if (box) box.innerHTML = wsResultHTML(fin);
    wsSave();
  } catch (e) {
    turn.status = "error";
    const box = document.getElementById(`wsc-${i}`);
    if (box) box.innerHTML = '<div style="color:var(--bad)">运行失败：' + esc(e.message || e) + "</div>";
    wsSave();
  } finally {
    wsBusy = false; btn.disabled = false; btn.textContent = oldTxt;
    host.scrollTop = host.scrollHeight;
  }
}

async function wsStream(i, runId){
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 480000);
  try {
    const resp = await fetch(`${API}/api/runs/${encodeURIComponent(runId)}/stream`, { signal: ctrl.signal });
    const reader = resp.body.getReader(); const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n"); buf = lines.pop();
      for (const line of lines) {
        const x = line.trim();
        if (x === "event: end") return;
        if (!x.startsWith("data: ")) continue;
        let ev; try { ev = JSON.parse(x.slice(6)); } catch { continue; }
        wsOnEvent(i, ev);
        if (ev.type === "end") return;
      }
    }
  } catch (e) { /* 流断开：以最终状态接口为准 */ }
  finally { clearTimeout(timer); }
}

function wsOnEvent(i, ev){
  const t = ev.type || "", d = ev.data || ev;
  if (t === "retrieval.completed"){ wsSetPhase(i, "retrieval", "done", d.duration_ms); wsSetPhase(i, "ranking", "run");
    wsSetSub(i, `检索完成：三档对照，候选 ${(d.selected || []).length} 个`); }
  else if (t === "ranking.completed"){ wsSetPhase(i, "ranking", "done"); wsSetPhase(i, "orchestration", "run"); }
  else if (t === "orchestration.completed"){ wsSetPhase(i, "orchestration", "done"); wsSetPhase(i, "dag", "run");
    wsSetSub(i, `编排完成：${(d.skills || []).length} 个技能进入执行图`); }
  else if (t === "dag.ready"){ wsSetPhase(i, "dag", "done"); wsSetPhase(i, "plan", "run");
    wsSetSub(i, `执行图就绪：${(d.nodes || []).length} 步（来源 ${d.workflow_source || "—"}）`); }
  else if (t === "plan.created"){ wsSetPhase(i, "plan", "done", d.duration_ms); wsSetPhase(i, "exec", "run");
    wsSetSub(i, `方案生成：${d.steps} 步`); }
  else if (t === "step.started"){ wsSetSub(i, `执行中：Step ${d.step + 1}`); }
  else if (t === "step.attempt" && d.ok === false){ wsSetSub(i, `Step ${d.step + 1} 第 ${d.attempt} 次失败，准备自动修复`); }
  else if (t === "execution.finished"){ wsSetPhase(i, "exec", d.failed > 0 ? "fail" : "done"); wsSetPhase(i, "final", "run"); }
  else if (t === "evolution.proposed"){ wsSetSub(i, d.accepted ? `技能蒸馏：已准入 ${d.name} · 库规模 ${d.library_size}` : "技能蒸馏：本次未准入"); }
  else if (t === "run.reply"){ wsSetPhase(i, "final", "done"); wsSetSub(i, "Agent 最终回复已生成"); }
  else if (t === "run.failed" || t === "run.budget_exceeded"){
    WS_PHASES.forEach(([k]) => { const el = document.getElementById(`wsp-${i}-${k}`);
      if (el && el.className !== "ph ok") wsSetPhase(i, k, "fail"); });
    wsSetSub(i, "运行中断：" + String(d.reason || t));
  }
}

/* 原「实时运行」入口并入工作台（功能不减：仍是真实 SSE 流） */
async function startRealRun(){ return wsSubmit(); }

async function boot() {
  try {
    const h = await jget(API + "/api/health", 4000);
    // 缓存自愈：版本不一致时强制刷新一次（带 cache-bust 参数）
    if (h.ui_version && h.ui_version !== PAGE_VER && !sessionStorage.getItem("verfix_" + h.ui_version)) {
      sessionStorage.setItem("verfix_" + h.ui_version, "1");
      const u = new URL(location.href);
      u.searchParams.set("v", h.ui_version);
      location.replace(u.toString());
      return;
    }
    $("dot-srv").className = "dot on"; $("srv-txt").textContent = "在线";
    $("dot-key").className = "dot " + (h.api_key_configured ? "on" : "off");
    $("key-txt").textContent = h.api_key_configured ? "已配置（全功能）" : "未配置（离线模式）";
    $("lib-n").textContent = h.skills + " 个技能";
  } catch (e) {
    $("dot-srv").className = "dot off"; $("srv-txt").textContent = "未启动（python run.py）";
  }
  try {
    TASKS = await jget(API + "/api/tasks", 4000);
    const picks = [TASKS[1], TASKS[4], TASKS[5]].filter(Boolean);
    $("chips").innerHTML = '<span style="font-size:11.5px;color:#9aa7b3;margin-right:2px">试试：</span>' +
      picks.map(t => `<button class="chip" data-i="${TASKS.indexOf(t)}">${esc(t.query.slice(0, 16))}…</button>`).join("");
    document.querySelectorAll(".chip").forEach(c => c.onclick = () => {
      const t = TASKS[+c.dataset.i];
      $("task").value = t.query; CUR_GOLD = t.gold || [];
    });
  } catch (e) { $("chips").innerHTML = ""; }

  // 对话工作台初始化：恢复本机会话；没有则新建一个空会话
  try {
    wsLoad();
    if (!WS_SESSIONS.length) { wsNew(); }
    else { WS_CUR = WS_SESSIONS[0].id; wsRenderList(); wsRenderMsgs(); }
  } catch (e) { /* 工作台不可用时不影响首页其余部分 */ }
}

function addUser(q) {
  const d = document.createElement("div"); d.className = "msg-user"; d.textContent = q;
  $("chat").appendChild(d); return d;
}
function addBot() {
  const d = document.createElement("div"); d.className = "msg-bot";
  d.innerHTML = `<div class="timeline" style="display:block">
    <div class="tl-item" data-s="1"><div class="tl-rail"><div class="tl-no">1</div><div class="tl-line"></div></div>
      <div class="tl-card"><h4>检索对比 · 三档同题对照 <span class="st"></span></h4><div class="tl-body"></div></div></div>
    <div class="tl-item" data-s="2"><div class="tl-rail"><div class="tl-no">2</div><div class="tl-line"></div></div>
      <div class="tl-card"><h4>策略选择 · LinUCB 历史反馈排序 <span class="st"></span></h4><div class="tl-body"></div></div></div>
    <div class="tl-item" data-s="3"><div class="tl-rail"><div class="tl-no">3</div><div class="tl-line"></div></div>
      <div class="tl-card"><h4>任务级路由与编排 <span class="st"></span></h4><div class="tl-body"></div></div></div>
    <div class="tl-item" data-s="4"><div class="tl-rail"><div class="tl-no">4</div><div class="tl-line"></div></div>
      <div class="tl-card"><h4>技能驱动执行与盲评 <span class="st"></span></h4><div class="tl-body"></div></div></div>
    <div class="tl-item" data-s="5"><div class="tl-rail"><div class="tl-no">5</div><div class="tl-line"></div></div>
      <div class="tl-card"><h4>真实执行 · 代码在沙箱里跑起来 <span class="st"></span></h4><div class="tl-body"></div></div></div>
    <div class="tl-item" data-s="6"><div class="tl-rail"><div class="tl-no">6</div><div class="tl-line"></div></div>
      <div class="tl-card"><h4>反馈回流与技能蒸馏 · 留下了什么 <span class="st"></span></h4><div class="tl-body"></div></div></div>
    <div class="tl-item" data-s="7"><div class="tl-rail"><div class="tl-no">7</div><div class="tl-line"></div></div>
      <div class="tl-card"><h4>本次产出 · 生成了什么 <span class="st"></span></h4><div class="tl-body"></div></div></div>
  </div><div class="costbar" style="display:none"></div>`;
  $("chat").appendChild(d); return d;
}
function setStage(bot, n, st) {
  const it = bot.querySelector(`[data-s="${n}"]`); it.className = "tl-item " + st;
  const stEl = it.querySelector(".st"), body = it.querySelector(".tl-body");
  stEl.textContent = st === "running" ? "执行中" : st === "done" ? "完成" : "失败";
  if (st === "running") body.innerHTML = '<div><span class="spin"></span> 正在调用真实接口…</div><div class="shimmer"></div>';
  if (st === "done") { body.innerHTML = `<div class="reveal">${body.innerHTML}</div>`; }
  const pr = document.getElementById("prog");
  if (pr) {
    const doneN = bot.querySelectorAll(".tl-item.done").length;
    pr.style.width = Math.min(100, (doneN / 7) * 100) + "%";
  }
}
function rollNum(el, target, dec) {
  const t0 = performance.now();
  (function f(now) {
    const k = Math.min(1, (now - t0) / 700);
    const ease = 1 - Math.pow(1 - k, 3);
    el.textContent = (target * ease).toFixed(dec);
    if (k < 1) requestAnimationFrame(f);
  })(t0);
}
const tick = ms => new Promise(r => setTimeout(r, ms));

function sklList(sel, gold) {
  const g = gold || [];
  return sel.map(s => `<span class="skl${g.includes(s) ? " hit" : ""}">${esc(s)}</span>`).join("");
}

function renderStage1(d, gold) {
  const badge = m => {
    const x = d[m]; if (!x || !x.decision) return "";
    const map = { auto: ["可自动执行", "var(--ok)", "#eef7f1", "#9fd0af"],
                  confirm: ["建议人工确认", "var(--warn)", "#fdf6ec", "#ecd9a0"],
                  direct: ["无匹配 · 直答", "#8a97a4", "#f2f5f8", "#dde4ea"] };
    const [label, color, bg, bd] = map[x.decision] || map.direct;
    return `<span title="${esc(x.decision_reason || "")}" style="display:inline-block;margin-left:6px;font-size:10.5px;color:${color};background:${bg};border:1px solid ${bd};border-radius:999px;padding:0 7px">${label} · ${(x.confidence * 100).toFixed(0)}%</span>`;
  };
  const rows = ["bm25", "hybrid", "fabric"].map(m => {
    const x = d[m]; if (!x) return "";
    const rc = x.recall == null ? '<span style="color:#9aa7b3">无 gold 基准（任意问题按技能相关性检索）</span>'
                               : `召回 <b style="color:var(--brand)">${(x.recall * 100).toFixed(1)}%</b>`;
    return `<tr><td style="width:76px;font-weight:700;color:var(--brand)">${m.toUpperCase()}</td>
      <td>${sklList(x.selected, gold)} <span style="color:#9aa7b3">${rc}</span>${badge(m)}</td></tr>`;
  }).join("");
  const tr = (d.fabric?.trace || []).map(t => `<div>· ${esc(t)}</div>`).join("");
  const miss = (gold || []).filter(g => !(d.bm25?.selected || []).includes(g) && (d.fabric?.selected || []).includes(g));
  const note = miss.length ? `<div style="margin-top:6px;color:var(--ok)">BM25 漏掉、Fabric 通过<b>关系图扩展</b>补回：${sklList(miss, gold)}</div>` : "";
  const dec = d.fabric?.decision_reason ? `<div class="trace">决策：${esc(d.fabric.decision_reason)}</div>` : "";
  return `<table class="cmp">${rows}</table>${tr ? `<div class="trace">${tr}</div>` : ""}${dec}${note}`;
}

function renderStage2(d) {
  const nodes = (d.order || d.skills || []).map(n => `<span class="dagn">${esc(n)}</span>`).join('<span class="dagi">→</span>');
  return `<div class="dag">${nodes || "<i>无</i>"}<span class="dagi">→</span><span class="dagn end">执行产物</span></div>
    <div>任务级 Wiki：${d.wiki_size ?? "—"} 个候选 · ${esc(d.reason || "")}</div>`;
}

function renderBandit(d) {
  if (!d.rows || !d.rows.length) return "<i>候选为空</i>";
  const rows = d.rows.map((r, i) => `<tr>
    <td style="color:#9aa7b3">${i + 1}</td>
    <td>${esc(r.name)}${i === 0 ? ' <span class="skl hit" style="margin-left:4px">top-1</span>' : ""}</td>
    <td style="font-variant-numeric:tabular-nums">${r.exploit.toFixed(4)}</td>
    <td style="font-variant-numeric:tabular-nums">${r.explore.toFixed(4)}</td>
    <td style="font-variant-numeric:tabular-nums;font-weight:700;color:var(--brand)">${r.priority.toFixed(4)}</td>
  </tr>`).join("");
  return `<div style="font-size:11.5px;color:#8a97a4;margin-bottom:6px">${esc(d.note || "")}（候选池 ${d.n_candidates} 条）</div>
    <table class="cmp"><tr><th style="width:30px">#</th><th>技能</th><th style="width:78px">预测收益</th><th style="width:78px">探索奖励</th><th style="width:78px">优先级</th></tr>${rows}</table>
    <div style="font-size:11.5px;color:#8a97a4;margin-top:4px">预测收益由历史任务反馈训练而来（旧数据驱动）；探索奖励随评估次数衰减——越没试过的技能越有机会被尝试。</div>`;
}

function renderFeedback(d) {
  let fb = "";
  const rows = (d.feedback || []).map(f => {
    const up = f.delta > 1e-6, dn = f.delta < -1e-6;
    const arr = up ? '<span style="color:var(--ok)">↑</span>' : dn ? '<span style="color:var(--bad)">↓</span>' : '·';
    return `<tr><td>${esc(f.name)}${f.nudged ? ' <span class="skl hit">本次采纳</span>' : ""}</td>
      <td style="font-variant-numeric:tabular-nums">${f.exploit_before.toFixed(4)}</td>
      <td style="font-variant-numeric:tabular-nums">${f.exploit_after.toFixed(4)}</td>
      <td>${arr} <b style="color:${up ? "var(--ok)" : dn ? "var(--bad)" : "inherit"}">${(f.delta >= 0 ? "+" : "") + f.delta.toFixed(4)}</b></td></tr>`;
  }).join("");
  if (rows) {
    fb = `<div style="font-size:12.5px;margin:8px 0 4px">本次盲评奖励 <b style="color:var(--brand)">${(d.reward ?? 0).toFixed(2)}/1.0</b>
      已写回共享参数 θ（采纳 ${esc((d.adopted || []).join("、"))}）——<b>所有</b>技能的预测随之更新，同领域技能变化最大：</div>
    <table class="cmp"><tr><th>技能</th><th style="width:86px">更新前预测</th><th style="width:86px">更新后预测</th><th style="width:74px">变化</th></tr>${rows}</table>
    <div style="font-size:11.5px;color:var(--ok);margin:4px 0 10px">这就是「根据旧数据迭代」：下次遇到相似任务，排序将不同——学习可见、可追溯。</div>`;
  }
  const distill = d.accepted
    ? `<div class="nskill"><b>新候选技能：${esc(d.name)}</b>
        <div style="font-size:12px;color:var(--ink2);margin-top:3px">${esc(d.capability || "")}</div>
        <div class="meta">第 ${d.generation} 代 · 库规模 → <b style="color:var(--ok)">${d.library_size}</b></div></div>
       <div style="margin-top:6px;color:var(--ok)">新技能下次将以探索加成的方式获得优先尝试——闭环合拢。</div>`
    : `<div style="font-size:12.5px;color:var(--ink2)">本次轨迹未通过质量准入（阈值拦截）——治理的一部分：不是所有蒸馏都会入库。当前库规模 ${d.library_size}。</div>`;
  return fb + distill;
}

function renderPlan(plan) {
  if (!plan || !plan.steps || !plan.steps.length) return "";
  const steps = plan.steps.map((s, i) => {
    const ps = typeof s === "string" ? { action: s } : s;
    const params = (ps.key_params || []).map(x => `<li>${esc(x)}</li>`).join("");
    return `<div class="pstep"><div class="ph"><span class="no">S${i + 1}</span><span class="act">${esc(ps.action)}</span></div>
      ${ps.skill ? `<div class="klabel">调用技能 <span class="skl">${esc(ps.skill)}</span></div>` : ""}
      ${params ? `<div class="klabel">关键参数</div><ul>${params}</ul>` : ""}
      ${ps.expected_output ? `<div class="klabel">产出</div><div>${esc(ps.expected_output)}</div>` : ""}
      ${ps.check ? `<div class="chk">校验：${esc(ps.check)}</div>` : ""}</div>`;
  }).join("");
  const risks = (plan.risks || []).length ? `<div class="risk-box"><b>风险与应对</b><ul>${plan.risks.map(r => `<li>${esc(r)}</li>`).join("")}</ul></div>` : "";
  const arts = (plan.artifacts || []).length ? `<div class="art-box"><b>交付物</b> ${plan.artifacts.map(a => esc(a)).join(" · ")}</div>` : "";
  return `<div style="margin-top:10px;font-size:13px">${esc(plan.approach || "")}</div>
    <div class="plan-steps">${steps}</div>${risks}${arts}`;
}

function renderStage3(d, gold) {
  const j = d.judge || {};
  const dims = j.dimensions || j.scores || {};
  const contracts = (d.skills || []).map(s => `<span class="skl">${esc(s)}</span>`).join("");
  let bars = "";
  const subj = Object.entries(dims).filter(([k, v]) => typeof v === "number");
  bars += subj.map(([k, v]) => brow(k, v, false)).join("");
  const hasCov = j.coverage != null;
  if (subj.length) bars += `<div class="split">── ${hasCov ? "客观线（可程序化）" : "客观线：无 gold 基准，本次跳过"} ──</div>`;
  if (hasCov) bars += brow(`要点覆盖 ${j.covered?.length ?? "—"}/${j.n_points ?? "—"}`, j.coverage, true);
  return `<div style="margin-bottom:8px;font-size:11.5px;color:#8a97a4">加载的技能契约：${contracts}</div>
    <div class="bars">${bars}</div>
    <div style="margin-top:8px">技能采纳率 <b style="color:var(--brand)">${(d.adoption * 100).toFixed(0)}%</b> ·
    执行步骤 ${d.steps} · 盲评均分 <b style="color:var(--brand)">${(j.weighted ?? 0).toFixed(2)}/10</b></div>
    ${j.comment ? `<div class="trace">盲评意见：${esc(j.comment)}</div>` : ""}
    ${renderPlan(d.plan)}`;
  function brow(k, v, isObj) {
    const pct = Math.max(0, Math.min(100, v <= 1 ? v * 100 : v * 10));
    return `<div class="brow"><span>${esc(k)}</span><div class="btrack"><div class="bfill${isObj ? " obj" : ""}" style="width:${pct}%"></div></div><span class="bval">${typeof v === "number" ? v.toFixed(v <= 1 ? 2 : 1) : v}</span></div>`;
  }
}

function renderStage4(d) {
  if (!d.accepted) return `<div>本次轨迹未通过质量准入（阈值拦截）——治理的一部分：不是所有蒸馏都会入库。当前库规模 ${d.library_size}。</div>`;
  return `<div class="nskill"><b>新候选技能：${esc(d.name)}</b>
    <div style="font-size:12px;color:var(--ink2);margin-top:3px">${esc(d.capability || "")}</div>
    <div class="meta">第 ${d.generation} 代 · 蒸馏记录 ${d.records} 条 · 库规模 → <b style="color:var(--ok)">${d.library_size}</b></div>
    <div style="margin-top:8px"><button class="abtn" onclick="viewSkillRaw('${esc(d.name)}')">查看技能契约全文</button></div>
    </div><div style="margin-top:6px;color:var(--ok)">下次遇到相似任务，它会被检索并优先推荐——闭环合拢。</div>`;
}

let LAST_EXEC = null;   // {task, step, skill, metrics} 供「无技能对照」复用

async function runCompare(btn) {
  if (!LAST_EXEC) return;
  btn.disabled = true; const oldTxt = btn.textContent;
  const box = document.getElementById("cmpbox");
  box.innerHTML = '<div style="font-size:12px;color:var(--brand2);margin-top:10px"><span class="spin"></span> 正在跑两种对照：裸模型 · 提示词塞技能（各约 30 秒）…</div>';
  const call = (mode) => jget2(API + "/api/execute_one",
    { task: LAST_EXEC.task, step: LAST_EXEC.step, skill: LAST_EXEC.skill, mode }, 300000);
  try {
    const rBare = await call("none");
    const rPrompt = await call("prompt");
    const g = LAST_EXEC.metrics, s = LAST_EXEC.skill || "";
    const m = r => ({
      code: (r.code || "").length, out: (r.stdout || "").length,
      files: (r.artifacts || []).length,
      vf: r.verification_total ? r.verification_passed + "/" + r.verification_total + " 条带证据" : "无验收标准",
      ok: r.final_ok ? "成功" : "未成功",
    });
    const B = m(rBare), P = m(rPrompt);
    const cell = (v, best) => `<td style="color:${best ? "var(--ok)" : "inherit"};font-weight:${best ? 700 : 400}">${v}</td>`;
    const win = (a, b, c) => [a, b, c].map(Number).indexOf(Math.max(a, b, c));
    const wCode = win(g.code, P.code, B.code), wOut = win(g.out, P.out, B.out), wFile = win(g.files, P.files, B.files);
    box.innerHTML = `<div class="reveal">
      <div class="klabel" style="margin-top:12px">三方对照 · 同一任务、同一模型、同一步骤，唯一变量是「技能怎么被用」</div>
      <table class="cmp">
        <tr><th>指标</th><th style="width:22%">裸模型</th><th style="width:22%">提示词塞技能</th><th style="width:26%">SkillNet（契约模式）</th></tr>
        <tr><td>运行结果</td>${cell(B.ok, false)}${cell(P.ok, false)}${cell(g.ok + "（" + (LAST_EXEC.metrics.fix || "") + "）", true)}</tr>
        <tr><td>生成代码规模</td>${cell(B.code + " 字", wCode === 2)}${cell(P.code + " 字", wCode === 1)}${cell(g.code + " 字", wCode === 0)}</tr>
        <tr><td>运行输出信息量</td>${cell(B.out + " 字", wOut === 2)}${cell(P.out + " 字", wOut === 1)}${cell(g.out + " 字", wOut === 0)}</tr>
        <tr><td>落盘真实产物</td>${cell(B.files + " 个", wFile === 2)}${cell(P.files + " 个", wFile === 1)}${cell(g.files + " 个", wFile === 0)}</tr>
        <tr><td>产物验收</td>${cell("无", false)}${cell("无", false)}${cell(g.vf, true)}</tr>
        <tr><td>失败时修复依据</td>${cell("盲试", false)}${cell("盲试", false)}${cell("技能已知陷阱", true)}</tr>
      </table>
      <div style="font-size:12px;color:var(--ok);margin-top:6px">差异全部来自「技能被当成了什么」：背景资料（prompt）只是多了一段文字，
      而契约模式把它变成<b>执行步骤 + 红线 + 验收标准 + 修复线索</b>——这才是技能资产该有的用法。</div>
      <div style="font-size:11.5px;color:#8a97a4;margin-top:4px">说明：单次对照是演示性证据，不是统计结论；要做统计判断需多任务多轮次（与实验三同口径）。</div>
    </div>`;
  } catch (e) {
    box.innerHTML = `<div style="font-size:12px;color:var(--bad);margin-top:8px">对照运行失败：${esc(e.message || e)}</div>`;
  } finally { btn.disabled = false; btn.textContent = oldTxt; }
}

function renderSandbox(d, slug) {
  if (!d || (!d.attempts || !d.attempts.length)) {
    return `<div style="font-size:12.5px;color:var(--ink2)">本方案未包含适合自动化执行的分析步骤（通常是文献/写作类任务），已跳过沙箱执行。</div>`;
  }
  const ok = d.final_ok;
  // 尝试轨迹：失败 -> 修复 -> 成功，这是 Run→Validate→Fix 的直接证据
  const trail = d.attempts.map(a => {
    const cls = a.ok ? "var(--ok)" : "var(--bad)";
    const tag = a.ok ? "成功" : (a.kind || a.error_kind || "失败");
    return `<span style="display:inline-block;border:1px solid ${cls};color:${cls};border-radius:999px;padding:0 9px;font-size:11px;margin-right:6px">第${a.n}次 ${tag}${a.duration ? " · " + a.duration + "s" : ""}</span>`;
  }).join('<span style="color:#9aa7b3">→</span> ');
  const fixNote = d.fixed
    ? `<div style="font-size:12px;color:var(--ok);margin-top:6px">技能驱动的修复：前 ${d.n_attempts - 1} 次运行报错，把<b>错误输出 + 该技能的已知陷阱</b>一起交给模型后修复成功——没有技能就只能盲试。</div>`
    : d.exhausted
      ? `<div style="font-size:12px;color:var(--bad);margin-top:6px">已尝试 ${d.n_attempts} 次仍未成功：错误与技能陷阱都交付给了模型，说明当前任务粒度超出单次生成能力。这属于<b>需要记录的失败样本</b>（应缩小步骤粒度或改写技能），不做粉饰。</div>`
      : `<div style="font-size:12px;color:#8a97a4;margin-top:6px">一次运行即通过（未触发修复）。</div>`;
  const truncNote = d.truncated
    ? `<div style="font-size:12px;color:var(--warn);margin-top:4px">检测到<b>输出截断</b>（报错指向文件末尾的未闭合结构）：已自动改用「精简重写」策略，不再让模型修补超长代码。</div>`
    : "";

  const codeBlock = `<details style="margin-top:10px"><summary style="cursor:pointer;font-size:12px;color:var(--brand2)">查看本次执行的完整代码（${(d.code || "").length} 字符）</summary><pre style="max-height:340px;overflow:auto;background:#f7f9fb;border:1px solid var(--line);padding:12px;font-size:11.5px;white-space:pre-wrap">${esc(d.code || "")}</pre></details>`;
  const outBlock = d.stdout
    ? `<div style="margin-top:10px"><div class="klabel">真实运行输出</div><pre style="max-height:260px;overflow:auto;background:#0f1720;color:#c8f0d8;padding:12px;font-size:11.5px;white-space:pre-wrap">${esc(d.stdout)}</pre></div>`
    : "";

  const arts = (d.artifacts || []);
  const imgs = arts.filter(a => /\.(png|jpg|jpeg|svg)$/i.test(a.name));
  const others = arts.filter(a => !/\.(png|jpg|jpeg|svg)$/i.test(a.name));
  const imgBlock = imgs.length ? `<div style="margin-top:12px"><div class="klabel">真实产物 · 图像（由代码运行生成）</div>${
      imgs.map(a => `<div style="margin-top:6px"><img src="${API}/api/artifact/${esc(slug)}/${encodeURIComponent(a.name)}" onerror="this.insertAdjacentHTML('afterend','<div style=&quot;color:#a8433a;font-size:12px&quot;>图片加载失败：浏览器可能缓存了旧版页面，请按 Ctrl+Shift+R 强制刷新</div>')" style="max-width:100%;border:1px solid var(--line);border-radius:4px" alt="${esc(a.name)}">
        <div style="font-size:11px;color:#8a97a4">${esc(a.name)} · ${(a.bytes / 1024).toFixed(1)} KB · <a class="abtn" style="padding:1px 10px" href="${API}/api/artifact/${esc(slug)}/${encodeURIComponent(a.name)}?download=1">下载</a></div></div>`).join("")}</div>` : "";
  const otherBlock = others.length ? `<div style="margin-top:10px;font-size:12px">落盘数据文件：${others.map(a => `<span class="skl">${esc(a.name)} · ${(a.bytes / 1024).toFixed(1)}KB</span>`).join(" ")}</div>` : "";

  const vf = d.verification || [];
  const vfBlock = vf.length ? `<div style="margin-top:12px"><div class="klabel">技能验收清单逐条核对（${d.verification_passed}/${d.verification_total} 通过）</div>
      <table class="cmp">${vf.map(c => `<tr><td style="width:34px;font-weight:700;color:${c.passed ? "var(--ok)" : "var(--bad)"}">${c.passed ? "PASS" : "FAIL"}</td>
        <td>${esc(c.item)}</td><td style="color:#8a97a4">${esc(c.evidence)}</td></tr>`).join("")}</table>
      <div style="font-size:11.5px;color:#8a97a4;margin-top:4px">验收标准来自该技能的 verification 字段——技能契约在这里变成可执行的验收，不只是提示词。</div></div>`
    : `<div style="font-size:11.5px;color:#8a97a4;margin-top:8px">${esc(d.verify_skip_reason || "本次未进行逐条验收")}。</div>`;

  return `<div style="font-size:12.5px;margin-bottom:8px">
      <b>${esc(d.step_label || "")} · ${esc(d.action || "")}</b>
      ${d.skill ? `调用技能 <span class="skl hit">${esc(d.skill)}</span>` : ""}
      <span style="color:#8a97a4">｜执行方式：生成代码 → 沙箱真实运行 → ${d.fixed ? "失败修复重试 → " : ""}技能验收</span>
    </div>
    ${(() => {
      const st = d.skill_exec_stats || {};
      const tot = st.exec_total || 0;
      if (!tot) return "";
      const okN = st.exec_ok || 0;
      const rate = Math.round(okN / tot * 100);
      return `<div style="font-size:11.5px;color:#8a97a4;margin-bottom:8px">该技能的历史执行记录：
        累计执行 <b style="color:var(--ink)">${tot}</b> 次 · 成功 <b style="color:${rate >= 70 ? "var(--ok)" : "var(--warn)"}">${okN}</b> 次（${rate}%）
        ${st.exec_fix ? `· 其中 ${st.exec_fix} 次经修复后成功` : ""}
        ${st.exec_fail ? `· 失败 ${st.exec_fail} 次（最近错误类型 ${esc(st.exec_last_error || "")}）` : ""}
        <span style="opacity:.8">—— 执行可靠性正在成为技能的质量信号</span></div>`;
    })()}
    <div>${trail}</div>${fixNote}${truncNote}${codeBlock}${outBlock}${imgBlock}${otherBlock}${vfBlock}
    ${ok ? "" : `<div style="margin-top:8px;font-size:12px;color:var(--bad)">本次沙箱执行未成功（已尝试 ${d.n_attempts} 次）：${esc((d.attempts[d.attempts.length - 1] || {}).stderr || "")}</div>`}
    ${ok && d.skill ? `<div style="margin-top:10px"><button class="abtn solid" onclick="runCompare(this)">跑三方对照：裸模型 / 提示词塞技能 / SkillNet</button></div><div id="cmpbox"></div>` : ""}`;
}

function renderArtifacts(d) {
  if (!d || !d.artifacts || !d.artifacts.length) return "<i>本次未生成产物</i>";
  const isDeliv = a => (a.kind || "").indexOf("方案交付物") >= 0;
  const card = a => `<div class="artcard">
      <div><div class="an">${esc(a.name)}</div>
      <div class="ak">${esc(a.kind)} · ${(a.bytes / 1024).toFixed(1)} KB${a.declared_as ? " · 兑现清单项：" + esc(a.declared_as) : ""}</div></div>
      <div class="sp"></div>
      <button class="abtn" onclick="previewArtifact('${esc(d.slug)}','${esc(a.name)}')">在线查看</button>
      <a class="abtn solid" href="${API}/api/artifact/${esc(d.slug)}/${encodeURIComponent(a.name)}?download=1">下载</a>
    </div>`;
  const deliv = d.artifacts.filter(isDeliv);
  const docs = d.artifacts.filter(a => !isDeliv(a));
  const stat = d.declared != null
    ? `<div style="font-size:12px;margin-bottom:8px">方案声明交付物 <b style="color:var(--brand)">${d.declared}</b> 项 · 实际生成 <b style="color:var(--ok)">${d.generated}</b> 项${
        d.generated < d.declared ? '<span style="color:var(--warn)">（未全部兑现，下方列出实际落盘的文件）</span>' : "（全部兑现）"}${d.deliverable_error ? `　<span style="color:var(--warn)">${esc(d.deliverable_error)}</span>` : ""}</div>`
    : "";
  const note = d.saved
    ? `<div style="font-size:11.5px;color:var(--ok);margin-bottom:6px">已落盘到 out/demo_artifacts/${esc(d.slug)}/ —— 可直接交付或打印为 PDF</div>`
    : `<div style="font-size:11.5px;color:var(--warn);margin-bottom:6px">内存产物（落盘失败：${esc(d.save_error || "未知")}）</div>`;
  const head = t => `<div style="font-size:12px;color:#8a97a4;letter-spacing:1px;margin:10px 0 2px">── ${t} ──</div>`;
  return `${stat}${note}
    ${deliv.length ? head("方案声明的交付物（本次已生成内容）") + `<div class="art">${deliv.map(card).join("")}</div>` : ""}
    ${docs.length ? head("过程文档（方案与依据）") + `<div class="art">${docs.map(card).join("")}</div>` : ""}
    <div class="digest">任务指纹 ${esc(d.slug)} · 产物指纹 ${esc(d.digest)}（同一任务重复运行产物一致，可审计）</div>
    <div style="font-size:11.5px;color:#8a97a4;margin-top:6px">交付物为方案级产出：内容具体到条目与参数，但涉及实验结果的数值均标注为示意值，需在真实数据上验证。</div>`;
}

/* ---------- 弹层：产物预览 / 技能全文 ---------- */
function closeLayer() {
  const l = document.getElementById("layer"); if (l) l.remove();
}
function openLayer(title, { html = "", src = "", text = "" } = {}) {
  closeLayer();
  const l = document.createElement("div"); l.className = "layer"; l.id = "layer";
  l.onclick = e => { if (e.target === l) closeLayer(); };
  const body = html ? html : src ? `<iframe src="${src}"></iframe>` : `<pre>${esc(text)}</pre>`;
  l.innerHTML = `<div class="box"><div class="lb"><b>${esc(title)}</b>
      <button class="abtn" onclick="closeLayer()">关闭</button></div>
      <div class="lbody">${body}</div></div>`;
  document.body.appendChild(l);
}
async function previewArtifact(slug, name) {
  const url = `${API}/api/artifact/${slug}/${encodeURIComponent(name)}`;
  if (name.endsWith(".html")) return openLayer(name, { src: url });
  try {
    const r = await fetch(url); const txt = await r.text();
    openLayer(name, { text: txt });
  } catch (e) { openLayer(name, { text: "加载失败：" + e.message }); }
}
async function viewSkillRaw(name) {
  openLayer(name + " · 技能契约全文", { text: "加载中…" });
  try {
    const r = await fetch(`${API}/api/skill/${encodeURIComponent(name)}/raw`);
    const d = await r.json();
    openLayer(name + " · 技能契约全文（来源 " + d.source + "）", { text: d.content || "（空）" });
  } catch (e) { openLayer(name, { text: "加载失败：" + e.message }); }
}

async function startRealRun() {
  const task = $("task").value.trim();
  if (!task){ $("task").focus(); return; }
  const btn = $("run"); btn.disabled = true; const oldTxt = btn.textContent;
  btn.textContent = "创建运行中…";
  $("err").style.display = "none";
  try {
    const r = await fetch(API + "/api/runs", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({task, gold: CUR_GOLD || [], k: 5, max_steps: 3, max_cost_yuan: 1.0, max_seconds: 300})
    });
    if (!r.ok){ const d = await r.json().catch(()=>({})); throw new Error(typeof d.detail === "string" ? d.detail : r.status); }
    const d = await r.json();
    runLive(d.run_id, task);          // 留在本页：Skill Universe 直接响应真实 Run
  } catch (e) {
    $("err").style.display = "block";
    $("err").textContent = "创建运行失败：" + (e.message || e);
    btn.disabled = false; btn.textContent = oldTxt;
  }
}

/* ---------- WOW-1：本页 Live Run —— 星图 + 阶段条全部由真实 SSE 驱动 ---------- */
const PHASES = [
  ["retrieval", "检索对比"], ["ranking", "策略选择"], ["orchestration", "任务编排"],
  ["dag", "DAG 收束"], ["plan", "研究方案"], ["exec", "真实执行"], ["final", "验收与进化"],
];
let LIVE_RUN = null;   // 当前本页展示的 run_id
let LIVE_REPLY = "";   // Agent 最终回复（run.reply 事件带来，真实 LLM 生成）

/* 步骤卡（多轮复用）：做什么 / 使用技能 / 尝试与失败详情 / 验收 / 产物 / 输出 / 时间轴 */
function stepCardHTML(s, fin) {
    const stMap = { done: ["完成", "#2e7d4f"], failed: ["失败", "#a8433a"], skipped: ["已跳过", "#8a97a4"], running: ["执行中", "#24557a"], pending: ["等待", "#8a97a4"] };
    const pair = stMap[s.status] || [s.status, "#8a97a4"];
    const fixed = s.status === "done" && (s.n_attempts || 1) > 1;
    const L = [];
    L.push(`<div><b>做什么：</b>${esc(s.action || "")}</div>`);
    if (s.skill) L.push(`<div><b>使用技能：</b><code>${esc(s.skill)}</code></div>`);
    L.push(`<div><b>执行过程：</b>共 ${s.n_attempts || 1} 次尝试 · 耗时 ${fmtMs(s.duration_ms)}${fixed ? '（前几次失败，对照技能记录的陷阱自动修复）' : ""}</div>`);
    const t0 = fin.started_at_ms || (steps[0] && steps[0].started_at_ms) || 0;
    const totalMs = Math.max(1, fin.duration_ms || 0);
    if (t0 && s.started_at_ms && s.duration_ms > 0) {
      const leftPct = Math.max(0, Math.min(99, (s.started_at_ms - t0) / totalMs * 100));
      const widthPct = Math.max(1, Math.min(100 - leftPct, s.duration_ms / totalMs * 100));
      L.push(`<div style="margin-left:14px"><div style="position:relative;height:6px;background:var(--soft);border-radius:3px;overflow:hidden"><div style="position:absolute;left:${leftPct}%;width:${widthPct}%;height:100%;background:${pair[1]};opacity:.72;border-radius:3px"></div></div><div style="font-size:10.5px;color:#8a97a4;margin-top:2px">时间轴：第 ${((s.started_at_ms - t0) / 1000).toFixed(1)}s 开始（占整条运行的 ${widthPct.toFixed(0)}%）</div></div>`);
    }
    const fails = (s.attempts || []).filter(a => !a.ok);
    if (fails.length) L.push(`<div style="margin-left:14px;color:#8a6d3b">失败详情：${fails.map(a => `第 ${a.n} 次 ${esc(a.error_kind || "未知错误")}（${esc((a.stderr || "").slice(-130))}）`).join("；")}</div>`);
    if ((s.checks || []).length) {
      const okN = s.checks.filter(c => c.passed).length;
      const bad = s.checks.filter(c => !c.passed).slice(0, 3).map(c => esc(c.name)).join("、");
      L.push(`<div style="margin-left:14px"><b>程序化验收：</b>${okN}/${s.checks.length} 通过${okN < s.checks.length ? ` — 未通过项：${bad}` : ""}</div>`);
    }
    if ((s.artifacts || []).length) L.push(`<div style="margin-left:14px"><b>产出物：</b>${s.artifacts.map(a => `<a href="${API}/api/runs/${encodeURIComponent(fin.run_id)}/artifacts/${encodeURIComponent(a.name)}" target="_blank" style="color:var(--brand2)">${esc(a.name)}</a>（${(a.bytes / 1024).toFixed(1)} KB）`).join("、")}</div>`);
    if ((s.inputs || []).length) L.push(`<div style="margin-left:14px;color:#8a97a4">读取的上游产物：${esc(s.inputs.join("、"))}（文件级真实传递）</div>`);
    if (s.status === "skipped" && s.verify_skip_reason) L.push(`<div style="margin-left:14px;color:#8a97a4">${esc(s.verify_skip_reason)}</div>`);
    if (s.status === "failed" && s.error) L.push(`<div style="margin-left:14px;color:var(--bad)">最终错误：${esc(String(s.error).slice(0, 220))}</div>`);
    const okAtt = (s.attempts || []).filter(a => a.ok).slice(-1)[0];
    if (okAtt && (okAtt.stdout || "").trim()) L.push(`<div style="margin-left:14px"><b>输出摘要：</b><pre style="white-space:pre-wrap;font:11px/1.6 Consolas,monospace;background:var(--soft);padding:8px 10px;border-radius:4px;margin-top:3px;max-height:240px;overflow:auto">${esc(okAtt.stdout.slice(-900))}</pre></div>`);
    return `<div style="background:var(--card);border:1px solid var(--line);border-left:3px solid ${pair[1]};border-radius:6px;padding:11px 15px;margin-top:10px;font-size:12.5px">` +
      `<div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><b style="color:var(--brand)">Step ${s.idx + 1} · ${esc(s.skill || "通用")}</b><span style="color:${pair[1]};font-weight:700;white-space:nowrap">${pair[0]}${fixed ? "（修复后成功）" : ""}</span></div>` +
      `<div style="margin-top:6px;display:grid;gap:3px">${L.join("")}</div></div>`;
}

/* ---------- 本次任务总结：SkillNet 在本次任务里的角色 + 技能库成长 ---------- */
function taskSummaryHTML(fin) {
  const imp = (fin.staged || {}).skill_impact;
  if (!imp) return "";
  const s = imp.summary || {};
  const steps = fin.steps || [];
  const nDone = steps.filter(x => x.status === "done").length;
  const nFix = steps.filter(x => x.status === "done" && (x.n_attempts || 1) > 1).length;
  const chkOk = steps.reduce((a, x) => a + (x.checks || []).filter(c => c.passed).length, 0);
  const chkAll = steps.reduce((a, x) => a + (x.checks || []).length, 0);
  const usedList = (imp.used || []).slice(0, 8).join("、") || "通用执行";
  const delta = s.library_delta || 0;
  const evoUp = (imp.evolved_after || 0) - (imp.evolved_before || 0);
  const touchedRows = (imp.touched || []).slice(0, 8).map(x => {
    const parts = Object.entries(x.delta || {}).map(([k, v]) =>
      `${k} <b class="up">${v > 0 ? "+" : ""}${v}</b>`).join(" · ");
    return `<tr><td><code>${esc(x.name)}</code></td><td>${parts || "—"}</td></tr>`;
  }).join("");
  const newCards = (imp.new_skills || []).map(n =>
    `<div class="newskill"><b style="color:var(--ok)">新增技能：<code>${esc(n.name)}</code></b>` +
    `<span style="color:#8a97a4"> · 第 ${n.generation} 代 · 领域 ${esc(n.domain || "—")}` +
    (n.parents && n.parents.length ? ` · 衍生自 ${esc(n.parents.join("、"))}` : "") + `</span>` +
    (n.capability ? `<div style="margin-top:5px;color:var(--ink2)">${esc(n.capability)}</div>` : "") +
    (n.origin_task ? `<div style="margin-top:4px;color:#8a97a4">来源任务：${esc(n.origin_task)}</div>` : "") + `</div>`
  ).join("");
  return `<div class="task-summary">
    <div class="ts-head"><i></i>本次任务总结 · SkillNet 扮演的角色<span class="rp-meta">数据来自技能统计前后差值</span></div>
    <div class="ts-role">它不是执行者，而是这个 Agent 的<b>能力运维层</b>：本次任务里它完成了「找到能力 → 挑出能力 → 编排能力 → 验收产物 → 沉淀能力」五件事。</div>
    <div class="ts-steps">
      <div class="ts-step"><b>① 检索</b><span>从 ${imp.library_before} 个技能中三档检索（BM25 / 语义 / 关系图扩展）定位候选</span></div>
      <div class="ts-step"><b>② 选择</b><span>LinUCB 按任务条件化排序，最终采用 ${s.used_n || 0} 个技能：${esc(usedList)}</span></div>
      <div class="ts-step"><b>③ 编排</b><span>按技能依赖边生成执行 DAG，${steps.length} 步真实执行（含修复后的 ${nFix} 步）</span></div>
      <div class="ts-step"><b>④ 验收</b><span>程序化验收 ${chkOk}/${chkAll} 通过${nDone < steps.length ? `，${steps.length - nDone} 步未完成` : "，全部步骤完成"}</span></div>
      <div class="ts-step"><b>⑤ 沉淀</b><span>${(imp.new_skills || []).length ? `蒸馏并准入 ${(imp.new_skills || []).length} 个新技能（见下）` : "本次未产生通过准入的新技能（相似度/质量闸拦截）"}</span></div>
    </div>
    <div class="ts-metrics">
      <div><b>${imp.library_before} → ${imp.library_after}</b>技能库规模${delta ? `（+${delta}）` : ""}</div>
      <div><b>${imp.evolved_before} → ${imp.evolved_after}</b>演化技能${evoUp ? `（+${evoUp}）` : ""}</div>
      <div><b>${s.updated_n || 0}</b>个技能被本次任务更新</div>
      <div><b>${s.used_n || 0}</b>个技能被采用</div>
    </div>
    ${touchedRows ? `<div class="ts-sec">── 技能资产更新（本次使用后的真实统计变化）──</div>
    <table><tr><th style="width:38%">技能</th><th>变化（pulls 调用 · exec_total 执行 · exec_ok 成功 · reward_sum 奖励）</th></tr>${touchedRows}</table>` : ""}
    ${newCards ? `<div class="ts-sec">── 能力沉淀（本次任务为 Agent 长出的新能力）──</div>${newCards}` : ""}
  </div>`;
}

function mountReplyCard() {
  const sum = $("livesum"); if (!sum) return;
  const old = document.getElementById("ai-reply-slot"); if (old) old.remove();
  if (!LIVE_REPLY) return;
  const slot = document.createElement("div");
  slot.id = "ai-reply-slot";
  slot.innerHTML = replyCardHTML(LIVE_REPLY);
  sum.appendChild(slot);                       // 流程展示完后，最后一段回复
}

function livebarHTML() {
  return "<div style='display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px 14px'>" +
    "<span style='font-size:11px;letter-spacing:2px;color:#8a97a4'>LIVE RUN</span>" +
    PHASES.map(([k, label]) =>
      `<span id="ph-${k}" style="font-size:12px;color:#8a97a4;display:inline-flex;align-items:center;gap:5px">` +
      `<i id="phd-${k}" style="width:8px;height:8px;border-radius:50%;background:#d5dde4;display:inline-block"></i>${label}<b id="pht-${k}" style="font-weight:400;color:#aab6c1"></b></span>`
    ).join("") +
    `<span style="flex:1"></span><a id="live-link" href="/run?id=${LIVE_RUN}" target="_blank" style="font-size:11.5px;color:var(--brand2)">完整面板 →</a></div>` +
    `<div id="livesum" style="display:none;margin-top:10px"></div>`;
}

function setPhase(k, state, ms) {
  const dot = document.getElementById("phd-" + k), t = document.getElementById("pht-" + k);
  const wrap = document.getElementById("ph-" + k);
  if (!dot) return;
  if (state === "run") { dot.style.background = "#24557a"; dot.style.animation = "sp 1s linear infinite"; wrap.style.color = "var(--brand2)"; }
  else { dot.style.animation = "";
    dot.style.background = state === "done" ? "#2e7d4f" : state === "fail" ? "#a8433a" : "#d5dde4";
    wrap.style.color = state === "done" ? "var(--ink)" : "#8a97a4"; }
  if (ms != null && t) t.textContent = (ms / 1000).toFixed(1) + "s";
}

async function runLive(runId, task) {
  LIVE_RUN = runId;
  const bar = $("livebar");
  bar.style.display = "block";
  bar.innerHTML = livebarHTML();
  document.getElementById("live-link").href = "/run?id=" + encodeURIComponent(runId);
  if (window.HeroNet) HeroNet.exitDag();
  LIVE_REPLY = "";
  setPhase("retrieval", "run");
  let ended = false;
  try {
    const resp = await fetch(`${API}/api/runs/${encodeURIComponent(runId)}/stream`);
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (!ended) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();
      for (const line of lines) {
        const s = line.trim();
        if (s === "event: end") { ended = true; break; }
        if (!s.startsWith("data: ")) continue;
        let ev; try { ev = JSON.parse(s.slice(6)); } catch { continue; }
        handleRunEvent(ev, runId);
        if (ev.type === "end") { ended = true; break; }
      }
    }
  } catch (e) { /* 流断开：以最终状态接口为准 */ }
  // 兜底：拉最终状态（无论流是否正常结束）
  try {
    const fin = await (await fetch(API + "/api/runs/" + encodeURIComponent(runId))).json();
    renderLiveFinal(fin);
  } catch {}
}

function handleRunEvent(ev, runId) {
  const t = ev.type || "";
  const d = ev.data || ev;                     // BUS 事件负载嵌套在 data 里
  if (t === "retrieval.completed") {
    setPhase("retrieval", "done", d.duration_ms);
    setPhase("ranking", "run");
    if (window.HeroNet && Array.isArray(d.selected)) HeroNet.highlight(d.selected);
  } else if (t === "ranking.completed") {
    setPhase("ranking", "done");
    setPhase("orchestration", "run");
  } else if (t === "orchestration.completed") {
    setPhase("orchestration", "done");
    setPhase("dag", "run");
    if (window.HeroNet) HeroNet.select(d.order || d.skills || []);
  } else if (t === "dag.ready") {
    setPhase("dag", "done");
    setPhase("plan", "run");
    if (window.HeroNet && Array.isArray(d.nodes)) HeroNet.dagify(d.nodes);
  } else if (t === "plan.created") {
    setPhase("plan", "done", d.duration_ms);
    setPhase("exec", "run");
  } else if (t === "step.started") {
    if (window.HeroNet) HeroNet.stepState(d.step, "running");
  } else if (t === "step.completed") {
    if (window.HeroNet) HeroNet.stepState(d.step, d.status === "done" ? "done" : "failed");
  } else if (t === "steps.skipped") {
    if (window.HeroNet) (d.steps || []).forEach(i => HeroNet.stepState(i, "skipped"));
  } else if (t === "execution.finished") {
    setPhase("exec", d.failed > 0 ? "fail" : "done");
    setPhase("final", "run");
  } else if (t === "run.reply") {
    LIVE_REPLY = d.text || "";
    mountReplyCard();                          // 可能早于或晚于 renderLiveFinal，幂等插入
  } else if (t === "evolution.proposed") {
    // Moment 5：反馈真实回流 —— 蒸馏候选是否被质量准入
    const sum = $("livesum"); if (!sum) return;
    const card = document.getElementById("evo-card") || document.createElement("div");
    card.id = "evo-card";
    card.style.cssText = "margin-top:10px";
    card.innerHTML = `<div style="background:var(--card);border:1px solid ${d.accepted ? "#cfe6d6" : "var(--line)"};border-left:3px solid ${d.accepted ? "var(--ok)" : "#9aa7b3"};border-radius:6px;padding:11px 15px;font-size:12.5px;color:var(--ink2)">` +
      `<b style="color:var(--brand)">反馈回流 · 技能蒸馏</b> —— 本次任务的轨迹${d.accepted ? "已蒸馏为候选技能并通过质量准入" : "未达到准入标准（相似度/质量闸）"}：` +
      `${d.accepted ? `<b style="color:var(--ok)">${esc(d.name || "新技能")}</b>` : "未准入"} · 库规模 ${d.library_size} · ` +
      `<a href="/graph" target="_blank" style="color:var(--brand2)">在星图查看进化技能 →</a></div>`;
    sum.appendChild(card);
  } else if (t === "run.failed" || t === "run.budget_exceeded") {
    ["retrieval","ranking","orchestration","dag","plan","exec"].forEach(k => {
      const el = document.getElementById("ph-" + k);
      if (el && el.style.color !== "var(--ink)") setPhase(k, "fail");
    });
    setPhase("final", "fail");
    const sum = $("livesum");
    if (sum) { sum.style.display = "block";
      sum.innerHTML = `<div class="next" style="border-left:3px solid var(--bad)">运行失败：${esc(String(d.reason || t))}。<a href="/run?id=${encodeURIComponent(runId)}" target="_blank">查看详情</a></div>`; }
    $("run").disabled = false; $("run").textContent = "发送";
  }
}

function renderLiveFinal(fin) {
  setPhase("final", fin.status === "COMPLETED" || fin.status === "PARTIAL" ? "done" : "fail");
  const sum = $("livesum"); if (!sum) return;
  sum.style.display = "block";
  const steps = fin.steps || [];
  const nDone = steps.filter(s => s.status === "done").length;
  const nFix = steps.filter(s => s.status === "done" && (s.n_attempts || 1) > 1).length;
  const nFail = steps.filter(s => s.status === "failed").length;
  const nSkip = steps.filter(s => s.status === "skipped").length;
  const cp = ((fin.staged || {}).critical_path) || null;
  const conc = (fin.staged || {}).max_concurrency;
  const evoExisting = document.getElementById("evo-card");
  const cpTxt = cp ? `关键路径 ${cp.steps.map(i => "Step " + (i + 1)).join(" → ")}（${(cp.ms / 1000).toFixed(1)}s / 总 ${(fin.duration_ms / 1000).toFixed(1)}s）` : "";
  const ccTxt = conc > 1 ? `最大并行 ${conc} 步` : "";

  /* ── 运行摘要 ── */
  const summaryCard = "<div style='background:var(--card);border:1px solid var(--line);border-radius:6px;padding:12px 16px;font-size:12.5px;color:var(--ink2)'>" +
    `<b style="color:var(--brand)">Run Summary</b> · ${fin.status === "COMPLETED" ? "已完成" : fin.status === "PARTIAL" ? "部分完成" : "失败"} · ¥${Number(fin.cost_yuan || 0).toFixed(3)} · ${(fin.duration_ms / 1000).toFixed(1)}s<br>` +
    `步骤 ${steps.length}：一次通过 <b style="color:var(--ok)">${nDone - nFix}</b> · 修复后成功 <b style="color:#b0781a">${nFix}</b> · 失败 <b style="color:var(--bad)">${nFail}</b> · 跳过 <b>${nSkip}</b>` +
    (ccTxt ? ` · <b style="color:var(--brand2)">${ccTxt}</b>` : "") +
    (cpTxt ? `<br><span style="color:#8a97a4">${cpTxt}</span>` : "") +
    ` · <a href="/run?id=${encodeURIComponent(fin.run_id)}" target="_blank" style="color:var(--brand2)">产物与验收证据 →</a></div>`;

  /* ── AI 回复卡：方案的结论 + 语义评审 ── */
  const approach = (fin.plan && fin.plan.approach) || "";
  const j = fin.judge || {};
  const jTxt = j.weighted != null ? `语义评审加权 ${Number(j.weighted).toFixed(1)}/10${j.coverage != null ? ` · 要点覆盖 ${(j.coverage * 100).toFixed(0)}%` : ""}` : "";
  const aiCard = "<div style='background:#f6f9fc;border:1px solid #c9d8e6;border-left:4px solid var(--brand2);border-radius:6px;padding:12px 16px;margin-top:10px;font-size:12.5px'>" +
    `<b style="color:var(--brand2)">AI 回复</b>${jTxt ? ` · <span style="color:#8a97a4">${jTxt}</span>` : ""}` +
    (approach ? `<div style="margin-top:6px;color:var(--ink)">${esc(String(approach))}</div>` : "<div style='margin-top:6px;color:#8a97a4'>（方案未包含结论段）</div>") +
    `</div>`;

  /* ── 每一步的详细解释 ── */
  const stepCard = s => stepCardHTML(s, fin);

  sum.innerHTML = summaryCard + aiCard +
    `<div style="margin-top:14px;font-size:11px;letter-spacing:2px;color:#8a97a4">── 每一步的执行解释 ──</div>` +
    steps.map(stepCard).join("");
  if (evoExisting) sum.appendChild(evoExisting);   // 保留进化卡（先到的事件）
  mountReplyCard();                                // Agent 最终回复（流程展示完的最后一段）
  document.getElementById("task-summary-slot")?.remove();
  const tsHtml = taskSummaryHTML(fin);
  if (tsHtml) {                                    // 本次任务总结（角色 + 技能库成长）
    const slot = document.createElement("div");
    slot.id = "task-summary-slot";
    slot.innerHTML = tsHtml;
    sum.appendChild(slot);
  }
  $("run").disabled = false; $("run").textContent = "发送";
}

async function loadRunCenter(){
  const host = document.getElementById("runlist");
  try {
    let runs = [];
    try { runs = (await (await fetch(API + "/api/runs?limit=8")).json()).runs || []; } catch {}
    if (!runs.length){ host.innerHTML = '<div style="font-size:12.5px;color:#8a97a4;padding:8px 0">还没有运行记录 —— 在上方输入任务，点「实时运行」创建第一条。</div>'; return; }
    const ST = {COMPLETED:["已完成","#2e7d4f"],PARTIAL:["部分完成","#b0781a"],FAILED:["失败","#a8433a"],
                RUNNING:["运行中","#1f5f9e"],EXECUTING:["执行中","#1f5f9e"],RETRIEVING:["检索中","#1f5f9e"],
                ORCHESTRATING:["编排中","#1f5f9e"],VERIFYING:["验收中","#1f5f9e"],EVOLVING:["进化中","#1f5f9e"],
                CANCELLED:["已取消","#8a97a4"],INTERRUPTED:["已中断","#8a97a4"],CREATED:["已创建","#8a97a4"],BUDGET_EXCEEDED:["超预算","#a8433a"]};
    host.innerHTML = '<table style="width:100%;border-collapse:collapse;font:12px/1.7 var(--mono)">' +
      '<tr><th style="text-align:left;color:#8a97a4;padding:4px 8px;border-bottom:1px solid var(--line)">状态</th>' +
      '<th style="text-align:left;color:#8a97a4;padding:4px 8px;border-bottom:1px solid var(--line)">任务</th>' +
      '<th style="text-align:left;color:#8a97a4;padding:4px 8px;border-bottom:1px solid var(--line)">时长</th>' +
      '<th style="text-align:left;color:#8a97a4;padding:4px 8px;border-bottom:1px solid var(--line)">成本</th>' +
      '<th style="text-align:left;color:#8a97a4;padding:4px 8px;border-bottom:1px solid var(--line)">产物</th></tr>' +
      runs.map(r => {
        const pair = ST[r.status] || [r.status, "#8a97a4"];
        return '<tr style="cursor:pointer" onclick="location.href=\'/run?id=' + encodeURIComponent(r.run_id) + '\'">' +
          '<td style="padding:5px 8px;border-bottom:1px solid var(--line)"><span style="color:' + pair[1] + ';font-weight:600">' + pair[0] + '</span></td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid var(--line);color:var(--ink)">' + esc((r.task||"").slice(0,52)) + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid var(--line)">' + fmtMs(r.duration_ms) + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid var(--line)">¥' + Number(r.cost_yuan||0).toFixed(3) + '</td>' +
          '<td style="padding:5px 8px;border-bottom:1px solid var(--line)">' + (r.artifacts||0) + '</td></tr>';
      }).join("") + "</table>";
  } catch (e) {   // 任何渲染异常都要可见，绝不留在"加载中…"
    host.innerHTML = '<div style="font-size:12.5px;color:var(--bad);padding:8px 0">运行中心加载失败：' + esc(String(e && e.message || e)) + '</div>';
  }
}

async function runDemo() {
  const input = $("task"); const q = input.value.trim();
  if (!q || input.disabled) return;
  input.disabled = true; $("run").disabled = true; $("err").style.display = "none";
  addUser(q);
  const bot = addBot();
  bot.scrollIntoView({ behavior: "smooth", block: "start" });
  if (!document.getElementById("prog")) {
    const pr = document.createElement("div"); pr.id = "prog"; pr.style.width = "0";
    document.body.appendChild(pr);
  } else { document.getElementById("prog").style.width = "0"; }
  $("run").textContent = "闭环运行中…";
  const t0 = performance.now(); const id = ++RUN_ID;
  try {
    const r = await jget2(API + "/api/demo", { task: q, gold: CUR_GOLD, k: 5 }, 300000);
    if (id !== RUN_ID) return;
    const stages = r.stages || [];
    const inject = (n, html) => { bot.querySelector(`[data-s="${n}"] .tl-body`).innerHTML = html; };
    setStage(bot, 1, "running"); await tick(650);
    inject(1, renderStage1(stages[0].detail, CUR_GOLD)); setStage(bot, 1, "done");
    await tick(480);
    setStage(bot, 2, "running"); await tick(560);
    inject(2, renderBandit(stages[1].detail)); setStage(bot, 2, "done");
    await tick(480);
    setStage(bot, 3, "running"); await tick(560);
    inject(3, renderStage2(stages[2].detail)); setStage(bot, 3, "done");
    await tick(480);
    setStage(bot, 4, "running"); await tick(620);
    inject(4, renderStage3(stages[3].detail, CUR_GOLD)); setStage(bot, 4, "done");
    await tick(480);
    setStage(bot, 5, "running"); await tick(700);
    const sbDet = stages[4] && stages[4].detail;
    if (sbDet) {
      const planSteps = ((stages[3] || {}).detail || {}).plan || {};
      LAST_EXEC = {
        task: q,
        step: (planSteps.steps || [])[sbDet.step_index] || { action: sbDet.action },
        skill: sbDet.skill,
        metrics: {
          code: (sbDet.code || "").length, out: (sbDet.stdout || "").length,
          files: (sbDet.artifacts || []).length,
          vf: sbDet.verification_total ? `${sbDet.verification_passed}/${sbDet.verification_total} 逐条带证据` : "无清单",
          fix: sbDet.fixed ? "触发修复 " + sbDet.n_attempts + " 次" : "一次通过",
        },
      };
    }
    inject(5, renderSandbox(sbDet, r.slug)); setStage(bot, 5, "done");
    await tick(480);
    setStage(bot, 6, "running"); await tick(560);
    inject(6, renderFeedback(stages[5].detail)); setStage(bot, 6, "done");
    await tick(420);
    setStage(bot, 7, "running"); await tick(520);
    inject(7, renderArtifacts(stages[6] && stages[6].detail)); setStage(bot, 7, "done");
    // 直接答复卡：用户问的问题在这里给出可见的回答（方案结论 + 真实执行输出）
    {
      const planDet = stages[3] && stages[3].detail;
      const approach = (planDet && planDet.plan && planDet.plan.approach) || "";
      const execDet = stages[4] && stages[4].detail;
      const stdout = (execDet && execDet.stdout) || "";
      const ans = document.createElement("div");
      ans.className = "tl-card reveal";
      ans.style.borderColor = "#cfe6d6";
      ans.innerHTML = `<h4>直接答复<span class="st" style="color:var(--ok)">来自真实执行</span></h4>` +
        `<div class="tl-body">` +
        (approach ? `<div style="margin-bottom:8px"><b style="color:var(--brand)">结论：</b>${esc(String(approach))}</div>` : "") +
        (stdout ? `<div><b style="color:var(--brand)">执行输出：</b><pre style="white-space:pre-wrap;font:11px/1.6 Consolas,monospace;color:var(--ink2);background:var(--soft);padding:8px 10px;border-radius:4px;margin-top:4px;max-height:260px;overflow:auto">${esc(stdout.slice(-1600))}</pre></div>`
                : `<div style="color:#8a97a4">本次任务未产生执行输出（方案级任务请看上方交付物）。</div>`) +
        `</div>`;
      bot.appendChild(ans);
      ans.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    const secs = (performance.now() - t0) / 1000;
    const cb = bot.querySelector(".costbar"); cb.style.display = "flex";
    cb.innerHTML = `<span>真实成本 ¥<b id="cv-${id}">0.00</b></span><span>Token <b id="tk-${id}">0</b></span><span>用时 <b>${secs.toFixed(1)}s</b></span><span>技能库 <b>${r.library_size}</b></span>`;
    rollNum(document.getElementById(`cv-${id}`), r.cost_yuan, 4);
    rollNum(document.getElementById(`tk-${id}`), r.tokens, 0);
    $("lib-n").textContent = r.library_size + " 个技能";
    $("run").textContent = "发送";
  } catch (e) {
    $("run").textContent = "发送";
    const run = bot.querySelector(".tl-item.running");
    if (run) run.className = "tl-item fail";
    const rest = bot.querySelectorAll(".tl-item:not(.done):not(.fail)");
    rest.forEach(x => (x.className = "tl-item fail"));
    $("err").style.display = "block";
    $("err").textContent = "调用失败：" + (e.message || e) + "。若提示 503 请在 .env 配置 DEEPSEEK_API_KEY；若服务未启动先运行 python run.py。";
  } finally { input.disabled = false; $("run").disabled = false; $("run").textContent = "发送"; }
}

async function jget2(url, body, t) {
  const c = new AbortController(); const to = setTimeout(() => c.abort(), t);
  try {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: c.signal });
    if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail) || r.status); }
    return await r.json();
  } finally { clearTimeout(to); }
}
$("task").addEventListener("input", () => { CUR_GOLD = []; });
boot();
loadRunCenter();
fillLiveNumbers();
