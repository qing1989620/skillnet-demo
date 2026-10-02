# -*- coding: utf-8 -*-
"""checks.py —— 确定性产物检查（Verification 第一层）。

设计原则
--------
**能在代码里判定的，绝不交给 LLM。** 竞品分析里最一致的一条结论是：
只评估最终输出的系统会漏掉 20–40% 的真实失败（step-level 才是失败面）。
因此每步产物必须先过这一层确定性检查，LLM 只做真正需要语义判断的部分。

四层验收（本模块实现第 1 层，第 2 层由技能声明驱动）：
  L1 Deterministic  文件存在/非空、CSV 表头与行数、JSON 可解析、PNG 可打开、
                    Python 可编译、数值列范围、退出码
  L2 Assertion      技能自定义的 machine-readable 断言（见 checks_from_skill）
  L3 LLM            技能 verification 条目的语义复核（executor 里）
  L4 Human          人工确认（未实现，属治理范围）

不依赖 pandas / PIL：CSV 用标准库，PNG 直接解析 IHDR 头，降低环境耦合。
"""
from __future__ import annotations

import ast
import csv
import io
import json
import pathlib
import struct
from typing import Any

# 常见数值列范围断言（L2 用；技能可覆盖）
DEFAULT_NUMERIC_RANGES: dict[str, tuple[float, float]] = {}


def _read_text(p: pathlib.Path, limit: int = 2_000_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def check_file(path: pathlib.Path) -> list[tuple[str, bool, str]]:
    """基础检查：存在性、大小、非空。"""
    out: list[tuple[str, bool, str]] = []
    if not path.exists():
        return [(f"{path.name} 存在", False, "文件不存在")]
    size = path.stat().st_size
    out.append((f"{path.name} 存在", True, f"{size} 字节"))
    out.append((f"{path.name} 非空", size > 0, f"{size} 字节"))
    return out


def check_csv(path: pathlib.Path) -> list[tuple[str, bool, str]]:
    txt = _read_text(path)
    if not txt.strip():
        return [(f"{path.name} 是可解析 CSV", False, "内容为空")]
    try:
        rows = list(csv.reader(io.StringIO(txt)))
    except (csv.Error, ValueError) as exc:
        return [(f"{path.name} 是可解析 CSV", False, f"解析失败：{exc}")]
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if not rows:
        return [(f"{path.name} 是可解析 CSV", False, "无有效行")]
    header, body = rows[0], rows[1:]
    out = [
        (f"{path.name} 是可解析 CSV", True, f"{len(rows)} 行（含表头）"),
        (f"{path.name} 含表头且列数 > 0", len(header) > 0, f"列：{', '.join(header[:6])}"),
        (f"{path.name} 含数据行", len(body) > 0, f"{len(body)} 行数据"),
    ]
    # 列数一致性（CSV 常见错误：某些行少列）
    widths = {len(r) for r in rows}
    out.append((f"{path.name} 各行列数一致", len(widths) == 1, f"列数集合 {sorted(widths)}"))
    return out


def check_json(path: pathlib.Path) -> list[tuple[str, bool, str]]:
    txt = _read_text(path)
    try:
        obj = json.loads(txt)
    except ValueError as exc:
        return [(f"{path.name} 是合法 JSON", False, f"{str(exc)[:80]}")]
    kind = type(obj).__name__
    n = len(obj) if isinstance(obj, (list, dict)) else 1
    return [(f"{path.name} 是合法 JSON", True, f"{kind}，{n} 项")]


def png_size(path: pathlib.Path) -> tuple[int, int] | None:
    """直接解析 PNG IHDR（不依赖 PIL）。返回 (w, h) 或 None。"""
    try:
        with path.open("rb") as f:
            head = f.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", head[16:24])
    return int(w), int(h)


def check_image(path: pathlib.Path) -> list[tuple[str, bool, str]]:
    if path.suffix.lower() == ".png":
        wh = png_size(path)
        if not wh:
            return [(f"{path.name} 是有效 PNG", False, "PNG 头无效或被截断")]
        w, h = wh
        return [
            (f"{path.name} 是有效 PNG", True, f"{w}×{h}"),
            (f"{path.name} 尺寸合理", w >= 200 and h >= 150, f"{w}×{h}（过小可能是空图）"),
        ]
    return [(f"{path.name} 是图片产物", path.stat().st_size > 0, f"{path.stat().st_size} 字节")]


def check_python(path: pathlib.Path) -> list[tuple[str, bool, str]]:
    txt = _read_text(path)
    try:
        tree = ast.parse(txt)
    except SyntaxError as exc:
        return [(f"{path.name} 可编译", False, f"SyntaxError: {exc.msg} (line {exc.lineno})")]
    n_def = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
    n_import = sum(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree))
    return [(f"{path.name} 可编译", True, f"{len(txt.splitlines())} 行 · {n_def} 个函数 · {n_import} 处 import")]


def check_execution(sandbox_result: dict[str, Any]) -> list[tuple[str, bool, str]]:
    """执行侧检查：退出码、是否有实质输出。"""
    out: list[tuple[str, bool, str]] = []
    ok = bool(sandbox_result.get("ok"))
    rc = sandbox_result.get("returncode")
    out.append(("执行退出码为 0", ok, f"returncode={rc}"))
    stdout = sandbox_result.get("stdout") or ""
    lines = [l for l in stdout.splitlines() if l.strip()]
    out.append(("运行有实质输出", len(stdout) >= 40, f"{len(stdout)} 字符 / {len(lines)} 行"))
    arts = sandbox_result.get("artifacts") or []
    out.append(("产生至少一个文件产物", len(arts) > 0, f"{len(arts)} 个"))
    return out


def check_numeric_ranges(csv_path: pathlib.Path,
                         ranges: dict[str, tuple[float, float]]) -> list[tuple[str, bool, str]]:
    """数值列范围断言（如 score ∈ [0,1]）。技能可通过 L2 断言声明。"""
    if not ranges or csv_path.suffix.lower() != ".csv":
        return []
    txt = _read_text(csv_path)
    try:
        rows = list(csv.DictReader(io.StringIO(txt)))
    except (csv.Error, ValueError):
        return []
    out: list[tuple[str, bool, str]] = []
    for col, (lo, hi) in ranges.items():
        if not rows or col not in (rows[0] or {}):
            out.append((f"{csv_path.name} 列 {col} 在 [{lo}, {hi}]", False, f"列不存在"))
            continue
        bad, vals = 0, 0
        for r in rows:
            try:
                v = float(str(r.get(col, "")).strip())
            except ValueError:
                continue
            vals += 1
            if v < lo or v > hi:
                bad += 1
        out.append((f"{csv_path.name} 列 {col} 在 [{lo}, {hi}]",
                    bad == 0 and vals > 0, f"{vals} 个数值，越界 {bad} 个"))
    return out


def run_checks(artifact_paths: list[pathlib.Path], sandbox_result: dict[str, Any],
               ranges: dict[str, tuple[float, float]] | None = None) -> list[dict[str, Any]]:
    """对一次执行的产物做全套确定性检查，返回可直接落盘的列表。"""
    results: list[tuple[str, bool, str]] = []
    results += check_execution(sandbox_result)
    for p in artifact_paths:
        results += check_file(p)
        ext = p.suffix.lower()
        if ext == ".csv":
            results += check_csv(p)
            results += check_numeric_ranges(p, ranges or DEFAULT_NUMERIC_RANGES)
        elif ext == ".json":
            results += check_json(p)
        elif ext in (".png", ".jpg", ".jpeg", ".svg"):
            results += check_image(p)
        elif ext == ".py":
            results += check_python(p)
    return [{"name": n, "passed": bool(ok), "detail": d} for n, ok, d in results]


# ----------------------------------------------------------------------
# L2：技能声明的 machine-readable 断言
# ----------------------------------------------------------------------
# 技能的 verification 目前是自然语言条目。为了支持程序化断言，
# 允许条目使用轻量前缀语法（写在 SKILL.md 的验证清单里即可生效）：
#   [artifact_exists] *.csv
#   [csv_columns] sample,score
#   [numeric_range] score 0 1
#   [min_rows] 5
#   [image_min] 200 150
# 未带前缀的条目仍走 L3（LLM 语义复核），行为不变。
ASSERT_PREFIXES = ("artifact_exists", "csv_columns", "numeric_range",
                   "min_rows", "image_min", "json_keys")


def parse_assertions(items: list[str]) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for it in items or []:
        s = (it or "").strip()
        if not s.startswith("["):
            continue
        head, _, rest = s[1:].partition("]")
        kind = head.strip()
        if kind in ASSERT_PREFIXES:
            args = [a.strip() for a in rest.replace(",", " ").split() if a.strip()]
            out.append((kind, args))
    return out


def checks_from_skill(items: list[str], artifact_paths: list[pathlib.Path]) -> list[dict[str, Any]]:
    """把技能里的 machine-readable 断言变成真实检查（L2）。"""
    out: list[dict[str, Any]] = []
    for kind, args in parse_assertions(items):
        if kind == "artifact_exists":
            pat = args[0] if args else "*"
            hit = [p for p in artifact_paths if p.match(pat) or p.name.endswith(pat.replace("*", ""))]
            out.append({"name": f"[技能断言] 存在产物匹配 {pat}", "passed": bool(hit),
                        "detail": f"{len(hit)} 个匹配"})
        elif kind == "csv_columns":
            need = args
            for p in artifact_paths:
                if p.suffix.lower() != ".csv":
                    continue
                txt = _read_text(p)
                rows = list(csv.reader(io.StringIO(txt)))
                header = rows[0] if rows else []
                missing = [c for c in need if c not in header]
                out.append({"name": f"[技能断言] {p.name} 含列 {','.join(need)}",
                            "passed": not missing, "detail": f"缺 {missing}" if missing else "齐全"})
        elif kind == "numeric_range" and len(args) >= 3:
            col, lo, hi = args[0], float(args[1]), float(args[2])
            for p in artifact_paths:
                for n, ok, d in check_numeric_ranges(p, {col: (lo, hi)}):
                    out.append({"name": f"[技能断言] {n}", "passed": ok, "detail": d})
        elif kind == "min_rows" and args:
            need = int(args[0])
            for p in artifact_paths:
                if p.suffix.lower() != ".csv":
                    continue
                rows = [r for r in csv.reader(io.StringIO(_read_text(p))) if any(r)]
                out.append({"name": f"[技能断言] {p.name} 数据行 ≥ {need}",
                            "passed": max(0, len(rows) - 1) >= need, "detail": f"{max(0, len(rows)-1)} 行"})
        elif kind == "image_min" and len(args) >= 2:
            w_min, h_min = int(args[0]), int(args[1])
            for p in artifact_paths:
                if p.suffix.lower() != ".png":
                    continue
                wh = png_size(p) or (0, 0)
                out.append({"name": f"[技能断言] {p.name} 尺寸 ≥ {w_min}×{h_min}",
                            "passed": wh[0] >= w_min and wh[1] >= h_min, "detail": f"{wh[0]}×{wh[1]}"})
        elif kind == "json_keys":
            need = args
            for p in artifact_paths:
                if p.suffix.lower() != ".json":
                    continue
                try:
                    obj = json.loads(_read_text(p))
                except ValueError:
                    out.append({"name": f"[技能断言] {p.name} 含键 {','.join(need)}",
                                "passed": False, "detail": "JSON 不可解析"})
                    continue
                keys = set(obj.keys()) if isinstance(obj, dict) else set()
                missing = [k for k in need if k not in keys]
                out.append({"name": f"[技能断言] {p.name} 含键 {','.join(need)}",
                            "passed": not missing, "detail": f"缺 {missing}" if missing else "齐全"})
    return out
