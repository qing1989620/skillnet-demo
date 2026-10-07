/* Shared connection, feedback and accessible interaction. Credentials are scoped
   to this browser tab and are never appended to URLs or persisted in localStorage. */
(function () {
  "use strict";
  const TOKEN_KEY = "skillnet_connection_token";
  const nativeFetch = window.fetch.bind(window);
  const storage = {
    get: () => { try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch (_) { return ""; } },
    set: value => { try { value ? sessionStorage.setItem(TOKEN_KEY, value) : sessionStorage.removeItem(TOKEN_KEY); } catch (_) {} }
  };
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
  function isLocalAPI(input) {
    try { const url = new URL(input instanceof Request ? input.url : String(input), location.href);
      return url.origin === location.origin && url.pathname.startsWith("/api/");
    } catch (_) { return false; }
  }
  async function apiFetch(input, options) {
    const local = isLocalAPI(input);
    const init = { ...(options || {}) };
    if (local) {
      const headers = new Headers(input instanceof Request ? input.headers : undefined);
      new Headers(init.headers || {}).forEach((value, key) => headers.set(key, value));
      const token = storage.get();
      if (token && !headers.has("X-SkillNet-Token") && !headers.has("Authorization")) headers.set("X-SkillNet-Token", token);
      init.headers = headers;
    }
    try { return await nativeFetch(input, init); }
    catch (error) {
      if (local && error.name !== "AbortError") throw new Error("无法连接 SkillNet 服务，请检查服务状态后重试。");
      throw error;
    }
  }
  // Legacy pages call fetch directly; the same-origin boundary prevents sending
  // this service's token to Liliai, external links, or third-party endpoints.
  window.fetch = apiFetch;
  async function json(input, options) {
    const response = await apiFetch(input, options);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = typeof body.detail === "string" ? body.detail : "";
      const message = response.status === 401 || response.status === 403
        ? "服务需要访问令牌，请打开「连接设置」配置后重试。"
        : response.status === 404 ? "记录不存在或已被移除。"
        : response.status === 429 ? "当前请求过多，请稍后重试。"
        : detail || `服务暂时无法完成请求（HTTP ${response.status}）。`;
      const error = new Error(message); error.status = response.status; throw error;
    }
    return response.json();
  }
  function toast(message) {
    document.getElementById("ui-toast")?.remove();
    const el = document.createElement("div"); el.id = "ui-toast"; el.className = "ui-toast";
    el.setAttribute("role", "status"); el.textContent = message; document.body.appendChild(el);
    setTimeout(() => el.remove(), 4500);
  }
  function errorHTML(error) { return `<div class="ui-error" role="alert">${esc(error?.message || error || "加载失败，请重试。")}</div>`; }
  function connectionSettings() {
    let dialog = document.getElementById("ui-connection-dialog");
    if (!dialog) {
      dialog = document.createElement("dialog"); dialog.id = "ui-connection-dialog"; dialog.className = "ui-dialog";
      dialog.setAttribute("aria-labelledby", "ui-connection-title");
      dialog.innerHTML = `<form method="dialog"><h2 id="ui-connection-title">连接设置</h2>
        <p>服务启用访问保护时，在此填写访问令牌。令牌仅保存在当前浏览器标签页的会话中；关闭标签页后清除。</p>
        <label for="ui-token">访问令牌</label><input id="ui-token" type="password" autocomplete="off" spellcheck="false" placeholder="未启用访问保护时可留空">
        <div class="ui-dialog-status" id="ui-token-status" role="status"></div>
        <div class="ui-dialog-actions"><button type="button" class="ui-btn ui-btn-secondary" id="ui-token-clear">清除</button><button class="ui-btn ui-btn-secondary" value="cancel">关闭</button><button type="button" class="ui-btn" id="ui-token-save">保存并验证</button></div></form>`;
      document.body.appendChild(dialog);
      dialog.addEventListener("click", event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
      dialog.querySelector("#ui-token-clear").addEventListener("click", () => {
        storage.set(""); dialog.querySelector("#ui-token").value = "";
        dialog.querySelector("#ui-token-status").textContent = "已清除当前标签页的访问令牌。";
      });
      dialog.querySelector("#ui-token-save").addEventListener("click", async event => {
        const button = event.currentTarget, status = dialog.querySelector("#ui-token-status");
        const previous = storage.get(); storage.set(dialog.querySelector("#ui-token").value.trim());
        button.disabled = true; status.textContent = "正在验证连接…"; status.style.color = "";
        try {
          const health = await json("/api/health");
          // Dedicated read-only check; public health cannot verify a token.
          if (health.token_required) await json("/api/auth/check");
          status.textContent = health.token_required ? "访问令牌已验证并保存。" : "服务连接正常。当前服务未启用令牌保护。";
          window.dispatchEvent(new Event("skillnet:connection-changed"));
        } catch (error) {
          storage.set(previous); status.textContent = error.message; status.style.color = "var(--bad)";
        } finally { button.disabled = false; }
      });
    }
    dialog.querySelector("#ui-token").value = storage.get();
    dialog.querySelector("#ui-token-status").textContent = "";
    dialog.querySelector("#ui-token-status").style.color = "";
    dialog.showModal();
  }
  const mark = `<svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M7 9 16 4l9 5v13l-9 6-9-6V9Z" stroke="currentColor" stroke-width="1.6"/><path d="m7 9 9 6 9-6M16 15v13M7 22l9-7 9 7" stroke="currentColor" stroke-width="1.4"/><circle cx="16" cy="15" r="2.8" fill="currentColor"/></svg>`;
  async function consumeSSE(url, onEvent, signal) {
    const response = await apiFetch(url, {signal, headers:{Accept:"text/event-stream"}});
    if (!response.ok) { const error = new Error(response.status === 401 ? "事件流需要访问令牌，请检查连接设置。" : `事件流连接失败（HTTP ${response.status}）。`); error.status = response.status; throw error; }
    if (!response.body) throw new Error("当前浏览器不支持实时事件流。");
    const reader = response.body.getReader(), decoder = new TextDecoder();
    let buffer = "";
    function dispatch(block) {
      const lines = block.split("\n"); let name = "message"; const data = [];
      lines.forEach(line => { if (line.startsWith("event:")) name = line.slice(6).trim(); if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /,"")); });
      if (name === "end") return true;
      if (!data.length) return false;
      let event; try { event = JSON.parse(data.join("\n")); } catch (_) { return false; }
      onEvent(event); return event.type === "end";
    }
    try {
      while (true) {
        const {done,value} = await reader.read();
        buffer += done ? decoder.decode() : decoder.decode(value,{stream:true});
        buffer = buffer.replace(/\r\n/g,"\n");
        let split;
        while ((split = buffer.indexOf("\n\n")) !== -1) { const block = buffer.slice(0,split); buffer = buffer.slice(split+2); if (dispatch(block)) return; }
        if (done) { if (buffer.trim()) dispatch(buffer); return; }
      }
    } finally { await reader.cancel().catch(()=>{}); reader.releaseLock(); }
  }
  function productNav(active) {
    return `<nav class="ui-product-nav" aria-label="产品导航">${[["/","产品概览","briefing"],["/chat","科研工作台","chat"],["/runs","运行中心","dashboard"],["/graph","技能图谱","graph"]].map(([href,label,page]) => `<a href="${href}"${page === active ? ' aria-current="page"' : ""}>${label}</a>`).join("")}<button class="ui-settings-btn" type="button" data-connection-settings>连接设置</button></nav>`;
  }
  function boot() {
    document.addEventListener("click", event => { if (event.target.closest("[data-connection-settings]")) connectionSettings(); });
    const interactive = ".gnode[data-step], .art[data-art], .ev, .list .row[data-n]";
    function enhance(root) {
      root.querySelectorAll(interactive).forEach(el => { el.tabIndex = 0; el.setAttribute("role", "button"); });
      root.querySelectorAll("input,textarea,select").forEach(el => { if (!el.getAttribute("aria-label") && !el.labels?.length) el.setAttribute("aria-label", el.placeholder || el.id || "输入项"); });
    }
    enhance(document);
    const observer = new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => { if (node.nodeType === 1) { enhance(node); if (node.matches(interactive)) { node.tabIndex = 0; node.setAttribute("role", "button"); } } })));
    observer.observe(document.body, { subtree: true, childList: true });
    document.addEventListener("keydown", event => {
      if ((event.key === "Enter" || event.key === " ") && event.target.matches(interactive)) { event.preventDefault(); event.target.click(); }
    });
  }
  window.UI = { fetch: apiFetch, json, esc, toast, errorHTML, consumeSSE, connectionSettings, getToken: storage.get,
    setToken: value => storage.set(String(value || "").trim()), productNav, mark,
    reveal: function () {}, progress: function () {} };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
