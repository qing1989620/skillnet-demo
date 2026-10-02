"""上下文老虎机的强制测试。

这三个测试是 v0.3 加固的核心 —— 它们锁定的正是 v0.2 实现**做不到**的事。

背景（为什么必须有这些测试）：
v0.2 用的是 per-arm LinUCB（每个技能独立的 A/b）。那个实现在数学上不可能让
「评估 A 的反馈影响未评估的 B」，但项目文档却声称可以。更糟的是
`predicted_reward` 恒为 0（b 初值为零向量），意味着它从未真正学习过。
单看输出不会发现这一点 —— 必须用测试把「泛化」这个性质显式断言出来。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skillnet.bandit import CTX_DIM, SharedLinUCB, stable_hash  # noqa: E402
from skillnet.catalog import SkillLibrary, build_seed_skills  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def lib() -> SkillLibrary:
    return SkillLibrary(build_seed_skills())


def _same_domain_pair(lib: SkillLibrary):
    """挑一个「同领域技能对 + 一个异领域技能」的三元组。

    必须严格按 domain 字段构造 —— 靠技能名猜「语义相近」会猜错：
    例如 scrna-qc-clustering（细胞生物学）与 differential-expression（基因组学）
    看着相关，实际不同领域，拿它们做泛化断言会得出错误结论。
    """
    groups: dict[str, list[str]] = {}
    for s in lib:
        groups.setdefault(s.domain, []).append(s.name)
    domain = max(groups, key=lambda d: len(groups[d]))
    near_a, near_b = groups[domain][0], groups[domain][1]
    far = next(s.name for s in lib if s.domain != domain)
    return near_a, near_b, far, domain


# ======================================================================
def test_bandit_cross_skill_generalization(lib: SkillLibrary) -> None:
    """只更新 A，未评估的同领域技能 B 也必须被带动，且幅度大于异领域 C。

    这是 shared LinUCB 相对 per-arm LinUCB 的**唯一**意义所在。
    如果这个测试失败，说明实现退回了 per-arm（或特征里没有领域/语义结构），
    那么文档中「一次评估的反馈能影响语义相近的未评估技能」就是虚假陈述。
    """
    near_a, near_b, far, domain = _same_domain_pair(lib)
    bandit = SharedLinUCB(lib, alpha=0.25, seed=17)
    task = lib.get(near_a).capability or f"{domain}领域的典型任务"

    before = {n: bandit.score(task, n) for n in (near_a, near_b, far)}
    bandit.update(task, near_a, reward=0.95)
    after = {n: bandit.score(task, n) for n in (near_a, near_b, far)}

    d_a = abs(after[near_a][1] - before[near_a][1])
    d_b = abs(after[near_b][1] - before[near_b][1])
    d_c = abs(after[far][1] - before[far][1])

    # 1) 被更新的技能变化最大
    assert d_a > 0, "被更新的技能预测值未发生变化"
    # 2) 未评估的同领域技能被显著带动（泛化确实发生）
    assert d_b > 1e-3, f"未评估的同领域技能未被带动（Δ={d_b:.6f}），泛化失败"
    # 3) 同领域受影响程度严格大于异领域
    assert d_b > d_c, (
        f"同领域 Ω={d_b:.6f} 未大于异领域 Δ={d_c:.6f}；"
        f"说明 φ 丢失了领域/语义结构，泛化退化成「所有技能一起涨」"
    )


def test_bandit_task_conditioning(lib: SkillLibrary) -> None:
    """同一个技能在两个不同任务上，上下文与优先级必须不同。

    如果这个测试失败，说明 φ 没有编码 task —— 那就退回了「只看技能本身」的
    v0.2 行为，也就谈不上 task-conditioned contextual bandit。
    """
    name = next(s.name for s in lib if len(s.capability) > 10)
    skill = lib.get(name)
    bandit = SharedLinUCB(lib, alpha=0.25, seed=17)

    t1 = "单细胞测序数据的质控、聚类与细胞亚群注释"
    t2 = "无机化合物形成能的机器学习预测与外推能力评估"

    phi1 = bandit.encoder.encode(t1, skill)
    phi2 = bandit.encoder.encode(t2, skill)
    assert phi1.shape == (CTX_DIM,) and phi2.shape == (CTX_DIM,)
    assert not np.allclose(phi1, phi2), "同一技能在两个任务上的 φ 完全相同：未编码 task"

    p1 = bandit.score(t1, name)[0]
    p2 = bandit.score(t2, name)[0]
    assert abs(p1 - p2) > 1e-4, (
        f"同一技能在两个不同任务上的优先级相同（{p1:.6f} vs {p2:.6f}）：未做 task conditioning"
    )


def test_bandit_reproducibility() -> None:
    """两个不同 PYTHONHASHSEED 的子进程必须给出完全一致的输出。

    这条针对的是 v0.2 用内置 `hash()` 构造上下文特征的缺陷 ——
    内置 `hash()` 对字符串的结果每个进程都不同，会导致上下文不可复现、
    模型无法持久化、两次实验无法比对。
    """
    code = (
        "import sys; sys.path.insert(0, '.');"
        "from skillnet.catalog import SkillLibrary, build_seed_skills;"
        "from skillnet.bandit import SharedLinUCB;"
        "lib = SkillLibrary(build_seed_skills());"
        "b = SharedLinUCB(lib, alpha=0.25, seed=17);"
        "b.update('单细胞测序质控与聚类', 'scrna-qc-clustering', 0.9);"
        "phi = b.encoder.encode('单细胞测序质控与聚类', lib.get('differential-expression'));"
        "print(round(float(sum(phi)), 8), round(b.score('单细胞测序质控与聚类','differential-expression')[0], 8))"
    )
    outputs = set()
    for seed in ("0", "987654"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        r = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True,
            env=env, cwd=str(ROOT), timeout=120,
        )
        assert r.returncode == 0, f"子进程执行失败：{r.stderr[:300]}"
        outputs.add(r.stdout.strip())
    assert len(outputs) == 1, f"不同 PYTHONHASHSEED 下结果不一致：{outputs}"


def test_stable_hash_helper() -> None:
    """稳定哈希本身：同一输入永远同一输出，且落在 [0, dim) 内。"""
    assert stable_hash("单细胞", 64) == stable_hash("单细胞", 64)
    for tok in ("a", "单细胞", "x" * 100, ""):
        assert 0 <= stable_hash(tok, 64) < 64


def test_shared_parameters_not_per_arm(lib: SkillLibrary) -> None:
    """结构断言：A / b 是**单个矩阵**，不是按技能名的字典。

    这是防止实现被改回 per-arm 的护栏 —— 只要有人把它改回
    `dict[str, np.ndarray]`，这个测试立刻失败。
    """
    bandit = SharedLinUCB(lib, alpha=0.25, seed=17)
    assert isinstance(bandit.A, np.ndarray), "A 应为单个共享矩阵，而非按臂分立的字典"
    assert isinstance(bandit.b, np.ndarray), "b 应为单个共享向量"
    assert bandit.A.shape == (CTX_DIM, CTX_DIM)
    assert bandit.b.shape == (CTX_DIM,)

    bandit.update("某任务", "scrna-qc-clustering", 0.9)
    assert bandit.n_updates == 1
    assert float(np.linalg.norm(bandit.theta)) > 0, "更新后 θ 仍为零向量，模型没有学习"


def test_theta_becomes_nonzero_after_update(lib: SkillLibrary) -> None:
    """v0.2 的直接症状：θ 恒为零向量，predicted_reward 恒为 0。

    这里断言更新一次后预测值必须离开 0。
    """
    bandit = SharedLinUCB(lib, alpha=0.25, seed=17)
    name = "scrna-qc-clustering"
    task = "单细胞测序质控"
    assert bandit.score(task, name)[1] == pytest.approx(0.0), "初始状态预测值应为 0"
    bandit.update(task, name, 0.9)
    assert abs(bandit.score(task, name)[1]) > 1e-6, "更新后 predicted_reward 仍为 0"
