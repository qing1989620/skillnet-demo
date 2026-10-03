
/* 自检模式（?selftest=1）：收集 JS 运行时错误与关键检查，结果写入 #selftest-out 与标题。 */
(function(){
  if (!location.search.includes("selftest=1")) return;
  var errors = [];
  window.addEventListener("error", function(e){ errors.push("JS错误: " + (e.message || e.type) + " @" + (e.filename||"") + ":" + (e.lineno||0)); });
  window.addEventListener("unhandledrejection", function(e){
    var r = e.reason; errors.push("未处理Promise: " + (r && r.message ? r.message : String(r)).slice(0,200)); });
  var ce = console.error;
  console.error = function(){ try { errors.push("console.error: " + Array.prototype.map.call(arguments, String).join(" ").slice(0,200)); } catch(_){} return ce.apply(console, arguments); };
  setTimeout(function(){
    var checks = { "页面": document.documentElement.dataset.page || location.pathname,
                   "DOM可见内容长度": document.body.innerText.length };
    try { if (typeof window.__SELFTEST__ === "function") Object.assign(checks, window.__SELFTEST__()); }
    catch (e) { errors.push("自检项抛出: " + (e.message || e)); }
    var failed = Object.keys(checks).filter(function(k){ return checks[k] === false; });
    var out = { ok: errors.length === 0 && failed.length === 0, errors: errors, failed: failed, checks: checks };
    var pre = document.createElement("pre"); pre.id = "selftest-out";
    pre.style.cssText = "position:fixed;left:-9999px;top:0";
    pre.textContent = "SELFTEST_JSON=" + JSON.stringify(out);
    document.body.appendChild(pre);
    document.title = "SELFTEST_" + (out.ok ? "PASS" : "FAIL");
  }, 4500);
})();
