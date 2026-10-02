# -*- coding: utf-8 -*-
"""pipeline.py —— 多步 DAG 真实执行引擎（Orchestration = Execution Semantics）。

此前最大的产品断裂
------------------
Orchestrator 会输出一个 DAG，但 Runtime **只执行其中一步**——DAG 成了装饰图。
本模块让 DAG 成为执行语义：

  计划步骤 → 依赖解析 → 逐步真实执行（前序产物进入后序输入） → 每步独立验收
          → 失败重试 → 依赖失败阻断下游 → 汇总

与前序模块的关系
----------------
- `executor.py` 提供单步执行的零件（生成代码 / 修复 / 技能验收），本模块负责**编排它们**；
- `checks.py` 提供 L1 确定性检查与 L2 技能断言；
- `runtime.py` 提供 Run/Step/Attempt/Artifact/Event 数据模型与预算守卫。

产物如何"进入下一步"
--------------------
同一个 Run 有一个 workspace 目录：每步执行完，把该步产物复制到 workspace 根；
下一步在开跑前，把 workspace 根已有产物复制进自己的沙箱目录。
于是后序步骤的代码**真的能读到前序产出的文件**——这是文件系统级的真实，
不是把文件名写进提示词而已。
"""
from __future__ import annotations

import contextvars
import pathlib
import re
import shutil
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any, Callable

from . import checks as checks_mod
from . import config, executor, llm, runtime, sandbox
from .runtime import (
    BUS, STEP_DONE, STEP_FAILED, STEP_PENDING, STEP_RUNNING, STEP_SKIPPED,
    Artifact, BudgetExceeded, ExecutionAttempt, ProgrammaticCheck, Run, RunStep,
    VerificationResult, check_budget, now_ms,
)

# 单步最大尝试次数（含首次）：与 executor 的 max_fix 语义一致
MAX_ATTEMPTS = 3


def _emit(run: Run, type_: str, **data: Any) -> None:
    BUS.publish(run, type_, **data)


def _sha256_file(p: pathlib.Path) -> str:
    import hashlib
    h = hashlib.sha256()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()[:16]


def sync_usage(run: Run, ledger: Any) -> None:
    """把成本账本的当前值同步进 Run（账本是请求级共享的）。"""
    try:
        run.cost_yuan = float(ledger.cost_yuan)
        run.tokens = int(ledger.prompt_tokens + ledger.completion_tokens)
        snap = ledger.snapshot() or {}
        calls = 0
        for v in (snap.get("by_role") or {}).values():
            calls += int((v or {}).get("calls") or 0)
        run.llm_calls = calls or run.llm_calls
    except Exception:
        pass


# ----------------------------------------------------------------------
# 依赖解析
# ----------------------------------------------------------------------
def build_steps(plan: dict[str, Any], workflow: list[list[str]] | None = None) -> list[RunStep]:
    """把方案步骤转成 RunStep，并推断依赖。

    依赖推断规则（可解释、保守）：
    1. **编排器 workflow 是权威**（若提供）：边 [A, B] 表示技能 A 先于 B。
       步骤 i 的依赖 = 所有「skill_j --edge--> skill_i」的步骤 j。
       这让无相互依赖的兄弟步骤（A→B、A→C）真正并行。
    2. 某步骤的技能**没有任何入边**时，保守保留方案顺序前驱作为依赖
       （方案作者按序写出必有原因——通常是数据流；编排图没覆盖到就别擅自并行）。
    3. workflow 缺省 → 线性链（旧行为）。
    4. 映射后若意外成环（防御），整体回退线性链并记录。
    """
    steps_plan = plan.get("steps") or []
    out: list[RunStep] = []
    for i, st in enumerate(steps_plan):
        s = st if isinstance(st, dict) else {"action": str(st)}
        step = RunStep(idx=i, action=str(s.get("action") or ""), skill=s.get("skill") or None)
        step.depends_on = [i - 1] if i > 0 else []
        out.append(step)

    if not workflow:
        return out

    skill_edges = {(a, b) for a, b in workflow if a != b}
    has_incoming = {b for _, b in skill_edges}
    for i, st in enumerate(out):
        if not st.skill:
            continue                              # 无技能映射 → 维持线性兜底
        graph_deps = [j for j, o in enumerate(out)
                      if j != i and o.skill and (o.skill, st.skill) in skill_edges]
        if graph_deps:
            st.depends_on = sorted(set(graph_deps))
        elif st.skill not in has_incoming and i > 0:
            st.depends_on = [i - 1]               # 无入边：保守串行
        else:
            st.depends_on = []                    # 有入边但映射不到库内步骤 → 图根

    # 防御：检查环；有环则整体回退线性（编排器已打断环，这里是最后一道闸）
    def _has_cycle() -> bool:
        state: dict[int, int] = {}
        def dfs(u: int) -> bool:
            state[u] = 1
            for v in out[u].depends_on:
                s = state.get(v, 0)
                if s == 1 or (s == 0 and dfs(v)):
                    return True
            state[u] = 2
            return False
        return any(state.get(i, 0) == 0 and dfs(i) for i in range(len(out)))

    if _has_cycle():
        for i, st in enumerate(out):
            st.depends_on = [i - 1] if i > 0 else []
    return out


def _copy_retry(src: pathlib.Path, dst: pathlib.Path, tries: int = 4) -> bool:
    """带退避的文件复制。Windows 上新写文件可能被 AV/索引服务短暂锁定，
    一次 copy2 的 OSError 不代表真失败——静默吞掉会导致产物传播偶发断裂
    （实测踩过：下游 FileNotFoundError，run 在 PARTIAL/VERIFYING 间摇摆）。"""
    for i in range(tries):
        try:
            shutil.copy2(src, dst)
            return True
        except OSError:
            if i == tries - 1:
                return False
            time.sleep(0.05 * (2 ** i))
    return False


def _mark_downstream_skipped(run: Run, failed_idx: int, reason: str) -> list[int]:
    """把依赖失败步骤的下游标记为 skipped（依赖链阻断）。"""
    skipped: list[int] = []
    changed = True
    while changed:
        changed = False
        for st in run.steps:
            if st.status == STEP_PENDING and any(d in [failed_idx] + skipped for d in st.depends_on):
                st.status = STEP_SKIPPED
                st.verify_skip_reason = f"上游步骤 {failed_idx + 1} 失败：{reason[:80]}"
                skipped.append(st.idx)
                changed = True
    return skipped


# ----------------------------------------------------------------------
# 单步执行（生成 → 沙箱 → 修复 → L1/L2 检查 → L3 技能验收）
# ----------------------------------------------------------------------
def run_step(run: Run, step: RunStep, lib: Any, workspace: pathlib.Path,
             budget: Any, up_artifacts: list[str], max_attempts: int = MAX_ATTEMPTS) -> None:
    skill = lib.get(step.skill) if (step.skill and lib is not None) else None
    step_dir = workspace / f"step{step.idx + 1}"
    step_dir.mkdir(parents=True, exist_ok=True)

    # ---- 前序产物进入本步输入（文件系统级真实）----
    # 注意：这里只登记名字；物理复制在每个 attempt 的 try 目录里做——
    # 沙箱 cwd 是 step_dir/tryN，把文件复制到 step_dir 根目录下游代码读不到
    # （实测踩过：s1.inputs 报告成功、沙箱里 FileNotFoundError）。
    carried: list[str] = []
    carry_pairs: list[tuple[str, str]] = []
    for name in up_artifacts:
        src = workspace / "artifacts" / name
        if not src.is_file():
            continue
        # 关键：恢复原始文件名（workspace 里的展示名带 stepN_ 前缀，但上游代码
        # 是按原名写的——下游沙箱里必须叫原名，否则 "clean.csv" 读不到）
        orig = re.sub(r"^step\d+_", "", name)
        carry_pairs.append((name, orig))
        carried.append(orig)
    step.inputs = carried
    if carried:
        _emit(run, "step.inputs", step=step.idx, files=carried)

    step.status = STEP_RUNNING
    step.started_at_ms = now_ms()
    _emit(run, "step.started", step=step.idx, action=step.action[:160], skill=step.skill)

    stack = sandbox.available_stack()
    code = ""
    result: dict[str, Any] = {}
    from .executor import (_extract_code, _fix_prompt, _gen_code_prompt,
                           _looks_truncated, _record_execution, _verify_with_skill)

    def _llm_snapshot() -> tuple[int, float]:
        """当前请求账本的（调用数, 成本）——用于算本阶段的增量。"""
        try:
            snap = (llm.current_ledger().snapshot() or {}).get("by_role") or {}
            calls = sum(int((v or {}).get("calls") or 0) for v in snap.values())
            cost = float(llm.current_ledger().cost_yuan)
            return calls, cost
        except Exception:
            return 0, 0.0

    for attempt in range(1, max_attempts + 1):
        check_budget(run)
        # 本 attempt 的沙箱工作目录 + 携带产物落位（cwd=tryN，文件必须在 tryN 里）
        workdir = step_dir / f"try{attempt}"
        workdir.mkdir(parents=True, exist_ok=True)
        for aname, orig in carry_pairs:
            _copy_retry(workspace / "artifacts" / aname, workdir / orig)
        phase = "code_gen" if attempt == 1 else f"repair{attempt - 1}_llm"
        if attempt == 1:
            prompt = _gen_code_prompt(run.task, {"action": step.action, "key_params": [],
                                                 "expected_output": ""}, skill, stack,
                                      mode="contract", carried=carried)
        else:
            prompt = _fix_prompt(code, step.attempts[-1].stderr, skill, attempt, mode="contract")
        _emit(run, "code.generating", step=step.idx, attempt=attempt)
        c0, y0 = _llm_snapshot()
        _t = now_ms()
        raw = llm.chat(
            [{"role": "system", "content": "你是严谨的科研工程师，只输出可运行代码。"},
             {"role": "user", "content": prompt}],
            role="executor", temperature=0.2 if attempt == 1 else 0.1,
            max_tokens=executor.CODE_MAX_TOKENS)
        code = _extract_code(raw)
        c1, y1 = _llm_snapshot()
        step.stages[phase + "_ms"] = step.stages.get(phase + "_ms", 0) + (now_ms() - _t)
        step.stages["llm_calls"] = step.stages.get("llm_calls", 0) + (c1 - c0)
        step.stages["llm_cost_yuan"] = round(
            float(step.stages.get("llm_cost_yuan", 0)) + (y1 - y0), 5)
        sync_usage(run, llm.current_ledger())

        # 本地语法预检
        import ast as _ast
        _t = now_ms()
        _syntax_err = None
        try:
            _ast.parse(code)
        except SyntaxError as _se:
            _syntax_err = _se
        # 语法检查与沙箱运行必须**分开计时**：早先合成一段，导致 syntax_check_ms
        # 把沙箱耗时也算了进去（实测出现 48.6s 的"语法检查"，严重误导性能分析）
        step.stages["syntax_check_ms"] = step.stages.get("syntax_check_ms", 0) + (now_ms() - _t)
        if _syntax_err is None:
            _t = now_ms()
            result = sandbox.run_python(code, timeout=90, keep_dir=True,
                                        workdir=workdir)
            step.stages[f"sandbox_try{attempt}_ms"] = now_ms() - _t
        else:
            _se = _syntax_err
            lines = code.splitlines()
            ctx = "\n".join(f"{n}: {lines[n-1]}" for n in
                            range(max(1, (_se.lineno or 1) - 1), min(len(lines), (_se.lineno or 1) + 1) + 1))
            result = {"ok": False, "stdout": "", "returncode": -1, "duration": 0.0, "artifacts": [],
                      "error_kind": "syntax",
                      "stderr": f"SyntaxError: {_se.msg} (line {_se.lineno})\n{ctx}",
                      "workdir": str(step_dir)}
            step.stages[f"sandbox_try{attempt}_ms"] = 0

        at = ExecutionAttempt(
            n=attempt, ok=bool(result.get("ok")), stdout=result.get("stdout") or "",
            stderr=result.get("stderr") or "", error_kind=result.get("error_kind") or "",
            duration_ms=int((result.get("duration") or 0) * 1000),
            truncated=_looks_truncated(result.get("stderr") or "", code))
        step.attempts.append(at)
        _emit(run, "step.attempt", step=step.idx, attempt=attempt, ok=at.ok,
              error_kind=at.error_kind, duration_ms=at.duration_ms)
        if at.ok:
            break
        if attempt < max_attempts:
            _emit(run, "step.retry", step=step.idx, attempt=attempt,
                  reason=("输出截断，要求精简重写" if at.truncated else at.error_kind),
                  hint=(at.stderr or "")[-200:])

    step.code = code
    (step_dir / "final_code.py").write_text(code, encoding="utf-8")

    # ---- 产物登记（复制到 workspace/artifacts 供下游使用）----
    art_dir = workspace / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    paths: list[pathlib.Path] = []
    for a in (result.get("artifacts") or []):
        src = pathlib.Path(a.get("path") or "")
        if not src.is_file():
            continue
        name = f"step{step.idx + 1}_{src.name}"
        dst = art_dir / name
        if not _copy_retry(src, dst):
            continue
        paths.append(dst)
        art = Artifact(name=name, kind="真实运行产物", bytes=dst.stat().st_size,
                       sha256=_sha256_file(dst), from_step=step.idx)
        step.artifacts.append(art)
        run.artifacts.append(art)
        _emit(run, "artifact.created", step=step.idx, name=name, bytes=art.bytes)

    # ---- L1 确定性检查 + L2 技能断言 ----
    _t = now_ms()
    l1 = checks_mod.run_checks(paths, result)
    l2 = checks_mod.checks_from_skill(getattr(skill, "verification", []) or [], paths) if skill else []
    step.checks = [ProgrammaticCheck(**c) for c in (l1 + l2)]
    step.stages["verify_det_ms"] = now_ms() - _t

    # ---- L3 技能验收（LLM，仅对非 machine-readable 条目）----
    if not result.get("ok"):
        step.status = STEP_FAILED
        step.error = (step.attempts[-1].stderr or "")[-400:]
        step.verify_skip_reason = "执行未成功，无法进行产物验收"
    elif skill is None:
        step.verify_skip_reason = "该步骤未关联技能，无验收标准"
        step.status = STEP_DONE
    else:
        items = [v for v in (skill.verification or [])
                 if not checks_mod.parse_assertions([v])]
        if items:
            _t = now_ms()
            raw_v = _verify_with_skill(skill, run.task, step.action, code,
                                       result.get("stdout") or "",
                                       [p.name for p in paths])
            step.stages["verify_sem_ms"] = now_ms() - _t
            c1, y1 = _llm_snapshot()
            step.stages["llm_calls"] = step.stages.get("llm_calls", 0) + (c1 - c0)
            step.stages["llm_cost_yuan"] = round(float(step.stages.get("llm_cost_yuan", 0)) + (y1 - y0), 5)
            step.verifications = [VerificationResult(layer="llm", **v) for v in raw_v]
        else:
            step.verify_skip_reason = "该技能的验收条目已全部由程序化断言覆盖（L1/L2）"
        # 执行成功即视为该步完成；验收结果单独记录（不覆盖完成状态），
        # 失败信号由「L1/L2 全部未通过 且 无 L3 验收」体现，供汇总与前端展示。
        step.status = STEP_DONE
        if step.checks and not any(c.passed for c in step.checks) and not step.verifications:
            step.verify_skip_reason = "产物未通过任何确定性检查，且无 L3 验收结果"
    for c in step.checks:
        _emit(run, "check.result", step=step.idx, name=c.name, passed=c.passed, detail=c.detail)

    step.ended_at_ms = now_ms()
    # 执行记账（沿用 executor 的记录逻辑，保持技能统计一致）
    try:
        _record_execution(skill, run.task, {"action": step.action}, result, step.attempts)
    except Exception:
        pass
    sync_usage(run, llm.current_ledger())
    _emit(run, "step.completed", step=step.idx, status=step.status,
          duration_ms=step.duration_ms, n_attempts=step.n_attempts,
          artifacts=len(step.artifacts),
          checks=f"{sum(1 for c in step.checks if c.passed)}/{len(step.checks)}")


# ----------------------------------------------------------------------
# 主入口：执行整条 DAG
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# 图调度器：DAG = Runtime 的执行核心
# ----------------------------------------------------------------------
def _run_steps_graph(run: Run, workspace: pathlib.Path, lib: Any,
                     budget: Any) -> None:
    """按依赖图真实调度：就绪即派发，无依赖的步骤并行执行。

    - 线程池并发（Demo 规模下正确性优先，不引入分布式）；
    - contextvars 在派发时快照，账本随线程正确传播（成本不串账）；
    - BudgetExceeded：停止派发新步骤，等在跑的收尾，run 标记预算超限；
    - 单步普通异常：标记该步失败、阻断其下游，不影响兄弟分支；
    - max_concurrency：真实并发度记录（前端画甘特/并行走廊用）。
    """
    lock = threading.Lock()
    conc = {"cur": 0, "max": 0}
    by_idx = {st.idx: st for st in run.steps}
    remaining = {st.idx: set(st.depends_on) for st in run.steps}
    budget_hit: BudgetExceeded | None = None
    max_workers = max(1, min(3, len(run.steps)))

    def _in_ctx(fn: Any, st: RunStep) -> Any:
        # 每个任务独立 copy_context()：Context 对象不可被多线程同时进入，
        # 但拷贝出的新 Context 携带同一份账本引用（成本随线程正确记账）
        return contextvars.copy_context().run(fn, st)

    def _dispatchable() -> list[int]:
        return [i for i in sorted(remaining) if not remaining[i]]

    def _worker(st: RunStep) -> str:
        with lock:
            conc["cur"] += 1
            conc["max"] = max(conc["max"], conc["cur"])
        try:
            up = [a.name for a in run.artifacts]
            run_step(run, st, lib, workspace, budget, up,
                     max_attempts=budget.max_attempts_per_step)
            return "done"
        except BudgetExceeded as exc:
            return f"budget:{exc}"
        except Exception as exc:                  # 单步异常不应终止整个 run
            st.status = STEP_FAILED
            st.error = f"{type(exc).__name__}: {exc}"
            st.ended_at_ms = now_ms()
            _emit(run, "step.error", step=st.idx, error=st.error[:300])
            return "error"
        finally:
            with lock:
                conc["cur"] -= 1

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        inflight: dict[Any, RunStep] = {}
        while True:
            if budget_hit is None:
                for idx in _dispatchable():
                    remaining.pop(idx)
                    st = by_idx[idx]
                    inflight[ex.submit(_in_ctx, _worker, st)] = st
            if not inflight:
                break
            done, _ = wait(set(inflight), return_when=FIRST_COMPLETED)
            for fut in done:
                st = inflight.pop(fut)
                outcome = fut.result()
                if outcome.startswith("budget:"):
                    budget_hit = BudgetExceeded(outcome.split(":", 1)[1])
                    continue
                if st.status == STEP_FAILED:
                    skipped = _mark_downstream_skipped(run, st.idx, st.error)
                    for i in skipped:
                        remaining.pop(i, None)
                    if skipped:
                        _emit(run, "steps.skipped", steps=skipped,
                              reason="上游失败，依赖链阻断")
                else:
                    # 成功收尾：从所有未派发步骤的依赖里移除自己（放行下游）
                    for ds in remaining.values():
                        ds.discard(st.idx)

    if budget_hit is not None:
        run.status = runtime.STATUS_BUDGET_EXCEEDED
        run.error = str(budget_hit)
        _emit(run, "run.budget_exceeded", reason=run.error, cost=run.cost_yuan)
    if conc["max"] > 1:
        run.staged["max_concurrency"] = conc["max"]
    run.staged["scheduler"] = "dag-parallel" if conc["max"] > 1 else "dag-serial"


def _critical_path(run: Run) -> dict[str, Any]:
    """DAG 上的最长路（按真实 duration_ms）——「时间到底花在哪条链上」。

    失败步骤同样占真实耗时，一并计入（失败+修复往往是关键路径的大头）。"""
    dur = {st.idx: st.duration_ms for st in run.steps
           if st.status in (STEP_DONE, STEP_FAILED) and st.duration_ms > 0}
    best: dict[int, tuple[int, list[int]]] = {}
    order = []                                    # 拓扑序（deps 均指向更小 idx 的重排图）
    visited: set[int] = set()
    def topo(i: int) -> None:
        if i in visited:
            return
        visited.add(i)
        for d in run.steps[i].depends_on:
            topo(d)
        order.append(i)
    for st in run.steps:
        topo(st.idx)
    for i in order:
        if i not in dur:
            continue
        preds = [best[d] for d in run.steps[i].depends_on if d in best]
        total, path = max(preds, key=lambda t: t[0]) if preds else (0, [])
        best[i] = (total + dur[i], path + [i])
    if not best:
        return {}
    total, path = max(best.values(), key=lambda t: t[0])
    return {"steps": path, "ms": total}


def execute_run(run: Run, lib: Any, workspace: pathlib.Path,
                plan: dict[str, Any], *, max_steps: int = 4,
                budget: Any | None = None,
                workflow: list[list[str]] | None = None,
                step_filter: Callable[[int, dict[str, Any]], bool] | None = None) -> Run:
    """按 DAG 顺序真实执行方案步骤。

    - `workflow`：编排器输出的技能依赖边 [A, B]（A 先于 B）——**权威执行图**。
      不传则回退线性链。DAG = Runtime 要求调用方必须传编排结果。
    - `max_steps`：最多执行几步（控制成本与时长；默认 4，选前 N 个可执行步骤）
    - `step_filter`：自定义筛选（默认用 executor 的可执行性启发式）
    - 依赖失败会阻断下游（标记 skipped），run 最终状态由 finalize_status 统一判定
    """
    budget = budget or run.budget
    steps_plan = plan.get("steps") or []
    if not steps_plan:
        run.status = runtime.STATUS_FAILED
        run.error = "方案没有可执行步骤"
        _emit(run, "run.failed", reason=run.error)
        return run

    # 选择要执行的步骤（启发式：优先可落地的分析类步骤）
    picked: list[int] = []
    for i, st in enumerate(steps_plan):
        if len(picked) >= max_steps:
            break
        action = st.get("action") if isinstance(st, dict) else str(st)
        if step_filter is not None:
            if step_filter(i, st if isinstance(st, dict) else {"action": str(action)}):
                picked.append(i)
        elif executor.pick_executable_step({"steps": [st]}) == 0:
            picked.append(i)
    if not picked:                       # 没有明显可执行步骤 -> 取前 max_steps 个
        picked = list(range(min(max_steps, len(steps_plan))))
    run.staged["picked_steps"] = picked

    all_steps = build_steps(plan, workflow)
    run.steps = [all_steps[i] for i in picked]
    for new_idx, st in enumerate(run.steps):      # 重排索引，依赖经 picked 映射到新下标
        st.idx = new_idx
    pos = {old: new for new, old in enumerate(picked)}
    for st in run.steps:
        st.depends_on = sorted({pos[d] for d in st.depends_on if d in pos})

    run.status = runtime.STATUS_EXECUTING
    # DAG = Runtime：把解析后的权威执行图广播给前端（WOW-1 的收束目标就是这张图）
    _emit(run, "dag.ready",
          nodes=[{"idx": st.idx, "skill": st.skill, "action": st.action[:80],
                  "depends_on": st.depends_on} for st in run.steps],
          workflow_source="orchestrator" if workflow else "linear-fallback")
    _emit(run, "run.executing", steps=len(run.steps), picked=picked)

    _run_steps_graph(run, workspace, lib, budget)

    if run.status != runtime.STATUS_BUDGET_EXCEEDED:
        cp = _critical_path(run)
        if cp:
            run.staged["critical_path"] = cp

    done = sum(1 for s in run.steps if s.status == STEP_DONE)
    failed = sum(1 for s in run.steps if s.status == STEP_FAILED)
    # 注意：这里**不设终态**。整条 Run 还包含后续阶段（盲评/反馈/蒸馏），
    # 终态必须由 pipeline.finalize_status() 在最后统一判定——早先在这里定终态，
    # 会被后续阶段（EVOLVING）覆盖成非终态，落盘时被误判为 PARTIAL（实测踩过）。
    if run.status != runtime.STATUS_BUDGET_EXCEEDED:   # 预算状态不被覆盖
        run.status = runtime.STATUS_VERIFYING if failed == 0 else runtime.STATUS_PARTIAL
    _emit(run, "execution.finished", done=done, failed=failed,
          duration_ms=run.duration_ms, artifacts=len(run.artifacts))
    return run


def finalize_status(run: Run) -> str:
    """在整条 Run 的所有阶段结束后调用，统一判定终态（唯一权威）。

    判定规则：
      - 预算超限 / 已取消 → 保持原状态
      - 无失败步骤 → COMPLETED
      - 有成功步骤 → PARTIAL
      - 全失败 → FAILED
    """
    if run.status in (runtime.STATUS_BUDGET_EXCEEDED, runtime.STATUS_CANCELLED):
        final = run.status
    else:
        done = sum(1 for s in run.steps if s.status == STEP_DONE)
        failed = sum(1 for s in run.steps if s.status == STEP_FAILED)
        skipped = sum(1 for s in run.steps if s.status == STEP_SKIPPED)
        if failed == 0 and skipped == 0 and done > 0:
            final = runtime.STATUS_COMPLETED      # 全部到位才算 COMPLETED（有跳过=部分完成）
        elif done > 0 or skipped > 0:
            final = runtime.STATUS_PARTIAL
        else:
            final = runtime.STATUS_FAILED
    run.status = final
    run.ended_at_ms = run.ended_at_ms or now_ms()
    return final
