# -*- coding: utf-8 -*-
"""SkillNet-S1 全量审计：静态检查 + 端点冒烟 + 边界与安全检查 + 一致性核对。

用法：python tools/full_audit.py            # 需要服务已在 8848 运行
产出：out/audit/audit_<ts>.json + 控制台摘要（按严重度分组）
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8848"
NODE = shutil.which("node")

issues: list[dict] = []
def add(sev: str, area: str, msg: str, detail: str = "") -> None:
    issues.append({"sev": sev, "area": area, "msg": msg, "detail": detail[:400]})

def get(path: str, timeout: int = 15):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            body = r.read()
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()

# ---------------------------------------------------------------- 1) 静态检查
def static_checks() -> None:
    py = list(ROOT.glob("*.py")) + list((ROOT / "skillnet").glob("*.py")) + \
         list((ROOT / "tools").glob("*.py")) + list((ROOT / "tests").glob("*.py")) + \
         list((ROOT / "bench").glob("*.py"))
    for p in py:
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            add("P0", "静态", f"Python 语法错误 {p.relative_to(ROOT)}", str(e))
    # JS 语法（HTML 内联脚本）
    if not NODE:
        add("P1", "静态", "无法验证 JS：未找到 Node.js")
    for p in sorted((ROOT / "web").glob("*.html")):
        t = p.read_text(encoding="utf-8")
        scripts = re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", t, re.S)
        for i, s in enumerate(scripts):
            fp = ROOT / "out" / "_audit_js.js"
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(s, encoding="utf-8")
            if NODE:
                r = subprocess.run([NODE, "--check", str(fp)], capture_output=True, text=True)
                if r.returncode != 0:
                    add("P0", "静态", f"JS 语法错误 {p.name} script#{i}", r.stderr[:300])
        # 重复 id
        ids = re.findall(r'\bid="([^"]+)"', t)
        dup = {x for x in ids if ids.count(x) > 1}
        if dup:
            add("P1", "静态", f"{p.name} 存在重复 id", ", ".join(sorted(dup)))
        # 连续重复行（重复导航项/重复脚本片段——都源自"追加式编辑未做幂等检查"）
        lines = t.splitlines()
        for i in range(len(lines) - 1):
            a, b = lines[i].strip(), lines[i + 1].strip()
            if a and a == b and ("<a href" in a or a.startswith("<div") or a.startswith("window.")):
                add("P1", "静态", f"{p.name} 连续重复行（疑似重复插入）", a[:100])
        # 明显的未闭合标签粗查（div/section）
        for tag in ("div", "section", "table"):
            opens = len(re.findall(rf"<{tag}[\s>]", t))
            closes = len(re.findall(rf"</{tag}>", t))
            if opens != closes:
                add("P1", "静态", f"{p.name} <{tag}> 开合数不一致", f"open={opens} close={closes}")

# ---------------------------------------------------------------- 2) 端点冒烟
PAGES = ["/", "/chat", "/graph", "/dashboard", "/runs", "/run"]
APIS = ["/api/health", "/api/graph", "/api/stats", "/api/tasks", "/api/capabilities",
        "/api/results", "/api/skills", "/api/runs?limit=5"]
def endpoint_smoke() -> dict:
    out: dict = {}
    for p in PAGES:
        st, body = get(p)
        out[p] = st
        if st != 200:
            add("P0", "端点", f"页面 {p} 返回 {st}", body[:200].decode("utf-8", "replace"))
        elif b"<!DOCTYPE HTML" not in body[:200].strip().upper():
            add("P1", "端点", f"页面 {p} 疑似非 HTML", body[:120].decode("utf-8", "replace"))
    data: dict = {}
    for p in APIS:
        st, body = get(p)
        out[p] = st
        if st != 200:
            add("P0", "端点", f"接口 {p} 返回 {st}", body[:200].decode("utf-8", "replace"))
            continue
        try:
            data[p] = json.loads(body.decode("utf-8"))
        except Exception as e:
            add("P0", "端点", f"接口 {p} 返回非 JSON", str(e))
    return {"status": out, "data": data}

# ---------------------------------------------------------------- 3) 边界与安全
def edge_cases() -> None:
    # 非法 run_id（路径穿越）
    for bad in ["../../etc/passwd", "..%2f..%2fwin.ini", "a" * 200]:
        st, _ = get(f"/api/runs/{bad}")
        if st not in (400, 404, 422):
            add("P0", "安全", f"非法 run_id 未被拒绝：{bad[:40]}", f"HTTP {st}")
    # 产物路径穿越
    st, _ = get("/api/runs/53e9d927-20261002-140122-0176/artifacts/..%2f..%2f..%2frun.json")
    if st == 200:
        add("P0", "安全", "产物接口疑似路径穿越", "返回 200")
    # 不存在产物（应 404 且给可用清单）
    st, body = get("/api/runs/53e9d927-20261002-140122-0176/artifacts/%E4%B8%8D%E5%AD%98%E5%9C%A8.csv")
    if st != 404:
        add("P1", "边界", f"不存在产物应 404，实际 {st}")
    elif "可用产物" not in body.decode("utf-8", "replace"):
        add("P2", "边界", "404 未附可用产物清单（可诊断性下降）")
    # 空任务 / 超长任务
    for payload, name in (({"task": ""}, "空任务"), ({"task": "x" * 7000}, "超长任务(7000)")):
        req = urllib.request.Request(BASE + "/api/runs", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                add("P1", "边界", f"{name} 未被拒绝", f"HTTP {r.status}")
        except urllib.error.HTTPError as e:
            if e.code not in (422, 400):
                add("P1", "边界", f"{name} 返回 {e.code}（期望 422/400）")
        except Exception as e:
            add("P1", "边界", f"{name} 请求异常", str(e))
    # 非法 history 结构：**本地 Pydantic 校验**（不真建 run，零成本）
    try:
        sys.path.insert(0, str(ROOT))
        import server as _srv  # noqa: E402
        _srv.RunReq(task="测试", history=[{"bad": 1}] * 3)
        _srv.RunReq(task="测试", history=[{"q": "问题", "a": "回答"}] * 25)  # 超 20 条
        add("P1", "边界", "RunReq 未拒绝脏/超长 history", "构造成功（期望 ValidationError）")
    except Exception as e:
        if "ValidationError" not in type(e).__name__ and "validation" not in str(e).lower():
            add("P0", "边界", f"RunReq 校验异常类型异常：{type(e).__name__}", str(e)[:200])

# ---------------------------------------------------------------- 4) 一致性
def consistency(data: dict) -> None:
    h = data.get("/api/health") or {}
    g = data.get("/api/graph") or {}
    c = data.get("/api/capabilities") or {}
    if h and g and h.get("skills") != len(g.get("nodes") or []):
        add("P1", "一致性", "health.skills 与 graph 节点数不一致",
            f"{h.get('skills')} vs {len(g.get('nodes') or [])}")
    lib = (c.get("library") or {})
    if lib and g and lib.get("skills") != len(g.get("nodes") or []):
        add("P1", "一致性", "capabilities 与 graph 技能数不一致",
            f"{lib.get('skills')} vs {len(g.get('nodes') or [])}")
    if lib and lib.get("evolved", 0) + lib.get("seed", 0) != lib.get("skills"):
        add("P1", "一致性", "capabilities 种子+演化 ≠ 总数",
            f"{lib.get('seed')}+{lib.get('evolved')} vs {lib.get('skills')}")
    # run.json 字段完整性（抽样最近 3 条）
    runs = sorted((ROOT / "out" / "runs").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    for p in runs:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            add("P0", "一致性", f"run.json 解析失败 {p.name}", str(e))
            continue
        for k in ("run_id", "status", "steps", "staged", "budget", "cost_yuan", "duration_ms"):
            if k not in d:
                add("P1", "一致性", f"{p.name} 缺字段 {k}")
        for s in d.get("steps") or []:
            if s.get("status") == "done" and not s.get("attempts"):
                add("P2", "一致性", f"{p.name} 步骤 {s.get('idx')} 标记完成但无 attempts")
    return len(runs)

def main() -> None:
    static_checks()
    res = endpoint_smoke()
    edge_cases()
    n_runs = consistency(res["data"])
    sev_order = {"P0": 0, "P1": 1, "P2": 2}
    issues.sort(key=lambda x: sev_order.get(x["sev"], 9))
    dest = ROOT / "out" / "audit"
    dest.mkdir(parents=True, exist_ok=True)
    fp = dest / f"audit_{time.strftime('%Y%m%d_%H%M%S')}.json"
    fp.write_text(json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                              "issues": issues, "endpoint_status": res["status"],
                              "runs_checked": n_runs}, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print("=" * 66)
    print("审计结果：", fp)
    print("=" * 66)
    if not issues:
        print("未发现问题（P0/P1/P2 均为 0）")
    for x in issues:
        print(f"[{x['sev']}] {x['area']}：{x['msg']}")
        if x["detail"]:
            print("        ", x["detail"].replace("\n", " ")[:180])
    cnt = {s: sum(1 for i in issues if i["sev"] == s) for s in ("P0", "P1", "P2")}
    print(f"\n汇总：P0={cnt['P0']} · P1={cnt['P1']} · P2={cnt['P2']} · 共 {len(issues)} 项")
    return 0 if cnt["P0"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
