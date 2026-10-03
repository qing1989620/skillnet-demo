/* ============================================================================
   SkillNet-S1 · 共享交互层（ui.js）
   所有页面统一引入。<script src="/static/assets/ui.js" defer></script>

   提供三件全局交互（都是"传达信息"的动效，不做装饰）：
     1. 滚动进度条：顶部 2px，随阅读进度生长
     2. 滚动进场：.ui-reveal / 主要内容块进入视口时淡入上移（一次性）
     3. 卡片指针微光：.ui-glow 跟随鼠标的极轻径向高亮
   另：尊重 prefers-reduced-motion（用户系统设置为减少动效时不执行）。
   ========================================================================== */
(function () {
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- 1) 滚动进度条 ---------- */
  function initProgress() {
    if (document.getElementById("ui-progress")) return;
    var bar = document.createElement("div");
    bar.id = "ui-progress";
    document.body.appendChild(bar);
    var raf = 0;
    function update() {
      raf = 0;
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      var p = max > 0 ? Math.min(1, Math.max(0, h.scrollTop / max)) : 0;
      bar.style.width = (p * 100).toFixed(2) + "%";
    }
    window.addEventListener("scroll", function () { if (!raf) raf = requestAnimationFrame(update); }, { passive: true });
    window.addEventListener("resize", update, { passive: true });
    update();
  }

  /* ---------- 2) 滚动进场 ---------- */
  function initReveal() {
    if (reduce || !("IntersectionObserver" in window)) return;
    // 自动挂载：主要区块标题 + 卡片 + 表格 + 大容器（避免手工逐个加 class）
    var auto = document.querySelectorAll(
      "section.wrap > .kicker, section.wrap > h2, section.wrap > .sub, " +
      ".pain, .kpi, .uq, .shot, .hm, .paper, .ui-card, table.vs, .ws, .shots, section.wrap > .card"
    );
    var els = [];
    Array.prototype.forEach.call(auto, function (el) {
      if (!el.classList.contains("ui-reveal")) { el.classList.add("ui-reveal"); els.push(el); }
    });
    // 同组元素错开 60ms，形成节奏（stagger）
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target;
        var idx = parseInt(el.dataset.stagger || "0", 10);
        setTimeout(function () { el.classList.add("is-in"); }, Math.min(idx * 60, 300));
        io.unobserve(el);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    // 给同一父容器内的元素编号，做 stagger
    els.forEach(function (el) {
      var sibs = el.parentNode ? Array.prototype.filter.call(el.parentNode.children, function (c) {
        return c.classList && c.classList.contains("ui-reveal");
      }) : [el];
      el.dataset.stagger = Math.min(sibs.indexOf(el), 5);
      io.observe(el);
    });
  }

  /* ---------- 3) 卡片指针微光 ---------- */
  function initGlow() {
    if (reduce) return;
    var sel = ".hm, .shot, .ui-glow, .pain, .kpi";
    document.addEventListener("pointermove", function (e) {
      var el = e.target && e.target.closest ? e.target.closest(sel) : null;
      if (!el) return;
      if (!el.classList.contains("ui-glow")) el.classList.add("ui-glow");
      var r = el.getBoundingClientRect();
      el.style.setProperty("--mx", ((e.clientX - r.left) / r.width * 100).toFixed(1) + "%");
      el.style.setProperty("--my", ((e.clientY - r.top) / r.height * 100).toFixed(1) + "%");
    }, { passive: true });
  }

  function boot() { initProgress(); initReveal(); initGlow(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  // 暴露为全局，页面可用 window.UI.reveal() 在动态内容插入后重新挂载
  window.UI = {
    reveal: function () { initReveal(); },
    progress: function () { initProgress(); }
  };
})();
