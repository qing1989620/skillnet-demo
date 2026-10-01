# -*- coding: utf-8 -*-
"""artifacts.py —— 执行产物的渲染与落盘。

为什么需要这一层
----------------
闭环演示此前只展示「过程」（检索排序、编排、评分），看不到「产出」——
使用者无法判断这次执行到底生成了什么、质量如何。Nexus 的做法是从模型回答里
提取代码块/HTML 落盘为真实文件（`_extract_artifacts`）；本模块沿用这一思路，
但产物形态针对本项目的执行契约（结构化方案 JSON）定制：

- `report.html`：自包含 HTML 研究报告（可在线预览、可直接交付）
- `plan.md`    ：Markdown 版方案（便于复制进文档/工单）
- 方案中出现的代码块 → 按语言落盘为独立源码文件（沿用 Nexus 的确定性提取规则）

设计约束
--------
1. **零 LLM**：产物完全由执行结果渲染，不额外调用模型（成本可控、结果确定）。
2. **确定性**：同一份执行结果渲染出的产物字节级一致（便于审计与比对）。
3. **不过度承诺**：产物是「执行方案与要点」，不是「已完成的实验」——
   报告页脚显式标注产物性质，避免把方案误读为结果。
"""
from __future__ import annotations

import hashlib
import html as _html
import re
from typing import Any

# 代码块提取（沿用 Nexus 的确定性规则：语言白名单 + 最小长度）
CODE_LANGS = {
    "python": "py", "py": "py", "javascript": "js", "js": "js",
    "typescript": "ts", "ts": "ts", "bash": "sh", "sh": "sh",
    "sql": "sql", "r": "r", "yaml": "yaml", "json": "json", "toml": "toml",
}
CODE_MIN_CHARS = 200
_FENCE_RE = re.compile(r"```([a-zA-Z0-9_+-]*)\n(.*?)```", re.S)


def task_slug(task: str) -> str:
    """任务 -> 稳定目录名（8 位十六进制）。用 sha256 而不是内置 hash()（跨进程稳定）。"""
    return hashlib.sha256(task.strip().encode("utf-8")).hexdigest()[:8]


def split_code_blocks(steps: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """从步骤文本中提取代码块，返回（清理后的步骤, 代码文件清单）。

    确定性规则：fenced 代码块 + 语言在白名单 + 长度 >= CODE_MIN_CHARS 才落盘；
    命中项在原文中替换为占位说明（避免同一份内容既在报告里又在文件里重复）。
    """
    cleaned: list[dict[str, Any]] = []
    files: list[dict[str, str]] = []
    for i, st in enumerate(steps, 1):
        s = dict(st)
        for field in ("action", "expected_output", "check"):
            text = str(s.get(field) or "")
            if "```" not in text:
                continue

            def _sub(m: re.Match) -> str:
                lang = (m.group(1) or "").lower()
                body = m.group(2)
                ext = CODE_LANGS.get(lang)
                if not ext or len(body.strip()) < CODE_MIN_CHARS:
                    return m.group(0)
                name = f"step{i}_code_{len(files) + 1}.{ext}"
                files.append({"name": name, "lang": lang or ext, "body": body.rstrip()})
                return f"（该步附带的 {lang} 代码已落盘为产物文件 {name}）"

            s[field] = _FENCE_RE.sub(_sub, text)
        cleaned.append(s)
    return cleaned, files


def build_markdown(task: str, plan: dict[str, Any], judge: dict[str, Any],
                   skills: list[str], adoption: float, meta: dict[str, str]) -> str:
    steps = plan.get("steps") or []
    lines: list[str] = [
        f"# 研究执行方案 · {task[:60]}",
        "",
        f"> 生成方式：SkillNet-S1 技能运维层（技能驱动执行）　|　任务指纹 `{meta.get('slug', '')}`",
        f"> 加载技能：{'、'.join(skills) if skills else '（无）'}　|　技能采纳率 {adoption * 100:.0f}%",
        f"> 盲评均分 {float(judge.get('weighted') or 0):.2f}/10"
        + (f"　|　要点覆盖 {len(judge.get('covered') or [])}/{judge.get('n_points')}"
           if judge.get("coverage") is not None else "　|　（无 gold 基准，客观线跳过）"),
        "",
        "## 研究思路",
        "",
        str(plan.get("approach") or "（未给出）"),
        "",
        "## 执行步骤",
        "",
    ]
    for i, st in enumerate(steps, 1):
        s = st if isinstance(st, dict) else {"action": str(st)}
        lines.append(f"### S{i} · {s.get('action') or ''}")
        lines.append("")
        if s.get("skill"):
            lines.append(f"- **调用技能**：`{s['skill']}`")
        for p in (s.get("key_params") or []):
            lines.append(f"- **关键参数**：{p}")
        if s.get("expected_output"):
            lines.append(f"- **预期产出**：{s['expected_output']}")
        if s.get("check"):
            lines.append(f"- **校验判据**：{s['check']}")
        lines.append("")
    risks = plan.get("risks") or []
    if risks:
        lines += ["## 风险与应对", ""] + [f"- {r}" for r in risks] + [""]
    arts = plan.get("artifacts") or []
    if arts:
        lines += ["## 交付物清单", ""] + [f"- {a}" for a in arts] + [""]
    lines += [
        "---",
        "",
        "> 说明：本文件由执行器输出渲染而来，内容为**研究方案与要点**（非实验结论）。",
        "> 方案中的参数取值与判据需在真实数据上验证后采用。",
        "",
    ]
    return "\n".join(lines)


def build_html(task: str, plan: dict[str, Any], judge: dict[str, Any],
               skills: list[str], adoption: float, meta: dict[str, str],
               code_files: list[dict[str, str]]) -> str:
    """自包含 HTML 报告（无外部依赖，可直接预览/交付/打印为 PDF）。"""
    e = _html.escape

    def esc(v: Any) -> str:
        return e(str(v if v is not None else ""))

    steps_html: list[str] = []
    for i, st in enumerate(plan.get("steps") or [], 1):
        s = st if isinstance(st, dict) else {"action": str(st)}
        params = "".join(f"<li>{esc(p)}</li>" for p in (s.get("key_params") or []))
        steps_html.append(f"""
    <div class="step">
      <div class="sh"><span class="sn">S{i}</span><span class="sa">{esc(s.get('action'))}</span></div>
      {f'<div class="k">调用技能 <code>{esc(s["skill"])}</code></div>' if s.get('skill') else ''}
      {f'<div class="k">关键参数</div><ul>{params}</ul>' if params else ''}
      {f'<div class="k">预期产出</div><div class="v">{esc(s.get("expected_output"))}</div>' if s.get('expected_output') else ''}
      {f'<div class="chk">校验：{esc(s.get("check"))}</div>' if s.get('check') else ''}
    </div>""")

    risks_html = "".join(f"<li>{esc(r)}</li>" for r in (plan.get("risks") or []))
    arts_html = "".join(f"<li>{esc(a)}</li>" for a in (plan.get("artifacts") or []))
    files_html = "".join(
        f'<li><code>{esc(f["name"])}</code> <span class="meta">({esc(f["lang"])}, {len(f["body"])} 字符)</span></li>'
        for f in code_files) or '<li class="meta">本次方案未包含可落盘代码块</li>'

    dims = judge.get("scores") or judge.get("dimensions") or {}
    dims_html = "".join(
        f'<div class="row"><span>{esc(k)}</span><div class="bar"><i style="width:{min(100, float(v) * 10):.0f}%"></i></div>'
        f'<b>{float(v):.1f}</b></div>'
        for k, v in dims.items() if isinstance(v, (int, float)))
    cov = judge.get("coverage")
    cov_html = (f'<div class="row"><span>要点覆盖 {len(judge.get("covered") or [])}/{esc(judge.get("n_points"))}</span>'
                f'<div class="bar obj"><i style="width:{float(cov) * 100:.0f}%"></i></div><b>{float(cov):.2f}</b></div>'
                ) if cov is not None else '<div class="meta">客观线：无 gold 基准，本次跳过</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>研究执行方案 · {esc(task[:40])}</title>
<style>
 :root {{ --ink:#22303e; --dim:#64748a; --line:#dfe6ec; --brand:#1a3a5c; --ok:#2e7d4f; }}
 * {{ box-sizing:border-box; margin:0; padding:0; }}
 body {{ font-family:"Microsoft YaHei","PingFang SC",sans-serif; color:var(--ink);
        background:#fbfaf8; line-height:1.75; padding:34px 22px; }}
 .wrap {{ max-width:820px; margin:0 auto; background:#fff; border:1px solid var(--line); padding:32px 36px; }}
 h1 {{ font-size:21px; color:var(--brand); margin-bottom:6px; line-height:1.4; }}
 .lead {{ color:var(--dim); font-size:12.5px; padding-bottom:14px; border-bottom:2px solid var(--brand); margin-bottom:20px; }}
 h2 {{ font-size:15px; color:var(--brand); margin:24px 0 10px; padding-bottom:5px; border-bottom:1px solid var(--line); }}
 .approach {{ background:#f2f6fa; border-left:3px solid var(--brand); padding:12px 15px; font-size:13.5px; }}
 .step {{ border:1px solid var(--line); border-left:3px solid #24557a; padding:12px 15px; margin-bottom:10px; }}
 .sh {{ display:flex; gap:9px; align-items:baseline; }}
 .sn {{ color:#24557a; font-weight:800; }}
 .sa {{ font-weight:700; font-size:13.5px; }}
 .k {{ color:var(--dim); font-size:11.5px; margin-top:6px; }}
 .v {{ font-size:12.5px; }}
 .chk {{ color:var(--ok); font-size:12px; margin-top:4px; }}
 ul {{ margin-left:18px; font-size:12.5px; }}
 code {{ background:#eef1f4; padding:1px 5px; border-radius:3px; font-size:12px; }}
 .row {{ display:grid; grid-template-columns:150px 1fr 46px; gap:10px; align-items:center; font-size:12.5px; margin:3px 0; }}
 .bar {{ height:8px; background:#edf1f4; }} .bar i {{ display:block; height:100%; background:#24557a; }} .bar.obj i {{ background:var(--ok); }}
 .meta {{ color:var(--dim); font-size:12px; }}
 .box {{ border:1px solid var(--line); background:#f7f9fb; padding:11px 15px; font-size:12.5px; margin-top:10px; }}
 footer {{ margin-top:26px; padding-top:12px; border-top:1px solid var(--line); color:var(--dim); font-size:11.5px; }}
</style></head><body><div class="wrap">
 <h1>研究执行方案</h1>
 <div class="lead">
   任务：{esc(task)}<br>
   生成方式：SkillNet-S1 技能运维层（技能驱动执行）　|　任务指纹 <code>{esc(meta.get('slug'))}</code><br>
   加载技能：{'、'.join(f'<code>{esc(s)}</code>' for s in skills) if skills else '（无）'}
   ｜技能采纳率 {adoption * 100:.0f}%
 </div>
 <h2>研究思路</h2>
 <div class="approach">{esc(plan.get('approach'))}</div>
 <h2>执行步骤（{len(plan.get('steps') or [])} 步）</h2>
 {''.join(steps_html)}
 <h2>风险与应对</h2>
 <ul>{risks_html or '<li class="meta">（未给出）</li>'}</ul>
 <h2>交付物清单</h2>
 <ul>{arts_html or '<li class="meta">（未给出）</li>'}</ul>
 <h2>落盘代码产物</h2>
 <ul>{files_html}</ul>
 <h2>评估（主客观分列）</h2>
 {dims_html}
 <div class="box">盲评均分 <b>{float(judge.get('weighted') or 0):.2f}/10</b>　|　技能采纳率 <b>{adoption * 100:.0f}%</b></div>
 {cov_html}
 {f'<div class="box">盲评意见：{esc(judge.get("comment"))}</div>' if judge.get('comment') else ''}
 <footer>
   本文件由执行器输出渲染，内容为<b>研究方案与要点</b>（非实验结论）；参数取值与判据需在真实数据上验证后采用。<br>
   SkillNet-S1 · 产物指纹 <code>{esc(meta.get('digest', ''))}</code>
 </footer>
</div></body></html>"""


def render_bundle(task: str, plan: dict[str, Any], judge: dict[str, Any],
                  skills: list[str], adoption: float) -> dict[str, Any]:
    """渲染产物包：返回 {files: [{name, kind, body, bytes}], meta}。不落盘（由调用方决定）。"""
    slug = task_slug(task)
    steps, code_files = split_code_blocks(list(plan.get("steps") or []))
    plan_clean = dict(plan)
    plan_clean["steps"] = steps
    meta = {"slug": slug}
    md = build_markdown(task, plan_clean, judge, skills, adoption, meta)
    html = build_html(task, plan_clean, judge, skills, adoption, meta, code_files)
    digest = hashlib.sha256((md + html).encode("utf-8")).hexdigest()[:12]
    meta["digest"] = digest
    # digest 参与页脚，重渲染一次保持一致（确定性）
    html = build_html(task, plan_clean, judge, skills, adoption, meta, code_files)
    files = [
        {"name": "report.html", "kind": "研究报告（HTML）", "body": html, "bytes": len(html.encode("utf-8"))},
        {"name": "plan.md", "kind": "方案 Markdown", "body": md, "bytes": len(md.encode("utf-8"))},
    ]
    for f in code_files:
        files.append({"name": f["name"], "kind": f"代码（{f['lang']}）", "body": f["body"],
                      "bytes": len(f["body"].encode("utf-8"))})
    return {"files": files, "meta": meta}


def save_bundle(bundle: dict[str, Any], out_dir) -> list[dict[str, Any]]:
    """把产物写入磁盘，返回可展示的清单（含相对索引，供 /api/artifact 取用）。"""
    import pathlib
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    for f in bundle["files"]:
        if f.get("_copy_only"):            # 沙箱产物已落盘（二进制），不再覆写
            manifest.append({"name": f["name"], "kind": f["kind"], "bytes": f["bytes"],
                             "slug": bundle["meta"]["slug"]})
            continue
        p = out_dir / f["name"]
        p.write_text(f["body"], encoding="utf-8")
        manifest.append({
            "name": f["name"], "kind": f["kind"], "bytes": f["bytes"],
            "slug": bundle["meta"]["slug"],
        })
    return manifest


# ======================================================================
# 交付物真实生成（回应「清单里说的东西在哪」）
# ======================================================================
# 背景：执行方案会声明一份「交付物清单」（如"泄漏审计报告""蒙特卡洛验证代码"），
# 但那只是**承诺**——早先的产物层只把方案本身渲染成报告，清单里的东西并不存在。
# 这里补上兑现环节：逐项生成实际内容并落盘。
#
# 诚实约束（重要）：
# - 生成的是**方案级产出**（文本/代码/表格骨架），不是真实实验结论；
# - 提示词明确要求标注「需在真实数据上验证」，禁止编造实验结果数字；
# - 生成失败如实降级并说明，绝不假装成功。

DELIVERABLE_SCHEMA = """{
  "deliverables": [
    {"name": "文件名（含扩展名，如 leak-audit-report.md / monte_carlo.py）",
     "kind": "doc|code|table",
     "content": "完整内容本身（不是对内容的描述）",
     "note": "一句话说明该产物是什么、可信度边界"}
  ]
}"""

_KIND_EXT = {"doc": ".md", "code": ".py", "table": ".csv"}


def safe_filename(name: str, kind: str) -> str:
    """文件名安全化：保留中文/字母/数字/-_.，其余替换为 -，并补正确扩展名。

    必须做：交付物名称来自模型输出，直接当路径用会有穿越与非法字符风险。
    """
    base = str(name or "").strip().replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^\w\u4e00-\u9fff.\-]+", "-", base, flags=re.UNICODE).strip("-._") or "deliverable"
    ext = _KIND_EXT.get(kind, ".md")
    stem, _, old = base.rpartition(".")
    if not stem or len(old) > 5:            # 无扩展名或扩展名异常
        base = base + ext
    return base[:80]


def generate_deliverables(task: str, plan: dict[str, Any], skills: list[str],
                          max_items: int = 6, max_tokens: int = 8000) -> dict[str, Any]:
    """按方案声明的交付物清单逐项生成真实内容。

    返回 {"files": [...], "error": "", "declared": N, "generated": M}。
    任何失败（无密钥 / JSON 异常 / 内容过短）都如实返回 error，不抛异常阻断主链路。
    """
    from . import llm

    declared = [str(a) for a in (plan.get("artifacts") or []) if str(a).strip()]
    if not declared:
        return {"files": [], "error": "", "declared": 0, "generated": 0}

    steps_txt = "\n".join(
        f"S{i}. {st.get('action', '') if isinstance(st, dict) else st}"
        for i, st in enumerate(plan.get("steps") or [], 1))
    prompt = f"""研究任务：
{task}

已确定的执行方案：
思路：{plan.get('approach') or ''}
步骤：
{steps_txt}
已加载技能：{'、'.join(skills) if skills else '（无）'}

方案的交付物清单（共 {len(declared)} 项）：
{chr(10).join('- ' + d for d in declared)}

请为其中最重要的 {min(max_items, len(declared))} 项生成**实际内容**——不是描述它应该包含什么，
而是把它本身写出来。要求：
1. doc 类：完整 Markdown 正文（标题、章节、具体条目），不低于 400 字；
2. code 类：可直接运行的 Python 代码（含 import、主函数、示例调用与注释），不低于 30 行；
3. table 类：CSV 文本，含表头与 5 行以上示例数据（数据须标注为示意值）；
4. 内容具体到参数、阈值、判据；范本条款/清单类要给出可直接套用的条目；
5. **诚实红线**：这是方案级产出，凡涉及实验结果的数字必须标注「示意值，需真实数据验证」，
   不得编造具体实验结论；不确定处显式写明。

严格输出 JSON（不要额外文字）：
{DELIVERABLE_SCHEMA}"""

    try:
        obj = llm.chat_json(
            [{"role": "system", "content": "你是科研方案交付物撰写助手，输出严格 JSON。"},
             {"role": "user", "content": prompt}],
            role="executor", temperature=0.3, max_tokens=max_tokens)
    except Exception as exc:                       # 无密钥 / 网络 / 解析失败
        return {"files": [], "error": f"交付物生成失败：{exc}", "declared": len(declared), "generated": 0}

    raw = obj.get("deliverables") if isinstance(obj, dict) else None
    if not isinstance(raw, list):
        return {"files": [], "error": "交付物生成返回格式异常（缺 deliverables 数组）",
                "declared": len(declared), "generated": 0}

    files: list[dict[str, Any]] = []
    for d in raw[:max_items]:
        if not isinstance(d, dict):
            continue
        content = str(d.get("content") or "").strip()
        if len(content) < 120:                     # 过短视为生成失败（防占位符）
            continue
        kind = str(d.get("kind") or "doc").lower()
        kind = kind if kind in _KIND_EXT else "doc"
        fname = safe_filename(str(d.get("name") or f"deliverable_{len(files) + 1}"), kind)
        files.append({
            "name": fname,
            "kind": f"方案交付物（{kind}）",
            "body": content if content.endswith("\n") else content + "\n",
            "bytes": len(content.encode("utf-8")),
            "note": str(d.get("note") or ""),
            "declared_as": str(d.get("name") or ""),
        })
    err = "" if files else "模型未产出足够长度的交付物内容"
    return {"files": files, "error": err, "declared": len(declared), "generated": len(files)}


# ======================================================================
# 沙箱执行产物的收集（供演示页直接预览图片/数据）
# ======================================================================
def collect_execution_artifacts(result: dict[str, Any], dest_dir, prefix: str = "step1") -> list[dict[str, Any]]:
    """把沙箱产出的文件复制到产物目录（平铺 + 加前缀），返回展示清单。

    平铺的原因：预览接口按 `demo_artifacts/{slug}/{name}` 一层寻址，
    沙箱的 try1/try2 子目录结构不适合直接暴露给前端。
    """
    import pathlib as _pl
    import shutil as _sh
    dest = _pl.Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    for a in result.get("artifacts", []):
        src = _pl.Path(a["path"])
        if not src.is_file():
            continue
        name = f"{prefix}_{src.name}"
        try:
            _sh.copy2(src, dest / name)
        except OSError:
            continue
        out.append({
            "name": name, "kind": "真实运行产物",
            "bytes": (dest / name).stat().st_size,
            "previewable_image": src.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg"),
        })
    return out
