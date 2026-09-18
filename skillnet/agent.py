"""技能驱动的研究 Agent 执行器。

三种运行风格，对应评估里的三档对照：
  bare   —— 不给任何技能（No Skill 基线）
  cards  —— 只给技能卡的 L1 元数据（模拟朴素 RAG：检索到名字就注入）
  guided —— 给出技能的完整 SKILL.md 正文（L2/L3 渐进披露，本 demo 的完整方案）

执行者与评审者分离（立理 S1 的独立评审设计），评审见 judge.py。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .catalog import SkillLibrary
from .llm import chat

STYLE_BARE = "bare"
STYLE_CARDS = "cards"
STYLE_GUIDED = "guided"

_RESP_SCHEMA = """{
  "approach": "一段话说明整体研究思路",
  "steps": [
    {"skill": "使用的技能名（没有就写 manual）",
     "action": "这一步具体做什么",
     "key_params": ["关键参数或阈值及取值理由"],
     "expected_output": "这一步应产出什么",
     "check": "怎么判断这一步做对了"}
  ],
  "risks": ["可能出错的地方与应对"],
  "artifacts": ["最终交付物清单"]
}"""


@dataclass
class AgentRun:
    task: str
    style: str
    skills: list[str] = field(default_factory=list)
    response: dict[str, Any] = field(default_factory=dict)
    raw: str = ""
    usage: dict[str, Any] = field(default_factory=dict)

    @property
    def adoption(self) -> float:
        """技能采纳率（完全客观，不受 LLM 评审噪声影响）。

        给定技能集里，有多少个真的出现在了方案的 skill 字段中。
        这是判断"技能是否被激活"最直接的指标 —— 社区评测（Vercel agent evals）
        发现默认配置下技能在 56% 的用例里根本没被调用，因此这个指标必须单独看。
        """
        if not self.skills:
            return 0.0
        used = set()
        for st in self.response.get("steps") or []:
            if isinstance(st, dict):
                name = str(st.get("skill", "")).strip()
                if name and name.lower() != "manual":
                    used.add(name)
        if not used:
            return 0.0
        return len(used & set(self.skills)) / len(set(self.skills))

    @property
    def trajectory(self) -> str:
        """把一次执行压缩成可供蒸馏的轨迹文本。"""
        parts = [f"任务: {self.task}"]
        if self.skills:
            parts.append("可用技能: " + ", ".join(self.skills))
        r = self.response
        if r.get("approach"):
            parts.append("思路: " + str(r["approach"]))
        for i, st in enumerate(r.get("steps") or [], 1):
            if not isinstance(st, dict):
                continue
            parts.append(
                f"步骤{i} [{st.get('skill','manual')}] {st.get('action','')} "
                f"| 参数: {', '.join(map(str, st.get('key_params') or []))[:200]} "
                f"| 产出: {st.get('expected_output','')} "
                f"| 校验: {st.get('check','')}"
            )
        if r.get("risks"):
            parts.append("风险: " + "; ".join(map(str, r["risks"])))
        if r.get("artifacts"):
            parts.append("交付物: " + "; ".join(map(str, r["artifacts"])))
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "style": self.style,
            "skills": self.skills,
            "response": self.response,
            "usage": self.usage,
        }


class ResearchAgent:
    """面向科研任务的技能驱动 Agent。"""

    def __init__(self, lib: SkillLibrary, *, model: str | None = None) -> None:
        self.lib = lib
        self.model = model

    # ------------------------------------------------------------------
    def _skill_block(self, names: list[str], style: str) -> str:
        if not names:
            return ""
        blocks = []
        for n in names:
            s = self.lib.get(n)
            if not s:
                continue
            if style == STYLE_CARDS:
                blocks.append(
                    f"- {s.name}：{s.description}\n"
                    f"  能力：{s.capability}\n"
                    f"  适用：{'；'.join(s.use_when[:2])}"
                )
            else:
                blocks.append(s.to_skill_md())
        if style == STYLE_CARDS:
            return "【可用技能（仅元数据）】\n" + "\n".join(blocks)
        return "【可用技能（完整定义）】\n" + "\n\n---\n\n".join(blocks)

    def run(
        self,
        task: str,
        *,
        skills: list[str] | None = None,
        style: str = STYLE_GUIDED,
        max_tokens: int = 3200,
    ) -> AgentRun:
        skills = skills or []
        if style == STYLE_BARE:
            skills = []
        block = self._skill_block(skills, style)

        system = (
            "你是立理 S1 的科研执行 Agent，擅长把复杂研究目标拆成可执行、可验证的研究步骤。"
            "你的输出必须具体到参数、工具与判据，避免空泛的方法论描述。"
        )
        if block:
            system += (
                "\n下面提供的技能是你已经掌握的操作性知识。"
                "当某个技能的适用条件与任务匹配时，请在对应步骤中直接调用它，"
                "并遵循其步骤、陷阱与验证清单。"
            )

        user = f"【研究任务】\n{task}\n\n"
        if block:
            user += block + "\n\n"
        user += (
            "请给出完成该任务的研究执行方案。要求：\n"
            "1. 步骤控制在 4–6 步，每步写明用什么技能或工具、关键参数取值及理由；\n"
            "2. 必须包含对结果可靠性的验证方式（如何证明这一步没做错）；\n"
            "3. 指出最可能出错的环节及应对，不超过 4 条；\n"
            "4. 若提供了技能且与任务匹配，步骤中的 skill 字段必须填对应的技能名；\n"
            "5. 控制篇幅，直接输出 JSON，不要写解释性文字。\n\n"
            f"严格输出 JSON：\n{_RESP_SCHEMA}"
        )

        raw = chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            role="executor",
            temperature=0.2,
            max_tokens=max_tokens,
            model=self.model,
        )
        parsed = _safe_json(raw)
        return AgentRun(task=task, style=style, skills=skills, response=parsed, raw=raw)

    # ------------------------------------------------------------------
    def execute_first_step(self, run: AgentRun) -> dict[str, Any]:
        """把方案的第一步真正展开：产出可运行的分析代码骨架。

        用于证明技能不只是被「引用」，而是真的改变了执行产物。
        """
        steps = run.response.get("steps") or []
        if not steps:
            return {}
        first = steps[0] if isinstance(steps[0], dict) else {}
        used = first.get("skill", "manual")
        skill = self.lib.get(used)
        prompt = (
            f"研究任务：{run.task}\n\n"
            f"第一步：{first.get('action','')}\n"
            + (f"\n参考技能定义：\n{skill.to_skill_md()[:2500]}\n" if skill else "")
            + "\n请写出这一步的 Python 代码骨架（含导入、关键参数与断言检查），"
            "只输出代码，不要解释。"
        )
        code = chat(
            [{"role": "user", "content": prompt}],
            role="executor",
            temperature=0.1,
            max_tokens=1200,
            model=self.model,
        )
        return {"skill": used, "action": first.get("action", ""), "code": code.strip()}


def _safe_json(text: str) -> dict[str, Any]:
    from .llm import extract_json

    try:
        out = extract_json(text)
        return out if isinstance(out, dict) else {"approach": str(out)}
    except Exception:  # noqa: BLE001
        return {"approach": text.strip()[:1500], "steps": [], "risks": [], "artifacts": [],
                "_parse_failed": True}


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)
