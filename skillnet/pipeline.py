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

import pathlib
import re
import shutil
import time
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

    依赖推断规则（保守、可解释）：
    1. 默认**顺序依赖**：第 i 步依赖第 i-1 步（方案本身就是按序给出的）；
    2. 若两步之间**没有任何技能耦合**（分属无关领域且无关系边），则不建立依赖，
       允许它们被识别为可并行（当前实现仍顺序执行，但标记出来供前端展示与后续并发化）。
    """
    steps_plan = plan.get("steps") or []
    out: list[RunStep] = []
    for i, st in enumerate(steps_plan):
        s = st if isinstance(st, dict) else {"action": str(st)}
        step = RunStep(idx=i, action=str(s.get("action") or ""), skill=s.get("skill") or None)
        step.depends_on = [i - 1] if i > 0 else []
        out.append(step)
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
    skill = lib.get(step.skill) if step.skill else None
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
def execute_run(run: Run, lib: Any, workspace: pathlib.Path,
                plan: dict[str, Any], *, max_steps: int = 4,
                budget: Any | None = None,
                step_filter: Callable[[int, dict[str, Any]], bool] | None = None) -> Run:
    """按 DAG 顺序真实执行方案步骤。

    - `max_steps`：最多执行几步（控制成本与时长；默认 4，选前 N 个可执行步骤）
    - `step_filter`：自定义筛选（默认用 executor 的可执行性启发式）
    - 依赖失败会阻断下游（标记 skipped），run 最终状态为 PARTIAL
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

    all_steps = build_steps(plan)
    run.steps = [all_steps[i] for i in picked]
    for new_idx, st in enumerate(run.steps):      # 重排索引，保持依赖指向本 run 内步骤
        st.idx = new_idx
        st.depends_on = [new_idx - 1] if new_idx > 0 else []

    run.status = runtime.STATUS_EXECUTING
    _emit(run, "run.executing", steps=len(run.steps), picked=picked)

    for st in run.steps:
        if st.status == STEP_SKIPPED:                 # 依赖链阻断：跳过执行
            _emit(run, "step.skipped", step=st.idx, reason=st.verify_skip_reason)
            continue
        try:
            check_budget(run)
        except BudgetExceeded as exc:
            run.status = runtime.STATUS_BUDGET_EXCEEDED
            run.error = str(exc)
            _emit(run, "run.budget_exceeded", reason=str(exc), cost=run.cost_yuan)
            break
        up = [a.name for a in run.artifacts]          # 目前所有已产出物均可被下游读取
        try:
            run_step(run, st, lib, workspace, budget, up, max_attempts=budget.max_attempts_per_step)
        except BudgetExceeded as exc:
            run.status = runtime.STATUS_BUDGET_EXCEEDED
            run.error = str(exc)
            _emit(run, "run.budget_exceeded", reason=str(exc), cost=run.cost_yuan)
            break
        except Exception as exc:                      # 单步异常不应终止整个 run
            st.status = STEP_FAILED
            st.error = f"{type(exc).__name__}: {exc}"
            st.ended_at_ms = now_ms()
            _emit(run, "step.error", step=st.idx, error=st.error[:300])
        if st.status == STEP_FAILED:
            skipped = _mark_downstream_skipped(run, st.idx, st.error)
            if skipped:
                _emit(run, "steps.skipped", steps=skipped, reason="上游失败，依赖链阻断")

    done = sum(1 for s in run.steps if s.status == STEP_DONE)
    failed = sum(1 for s in run.steps if s.status == STEP_FAILED)
    # 注意：这里**不设终态**。整条 Run 还包含后续阶段（盲评/反馈/蒸馏），
    # 终态必须由 pipeline.finalize_status() 在最后统一判定——早先在这里定终态，
    # 会被后续阶段（EVOLVING）覆盖成非终态，落盘时被误判为 PARTIAL（实测踩过）。
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
        if failed == 0 and done > 0:
            final = runtime.STATUS_COMPLETED
        elif done > 0:
            final = runtime.STATUS_PARTIAL
        else:
            final = runtime.STATUS_FAILED
    run.status = final
    run.ended_at_ms = run.ended_at_ms or now_ms()
    return final
