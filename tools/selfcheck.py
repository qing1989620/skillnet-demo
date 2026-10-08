# -*- coding: utf-8 -*-
"""selfcheck.py —— 交付前自检：页面可达性 + 数字一致性 + 关键接口结构。

为什么需要它
------------
本项目页面里曾多次出现**硬编码数字与真实数据不一致**（技能数 51/75/90 三个版本
同时存在于不同页面），而这类问题不会报错、只在演示时被当场发现。
本脚本把「页面上的数字必须等于 API 的真实值」变成可自动执行的检查。

用法
----
    python tools/selfcheck.py            # 需要服务已启动（python run.py）
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8848"
WEB = ROOT / "web"

PAGES = ["/", "/chat", "/runs", "/run", "/graph", "/dashboard", "/static/briefing.html", "/static/graph.html"]
APIS = ["/api/health", "/api/stats", "/api/graph", "/api/skills", "/api/tasks", "/api/results", "/api/config", "/api/runs?limit=1", "/api/integrations/s1"]

_ok: list[str] = []
_bad: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (_ok if cond else _bad).append(f"{name}{('  -> ' + detail) if detail and not cond else ''}")
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (f"  -> {detail}" if detail and not cond else ""))


def get(path: str, timeout: int = 10):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.status, r.read()


def main() -> int:
    print("=" * 64)
    print("SkillNet-S1 交付自检（页面 / 数字一致性 / 接口）")
    print("=" * 64)

    # ---- 1) 服务与页面可达 ----
    print("\n[1] 页面可达性")
    try:
        st, _ = get("/api/health", 4)
    except Exception as exc:
        print(f"  [FAIL] 服务未启动：{exc}")
        print("\n请先运行：python run.py")
        return 1
    for p in PAGES:
        try:
            st, body = get(p)
            check(f"{p} 可访问", st == 200 and len(body) > 200, f"HTTP {st}")
        except Exception as exc:
            check(f"{p} 可访问", False, str(exc))

    # ---- 2) 接口结构 ----
    print("\n[2] 关键接口")
    health = json.loads(get("/api/health")[1])
    graph = json.loads(get("/api/graph")[1])
    for a in APIS:
        try:
            st, body = get(a)
            json.loads(body)
            check(f"{a} 返回合法 JSON", st == 200, f"HTTP {st}")
        except Exception as exc:
            check(f"{a} 返回合法 JSON", False, str(exc))

    real_skills = len(graph["nodes"])
    real_domains = len({n["domain"] for n in graph["nodes"]})
    real_edges = len(graph["edges"])
    real_evolved = sum(1 for n in graph["nodes"] if n["source"] != "seed")
    print(f"\n  真实数据：技能 {real_skills} · 领域 {real_domains} · 边 {real_edges} · 演化 {real_evolved}"
          f"（health 报告技能 {health.get('skills')}）")
    check("health.skills 与图谱节点数一致", health.get("skills") == real_skills,
          f"{health.get('skills')} vs {real_skills}")
    check("health.evolved 与图谱演化数一致", health.get("evolved") == real_evolved,
          f"{health.get('evolved')} vs {real_evolved}")

    # ---- 3) 页面硬编码数字（核心检查）----
    print("\n[3] 页面数字一致性（硬编码 vs 真实值）")
    # 只检查「未标注 data-live 的裸数字」：这些是改版后最容易漂移的地方
    patterns = [
        (re.compile(r"(?<!data-live=\"skills\">)\b(\d{2,3})\s*个技能"), "技能数"),
        (re.compile(r"(?<!data-live=\"domains\">)\b(\d{1,2})\s*个?领域"), "领域数"),
        (re.compile(r"(?<!data-live=\"edges\">)\b(\d{2,3})\s*条(?:类型化)?(?:关系)?边"), "关系边数"),
    ]
    for fname in ("briefing.html", "graph.html", "index.html"):
        f = WEB / fname
        if not f.exists():
            continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        # 去掉 <script>…</script> 与 data-live 的 span 之后再做检查
        body = re.sub(r"<script>.*?</script>", "", txt, flags=re.S)
        body = re.sub(r'<span data-live="[^"]+">[^<]*</span>', "LIVE", body)
        for pat, label in patterns:
            for m in pat.finditer(body):
                v = int(m.group(1))
                real = {"技能数": real_skills, "领域数": real_domains, "关系边数": real_edges}[label]
                # 允许「构成说明」里的固定数字（如 51 个科研方法技能 / 24 个工具技能）
                if label == "技能数" and v in (51, 24):
                    continue
                check(f"{fname} 中硬编码{label} {v} 与真实值一致", v == real,
                      f"页面写 {v}，实际 {real}")

    # ---- 4) 产物接口（含中文名与图片）----
    print("\n[4] 产物接口")
    arts = sorted((ROOT / "out" / "demo_artifacts").glob("*"))
    if arts:
        slug = arts[-1].name
        files = [p for p in arts[-1].iterdir() if p.is_file()]
        pngs = [p for p in files if p.suffix.lower() == ".png"]
        cns = [p for p in files if any("\u4e00" <= ch <= "\u9fff" for ch in p.name)]
        if files:
            import urllib.parse
            f0 = files[0]
            try:
                st, body = get(f"/api/artifact/{slug}/{urllib.parse.quote(f0.name)}")
                check("产物可预览", st == 200 and len(body) > 0, f"HTTP {st}")
            except Exception as exc:
                check("产物可预览", False, str(exc))
            check("产物目录含图片（可内联展示）", bool(pngs), f"{len(pngs)} 张")
            if cns:
                import urllib.parse
                try:
                    st, _ = get(f"/api/artifact/{slug}/{urllib.parse.quote(cns[0].name)}")
                    check("中文名产物可访问", st == 200, f"HTTP {st}")
                except Exception as exc:
                    check("中文名产物可访问", False, str(exc))
        # 路径穿越必须被拒
        for bad in ("..%2f..%2fserver.py", "%2e%2e%2fdata%2flibrary.json"):
            try:
                get(f"/api/artifact/{slug}/{bad}")
                check(f"路径穿越被拦截（{bad}）", False, "未被拦截")
            except urllib.error.HTTPError as e:
                check(f"路径穿越被拦截（{bad}）", e.code in (400, 404), f"HTTP {e.code}")
    else:
        print("  （尚无产物目录，跳过）")

    print("\n" + "=" * 64)
    print(f"自检结果：{len(_ok)} 项通过，{len(_bad)} 项失败")
    if _bad:
        print("\n失败明细：")
        for b in _bad:
            print("  - " + b)
    print("=" * 64)
    return 1 if _bad else 0


if __name__ == "__main__":
    sys.exit(main())
