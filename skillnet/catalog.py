"""技能库（SkillNet 本体）的构建、加载与持久化。

对应 SkillNet 论文的三层本体：
  Taxonomy（domain/tags） -> Relation Graph（relations） -> Package（seed/skills 目录）
"""
from __future__ import annotations

import json
from typing import Any

from . import config
from .schema import Skill, dedup_key, quality_score

try:
    from seed.catalog_data import RAW
except ImportError:  # 允许从不同工作目录导入
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from seed.catalog_data import RAW


def normalize_relations(skills: list[Skill]) -> list[Skill]:
    """让关系图「可定向」，否则编排会凭空产生环。

    两条确定性规则：

    1. **依赖优先**：若 A `depend_on` B，则删除 B 中所有指向 A 的边。
       （A 依赖 B 已完整表达了先后，B 再声明指向 A 的 compose_with 就是矛盾。）
    2. **双向 compose_with 去重**：compose_with 语义上不表示先后，
       两侧都声明会让方向变得不确定（进而随机断环）。保留源技能名字典序较小的一条。

    这一步是必要的：本 demo 的自检发现，未规范化时「A 依赖 B」会在遍历 B 时
    被反向记成「B 依赖 A」，导致拓扑序把下游技能排到上游之前。
    """
    by = {s.name: s for s in skills}
    removed = 0

    # 规则 1：depend_on 优先
    for s in skills:
        for rel, tgt in list(s.relations):
            if rel != "depend_on":
                continue
            other = by.get(tgt)
            if not other:
                continue
            before = len(other.relations)
            other.relations = [
                (r, t) for r, t in other.relations
                if not (t == s.name and r in ("compose_with", "depend_on"))
            ]
            removed += before - len(other.relations)

    # 规则 2：双向 compose_with 去重
    for s in skills:
        for rel, tgt in list(s.relations):
            if rel != "compose_with":
                continue
            other = by.get(tgt)
            if not other:
                continue
            if any(r == "compose_with" and t == s.name for r, t in other.relations):
                if s.name < tgt:  # 保留字典序小的一方作为源
                    continue
                s.relations = [(r, t) for r, t in s.relations
                               if not (r == "compose_with" and t == tgt)]
                removed += 1

    if removed:
        print(f"[catalog] 关系规范化：消除 {removed} 条矛盾/重复边")
    return skills


def build_seed_skills() -> list[Skill]:
    """把目录数据实例化成 Skill 对象，校验目标存在性并规范化关系图。"""
    skills = [Skill(**item) for item in RAW]
    names = {s.name for s in skills}
    for s in skills:
        valid = [(rel, tgt) for rel, tgt in s.relations if tgt in names]
        dropped = [t for _, t in s.relations if t not in names]
        if dropped:
            print(f"[catalog] 技能 {s.name} 引用了不存在的技能，已丢弃: {dropped}")
        s.relations = valid
    return normalize_relations(skills)


class SkillLibrary:
    """技能库：内存中的技能集合 + 关系图 + 反向索引。"""

    def __init__(self, skills: list[Skill] | None = None) -> None:
        self.skills: dict[str, Skill] = {}
        for s in skills or []:
            self.add(s)

    # ------------------------------------------------------------------
    def add(self, skill: Skill) -> Skill:
        self.skills[skill.name] = skill
        return skill

    def get(self, name: str) -> Skill | None:
        return self.skills.get(name)

    def remove(self, name: str) -> Skill | None:
        return self.skills.pop(name, None)

    def __len__(self) -> int:
        return len(self.skills)

    def __iter__(self):
        return iter(self.skills.values())

    def all(self) -> list[Skill]:
        return list(self.skills.values())

    # ------------------------------------------------------------------
    def by_domain(self) -> dict[str, list[Skill]]:
        out: dict[str, list[Skill]] = {}
        for s in self.skills.values():
            out.setdefault(s.domain, []).append(s)
        return out

    def neighbours(
        self, name: str, rel_types: tuple[str, ...] = ("compose_with", "depend_on")
    ) -> list[tuple[str, str]]:
        """无向邻接：既返回出边也返回入边，返回 (关系, 技能名)。"""
        out: list[tuple[str, str]] = []
        node = self.skills.get(name)
        if node:
            for rel, tgt in node.relations:
                if rel in rel_types and tgt in self.skills:
                    out.append((rel, tgt))
        for other in self.skills.values():
            for rel, tgt in other.relations:
                if tgt == name and rel in rel_types:
                    out.append((rel, other.name))
        return out

    def relation_edges(self) -> list[dict[str, str]]:
        edges = []
        for s in self.skills.values():
            for rel, tgt in s.relations:
                if tgt in self.skills:
                    edges.append({"source": s.name, "target": tgt, "type": rel})
        return edges

    def duplicates(self) -> list[tuple[str, str]]:
        seen: dict[str, str] = {}
        dups = []
        for s in self.skills.values():
            k = dedup_key(s)
            if k in seen:
                dups.append((seen[k], s.name))
            else:
                seen[k] = s.name
        return dups

    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        domains = self.by_domain()
        gen = {}
        for s in self.skills.values():
            gen[f"G{s.generation}"] = gen.get(f"G{s.generation}", 0) + 1
        edges = self.relation_edges()
        edge_types: dict[str, int] = {}
        for e in edges:
            edge_types[e["type"]] = edge_types.get(e["type"], 0) + 1
        qsum = sum(quality_score(s.quality) for s in self.skills.values())
        return {
            "total": len(self.skills),
            "domains": len(domains),
            "domain_distribution": {k: len(v) for k, v in sorted(domains.items())},
            "edges": len(edges),
            "edge_types": edge_types,
            "generations": gen,
            "avg_quality": round(qsum / max(1, len(self.skills)), 3),
            "evolved": sum(1 for s in self.skills.values() if s.source != "seed"),
            "total_pulls": int(sum(s.stats.get("pulls", 0) for s in self.skills.values())),
        }

    # ------------------------------------------------------------------
    def save(self, path=None) -> str:
        p = path or config.LIBRARY_FILE
        payload = {
            "skills": [s.to_dict() for s in self.skills.values()],
            "edges": self.relation_edges(),
        }
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        return str(p)

    @classmethod
    def load(cls, path=None) -> "SkillLibrary":
        p = path or config.LIBRARY_FILE
        if not p.exists():
            return cls(build_seed_skills())
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls([Skill.from_dict(d) for d in data["skills"]])

    @classmethod
    def fresh(cls) -> "SkillLibrary":
        """从种子重建（清掉所有演化出来的技能）。"""
        return cls(build_seed_skills())


def export_skill_dirs(lib: SkillLibrary, out_dir=None) -> int:
    """把技能渲染成 SKILL.md 目录（agentskills.io 规范）。

    Claude Code / Google ADK / Cursor / Gemini CLI 可直接加载该目录。
    """
    base = out_dir or config.SEED_DIR
    base.mkdir(parents=True, exist_ok=True)
    n = 0
    for s in lib:
        d = base / s.name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(s.to_skill_md(), encoding="utf-8")
        n += 1
    return n
