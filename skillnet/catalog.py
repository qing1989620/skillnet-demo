"""技能库（SkillNet 本体）的构建、加载与持久化。

对应 SkillNet 论文的三层本体：
  Taxonomy（domain/tags） -> Relation Graph（relations） -> Package（seed/skills 目录）
"""
from __future__ import annotations

import json
import os
import pathlib
import threading
import time
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
    """技能库：内存中的技能集合 + 关系图 + 反向索引。

    并发设计：所有内存读写都在一把可重入锁内完成，遍历类方法返回**副本**。
    否则当 `/api/evolve` 正在往库里加技能时，并发的 `/api/search`
    会在遍历做召回时抛 `RuntimeError: dictionary changed size during iteration`。
    锁只覆盖内存操作，**不覆盖 LLM 调用**（秒级，持锁会拖垮并发）。

    持久化设计：落盘只写「演化产生的技能」+「运行期统计」，不写种子技能。
    加载时用 `build_seed_skills()` 重建种子再叠加这两部分——
    这样代码升级带来的种子技能更新能自动生效，而演化成果与学习到的统计不会丢。
    """

    def __init__(self, skills: list[Skill] | None = None) -> None:
        self._lock = threading.RLock()
        self.skills: dict[str, Skill] = {}
        for s in skills or []:
            self.add(s)
        self.dirty = False          # 初始化不算修改

    # ------------------------------------------------------------------
    def add(self, skill: Skill) -> Skill:
        with self._lock:
            self.skills[skill.name] = skill
            self.dirty = True
        return skill

    def get(self, name: str) -> Skill | None:
        with self._lock:
            return self.skills.get(name)

    def remove(self, name: str) -> Skill | None:
        with self._lock:
            got = self.skills.pop(name, None)
            if got is not None:
                self.dirty = True
            return got

    def __len__(self) -> int:
        with self._lock:
            return len(self.skills)

    def __iter__(self):
        return iter(self.all())

    def __contains__(self, name: object) -> bool:
        with self._lock:
            return name in self.skills

    def all(self) -> list[Skill]:
        with self._lock:
            return list(self.skills.values())

    def names(self) -> list[str]:
        with self._lock:
            return list(self.skills.keys())

    # ------------------------------------------------------------------
    def by_domain(self) -> dict[str, list[Skill]]:
        out: dict[str, list[Skill]] = {}
        for s in self.all():
            out.setdefault(s.domain, []).append(s)
        return out

    def neighbours(
        self, name: str, rel_types: tuple[str, ...] = ("compose_with", "depend_on")
    ) -> list[tuple[str, str]]:
        """无向邻接：既返回出边也返回入边，返回 (关系, 技能名)。"""
        snapshot = self.all()
        present = {s.name for s in snapshot}
        out: list[tuple[str, str]] = []
        node = next((s for s in snapshot if s.name == name), None)
        if node:
            for rel, tgt in node.relations:
                if rel in rel_types and tgt in present:
                    out.append((rel, tgt))
        for other in snapshot:
            for rel, tgt in other.relations:
                if tgt == name and rel in rel_types:
                    out.append((rel, other.name))
        return out

    def relation_edges(self) -> list[dict[str, str]]:
        snapshot = self.all()
        present = {s.name for s in snapshot}
        return [
            {"source": s.name, "target": tgt, "type": rel}
            for s in snapshot
            for rel, tgt in s.relations
            if tgt in present
        ]

    def duplicates(self) -> list[tuple[str, str]]:
        seen: dict[str, str] = {}
        dups = []
        for s in self.all():
            k = dedup_key(s)
            if k in seen:
                dups.append((seen[k], s.name))
            else:
                seen[k] = s.name
        return dups

    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        snapshot = self.all()
        domains = self.by_domain()
        gen: dict[str, int] = {}
        for s in snapshot:
            gen[f"G{s.generation}"] = gen.get(f"G{s.generation}", 0) + 1
        edges = self.relation_edges()
        edge_types: dict[str, int] = {}
        for e in edges:
            edge_types[e["type"]] = edge_types.get(e["type"], 0) + 1
        qsum = sum(quality_score(s.quality) for s in snapshot)
        return {
            "total": len(snapshot),
            "domains": len(domains),
            "domain_distribution": {k: len(v) for k, v in sorted(domains.items())},
            "edges": len(edges),
            "edge_types": edge_types,
            "generations": gen,
            "avg_quality": round(qsum / max(1, len(snapshot)), 3),
            "evolved": sum(1 for s in snapshot if s.source != "seed"),
            "total_pulls": int(sum(s.stats.get("pulls", 0) for s in snapshot)),
        }

    # ------------------------------------------------------------------
    def save(self, path=None) -> str:
        """原子落盘：先写临时文件再 `os.replace`，避免写一半被读到或进程中断损坏文件。"""
        p = pathlib.Path(path or config.LIBRARY_FILE)
        snapshot = self.all()
        payload = {
            "schema_version": 2,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            # 只存演化技能：种子技能由代码提供，这样升级代码时种子更新能自动生效
            "evolved": [s.to_dict() for s in snapshot if s.source != "seed"],
            # 统计（老虎机回填的实测奖励）按技能名单独存
            "stats": {
                s.name: s.stats for s in snapshot if s.stats.get("pulls", 0) > 0
            },
        }
        text = json.dumps(payload, ensure_ascii=False, indent=1)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, p)
        self.dirty = False
        return str(p)

    @classmethod
    def load(cls, path=None) -> "SkillLibrary":
        """种子技能 + 演化技能 + 统计，三层叠加。"""
        lib = cls(build_seed_skills())
        p = pathlib.Path(path or config.LIBRARY_FILE)
        if not p.exists():
            return lib
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[catalog] 技能库文件损坏，已回退到种子技能：{exc}")
            return lib

        for d in data.get("evolved") or []:
            try:
                lib.add(Skill.from_dict(d))
            except (TypeError, ValueError) as exc:
                print(f"[catalog] 跳过一条无法解析的演化技能：{exc}")
        for name, st in (data.get("stats") or {}).items():
            s = lib.get(name)
            if s is not None and isinstance(st, dict):
                s.stats = {**s.stats, **st}
        lib.dirty = False
        return lib

    @classmethod
    def fresh(cls) -> "SkillLibrary":
        """从种子重建（清掉所有演化出来的技能与统计）。"""
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
