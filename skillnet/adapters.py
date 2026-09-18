"""跨框架适配：一套技能库，导出成各 Agent 框架可直接加载的形式。

已核实的事实基础：
- Google ADK 从 v1.25 起通过 SkillToolset 支持 Skills，遵循 agentskills.io 目录规范
  （SKILL.md + references/ + assets/ + scripts/），并自动生成三级工具：
  list_skills(L1) / load_skill(L2) / load_skill_resource(L3)。
  ADK 官方文档明确：为 Claude Code / Cursor / Gemini CLI 编写的技能目录
  可用 load_skill_from_dir 原样加载。
- 因此本 demo 的 SKILL.md 目录是唯一真源，Claude Code、ADK、Cursor 共享同一份产物。

导出物：
  claude_code/  .claude/skills/<name>/SKILL.md  +  CLAUDE.md 索引
  google_adk/   skills/<name>/SKILL.md          +  agent.py（可直接跑的 ADK Agent）
  openai_tools/ tools.json（function calling 形式的技能路由工具集）
  index/        SKILLS_INDEX.md（压缩文档索引方案，用于对照「技能是否被激活」）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .catalog import SkillLibrary

ADK_AGENT_TEMPLATE = '''"""由 SkillNet-S1 自动生成的 Google ADK Agent。

用法：
    pip install google-adk
    export GOOGLE_API_KEY=...        # 或使用 Vertex AI
    python agent.py                  # 或者 `adk web` 打开可视化调试

说明：技能目录遵循 agentskills.io 规范，本文件用官方 API 原样加载，
不需要对技能做任何格式转换。
"""
from __future__ import annotations

import pathlib

from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset

SKILLS_DIR = pathlib.Path(__file__).parent / "skills"


def build_skills():
    if not SKILLS_DIR.exists():
        return []
    return [
        load_skill_from_dir(d)
        for d in sorted(SKILLS_DIR.iterdir())
        if d.is_dir() and (d / "SKILL.md").exists()
    ]


skill_toolset_instance = skill_toolset.SkillToolset(skills=build_skills())

root_agent = Agent(
    model="{model}",
    name="liliai_s1_skillnet_agent",
    description=(
        "面向科研任务的技能驱动 Agent。技能库由 SkillNet-S1 构建、评估与演化，"
        "覆盖 {n_domains} 个科研领域共 {n_skills} 项技能。"
    ),
    instruction=(
        "你是科研执行助手。当任务匹配某个技能的适用条件时，"
        "必须先调用 load_skill 读取该技能的完整指令，再严格按其中的步骤、"
        "陷阱与验证清单执行。不要凭常识绕过技能中给出的验证步骤。"
    ),
    tools=[skill_toolset_instance],
)
'''

CLAUDE_MD_TEMPLATE = """# 项目技能库（SkillNet-S1 生成）

本目录下的 `.claude/skills/` 由 SkillNet-S1 构建并持续演化，
共 {n_skills} 个技能，覆盖 {n_domains} 个科研领域。

## 使用方式
技能按 agentskills.io 规范组织：每个技能一个目录，入口为 `SKILL.md`。
当你判断某个技能与当前任务匹配时，读取它的 `SKILL.md` 并严格按其步骤执行。

## 技能激活率提示
社区评测（Vercel agent evals）发现：默认配置下技能可能大量不被调用。
若技能未被激活，请在本文件顶部补充显式的触发短语，例如：
「当任务涉及 {example_domain} 时，必须优先检查并加载 `{example_skill}` 技能。」
"""


def export_claude_code(lib: SkillLibrary, out: Path) -> dict[str, Any]:
    base = out / "claude_code"
    skill_root = base / ".claude" / "skills"
    for s in lib:
        d = skill_root / s.name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(s.to_skill_md(), encoding="utf-8")
    sample = next(iter(lib.all()), None)
    (base / "CLAUDE.md").write_text(
        CLAUDE_MD_TEMPLATE.format(
            n_skills=len(lib),
            n_domains=len(lib.by_domain()),
            example_domain=sample.domain if sample else "文献检索",
            example_skill=sample.name if sample else "literature-review",
        ),
        encoding="utf-8",
    )
    return {
        "framework": "claude_code",
        "path": str(skill_root),
        "skills": len(lib),
        "entry": ".claude/skills/<name>/SKILL.md",
    }


def export_google_adk(lib: SkillLibrary, out: Path, *, model: str = "gemini-flash-latest") -> dict[str, Any]:
    base = out / "google_adk"
    skill_root = base / "skills"
    for s in lib:
        d = skill_root / s.name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(s.to_skill_md(), encoding="utf-8")
    (base / "agent.py").write_text(
        ADK_AGENT_TEMPLATE.format(
            model=model, n_skills=len(lib), n_domains=len(lib.by_domain())
        ),
        encoding="utf-8",
    )
    (base / "requirements.txt").write_text("google-adk>=1.25\n", encoding="utf-8")
    return {
        "framework": "google_adk",
        "path": str(skill_root),
        "skills": len(lib),
        "entry": "agent.py（SkillToolset + load_skill_from_dir）",
    }


def export_openai_tools(lib: SkillLibrary, out: Path) -> dict[str, Any]:
    """导出 function-calling 形式的技能路由工具集。

    设计对齐 ADK 的渐进披露：先用轻量索引做发现，再按需加载全文，
    避免把几千个技能的正文一次性塞进上下文。
    """
    base = out / "openai_tools"
    base.mkdir(parents=True, exist_ok=True)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_skills",
                "description": (
                    "按语义检索技能库，返回最相关的技能摘要（L1 元数据）。"
                    "当不确定该用哪个技能时先调用本工具。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "研究任务或需求描述"},
                        "k": {"type": "integer", "description": "返回条数，默认 5"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": "加载指定技能的完整定义（步骤、陷阱、验证清单）并严格遵循执行。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "技能名（kebab-case）"}
                    },
                    "required": ["name"],
                },
            },
        },
    ]
    index = [
        {
            "name": s.name,
            "description": s.description,
            "domain": s.domain,
            "capability": s.capability,
            "inputs": s.inputs,
            "outputs": s.outputs,
            "use_when": s.use_when,
        }
        for s in lib
    ]
    (base / "tools.json").write_text(
        json.dumps(tools, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (base / "skill_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return {
        "framework": "openai_tools",
        "path": str(base),
        "skills": len(lib),
        "entry": "tools.json + skill_index.json",
    }


def export_flat_index(lib: SkillLibrary, out: Path) -> dict[str, Any]:
    """导出「压缩文档索引」方案（Vercel 评测中优于技能机制的对照）。

    用于本 demo 的额外消融：把全部技能描述压成一个 Markdown 索引塞进系统提示。
    """
    base = out / "index"
    base.mkdir(parents=True, exist_ok=True)
    lines = ["# 技能索引", "", f"共 {len(lib)} 个技能，按领域分组。", ""]
    for domain, skills in sorted(lib.by_domain().items()):
        lines.append(f"## {domain}")
        lines.append("")
        for s in sorted(skills, key=lambda x: x.name):
            lines.append(f"- **{s.name}** — {s.capability}（适用：{'；'.join(s.use_when[:2])}）")
        lines.append("")
    text = "\n".join(lines)
    (base / "SKILLS_INDEX.md").write_text(text, encoding="utf-8")
    return {
        "framework": "flat_index",
        "path": str(base),
        "skills": len(lib),
        "chars": len(text),
        "entry": "SKILLS_INDEX.md",
    }


def export_all(lib: SkillLibrary, out_dir: Path) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return [
        export_claude_code(lib, out_dir),
        export_google_adk(lib, out_dir),
        export_openai_tools(lib, out_dir),
        export_flat_index(lib, out_dir),
    ]
