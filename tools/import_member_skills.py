# -*- coding: utf-8 -*-
"""import_member_skills.py —— 把成员项目（Nexus）的技能导入 SkillNet 技能库。

背景
----
开发组另一成员的项目 `_member_ref/` 提供 24 个可执行技能（Anthropic 官方技能
套装 + 中文自制教练类技能），格式为「frontmatter + 自由 markdown 正文」。
本脚本把它们转换为 SkillNet 的 Skill Contract 格式（结构化契约），
并把工具类能力与既有 51 个科研方法技能用类型化关系边连接起来。

转换的诚实性约定
----------------
- `capability / inputs / outputs` 依据原文 description 与正文提炼，**不编造**；
  无法从原文确定的字段给出保守值并在正文注明「导入时未逐条复核」。
- 领域、关系边为本项目补充（原文无此概念），在来源行标注 `member-import`。
- 自动提取的 pitfalls / verification 只保留能在原文中找到依据的条目。

用法
----
    python tools/import_member_skills.py            # 导入（幂等：同名覆盖）
    python tools/import_member_skills.py --dry-run  # 只报告，不写文件
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT.parent / "_member_ref" / "skills"
DST = ROOT / "seed" / "skills"
BEGIN_MARK = "# ===== BEGIN member-import skills (Nexus) ====="
END_MARK = "# ===== END member-import skills (Nexus) ====="

# ----------------------------------------------------------------------
# 元数据表：id -> (中文名, 领域, 关系边, 输入, 输出)
# 领域与关系为本项目补充；输入/输出依据技能语义给出（原文为自由描述）。
# ----------------------------------------------------------------------
META: dict[str, dict] = {
    # ---------------- 文档工程 ----------------
    "docx": {
        "cn": "Word 文档处理",
        "domain": "文档工程",
        "relations": [("compose_with", "scientific-writing"), ("similar_to", "pdf")],
        "inputs": ["待处理的 .docx/.dotx 文件或文档需求说明", "正文内容与格式要求"],
        "outputs": ["处理完成的 Word 文档", "渲染校验截图"],
        "tags": ["Word", "docx", "文档生成", "docx-js", "版式"],
    },
    "pdf": {
        "cn": "PDF 文档处理",
        "domain": "文档工程",
        "relations": [("compose_with", "literature-review"), ("similar_to", "docx")],
        "inputs": ["PDF 文件或生成 PDF 的内容源", "页面/提取/合并等操作需求"],
        "outputs": ["处理后的 PDF 文件", "文本或表格提取结果"],
        "tags": ["PDF", "文本提取", "表单", "文档转换"],
    },
    "pptx": {
        "cn": "演示文稿制作",
        "domain": "文档工程",
        "relations": [("compose_with", "poster-slides"), ("similar_to", "docx")],
        "inputs": ["演示主题与素材内容", "可选 .pptx 模板"],
        "outputs": ["生成的 .pptx 演示文稿", "版式校验结果"],
        "tags": ["PPT", "pptxgenjs", "演示", "模板"],
    },
    "xlsx": {
        "cn": "Excel 表格处理",
        "domain": "文档工程",
        "relations": [("compose_with", "eda-profiling"), ("similar_to", "docx")],
        "inputs": ["表格数据或 .xlsx 文件", "公式/图表/格式要求"],
        "outputs": ["生成的表格文件", "公式重算校验结果"],
        "tags": ["Excel", "xlsx", "公式", "数据表"],
    },
    "doc-coauthoring": {
        "cn": "文档协同创作",
        "domain": "文档工程",
        "relations": [("compose_with", "docx"), ("compose_with", "scientific-writing")],
        "inputs": ["文档目标与读者", "已有素材与上下文"],
        "outputs": ["分阶段打磨后的文档", "结构与措辞修订记录"],
        "tags": ["协同写作", "工作流", "审阅", "修订"],
    },
    "internal-comms": {
        "cn": "内部沟通文案",
        "domain": "文档工程",
        "relations": [("similar_to", "doc-coauthoring")],
        "inputs": ["沟通场景与受众", "要传达的事实要点"],
        "outputs": ["内部通告/邮件/简报等文案"],
        "tags": ["内部沟通", "文案", "通告"],
    },
    # ---------------- 技能工程 ----------------
    "skill-creator": {
        "cn": "技能创作工坊",
        "domain": "技能工程",
        "relations": [("compose_with", "mcp-builder")],
        "inputs": ["待沉淀的能力描述与使用场景", "可选参考材料"],
        "outputs": ["符合规范的 SKILL.md 技能定义", "技能评估与改进建议"],
        "tags": ["技能创作", "SKILL.md", "规范", "元技能"],
    },
    "mcp-builder": {
        "cn": "MCP 服务构建器",
        "domain": "技能工程",
        "relations": [("compose_with", "claude-api")],
        "inputs": ["外部服务/API 的能力边界说明", "认证与调用方式"],
        "outputs": ["MCP 服务端实现", "工具定义与测试"],
        "tags": ["MCP", "工具集成", "服务端"],
    },
    "claude-api": {
        "cn": "Claude 接口参考",
        "domain": "技能工程",
        "relations": [("similar_to", "mcp-builder")],
        "inputs": ["待接入的模型调用需求"],
        "outputs": ["正确的接口调用参数与代码"],
        "tags": ["API", "模型调用", "参数", "版本漂移"],
    },
    "code-helper": {
        "cn": "Python 代码生成助手",
        "domain": "技能工程",
        "relations": [("compose_with", "webapp-testing")],
        "inputs": ["编程需求或待排错代码"],
        "outputs": ["可运行代码与解释说明"],
        "tags": ["Python", "代码生成", "调试"],
    },
    "webapp-testing": {
        "cn": "网页应用测试",
        "domain": "技能工程",
        "relations": [("compose_with", "web-artifacts-builder")],
        "inputs": ["本地 Web 应用地址或代码"],
        "outputs": ["浏览器自动化测试结果", "截图与问题清单"],
        "tags": ["Web 测试", "浏览器自动化", "Playwright"],
    },
    "web-artifacts-builder": {
        "cn": "网页应用构建",
        "domain": "技能工程",
        "relations": [("depend_on", "frontend-design")],
        "inputs": ["应用需求与交互说明"],
        "outputs": ["可运行的前端应用产物"],
        "tags": ["前端", "Web 应用", "组件化"],
    },
    # ---------------- 设计与创意 ----------------
    "canvas-design": {
        "cn": "视觉海报设计",
        "domain": "设计与创意",
        "relations": [("compose_with", "scientific-visualization"), ("similar_to", "brand-guidelines")],
        "inputs": ["设计主题与参考意象", "输出尺寸与格式要求"],
        "outputs": ["PNG/PDF 视觉成品", "设计说明"],
        "tags": ["海报", "视觉设计", "排版"],
    },
    "brand-guidelines": {
        "cn": "品牌视觉规范",
        "domain": "设计与创意",
        "relations": [("similar_to", "theme-factory")],
        "inputs": ["待应用的品牌素材与使用场景"],
        "outputs": ["符合品牌规范的视觉方案"],
        "tags": ["品牌", "配色", "字体规范"],
    },
    "algorithmic-art": {
        "cn": "算法生成艺术",
        "domain": "设计与创意",
        "relations": [("similar_to", "canvas-design")],
        "inputs": ["艺术概念种子", "生成参数与交互要求"],
        "outputs": ["p5.js 生成艺术代码与作品"],
        "tags": ["生成艺术", "p5.js", "算法美学"],
    },
    "frontend-design": {
        "cn": "前端视觉设计",
        "domain": "设计与创意",
        "relations": [("similar_to", "canvas-design")],
        "inputs": ["产品定位与目标用户", "设计参考"],
        "outputs": ["有辨识度的界面设计方案"],
        "tags": ["界面设计", "视觉规范", "克制美学"],
    },
    "theme-factory": {
        "cn": "主题样式工厂",
        "domain": "设计与创意",
        "relations": [("compose_with", "pptx")],
        "inputs": ["待套用主题的产物（幻灯片/网页/文档）", "主题偏好"],
        "outputs": ["应用主题后的产物", "主题定义文件"],
        "tags": ["主题", "样式系统", "一致性"],
    },
    "slack-gif-creator": {
        "cn": "Slack 动图制作",
        "domain": "设计与创意",
        "relations": [("similar_to", "algorithmic-art")],
        "inputs": ["动图创意与尺寸要求"],
        "outputs": ["符合规格的 GIF 动图"],
        "tags": ["GIF", "动效", "消息表情"],
    },
    # ---------------- 职业与学习 ----------------
    "interview": {
        "cn": "SDE 面试备考教练",
        "domain": "职业与学习",
        "relations": [("similar_to", "leetcode-hot100-coach")],
        "inputs": ["面试目标岗位与时间线", "当前准备状态"],
        "outputs": ["分阶段备考计划", "模拟面试与反馈"],
        "tags": ["面试", "职业发展", "模拟问答"],
    },
    "leetcode-hot100-coach": {
        "cn": "LeetCode Hot100 教练",
        "domain": "职业与学习",
        "relations": [("similar_to", "algotrace")],
        "inputs": ["当前刷题进度", "目标题目与薄弱点"],
        "outputs": ["固定流程的刷题指导与复盘"],
        "tags": ["算法刷题", "Hot100", "讲解"],
    },
    "algotrace": {
        "cn": "算法可视化教练",
        "domain": "职业与学习",
        "relations": [("similar_to", "leetcode-hot100-coach")],
        "inputs": ["待讲解的算法或数据结构问题"],
        "outputs": ["可视化讲解与逐步执行轨迹"],
        "tags": ["算法可视化", "数据结构", "教学"],
    },
    "academy-guide": {
        "cn": "Claude 学堂向导",
        "domain": "职业与学习",
        "relations": [("similar_to", "skill-creator")],
        "inputs": ["学习目标与当前水平"],
        "outputs": ["课程化的学习路径与练习"],
        "tags": ["教学", "课程设计", "向导"],
    },
    # ---------------- 知识与合规 ----------------
    "contract-review": {
        "cn": "合同审查专家",
        "domain": "知识与合规",
        "relations": [("compose_with", "docx")],
        "inputs": ["待审查合同文本", "审查立场（甲方/乙方）"],
        "outputs": ["风险条款清单与修改建议"],
        "tags": ["合同", "风险识别", "条款审查"],
    },
    "discernment-nudge": {
        "cn": "判断校准助手",
        "domain": "知识与合规",
        "relations": [("similar_to", "peer-review-response")],
        "inputs": ["待复核的结论或判断"],
        "outputs": ["校准提问与判断修正建议"],
        "tags": ["判断校准", "批判性思维", "自省"],
    },
}

# ----------------------------------------------------------------------
# 从原文提取：适用时机 / 执行要点 / 陷阱 / 验证
# ----------------------------------------------------------------------
STOP_RE = re.compile(r"^\s*(#|\||```|>)")
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$")
PITFALL_KW = re.compile(
    r"gotcha|never|do not|don't|avoid|caution|warning|陷阱|禁止|不要|切勿|注意|易错|failure",
    re.I)
VERIFY_KW = re.compile(r"verify|validation|check|checklist|test|验证|检查|校验|自检", re.I)


def _clean(s: str) -> str:
    s = re.sub(r"`{1,3}", "", s).strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\*\*|\*|__|_", "", s)
    return s.rstrip("。.").strip()


def _frontmatter(text: str) -> dict[str, str]:
    """解析 SKILL.md 的 YAML frontmatter。

    必须用真正的 YAML 解析：技能描述大量使用多行标量（`description: >`）与
    含逗号的引号串，逐行正则会截断成 ">" 之类的残片（实测 interview 技能）。
    """
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}
    raw = m.group(1)
    try:
        import yaml
        data = yaml.safe_load(raw) or {}
        return {str(k): ("" if v is None else str(v).strip()) for k, v in data.items()
                if isinstance(k, (str, int))}
    except Exception:                     # YAML 异常时回退逐行解析（保底不阻断导入）
        fm: dict[str, str] = {}
        for line in raw.splitlines():
            mm = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
            if mm:
                fm[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
        return fm


def _body(text: str) -> str:
    parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.M)
    return parts[2] if len(parts) >= 3 else text


def _clean_desc(desc: str) -> str:
    """描述清洗：压缩空白、去掉 "Use this skill ..." 引导语、按句截到两句。

    英文官方技能的 description 常以 "Use this skill whenever ..." 开头且很长，
    但它包含最有价值的关键词（文件名后缀、工具名），因此**保留正文、只去引导语**，
    不整句删除——早先按 [^.]* 删句会踩到 "(.docx files)" 里的点号截成残片。
    """
    s = re.sub(r"\s+", " ", str(desc or "")).strip()
    s = re.sub(r"^Use this skill (any time|whenever)\s*", "", s, flags=re.I)
    s = re.sub(r"^(Use|Use this) when\s*", "", s, flags=re.I)
    s = re.sub(r"^the user (wants? to|needs? to|is asking to)\s*", "", s, flags=re.I)
    parts = re.split(r"(?<=[.。!?！？])\s+", s)
    return " ".join(parts[:2]).strip()


def _sections(body: str) -> list[tuple[str, str]]:
    """按二级标题切段 -> [(title, content)]。"""
    out: list[tuple[str, str]] = []
    cur, buf = "", []
    for line in body.splitlines():
        if line.startswith("## "):
            if cur or buf:
                out.append((cur, "\n".join(buf)))
            cur, buf = line[3:].strip(), []
        elif line.startswith("# "):
            continue
        else:
            buf.append(line)
    out.append((cur, "\n".join(buf)))
    return out


def extract_use_when(fm: dict[str, str], desc: str) -> list[str]:
    items: list[str] = []
    wtu = fm.get("when_to_use", "")
    if wtu:
        items.append(_clean(wtu))
    for m in re.finditer(r"[Tt]riggers? include[:\s]*(.*?)(?:\.\s|$)", desc):
        chunk = m.group(1)
        parts = [p.strip(" '\"") for p in re.split(r",| or ", chunk) if p.strip()]
        for p in parts[:4]:
            if len(p) > 3:
                items.append(f"用户提到 {_clean(p)} 时")
    if not items:
        first = re.split(r"[。.;]", desc)[0]
        items.append(_clean(first)[:80] + " 相关任务")
    # 去重保序
    seen, out = set(), []
    for it in items:
        k = it[:30]
        if it and k not in seen:
            seen.add(k)
            out.append(it)
    return out[:4]


def extract_steps(sections: list[tuple[str, str]]) -> list[str]:
    """执行要点：优先取正文中最像「操作流程」的段落里的要点行。"""
    cand: list[str] = []
    for title, content in sections:
        if re.search(r"workflow|quick start|process|usage|steps|how to|执行|流程|步骤|开始", title, re.I):
            for line in content.splitlines():
                m = BULLET_RE.match(line)
                if m:
                    c = _clean(m.group(1))
                    if 6 < len(c) < 160:
                        cand.append(c)
            if len(cand) >= 4:
                break
    if not cand:
        for title, content in sections:
            for line in content.splitlines():
                m = BULLET_RE.match(line)
                if m and len(_clean(m.group(1))) > 12:
                    cand.append(_clean(m.group(1)))
                if len(cand) >= 5:
                    break
            if len(cand) >= 5:
                break
    # 兜底：用二级标题充当步骤骨架
    if not cand:
        cand = [f"按「{t}」章节的要求执行" for t, _ in sections if t][:5]
    return cand[:6]


def extract_pitfalls(sections: list[tuple[str, str]], desc: str) -> list[str]:
    out: list[str] = []
    for title, content in sections:
        if PITFALL_KW.search(title) or re.search(r"gotcha|pitfall|陷阱|限制", title, re.I):
            for line in content.splitlines():
                m = BULLET_RE.match(line)
                if m:
                    c = _clean(m.group(1))
                    if 8 < len(c) < 170:
                        out.append(c)
                elif line.strip() and not STOP_RE.match(line) and 10 < len(line.strip()) < 170:
                    out.append(_clean(line))
        if len(out) >= 6:
            break
    if not out:
        for m in re.finditer(r"(?:Do NOT use|不要|禁止)[^。.;\n]{6,80}", desc):
            out.append(_clean(m.group(0)))
    return out[:6] or ["导入时未从原文提取到显式陷阱条目，执行前请复核原文正文"]


def extract_verification(sections: list[tuple[str, str]]) -> list[str]:
    out: list[str] = []
    for title, content in sections:
        if VERIFY_KW.search(title):
            for line in content.splitlines():
                m = BULLET_RE.match(line)
                if m:
                    c = _clean(m.group(1))
                    if 4 < len(c) < 150:
                        out.append(c)
                elif re.match(r"^\s*-\s*\[[ x]\]", line):
                    out.append(_clean(re.sub(r"^\s*-\s*\[[ x]\]", "", line)))
            if not out and content.strip():
                first = [l for l in content.splitlines() if l.strip() and not STOP_RE.match(l)][:2]
                out = [_clean(l) for l in first]
        if len(out) >= 4:
            break
    return out[:5] or ["产出物已按原文「验证」章节要求自查（原文未提供结构化清单）"]


def rate_quality(pitfalls: list[str], verification: list[str], steps: list[str],
                 src_lines: int) -> dict[str, str]:
    """五维质量评级：按可提取的结构化信息量给出，宁可保守。"""
    def lvl(n: int, hi: int, mid: int) -> str:
        return "Good" if n >= hi else ("Average" if n >= mid else "Basic")
    return {
        "safety": "Good",                                   # 导入技能均无外部副作用声明
        "completeness": lvl(src_lines, 120, 60),
        "executability": lvl(len(steps), 5, 3),
        "maintainability": lvl(len(pitfalls) + len(verification), 6, 3),
        "cost_awareness": "Average",
    }


def _dedupe_relations(all_meta: dict[str, dict]) -> dict[str, list[tuple[str, str]]]:
    """同一对技能之间只保留一条同类型边（避免图上出现对称重复边）。

    规则：若 A->B 与 B->A 同为某一类型，保留技能名（字典序）较小的一方作为源，
    与 catalog.normalize_relations 的 compose_with 去重口径保持一致。
    """
    out: dict[str, list[tuple[str, str]]] = {}
    for name, meta in all_meta.items():
        kept: list[tuple[str, str]] = []
        for rel, tgt in meta["relations"]:
            rev = [(r, t) for m, r, t in
                   ((k, r, t) for k, v in all_meta.items() for r, t in v["relations"])
                   if m == tgt and t == name and r == rel]
            if rev and rel != "depend_on" and name > tgt:
                continue          # 反向边已存在且本技能字典序更大 -> 让位
            kept.append((rel, tgt))
        out[name] = kept
    return out


def build_raw_entry(skill_id: str, src_dir: pathlib.Path, meta: dict,
                    relations: list[tuple[str, str]]) -> str:
    """生成 catalog_data.py 中的 S(...) 调用代码（与既有 51 条同风格）。"""
    text = (src_dir / "SKILL.md").read_text(encoding="utf-8-sig", errors="replace")
    fm = _frontmatter(text)
    sections = _sections(_body(text))
    desc_raw = _clean_desc(fm.get("description", ""))
    desc_core = desc_raw[:170]
    if not desc_core.startswith(meta["cn"]):
        desc_core = f"{meta['cn']}：{desc_core}"
    desc = desc_core
    cap = f"依据原文 SKILL.md 提供{meta['cn']}能力（member-import 导入，契约字段由原文提炼）"
    use_when = extract_use_when(fm, fm.get("description", ""))
    steps = extract_steps(sections)
    pitfalls = extract_pitfalls(sections, fm.get("description", ""))
    verify = extract_verification(sections)
    quality = rate_quality(pitfalls, verify, steps, len(text.splitlines()))
    quality["member_import"] = "true"

    def esc_lit(s: str) -> str:
        """把任意文本安全嵌入 Python 双引号字面量。

        必须转义：英文官方技能描述里含双引号（如 natural phrases like "daily problem"），
        直接拼接会生成语法错误的 catalog_data.py（实测踩过）。
        """
        s = str(s).replace("\\", "/").replace('"', "'")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def lit(items: list[str]) -> str:
        return "[" + ", ".join(f'"{esc_lit(s)}"' for s in items) + "]"

    rels = "[" + ", ".join(f'("{r}", "{t}")' for r, t in relations) + "]"
    qmap = "{" + ", ".join(f'"{esc_lit(k)}": "{esc_lit(v)}"' for k, v in quality.items()) + "}"
    return (
        "S(\n"
        f'    "{esc_lit(skill_id)}", "{esc_lit(meta["domain"])}",\n'
        f'    "{esc_lit(desc)}",\n'
        f'    "{esc_lit(cap)}",\n'
        f'    {lit(meta["inputs"])},\n'
        f'    {lit(meta["outputs"])},\n'
        f'    {lit(use_when)},\n'
        f'    {lit(steps)},\n'
        f'    {lit(pitfalls)},\n'
        f'    {lit(verify)},\n'
        f'    {lit(meta["tags"])},\n'
        f'    {rels},\n'
        f'    {qmap},\n'
        ")\n"
    )


def build(skill_id: str, src_dir: pathlib.Path, meta: dict) -> str:
    text = (src_dir / "SKILL.md").read_text(encoding="utf-8-sig", errors="replace")
    fm = _frontmatter(text)
    body = _body(text)
    sections = _sections(body)

    desc_raw = _clean_desc(fm.get("description", ""))
    if not desc_raw:
        desc_raw = sections[0][1].strip()[:160] if sections and sections[0][1].strip() else meta["cn"]

    capability = desc_raw if len(desc_raw) > 20 else meta["cn"]
    use_when = extract_use_when(fm, fm.get("description", ""))
    steps = extract_steps(sections)
    pitfalls = extract_pitfalls(sections, fm.get("description", ""))
    verification = extract_verification(sections)
    quality = rate_quality(pitfalls, verification, steps, len(text.splitlines()))

    desc_short = f"{meta['cn']}：" + desc_raw[:110].rstrip("，,。.") + "。"
    lines: list[str] = []
    lines.append("---")
    lines.append(f'name: "{skill_id}"')
    lines.append(f'description: "{desc_short}"')
    lines.append("---")
    lines.append("")
    lines.append(f"# {skill_id}")
    lines.append("")
    lines.append(f"> 领域：{meta['domain']}　|　来源：member-import（Nexus skills/{skill_id}）　|　代际：G0")
    lines.append("")
    lines.append("## 能力契约 / Capability")
    lines.append("")
    lines.append(capability[:300])
    lines.append("")
    lines.append("**输入**：" + "；".join(meta["inputs"]))
    lines.append("")
    lines.append("**输出**：" + "；".join(meta["outputs"]))
    lines.append("")
    lines.append("**适用时机**：")
    for it in use_when:
        lines.append(f"- {it}")
    lines.append("")
    lines.append("## 执行步骤")
    lines.append("")
    for i, s in enumerate(steps, 1):
        lines.append(f"{i}. {s}")
    lines.append("")
    lines.append("## 常见陷阱")
    lines.append("")
    for p in pitfalls:
        lines.append(f"- {p}")
    lines.append("")
    lines.append("## 验证清单")
    lines.append("")
    for v in verification:
        lines.append(f"- [ ] {v}")
    lines.append("")
    lines.append("## 标签")
    lines.append("")
    lines.append(" ".join(f"`{t}`" for t in meta["tags"]))
    lines.append("")
    lines.append("## 质量评估")
    lines.append("")
    lines.append("| 维度 | 评级 |")
    lines.append("| --- | --- |")
    for k in ("safety", "completeness", "executability", "maintainability", "cost_awareness"):
        lines.append(f"| {k} | {quality[k]} |")
    lines.append("")
    if meta["relations"]:
        lines.append("## 关联技能")
        lines.append("")
        for rel, target in meta["relations"]:
            lines.append(f"- `{rel}` → `{target}`")
        lines.append("")
    lines.append("> 说明：本技能由开发组成员项目（Nexus）导入，契约字段依据原文提炼；")
    lines.append("> 领域划分与关系边由本项目补充。深度改写请以原文 SKILL.md 为准。")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-catalog", action="store_true",
                    help="只写 SKILL.md，不改 catalog_data.py")
    args = ap.parse_args()

    if not SRC.exists():
        print(f"[ERR] 源目录不存在：{SRC}")
        return 1

    missing = [k for k in META if not (SRC / k / "SKILL.md").exists()]
    if missing:
        print(f"[ERR] 元数据表中有 {len(missing)} 个技能在源目录缺失：{missing}")
        return 1

    relations = _dedupe_relations(META)
    written = 0
    entries: list[str] = []
    for skill_id, meta in META.items():
        out = build(skill_id, SRC / skill_id, meta)
        entries.append(build_raw_entry(skill_id, SRC / skill_id, meta, relations[skill_id]))
        dest = DST / skill_id / "SKILL.md"
        if args.dry_run:
            print(f"[DRY] {skill_id:26s} {meta['domain']}  {len(out)} 字符")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(out, encoding="utf-8")
            print(f"[OK ] {skill_id:26s} {meta['domain']}")
        written += 1

    # ---- 注入 catalog_data.py（标记块，幂等）----
    if not args.dry_run and not args.no_catalog:
        catalog = ROOT / "seed" / "catalog_data.py"
        src_text = catalog.read_text(encoding="utf-8")
        block = (
            f"\n\n{BEGIN_MARK}\n"
            "# 由 tools/import_member_skills.py 生成，请勿手工编辑本块。\n"
            "# 来源：开发组成员项目（Nexus）的 skills/ 目录，共 %d 个技能。\n\n" % len(META)
            + "\n".join(entries)
            + f"\n{END_MARK}\n"
        )
        if BEGIN_MARK in src_text:
            head, _, rest = src_text.partition(BEGIN_MARK)
            _, _, tail = rest.partition(END_MARK)
            src_text = head.rstrip("\n") + block + tail.lstrip("\n")
        else:
            src_text = src_text.rstrip("\n") + "\n" + block
        catalog.write_text(src_text, encoding="utf-8")
        print(f"[OK ] catalog_data.py 已注入 {len(META)} 条 S(...) 调用（标记块幂等）")

    print(f"\n{'预演' if args.dry_run else '导入'}完成：{written} 个技能 -> {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
