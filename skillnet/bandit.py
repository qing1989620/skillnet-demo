"""LinUCB 上下文老虎机：在有限预算下决定「评估哪个技能」。

直接对照 COBRA-Skills (arXiv:2609.11682) 的设计：
  优先级 = 预测收益 + 探索奖励
    预测收益  theta^T x                 （用历史执行反馈拟合）
    探索奖励  alpha * sqrt(x^T A^-1 x)  （LinearUCB 风格，越少被评估的语义方向越大）

与论文一致的两点设计：
  1) 上下文 x 来自技能的语义表示，因此一次评估的反馈能影响语义相近的未评估技能；
  2) 最终输出按「实测平均奖励」而不是预测分数选取。

同时实现 RandomSelector（COBRA-Skills 表 4 的消融对照：保留进化但随机选择）。
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .catalog import SkillLibrary
from .index import VectorIndex
from .schema import Skill, quality_score

CTX_DIM = 48


class ContextEncoder:
    """把技能编码成上下文向量：语义哈希分量 + 质量/代际/新鲜度特征。"""

    def __init__(self, dim: int = CTX_DIM) -> None:
        self.dim = dim

    def encode(self, skill: Skill, extra: dict[str, float] | None = None) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=float)
        text = skill.l1_text()
        for tok in set(text.lower().split()):
            vec[hash(tok) % (self.dim - 4)] += 1.0
        norm = np.linalg.norm(vec)
        if norm:
            vec /= norm
        vec[self.dim - 4] = quality_score(skill.quality)
        vec[self.dim - 3] = min(skill.generation, 5) / 5.0
        vec[self.dim - 2] = 1.0 if skill.source != "seed" else 0.0
        vec[self.dim - 1] = float((extra or {}).get("retrieval", 0.0))
        return vec


@dataclass
class Pull:
    round: int
    skill: str
    predicted: float
    reward: float
    reason: str = ""


class LinUCB:
    """每个技能一个臂的 LinUCB（共享上下文特征空间）。"""

    def __init__(
        self,
        lib: SkillLibrary,
        *,
        alpha: float = 0.1,
        dim: int = CTX_DIM,
        seed: int = 17,
    ) -> None:
        self.lib = lib
        self.alpha = alpha
        self.dim = dim
        self.encoder = ContextEncoder(dim)
        self.rng = random.Random(seed)
        self.A: dict[str, np.ndarray] = {}
        self.b: dict[str, np.ndarray] = {}
        self.cache: dict[str, np.ndarray] = {}
        self.history: list[Pull] = []

    # ------------------------------------------------------------------
    def _A(self, name: str) -> np.ndarray:
        if name not in self.A:
            self.A[name] = np.eye(self.dim)
            self.b[name] = np.zeros(self.dim)
        return self.A[name]

    def _ctx(self, name: str, extra: dict[str, float] | None = None) -> np.ndarray:
        key = f"{name}|{round((extra or {}).get('retrieval', 0.0), 3)}"
        if key not in self.cache:
            s = self.lib.get(name)
            self.cache[key] = (
                self.encoder.encode(s, extra) if s else np.zeros(self.dim)
            )
        return self.cache[key]

    # ------------------------------------------------------------------
    def score(self, name: str, extra: dict[str, float] | None = None) -> tuple[float, float, float]:
        """返回 (优先级, 预测收益, 探索奖励)。"""
        A = self._A(name)
        x = self._ctx(name, extra)
        A_inv = np.linalg.inv(A)
        theta = A_inv @ self.b[name]
        exploit = float(theta @ x)
        explore = float(self.alpha * math.sqrt(max(0.0, x @ A_inv @ x)))
        return exploit + explore, exploit, explore

    def select(
        self, candidates: list[str], *, extra: dict[str, dict[str, float]] | None = None
    ) -> tuple[str, dict[str, float]]:
        best, best_p, info = None, -1e9, {}
        for n in candidates:
            if self.lib.get(n) is None:
                continue
            ex = (extra or {}).get(n)
            p, exploit, explore = self.score(n, ex)
            if p > best_p:
                best, best_p = n, p
                info = {
                    "priority": round(p, 5),
                    "predicted_reward": round(exploit, 5),
                    "exploration_bonus": round(explore, 5),
                }
        return best, info

    def update(self, name: str, reward: float, extra: dict[str, float] | None = None) -> None:
        x = self._ctx(name, extra)
        self.A[name] = self._A(name) + np.outer(x, x)
        self.b[name] = self.b[name] + reward * x
        s = self.lib.get(name)
        if s is not None:
            s.stats["pulls"] = s.stats.get("pulls", 0) + 1
            s.stats["reward_sum"] = s.stats.get("reward_sum", 0) + reward
            s.stats["best"] = max(s.stats.get("best", 0.0), reward)

    def log(self, rnd: int, name: str, predicted: float, reward: float, reason: str = "") -> None:
        self.history.append(Pull(rnd, name, predicted, reward, reason))

    def invalidate(self, name: str | None = None) -> None:
        self.cache.clear()

    # ------------------------------------------------------------------
    def best_by_actual(self, candidates: list[str] | None = None) -> Skill | None:
        """按历史实测平均奖励返回最佳技能（COBRA-Skills 的最终输出规则）。"""
        pool = candidates or [s.name for s in self.lib]
        scored = [(n, self.lib.get(n)) for n in pool]
        scored = [(n, s) for n, s in scored if s is not None and s.stats.get("pulls", 0) > 0]
        if not scored:
            return None
        scored.sort(key=lambda kv: (-kv[1].mean_reward, -kv[1].stats.get("pulls", 0)))
        return scored[0][1]

    def snapshot(self) -> dict[str, Any]:
        return {
            "alpha": self.alpha,
            "arms_informed": sum(
                1 for n in self.A if float(np.sum(np.abs(self.A[n] - np.eye(self.dim)))) > 0
            ),
            "pulls": len(self.history),
            "curve": [
                {"round": p.round, "skill": p.skill, "reward": round(p.reward, 4),
                 "predicted": round(p.predicted, 4), "reason": p.reason}
                for p in self.history
            ],
            "arm_stats": {
                s.name: {
                    "pulls": int(s.stats.get("pulls", 0)),
                    "mean_reward": round(s.mean_reward, 4),
                    "best": round(s.stats.get("best", 0.0), 4),
                }
                for s in self.lib
                if s.stats.get("pulls", 0) > 0
            },
        }


class RandomSelector:
    """消融对照：随机选择候选技能评估（不用老虎机）。"""

    def __init__(self, lib: SkillLibrary, seed: int = 17) -> None:
        self.lib = lib
        self.rng = random.Random(seed)
        self.history: list[Pull] = []

    def select(
        self, candidates: list[str], *, extra: dict[str, dict[str, float]] | None = None
    ) -> tuple[str, dict[str, float]]:
        pool = [n for n in candidates if self.lib.get(n)]
        if not pool:
            return None, {}
        return self.rng.choice(pool), {"priority": 0.0, "predicted_reward": 0.0,
                                       "exploration_bonus": 0.0}

    def update(self, name: str, reward: float, extra: dict[str, float] | None = None) -> None:
        s = self.lib.get(name)
        if s is not None:
            s.stats["pulls"] = s.stats.get("pulls", 0) + 1
            s.stats["reward_sum"] = s.stats.get("reward_sum", 0) + reward
            s.stats["best"] = max(s.stats.get("best", 0.0), reward)

    def log(self, rnd: int, name: str, predicted: float, reward: float, reason: str = "") -> None:
        self.history.append(Pull(rnd, name, predicted, reward, reason))

    def invalidate(self, name: str | None = None) -> None:
        return None

    def best_by_actual(self, candidates: list[str] | None = None) -> Skill | None:
        pool = candidates or [s.name for s in self.lib]
        scored = [
            (n, self.lib.get(n)) for n in pool
            if self.lib.get(n) is not None and self.lib.get(n).stats.get("pulls", 0) > 0
        ]
        if not scored:
            return None
        scored.sort(key=lambda kv: (-kv[1].mean_reward, -kv[1].stats.get("pulls", 0)))
        return scored[0][1]

    def snapshot(self) -> dict[str, Any]:
        return {
            "alpha": None,
            "arms_informed": 0,
            "pulls": len(self.history),
            "curve": [
                {"round": p.round, "skill": p.skill, "reward": round(p.reward, 4),
                 "predicted": 0.0, "reason": p.reason}
                for p in self.history
            ],
            "arm_stats": {
                s.name: {
                    "pulls": int(s.stats.get("pulls", 0)),
                    "mean_reward": round(s.mean_reward, 4),
                    "best": round(s.stats.get("best", 0.0), 4),
                }
                for s in self.lib
                if s.stats.get("pulls", 0) > 0
            },
        }
