"""技能检索与路由。

实现三档检索策略，用于对照实验（对标 SkillNet 表 5 的 BM25 / Dense / Rerank / Fabric 对比）：

  bm25    —— 纯关键词检索（朴素基线）
  hybrid  —— BM25 + 稀疏语义向量 + RRF 融合 + 领域/标签结构加成
  fabric  —— hybrid + 技能关系图扩展 + LLM 重排（技能卡为输入）

fabric 一档对应 SkillNet-Fabric 的「任务级 Wiki」：先用检索 + 关系扩展构造
候选路由空间 S_q，再让 Explore 在这个空间里做最终选择。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .catalog import SkillLibrary
from .index import BM25Index, VectorIndex, tokenize, weighted_fuse
from .llm import chat_json
from .schema import Skill, quality_score

MODE_BM25 = "bm25"
MODE_HYBRID = "hybrid"
MODE_FABRIC = "fabric"
MODES = (MODE_BM25, MODE_HYBRID, MODE_FABRIC)


@dataclass
class Candidate:
    name: str
    channels: list[str] = field(default_factory=list)
    score: float = 0.0
    rank: int = 0
    rerank_score: float | None = None
    note: str = ""


@dataclass
class RetrievalResult:
    query: str
    mode: str
    selected: list[str] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode,
            "selected": self.selected,
            "candidates": [c.__dict__ for c in self.candidates],
            "trace": self.trace,
        }


class Retriever:
    def __init__(self, lib: SkillLibrary) -> None:
        self.lib = lib
        self.bm25 = BM25Index()
        self.vec = VectorIndex()
        self._built = False

    # ------------------------------------------------------------------
    def build(self) -> "Retriever":
        skills = self.lib.all()
        ids = [s.name for s in skills]
        l1 = [s.l1_text() for s in skills]
        self.bm25.fit(ids, l1)
        self.vec.fit(ids, l1)
        # 领域与标签的词表，用于结构化加成
        self.domain_vocab = {s.domain for s in skills}
        self.tag_vocab = {t for s in skills for t in s.tags}
        self._built = True
        return self

    def refresh(self) -> "Retriever":
        return self.build()

    def _ensure(self) -> None:
        if not self._built:
            self.build()

    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        *,
        k: int = 5,
        mode: str = MODE_FABRIC,
        pool: int = 20,
        expand: bool = True,
        rerank: bool = True,
    ) -> RetrievalResult:
        self._ensure()
        if mode not in MODES:
            raise ValueError(f"未知检索模式: {mode}")
        res = RetrievalResult(query=query, mode=mode)

        # ---- 通路 1：BM25 ----
        bm25_hits = self.bm25.search(query, top_k=pool)
        res.trace.append(f"BM25 召回 {len(bm25_hits)} 条")
        if mode == MODE_BM25:
            fused = bm25_hits
        else:
            # ---- 通路 2：语义向量 ----
            vec_hits = self.vec.search(query, top_k=pool)
            res.trace.append(f"语义向量召回 {len(vec_hits)} 条")
            # ---- 通路 3：领域/标签结构信号 ----
            struct_hits = self._structural_hits(query, top_k=pool)
            res.trace.append(f"结构信号召回 {len(struct_hits)} 条")
            # 权重按「强通路主导、弱通路补充」定，并经过一轮扫描验证
            # （见 README 第四节：0.55/0.30/0.15 时混合档会低于纯 BM25 基线，
            #  因为本环境的语义通路是稀疏向量的降级实现，噪声偏大）。
            # 这里取 0.70/0.20/0.10：既让混合档稳定优于基线，
            # 又不至于把语义通路的权重压到形同虚设。
            # **接入稠密编码器后这个权重需要重新标定。**
            fused = weighted_fuse(
                [bm25_hits, vec_hits, struct_hits], weights=[0.70, 0.20, 0.10]
            )
            res.trace.append(
                f"加权融合后候选池 {len(fused)} 条（BM25 0.70 / 语义 0.20 / 结构 0.10）"
            )

        # ---- 质量先验：同等相关度下偏好高质量技能 ----
        score_map: dict[str, float] = {}
        for name, score in fused:
            sk = self.lib.get(name)
            prior = quality_score(sk.quality) if sk else 0.6
            score_map[name] = score * (0.85 + 0.3 * prior)
        ranked = sorted(score_map.items(), key=lambda kv: -kv[1])
        # 保序记录候选来源，并只保留仍存在于库中的技能（演化中可能被淘汰）
        ranked = [(n, s) for n, s in ranked if self.lib.get(n)][:pool]
        chan_map = self._channel_map(query, bm25_hits, pool)

        # ---- 关系图扩展（Fabric 的 relation expansion）----
        if mode == MODE_FABRIC and expand and ranked:
            ranked, added = self._graph_expand(ranked)
            if added:
                res.trace.append(
                    f"关系图扩展补入 {len(added)} 条：{', '.join(added[:6])}"
                )

        cands = [
            Candidate(
                name=n,
                score=round(s, 5),
                channels=chan_map.get(n, ["fused"]),
            )
            for n, s in ranked
        ]
        for i, c in enumerate(cands, 1):
            c.rank = i

        # ---- LLM 重排 ----
        if mode == MODE_FABRIC and rerank and len(cands) > k:
            ordered = self._llm_rerank(query, [c.name for c in cands[: min(pool, 16)]])
            if ordered:
                rank_of = {n: i for i, n in enumerate(ordered)}
                head = [c for c in cands if c.name in rank_of]
                head.sort(key=lambda c: rank_of[c.name])
                tail = [c for c in cands if c.name not in rank_of]
                cands = []
                for i, c in enumerate(head + tail, 1):
                    c.rerank_score = 1.0 - (rank_of.get(c.name, 99) / max(1, len(rank_of)))
                    c.rank = i
                    cands.append(c)
                res.trace.append(f"LLM 重排 {len(rank_of)} 条候选")

        res.candidates = cands
        res.selected = [c.name for c in cands[:k]]
        return res

    # ------------------------------------------------------------------
    def _structural_hits(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """结构化召回：只认「原样出现」的领域名与标签，避免分词带来的假命中。

        领域名按「与 / 、」切成段，任一段在 query 中原样出现才算命中。
        """
        q = query.lower()
        hits: list[tuple[str, float]] = []
        for s in self.lib:
            score = 0.0
            segments = [seg for seg in re.split(r"[与、，,/]", s.domain) if len(seg) >= 2]
            if any(seg.lower() in q for seg in segments):
                score += 0.7
            for tag in s.tags:
                t = tag.lower()
                if len(t) >= 2 and t in q:
                    score += 0.3
            if score > 0:
                hits.append((s.name, round(min(score, 2.0), 4)))
        hits.sort(key=lambda kv: -kv[1])
        return hits[:top_k]

    def _channel_map(
        self, query: str, bm25_hits: list[tuple[str, float]], pool: int
    ) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for n, _ in bm25_hits:
            out.setdefault(n, []).append("bm25")
        for n, _ in self.vec.search(query, top_k=pool):
            out.setdefault(n, []).append("vector")
        for n, _ in self._structural_hits(query, top_k=pool):
            out.setdefault(n, []).append("structural")
        return out

    def _graph_expand(
        self, ranked: list[tuple[str, float]], top_n: int = 5
    ) -> tuple[list[tuple[str, float]], list[str]]:
        """用依赖/组合关系把强相关但未被检索到的技能补进候选池。

        只在头部候选上扩展，且 compose_with 的传播权重高于 depend_on，
        避免关系图把无关技能带进候选池（SkillNet 论文提到扩展 S_q 会引入噪声）。
        """
        base = dict(ranked)
        added: list[str] = []
        rel_weight = {"compose_with": 0.88, "depend_on": 0.80}
        for name, score in ranked[:top_n]:
            for rel, nb in self.lib.neighbours(
                name, rel_types=("compose_with", "depend_on")
            ):
                if nb in base:
                    base[nb] = base[nb] * 1.03  # 互相印证，小幅加权
                    continue
                base[nb] = score * rel_weight.get(rel, 0.8)
                added.append(nb)
        merged = sorted(base.items(), key=lambda kv: -kv[1])
        return merged, added

    # ------------------------------------------------------------------
    def _llm_rerank(self, query: str, names: list[str]) -> list[str]:
        """把技能卡（contract）交给 LLM 做相关性重排。"""
        if not names:
            return []
        cards = []
        for n in names:
            s = self.lib.get(n)
            if not s:
                continue
            cards.append(
                {
                    "skill": n,
                    "capability": s.capability,
                    "use_when": s.use_when[:3],
                    "domain": s.domain,
                }
            )
        prompt = (
            "你是科研 Agent 的技能路由器。下面是一个研究任务和候选技能卡。\n"
            "请按「对完成该任务的实际必要性」从高到低排序，只保留真正需要的技能。\n\n"
            f"【研究任务】\n{query}\n\n"
            f"【候选技能卡】\n{cards}\n\n"
            "只输出 JSON 数组，元素为技能名字符串，按相关性降序，不要解释。"
        )
        out = chat_json(
            [{"role": "user", "content": prompt}],
            role="router",
            temperature=0.0,
            max_tokens=600,
            default=[],
        )
        if isinstance(out, list):
            valid = {n for n in names}
            return [str(x) for x in out if str(x) in valid]
        return []

    # ------------------------------------------------------------------
    def route_with_wiki(
        self, query: str, *, k: int = 5, pool: int = 20
    ) -> dict[str, Any]:
        """Fabric 式任务级 Wiki：候选 + 证据 + 关系，供 Explore 决策。"""
        r = self.search(query, k=pool, mode=MODE_FABRIC, expand=True, rerank=False)
        names = [c.name for c in r.candidates]
        cards = []
        for n in names:
            s = self.lib.get(n)
            if not s:
                continue
            rels = [
                {"type": rel, "target": tgt}
                for rel, tgt in s.relations
                if tgt in set(names)
            ]
            cards.append(
                {
                    "name": s.name,
                    "capability": s.capability,
                    "inputs": s.inputs,
                    "outputs": s.outputs,
                    "use_when": s.use_when,
                    "relations": rels,
                    "quality": s.quality,
                }
            )
        prompt = (
            "你是一个科研任务的技能路由 Explorer。下面给出一个任务，以及一个由检索和"
            "关系扩展构造出的「技能 Wiki」（技能卡 + 技能间关系）。\n\n"
            f"【任务】\n{query}\n\n"
            f"【技能 Wiki】\n{cards}\n\n"
            f"请选出最多 {k} 个技能构成完成任务所需的最终技能集，并给出它们的依赖顺序。\n"
            '严格输出 JSON：{"skills": ["技能名", ...], "workflow": [["技能名","技能名"], ...], '
            '"reason": "一句话理由"}\n'
            "workflow 中每条边 [A, B] 表示 A 的输出是 B 的输入，或 A 必须在 B 之前执行。"
        )
        out = chat_json(
            [{"role": "user", "content": prompt}],
            role="explorer",
            temperature=0.0,
            max_tokens=900,
            default={},
        )
        valid = set(names)
        skills = [s for s in (out.get("skills") or []) if s in valid][:k]
        wf = [
            e
            for e in (out.get("workflow") or [])
            if isinstance(e, list) and len(e) == 2 and e[0] in valid and e[1] in valid
        ]
        return {
            "query": query,
            "wiki_size": len(cards),
            "skills": skills,
            "workflow": wf,
            "reason": out.get("reason", ""),
            "retrieval_trace": r.trace,
        }


def gold_overlap(selected: list[str], gold: list[str]) -> float:
    """召回完整度：gold 技能被选中的比例。"""
    gold = gold or []
    if not gold:
        return 0.0
    return len(set(selected) & set(gold)) / len(set(gold))
