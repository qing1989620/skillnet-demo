# -*- coding: utf-8 -*-
"""runtime.py —— Run Runtime：运行的核心数据模型、事件流与持久化。

为什么要单独建这一层
--------------------
此前所有能力都通过 `/api/demo` 一次性串起来：前端拿不到中间状态、看不到运行标识、
无法对比两次运行、也没有可查询的历史。而竞品（LangSmith / Langfuse / Braintrust 等）
在 2026 年已经把「trace → eval → 回归门禁」做成标准闭环——我们必须有自己的运行模型，
哪怕不重建 observability 平台，也至少要把运行事实**结构化、可查询、可对比**。

核心实体（与竞品对齐的概念模型）
--------------------------------
Run                   一次任务运行，有独立 run_id 与状态机
RunStep               DAG 中的一个可执行步骤（含依赖）
ExecutionAttempt      某个步骤的一次执行尝试（首次 + 每次修复重试）
Artifact              产物文件（含 sha256 与来源步骤）
ProgrammaticCheck     确定性检查结果（文件存在/表头/数值范围/退出码…）
VerificationResult    技能验收结果（按层标注来源：程序化 / 技能断言 / LLM）
TraceEvent            时间轴事件（用于 SSE 实时推送与事后追溯）

设计约束
--------
1. **不覆盖历史**：同一任务重复运行产生不同 run_id（任务指纹仅用于分组）。
2. **持久化**：每个 Run 落盘为 `out/runs/{run_id}.json`，重启后可查。
3. **事件流**：内存队列 + 落盘事件列表；SSE 端点消费队列，重连可回放已落盘事件。
4. **预算**：Run 级 max_cost / max_calls / max_seconds，超限进入 BUDGET_EXCEEDED。
5. **可对接**：字段采用通用命名（run_id / step_id / attempt_id / duration_ms / token / cost），
   便于后续导出为 OTel 风格 trace 交给成熟平台采集。
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ----------------------------------------------------------------------
# 状态机
# ----------------------------------------------------------------------
STATUS_CREATED = "CREATED"
STATUS_RETRIEVING = "RETRIEVING"
STATUS_ORCHESTRATING = "ORCHESTRATING"
STATUS_EXECUTING = "EXECUTING"
STATUS_VERIFYING = "VERIFYING"
STATUS_EVOLVING = "EVOLVING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_PARTIAL = "PARTIAL"
STATUS_CANCELLED = "CANCELLED"
STATUS_BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
TERMINAL = {STATUS_COMPLETED, STATUS_FAILED, STATUS_PARTIAL, STATUS_CANCELLED, STATUS_BUDGET_EXCEEDED}

STEP_PENDING = "pending"
STEP_RUNNING = "running"
STEP_DONE = "done"
STEP_FAILED = "failed"
STEP_SKIPPED = "skipped"


def now_ms() -> int:
    return int(time.time() * 1000)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def task_fingerprint(task: str) -> str:
    """任务指纹：同一任务重复运行共享指纹（用于分组），但 run_id 各自独立。"""
    return sha256_text(task.strip())[:8]


def new_run_id(fp: str) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    return f"{fp}-{ts}-{uuid.uuid4().hex[:4]}"


# ----------------------------------------------------------------------
# 实体
# ----------------------------------------------------------------------
@dataclass
class Artifact:
    name: str
    kind: str = ""              # 真实运行产物 / 方案交付物 / 过程文档
    bytes: int = 0
    sha256: str = ""
    from_step: int | None = None
    url: str = ""               # 相对 API 路径（前端可直接用）

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionAttempt:
    n: int
    ok: bool
    stdout: str = ""
    stderr: str = ""
    error_kind: str = ""
    duration_ms: int = 0
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["stdout"] = d["stdout"][-4000:]
        d["stderr"] = d["stderr"][-2000:]
        return d


@dataclass
class ProgrammaticCheck:
    """确定性检查（第一层验收）：不做 LLM 判断，只看事实。"""
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    item: str
    passed: bool
    evidence: str = ""
    layer: str = "llm"          # deterministic | assertion | llm

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunStep:
    idx: int                              # 0-based
    action: str
    skill: str | None = None
    status: str = STEP_PENDING
    depends_on: list[int] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)      # 来自前序步骤的产物名
    code: str = ""
    attempts: list[ExecutionAttempt] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    checks: list[ProgrammaticCheck] = field(default_factory=list)
    verifications: list[VerificationResult] = field(default_factory=list)
    verify_skip_reason: str = ""
    error: str = ""
    started_at_ms: int = 0
    ended_at_ms: int = 0

    @property
    def duration_ms(self) -> int:
        if not self.started_at_ms or not self.ended_at_ms:
            return 0
        return self.ended_at_ms - self.started_at_ms

    @property
    def n_attempts(self) -> int:
        return len(self.attempts)

    @property
    def fixed(self) -> bool:
        return self.n_attempts > 1 and self.status == STEP_DONE

    @property
    def exhausted(self) -> bool:
        return self.status == STEP_FAILED and self.n_attempts > 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "idx": self.idx, "action": self.action, "skill": self.skill,
            "status": self.status, "depends_on": self.depends_on, "inputs": self.inputs,
            "code": self.code, "n_attempts": self.n_attempts,
            "fixed": self.fixed, "exhausted": self.exhausted,
            "attempts": [a.to_dict() for a in self.attempts],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "checks": [c.to_dict() for c in self.checks],
            "checks_passed": sum(1 for c in self.checks if c.passed),
            "checks_total": len(self.checks),
            "verifications": [v.to_dict() for v in self.verifications],
            "verification_passed": sum(1 for v in self.verifications if v.passed),
            "verification_total": len(self.verifications),
            "verify_skip_reason": self.verify_skip_reason,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class TraceEvent:
    ts_ms: int
    type: str
    step: int | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Budget:
    max_cost_yuan: float = 1.0
    max_llm_calls: int = 40
    max_seconds: int = 300
    max_attempts_per_step: int = 3

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Run:
    run_id: str
    task: str
    task_fp: str
    status: str = STATUS_CREATED
    model: str = ""
    skills: list[str] = field(default_factory=list)
    retrieval: dict[str, Any] = field(default_factory=dict)
    ranking: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] = field(default_factory=dict)
    judge: dict[str, Any] = field(default_factory=dict)
    steps: list[RunStep] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    events: list[TraceEvent] = field(default_factory=list)
    feedback: list[dict[str, Any]] = field(default_factory=list)
    evolution: dict[str, Any] = field(default_factory=dict)
    staged: dict[str, Any] = field(default_factory=dict)   # 各阶段耗时
    budget: Budget = field(default_factory=Budget)
    cost_yuan: float = 0.0
    tokens: int = 0
    llm_calls: int = 0
    cancel_requested: bool = False
    error: str = ""
    started_at_ms: int = field(default_factory=now_ms)
    ended_at_ms: int = 0

    # ---------- 派生 ----------
    @property
    def duration_ms(self) -> int:
        return (self.ended_at_ms or now_ms()) - self.started_at_ms

    @property
    def executable_steps(self) -> list[RunStep]:
        return [s for s in self.steps if s.status in (STEP_DONE, STEP_FAILED, STEP_SKIPPED)]

    def step_stats(self) -> dict[str, int]:
        return {
            "total": len(self.steps),
            "done": sum(1 for s in self.steps if s.status == STEP_DONE),
            "failed": sum(1 for s in self.steps if s.status == STEP_FAILED),
            "skipped": sum(1 for s in self.steps if s.status == STEP_SKIPPED),
            "retried": sum(1 for s in self.steps if s.n_attempts > 1),
        }

    def to_dict(self, *, with_events: bool = True) -> dict[str, Any]:
        d = {
            "run_id": self.run_id, "task": self.task, "task_fp": self.task_fp,
            "status": self.status, "model": self.model,
            "skills": self.skills, "retrieval": self.retrieval, "ranking": self.ranking,
            "plan": self.plan, "judge": self.judge,
            "steps": [s.to_dict() for s in self.steps],
            "step_stats": self.step_stats(),
            "artifacts": [a.to_dict() for a in self.artifacts],
            "feedback": self.feedback, "evolution": self.evolution,
            "staged": self.staged, "budget": self.budget.to_dict(),
            "cost_yuan": round(self.cost_yuan, 5), "tokens": self.tokens,
            "llm_calls": self.llm_calls,
            "duration_ms": self.duration_ms,
            "started_at_ms": self.started_at_ms, "ended_at_ms": self.ended_at_ms,
            "error": self.error,
        }
        if with_events:
            d["events"] = [e.to_dict() for e in self.events[-400:]]
        return d


# ----------------------------------------------------------------------
# 事件总线（SSE 用）
# ----------------------------------------------------------------------
class EventBus:
    """极简事件总线：每个订阅者一个队列；事件同时落盘在 Run.events。

    说明：单进程内使用；不做跨进程投递（本项目为单进程部署）。
    重连时可用 `replay_from` 从落盘事件回放，避免长任务断线即丢上下文。
    """

    def __init__(self) -> None:
        self._subs: dict[str, list[Any]] = {}
        self._lock = threading.Lock()

    def subscribe(self, run_id: str):
        q: list[TraceEvent] = []
        with self._lock:
            self._subs.setdefault(run_id, []).append(q)
        return q

    def unsubscribe(self, run_id: str, q) -> None:
        with self._lock:
            subs = self._subs.get(run_id) or []
            if q in subs:
                subs.remove(q)

    def publish(self, run: Run, type_: str, *, step: int | None = None, **data: Any) -> TraceEvent:
        ev = TraceEvent(ts_ms=now_ms(), type=type_, step=step, data=data)
        run.events.append(ev)
        with self._lock:
            for q in self._subs.get(run.run_id, []):
                q.append(ev)
        return ev


BUS = EventBus()


# ----------------------------------------------------------------------
# 存储：Run 不覆盖，落盘可查
# ----------------------------------------------------------------------
class RunStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._mem: dict[str, Run] = {}
        self._lock = threading.RLock()

    # ---- 内存 ----
    def put(self, run: Run) -> None:
        with self._lock:
            self._mem[run.run_id] = run

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            if run_id in self._mem:
                return self._mem[run_id]
        return self.load(run_id)

    def list_recent(self, limit: int = 50, task_fp: str | None = None) -> list[dict[str, Any]]:
        """按开始时间倒序列出 Run 摘要（内存 + 磁盘合并，磁盘优先保证不丢历史）。"""
        seen: dict[str, dict[str, Any]] = {}
        for f in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if task_fp and d.get("task_fp") != task_fp:
                continue
            seen[d.get("run_id", f.stem)] = self._summary(d)
            if len(seen) >= limit:
                break
        with self._lock:
            for rid, r in self._mem.items():
                if task_fp and r.task_fp != task_fp:
                    continue
                if rid not in seen:
                    seen[rid] = self._summary(r.to_dict(with_events=False))
        return sorted(seen.values(), key=lambda x: x.get("started_at_ms", 0), reverse=True)[:limit]

    @staticmethod
    def _summary(d: dict[str, Any]) -> dict[str, Any]:
        ss = d.get("step_stats") or {}
        return {
            "run_id": d.get("run_id"), "task": (d.get("task") or "")[:120],
            "task_fp": d.get("task_fp"), "status": d.get("status"),
            "duration_ms": d.get("duration_ms"), "cost_yuan": d.get("cost_yuan"),
            "tokens": d.get("tokens"), "steps": ss.get("total", 0),
            "steps_done": ss.get("done", 0), "steps_failed": ss.get("failed", 0),
            "artifacts": len(d.get("artifacts") or []),
            "started_at_ms": d.get("started_at_ms"),
        }

    # ---- 磁盘 ----
    def save(self, run: Run) -> Path:
        self.put(run)
        p = self.root / f"{run.run_id}.json"
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
        return p

    def load(self, run_id: str) -> Run | None:
        p = self.root / f"{run_id}.json"
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return self._from_dict(d)

    @staticmethod
    def _from_dict(d: dict[str, Any]) -> Run:
        """从磁盘恢复 Run（事件与步骤产物保留；运行中状态标记为中断）。"""
        run = Run(run_id=d.get("run_id", ""), task=d.get("task", ""),
                  task_fp=d.get("task_fp", ""), status=d.get("status", STATUS_FAILED))
        run.model = d.get("model", "")
        run.skills = d.get("skills") or []
        run.retrieval = d.get("retrieval") or {}
        run.ranking = d.get("ranking") or []
        run.plan = d.get("plan") or {}
        run.judge = d.get("judge") or {}
        run.artifacts = [Artifact(**a) for a in (d.get("artifacts") or []) if isinstance(a, dict)]
        run.feedback = d.get("feedback") or []
        run.evolution = d.get("evolution") or {}
        run.staged = d.get("staged") or {}
        run.cost_yuan = d.get("cost_yuan") or 0.0
        run.tokens = d.get("tokens") or 0
        run.llm_calls = d.get("llm_calls") or 0
        run.started_at_ms = d.get("started_at_ms") or now_ms()
        run.ended_at_ms = d.get("ended_at_ms") or 0
        run.events = [TraceEvent(**e) for e in (d.get("events") or []) if isinstance(e, dict)]
        for sd in (d.get("steps") or []):
            st = RunStep(idx=sd.get("idx", 0), action=sd.get("action", ""), skill=sd.get("skill"))
            st.status = sd.get("status", STEP_PENDING)
            st.depends_on = sd.get("depends_on") or []
            st.inputs = sd.get("inputs") or []
            st.code = sd.get("code") or ""
            st.error = sd.get("error") or ""
            st.verify_skip_reason = sd.get("verify_skip_reason") or ""
            st.attempts = [ExecutionAttempt(**a) for a in (sd.get("attempts") or []) if isinstance(a, dict)]
            st.artifacts = [Artifact(**a) for a in (sd.get("artifacts") or []) if isinstance(a, dict)]
            st.checks = [ProgrammaticCheck(**c) for c in (sd.get("checks") or []) if isinstance(c, dict)]
            st.verifications = [VerificationResult(**v) for v in (sd.get("verifications") or []) if isinstance(v, dict)]
            run.steps.append(st)
        return run

    def delete(self, run_id: str) -> bool:
        with self._lock:
            self._mem.pop(run_id, None)
        p = self.root / f"{run_id}.json"
        if p.exists():
            p.unlink()
            return True
        return False


# ----------------------------------------------------------------------
# 预算守卫
# ----------------------------------------------------------------------
class BudgetExceeded(RuntimeError):
    pass


def check_budget(run: Run) -> None:
    """在关键节点调用（每次 LLM 调用前后、每步执行前）。超限抛 BudgetExceeded。"""
    if run.cost_yuan > run.budget.max_cost_yuan:
        raise BudgetExceeded(f"成本超限：¥{run.cost_yuan:.4f} > ¥{run.budget.max_cost_yuan}")
    if run.llm_calls > run.budget.max_llm_calls:
        raise BudgetExceeded(f"模型调用超限：{run.llm_calls} > {run.budget.max_llm_calls}")
    if run.duration_ms > run.budget.max_seconds * 1000:
        raise BudgetExceeded(f"耗时超限：{run.duration_ms/1000:.1f}s > {run.budget.max_seconds}s")
    if run.cancel_requested:
        raise BudgetExceeded("运行已被取消")
