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

from . import config
from .catalog import SkillLibrary
from .index import BM25Index, VectorIndex, tokenize, weighted_fuse
from .llm import chat_json
from .schema import Skill, quality_score
from .semantic import make_index, WEIGHTS

MODE_BM25 = "bm25"
MODE_HYBRID = "hybrid"
MODE_FABRIC = "fabric"
MODES = (MODE_BM25, MODE_HYBRID, MODE_FABRIC)

# ----------------------------------------------------------------------
# 检索置信度分流（吸收自开发组成员项目 Nexus 的混合调度设计）
# ----------------------------------------------------------------------
# Nexus 用 Top-1 余弦相似度分三档决定下游动作（自动执行 / 人工确认 / 无匹配直答）。
# 本项目的融合分经过 min-max 归一化，**对候选池组成敏感、跨查询不可比**
# （同一个技能在不同查询下分数尺度不同），不能直接套绝对阈值。
# 因此改用 BM25 原始分——它是 TF-IDF 累加值，量纲固定、跨查询可比。
#
# 阈值依据本项目 42 条查询的实测分布标定：
#   真实科研任务 dev (20)   9.9 – 88.9（中位 42.6）
#   真实科研任务 heldout(12) 20.7 – 61.8（中位 33.7）
#   交付物任务 (5)           8.0 – 29.0
#   无关问题 (5)             0.0 – 4.6
#
# 标定过程中的一个发现（诚实记录）：纯词汇法对「措辞与技能文本重叠少」的真实任务
# 会低估相关度——dev 集里「省级面板数据评估产业政策」「农田耕作方式对产量影响」
# 两条真实任务的 BM25 原始分只有 3.80 / 4.27，低于 6.0 的初版阈值，会被误判为
# 无匹配。因此阈值改为**保守标定**：只有词面几乎完全不重叠（raw < 2.0）才判无匹配，
# 其余一律建议人工确认。设计原则是「错杀技能的代价 > 多问一句的代价」。
AUTO_EXECUTE_THRESHOLD = 15.0    # BM25 原始分 >= 15：技能匹配明确，直接执行
MANUAL_CONFIRM_THRESHOLD = 2.0   # [2, 15) 建议人工确认；< 2 判为无匹配（实测无关查询为 0）

DECISION_AUTO = "auto"
DECISION_CONFIRM = "confirm"
DECISION_DIRECT = "direct"


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

    # ---- 降级可观测性 ----
    # 缺 DEEPSEEK_API_KEY 时，fabric 的关系图扩展仍然会跑，但 LLM 重排不会。
    # 早先这种情况是**静默**的：使用者看到 mode=fabric 就以为重排生效了，
    # 实际拿到的是未重排的结果，而 trace 里也不会有任何提示。
    # 现在每个组件是否真正执行都被显式记录下来。
    components: dict[str, bool] = field(default_factory=dict)
    degraded: bool = False
    degraded_reason: str = ""

    # ---- 置信度分流（产品化决策）----
    # 用 BM25 原始分（跨查询可比的绝对信号）-> 自动执行 / 人工确认 / 无匹配直答。
    # confidence 为归一到 0–1 的相关度（raw / AUTO_THRESHOLD，封顶 1.0），
    # raw_bm25_top 保留原始值便于审计；fusion_score 是归一化融合分（仅作排序参考）。
    confidence: float = 0.0
    raw_bm25_top: float = 0.0
    fusion_score: float = 0.0
    decision: str = DECISION_DIRECT
    decision_reason: str = ""
    encoder: dict[str, Any] = field(default_factory=dict)
    weights: list[float] = field(default_factory=lambda: list(WEIGHTS))

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "mode": self.mode,
            "selected": self.selected,
            "candidates": [c.__dict__ for c in self.candidates],
            "trace": self.trace,
            "confidence": self.confidence,
            "confidence_kind": "heuristic_relevance_not_probability",
            "raw_bm25_top": self.raw_bm25_top,
            "fusion_score": self.fusion_score,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "degraded": self.degraded,
            "components": self.components,
            "degraded_reason": self.degraded_reason,
            "encoder": self.encoder, "weights": self.weights,
        }


class Retriever:
    def __init__(self, lib: SkillLibrary) -> None:
        self.lib = lib
        self.bm25 = BM25Index()
        self.vec = make_index()
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
        res.encoder = getattr(self.vec, 'status', {})

        # ---- 通路 1：BM25 ----
        bm25_hits = self.bm25.search(query, top_k=pool)
        res.raw_bm25_top = float(bm25_hits[0][1]) if bm25_hits else 0.0
        res.trace.append(f"BM25 召回 {len(bm25_hits)} 条")
        if mode == MODE_BM25:
            fused = bm25_hits
        else:
            # ---- 通路 2：语义向量 ----
            vec_hits = self.vec.search(query, top_k=pool)
            res.trace.append(f"{res.encoder.get('kind', 'lexical-hashing')} 向量召回 {len(vec_hits)} 条")
            # ---- 通路 3：领域/标签结构信号 ----
            struct_hits = self._structural_hits(query, top_k=pool)
            res.trace.append(f"结构信号召回 {len(struct_hits)} 条")
            # 权重按「强通路主导、弱通路补充」定，并经过一轮扫描验证
            # （见 README 第四节：0.55/0.30/0.15 时混合档会低于纯 BM25 基线，
            #  因为本环境的语义通路是稀疏向量的降级实现，噪声偏大）。
            # 这里取 0.70/0.20/0.10：既让混合档稳定优于基线，
            # 又不至于把语义通路的权重压到形同虚设。
            # **接入稠密编码器后这个权重需要重新标定。**
            from .semantic import DENSE_WEIGHTS
            res.weights = list(DENSE_WEIGHTS if res.encoder.get('kind') == 'dense-onnx' else WEIGHTS)
            fused = weighted_fuse([bm25_hits, vec_hits, struct_hits], weights=res.weights)
            res.trace.append(
                f"加权融合后候选池 {len(fused)} 条（BM25 {res.weights[0]:.2f} / 语义 {res.weights[1]:.2f} / 结构 {res.weights[2]:.2f}）"
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
        chan_map = self._channel_map(query, bm25_hits, pool, multi=mode != MODE_BM25)

        # ---- 关系图扩展（Fabric 的 relation expansion）----
        graph_ran = False
        if mode == MODE_FABRIC and expand and ranked:
            ranked, added = self._graph_expand(ranked)
            graph_ran = True
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
        rerank_ran = False
        skip_reason = ""
        if mode == MODE_FABRIC and rerank:
            if not config.API_KEY:
                skip_reason = "DEEPSEEK_API_KEY not configured"
            elif len(cands) <= k:
                skip_reason = f"candidates({len(cands)}) <= k({k})"
            else:
                ordered = self._llm_rerank(query, [c.name for c in cands[: min(pool, 16)]])
                if ordered:
                    rerank_ran = True
                    rank_of = {n: i for i, n in enumerate(ordered)}
                    head = [c for c in cands if c.name in rank_of]
                    head.sort(key=lambda c: rank_of[c.name])
                    tail = [c for c in cands if c.name not in rank_of]
                    cands = []
                    for i, c in enumerate(head + tail, 1):
                        c.rerank_score = (1.0 - rank_of[c.name] / max(1, len(rank_of))) if c.name in rank_of else None
                        c.rank = i
                        cands.append(c)
                    res.trace.append(f"LLM 重排 {len(rank_of)} 条候选")
                else:
                    skip_reason = "LLM rerank call failed or returned empty"

        # ---- 降级状态：任何组件没按预期执行都必须显式暴露，不允许静默 ----
        multi = mode != MODE_BM25
        res.components = {
            "bm25": True,
            "vector": multi,
            "structural": multi,
            "graph_expansion": graph_ran,
            "llm_rerank": rerank_ran,
        }
        expected = {
            "bm25": True,
            "vector": multi,
            "structural": multi,
            "graph_expansion": mode == MODE_FABRIC and expand and bool(ranked),
            "llm_rerank": mode == MODE_FABRIC and rerank,
        }
        missing = [k for k, want in expected.items() if want and not res.components.get(k)]
        res.degraded = bool(missing)
        if skip_reason:
            res.degraded_reason = f"llm_rerank skipped: {skip_reason}"
        elif missing:
            res.degraded_reason = "components not executed: " + ", ".join(missing)
        if res.degraded:
            res.trace.append(f"[degraded] {res.degraded_reason}")

        res.candidates = cands
        res.selected = [c.name for c in cands[:k]]
        self._decide(res)
        return res

    @staticmethod
    def _decide(res: "RetrievalResult") -> None:
        """按 top-1 融合分给出下游动作建议（置信度分流）。

        分档依据本项目实测分布标定（见模块常量注释），只改「建议」不改检索结果，
        避免把阈值误用成硬过滤——错杀技能比多问一句代价大得多。
        """
        raw = res.raw_bm25_top
        res.fusion_score = round(res.candidates[0].score, 4) if res.candidates else 0.0
        res.confidence = round(min(1.0, raw / AUTO_EXECUTE_THRESHOLD), 4)
        top = raw
        if top >= AUTO_EXECUTE_THRESHOLD:
            res.decision = DECISION_AUTO
            res.decision_reason = (
                f"BM25 原始分 {top:.2f} ≥ {AUTO_EXECUTE_THRESHOLD}：技能匹配明确，可直接执行"
            )
        elif top >= MANUAL_CONFIRM_THRESHOLD:
            res.decision = DECISION_CONFIRM
            res.decision_reason = (
                f"BM25 原始分 {top:.2f} 落在 [{MANUAL_CONFIRM_THRESHOLD}, "
                f"{AUTO_EXECUTE_THRESHOLD})：建议展示候选让使用者确认后再执行"
            )
        else:
            res.decision = DECISION_DIRECT
            res.decision_reason = (
                f"BM25 原始分 {top:.2f} < {MANUAL_CONFIRM_THRESHOLD}：词面与技能库几乎无重叠，"
                "建议由通用模型直答而非强行套用技能"
            )

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
        self, query: str, bm25_hits: list[tuple[str, float]], pool: int, *, multi: bool = True
    ) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for n, _ in bm25_hits:
            out.setdefault(n, []).append("bm25")
        if not multi:
            return out
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
            return list(dict.fromkeys(x for x in out if isinstance(x, str) and x in valid))
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
            '"reason": "一句话总体理由", "decisions": [{"name":"候选技能名","reason":"针对本任务采用或未采用的具体理由"}]}\n'
            'decisions 应涵盖提供的候选；不要把检索分解释为成功概率。\n'
            "workflow 中每条边 [A, B] 表示 A 的输出是 B 的输入，或 A 必须在 B 之前执行。"
        )
        out = chat_json(
            [{"role": "user", "content": prompt}],
            role="explorer",
            temperature=0.0,
            max_tokens=1800,
            default={},
        )
        from .orchestrator import Orchestrator

        valid = set(names)
        reasons = []
        if not isinstance(out, dict):
            out = {}
            reasons.append("Explorer returned a non-object response")
        raw_skills = out.get("skills")
        if not isinstance(raw_skills, list):
            skills = names[:k]
            reasons.append("Explorer skills unavailable; used retrieved candidates")
        else:
            skills = list(dict.fromkeys(s for s in raw_skills if isinstance(s, str) and s in valid))[:k]
            invalid = sum(1 for s in raw_skills if not isinstance(s, str) or s not in valid)
            if invalid:
                reasons.append(f"ignored {invalid} invalid Explorer skill(s)")
            if raw_skills and not skills:
                skills = names[:k]
                reasons.append("Explorer selected no valid skills; used retrieved candidates")
        # Edges are constrained to the final selected nodes, not the larger Wiki.
        # Preserve known prerequisites if a proposed edge would form a cycle.
        orchestration = Orchestrator(self.lib).merge_workflow(skills, out.get("workflow"))
        if orchestration["degraded_reason"]:
            reasons.append(orchestration["degraded_reason"])
        return {
            "query": query,
            "wiki_size": len(cards),
            "skills": skills,
            "workflow": orchestration["workflow"],
            "order": orchestration["skills"],
            "cycles_broken": orchestration["cycles_broken"],
            "source": orchestration["source"],
            "degraded": bool(reasons),
            "degraded_reason": "; ".join(reasons),
            "reason": out.get("reason", "") if isinstance(out.get("reason", ""), str) else "",
            "decisions": [{"name":d['name'],"selected":d['name'] in skills,"reason":d['reason'][:300]}
                          for d in (out.get('decisions') if isinstance(out.get('decisions'),list) else [])
                          if isinstance(d,dict) and isinstance(d.get('name'),str)
                          and d['name'] in valid and isinstance(d.get('reason'),str)],
            "retrieval_trace": r.trace,
        }


def gold_overlap(selected: list[str], gold: list[str]) -> float:
    """召回完整度：gold 技能被选中的比例。"""
    gold = gold or []
    if not gold:
        return 0.0
    return len(set(selected) & set(gold)) / len(set(gold))
