
/* ================= HERO · 真实技能星图（数据来自 /api/graph，非插画） ================= */
(function () {
  const box = document.getElementById("heroNet");
  const cv = document.getElementById("netcv");
  const tip = document.getElementById("nettip");
  const legendEl = document.getElementById("netlegend");
  if (!box || !cv) return;
  const ctx = cv.getContext("2d");
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const PALETTE = ["#24557a", "#2e7d4f", "#b0783a", "#7a4a78", "#38788c", "#8c5a3a", "#5a6e3a", "#4a5a8c", "#a8433a", "#6b7b8c"];
  let W = 0, H = 0, DPR = 1;
  let nodes = [], edges = [], adj = new Map();     // id -> [{other, type}]
  let alpha = 0, hover = null, drag = null, dragMoved = false, focusSet = null;
  let visible = true, inited = false;

  function resize() {
    const r = box.getBoundingClientRect();
    DPR = window.devicePixelRatio || 1;
    W = r.width; H = r.height;
    cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  window.addEventListener("resize", () => { resize(); });

  const hash = s => { let h = 0; for (const c of s) h = ((h * 31 + c.charCodeAt(0)) >>> 0); return h; };
  const colorOf = (() => { const m = new Map(); return d => { if (!m.has(d)) m.set(d, PALETTE[hash(d) % PALETTE.length]); return m.get(d); }; })();

  async function load() {
    try {
      const [g, st] = await Promise.all([
        fetch(API + "/api/graph").then(r => r.json()),
        fetch(API + "/api/stats").then(r => r.json()).catch(() => ({}))
      ]);
      edges = (g.edges || []).map(e => ({ s: e.source, t: e.target }));
      const domCount = {};
      nodes = (g.nodes || []).map(n => ({
        id: n.id, dom: n.domain || "其他", ev: n.source !== "seed" || (n.generation || 0) > 0,
        deg: 0, reward: n.mean_reward, pulls: n.pulls || 0,
        x: 0, y: 0, vx: 0, vy: 0, fixed: false
      }));
      const byIdL = new Map(nodes.map(n => [n.id, n]));
      edges = edges.filter(e => byIdL.has(e.s) && byIdL.has(e.t));
      idx.clear(); nodes.forEach((n, i) => idx.set(n.id, i));
      for (const e of edges) {
        byIdL.get(e.s).deg++; byIdL.get(e.t).deg++;
        if (!adj.has(e.s)) adj.set(e.s, []); adj.get(e.s).push(e.t);
        if (!adj.has(e.t)) adj.set(e.t, []); adj.get(e.t).push(e.s);
      }
      // 初始位置：按领域聚拢在圆周附近
      const doms = [...new Set(nodes.map(n => n.dom))];
      doms.forEach((d, i) => {
        const a = (i / doms.length) * Math.PI * 2;
        const cx = W / 2 + Math.cos(a) * W * 0.28, cy = H / 2 + Math.sin(a) * H * 0.30;
        domCount[d] = 0;
        nodes.filter(n => n.dom === d).forEach(n => {
          n.x = cx + (Math.random() - 0.5) * 90; n.y = cy + (Math.random() - 0.5) * 90; domCount[d]++;
        });
      });
      // 指标数字（editorial count-up）
      const stats = st && typeof st === "object" ? st : {};
      const domN = typeof stats.domains === "number" ? stats.domains
        : (stats.domains && typeof stats.domains === "object" ? Object.keys(stats.domains).length : doms.length);
      const evN = typeof stats.evolved === "number" ? stats.evolved : nodes.filter(n => n.ev).length;
      roll($("hm-skills"), nodes.length); roll($("hm-edges"), edges.length);
      roll($("hm-evolved"), evN); roll($("hm-domains"), domN);
      // 图例：前 5 大领域 + 进化标记
      const top = Object.entries(domCount).sort((a, b) => b[1] - a[1]).slice(0, 5);
      legendEl.innerHTML = top.map(([d, c]) =>
        `<span><i style="background:${colorOf(d)}"></i>${d} ${c}</span>`).join("")
        + `<span><i class="ev"></i>进化技能 ${evN}</span>`;
      inited = true; alpha = REDUCED ? 0 : 1;
      pickBig();
      if (REDUCED) { for (let i = 0; i < 320; i++) step(1); draw(); }
      else if (!tick.raf) tick.raf = requestAnimationFrame(tick);
    } catch (e) {
      ctx.fillStyle = "#8a97a4"; ctx.font = "12px Microsoft YaHei"; ctx.textAlign = "center";
      ctx.fillText("星图数据加载失败（服务未启动？）", W / 2, H / 2);
    }
  }

  function roll(el, target) {
    if (!el) return;
    if (REDUCED) { el.textContent = target; return; }
    const t0 = performance.now(), dur = 950;
    (function f(t) {
      const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * e);
      if (p < 1) requestAnimationFrame(f);
    })(t0);
  }

  function step(dt) {
    const a = Math.max(alpha, 0.02);
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      // 斥力（栅格加速足够：98 节点 O(n²) 无压力）
      for (let j = i + 1; j < nodes.length; j++) {
        const o = nodes[j];
        let dx = n.x - o.x, dy = n.y - o.y, d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; d2 = 1; }
        if (d2 > 36000) continue;                 // 远距离截断
        const f = 2400 / d2 * a, d = Math.sqrt(d2);
        const fx = dx / d * f, fy = dy / d * f;
        n.vx += fx; n.vy += fy; o.vx -= fx; o.vy -= fy;
      }
      // 向心力
      n.vx += (W / 2 - n.x) * 0.0035 * a; n.vy += (H / 2 - n.y) * 0.0055 * a;
    }
    // 弹簧
    for (const e of edges) {
      const s = byId(e.s), t = byId(e.t); if (!s || !t) continue;
      const dx = t.x - s.x, dy = t.y - s.y, d = Math.max(1, Math.hypot(dx, dy));
      const f = (d - 62) * 0.028 * a, fx = dx / d * f, fy = dy / d * f;
      s.vx += fx; s.vy += fy; t.vx -= fx; t.vy -= fy;
    }
    // 积分
    for (const n of nodes) {
      if (n === drag || n.fixed) { n.vx = n.vy = 0; continue; }
      n.vx *= 0.86; n.vy *= 0.86;
      n.x = Math.max(14, Math.min(W - 14, n.x + Math.max(-24, Math.min(24, n.vx))));
      n.y = Math.max(14, Math.min(H - 14, n.y + Math.max(-24, Math.min(24, n.vy))));
    }
    alpha *= 0.991;
  }
  const idx = new Map();
  function byId(id) { return nodes[idx.get(id)]; }

  const big = new Set();                               // 常显标签：度数前 14
  function pickBig() { [...nodes].sort((a, b) => b.deg - a.deg).slice(0, 10).forEach(n => big.add(n.id)); }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const dimAll = focusSet !== null;
    // 边
    for (const e of edges) {
      const s = byId(e.s), t = byId(e.t); if (!s || !t) continue;
      const hot = hover && (e.s === hover.id || e.t === hover.id);
      const inF = dimAll && (focusSet.has(e.s) && focusSet.has(e.t));
      let aLine = hot ? 0.85 : (focusSet ? (inF ? 0.5 : 0.05) : 0.14);
      if (focusSet && !inF && !hot) aLine = 0.05;
      ctx.strokeStyle = hot ? "rgba(36,85,122," + aLine + ")" : "rgba(34,48,62," + aLine + ")";
      ctx.lineWidth = hot ? 1.4 : 0.8;
      ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(t.x, t.y); ctx.stroke();
    }
    // 节点
    for (const n of nodes) {
      const isH = hover === n;
      const dim = (focusSet && !focusSet.has(n.id)) || (hover && hover !== n && !(adj.get(hover.id) || []).includes(n.id));
      const r = 3 + Math.min(7, n.deg * 0.55) + (isH ? 2.2 : 0);
      ctx.globalAlpha = dim ? 0.13 : 1;
      ctx.fillStyle = colorOf(n.dom);
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 6.2832); ctx.fill();
      if (n.ev) { ctx.strokeStyle = "rgba(201,138,45,.85)"; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.arc(n.x, n.y, r + 2.4, 0, 6.2832); ctx.stroke(); }
      if (isH) { ctx.strokeStyle = "rgba(36,85,122,.9)"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(n.x, n.y, r + 5, 0, 6.2832); ctx.stroke(); }
      ctx.globalAlpha = 1;
    }
    // 标签（LOD：常显前 14 + 悬停邻域）
    ctx.font = "9.5px 'Microsoft YaHei'"; ctx.textAlign = "left"; ctx.textBaseline = "middle";
    for (const n of nodes) {
      const show = big.has(n.id) || (hover && (n === hover || (adj.get(hover.id) || []).includes(n.id))) || (focusSet && focusSet.has(n.id));
      if (!show) continue;
      const dim = (focusSet && !focusSet.has(n.id)) || (hover && hover !== n && !(adj.get(hover.id) || []).includes(n.id));
      ctx.globalAlpha = dim ? 0.15 : 0.92;
      ctx.fillStyle = "#44576b";
      if (n.x > W - 130) { ctx.textAlign = "right"; ctx.fillText(n.id, n.x - 9, n.y); ctx.textAlign = "left"; }
      else ctx.fillText(n.id, n.x + 9, n.y);
      ctx.globalAlpha = 1;
    }
  }

  function tick() {
    tick.raf = 0;
    if (!visible || !inited) return;              // 恢复时由 IntersectionObserver 重新拉起
    if (alpha > 0.003) { step(1); draw(); tick.drawn = false; }
    else if (!tick.drawn) { draw(); tick.drawn = true; }
    tick.raf = requestAnimationFrame(tick);
  }

  function pos(ev) { const r = cv.getBoundingClientRect(); return { x: ev.clientX - r.left, y: ev.clientY - r.top }; }
  function pick(p) {
    let best = null, bd = 1e9;
    for (const n of nodes) { const d = Math.hypot(n.x - p.x, n.y - p.y); if (d < bd && d < 16) { bd = d; best = n; } }
    return best;
  }
  cv.addEventListener("pointermove", ev => {
    const p = pos(ev);
    if (drag) { drag.x = p.x; drag.y = p.y; drag.vx = drag.vy = 0; dragMoved = true; alpha = Math.max(alpha, 0.3); draw(); return; }
    const n = pick(p);
    if (n !== hover) { hover = n; cv.style.cursor = n ? "pointer" : "crosshair"; if (!n) tip.style.opacity = 0; draw(); }
    if (n) {
      tip.innerHTML = `<b>${n.id}</b><br>领域 ${n.dom} · ${n.deg} 条关系<br>${n.ev ? "进化技能 · " : ""}质量分 ${n.reward != null ? n.reward.toFixed(2) : "—"} · 调用 ${n.pulls} 次`;
      const br = box.getBoundingClientRect();
      tip.style.left = Math.min(p.x + 14, br.width - 200) + "px";
      tip.style.top = Math.min(p.y + 12, br.height - 70) + "px";
      tip.style.opacity = 1;
    }
  });
  cv.addEventListener("pointerdown", ev => {
    const p = pos(ev); const n = pick(p);
    if (n) { drag = n; dragMoved = false; cv.setPointerCapture(ev.pointerId); }
  });
  cv.addEventListener("pointerup", ev => {
    if (drag && !dragMoved) {                       // 点击：聚焦邻域
      if (focusSet && focusSet.has(drag.id)) focusSet = null;
      else { focusSet = new Set([drag.id, ...(adj.get(drag.id) || [])]); }
      alpha = Math.max(alpha, 0.25); draw();
    }
    drag = null;
  });
  cv.addEventListener("pointerleave", () => { hover = null; tip.style.opacity = 0; draw(); });

  new IntersectionObserver(es => {
    visible = es[0].isIntersecting;
    if (visible && inited && !REDUCED && !tick.raf) tick.raf = requestAnimationFrame(tick);
  }, { threshold: 0.02 }).observe(box);

  // 对外 API：Run 事件驱动「候选技能点亮」（WOW-1 钩子）
  window.HeroNet = {
    highlight(ids) {
      if (!inited || !ids || !ids.length) return;
      focusSet = new Set(ids.filter(id => idx.has(id) || nodes.some(n => n.id === id)));
      alpha = Math.max(alpha, 0.35); tick.drawn = false; if (REDUCED) draw();
    },
    clear() { focusSet = null; tick.drawn = false; if (REDUCED) draw(); }
  };

  // 数据加载
  resize();
  load();
})();
