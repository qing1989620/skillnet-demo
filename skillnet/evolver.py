"""技能进化：蒸馏 / 变异 / 交叉 / 再生成，以及入库准入检查。

算子设计直接对照三篇文献：
  distill      —— DisCo 的 task-oriented 蒸馏：从一次真实执行轨迹提炼技能
  mutate       —— COBRA-Skills 的 rollout mutation：依据刚获得的成功/失败轨迹修补技能
  crossover    —— COBRA-Skills 的 crossover：高分技能作主干，借鉴另一高分技能，
                  低分技能作负面证据
  regenerate   —— COBRA-Skills 的 regeneration：跳出局部，从任务本身独立提炼新策略

外加 SkillNet 的准入过滤：去重 + 质量门槛，防止技能库被污染。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .catalog import SkillLibrary
from .index import jaccard, tokenize
from .llm import chat_json
from .schema import Skill

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

SKILL_SCHEMA_HINT = """{
  "name": "kebab-case 英文技能名（小写字母数字与连字符，不超过 48 字符）",
  "description": "一两句话说明这个技能做什么、什么时候该用（中文）",
  "domain": "所属领域（中文，尽量复用已有领域名）",
  "tags": ["检索关键词", "..."],
  "capability": "能力契约：一句话说清它能产出什么",
  "inputs": ["需要的输入", "..."],
  "outputs": ["产出的结果", "..."],
  "use_when": ["什么时机该激活这个技能", "..."],
  "steps": ["可执行步骤，含关键参数与工具", "..."],
  "pitfalls": ["常见陷阱与失败模式", "..."],
  "verification": ["怎么验证结果是可靠的", "..."],
  "relations": [{"type": "compose_with|depend_on|similar_to", "target": "已有技能名"}]
}"""


@dataclass
class EvolveRecord:
    op: str
    name: str
    accepted: bool
    reason: str
    parent: list[str] = field(default_factory=list)


class SkillEvolver:
    def __init__(self, lib: SkillLibrary, *, sim_threshold: float = 0.72) -> None:
        self.lib = lib
        self.sim_threshold = sim_threshold
        self.records: list[EvolveRecord] = []

    # ------------------------------------------------------------------
    # 准入检查（SkillNet 的 filtering / deduplication）
    # ------------------------------------------------------------------
    def _admit(self, raw: dict[str, Any], op: str, parents: list[str]) -> Skill | None:
        name = str(raw.get("name", "")).strip().lower().replace("_", "-")
        name = re.sub(r"[^a-z0-9\-]", "-", name).strip("-")
        name = re.sub(r"-{2,}", "-", name)
        if not name:
            self.records.append(EvolveRecord(op, "<invalid>", False, "技能名为空"))
            return None
        if not NAME_RE.match(name):
            self.records.append(EvolveRecord(op, name, False, "技能名不符合 kebab-case"))
            return None
        if name in self.lib.skills:
            self.records.append(EvolveRecord(op, name, False, "与已有技能重名"))
            return None

        steps = [s for s in (raw.get("steps") or []) if str(s).strip()]
        if len(steps) < 3:
            self.records.append(
                EvolveRecord(op, name, False, f"步骤过少（{len(steps)} 条），判定为不完整")
            )
            return None

        # 语义去重：与现有技能高度重合则拒绝。
        # 用 max(Jaccard, 0.9×重叠系数)：Jaccard 对长度差异敏感，
        # 而新技能的文本通常比 l1_text 短，单靠 Jaccard 会漏掉明显的冗余技能。
        text = " ".join(
            [
                str(raw.get("description", "")),
                str(raw.get("capability", "")),
                " ".join(str(x) for x in (raw.get("use_when") or [])),
            ]
        )
        new_tokens = tokenize(text)
        for s in self.lib:
            old_tokens = tokenize(s.l1_text())
            jac = jaccard(new_tokens, old_tokens)
            inter = len(set(new_tokens) & set(old_tokens))
            overlap = inter / max(1, min(len(set(new_tokens)), len(set(old_tokens))))
            sim = max(jac, overlap * 0.9)
            if sim > self.sim_threshold:
                self.records.append(
                    EvolveRecord(
                        op, name, False,
                        f"与 {s.name} 语义重合度过高（sim={sim:.2f}），判定为冗余",
                    )
                )
                return None

        rels: list[tuple[str, str]] = []
        for r in raw.get("relations") or []:
            if isinstance(r, dict):
                t = str(r.get("target", ""))
                ty = str(r.get("type", "compose_with"))
                if t in self.lib.skills and ty in (
                    "compose_with", "depend_on", "similar_to", "belong_to"
                ):
                    rels.append((ty, t))
        # 保底：与父技能建立关系
        for p in parents:
            if p in self.lib.skills and not any(t == p for _, t in rels):
                rels.append(("compose_with", p))

        skill = Skill(
            name=name,
            description=str(raw.get("description", "")).strip(),
            domain=str(raw.get("domain", "未分类")).strip() or "未分类",
            tags=[str(t) for t in (raw.get("tags") or [])][:8],
            capability=str(raw.get("capability", "")).strip(),
            inputs=[str(x) for x in (raw.get("inputs") or [])][:6],
            outputs=[str(x) for x in (raw.get("outputs") or [])][:6],
            use_when=[str(x) for x in (raw.get("use_when") or [])][:6],
            steps=[str(x) for x in steps][:12],
            pitfalls=[str(x) for x in (raw.get("pitfalls") or [])][:8],
            verification=[str(x) for x in (raw.get("verification") or [])][:8],
            quality={
                "safety": "Average",
                "completeness": "Average",
                "executability": "Average",
                "maintainability": "Average",
                "cost_awareness": "Average",
            },
            relations=rels,
            source=op,
            parent=parents,
            generation=max([self.lib.skills[p].generation for p in parents if p in self.lib.skills] or [0]) + 1,
        )
        self.lib.add(skill)
        self.records.append(
            EvolveRecord(op, name, True, f"G{skill.generation} 新技能入库", parents)
        )
        return skill

    # ------------------------------------------------------------------
    # 算子 1：从执行轨迹蒸馏（DisCo / Trace2Skill 路线）
    # ------------------------------------------------------------------
    def distill(
        self, task: str, trajectory: str, *, score: float, parent: list[str] | None = None
    ) -> Skill | None:
        prompt = (
            "你是一个技能蒸馏器。下面是科研 Agent 完成一个任务的执行轨迹。\n"
            "请从轨迹中提炼出**可迁移的操作性知识**（不是复述这道题的答案），"
            "写成一个新的可复用技能。\n"
            "要求：\n"
            "1. 只提炼方法、参数、陷阱与验证方式，禁止写入具体训练题、标准答案或任务 ID；\n"
            "2. 步骤必须是可执行的动作，而不是抽象建议；\n"
            "3. 若轨迹中存在失败与修正，把修正后的做法写进步骤，把失败模式写进 pitfalls。\n\n"
            f"【任务】\n{task}\n\n"
            f"【执行轨迹】\n{trajectory[:6000]}\n\n"
            f"【该次执行得分】{score:.2f}（1 分制）\n\n"
            f"严格输出 JSON，字段如下：\n{SKILL_SCHEMA_HINT}"
        )
        raw = chat_json(
            [{"role": "user", "content": prompt}],
            role="teacher",
            temperature=0.35,
            max_tokens=3500,
            default={},
        )
        if not isinstance(raw, dict) or not raw:
            self.records.append(EvolveRecord("distill", "<llm-failed>", False, "模型未返回有效技能"))
            return None
        return self._admit(raw, "distill", parent or [])

    # ------------------------------------------------------------------
    # 算子 2：轨迹变异（COBRA-Skills 的 rollout mutation）
    # ------------------------------------------------------------------
    def mutate(
        self,
        base_name: str,
        *,
        successes: list[str],
        failures: list[str],
    ) -> Skill | None:
        base = self.lib.get(base_name)
        if base is None:
            return None
        prompt = (
            "你在做技能迭代。下面是一个已有技能，以及它刚刚产生的成功与失败执行记录。\n"
            "请做**有依据的局部修改**：把成功记录中有效的做法固化进步骤，"
            "针对失败记录补上陷阱与规避方式。不要推翻整体结构，也不要把技能改成另一个主题。\n\n"
            f"【原技能】\n{base.to_skill_md()[:4000]}\n\n"
            f"【成功记录】\n{chr(10).join(successes)[:2500] or '（无）'}\n\n"
            f"【失败记录】\n{chr(10).join(failures)[:2500] or '（无）'}\n\n"
            "请输出**修改后的新版本技能**（技能名需与原技能不同，建议在原名后加版本后缀），"
            f"字段如下：\n{SKILL_SCHEMA_HINT}"
        )
        raw = chat_json(
            [{"role": "user", "content": prompt}],
            role="teacher",
            temperature=0.3,
            max_tokens=3500,
            default={},
        )
        if not isinstance(raw, dict) or not raw:
            return None
        return self._admit(raw, "mutate", [base_name])

    # ------------------------------------------------------------------
    # 算子 3：交叉（COBRA-Skills 的 crossover）
    # ------------------------------------------------------------------
    def crossover(self, backbone: str, donor: str, negatives: list[str]) -> Skill | None:
        b, d = self.lib.get(backbone), self.lib.get(donor)
        if not b or not d:
            return None
        negs = [self.lib.get(n) for n in negatives]
        neg_txt = "\n\n".join(
            f"【低分技能：{n.name}】\n{n.to_skill_md()[:1200]}" for n in negs if n
        ) or "（无）"
        prompt = (
            "你在做技能交叉。规则很严格：\n"
            "1. 以【主干技能】的框架为主体，保持它的结构；\n"
            "2. 从【供体技能】中**只借鉴一个**可靠策略并说明它解决了主干技能的什么缺口；\n"
            "3. 【低分技能】仅作为负面证据，用来避免某些错误做法；\n"
            "4. 禁止把多份文本直接拼接成一段大杂烩。\n\n"
            f"【主干技能（高分）】\n{b.to_skill_md()[:3000]}\n\n"
            f"【供体技能（高分）】\n{d.to_skill_md()[:2500]}\n\n"
            f"{neg_txt}\n\n"
            f"输出一个新技能，字段如下（技能名需与主干、供体都不同）：\n{SKILL_SCHEMA_HINT}"
        )
        raw = chat_json(
            [{"role": "user", "content": prompt}],
            role="teacher",
            temperature=0.35,
            max_tokens=3500,
            default={},
        )
        if not isinstance(raw, dict) or not raw:
            return None
        return self._admit(raw, "crossover", [backbone, donor])

    # ------------------------------------------------------------------
    # 算子 4：再生成（COBRA-Skills 的 regeneration）
    # ------------------------------------------------------------------
    def regenerate(self, task_cluster: str, *, reference_traces: list[str] | None = None) -> Skill | None:
        refs = "\n\n".join(reference_traces or [])[:3000] or "（无参考轨迹）"
        prompt = (
            "下面是一类科研任务的描述，以及若干条**没有技能辅助**时的执行轨迹。\n"
            "请独立提炼出能提升这类任务表现的新策略，写成一个技能。\n"
            "要求打开新的搜索方向，不要与常规做法雷同。\n\n"
            f"【任务类型】\n{task_cluster}\n\n"
            f"【无技能执行轨迹】\n{refs}\n\n"
            f"字段如下：\n{SKILL_SCHEMA_HINT}"
        )
        raw = chat_json(
            [{"role": "user", "content": prompt}],
            role="teacher",
            temperature=0.5,
            max_tokens=3500,
            default={},
        )
        if not isinstance(raw, dict) or not raw:
            return None
        return self._admit(raw, "regenerate", [])

    # ------------------------------------------------------------------
    def summary(self) -> dict[str, Any]:
        ok = [r for r in self.records if r.accepted]
        return {
            "attempts": len(self.records),
            "accepted": len(ok),
            "rejected": len(self.records) - len(ok),
            "by_operator": {
                op: {
                    "attempts": sum(1 for r in self.records if r.op == op),
                    "accepted": sum(1 for r in self.records if r.op == op and r.accepted),
                }
                for op in ("distill", "mutate", "crossover", "regenerate")
            },
            "records": [
                {"op": r.op, "name": r.name, "accepted": r.accepted,
                 "reason": r.reason, "parent": r.parent}
                for r in self.records
            ],
        }
