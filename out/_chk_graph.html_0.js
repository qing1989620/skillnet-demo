
const API = location.port ? location.origin : "http://127.0.0.1:8848";
const cv = document.getElementById("cv"), ctx = cv.getContext("2d");
let W = 0, H = 0, DPR = Math.min(2, window.devicePixelRatio || 1);

/* ---------------- 状态 ---------------- */
const S = {
  nodes: [], edges: [], byId: {},
  view: { x: 0, y: 0, k: 1 }, target: { x: 0, y: 0, k: 1 },
  drag: null, panning: false, hover: null, selected: null,
  paused: false, showLabel: true, onlyEvolved: false, t: 0,
};

/* ---------------- 颜色 ---------------- */
const PALETTE = ["#4a9eff","#5fd0a0","#c295f0","#f0b23a","#54c8d8","#e08a5f",
                 "#8ad05f","#d86fa8","#6f8cf0","#5fd6c0","#c0a24a","#9aa8d8",
                 "#e0a0a0","#7fc0e8","#b0c46a","#d08ad0","#7ad0a8","#a8b0e0",
                 "#e8c07a","#90d0e0","#c8a0e0","#a0c8d0"];
let domainColor = {};

/* ---------------- 物理 ---------------- */
const LINK_LEN = { depend_on: 62, compose_with: 92, similar_to: 130 };
function initPhysics() {
  const cx = 0, cy = 0;
  // 初始布点：按领域分簇，避免全挤在中心
  const domIdx = {};
  S.nodes.forEach((n, i) => {
    const di = domIdx[n.domain] ?? (domIdx[n.domain] = Object.keys(domIdx).length);
    const ang = (di / Math.max(1, Object.keys(domIdx).length)) * Math.PI * 2;
    const R = 210 + (i % 7) * 26;
    n.x = cx + Math.cos(ang) * R + (Math.random() - .5) * 60;
    n.y = cy + Math.sin(ang) * R + (Math.random() - .5) * 60;
    n.vx = 0; n.vy = 0;
    n.r = 3.4 + Math.min(9, (n.mean_reward || 0) * 11);
    n.fixed = false;
  });
}

function step() {
  const N = S.nodes, E = S.edges;
  const REP = 1500, DAMP = 0.86, CENTER = 0.006;
  // 斥力（O(n²)，90 节点无压力）
  for (let i = 0; i < N.length; i++) {
    const a = N[i];
    for (let j = i + 1; j < N.length; j++) {
      const b = N[j];
      let dx = b.x - a.x, dy = b.y - a.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 1e-4) { dx = (Math.random() - .5); dy = (Math.random() - .5); d2 = 1; }
      if (d2 > 90000) continue;                       // 远处不算，省算力
      const d = Math.sqrt(d2), f = REP / d2;
      const fx = (dx / d) * f, fy = (dy / d) * f;
      a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
    }
  }
  // 弹簧
  const src = S.byId;
  for (const e of E) {
    const a = src[e.source], b = src[e.target];
    if (!a || !b) continue;
    const L = LINK_LEN[e.type] || 100;
    let dx = b.x - a.x, dy = b.y - a.y;
    const d = Math.max(1, Math.hypot(dx, dy));
    const f = (d - L) * 0.012;
    const fx = (dx / d) * f, fy = (dy / d) * f;
    a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
  }
  // 中心引力 + 积分
  for (const n of N) {
    if (n === S.drag) continue;
    if (n.fixed) { n.vx = n.vy = 0; continue; }
    n.vx -= n.x * CENTER; n.vy -= n.y * CENTER;
    n.vx *= DAMP; n.vy *= DAMP;
    const lim = 8;
    n.x += Math.max(-lim, Math.min(lim, n.vx));
    n.y += Math.max(-lim, Math.min(lim, n.vy));
  }
}

/* ---------------- 坐标 ---------------- */
function toScreen(x, y) {
  const v = S.view;
  return [ (x + v.x) * v.k + W / 2, (y + v.y) * v.k + H / 2 ];
}
function toWorld(sx, sy) {
  const v = S.view;
  return [ (sx - W / 2) / v.k - v.x, (sy - H / 2) / v.k - v.y ];
}

/* ---------------- 绘制 ---------------- */
function draw() {
  S.t += 0.016;
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  ctx.clearRect(0, 0, W, H);

  // 视角平滑（缩放惯性）
  const v = S.view, tg = S.target;
  v.k += (tg.k - v.k) * 0.18;
  v.x += (tg.x - v.x) * 0.18;
  v.y += (tg.y - v.y) * 0.18;

  const hov = S.hover, sel = S.selected;
  const focus = sel || hov;
  const neigh = new Set();
  if (focus) {
    neigh.add(focus.id);
    for (const e of S.edges) {
      if (e.source === focus.id) neigh.add(e.target);
      if (e.target === focus.id) neigh.add(e.source);
    }
  }

  // 边
  ctx.lineCap = "round";
  for (const e of S.edges) {
    const a = S.byId[e.source], b = S.byId[e.target];
    if (!a || !b) continue;
    if (S.onlyEvolved && !(a.source !== "seed" && b.source !== "seed")) continue;
    const [x1, y1] = toScreen(a.x, a.y), [x2, y2] = toScreen(b.x, b.y);
    const hot = focus && (e.source === focus.id || e.target === focus.id);
    let color, w;
    if (e.type === "depend_on") { color = hot ? "#7dffc0" : "rgba(95,208,160,.42)"; w = hot ? 2.0 : 1.1; }
    else if (e.type === "compose_with") { color = hot ? "#8ccbff" : "rgba(74,158,255,.34)"; w = hot ? 1.8 : 0.9; }
    else { color = hot ? "#d6e2f0" : "rgba(160,180,210,.22)"; w = hot ? 1.4 : 0.7; }
    if (focus && !hot) { ctx.globalAlpha = 0.12; } else { ctx.globalAlpha = 1; }
    ctx.strokeStyle = color; ctx.lineWidth = w;
    if (e.type === "compose_with") ctx.setLineDash([5, 5]);
    else if (e.type === "similar_to") ctx.setLineDash([2, 5]);
    else ctx.setLineDash([]);
    // 高亮时连线流动
    if (hot) { ctx.lineDashOffset = -S.t * 26; }
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    ctx.setLineDash([]); ctx.lineDashOffset = 0;
  }
  ctx.globalAlpha = 1;

  // 节点
  for (const n of S.nodes) {
    if (S.onlyEvolved && n.source === "seed") continue;
    const [x, y] = toScreen(n.x, n.y);
    if (x < -60 || y < -60 || x > W + 60 || y > H + 60) continue;
    const evolved = n.source !== "seed";
    const base = evolved ? "#ff5a4d" : (domainColor[n.domain] || "#4a9eff");
    const isFocus = focus && n.id === focus.id;
    const inNeigh = !focus || neigh.has(n.id);
    // 呼吸
    const pulse = 1 + Math.sin(S.t * 1.6 + (n.x + n.y) * 0.01) * 0.05;
    const r = n.r * v.k * (isFocus ? 1.5 : pulse);

    ctx.globalAlpha = inNeigh ? 1 : 0.16;
    // 光晕
    const glow = ctx.createRadialGradient(x, y, 0, x, y, r * (isFocus ? 6 : 3.4));
    glow.addColorStop(0, base + (isFocus ? "66" : "3a"));
    glow.addColorStop(1, "transparent");
    ctx.fillStyle = glow;
    ctx.beginPath(); ctx.arc(x, y, r * (isFocus ? 6 : 3.4), 0, 6.2832); ctx.fill();
    // 实心球
    const g2 = ctx.createRadialGradient(x - r * .3, y - r * .3, 0, x, y, r);
    g2.addColorStop(0, "#ffffff"); g2.addColorStop(.35, base); g2.addColorStop(1, base + "cc");
    ctx.fillStyle = g2;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
    // 选中环
    if (isFocus) {
      ctx.strokeStyle = base; ctx.lineWidth = 1.6; ctx.globalAlpha = .9;
      ctx.beginPath(); ctx.arc(x, y, r + 6, 0, 6.2832); ctx.stroke();
    }
    // 标签延后到第二遍统一绘制（做占位防重叠）
    n._lx = x + r + 5; n._ly = y + 3.5; n._r = r; n._focus = isFocus; n._in = inNeigh;
  }
  ctx.globalAlpha = 1;

  // ---- 标签绘制：屏幕分格占位，聚焦/大节点优先，避免堆叠压字 ----
  if (S.showLabel) {
    const font = Math.max(9.5, Math.min(13, 11 * v.k));
    const CELL = 44;
    const occupied = new Set();
    const cand = [];
    for (const n of S.nodes) {
      if (S.onlyEvolved && n.source === "seed") continue;
      if (n._lx == null) continue;
      if (n._lx < -40 || n._ly < -20 || n._lx > W + 40 || n._ly > H + 20) continue;
      const rank = n._focus ? 0 : (n._in ? 1 : 2);
      cand.push({ n, rank });
    }
    cand.sort((a, b) => a.rank - b.rank || b.n._r - a.n._r);
    for (const { n } of cand) {
      const c0 = Math.floor(n._lx / CELL), c1 = Math.floor(n._ly / CELL);
      const k1 = c0 + "," + c1, k2 = (c0 + 1) + "," + c1;
      if (occupied.has(k1) || occupied.has(k2)) continue;
      occupied.add(k1); occupied.add(k2);
      ctx.globalAlpha = n._focus ? 1 : (n._in ? 0.92 : 0.14);
      ctx.font = `${n._focus ? 600 : 400} ${font}px "Microsoft YaHei", sans-serif`;
      ctx.fillStyle = n._focus ? "#ffffff" : "#c3d5e6";
      ctx.shadowColor = "rgba(0,0,0,.9)"; ctx.shadowBlur = 4;
      ctx.fillText(n.id, n._lx, n._ly);
      ctx.shadowBlur = 0;
    }
    ctx.globalAlpha = 1;
  }
  for (const n of S.nodes) { n._lx = null; }
}

let FRAMES = 0;
const FRAME_CAP = new URLSearchParams(location.search).get("frames");   // 供无头截图用
function loop() {
  if (!S.paused) { step(); if (FRAME_CAP) step(); }   // 截图模式每帧跑两次物理，加快收敛
  draw();
  FRAMES++;
  // 无头浏览器（Edge --screenshot）无法推进带无限 rAF 的虚拟时钟，
  // 因此支持 ?frames=N：跑够 N 帧后停住，便于自动化截图验证。
  if (FRAME_CAP && FRAMES >= +FRAME_CAP) { S.paused = true; return; }
  requestAnimationFrame(loop);
}

/* ---------------- 交互 ---------------- */
function pick(sx, sy) {
  const [wx, wy] = toWorld(sx, sy);
  let best = null, bestD = 1e9;
  const R = 18 / S.view.k;
  for (const n of S.nodes) {
    if (S.onlyEvolved && n.source === "seed") continue;
    const d = Math.hypot(n.x - wx, n.y - wy);
    const hit = Math.max(R, n.r + 6 / S.view.k);
    if (d < hit && d < bestD) { best = n; bestD = d; }
  }
  return best;
}

cv.addEventListener("mousemove", ev => {
  const sx = ev.clientX, sy = ev.clientY;
  if (S.drag) {
    const [wx, wy] = toWorld(sx, sy);
    S.drag.x = wx; S.drag.y = wy; S.drag.vx = S.drag.vy = 0; S.drag.fixed = true;
    return;
  }
  if (S.panning) {
    S.view.x += (ev.movementX || 0) / S.view.k;
    S.view.y += (ev.movementY || 0) / S.view.k;
    S.target.x = S.view.x; S.target.y = S.view.y;
    return;
  }
  const n = pick(sx, sy);
  S.hover = n;
  cv.className = n ? "onnode" : "";
  const tip = document.getElementById("tip");
  if (n) {
    tip.style.display = "block";
    tip.style.left = (sx + 14) + "px"; tip.style.top = (sy + 14) + "px";
    tip.innerHTML = `<b>${n.id}</b> · ${n.domain} · 平均奖励 ${(n.mean_reward || 0).toFixed(3)}`
      + (n.source !== "seed" ? " · 演化技能" : "");
  } else tip.style.display = "none";
});

cv.addEventListener("mousedown", ev => {
  const n = pick(ev.clientX, ev.clientY);
  if (n) { S.drag = n; cv.classList.add("dragging"); }
  else { S.panning = true; cv.classList.add("dragging"); }
});
window.addEventListener("mouseup", () => {
  if (S.drag) { S.drag.fixed = false; S.drag = null; }
  S.panning = false; cv.classList.remove("dragging");
});
cv.addEventListener("click", ev => {
  const n = pick(ev.clientX, ev.clientY);
  if (n) { selectNode(n); } else { closeCard(); }
});
cv.addEventListener("wheel", ev => {
  ev.preventDefault();
  const factor = Math.exp(-ev.deltaY * 0.0012);
  const k0 = S.target.k;
  const k1 = Math.max(0.22, Math.min(3.2, k0 * factor));
  // 以鼠标为中心缩放
  const [wx, wy] = toWorld(ev.clientX, ev.clientY);
  S.target.k = k1;
  S.target.x = (ev.clientX - W / 2) / k1 - wx;
  S.target.y = (ev.clientY - H / 2) / k1 - wy;
}, { passive: false });

function selectNode(n) {
  S.selected = n;
  const card = document.getElementById("card");
  document.getElementById("cName").textContent = n.id;
  document.getElementById("cDom").textContent =
    `${n.domain}　|　${n.source === "seed" ? "种子技能" : "演化技能（G" + (n.generation || 0) + "）"}`;
  const q = n.quality || {};
  const st = n.stats || {};
  const tot = st.exec_total || 0;
  const execLine = tot
    ? `沙箱执行 <b>${tot}</b> 次 · 成功 <b style="color:${(st.exec_ok || 0) / tot >= .7 ? "#5fd0a0" : "#f0b23a"}">${st.exec_ok || 0}</b>`
      + (st.exec_fix ? ` · 修复后成功 <b>${st.exec_fix}</b>` : "")
      + (st.exec_fail ? ` · 失败 <b style="color:#ff5a4d">${st.exec_fail}</b>` : "")
      + "<br>"
    : "";
  document.getElementById("cKv").innerHTML =
    `平均奖励 <b>${(n.mean_reward || 0).toFixed(3)}</b>　·　被调用 <b>${n.pulls || 0}</b> 次<br>`
    + execLine
    + `质量：安全性 <b>${q.safety || "—"}</b> · 完整性 <b>${q.completeness || "—"}</b> · 可执行性 <b>${q.executability || "—"}</b>`;
  const rels = n.relations || [];
  document.getElementById("cRel").innerHTML = rels.length
    ? "关联技能：" + rels.map(r => `<span>${r[0]} → ${r[1]}</span>`).join("")
    : "";
  card.classList.add("show");
}
function closeCard() {
  S.selected = null;
  document.getElementById("card").classList.remove("show");
}

document.getElementById("btnReset").onclick = () => {
  S.target.x = S.view.x = 0; S.target.y = S.view.y = 0; S.target.k = S.view.k = 1;
  initPhysics(); closeCard();
};
document.getElementById("btnPause").onclick = e => {
  S.paused = !S.paused;
  e.target.textContent = S.paused ? "继续物理" : "暂停物理";
  e.target.classList.toggle("on", S.paused);
};
document.getElementById("btnLabel").onclick = e => {
  S.showLabel = !S.showLabel; e.target.classList.toggle("on", S.showLabel);
};
document.getElementById("btnEvolved").onclick = e => {
  S.onlyEvolved = !S.onlyEvolved; e.target.classList.toggle("on", S.onlyEvolved);
};

/* ---------------- 启动 ---------------- */
function resize() {
  W = window.innerWidth; H = window.innerHeight;
  cv.width = W * DPR; cv.height = H * DPR;
  cv.style.width = W + "px"; cv.style.height = H + "px";
}
window.addEventListener("resize", resize);

(async function boot() {
  resize();
  let data;
  try {
    const r = await fetch(API + "/api/graph");
    data = await r.json();
  } catch (e) {
    document.getElementById("load").textContent = "加载失败：请确认服务已启动（python run.py）";
    return;
  }
  // 技能详情（质量/关系）在 /api/skills 里
  let detail = {};
  try {
    const s = await (await fetch(API + "/api/skills")).json();
    for (const it of (s.skills || [])) detail[it.name] = it;
  } catch (e) {}

  for (const n of data.nodes) {
    const d = detail[n.id] || {};
    S.nodes.push({ ...n, quality: d.quality, relations: d.relations });
  }
  S.edges = data.edges;
  S.byId = Object.fromEntries(S.nodes.map(n => [n.id, n]));

  const doms = [...new Set(S.nodes.map(n => n.domain))];
  doms.forEach((d, i) => domainColor[d] = PALETTE[i % PALETTE.length]);
  document.getElementById("nN").textContent = S.nodes.length;
  document.getElementById("nE").textContent = S.edges.length;
  document.getElementById("nD").textContent = doms.length;

  initPhysics();
  document.getElementById("load").style.display = "none";
  loop();
})();

/* 自检项（仅 selftest 模式读取） */
window.__SELFTEST__ = function(){ return {
  "canvas存在": !!document.querySelector("canvas"),
  "星图已加载节点": typeof window.__GRAPHN__ === "number" && window.__GRAPHN__ > 0
}; };
