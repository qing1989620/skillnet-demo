
const API = "";
const LS_KEY = "skillnet_chat_sessions_v1";
let SESSIONS = [], CUR = null, busy = false;
const PHASES = [["retrieval","检索对比"],["ranking","策略选择"],["orchestration","任务编排"],
                ["dag","DAG 收束"],["plan","研究方案"],["exec","真实执行"],["final","验收与进化"]];
const CHIPS = [
  "解释一下费马大定理",
  "对一批剂量-存活率实验数据做清洗并做剂量-反应分析",
  "分析学生考试成绩，找出薄弱环节并给出复习建议表"
];

/* ---------- 基础工具 ---------- */
const esc = s => String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
const fmtMs = ms => ms == null ? "—" : (ms >= 1000 ? (ms/1000).toFixed(1) + "s" : Math.max(0, Math.round(ms)) + "ms");
const fmtTime = ts => { const d = new Date(ts);
  return `${d.getMonth()+1}-${String(d.getDate()).padStart(2,"0")} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`; };
const jget = (u, t=10000) => Promise.race([fetch(u).then(r => r.json()),
  new Promise((_, rej) => setTimeout(() => rej(new Error("超时")), t))]);

/* 轻量 Markdown → HTML（先转义再解析标记） */
function mdToHtml(md) {
  const inline = s => s.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
  const src = esc(String(md || "")).replace(/```(\w*)\n?([\s\S]*?)```/g,
    (_m, _l, code) => "\u0000PRE" + btoa(unescape(encodeURIComponent(code))) + "\u0000");
  return src.split(/\n{2,}/).map(b => {
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
    if (/^>\s?/m.test(t)) return `<blockquote>${inline(t.split("\n").map(l => l.replace(/^>\s?/, "")).join("<br>"))}</blockquote>`;
    if (t.split("\n").every(l => !l.trim() || /^\s*[-*]\s/.test(l)))
      return "<ul>" + t.split("\n").filter(l => l.trim()).map(l => `<li>${inline(l.replace(/^\s*[-*]\s/, ""))}</li>`).join("") + "</ul>";
    if (t.split("\n").every(l => !l.trim() || /^\s*\d+[.、)]\s/.test(l)))
      return "<ol>" + t.split("\n").filter(l => l.trim()).map(l => `<li>${inline(l.replace(/^\s*\d+[.、)]\s/, ""))}</li>`).join("") + "</ol>";
    return `<p>${inline(t).replace(/\n/g, "<br>")}</p>`;
  }).filter(Boolean).join("");
}

/* ---------- 会话存储 ---------- */
function loadSessions(){
  try { SESSIONS = JSON.parse(localStorage.getItem(LS_KEY) || "[]"); } catch { SESSIONS = []; }
  if (!Array.isArray(SESSIONS)) SESSIONS = [];
}
function saveSessions(){ try { localStorage.setItem(LS_KEY, JSON.stringify(SESSIONS)); } catch {} }
function cur(){ return SESSIONS.find(s => s.id === CUR) || null; }
function newSession(){
  if (busy) return;
  const s = { id: "s" + Date.now(), title: "", created: Date.now(), turns: [] };
  SESSIONS.unshift(s); CUR = s.id; saveSessions(); renderSidebar(); renderMain();
  document.getElementById("q").focus();
}
function openSession(id){ if (busy) return; CUR = id; renderSidebar(); renderMain(); }

/* ---------- 左栏 ---------- */
function renderSidebar(){
  const host = document.getElementById("slist");
  if (!SESSIONS.length){
    host.innerHTML = '<div style="padding:14px;font-size:12px;color:#8a97a4;line-height:1.9">还没有对话。<br>点上方「新建对话」开始。</div>';
    return;
  }
  host.innerHTML = SESSIONS.map(s => `
    <div class="sitem ${s.id === CUR ? "on" : ""}" onclick="openSession('${s.id}')">
      <div class="t">${esc(s.title || "（新对话）")}</div>
      <div class="m"><span>${s.turns.length} 问</span><span>${fmtTime(s.created)}</span></div>
    </div>`).join("");
}

/* ---------- 右栏渲染 ---------- */
function renderMain(){
  const s = cur(), host = document.getElementById("msgs");
  document.getElementById("sess-title").textContent = s && s.title ? s.title : "新对话";
  const last = s && s.turns.filter(t => t.run_id).slice(-1)[0];
  const link = document.getElementById("last-run");
  if (last){ link.style.display = ""; link.href = `/run?id=${encodeURIComponent(last.run_id)}`; }
  else link.style.display = "none";
  if (!s || !s.turns.length){
    host.innerHTML = '<div class="empty">在上方输入问题，调用完整 Agent 框架。<br>' +
      '执行完成后这里会给出：AI 回复 · 每一步的执行解释 · 本次任务总结（SkillNet 的角色与技能库成长）。<br>' +
      '同一个对话里可以继续追问，系统会自动带上上下文。</div>';
    return;
  }
  host.innerHTML = s.turns.map((t, i) => turnHTML(t, i)).join("");
  s.turns.forEach((t, i) => { if (t.run_id && !t._loaded) hydrateTurn(i, t.run_id); });
  host.scrollTop = host.scrollHeight;
}

function turnHTML(t, i){
  return `<div class="turn" id="turn-${i}">
    <div class="q"><div class="who">你</div><div class="txt">${esc(t.q)}</div></div>
    <div class="acard" id="acard-${i}">${t.body || '<span style="color:#8a97a4">排队中…</span>'}</div>
  </div>`;
}

function phaseBarHTML(){
  return '<div class="phases">' + PHASES.map(([k, label]) =>
    `<span class="ph" id="ph-${k}"><i></i>${label}<b id="pht-${k}" style="font-weight:400;color:#aab6c1"></b></span>`).join("") +
    '</div><div class="sub" id="ph-sub">Run 创建后实时显示各阶段状态</div>';
}
function setPhase(k, state, ms, i){
  const wrap = document.getElementById(`ph-${k}-${i}`) || document.getElementById(`ph-${k}`);
  const dot = wrap && wrap.querySelector("i"), tp = wrap && wrap.querySelector("b");
  if (!wrap) return;
  wrap.className = "ph " + (state === "run" ? "on" : state === "done" ? "ok" : state === "fail" ? "no" : "");
  if (ms != null && tp) tp.textContent = " " + (ms/1000).toFixed(1) + "s";
}
const setSub = (i, txt) => { const el = document.getElementById(`ph-sub-${i}`) || document.getElementById("ph-sub"); if (el) el.textContent = txt; };

/* 步骤明细（含时间轴条） */
function stepCardHTML(s, fin, i){
  const map = { done:["完成","#2e7d4f"], failed:["失败","#a8433a"], skipped:["已跳过","#8a97a4"],
                running:["执行中","#24557a"], pending:["等待","#8a97a4"] };
  const pair = map[s.status] || [s.status, "#8a97a4"];
  const fixed = s.status === "done" && (s.n_attempts || 1) > 1;
  const L = [];
  L.push(`<div><b>做什么：</b>${esc(s.action || "")}</div>`);
  if (s.skill) L.push(`<div><b>使用技能：</b><code>${esc(s.skill)}</code></div>`);
  L.push(`<div><b>执行过程：</b>共 ${s.n_attempts || 1} 次尝试 · 耗时 ${fmtMs(s.duration_ms)}${fixed ? "（前几次失败，已自动修复）" : ""}</div>`);
  const fails = (s.attempts || []).filter(a => !a.ok);
  if (fails.length) L.push(`<div style="margin-left:14px;color:#8a6d3b">失败详情：${fails.map(a => `第 ${a.n} 次 ${esc(a.error_kind || "错误")}（${esc((a.stderr || "").slice(-120))}）`).join("；")}</div>`);
  if ((s.checks || []).length){
    const ok = s.checks.filter(c => c.passed).length;
    L.push(`<div style="margin-left:14px"><b>程序化验收：</b>${ok}/${s.checks.length} 通过${ok < s.checks.length ? ` — 未通过：${s.checks.filter(c => !c.passed).slice(0,3).map(c => esc(c.name)).join("、")}` : ""}</div>`);
  }
  if ((s.artifacts || []).length) L.push(`<div style="margin-left:14px"><b>产出物：</b>${s.artifacts.map(a => `<a href="${API}/api/runs/${encodeURIComponent(fin.run_id)}/artifacts/${encodeURIComponent(a.name)}" target="_blank" style="color:var(--brand2)">${esc(a.name)}</a>（${(a.bytes/1024).toFixed(1)} KB）`).join("、")}</div>`);
  if ((s.inputs || []).length) L.push(`<div style="margin-left:14px;color:#8a97a4">读取的上游产物：${esc(s.inputs.join("、"))}</div>`);
  if (s.status === "skipped" && s.verify_skip_reason) L.push(`<div style="margin-left:14px;color:#8a97a4">${esc(s.verify_skip_reason)}</div>`);
  if (s.status === "failed" && s.error) L.push(`<div style="margin-left:14px;color:var(--bad)">最终错误：${esc(String(s.error).slice(0,200))}</div>`);
  const okAtt = (s.attempts || []).filter(a => a.ok).slice(-1)[0];
  if (okAtt && (okAtt.stdout || "").trim()) L.push(`<div style="margin-left:14px"><b>输出摘要：</b><pre>${esc(okAtt.stdout.slice(-800))}</pre></div>`);
  // 时间轴条（真实 started_at/ended_at）
  const t0 = fin.started_at_ms || (fin.steps?.[0]?.started_at_ms) || 0;
  const total = Math.max(1, fin.duration_ms || 0);
  if (t0 && s.started_at_ms && s.duration_ms > 0){
    const left = Math.max(0, Math.min(99, (s.started_at_ms - t0) / total * 100));
    const w = Math.max(1, Math.min(100 - left, s.duration_ms / total * 100));
    L.push(`<div style="margin-left:14px"><div style="position:relative;height:6px;background:var(--soft);border-radius:3px;overflow:hidden"><div style="position:absolute;left:${left}%;width:${w}%;height:100%;background:${pair[1]};opacity:.72"></div></div><div style="font-size:10.5px;color:#8a97a4;margin-top:2px">时间轴：第 ${((s.started_at_ms - t0)/1000).toFixed(1)}s 开始（占 ${w.toFixed(0)}%）</div></div>`);
  }
  return `<div class="stepcard" style="border-left-color:${pair[1]}">
    <div class="sh"><b>Step ${s.idx+1} · ${esc(s.skill || "通用")}</b><span style="color:${pair[1]}">${pair[0]}${fixed ? "（修复后成功）" : ""}</span></div>
    <div class="body">${L.join("")}</div></div>`;
}

/* Agent 回复 / 任务总结（与首页同一套渲染） */
const replyCardHTML = text => `<div class="ai-reply"><div class="rp-head"><i></i>Agent 最终回复` +
  `<span class="rp-meta">基于本次真实执行数据生成</span></div><div class="rp-body">${mdToHtml(text)}</div></div>`;

function taskSummaryHTML(fin){
  const imp = (fin.staged || {}).skill_impact;
  if (!imp) return "";
  const s = imp.summary || {}, steps = fin.steps || [];
  const nFix = steps.filter(x => x.status === "done" && (x.n_attempts || 1) > 1).length;
  const chkOk = steps.reduce((a, x) => a + (x.checks || []).filter(c => c.passed).length, 0);
  const chkAll = steps.reduce((a, x) => a + (x.checks || []).length, 0);
  const delta = s.library_delta || 0, evoUp = (imp.evolved_after || 0) - (imp.evolved_before || 0);
  const rows = (imp.touched || []).slice(0, 8).map(x =>
    `<tr><td><code>${esc(x.name)}</code></td><td>${Object.entries(x.delta || {}).map(([k, v]) =>
      `${k} <b class="up">${v > 0 ? "+" : ""}${v}</b>`).join(" · ") || "—"}</td></tr>`).join("");
  const news = (imp.new_skills || []).map(n =>
    `<div class="newskill"><b style="color:var(--ok)">新增技能：<code>${esc(n.name)}</code></b>` +
    `<span style="color:#8a97a4"> · 第 ${n.generation} 代 · 领域 ${esc(n.domain || "—")}` +
    (n.parents && n.parents.length ? ` · 衍生自 ${esc(n.parents.join("、"))}` : "") + `</span>` +
    (n.capability ? `<div style="margin-top:5px;color:var(--ink2)">${esc(n.capability)}</div>` : "") + `</div>`).join("");
  return `<div class="task-summary">
    <div class="ts-head"><i></i>本次任务总结 · SkillNet 扮演的角色<span class="rp-meta">数据来自技能统计前后差值</span></div>
    <div class="ts-role">它不是执行者，而是这个 Agent 的<b>能力运维层</b>：本次任务里它完成了「找到能力 → 挑出能力 → 编排能力 → 验收产物 → 沉淀能力」五件事。</div>
    <div class="ts-steps">
      <div class="ts-step"><b>① 检索</b><span>从 ${imp.library_before} 个技能中三档检索（BM25 / 语义 / 关系图扩展）定位候选</span></div>
      <div class="ts-step"><b>② 选择</b><span>LinUCB 按任务条件化排序，最终采用 ${s.used_n || 0} 个技能：${esc((imp.used || []).slice(0,8).join("、") || "通用执行")}</span></div>
      <div class="ts-step"><b>③ 编排</b><span>按技能依赖边生成执行 DAG，${steps.length} 步真实执行（含修复后的 ${nFix} 步）</span></div>
      <div class="ts-step"><b>④ 验收</b><span>程序化验收 ${chkOk}/${chkAll} 通过</span></div>
      <div class="ts-step"><b>⑤ 沉淀</b><span>${(imp.new_skills || []).length ? `蒸馏并准入 ${(imp.new_skills || []).length} 个新技能` : "本次未产生通过准入的新技能（相似度/质量闸拦截）"}</span></div>
    </div>
    <div class="ts-metrics">
      <div><b>${imp.library_before} → ${imp.library_after}</b>技能库规模${delta ? `（+${delta}）` : ""}</div>
      <div><b>${imp.evolved_before} → ${imp.evolved_after}</b>演化技能${evoUp ? `（+${evoUp}）` : ""}</div>
      <div><b>${s.updated_n || 0}</b>个技能被本次任务更新</div>
    </div>
    ${rows ? `<div class="ts-sec">── 技能资产更新（真实统计变化）──</div>
      <table><tr><th style="width:40%">技能</th><th>变化</th></tr>${rows}</table>` : ""}
    ${news ? `<div class="ts-sec">── 能力沉淀（本次为 Agent 长出的新能力）──</div>${news}` : ""}
  </div>`;
}

/* 完整结果渲染（实时流结束后 / 历史加载） */
function resultHTML(fin){
  const steps = fin.steps || [];
  const nDone = steps.filter(s => s.status === "done").length;
  const nFix = steps.filter(s => s.status === "done" && (s.n_attempts || 1) > 1).length;
  const nFail = steps.filter(s => s.status === "failed").length;
  const nSkip = steps.filter(s => s.status === "skipped").length;
  const cp = (fin.staged || {}).critical_path;
  const cpTxt = cp ? `关键路径 ${cp.steps.map(i => "Step " + (i+1)).join(" → ")}（${(cp.ms/1000).toFixed(1)}s / 总 ${(fin.duration_ms/1000).toFixed(1)}s）` : "";
  const sum = `<div class="runsum"><b style="color:var(--brand)">Run Summary</b> · ` +
    `${fin.status === "COMPLETED" ? "已完成" : fin.status === "PARTIAL" ? "部分完成" : fin.status} · ` +
    `¥${Number(fin.cost_yuan || 0).toFixed(3)} · ${(fin.duration_ms/1000).toFixed(1)}s<br>` +
    `步骤 ${steps.length}：一次通过 <b style="color:var(--ok)">${nDone - nFix}</b> · 修复后成功 <b style="color:var(--warn)">${nFix}</b> · 失败 <b style="color:var(--bad)">${nFail}</b> · 跳过 <b>${nSkip}</b>` +
    (cpTxt ? `<br><span style="color:#8a97a4">${cpTxt}</span>` : "") +
    ` · <a href="/run?id=${encodeURIComponent(fin.run_id)}" target="_blank">完整面板 →</a></div>`;
  const reply = (fin.staged || {}).final_reply;
  return sum +
    `<div class="toggle" onclick="toggleDetail(this)">查看执行详情（${steps.length} 步 · 逐步解释与产物）▾</div>
     <div class="detail" style="display:none">
       <div class="dtabs">
         <span class="on" onclick="dtab(this,'steps')">每一步执行</span>
         <span onclick="dtab(this,'raw')">原始事件</span>
       </div>
       <div class="dsec on" data-sec="steps">${steps.map(s => stepCardHTML(s, fin)).join("") || "<div style='color:#8a97a4'>无步骤</div>"}</div>
       <div class="dsec" data-sec="raw"><pre style="max-height:280px;overflow:auto;font:11px/1.6 var(--mono);background:var(--soft);padding:10px;border-radius:4px">${esc(((fin.events || []).map(e => e.type).join(" → ")) || "（无事件记录）")}</pre></div>
     </div>` +
    (reply ? replyCardHTML(reply) : "") +
    taskSummaryHTML(fin);
}
function toggleDetail(el){
  const d = el.nextElementSibling;
  const open = d.style.display !== "none";
  d.style.display = open ? "none" : "block";
  el.textContent = el.textContent.replace(open ? "▾" : "▴", open ? "▴" : "▾");
}
function dtab(el, sec){
  el.parentNode.querySelectorAll("span").forEach(s => s.classList.remove("on"));
  el.classList.add("on");
  const host = el.closest(".detail");
  host.querySelectorAll(".dsec").forEach(s => s.classList.toggle("on", s.dataset.sec === sec));
}

async function hydrateTurn(i, runId){
  const t = cur() && cur().turns[i]; if (!t) return;
  try {
    const fin = await jget(`${API}/api/runs/${encodeURIComponent(runId)}`, 15000);
    t._loaded = true; t.status = fin.status;
    const box = document.getElementById(`acard-${i}`);
    if (box) box.innerHTML = resultHTML(fin);
  } catch (e) {
    const box = document.getElementById(`acard-${i}`);
    if (box) box.innerHTML = `<span style="color:var(--ink3)">无法加载该次运行的详情（${esc(e.message || e)}）</span>`;
  }
}

/* ---------- 提问（含追问上下文） ---------- */
async function submitQ(){
  if (busy) return;
  const ta = document.getElementById("q");
  const q = ta.value.trim(); if (!q) return;
  if (!cur()) newSession();
  const s = cur();
  busy = true;
  document.getElementById("send").disabled = true;
  document.getElementById("send").textContent = "运行中…";

  const history = s.turns.filter(t => t.q !== q || true)
    .map(t => ({ q: t.q, a: t.reply_digest || "" })).slice(-3);
  const turn = { q, run_id: null, ts: Date.now(), status: "running", body: phaseBarHTML() };
  s.turns.push(turn);
  if (!s.title) s.title = q.slice(0, 34);
  saveSessions(); renderSidebar(); renderMain();
  const idx = s.turns.length - 1;
  ta.value = ""; ta.style.height = "46px";
  document.getElementById("msgs").scrollTop = document.getElementById("msgs").scrollHeight;

  try {
    const r = await fetch(`${API}/api/runs`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: q, k: 5, max_steps: 3, max_cost_yuan: 1.0,
                             max_seconds: 420, history })
    });
    if (!r.ok){
      const d = await r.json().catch(() => ({}));
      throw new Error(typeof d.detail === "string" ? d.detail : ("HTTP " + r.status));
    }
    const { run_id } = await r.json();
    turn.run_id = run_id; saveSessions();
    const link = document.getElementById("last-run");
    link.style.display = ""; link.href = `/run?id=${encodeURIComponent(run_id)}`;
    setSub(idx, "Run 已创建：" + run_id);
    await stream(idx, run_id);
    const fin = await jget(`${API}/api/runs/${encodeURIComponent(run_id)}`, 15000);
    turn.status = fin.status; turn._loaded = true;
    const reply = (fin.staged || {}).final_reply || "";
    turn.reply_digest = reply.replace(/[#*`>\-]/g, "").slice(0, 400);
    const box = document.getElementById(`acard-${idx}`);
    if (box) box.innerHTML = resultHTML(fin);
    saveSessions();
  } catch (e) {
    turn.status = "error";
    const box = document.getElementById(`acard-${idx}`);
    if (box) box.innerHTML = `<div class="acard err" style="margin-left:0">运行失败：${esc(e.message || e)}</div>`;
    saveSessions();
  } finally {
    busy = false;
    document.getElementById("send").disabled = false;
    document.getElementById("send").textContent = "发送";
    document.getElementById("msgs").scrollTop = document.getElementById("msgs").scrollHeight;
  }
}

async function stream(i, runId){
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
        const s = line.trim();
        if (s === "event: end") return;
        if (!s.startsWith("data: ")) continue;
        let ev; try { ev = JSON.parse(s.slice(6)); } catch { continue; }
        onEvent(i, ev);
        if (ev.type === "end") return;
      }
    }
  } catch (e) { /* 流断开：以最终状态接口为准 */ }
  finally { clearTimeout(timer); }
}

function onEvent(i, ev){
  const t = ev.type || "", d = ev.data || ev;
  const P = k => document.getElementById(`ph-${k}`);
  if (t === "retrieval.completed"){ setPhase("retrieval","done",d.duration_ms); setPhase("ranking","run");
    setSub(i, `检索完成：三档对照，候选 ${(d.selected || []).length} 个`); }
  else if (t === "ranking.completed"){ setPhase("ranking","done"); setPhase("orchestration","run"); }
  else if (t === "orchestration.completed"){ setPhase("orchestration","done"); setPhase("dag","run");
    setSub(i, `编排完成：${(d.skills || []).length} 个技能进入执行图`); }
  else if (t === "dag.ready"){ setPhase("dag","done"); setPhase("plan","run");
    setSub(i, `执行图就绪：${(d.nodes || []).length} 步（来源 ${d.workflow_source || "—"}）`); }
  else if (t === "plan.created"){ setPhase("plan","done",d.duration_ms); setPhase("exec","run");
    setSub(i, `方案生成：${d.steps} 步`); }
  else if (t === "step.started"){ setSub(i, `执行中：Step ${d.step + 1}`); }
  else if (t === "step.attempt" && d.ok === false){ setSub(i, `Step ${d.step + 1} 第 ${d.attempt} 次失败，准备修复`); }
  else if (t === "execution.finished"){ setPhase("exec", d.failed > 0 ? "fail" : "done"); setPhase("final","run"); }
  else if (t === "evolution.proposed"){ setSub(i, d.accepted ? `技能蒸馏：已准入 ${d.name} · 库规模 ${d.library_size}` : "技能蒸馏：本次未准入"); }
  else if (t === "run.reply"){ setPhase("final","done"); setSub(i, "Agent 最终回复已生成"); }
  else if (t === "run.failed" || t === "run.budget_exceeded"){
    PHASES.forEach(([k]) => { if (P(k) && P(k).className !== "ph ok") setPhase(k, "fail"); });
    setSub(i, "运行中断：" + String(d.reason || t));
  }
}

/* ---------- 启动 ---------- */
document.getElementById("chips").innerHTML =
  CHIPS.map(c => `<span class="chip" onclick="useChip(this)">${esc(c)}</span>`).join("");
function useChip(el){ const ta = document.getElementById("q"); ta.value = el.textContent; ta.focus(); autosize(ta); }
function autosize(ta){ ta.style.height = "46px"; ta.style.height = Math.min(150, ta.scrollHeight) + "px"; }
document.getElementById("q").addEventListener("input", e => autosize(e.target));
document.getElementById("q").addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey){ e.preventDefault(); submitQ(); }
});
loadSessions();
if (!SESSIONS.length) newSession(); else { CUR = SESSIONS[0].id; renderSidebar(); renderMain(); }

/* 自检项（仅 selftest 模式读取） */
window.__SELFTEST__ = function(){ return {
  "mdToHtml存在": typeof window.mdToHtml === "function",
  "submitQ存在": typeof window.submitQ === "function",
  "会话列表": !!document.getElementById("slist"),
  "消息区": !!document.getElementById("msgs"),
  "输入框": !!document.getElementById("q")
}; };
