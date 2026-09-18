"""技能数据模型。

对照三篇文献的抽象：
- SkillNet (arXiv:2603.04448) 的三层本体：Taxonomy / Relation Graph / Package，
  以及 Skill Contract（capability / inputs / outputs / use_when）。
- DisCo (arXiv:2609.02749) 的「技能图 + 验证记录」。
- COBRA-Skills (arXiv:2609.11682) 把技能看作可被评估与改写的候选臂。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

RELATION_TYPES = ("depend_on", "compose_with", "similar_to", "belong_to")
QUALITY_DIMENSIONS = (
    "safety",
    "completeness",
    "executability",
    "maintainability",
    "cost_awareness",
)
GRADES = ("Good", "Average", "Poor")


@dataclass
class SkillContract:
    """技能卡：让检索与关系构建可以只读摘要而不读全文（Fabric 的 contract）。"""

    capability: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    use_when: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def flat(self) -> str:
        return " ".join(
            [self.capability, *self.inputs, *self.outputs, *self.use_when]
        )


@dataclass
class Skill:
    """一个可被 Agent 加载执行的技能。"""

    name: str
    description: str
    domain: str
    tags: list[str] = field(default_factory=list)
    capability: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    use_when: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    pitfalls: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    quality: dict[str, str] = field(default_factory=dict)
    relations: list[tuple[str, str]] = field(default_factory=list)
    source: str = "seed"
    origin_task: str | None = None       # 由哪条任务蒸馏而来
    parent: list[str] = field(default_factory=list)  # 变异/交叉的父技能
    generation: int = 0                  # 0 = 种子技能
    version: int = 1

    # ---- 运行期统计（老虎机 / 评估回填）----
    stats: dict[str, float] = field(
        default_factory=lambda: {"pulls": 0.0, "reward_sum": 0.0, "best": 0.0}
    )

    # ------------------------------------------------------------------
    @property
    def contract(self) -> SkillContract:
        return SkillContract(
            capability=self.capability,
            inputs=list(self.inputs),
            outputs=list(self.outputs),
            use_when=list(self.use_when),
        )

    @property
    def mean_reward(self) -> float:
        pulls = self.stats.get("pulls", 0.0)
        return self.stats.get("reward_sum", 0.0) / pulls if pulls else 0.0

    @property
    def uid(self) -> str:
        return hashlib.md5(self.name.encode("utf-8")).hexdigest()[:10]

    # ---- 检索文本（L1 metadata，对标 ADK 渐进披露的第一层）----
    def l1_text(self) -> str:
        """只含 name + description + contract 的轻量检索文本。"""
        return " ".join(
            [
                self.name.replace("-", " "),
                self.description,
                self.domain,
                " ".join(self.tags),
                self.capability,
                " ".join(self.use_when),
            ]
        )

    def l2_text(self) -> str:
        """完整 SKILL.md 正文文本。"""
        return " ".join(
            [self.l1_text(), *self.steps, *self.pitfalls, *self.verification]
        )

    # ---- 序列化 ----
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["relations"] = [list(r) for r in self.relations]
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Skill":
        d = dict(d)
        d["relations"] = [tuple(r) for r in d.get("relations", [])]
        known = {f for f in Skill.__dataclass_fields__}
        return Skill(**{k: v for k, v in d.items() if k in known})

    # ---- 渲染为 SKILL.md（agentskills.io / Claude Code / ADK 通用格式）----
    def to_skill_md(self) -> str:
        fm = {
            "name": self.name,
            "description": self.description,
        }
        lines = ["---"]
        for k, v in fm.items():
            lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.name}")
        lines.append("")
        lines.append(f"> 领域：{self.domain}　|　来源：{self.source}"
                     f"　|　代际：G{self.generation}")
        lines.append("")
        lines.append("## 能力契约 / Capability")
        lines.append("")
        lines.append(self.capability)
        lines.append("")
        lines.append("**输入**：" + "；".join(self.inputs))
        lines.append("")
        lines.append("**输出**：" + "；".join(self.outputs))
        lines.append("")
        lines.append("**适用时机**：")
        lines.extend(f"- {u}" for u in self.use_when)
        lines.append("")
        lines.append("## 执行步骤")
        lines.append("")
        for i, s in enumerate(self.steps, 1):
            lines.append(f"{i}. {s}")
        if self.pitfalls:
            lines.append("")
            lines.append("## 常见陷阱")
            lines.append("")
            lines.extend(f"- {p}" for p in self.pitfalls)
        if self.verification:
            lines.append("")
            lines.append("## 验证清单")
            lines.append("")
            lines.extend(f"- [ ] {v}" for v in self.verification)
        if self.tags:
            lines.append("")
            lines.append("## 标签")
            lines.append("")
            lines.append("`" + "` `".join(self.tags) + "`")
        if self.quality:
            lines.append("")
            lines.append("## 质量评估")
            lines.append("")
            lines.append("| 维度 | 评级 |")
            lines.append("| --- | --- |")
            for dim in QUALITY_DIMENSIONS:
                lines.append(f"| {dim} | {self.quality.get(dim, 'Average')} |")
        if self.relations:
            lines.append("")
            lines.append("## 关联技能")
            lines.append("")
            for rel, target in self.relations:
                lines.append(f"- `{rel}` → `{target}`")
        if self.parent:
            lines.append("")
            lines.append(f"<!-- 演化自：{', '.join(self.parent)} -->")
        return "\n".join(lines) + "\n"


def quality_score(quality: dict[str, str]) -> float:
    """把三维评级折算成 0-1 的权重，用于检索排序的先验。"""
    grade = {"Good": 1.0, "Average": 0.6, "Poor": 0.25}
    if not quality:
        return 0.6
    vals = [grade.get(quality.get(d, "Average"), 0.6) for d in QUALITY_DIMENSIONS]
    return sum(vals) / len(vals)


def dedup_key(skill: Skill) -> str:
    return hashlib.md5(skill.to_skill_md().encode("utf-8")).hexdigest()


def iter_targets(skills: Iterable[Skill]) -> list[str]:
    return [s.name for s in skills]
