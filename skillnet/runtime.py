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
import os
import re
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from collections import deque
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
STATUS_INTERRUPTED = "INTERRUPTED"
TERMINAL = {STATUS_COMPLETED, STATUS_FAILED, STATUS_PARTIAL, STATUS_CANCELLED,
            STATUS_BUDGET_EXCEEDED, STATUS_INTERRUPTED}

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
    input_artifacts: list[dict[str, Any]] = field(default_factory=list)
    code: str = ""
    attempts: list[ExecutionAttempt] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    checks: list[ProgrammaticCheck] = field(default_factory=list)
    verifications: list[VerificationResult] = field(default_factory=list)
    verify_skip_reason: str = ""
    error: str = ""
    started_at_ms: int = 0
    ended_at_ms: int = 0
    # 子阶段细分（回应「execution 39.7s 仍是黑盒」）：
    # 记录每一步内部的阶段耗时、LLM 调用数、token 与成本，用于回答
    # 「这段时间里有多少是模型等待」。键名形如 code_gen_ms / sandbox_try1_ms /
    # repair1_llm_ms / verify_det_ms / verify_sem_ms / llm_calls / llm_tokens。
    stages: dict[str, float] = field(default_factory=dict)

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
            "input_artifacts": self.input_artifacts,
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
            "started_at_ms": self.started_at_ms,
            "ended_at_ms": self.ended_at_ms,
            "stages": {k: (round(v, 1) if isinstance(v, float) else v) for k, v in self.stages.items()},
        }


@dataclass
class TraceEvent:
    ts_ms: int
    type: str
    step: int | None = None
    data: dict[str, Any] = field(default_factory=dict)
    seq: int = 0

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
            "cost_yuan": round(self.cost_yuan, 4), "tokens": self.tokens,
            "llm_calls": self.llm_calls,
            "cancel_requested": self.cancel_requested,
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
        q = deque(maxlen=2048)
        with self._lock:
            self._subs.setdefault(run_id, []).append(q)
        return q

    def unsubscribe(self, run_id: str, q) -> None:
        with self._lock:
            subs = self._subs.get(run_id) or []
            if q in subs:
                subs.remove(q)
            if not subs:
                self._subs.pop(run_id, None)

    def replay(self, run: Run, after: int = 0) -> list[TraceEvent]:
        """在发布锁下读取事件快照；游标同时适用于存量回放和实时轮询。"""
        with self._lock:
            return [ev for ev in run.events if ev.seq > after]

    def publish(self, run: Run, type_: str, *, step: int | None = None, **data: Any) -> TraceEvent:
        with self._lock:
            seq = run.events[-1].seq + 1 if run.events else 1
            ev = TraceEvent(ts_ms=now_ms(), type=type_, step=step, data=data, seq=seq)
            run.events.append(ev)
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
        self._summaries: dict[Path, tuple[tuple[int, int, int, int], dict[str, Any]]] = {}

    # ---- 内存 ----
    def put(self, run: Run) -> None:
        with self._lock:
            self._mem[run.run_id] = run

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            if run_id in self._mem:
                return self._mem[run_id]
            run = self.load(run_id)
            if run is not None:
                self._mem[run_id] = run
            return run

    def sweep_interrupted(self) -> int:
        """启动时清理僵尸 Run：非终态（进程被杀留下的）标记为 INTERRUPTED。

        为什么需要：worker 抛异常或进程被杀时，Run 会永久停在 CREATED/EXECUTING，
        列表里出现"永远在跑"的假象（实测踩过）。
        """
        n = 0
        for f in self.root.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(d, dict):
                continue
            if d.get("status") in TERMINAL:
                continue
            d["status"] = STATUS_INTERRUPTED
            d["error"] = d.get("error") or "进程中断（启动时清扫）"
            d["ended_at_ms"] = now_ms()
            try:
                self.save(self._from_dict(d))
                n += 1
            except (OSError, ValueError, TypeError):
                pass
        return n

    def list_recent(self, limit: int = 50, task_fp: str | None = None) -> list[dict[str, Any]]:
        return self.list_page(limit=limit, task_fp=task_fp)["runs"]

    def list_page(self, limit: int = 50, offset: int = 0, *, task_fp: str | None = None,
                  q: str = "", status: str | None = None) -> dict[str, Any]:
        """按任务开始时间分页。缓存轻量摘要；仅重新读取改变的检查点文件。

        文件修改时间不能代表任务时间（取消、性能上报也会改写旧记录）。
        内存中的活动任务总是覆盖磁盘检查点，完整任务文本用于搜索。
        """
        with self._lock:
            paths = set(self.root.glob("*.json"))
            for stale in self._summaries.keys() - paths:
                del self._summaries[stale]
            seen: dict[str, dict[str, Any]] = {}
            for path in paths:
                try:
                    stat = path.stat()
                    # Atomic replacements can share size and a coarse Windows
                    # timestamp; file identity distinguishes those checkpoints.
                    fingerprint = (stat.st_mtime_ns, stat.st_size, stat.st_ino, stat.st_ctime_ns)
                    cached = self._summaries.get(path)
                    if not cached or cached[0] != fingerprint:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        if not isinstance(data, dict) or not data.get("run_id"):
                            continue
                        cached = (fingerprint, self._summary(data))
                        self._summaries[path] = cached
                    seen[cached[1]["run_id"]] = cached[1]
                except (OSError, ValueError, TypeError, AttributeError):
                    continue
            for rid, run in self._mem.items():
                # Do not serialize code, attempts or the event log for a list request.
                seen[rid] = self._summary({
                    "run_id": rid, "task": run.task, "task_fp": run.task_fp,
                    "status": run.status, "duration_ms": run.duration_ms,
                    "cost_yuan": run.cost_yuan, "tokens": run.tokens, "llm_calls": run.llm_calls,
                    "step_stats": run.step_stats(), "steps": [
                        {"checks": [c.to_dict() for c in s.checks],
                         "verifications": [v.to_dict() for v in s.verifications]}
                        for s in run.steps], "staged": run.staged,
                    "artifacts": run.artifacts, "started_at_ms": run.started_at_ms,
                })
            needle = q.strip().casefold()
            rows = [s for s in seen.values()
                    if (not task_fp or s["task_fp"] == task_fp)
                    and (not status or s["status"] == status)
                    and (not needle or needle in s["_search"])]
            rows.sort(key=lambda s: (s.get("started_at_ms") or 0, s["run_id"]), reverse=True)
            summary = {"total": len(rows), "completed": sum(s["status"] == STATUS_COMPLETED for s in rows),
                       "active": sum(s["status"] not in TERMINAL for s in rows),
                       "artifacts": sum(s["artifacts"] for s in rows),
                       "cost_yuan": round(sum(s.get("cost_yuan") or 0 for s in rows), 4)}
            page = [{k: v for k, v in s.items() if k != "_search"} for s in rows[offset:offset + limit]]
            return {"runs": page, "total": len(rows), "offset": offset, "limit": limit,
                    "has_more": offset + len(page) < len(rows), "summary": summary}

    @staticmethod
    def _summary(d: dict[str, Any]) -> dict[str, Any]:
        ss = d.get("step_stats") or {}
        checks = [c for s in d.get("steps") or [] for c in s.get("checks") or []]
        semantic = [c for s in d.get("steps") or [] for c in s.get("verifications") or []]
        gate = (d.get("staged") or {}).get("learning_gate") or {}
        return {
            "run_id": d.get("run_id"), "task": (d.get("task") or "")[:120],
            "task_fp": d.get("task_fp"), "status": d.get("status"),
            "duration_ms": d.get("duration_ms"), "cost_yuan": d.get("cost_yuan"),
            "tokens": d.get("tokens"), "steps": ss.get("total", 0),
            "steps_done": ss.get("done", 0), "steps_failed": ss.get("failed", 0),
            "artifacts": len(d.get("artifacts") or []),
            "started_at_ms": d.get("started_at_ms"),
            "llm_calls": d.get("llm_calls", 0),
            "checks_passed": sum(c.get("passed") is True for c in checks), "checks_total": len(checks),
            "semantic_passed": sum(c.get("passed") is True for c in semantic), "semantic_total": len(semantic),
            "learning_eligible": gate.get("eligible"), "learning_reason": gate.get("reason") or gate.get("skip_reason", ""),
            "_search": " ".join(str(d.get(k) or "") for k in ("task", "run_id", "task_fp")).casefold(),
        }

    # ---- 磁盘 ----
    def save(self, run: Run) -> Path:
        p = self._path(run.run_id)
        with self._lock:
            self._mem[run.run_id] = run
            # 同一 Run 的 worker/取消/性能上报可并发保存。唯一临时文件和串行替换
            # 防止写坏 JSON、覆盖尚未完成的写入，或因共用 .tmp 导致 FileNotFound。
            tmp: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                                 dir=self.root, suffix=".tmp", delete=False) as f:
                    tmp = Path(f.name)
                    json.dump(run.to_dict(), f, ensure_ascii=False, indent=1)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, p)
            finally:
                if tmp is not None:
                    tmp.unlink(missing_ok=True)
        return p

    def _path(self, run_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,95}", run_id):
            raise ValueError("非法的 run_id")
        return self.root / f"{run_id}.json"

    def load(self, run_id: str) -> Run | None:
        try:
            p = self._path(run_id)
        except ValueError:
            return None
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        try:
            return self._from_dict(d)
        except (TypeError, ValueError, KeyError):
            return None

    @staticmethod
    def _from_dict(d: dict[str, Any]) -> Run:
        """从磁盘恢复 Run（事件与步骤产物保留；运行中状态标记为中断）。"""
        if not isinstance(d, dict):
            raise TypeError("Run checkpoint must be an object")
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
        run.cancel_requested = bool(d.get("cancel_requested"))
        run.budget = Budget(**{k: v for k, v in (d.get("budget") or {}).items()
                              if k in Budget.__dataclass_fields__})
        run.started_at_ms = d.get("started_at_ms") or now_ms()
        run.ended_at_ms = d.get("ended_at_ms") or 0
        run.events = [TraceEvent(**e) for e in (d.get("events") or []) if isinstance(e, dict)]
        for seq, ev in enumerate(run.events, 1):
            if not ev.seq:
                ev.seq = seq                  # 兼容尚未持久化 SSE 游标的历史记录
        for sd in (d.get("steps") or []):
            st = RunStep(idx=sd.get("idx", 0), action=sd.get("action", ""), skill=sd.get("skill"))
            st.status = sd.get("status", STEP_PENDING)
            st.depends_on = sd.get("depends_on") or []
            st.inputs = sd.get("inputs") or []
            st.input_artifacts = sd.get("input_artifacts") or []
            st.code = sd.get("code") or ""
            st.error = sd.get("error") or ""
            st.verify_skip_reason = sd.get("verify_skip_reason") or ""
            st.stages = sd.get("stages") or {}
            # 时间戳必须一并恢复：漏掉会导致 duration_ms 恒为 0（实测踩过——
            # 页面上所有步骤耗时显示 0ms，而实际是 23.9s/26.0s/96.3s）
            st.started_at_ms = sd.get("started_at_ms") or 0
            st.ended_at_ms = sd.get("ended_at_ms") or 0
            # 兼容早先落盘的文件（那时未写时间戳但写了 duration_ms）：
            # 用 duration_ms 反推，避免历史 Run 的步骤耗时全部显示 0ms。
            if not st.started_at_ms and (sd.get("duration_ms") or 0) > 0:
                st.started_at_ms = 1
                st.ended_at_ms = 1 + int(sd["duration_ms"])
            st.attempts = [ExecutionAttempt(**a) for a in (sd.get("attempts") or []) if isinstance(a, dict)]
            st.artifacts = [Artifact(**a) for a in (sd.get("artifacts") or []) if isinstance(a, dict)]
            st.checks = [ProgrammaticCheck(**c) for c in (sd.get("checks") or []) if isinstance(c, dict)]
            st.verifications = [VerificationResult(**v) for v in (sd.get("verifications") or []) if isinstance(v, dict)]
            run.steps.append(st)
        return run

    def delete(self, run_id: str) -> bool:
        with self._lock:
            self._mem.pop(run_id, None)
        p = self._path(run_id)
        if p.exists():
            p.unlink()
            return True
        return False


# ----------------------------------------------------------------------
# 预算守卫
# ----------------------------------------------------------------------
class BudgetExceeded(RuntimeError):
    pass


class RunCancelled(BudgetExceeded):
    """取消与额度超限使用不同终态，但兼容既有预算检查点。"""


def check_budget(run: Run) -> None:
    """在关键节点调用（每次 LLM 调用前后、每步执行前）。超限抛 BudgetExceeded。"""
    if run.cancel_requested:
        raise RunCancelled("运行已被取消")
    if run.cost_yuan >= run.budget.max_cost_yuan:
        raise BudgetExceeded(f"成本已达上限：¥{run.cost_yuan:.4f} / ¥{run.budget.max_cost_yuan}")
    if run.llm_calls >= run.budget.max_llm_calls:
        raise BudgetExceeded(f"模型调用已达上限：{run.llm_calls} / {run.budget.max_llm_calls}")
    if run.duration_ms > run.budget.max_seconds * 1000:
        raise BudgetExceeded(f"耗时超限：{run.duration_ms/1000:.1f}s > {run.budget.max_seconds}s")
