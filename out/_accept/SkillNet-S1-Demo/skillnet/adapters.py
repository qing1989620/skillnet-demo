"""跨框架适配：一套技能库，导出成各 Agent 客户端可直接加载的形式。

两个已核实的事实基础（决定了本模块的设计）：

1. **格式统一**：Google ADK 自 v1.25 起通过 `SkillToolset` 支持 Skills，遵循
   agentskills.io 目录规范（SKILL.md + references/ + assets/ + scripts/），
   官方文档明确说明「为 Claude Code / Cursor / Gemini CLI 编写的技能目录
   可用 `load_skill_from_dir` 原样加载」。
   → 所以技能文件本身只需一份，不需要为每个框架写转换器。

2. **发现路径不统一**：文件格式一样，但各家去哪里找不一样。
   Claude Code 读 `.claude/skills/`，Codex 读 `.agents/skills/`（从当前目录向上找），
   Cursor 从 v2.4 起读 `.cursor/skills/`，Gemini CLI 另有位置。
   → 所以导出时要**一次写全多个落点**，而不是只给一个 `.claude/skills/`
   让使用者自己去拷贝。
   （实践中常见的做法是保留一份权威副本 + 软链，这里为降低使用门槛直接写多份。）

导出物：
  agent_skills/  四种客户端的技能目录（.claude / .agents / .cursor / .gemini）
  AGENTS.md      仓库级技能索引（调研显示它在部分评测中比技能机制更可靠地提升通过率）
  google_adk/    skills/ + 可直接运行的 agent.py（SkillToolset）
  openai_tools/  tools.json（function calling 形式的技能路由工具集）+ 技能索引
  index/         SKILLS_INDEX.md（压缩文档索引，作为对照方案）
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .catalog import SkillLibrary

# 技能名白名单。导出时会把技能名当目录名用，而 `SkillLibrary.load()` 读进来的
# 技能可能来自外部数据（演化技能是模型生成后落盘的），因此必须校验，
# 否则一个精心构造的技能名就能把文件写到仓库之外。
SAFE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

#: 各 Agent 客户端的技能目录落点
SKILLS_DIRS: dict[str, str] = {
    "claude_code": ".claude/skills",
    "codex": ".agents/skills",
    "cursor": ".cursor/skills",
    "gemini_cli": ".gemini/skills",
}


def _safe_dir_name(name: str) -> str:
    if not SAFE_NAME.match(name) or len(name) > 64:
        raise ValueError(f"技能名不合法或含路径字符，拒绝导出：{name!r}")
    return name


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

AGENTS_MD_TEMPLATE = """# 技能库索引

本仓库的技能遵循 agentskills.io 规范组织，共 **{n_skills} 个技能**，
覆盖 **{n_domains} 个领域**。由 SkillNet-S1 生成。

## 技能目录落点

不同 Agent 客户端去不同的地方找技能，同一份 SKILL.md 已写入以下全部位置：

| 客户端 | 目录 |
|---|---|
| Claude Code | `.claude/skills/` |
| Codex | `.agents/skills/` |
| Cursor | `.cursor/skills/` |
| Gemini CLI | `.gemini/skills/` |

## 使用方式

当任务与某个技能的适用条件匹配时，读取它的 `SKILL.md`，
严格按其中的执行步骤操作，并遵守「常见陷阱」与「验证清单」两节。

## 技能激活提示

社区评测（Vercel agent evals）发现：默认配置下技能有相当比例**从未被调用**，
而把技能索引直接放进仓库级指令文件反而更稳定。因此本文件本身就是索引的一部分。

如果观察到技能未被激活，在这里补一条显式触发规则即可，例如：

> 当任务涉及 {example_domain} 时，必须先检查并加载 `{example_skill}` 技能。

{skill_list}
"""


# ======================================================================
def export_agent_skills(lib: SkillLibrary, out: Path, targets: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """把技能写入各 Agent 客户端的技能目录，并生成仓库级 AGENTS.md。"""
    base = out / "agent_skills"
    targets = targets or SKILLS_DIRS
    exported: list[dict[str, Any]] = []

    for client, rel in targets.items():
        root = base / rel
        n = 0
        for s in lib:
            d = root / _safe_dir_name(s.name)
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text(s.to_skill_md(), encoding="utf-8")
            n += 1
        exported.append({
            "framework": client,
            "path": str(root),
            "rel_path": rel,
            "skills": n,
            "entry": f"{rel}/<name>/SKILL.md",
        })

    # 仓库级指令文件：调研显示它在部分评测里比技能机制更可靠地触发调用
    sample = next(iter(lib.all()), None)
    lines = ["", "## 技能清单", ""]
    for domain, skills in sorted(lib.by_domain().items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"**{domain}**（{len(skills)}）")
        lines.append("")
        for s in sorted(skills, key=lambda x: x.name):
            lines.append(f"- `{s.name}` — {s.capability or s.description}")
        lines.append("")

    (base / "AGENTS.md").write_text(
        AGENTS_MD_TEMPLATE.format(
            n_skills=len(lib),
            n_domains=len(lib.by_domain()),
            example_domain=sample.domain if sample else "文献检索",
            example_skill=sample.name if sample else "literature-review",
            skill_list="\n".join(lines),
        ),
        encoding="utf-8",
    )
    exported.append({
        "framework": "agents_md",
        "path": str(base / "AGENTS.md"),
        "rel_path": "AGENTS.md",
        "skills": len(lib),
        "entry": "仓库级指令文件（把技能索引直接放进 agent 上下文）",
    })
    return exported


def export_google_adk(lib: SkillLibrary, out: Path, *, model: str = "gemini-flash-latest") -> dict[str, Any]:
    base = out / "google_adk"
    skill_root = base / "skills"
    for s in lib:
        d = skill_root / _safe_dir_name(s.name)
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
        "rel_path": "google_adk/skills",
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
        "rel_path": "openai_tools",
        "skills": len(lib),
        "entry": "tools.json + skill_index.json",
    }


def export_flat_index(lib: SkillLibrary, out: Path) -> dict[str, Any]:
    """导出「压缩文档索引」方案（作为对照：不加载技能、只给索引）。"""
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
        "rel_path": "index/SKILLS_INDEX.md",
        "skills": len(lib),
        "chars": len(text),
        "entry": "SKILLS_INDEX.md",
    }


def export_all(lib: SkillLibrary, out_dir: Path) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return [
        *export_agent_skills(lib, out_dir),
        export_google_adk(lib, out_dir),
        export_openai_tools(lib, out_dir),
        export_flat_index(lib, out_dir),
    ]
