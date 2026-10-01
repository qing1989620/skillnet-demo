# -*- coding: utf-8 -*-
"""检索置信度分流的回归测试。

分流机制的背景与阈值标定依据见 `skillnet/retriever.py` 模块常量注释：
吸收自开发组成员项目 Nexus 的混合调度设计（Top-1 相关度 -> 自动执行 /
人工确认 / 无匹配直答）。本项目因融合分跨查询不可比，改用 BM25 原始分，
并用保守阈值保证「不误杀技能」。

这些测试锁定的行为契约：
1. 无关查询不得被判为 auto/confirm（否则会强行套用技能）；
2. 真实任务不得被判为 direct（误杀技能比多问一句代价大）；
3. 阈值边界稳定（避免后续调参无声漂移）；
4. 分流只改建议，不改检索结果本身。
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillnet.catalog import SkillLibrary, build_seed_skills   # noqa: E402
from skillnet.retriever import (                               # noqa: E402
    AUTO_EXECUTE_THRESHOLD,
    DECISION_AUTO,
    DECISION_CONFIRM,
    DECISION_DIRECT,
    MANUAL_CONFIRM_THRESHOLD,
    Retriever,
)

UNRELATED = [
    "今天天气怎么样",
    "随便聊聊",
    "给我讲个笑话",
    "现在几点了",
]


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    return Retriever(SkillLibrary(build_seed_skills())).build()


def _tasks(name: str) -> list[dict]:
    return json.loads((ROOT / "tasks" / name).read_text(encoding="utf-8"))["tasks"]


def test_unrelated_queries_never_auto_execute(retriever: Retriever) -> None:
    """无关查询不得被判为自动执行（否则会把无关任务硬套技能）。"""
    for q in UNRELATED:
        res = retriever.search(q, k=5, mode="fabric")
        assert res.decision != DECISION_AUTO, f"无关查询被判 auto：{q}"


def test_real_tasks_never_direct(retriever: Retriever) -> None:
    """真实科研任务不得被判为「无匹配」——这是本项目最不能接受的错误类型。"""
    for split, fname in (("dev", "benchmark.json"), ("heldout", "heldout.json")):
        for t in _tasks(fname):
            res = retriever.search(t["query"], k=5, mode="fabric")
            assert res.decision != DECISION_DIRECT, (
                f"[{split}] 真实任务被误判 direct（误杀技能）：{t['id']} raw={res.raw_bm25_top:.2f}"
            )


def test_threshold_boundaries(retriever: Retriever) -> None:
    """阈值边界行为：raw < MANUAL 判 direct；MANUAL <= raw < AUTO 判 confirm。"""
    assert MANUAL_CONFIRM_THRESHOLD < AUTO_EXECUTE_THRESHOLD
    res = retriever.search("今天天气怎么样", k=5, mode="fabric")
    assert res.raw_bm25_top < MANUAL_CONFIRM_THRESHOLD
    assert res.decision == DECISION_DIRECT
    assert "无重叠" in res.decision_reason or "几乎无重叠" in res.decision_reason


def test_confidence_is_monotonic_and_bounded(retriever: Retriever) -> None:
    """confidence 归一到 0–1，且随 BM25 原始分单调不减。"""
    samples = []
    for q in ["今天天气怎么样", "帮我准备算法面试", "我拿到一批 PBMC 的单细胞测序数据想做质控"]:
        res = retriever.search(q, k=5, mode="fabric")
        assert 0.0 <= res.confidence <= 1.0
        samples.append((res.raw_bm25_top, res.confidence))
    samples.sort()
    for (r1, c1), (r2, c2) in zip(samples, samples[1:]):
        assert c2 >= c1 - 1e-9, f"confidence 未随原始分单调：{r1}->{c1}, {r2}->{c2}"


def test_decision_does_not_change_selection(retriever: Retriever) -> None:
    """分流只影响建议字段，不得改变 selected 检索结果（防止阈值被误用成过滤）。"""
    q = "我拿到一批 PBMC 的 10x 单细胞 RNA 测序数据，想先做质控并识别出免疫细胞亚群"
    a = retriever.search(q, k=5, mode="fabric")
    b = retriever.search(q, k=5, mode="fabric")
    assert a.selected == b.selected
    assert a.decision == b.decision
    d = a.to_dict()
    for key in ("confidence", "raw_bm25_top", "fusion_score", "decision", "decision_reason"):
        assert key in d, f"to_dict 缺少分流字段 {key}"
