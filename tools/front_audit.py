# -*- coding: utf-8 -*-
"""前端运行时审计：用 Edge 无头浏览器加载每个页面（?selftest=1），
收集 JS 运行时错误与关键检查项。零第三方依赖，可反复回归。

用法：python tools/front_audit.py           # 需要服务已在 8848 运行
产出：out/audit/front_<ts>.json + 控制台摘要
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
EDGE = r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
BASE = "http://127.0.0.1:8848"
PAGES = [("/", "briefing"), ("/chat", "chat"), ("/graph", "graph"),
         ("/dashboard", "dashboard"), ("/runs", "runs")]

def audit_page(path: str, tag: str, run_id: str | None = None) -> dict:
    url = f"{BASE}{path}{'?' if '?' not in path else '&'}selftest=1"
    if run_id and tag == "run":
        url = f"{BASE}/run?id={run_id}&selftest=1"
    with tempfile.TemporaryDirectory() as td:
        cmd = [EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
               f"--user-data-dir={td}", "--virtual-time-budget=12000",
               "--dump-dom", url]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return {"page": tag, "ok": False, "errors": ["页面加载超时（>120s）"], "checks": {}}
    dom = r.stdout or ""
    m = re.search(r"SELFTEST_JSON=(\{.*?\})</pre>", dom, re.S)
    if not m:
        return {"page": tag, "ok": False, "errors": ["未产出自检结果（页面可能白屏或脚本未执行）"],
                "checks": {}, "dom_len": len(dom)}
    try:
        data = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&"))
    except Exception as e:
        return {"page": tag, "ok": False, "errors": [f"自检结果解析失败：{e}"], "checks": {}}
    data["page"] = tag
    return data

def main() -> None:
    # 取一个真实 run_id 用于 /run 页审计
    run_id = None
    try:
        import urllib.request
        with urllib.request.urlopen(BASE + "/api/runs?limit=1", timeout=10) as r:
            runs = json.loads(r.read()).get("runs") or []
        if runs:
            run_id = runs[0]["run_id"]
    except Exception:
        pass

    results = [audit_page(p, t) for p, t in PAGES]
    if run_id:
        results.append(audit_page("/run", "run", run_id))

    dest = ROOT / "out" / "audit"
    dest.mkdir(parents=True, exist_ok=True)
    fp = dest / f"front_{time.strftime('%Y%m%d_%H%M%S')}.json"
    fp.write_text(json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                              "run_id_used": run_id, "results": results},
                             ensure_ascii=False, indent=1), encoding="utf-8")
    print("=" * 66)
    bad = 0
    for res in results:
        status = "PASS" if res.get("ok") else "FAIL"
        if not res.get("ok"):
            bad += 1
        print(f"[{status}] {res['page']:<10} 检查项 {len(res.get('checks') or {})} 个")
        for e in res.get("errors") or []:
            print("        ERROR:", e)
        for f in res.get("failed") or []:
            print("        FAILED:", f)
    print("=" * 66)
    print(f"页面 {len(results)} 个 · 失败 {bad} 个 · 明细 {fp}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
